"""Service-level acceptance checks (PRD §12) on the seeded scenario with deterministic extraction."""

from __future__ import annotations

import threading
import time

import pytest

from recovery.adapters import store as st
from recovery.domain.errors import DomainError

from wf_helpers import accept, approve_and_submit, current, drain_outbox, investigate, ranked


@pytest.fixture()
def run(svc):
    return svc.scenario.create_run()["scenario_run_id"]


def test_ac02_ac03_primary_d1_to_d2_with_selective_rerun(svc, run):
    d1 = investigate(svc, "case-primary")
    assert d1["label"] == "D1"
    assert ranked(d1) == ["OFF-PA", "OFF-PB", "OFF-PC"]
    assert sum(1 for c in d1["candidates"] if c["eligibility"] == "eligible") >= 2
    assert all(c["evidence_refs"] for c in d1["checks"] if c["result"] == "pass" and c["category"] != "logistics")
    res = svc.changes.inject_signal(run, "SIG-RTM-CLOSURE")
    assert res["affected_case_ids"] == ["case-primary"]
    svc.coordinator.wait_idle(60)
    case, d2 = current(svc, "case-primary")
    assert d2["label"] == "D2" and ranked(d2) == ["OFF-PB", "OFF-PA", "OFF-PC"]
    a = next(c for c in d2["candidates"] if c["candidate"]["candidate_id"] == "OFF-PA")
    assert a["plan"]["finish_day"] == 11.0 and a["plan"]["landed_cost"]["amount"] == "50500.00"
    diff = svc.decisions.get_diff(run, "case-primary", d1["decision_id"], d2["decision_id"])
    assert diff["preferred_before"] == "OFF-PA" and diff["preferred_after"] == "OFF-PB"
    assert len(diff["rerun_check_ids"]) == 1 and len(diff["reused_check_ids"]) > 30
    assert [n["id"] for n in diff["impact_paths"][0]] == ["GEO-PORT-NLRTM", "R-RTM-HWC", "OFF-PA", "case-primary"]
    # reliability unchanged: the risk is a changed plan
    assert a["reliability"][0]["value"] == next(c for c in d1["candidates"] if c["candidate"]["candidate_id"] == "OFF-PA")["reliability"][0]["value"]
    # other cases untouched
    assert svc.store.get_case(run, "case-secondary-a")["input_revision"] == 1


def test_ac04_unrelated_duplicate_correction_retraction(svc, run):
    investigate(svc, "case-primary")
    rev0 = svc.store.get_case(run, "case-primary")["input_revision"]
    assert svc.changes.inject_signal(run, "SIG-KHH-TYPHOON")["affected_case_ids"] == []
    assert svc.store.get_case(run, "case-primary")["input_revision"] == rev0
    svc.changes.inject_signal(run, "SIG-RTM-CLOSURE")
    dup = svc.changes.inject_signal(run, "SIG-RTM-CLOSURE")
    assert dup["duplicate"] is True
    svc.coordinator.wait_idle(60)
    assert svc.store.get_case(run, "case-primary")["input_revision"] == rev0 + 1  # duplicate did no work
    svc.changes.inject_signal(run, "SIG-RTM-CLOSURE-CORRECTION")
    svc.coordinator.wait_idle(60)
    _, d3 = current(svc, "case-primary")
    a = next(c for c in d3["candidates"] if c["candidate"]["candidate_id"] == "OFF-PA")
    assert a["plan"]["finish_day"] == 7.0 and ranked(d3)[0] == "OFF-PB"
    svc.changes.inject_signal(run, "SIG-RTM-CLOSURE-RETRACTION")
    svc.coordinator.wait_idle(60)
    _, d4 = current(svc, "case-primary")
    assert ranked(d4) == ["OFF-PA", "OFF-PB", "OFF-PC"]  # retraction restores earlier conditions
    assert d4["label"] == "D4"


