"""Batch creation preserves visitor, transaction and retry boundaries."""

import importlib
import threading
from concurrent.futures import ThreadPoolExecutor

import pytest

from recovery.config import settings
from recovery.domain.errors import DomainError
from recovery.runtime.context import visitor_id
from recovery.services.batches import BatchService


@pytest.fixture
def public_api(svc, monkeypatch):
    module = importlib.import_module("recovery.api.app")
    monkeypatch.setattr(module, "SERVICES", svc)
    old = settings.public_demo
    object.__setattr__(settings, "public_demo", True)
    yield module
    object.__setattr__(settings, "public_demo", old)


def test_batch_is_durable_idempotent_and_launches_each_component(svc, monkeypatch):
    run = svc.scenario.create_run()["scenario_run_id"]
    launches = []
    monkeypatch.setattr(svc.coordinator, "_launch", lambda *args, **kwargs: launches.append(args))
    service = BatchService(svc)
    request = {"assembly_id": svc.catalog.engine["engine_id"],
               "component_ids": ["component-primary", "component-secondary-a"], "mode": "seeded"}

    batch, replay = service.create(run, request, "same-key")
    again, replay_again = service.create(run, request, "same-key")
    assert replay is False and replay_again is True and again == batch
    assert len(launches) == 2
    assert {row["component_id"] for row in batch["components"]} == set(request["component_ids"])
    assert all(row["generation_id"] and row["status"] == "accepted" for row in batch["components"])
    status = service.get(batch["batch_id"])
    assert status["run_id"] == run
    assert all(part["tasks"] == [] for part in status["components"])
    with pytest.raises(DomainError) as error:
        service.create(run, {**request, "component_ids": ["component-primary"]}, "same-key")
    assert error.value.status == 409


def test_batch_rejects_invalid_parts_before_starting_any_work(svc, monkeypatch):
    run = svc.scenario.create_run()["scenario_run_id"]
    launches = []
    monkeypatch.setattr(svc.coordinator, "_launch", lambda *args, **kwargs: launches.append(args))
    service = BatchService(svc)
    for component_ids in ([], ["component-primary", "component-primary"], ["component-primary", "missing"]):
        with pytest.raises(DomainError):
            service.create(run, {"assembly_id": svc.catalog.engine["engine_id"], "component_ids": component_ids,
                                 "mode": "seeded"}, "key")
    assert launches == []
    assert svc.store.get_case(run, "case-primary")["active_generation_id"] is None


def test_batch_is_not_visible_to_another_visitor(svc, monkeypatch):
    monkeypatch.setattr(svc.coordinator, "_launch", lambda *args, **kwargs: None)
    owner = visitor_id.set("owner-a")
    try:
        run = svc.scenario.create_run()["scenario_run_id"]
        service = BatchService(svc)
        batch, _ = service.create(run, {"assembly_id": svc.catalog.engine["engine_id"],
                                        "component_ids": ["component-primary"], "mode": "seeded"}, "key")
        assert service.get(batch["batch_id"])["run_id"] == run
        other = visitor_id.set("owner-b")
        try:
            with pytest.raises(DomainError) as error:
                service.get(batch["batch_id"])
            assert error.value.status == 404
        finally:
            visitor_id.reset(other)
    finally:
        visitor_id.reset(owner)


def test_simultaneous_retries_create_only_one_batch(svc, monkeypatch):
    run = svc.scenario.create_run()["scenario_run_id"]
    launches = []
    monkeypatch.setattr(svc.coordinator, "_launch", lambda *args, **kwargs: launches.append(args))
    service = BatchService(svc)
    request = {"assembly_id": svc.catalog.engine["engine_id"],
               "component_ids": ["component-primary", "component-secondary-a"], "mode": "seeded"}
    with ThreadPoolExecutor(max_workers=2) as pool:
        results = list(pool.map(lambda _: service.create(run, request, "concurrent-key"), range(2)))
    assert results[0][0]["batch_id"] == results[1][0]["batch_id"]
    assert sorted(result[1] for result in results) == [False, True]
    assert len(launches) == 2


def test_failed_batch_rolls_back_all_generations(svc, monkeypatch):
    run = svc.scenario.create_run()["scenario_run_id"]
    launches = []
    monkeypatch.setattr(svc.coordinator, "_launch", lambda *args, **kwargs: launches.append(args))
    original = svc.coordinator.start_investigation

    def fail_second(run_id, case_id, mode, revision):
        if case_id == "case-secondary-a":
            raise RuntimeError("injected failure")
        return original(run_id, case_id, mode, revision)

    monkeypatch.setattr(svc.coordinator, "start_investigation", fail_second)
    service = BatchService(svc)
    request = {"assembly_id": svc.catalog.engine["engine_id"],
               "component_ids": ["component-primary", "component-secondary-a"], "mode": "seeded"}
    with pytest.raises(RuntimeError, match="injected failure"):
        service.create(run, request, "failure-key")
    assert launches == []
    assert svc.store.get_case(run, "case-primary")["active_generation_id"] is None
    assert svc.store.idem_get(f"batch:{run}", "failure-key") is None


