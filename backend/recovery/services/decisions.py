"""Decision persistence (PRD §5.3.1 persist_decision) and decision diffs (FR-10 step 6).

`persist` is a compare-and-swap: the decision becomes current only if the case input revision, the
active execution generation and the namespace barrier all still match. Otherwise the result is kept
as superseded history and no current `decision.updated` event is emitted.
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Any, Optional

from ..adapters import store as st
from ..adapters.model_client import model_client
from ..runtime.tracing import current_trace_id


def _now() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def _short(label: str) -> str:
    return label.split(" — ")[0]


def compute_diff(prev: dict, new: dict, trigger: Optional[dict], catalog: Any) -> dict:
    prev_c = {c["candidate"]["candidate_id"]: c for c in prev["candidates"]}
    new_c = {c["candidate"]["candidate_id"]: c for c in new["candidates"]}
    moves, changes = [], []
    for cid in sorted(set(prev_c) | set(new_c)):
        a, b = prev_c.get(cid), new_c.get(cid)
        label = (b or a)["candidate"]["label"]
        ra, rb = (a or {}).get("rank"), (b or {}).get("rank")
        sa = (a or {}).get("score", {}) or {}
        sb = (b or {}).get("score", {}) or {}
        if ra != rb or sa.get("score") != sb.get("score"):
            moves.append({"candidate_id": cid, "label": label, "from_rank": ra, "to_rank": rb, "from_score": sa.get("score"), "to_score": sb.get("score")})
        if a and b:
            pa, pb = a.get("plan") or {}, b.get("plan") or {}
            for fld, get, unit in (
                ("elapsed_days", lambda p: p.get("elapsed_days"), "days"),
                ("landed_cost", lambda p: (p.get("landed_cost") or {}).get("amount"), "GBP"),
            ):
                if get(pa) != get(pb):
                    changes.append({"candidate_id": cid, "field": fld, "before": get(pa), "after": get(pb), "unit": unit})
            if (a.get("exposure") or {}).get("value") != (b.get("exposure") or {}).get("value"):
                changes.append({"candidate_id": cid, "field": "current_exposure", "before": a["exposure"]["value"], "after": b["exposure"]["value"], "unit": "ratio"})
            if a["eligibility"] != b["eligibility"]:
                changes.append({"candidate_id": cid, "field": "eligibility", "before": a["eligibility"], "after": b["eligibility"], "unit": None})
    prev_checks = {c["check_id"]: c for c in prev["checks"]}
    rerun, reused = [], []
    for c in new["checks"]:
        if c.get("reused_from_decision_id") or (c["check_id"] in prev_checks and prev_checks[c["check_id"]]["fingerprint"] == c["fingerprint"]):
            reused.append(c["check_id"])
        else:
            rerun.append(c["check_id"])
    return {
        "changed_fields": changes,
        "rank_moves": moves,
        "rerun_check_ids": rerun,
        "reused_check_ids": reused,
        "preferred_before": prev.get("preferred_candidate_id"),
        "preferred_after": new.get("preferred_candidate_id"),
        "impact_paths": (trigger or {}).get("impact_paths", []),
    }


class DecisionService:
    def __init__(self, services: Any):
        self.s = services

    def list(self, run_id: str, case_id: str) -> list[dict]:
        rows = self.s.store.find(st.decisions, run_id=run_id, case_id=case_id)
        return [r["payload"] for r in rows]

    def get(self, decision_id: str) -> Optional[dict]:
        row = self.s.store.get(st.decisions, decision_id)
        return row["payload"] if row else None

    def get_diff(self, run_id: str, case_id: str, from_id: str, to_id: str) -> Optional[dict]:
        for row in self.s.store.find(st.diffs, run_id=run_id, case_id=case_id):
            if row["from_id"] == from_id and row["to_id"] == to_id:
                return row["payload"]
        prev, new = self.get(from_id), self.get(to_id)
        if not prev or not new:
            return None
        d = compute_diff(prev, new, None, self.s.catalog)
        return self._diff_record(case_id, prev, new, d, None, explanation=self._deterministic_explanation(prev, new, d, None))

    # ------------------------------------------------------------------
    def _deterministic_explanation(self, prev: dict, new: dict, d: dict, trigger: Optional[dict]) -> str:
        names = {c["candidate"]["candidate_id"]: _short(c["candidate"]["label"]) for c in new["candidates"]}
        parts = []
        if trigger:
            parts.append(f"Trigger: {trigger.get('title') or trigger.get('trigger_id')}.")
        if d["preferred_before"] != d["preferred_after"]:
            parts.append(f"Preferred option changed from {names.get(d['preferred_before'], 'none')} to {names.get(d['preferred_after'], 'none')}.")
        else:
            parts.append(f"Preferred option unchanged ({names.get(d['preferred_after'], 'none')}).")
        for ch in d["changed_fields"]:
            if ch["field"] == "elapsed_days":
                parts.append(f"{names.get(ch['candidate_id'])} readiness moves from day {ch['before']:g} to day {ch['after']:g}.")
            elif ch["field"] == "landed_cost":
                parts.append(f"{names.get(ch['candidate_id'])} landed cost £{float(ch['before']):,.0f} → £{float(ch['after']):,.0f}.")
            elif ch["field"] == "eligibility":
                parts.append(f"{names.get(ch['candidate_id'])} eligibility {ch['before']} → {ch['after']}.")
        parts.append(f"{len(d['rerun_check_ids'])} check(s) rerun, {len(d['reused_check_ids'])} reused unchanged.")
        rel = [c for c in new["candidates"] if c.get("reliability")]
        if rel and d["changed_fields"]:
            parts.append("Historical supplier reliability figures are unchanged; the change is to schedule, cost and exposure.")
        return " ".join(parts)

    def _diff_record(self, case_id: str, prev: dict, new: dict, d: dict, trigger: Optional[dict], explanation: str) -> dict:
        return {
            "diff_id": f"diff-{prev['decision_id']}-{new['decision_id']}",
            "case_id": case_id,
            "from_decision_id": prev["decision_id"],
            "to_decision_id": new["decision_id"],
            "trigger_id": new.get("trigger_id"),
            "trigger": trigger,
            "impact_paths": d["impact_paths"],
            "changed_fields": d["changed_fields"],
            "rank_moves": d["rank_moves"],
            "rerun_check_ids": d["rerun_check_ids"],
            "reused_check_ids": d["reused_check_ids"],
            "preferred_before": d["preferred_before"],
            "preferred_after": d["preferred_after"],
            "downstream_invalidations": new.get("downstream_invalidations", []),
            "explanation": explanation,
            "user_action_needed": ("Review the changed recommendation and accept an eligible option from the current decision."
                                   if d["preferred_before"] != d["preferred_after"] or new.get("downstream_invalidations") else None),
        }

    def persist(self, state: dict, tool_usage: dict) -> dict:
        s = self.s
        run_id, case_id = state["run_id"], state["case_id"]
        decision_id = f"dec-{uuid.uuid4().hex[:12]}"
        ranked = state["ranked"]
        preferred = next((r for r in ranked if r.get("rank") == 1), None)
        evidence_set_id, evidence_hash = s.run_state.evidence_set_hash(state["docs"])
        used_versions = sorted({d["version_id"] for ds in state["docs"].values() for d in ds})
        trigger = state.get("trigger")
        requirements_version = s.catalog.requirements_version
        # Use the checkpointed requirements that this decision evaluated.
        overlay = next((req["overlay"] for req in state.get("requirements", []) if req.get("overlay")), None)
        if overlay:
            requirements_version += f"+{overlay['draft_id']}.v{overlay['draft_version']}"
        decision = {
            "decision_id": decision_id,
            "label": "pending",
            "case_id": case_id,
            "scenario_run_id": run_id,
            "case_revision": 0,
            "input_revision": state["input_revision"],
            "generation_id": state["generation_id"],
            "candidates": ranked,
            "checks": sorted(state["checks"].values(), key=lambda c: (c["candidate_id"], c["requirement_id"])),
            "evidence_set_id": evidence_set_id,
            "evidence_hash": evidence_hash,
            "requirements_version": requirements_version,
            "ranking_config_version": s.catalog.ranking["ranking_config_version"],
            "relationship_versions": {"catalog": 1, "run_extra": len(s.store.kv_get(f"rels:{run_id}") or [])},
            "signal_versions": {sig["source_event_id"]: sig["version"] for sig in state["signals"]},
            "active_signals": state["signals"],
            "preferred_candidate_id": preferred["candidate"]["candidate_id"] if preferred else None,
            "trigger_id": state.get("trigger_id"),
            "summary": "",
            "status": "current",
            "created_at": _now(),
            "mode": state["mode"],
            "trace_id": current_trace_id(),
            "tool_usage": tool_usage,
            "facts": {vid: f for vid, f in state["facts"].items() if vid in used_versions},
            "candidate_evidence": {cid: [d["version_id"] for d in ds] for cid, ds in state["docs"].items()},
            "public_leads": state.get("public_leads", {}),
            "gaps": list(state.get("gaps", {}).values()),
            "extraction_modes": state.get("extraction_modes", {}),
            "scenario_now": state["now"],
            "downstream_invalidations": [],
        }
        prev = state.get("prev_decision")
        diff = compute_diff(prev, decision, trigger, s.catalog) if prev else None
        # Model explains (outside the transaction); code already computed everything.
        if preferred:
            fb = (f"Recommend {preferred['candidate']['label']}: ready by day {preferred['plan']['finish_day']:g}, "
                  f"£{float(preferred['plan']['landed_cost']['amount']):,.0f} landed, score {preferred['score']['score']:.2f}. "
                  f"{sum(1 for r in ranked if r['eligibility'] == 'eligible')} eligible of {len(ranked)} options.")
        else:
            fb = f"No eligible option yet; {sum(1 for r in ranked if r['eligibility'] == 'pending')} pending evidence."
        decision["summary"], decision["summary_origin"] = model_client.summarise("decision", {
            "preferred": preferred and {"label": preferred["candidate"]["label"], "day": preferred["plan"]["finish_day"],
                                        "landed_gbp": preferred["plan"]["landed_cost"]["amount"], "score": preferred["score"]["score"]},
            "ranked": [{"label": r["candidate"]["label"], "rank": r["rank"], "eligibility": r["eligibility"], "summary": r["summary"]} for r in ranked],
        }, fb, max_words=60)
        explanation = None
        if diff:
            det = self._deterministic_explanation(prev, decision, diff, trigger)
            explanation, _ = model_client.summarise("diff", {"trigger": trigger and {k: trigger.get(k) for k in ("title", "trigger_type")},
                                                             "changes": diff["changed_fields"], "rank_moves": diff["rank_moves"],
                                                             "rerun": len(diff["rerun_check_ids"]), "reused": len(diff["reused_check_ids"]),
                                                             "deterministic_explanation": det}, det, max_words=70)

        with s.store.tx() as c:
            run = s.store.lock_run(c, run_id)
            case = s.store.lock_case(c, run_id, case_id)
            ok = (case["active_generation_id"] == state["generation_id"] and case["input_revision"] == state["input_revision"]
                  and run["barrier_count"] == 0)
            if not ok:
                decision["status"] = "superseded"
                decision["label"] = "superseded"
                reason = ("newer input revision pending" if case["input_revision"] != state["input_revision"]
                          else "pending-change barrier active" if run["barrier_count"] else "not the active execution generation")
                decision["superseded_reason"] = reason
                s.store.put(st.decisions, decision_id, run_id, decision, case_id=case_id, status="superseded",
                            label="superseded", generation_id=state["generation_id"], input_revision=state["input_revision"])
                return {"decision_id": decision_id, "status": "superseded", "summary": f"Result kept as history (superseded: {reason})"}
            labels = dict(case["decision_labels"])
            n = sum(1 for v in labels.values() if v.startswith("D")) + 1
            decision["label"] = f"D{n}"
            labels[decision_id] = decision["label"]
            new_rev = case["revision"] + 1
            decision["case_revision"] = new_rev
            selection_stale = False
            if case["current_selection_id"]:
                sel = s.store.get(st.selections, case["current_selection_id"])
                selection_stale = bool(sel and sel["status"] == "stale")
                if selection_stale:
                    decision["downstream_invalidations"].append(f"selection {case['current_selection_id']} is stale — reconfirm from {decision['label']}")
            if selection_stale:
                new_state = "selection_stale"
            elif case["current_selection_id"] and case["prior_stable_state"] and case["state"] == "reassessing":
                new_state = case["prior_stable_state"]
            elif not preferred and any(r["eligibility"] == "pending" for r in ranked):
                new_state = "waiting_for_evidence"  # no ready-to-select option yet; pending gaps are listed per candidate
            else:
                new_state = "recommendations_ready"
            if prev:
                s.store.set_status(st.decisions, prev["decision_id"], "superseded")
            s.store.put(st.decisions, decision_id, run_id, decision, case_id=case_id, status="current", label=decision["label"],
                        generation_id=state["generation_id"], input_revision=state["input_revision"])
            stale = [r for r in case["stale_reasons"] if r.get("kind") not in ("decision",)]
            s.store.update_case(c, run_id, case_id, current_decision_id=decision_id,
                                initial_decision_id=case["initial_decision_id"] or decision_id, state=new_state,
                                prior_stable_state=None, revision=new_rev, decision_labels=labels, stale_reasons=stale,
                                active_generation_id=None)
            diff_rec = None
            if diff:
                diff_rec = self._diff_record(case_id, prev, decision, diff, trigger, explanation or "")
                s.store.put(st.diffs, diff_rec["diff_id"], run_id, diff_rec, case_id=case_id, from_id=prev["decision_id"], to_id=decision_id)
            s.store.put(st.outbox, f"op-project-decision-{decision_id}", run_id,
                        {"op": "project_decision", "record": {k: v for k, v in decision.items() if k != "facts"}, "source_revision": new_rev},
                        case_id=case_id, status="pending", op_type="project_decision", attempts=0, available_at=_now())
            evt = "decision.updated" if prev else "decision.created"
            summary = (f"{decision['label']}: " + (explanation if diff else decision["summary"]))[:400]
            s.bus.publish(run_id, case_id, evt, summary, {
                "decision_id": decision_id, "label": decision["label"], "previous_decision_id": prev and prev["decision_id"],
                "preferred_candidate_id": decision["preferred_candidate_id"], "trigger_id": decision["trigger_id"],
                "diff_id": diff_rec and diff_rec["diff_id"], "evidence_hash": evidence_hash}, case_revision=new_rev)
            s.bus.publish(run_id, case_id, "case.state_changed", f"Case is now {new_state.replace('_', ' ')}", {"state": new_state}, case_revision=new_rev)
            s.monitoring.reconcile_subscription(c, run_id, case_id, decision)
        return {"decision_id": decision_id, "status": "current", "summary": f"{decision['label']} persisted as current decision"}