def test_ac05_evidence_change_invalidates_checks_and_documents(svc, run):
    investigate(svc, "case-primary")
    accept(svc, "case-primary", "OFF-PA", "sel-a")
    drain_outbox(svc, "case-primary")
    res = svc.changes.inject_evidence_change(run, "EVC-SB-0042-REVB")
    assert set(res["change"]["affected_entity_ids"]) >= {"OFF-PA", "OFF-PB", "OFF-PC"}
    case = svc.store.get_case(run, "case-primary")
    sel = svc.store.get(st.selections, case["current_selection_id"])
    assert sel["status"] == "stale"
    pkg = svc.store.get(st.packages, case["current_package_id"])
    assert pkg["status"] == "stale"
    svc.coordinator.wait_idle(60)
    case, d2 = current(svc, "case-primary")
    c = next(x for x in d2["candidates"] if x["candidate"]["candidate_id"] == "OFF-PC")
    assert c["eligibility"] == "ineligible"
    assert any("ev-sb-fn-0042-b" in chk["evidence_refs"] for chk in d2["checks"])
    assert case["state"] == "selection_stale"
    accept(svc, "case-primary", "OFF-PA", "sel-a2")
    case = drain_outbox(svc, "case-primary")
    view = svc.documents.view(run, "case-primary")
    assert view["current_package"]["status"] == "current" and view["current_package"]["decision_id"] == d2["decision_id"]


def test_ac08_gap_resolved_by_followup_and_budget_respected(svc, run):
    d = investigate(svc, "case-secondary-a")
    gaps = {(g["candidate_id"], g["requirement_id"]): g for g in d["gaps"]}
    assert gaps[("OFF-SA1", "REQ-NGV-TRC-01")]["status"] == "resolved"
    sa1 = next(c for c in d["candidates"] if c["candidate"]["candidate_id"] == "OFF-SA1")
    assert sa1["eligibility"] == "eligible" and sa1["rank"] == 1
    trc = next(c for c in d["checks"] if c["candidate_id"] == "OFF-SA1" and c["requirement_id"] == "REQ-NGV-TRC-01")
    assert "ev-tr-sa1" in trc["evidence_refs"]
    sa3_attempts = sum(len(g["attempts"]) for g in d["gaps"] if g["candidate_id"] == "OFF-SA3")
    assert sa3_attempts <= 2
    assert any(g["status"] == "exhausted" for g in d["gaps"] if g["candidate_id"] == "OFF-SA3")


def test_ac09_stale_and_concurrent_acceptance(svc, run):
    d1 = investigate(svc, "case-primary")
    svc.changes.inject_signal(run, "SIG-RTM-CLOSURE")
    svc.coordinator.wait_idle(60)
    case, d2 = current(svc, "case-primary")
    with pytest.raises(DomainError) as e:
        svc.selection.accept(run, "case-primary", {"candidate_id": "OFF-PA", "decision_id": d1["decision_id"], "evidence_hash": d1["evidence_hash"],
                                                   "expected_revision": case["revision"]}, "old")
    assert e.value.status == 409 and e.value.code == "STALE_DECISION"
    with pytest.raises(DomainError) as e:
        svc.selection.accept(run, "case-primary", {"candidate_id": "OFF-PB", "decision_id": d2["decision_id"], "evidence_hash": "sha256:wrong",
                                                   "expected_revision": case["revision"]}, "bad-hash")
    assert e.value.code == "STALE_DECISION"
    results, errors = [], []

    def attempt(cid, key):
        try:
            results.append(svc.selection.accept(run, "case-primary", {"candidate_id": cid, "decision_id": d2["decision_id"],
                                                                      "evidence_hash": d2["evidence_hash"], "expected_revision": case["revision"]}, key))
        except DomainError as exc:
            errors.append(exc)

    ts = [threading.Thread(target=attempt, args=(cid, f"race-{i}")) for i, cid in enumerate(["OFF-PB", "OFF-PA", "OFF-PB"])]
    [t.start() for t in ts]
    [t.join() for t in ts]
    assert len(results) == 1 and len(errors) == 2 and all(x.status == 409 for x in errors)
    current_sels = [r for r in svc.store.find(st.selections, run_id=run, case_id="case-primary") if r["status"] == "current"]
    assert len(current_sels) == 1 and current_sels[0]["payload"]["evidence_hash"] == d2["evidence_hash"]
    # same key replays the same selection
    again = svc.selection.accept(run, "case-primary", {"candidate_id": results[0]["candidate_id"], "decision_id": d2["decision_id"],
                                                       "evidence_hash": d2["evidence_hash"], "expected_revision": case["revision"]},
                                 results[0]["idempotency_key"])
    assert again["selection_id"] == results[0]["selection_id"]


