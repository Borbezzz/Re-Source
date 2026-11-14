"""Published case contracts match both sources of stale reasons."""

from wf_helpers import investigate

from recovery.domain.models import CaseView


def test_change_fanout_reason_matches_case_contract(svc, monkeypatch):
    run = svc.scenario.create_run()["scenario_run_id"]
    investigate(svc, "case-primary")
    monkeypatch.setattr(svc.coordinator, "request_reassessment", lambda *args, **kwargs: None)
    svc.changes.inject_signal(run, "SIG-RTM-CLOSURE")
    raw = svc.views.case("case-primary", run)
    assert raw["stale_reasons"]
    reason = CaseView.model_validate(raw).stale_reasons[0]
    assert reason.kind == "decision" and reason.summary and reason.change_id
    assert "OFF-PA" in reason.affected_candidate_ids


def test_resumed_monitoring_reason_matches_case_contract(svc, monkeypatch):
    run = svc.scenario.create_run()["scenario_run_id"]
    investigate(svc, "case-primary")
    case = svc.store.get_case(run, "case-primary")
    svc.monitoring.set_status(run, "case-primary", "paused", case["revision"])
    svc.changes.inject_signal(run, "SIG-RTM-CLOSURE")
    monkeypatch.setattr(svc.coordinator, "request_reassessment", lambda *args, **kwargs: None)
    case = svc.store.get_case(run, "case-primary")
    svc.monitoring.set_status(run, "case-primary", "active", case["revision"])
    reason = CaseView.model_validate(svc.views.case("case-primary", run)).stale_reasons[0]
    assert reason.kind == "decision" and reason.summary and reason.change_ids
