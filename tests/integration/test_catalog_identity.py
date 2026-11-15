"""Run catalog identity is durable and never guessed for mismatched manifests."""

from concurrent.futures import ThreadPoolExecutor

import pytest

from recovery.adapters.store import OperationalStore
from recovery.domain.errors import DomainError
from recovery.runtime.context import visitor_id
from recovery.services.catalog_identity import identity, resolve


def test_run_identity_is_recorded_durably_and_rejects_manifest_drift(svc, monkeypatch):
    run = svc.scenario.create_run()["scenario_run_id"]
    recorded = svc.store.kv_get(f"run_catalog:{run}")
    assert recorded == identity(svc.catalog)
    assert resolve(svc, run) is svc.catalog
    reopened = OperationalStore(svc.store.url)
    try:
        assert reopened.kv_get(f"run_catalog:{run}") == recorded
    finally:
        reopened.engine.dispose()
    monkeypatch.setitem(svc.catalog.manifest, "manifest_version", "changed-without-migration")
    with pytest.raises(DomainError) as error:
        resolve(svc, run)
    assert error.value.code == "CATALOG_IDENTITY_MISMATCH"


def test_failed_identity_write_rolls_back_run(svc, monkeypatch):
    previous = svc.scenario.create_run()["scenario_run_id"]
    assert svc.monitoring.get(previous, "case-primary")["status"] == "active"
    created = []
    original = svc.store.kv_set

    def fail_identity(key, value):
        if key.startswith("run_catalog:"):
            created.append(key.split(":", 1)[1])
            raise RuntimeError("injected identity write failure")
        return original(key, value)

    monkeypatch.setattr(svc.store, "kv_set", fail_identity)
    with pytest.raises(RuntimeError, match="identity write failure"):
        svc.scenario.create_run()
    assert len(created) == 1 and svc.store.get_run(created[0]) is None
    assert svc.store.current_run()["run_id"] == previous
    assert svc.monitoring.get(previous, "case-primary")["status"] == "active"


def test_failed_case_setup_rolls_back_run_identity_and_previous_pause(svc, monkeypatch):
    previous = svc.scenario.create_run()["scenario_run_id"]
    created = []
    original_write = svc.store.kv_set
    original_subscription = svc.monitoring.create_subscription

    def capture_identity(key, value):
        if key.startswith("run_catalog:"):
            created.append(key.split(":", 1)[1])
        return original_write(key, value)

    def fail_second(run_id, case_id):
        if case_id == "case-secondary-a":
            raise RuntimeError("injected subscription failure")
        return original_subscription(run_id, case_id)

    monkeypatch.setattr(svc.store, "kv_set", capture_identity)
    monkeypatch.setattr(svc.monitoring, "create_subscription", fail_second)
    with pytest.raises(RuntimeError, match="subscription failure"):
        svc.scenario.create_run()
    assert len(created) == 1 and svc.store.get_run(created[0]) is None
    assert svc.store.kv_get(f"run_catalog:{created[0]}") is None
    assert svc.store.list_cases(created[0]) == []
    assert svc.store.current_run()["run_id"] == previous
    assert svc.monitoring.get(previous, "case-primary")["status"] == "active"


def test_missing_identity_is_not_silently_reconstructed(svc):
    run = svc.scenario.create_run()["scenario_run_id"]
    svc.store.kv_set(f"run_catalog:{run}", None)
    with pytest.raises(DomainError) as error:
        resolve(svc, run)
    assert error.value.code == "CATALOG_IDENTITY_UNAVAILABLE"


def test_concurrent_visitors_keep_separate_run_identities(svc):
    def create_for(visitor):
        token = visitor_id.set(visitor)
        try:
            run = svc.scenario.create_run()["scenario_run_id"]
            return run, svc.store.kv_get(f"run_catalog:{run}"), svc.store.kv_get(f"run_owner:{run}")
        finally:
            visitor_id.reset(token)

    with ThreadPoolExecutor(max_workers=2) as pool:
        runs = list(pool.map(create_for, ["visitor-one", "visitor-two"]))
    assert runs[0][0] != runs[1][0]
    assert {row[2] for row in runs} == {"visitor-one", "visitor-two"}
    assert all(row[1] == identity(svc.catalog) for row in runs)