def test_ac10_ac11_documents_and_single_receipt(svc, run):
    investigate(svc, "case-primary")
    accept(svc, "case-primary", "OFF-PB")
    drain_outbox(svc, "case-primary")
    view = svc.documents.view(run, "case-primary")
    assert [d["template_id"] for d in view["current_drafts"]] == ["TPL-CAA-FORM1-MO", "TPL-COMPONENT-ACCEPTANCE", "TPL-SUPPLIER-APPROVAL"]
    form1 = view["current_drafts"][0]
    pn = next(f for f in form1["fields"] if f["field_id"] == "b8")
    assert pn["value"] == "RS-FN-1001" and pn["provenance"]["source_fact_ids"]
    r1 = approve_and_submit(svc, "case-primary")
    case = svc.store.get_case(run, "case-primary")
    r2 = svc.documents.submit(run, "case-primary", {"selection_id": case["current_selection_id"], "package_id": r1["package_id"],
                                                    "package_version": r1["package_version"]})
    assert r1["receipt_id"] == r2["receipt_id"]
    assert len(svc.store.find(st.receipts, run_id=run, case_id="case-primary")) == 1
    assert case["state"] == "submission_simulated"


def test_ac11_stale_package_cannot_be_submitted(svc, run):
    investigate(svc, "case-primary")
    accept(svc, "case-primary", "OFF-PB")
    drain_outbox(svc, "case-primary")
    view = svc.documents.view(run, "case-primary")
    pkg = svc.documents.patch(run, view["current_package"]["package_id"], {"expected_version": view["current_package"]["version"],
                                                                         "review_action": "approve"})["package"]
    svc.changes.inject_evidence_change(run, "EVC-SB-0042-REVB")
    case = svc.store.get_case(run, "case-primary")
    with pytest.raises(DomainError) as e:
        svc.documents.submit(run, "case-primary", {"selection_id": case["current_selection_id"], "package_id": pkg["package_id"],
                                                   "package_version": pkg["version"]})
    assert e.value.status == 409
    svc.coordinator.wait_idle(60)


def test_ac13_secondary_cases_complete_full_workflow(svc, run):
    for case_id, winner in (("case-secondary-a", "OFF-SA1"), ("case-secondary-b", "OFF-SB3")):
        d = investigate(svc, case_id)
        assert ranked(d)[0] == winner
        accept(svc, case_id, winner, f"sel-{case_id}")
        drain_outbox(svc, case_id)
        receipt = approve_and_submit(svc, case_id)
        assert receipt["destination_type"] == "internal_quality_records"
        v = svc.scenario.visual_action(run, case_id, "install")
        assert v["case_state"] == "installation_visualized"
    sb = current(svc, "case-secondary-b")[1]
    sb2 = next(c for c in sb["candidates"] if c["candidate"]["candidate_id"] == "OFF-SB2")
    assert sb2["eligibility"] == "pending" and sb2["feasible"] is True
    docs_b = svc.documents.view(run, "case-secondary-b")
    assert "TPL-CAA-FORM1-21" in [d["template_id"] for d in docs_b["current_drafts"]]