def test_batch_http_retries_and_anonymous_isolation(public_api, monkeypatch):
    from fastapi.testclient import TestClient

    svc = public_api.SERVICES
    monkeypatch.setattr(svc.coordinator, "_launch", lambda *args, **kwargs: None)
    with TestClient(public_api.app) as owner, TestClient(public_api.app) as other:
        body = {"assembly_id": svc.catalog.engine["engine_id"],
                "component_ids": ["component-primary", "component-secondary-a"], "mode": "seeded"}
        assert owner.post("/api/v1/batches", json=body).status_code == 422
        first = owner.post("/api/v1/batches", json=body, headers={"Idempotency-Key": "request-1"})
        assert first.status_code == 202
        retry = owner.post("/api/v1/batches", json=body, headers={"Idempotency-Key": "request-1"})
        assert retry.status_code == 202 and retry.headers["Idempotent-Replay"] == "true"
        assert retry.json() == first.json()
        batch_url = f"/api/v1/batches/{first.json()['batch_id']}"
        assert owner.get(batch_url).status_code == 200
        assert other.get(batch_url).status_code == 404


def test_independent_batch_investigations_overlap_and_complete(svc, monkeypatch):
    run = svc.scenario.create_run()["scenario_run_id"]
    barrier = threading.Barrier(2, timeout=10)
    original = svc.coordinator.graph.invoke
    entered = []
    lock = threading.Lock()

    def coordinated_invoke(input_state, config):
        with lock:
            entered.append(input_state["case_id"])
        barrier.wait()
        return original(input_state, config)

    monkeypatch.setattr(svc.coordinator.graph, "invoke", coordinated_invoke)
    request = {"assembly_id": svc.catalog.engine["engine_id"],
               "component_ids": ["component-primary", "component-secondary-a"], "mode": "seeded"}
    batch, _ = BatchService(svc).create(run, request, "overlap-key")
    assert svc.coordinator.wait_idle(60)
    assert set(entered) == {"case-primary", "case-secondary-a"}
    for part in BatchService(svc).get(batch["batch_id"])["components"]:
        assert part["generation_status"] == "completed"
        assert part["tasks"]
        assert svc.store.get_case(run, part["case_id"])["current_decision_id"]


def test_public_batches_reject_missing_visitor_identity(svc, monkeypatch):
    run = svc.scenario.create_run()["scenario_run_id"]
    monkeypatch.setattr(svc.coordinator, "_launch", lambda *args, **kwargs: None)
    service = BatchService(svc)
    request = {"assembly_id": svc.catalog.engine["engine_id"],
               "component_ids": ["component-primary"], "mode": "seeded"}
    batch, _ = service.create(run, request, "private-key")
    previous_public_demo = settings.public_demo
    object.__setattr__(settings, "public_demo", True)
    try:
        with pytest.raises(DomainError) as create_error:
            service.create(run, request, "public-key")
        assert create_error.value.status == 404
        with pytest.raises(DomainError) as get_error:
            service.get(batch["batch_id"])
        assert get_error.value.status == 404
    finally:
        object.__setattr__(settings, "public_demo", previous_public_demo)


def test_batch_investigation_failure_does_not_stop_other_parts(svc, monkeypatch):
    run = svc.scenario.create_run()["scenario_run_id"]
    original = svc.coordinator.graph.invoke

    def fail_one(input_state, config):
        if input_state["case_id"] == "case-primary":
            raise RuntimeError("injected investigation failure")
        return original(input_state, config)

    monkeypatch.setattr(svc.coordinator.graph, "invoke", fail_one)
    request = {"assembly_id": svc.catalog.engine["engine_id"],
               "component_ids": ["component-primary", "component-secondary-a"], "mode": "seeded"}
    batch, _ = BatchService(svc).create(run, request, "independent-failure")
    assert svc.coordinator.wait_idle(60)
    parts = {part["component_id"]: part for part in BatchService(svc).get(batch["batch_id"])["components"]}
    assert parts["component-primary"]["generation_status"] == "failed"
    assert parts["component-secondary-a"]["generation_status"] == "completed"
    assert parts["component-secondary-a"]["tasks"]


def test_durable_batch_jobs_preserve_requested_mode_for_recovery(svc, monkeypatch):
    run = svc.scenario.create_run()["scenario_run_id"]
    previous_backend = settings.job_backend
    object.__setattr__(settings, "job_backend", "vercel")
    monkeypatch.setattr(svc.jobs, "dispatch", lambda job_id: None)
    try:
        request = {"assembly_id": svc.catalog.engine["engine_id"],
                   "component_ids": ["component-primary", "component-secondary-a"], "mode": "live"}
        batch, _ = BatchService(svc).create(run, request, "durable-live")
        for component in batch["components"]:
            job = svc.store.kv_get(f"job:{component['generation_id']}")
            assert job["payload"]["mode"] == "live"
    finally:
        object.__setattr__(settings, "job_backend", previous_backend)
