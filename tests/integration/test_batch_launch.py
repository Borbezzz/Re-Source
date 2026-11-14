"""Generation dispatch must follow the transaction that creates the work."""

import pytest


def test_investigation_is_dispatched_after_enclosing_commit(svc, monkeypatch):
    run_id = svc.scenario.create_run()["scenario_run_id"]
    launches = []
    monkeypatch.setattr(svc.coordinator, "_launch", lambda *args, **kwargs: launches.append((args, kwargs)))

    with svc.store.tx():
        result = svc.coordinator.start_investigation(run_id, "case-primary", "seeded", None)
        assert result["status"] == "accepted"
        assert launches == []

    assert len(launches) == 1
    assert launches[0][0][2] == result["generation_id"]
    assert svc.store.get_case(run_id, "case-primary")["active_generation_id"] == result["generation_id"]


def test_rolled_back_investigation_is_never_dispatched(svc, monkeypatch):
    run_id = svc.scenario.create_run()["scenario_run_id"]
    launches = []
    monkeypatch.setattr(svc.coordinator, "_launch", lambda *args, **kwargs: launches.append((args, kwargs)))

    with pytest.raises(RuntimeError, match="rollback"), svc.store.tx():
        svc.coordinator.start_investigation(run_id, "case-primary", "seeded", None)
        raise RuntimeError("rollback")

    assert launches == []
    assert svc.store.get_case(run_id, "case-primary")["active_generation_id"] is None