def test_ac12_interrupted_worker_resumes_from_checkpoint_without_duplicates(svc, run, tmp_path, monkeypatch):
    from recovery.agents import investigation as inv
    from recovery.services.container import Services

    gate = threading.Event()
    original = inv.rank

    def blocking(rows):
        if not gate.is_set():
            gate.wait(30)
            raise RuntimeError("worker killed (simulated)")
        return original(rows)

    monkeypatch.setattr(inv, "rank", blocking)  # module-level name used inside schedule_and_rank at call time
    svc.coordinator.start_investigation(run, "case-primary", "seeded", None)
    time.sleep(1.5)  # graph reaches the blocking node; earlier supersteps are checkpointed
    gen = svc.store.get_case(run, "case-primary")["active_generation_id"]
    assert gen
    gate.set()
    monkeypatch.setattr(inv, "rank", original)
    # "restart": a new process (container) on the same store + checkpoint file
    s2 = Services(db_url=svc.store.url, start_worker=False)
    # the old worker thread dies; mark it as interrupted rather than failed for the restart path
    svc.coordinator.wait_idle(10)
    with s2.store.tx() as c:
        s2.store.update_case(c, run, "case-primary", active_generation_id=gen, state="investigating")
    s2.store.set_status(st.generations, gen, "running")
    resumed = s2.coordinator.recover_interrupted()
    assert gen in resumed
    assert s2.coordinator.wait_idle(60)
    case = s2.store.get_case(run, "case-primary")
    assert case["current_decision_id"]
    current_decisions = [r for r in s2.store.find(st.decisions, run_id=run, case_id="case-primary") if r["status"] == "current"]
    assert len(current_decisions) == 1
    types = [e["type"] for e in s2.store.events_after(run, "case-primary", 0, 5000)]
    assert "run.interrupted" in types and "run.recovered" in types
    seqs = [e["sequence"] for e in s2.store.events_after(run, "case-primary", 0, 5000)]
    assert seqs == sorted(seqs) and len(seqs) == len(set(seqs))
    s2.stop()


def test_ac18_reset_creates_isolated_runs_with_same_outcome(svc, run):
    d_a = investigate(svc, "case-primary", run)
    run2 = svc.scenario.create_run()["scenario_run_id"]
    assert run2 != run
    d_b = investigate(svc, "case-primary", run2)
    assert ranked(d_a) == ranked(d_b)
    assert svc.store.get_case(run, "case-primary")["current_decision_id"] == d_a["decision_id"]  # history retained
    assert svc.monitoring.get(run, "case-primary")["status"] == "paused"
    res = svc.changes.inject_signal(run2, "SIG-RTM-CLOSURE")
    svc.coordinator.wait_idle(60)
    assert svc.store.get_case(run, "case-primary")["current_decision_id"] == d_a["decision_id"]  # old namespace untouched
    assert res["affected_case_ids"] == ["case-primary"]


def test_ac19_newest_generation_wins_when_changes_overlap(svc, run, monkeypatch):
    investigate(svc, "case-primary")
    from recovery.config import settings

    object.__setattr__(settings, "pacing_ms", 120)  # make the reassessment slow enough to overlap
    svc.changes.inject_signal(run, "SIG-RTM-CLOSURE")
    time.sleep(0.3)
    svc.changes.inject_signal(run, "SIG-RTM-CLOSURE-CORRECTION")
    assert svc.coordinator.wait_idle(120)
    object.__setattr__(settings, "pacing_ms", 0)
    case, d = current(svc, "case-primary")
    a = next(c for c in d["candidates"] if c["candidate"]["candidate_id"] == "OFF-PA")
    assert a["plan"]["finish_day"] == 7.0  # newest change (correction) is what is current
    assert d["input_revision"] == case["input_revision"]
    updated = [e for e in svc.store.events_after(run, "case-primary", 0, 5000) if e["type"] == "decision.updated"]
    labels = [e["data"]["decision_id"] for e in updated]
    superseded = [r["id"] for r in svc.store.find(st.decisions, run_id=run, case_id="case-primary") if r["label"] == "superseded"]
    assert not set(superseded) & set(labels)  # superseded results never emitted as current


