"""Case monitoring lifecycle (PRD FR-10): run-scoped CaseSubscriptions, reconciliation after each
published decision, pause/close/resume with reconciliation of changes received while paused."""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Any, Optional

from ..adapters import store as st
from ..domain.errors import conflict, invalid


def _now() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


class MonitoringService:
    def __init__(self, services: Any):
        self.s = services

    def _deps_for_offers(self, offers: list[dict]) -> list[str]:
        cat = self.s.catalog
        deps: set[str] = set()
        for o in offers:
            route = cat.routes[o["logistics_route_id"]]
            site = cat.sites[o["site_id"]]
            deps |= {o["candidate_id"], o["site_id"], o["supplier_id"], o["logistics_route_id"], o["part_id"], site["geography"]["geo_id"],
                     f"GEO-COUNTRY-{site['geography']['country']}", *route.get("passes_through", [])}
            for vid in o["evidence_ids"]:
                ev = cat.evidence.get(vid)
                if ev:
                    deps.add(ev["document_id"])
        return sorted(deps)

    def subscription_id(self, run_id: str, case_id: str) -> str:
        return f"sub-{run_id[:8]}-{case_id}"

    def create_subscription(self, run_id: str, case_id: str) -> dict:
        offers = self.s.catalog.offers_for_case(case_id)
        comp = self.s.catalog.component_for_case(case_id)
        sub = {"subscription_id": self.subscription_id(run_id, case_id), "scenario_run_id": run_id, "case_id": case_id,
               "dependency_ids": sorted(set(self._deps_for_offers(offers)) | {comp["component_id"], comp["part_identity"]}),
               "dependency_revision": 1, "status": "active", "owner": "demo-operator", "reconciled_change_cursor": 0,
               "pending_change_ids": [], "updated_at": _now()}
        self.s.store.put(st.subscriptions, sub["subscription_id"], run_id, sub, case_id=case_id, status="active", dependency_revision=1)
        return sub

    def get(self, run_id: str, case_id: str) -> Optional[dict]:
        row = self.s.store.get(st.subscriptions, self.subscription_id(run_id, case_id))
        return row["payload"] if row else None

    def reconcile_subscription(self, c: Any, run_id: str, case_id: str, decision: dict) -> None:
        """Union of previous and new dependencies after every published decision / reselection."""
        sub = self.get(run_id, case_id)
        if not sub:
            return
        offers = [cand["candidate"] for cand in decision.get("candidates", [])]
        new_deps = set(self._deps_for_offers(offers))
        sub["dependency_ids"] = sorted(set(sub["dependency_ids"]) | new_deps)
        sub["dependency_revision"] += 1
        sub["updated_at"] = _now()
        self.s.store.put(st.subscriptions, sub["subscription_id"], run_id, sub, case_id=case_id, status=sub["status"],
                         dependency_revision=sub["dependency_revision"])

    def pause_run(self, run_id: str) -> None:
        for row in self.s.store.find(st.subscriptions, run_id=run_id):
            sub = row["payload"]
            if sub["status"] == "active":
                sub["status"] = "paused"
                sub["paused_reason"] = "run reset — history preserved read-only"
                sub["updated_at"] = _now()
                self.s.store.put(st.subscriptions, sub["subscription_id"], run_id, sub, case_id=sub["case_id"], status="paused",
                                 dependency_revision=sub["dependency_revision"])

    def queue_while_paused(self, run_id: str, case_id: str, change_id: str, affected_offers: list[str]) -> None:
        sub = self.get(run_id, case_id)
        if not sub:
            return
        sub.setdefault("pending_change_ids", []).append(change_id)
        sub.setdefault("pending_affected", [])
        sub["pending_affected"] = sorted(set(sub["pending_affected"]) | set(affected_offers))
        self.s.store.put(st.subscriptions, sub["subscription_id"], run_id, sub, case_id=case_id, status=sub["status"],
                         dependency_revision=sub["dependency_revision"])

    def set_status(self, run_id: str, case_id: str, status: str, expected_revision: int) -> dict:
        s = self.s
        if status not in ("active", "paused", "closed"):
            raise invalid("status must be active, paused or closed")
        resume_payload = None
        with s.store.tx() as c:
            case = s.store.lock_case(c, run_id, case_id)
            if expected_revision != case["revision"]:
                raise conflict("REVISION_MISMATCH", f"Case is at revision {case['revision']}", case_revision=case["revision"])
            sub = self.get(run_id, case_id)
            if sub["status"] == "closed" and status != "closed":
                raise conflict("MONITORING_CLOSED", "Monitoring was closed for this case", case_revision=case["revision"])
            prev = sub["status"]
            sub["status"] = status
            sub["updated_at"] = _now()
            sub.setdefault("history", []).append({"from": prev, "to": status, "at": _now(), "case_revision": case["revision"], "command_id": str(uuid.uuid4())})
            new_rev = case["revision"] + 1
            if prev == "paused" and status == "active" and sub.get("pending_change_ids"):
                resume_payload = {"change_ids": list(sub["pending_change_ids"]), "affected": list(sub.get("pending_affected", []))}
                sub["pending_change_ids"], sub["pending_affected"] = [], []
                s.store.update_case(c, run_id, case_id, input_revision=case["input_revision"] + 1, monitoring_status=status, revision=new_rev,
                                    stale_reasons=case["stale_reasons"] + [{"kind": "decision", "change_ids": resume_payload["change_ids"],
                                                                            "summary": "Changes received while monitoring was paused"}])
            else:
                s.store.update_case(c, run_id, case_id, monitoring_status=status, revision=new_rev)
            s.store.put(st.subscriptions, sub["subscription_id"], run_id, sub, case_id=case_id, status=status, dependency_revision=sub["dependency_revision"])
            s.bus.publish(run_id, case_id, "monitoring.updated", f"Monitoring {prev} → {status}", {"from": prev, "to": status,
                                                                                                  "reconciling": resume_payload}, case_revision=new_rev)
        if resume_payload and s.store.get_case(run_id, case_id)["current_decision_id"]:
            s.coordinator.request_reassessment(run_id, case_id, {"trigger_id": resume_payload["change_ids"][-1], "trigger_type": "reconcile",
                                                                 "title": "Reconcile changes received while paused", "impact_paths": []},
                                               resume_payload["affected"] or None)
        return {"case_id": case_id, "status": status, "case_revision": new_rev, "reconciled": resume_payload}
