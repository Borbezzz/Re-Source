"""Contract test: real service payloads validate against the canonical Pydantic models that generate
contracts/openapi + contracts/generated-types (so the frontend's types cannot drift from reality)."""

from __future__ import annotations

from recovery.domain import models as M

from wf_helpers import accept, approve_and_submit, current, drain_outbox, investigate


def test_payloads_match_published_contracts(svc):
    run = svc.scenario.create_run()["scenario_run_id"]
    M.ScenarioRunView.model_validate(svc.scenario.view(run))
    M.EngineView.model_validate(svc.views.engine("engine-demo-001", run))
    d1 = investigate(svc, "case-primary")
    M.DecisionSnapshot.model_validate(d1)
    M.CaseView.model_validate(svc.views.case("case-primary", run))
    res = svc.changes.inject_signal(run, "SIG-RTM-CLOSURE")
    M.SignalInjectionResult.model_validate(res)
    svc.coordinator.wait_idle(60)
    _, d2 = current(svc, "case-primary")
    M.DecisionDiff.model_validate(svc.decisions.get_diff(run, "case-primary", d1["decision_id"], d2["decision_id"]))
    sel = accept(svc, "case-primary", "OFF-PB")
    M.Selection.model_validate(sel)
    drain_outbox(svc, "case-primary")
    M.DocumentsView.model_validate(svc.documents.view(run, "case-primary"))
    M.SimulatedReceipt.model_validate(approve_and_submit(svc, "case-primary"))
    M.VisualActionResult.model_validate(svc.scenario.visual_action(run, "case-primary", "install"))
    M.EvidenceView.model_validate(svc.views.evidence("ev-f1-pb", run))
    M.ClockState.model_validate(svc.changes.advance_clock(run, 1))
    for e in svc.store.events_after(run, "case-primary", 0, 5000):
        M.DomainEvent.model_validate(e)
        assert e["type"] in M.EVENT_TYPES