def test_ac20_barrier_blocks_commits_until_fanout_completes(svc, run):
    investigate(svc, "case-secondary-a")
    investigate(svc, "case-secondary-b")
    sig = dict(svc.catalog.signals["SIG-HAM-STRIKE"])
    sig.pop("fixture_id")
    sig.update(signal_id="sig-ham-now-v1", source_event_id="PORT-DEHAM-NOW", effective_from="2026-11-16T08:00:00Z")
    svc.changes.fail_fanout_after = 1
    with pytest.raises(RuntimeError):
        svc.changes.inject_signal(run, signal=sig)
    assert svc.store.get_run(run)["barrier_count"] == 1
    case_b, d_b = current(svc, "case-secondary-b")
    with pytest.raises(DomainError) as e:
        svc.selection.accept(run, "case-secondary-b", {"candidate_id": "OFF-SB3", "decision_id": d_b["decision_id"], "evidence_hash": d_b["evidence_hash"],
                                                       "expected_revision": case_b["revision"]}, "blocked")
    assert e.value.status == 409
    rev_a_before = svc.store.get_case(run, "case-secondary-a")["input_revision"]
    svc.changes.fail_fanout_after = None
    change_id = svc.store.find(st.change_events, run_id=run)[-1]["id"]
    res = svc.changes.retry_fanout(run, change_id)
    assert sorted(res["affected_case_ids"]) == ["case-secondary-a", "case-secondary-b"] or res["affected_case_ids"] == ["case-secondary-b"]
    assert svc.store.get_case(run, "case-secondary-a")["input_revision"] == rev_a_before  # retry deduplicated per case key
    assert svc.store.get_run(run)["barrier_count"] == 0
    svc.coordinator.wait_idle(60)


def test_ac21_active_change_before_open_clock_expiry_and_pause(svc, run):
    svc.changes.inject_signal(run, "SIG-RTM-CLOSURE")  # disruption active before the case is opened
    d1 = investigate(svc, "case-primary")
    assert ranked(d1)[0] == "OFF-PB"  # initial snapshot includes the active change
    investigate(svc, "case-secondary-a")
    svc.changes.advance_clock(run, 24 * 6)  # Meridane AS9120 certificate expires on day 5
    svc.coordinator.wait_idle(60)
    _, da = current(svc, "case-secondary-a")
    sa2 = next(c for c in da["candidates"] if c["candidate"]["candidate_id"] == "OFF-SA2")
    assert sa2["eligibility"] == "ineligible"
    case = svc.store.get_case(run, "case-primary")
    svc.monitoring.set_status(run, "case-primary", "paused", case["revision"])
    svc.changes.inject_signal(run, "SIG-RTM-CLOSURE-RETRACTION")
    assert svc.monitoring.get(run, "case-primary")["pending_change_ids"]
    case = svc.store.get_case(run, "case-primary")
    svc.monitoring.set_status(run, "case-primary", "active", case["revision"])
    svc.coordinator.wait_idle(60)
    _, d = current(svc, "case-primary")
    assert ranked(d)[0] == "OFF-PA"  # resumed case reconciled the retraction


def test_replay_mode_is_labelled_and_keeps_source_history(svc, run):
    d = investigate(svc, "case-primary")
    rep = svc.scenario.create_run(mode="replay", replay_source_run_id=run)["scenario_run_id"]
    for _ in range(200):
        case = svc.store.get_case(rep, "case-primary")
        if case["current_decision_id"]:
            break
        time.sleep(0.1)
    assert case["mode"] == "replay" and case["current_decision_id"].startswith(d["decision_id"])
    evs = svc.store.events_after(rep, "case-primary", 0, 5000)
    replayed = [e for e in evs if e["data"].get("replay")]
    assert replayed and all(e["summary"].startswith("Replay:") for e in replayed)
    assert svc.store.get_case(run, "case-primary")["current_decision_id"] == d["decision_id"]


def test_signal_sources_report_health_and_freshness(svc, run):
    from recovery.services.signal_sources import SignalSources

    rows = {r["source_id"]: r for r in SignalSources(svc).status(run)}
    assert rows["scenario-port-feed"]["health"] == "ok"
    assert rows["linkup-news"]["kind"] == "live" and rows["linkup-news"]["freshness_slo_minutes"] == 60
