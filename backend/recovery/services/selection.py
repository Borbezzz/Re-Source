"""Acceptance and version control (PRD FR-12): one operational transaction confirms current
eligibility, decision/evidence versions, expected case revision and the namespace barrier, then
persists the selection and an outbox work item for document generation."""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Any

from ..adapters import store as st
from ..domain.errors import DomainError, conflict, invalid, stale


def _now() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


class SelectionService:
    def __init__(self, services: Any):
        self.s = services

    def accept(self, run_id: str, case_id: str, req: dict, idem_key: str) -> dict:
        s = self.s
        with s.store.tx() as c:
            run = s.store.lock_run(c, run_id)
            case = s.store.lock_case(c, run_id, case_id)
            # idempotent replay of the same key returns the same selection
            for row in s.store.find(st.selections, run_id=run_id, case_id=case_id):
                if row["idem_key"] == idem_key:
                    sel = row["payload"]
                    if sel["candidate_id"] != req["candidate_id"] or sel["decision_id"] != req["decision_id"]:
                        raise conflict("IDEMPOTENCY_KEY_REUSED", "Idempotency key reused with a different payload", case_revision=case["revision"])
                    return {**sel, "status": row["status"], "replayed": True}
            if run["barrier_count"] > 0:
                raise stale("A change is being registered for this scenario run; retry when reassessment completes", case["revision"],
                            reason="pending_change_barrier")
            if case["current_decision_id"] != req["decision_id"]:
                raise stale("The decision you are accepting has been superseded", case["revision"], latest_decision_id=case["current_decision_id"])
            if case["revision"] != req["expected_revision"]:
                raise stale(f"Case moved to revision {case['revision']} (expected {req['expected_revision']})", case["revision"],
                            latest_decision_id=case["current_decision_id"])
            if case["state"] in ("reassessing", "investigating") or case["active_generation_id"]:
                raise stale("A reassessment is in progress; the current decision is stale", case["revision"], latest_decision_id=case["current_decision_id"])
            dec_row = s.store.get(st.decisions, req["decision_id"])
            decision = dec_row["payload"]
            if decision["evidence_hash"] != req["evidence_hash"]:
                raise stale("Evidence snapshot hash does not match the current decision", case["revision"], expected_hash=decision["evidence_hash"])
            cand = next((x for x in decision["candidates"] if x["candidate"]["candidate_id"] == req["candidate_id"]), None)
            if cand is None:
                raise invalid(f"Candidate {req['candidate_id']} is not part of decision {decision['label']}")
            if cand["eligibility"] != "eligible":
                raise DomainError(409, "CANDIDATE_NOT_ELIGIBLE", f"{cand['candidate']['label']} is {cand['eligibility']} — only eligible candidates can be accepted",
                                  case_revision=case["revision"], details={"eligibility": cand["eligibility"], "gaps": cand.get("gaps", [])})
            if case["current_selection_id"]:
                s.store.set_status(st.selections, case["current_selection_id"], "superseded")
            sel_id = f"sel-{uuid.uuid4().hex[:12]}"
            new_rev = case["revision"] + 1
            sel = {"selection_id": sel_id, "case_id": case_id, "scenario_run_id": run_id, "candidate_id": req["candidate_id"],
                   "decision_id": req["decision_id"], "decision_label": decision["label"], "accepted_case_revision": new_rev,
                   "evidence_hash": decision["evidence_hash"], "actor": req.get("actor", "demo-operator"), "accepted_at": _now(),
                   "idempotency_key": idem_key, "status": "current", "candidate_label": cand["candidate"]["label"],
                   "route": cand["candidate"]["route"]}
            s.store.put(st.selections, sel_id, run_id, sel, case_id=case_id, status="current", idem_key=idem_key)
            stale_reasons = [r for r in case["stale_reasons"] if r.get("kind") != "selection"]
            s.store.update_case(c, run_id, case_id, current_selection_id=sel_id, current_package_id=None, state="selected", revision=new_rev,
                                stale_reasons=stale_reasons, prior_stable_state=None)
            s.store.put(st.outbox, f"op-gen-docs-{sel_id}", run_id, {"op": "generate_documents", "run_id": run_id, "case_id": case_id,
                                                                     "selection_id": sel_id},
                        case_id=case_id, status="pending", op_type="generate_documents", attempts=0, available_at=_now())
            s.store.put(st.outbox, f"op-project-selection-{sel_id}", run_id, {"op": "project_selection", "record": sel},
                        case_id=case_id, status="pending", op_type="project_selection", attempts=0, available_at=_now())
            s.bus.publish(run_id, case_id, "selection.accepted", f"Accepted {cand['candidate']['label']} from {decision['label']}",
                          {"selection_id": sel_id, "candidate_id": req["candidate_id"], "decision_id": req["decision_id"],
                           "evidence_hash": decision["evidence_hash"]}, case_revision=new_rev)
            s.bus.publish(run_id, case_id, "case.state_changed", "Option accepted; preparing documents", {"state": "selected"}, case_revision=new_rev)
        s.worker_kick()
        return sel
