"""Scenario runs (PRD §2.3): create/reset isolated run namespaces, seeded/live/replay modes, and the
validated visual-action state machine (PRD §6.3 component visual state)."""

from __future__ import annotations

import threading
import time
import uuid
from datetime import datetime, timezone
from typing import Any, Optional

from ..config import settings

from ..adapters import store as st
from ..domain.errors import conflict, invalid, not_found
from .catalog_identity import identity as catalog_identity
from .run_state import iso, parse_ts


def _now() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


VISUAL_TRANSITIONS: dict[str, dict[str, Any]] = {
    # action: (allowed from visual states, to state, case-state prerequisite or None)
    "focus": {"from": None, "to": None},
    "reset_view": {"from": None, "to": None},
    "explode": {"from": {"assembled"}, "to": "exploded"},
    "reassemble": {"from": {"exploded", "failed"}, "to": "assembled"},
    "show_failure": {"from": {"assembled", "exploded"}, "to": "failed"},
    "remove": {"from": {"failed", "exploded"}, "to": "removed"},
    "install": {"from": {"removed", "replacement_ready", "failed", "exploded"}, "to": "installed",
                "requires_case": {"submission_simulated", "installation_visualized"}},
    "restore": {"from": {"installed"}, "to": "running", "requires_case": {"installation_visualized", "submission_simulated"}},
}


class ScenarioService:
    def __init__(self, services: Any):
        self.s = services

    def create_run(self, mode: str = "seeded", manifest_id: str = "engine-demo-001", fixture_version: str = "seed-v1",
                   replay_source_run_id: Optional[str] = None) -> dict:
        s = self.s
        cat = s.catalog
        if manifest_id != cat.engine["engine_id"]:
            raise invalid(f"manifest {manifest_id} is not available for investigations")
        if fixture_version != cat.fixture_version:
            raise invalid(f"fixture version {fixture_version} not loaded (have {cat.fixture_version})")
        if mode == "replay" and not (replay_source_run_id and s.store.get_run(replay_source_run_id)):
            raise invalid("replay mode needs replay_source_run_id of an existing run")
        if settings.public_demo and replay_source_run_id:
            from ..runtime.context import visitor_id
            if s.store.kv_get(f"run_owner:{replay_source_run_id}") != visitor_id.get():
                raise not_found("replay source")
        run_id = str(uuid.uuid4())
        start = parse_ts(cat.scenario["scenario_clock_start"])
        with s.store.tx():
            previous = s.store.current_run()
            if previous:
                s.monitoring.pause_run(previous["run_id"])
            s.store.create_run({"run_id": run_id, "mode": mode, "fixture_version": cat.fixture_version, "manifest_version": cat.manifest["manifest_version"],
                                "scenario_now": iso(start), "status": "active", "replay_source_run_id": replay_source_run_id, "barrier_count": 0,
                                "manifest_version_counter": 1})
            s.store.kv_set(f"run_catalog:{run_id}", catalog_identity(cat))
            for comp in cat.manifest["components"]:
                s.store.insert_case({"run_id": run_id, "case_id": comp["case_id"], "component_id": comp["component_id"], "state": "ready",
                                     "revision": 1, "input_revision": 1, "mode": mode, "visual_state": "assembled", "monitoring_status": "active",
                                     "stale_reasons": "[]", "decision_labels": "{}", "event_seq": 0})
                s.monitoring.create_subscription(run_id, comp["case_id"])
                s.bus.publish(run_id, comp["case_id"], "case.state_changed", f"Case ready: {comp['display_name']}",
                              {"state": "ready", "mode": mode, "fixture_version": cat.fixture_version})
            s.changes.register_evidence_expiry_timers(run_id, start)
            s.bus.publish(run_id, "__run__", "case.started", f"Scenario run created ({mode})", {"previous_run_id": previous and previous["run_id"]})
        if mode == "replay":
            if settings.job_backend == "vercel":
                s.jobs.enqueue("replay", run_id, {"source_run_id": replay_source_run_id}, key=f"replay:{run_id}")
            else:
                threading.Thread(target=self._replay, args=(replay_source_run_id, run_id), daemon=True).start()
        return self.view(run_id)

    def view(self, run_id: str) -> dict:
        run = self.s.store.get_run(run_id)
        if not run:
            raise not_found(f"run {run_id}")
        return {"scenario_run_id": run_id, "mode": run["mode"], "fixture_version": run["fixture_version"], "manifest_version": run["manifest_version"],
                "scenario_now": run["scenario_now"], "case_map": {c["component_id"]: c["case_id"] for c in self.s.store.list_cases(run_id)},
                "created_at": run["created_at"], "previous_run_ids": [r["run_id"] for r in self.s.store.list_runs() if r["run_id"] != run_id],
                "replay_source_run_id": run["replay_source_run_id"], "barrier_count": run["barrier_count"]}

    def ensure_run(self) -> dict:
        run = self.s.store.current_run()
        return self.view(run["run_id"]) if run else self.create_run()

    def _replay(self, source_run_id: str, run_id: str) -> None:
        """Presentation recovery: re-emit a recorded run's domain events, labelled Replay, and copy its records."""
        s = self.s
        for case in s.store.list_cases(source_run_id):
            for row in s.store.find(st.decisions, run_id=source_run_id, case_id=case["case_id"]):
                p = dict(row["payload"], scenario_run_id=run_id, replay_of=row["id"])
                s.store.put(st.decisions, f"{row['id']}-replay-{run_id[:6]}", run_id, p, case_id=case["case_id"], status=row["status"],
                            label=row["label"], generation_id=row["generation_id"], input_revision=row["input_revision"])
        cases = s.store.list_cases(source_run_id)
        streams = {c["case_id"]: s.store.events_after(source_run_id, c["case_id"], 0, 5000) for c in cases}
        for case_id, evs in streams.items():
            for e in evs:
                if e["type"] in ("case.state_changed",) and e["data"].get("state") == "ready":
                    continue
                s.bus.publish(run_id, case_id, e["type"], f"Replay: {e['summary']}", {**e["data"], "replay": True, "replay_of_event": e["event_id"]},
                              task_id=e.get("task_id"), evidence_refs=e.get("evidence_refs", []),
                              data_origin=e.get("data_origin", "synthetic_demo"))
                time.sleep(0.05)
        for c in cases:
            with s.store.tx() as conn:
                labels = {f"{k}-replay-{run_id[:6]}": v for k, v in c["decision_labels"].items()}
                s.store.update_case(conn, run_id, c["case_id"], state=c["state"], current_decision_id=c["current_decision_id"] and f"{c['current_decision_id']}-replay-{run_id[:6]}",
                                    initial_decision_id=c["initial_decision_id"] and f"{c['initial_decision_id']}-replay-{run_id[:6]}",
                                    decision_labels=labels, revision=c["revision"] + 1)

    # ------------------------------------------------------------------ visual state machine
    def visual_action(self, run_id: str, case_id: str, action: str) -> dict:
        s = self.s
        rule = VISUAL_TRANSITIONS.get(action)
        if rule is None:
            raise invalid(f"unknown visual action {action}")
        with s.store.tx() as c:
            case = s.store.lock_case(c, run_id, case_id)
            vs, cs = case["visual_state"], case["state"]
            if rule["from"] is not None and vs not in rule["from"]:
                raise conflict("VISUAL_TRANSITION_NOT_ALLOWED", f"Cannot {action} from visual state {vs}", case_revision=case["revision"],
                               allowed_next=self.allowed_next(vs, cs))
            req = rule.get("requires_case")
            if req and cs not in req:
                raise conflict("WORKFLOW_PREREQUISITE", f"{action} requires the workflow to reach {' or '.join(sorted(req))} (currently {cs})",
                               case_revision=case["revision"], allowed_next=self.allowed_next(vs, cs))
            new_vs = rule["to"] or vs
            new_cs = cs
            if action == "install":
                new_cs = "installation_visualized"
            elif action == "restore":
                new_cs = "restored_visualized"
            new_rev = case["revision"] + (1 if (new_vs != vs or new_cs != cs) else 0)
            if new_rev != case["revision"]:
                s.store.update_case(c, run_id, case_id, visual_state=new_vs, state=new_cs, revision=new_rev)
            sel = s.store.get(st.selections, case["current_selection_id"]) if case["current_selection_id"] else None
            s.bus.publish(run_id, case_id, "visual.updated", f"Visual: {action} → {new_vs}", {"action": action, "visual_state": new_vs, "case_state": new_cs,
                                                                                             "selected_candidate_id": sel and sel["payload"]["candidate_id"]},
                          case_revision=new_rev)
            if new_cs != cs:
                s.bus.publish(run_id, case_id, "case.state_changed", f"Case is now {new_cs.replace('_', ' ')}", {"state": new_cs}, case_revision=new_rev)
        return {"case_id": case_id, "visual_state": new_vs, "case_state": new_cs, "allowed_next": self.allowed_next(new_vs, new_cs),
                "selected_candidate_id": sel and sel["payload"]["candidate_id"]}

    @staticmethod
    def allowed_next(vs: str, cs: str) -> list[str]:
        out = []
        for action, rule in VISUAL_TRANSITIONS.items():
            if rule["from"] is not None and vs not in rule["from"]:
                continue
            if rule.get("requires_case") and cs not in rule["requires_case"]:
                continue
            out.append(action)
        return out
