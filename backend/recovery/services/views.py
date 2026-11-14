"""Read projections for the BFF: engine view, case view, evidence view (PRD §7)."""

from __future__ import annotations

from typing import Any, Optional

from ..adapters import store as st
from ..domain.errors import not_found


class Views:
    def __init__(self, services: Any):
        self.s = services

    def run_id(self, run_id: Optional[str] = None) -> str:
        if run_id:
            if not self.s.store.get_run(run_id):
                raise not_found(f"run {run_id}")
            return run_id
        return self.s.scenario.ensure_run()["scenario_run_id"]

    def engine(self, engine_id: str, run_id: Optional[str] = None) -> dict:
        cat = self.s.catalog
        if engine_id != cat.engine["engine_id"]:
            raise not_found(f"engine {engine_id}")
        rid = self.run_id(run_id)
        run = self.s.store.get_run(rid)
        cases = []
        for case in self.s.store.list_cases(rid):
            comp = cat.components[case["component_id"]]
            pref_label = None
            if case["current_decision_id"]:
                d = self.s.decisions.get(case["current_decision_id"])
                pref = next((c for c in d["candidates"] if c["candidate"]["candidate_id"] == d.get("preferred_candidate_id")), None) if d else None
                pref_label = pref and pref["candidate"]["label"]
            cases.append({"case_id": case["case_id"], "component_id": case["component_id"], "display_name": comp["display_name"],
                          "state": case["state"], "revision": case["revision"], "visual_state": case["visual_state"],
                          "current_decision_id": case["current_decision_id"], "preferred_candidate_label": pref_label,
                          "stale": bool(case["stale_reasons"])})
        engine = {k: v for k, v in cat.engine.items() if k in ("engine_id", "display_name", "representative_note", "configuration_revision",
                                                               "component_instance_ids", "scenario_manifest_version", "asset", "data_origin")}
        return {"engine": engine, "operating_story": cat.engine.get("operating_story"), "components": cat.manifest["components"], "cases": cases,
                "scenario_run_id": rid, "mode": run["mode"], "visual_states": cat.manifest.get("visual_states", [])}

    def tasks(self, run_id: str, case_id: str, generation_id: Optional[str]) -> list[dict]:
        if not generation_id:
            return []
        out: dict[str, dict] = {}
        for e in self.s.store.events_after(run_id, case_id, 0, 5000):
            if e.get("invocation_id") != generation_id or not e["type"].startswith("task."):
                continue
            tid = e["task_id"]
            cur = out.get(tid, {"task_id": tid, "name": e["data"].get("task", tid), "status": "pending", "started_at": None, "finished_at": None, "summary": None})
            st_ = e["data"].get("status")
            if st_ == "running":
                cur["started_at"] = e["occurred_at"]
                cur["status"] = "running"
            else:
                cur["status"] = st_ or "completed"
                cur["finished_at"] = e["occurred_at"]
                cur["started_at"] = cur["started_at"] or e["occurred_at"]
            cur["summary"] = e["summary"]
            out[tid] = cur
        return list(out.values())

    def case(self, case_id: str, run_id: Optional[str] = None) -> dict:
        rid = self.run_id(run_id)
        case = self.s.store.get_case(rid, case_id)
        if not case:
            raise not_found(f"case {case_id}")
        run = self.s.store.get_run(rid)
        comp = self.s.catalog.components[case["component_id"]]
        sel = None
        if case["current_selection_id"]:
            row = self.s.store.get(st.selections, case["current_selection_id"])
            sel = {**row["payload"], "status": row["status"]} if row else None
        gen = case["active_generation_id"]
        if not gen:
            gens = self.s.store.find(st.generations, run_id=rid, case_id=case_id, desc=True, limit=1)
            gen = gens[0]["id"] if gens else None
        sub = self.s.monitoring.get(rid, case_id)
        return {
            "case_id": case_id, "scenario_run_id": rid, "engine_id": comp["engine_id"], "component": comp, "state": case["state"],
            "prior_stable_state": case["prior_stable_state"], "revision": case["revision"], "input_revision": case["input_revision"],
            "mode": case["mode"], "visual_state": case["visual_state"], "monitoring_status": case["monitoring_status"],
            "current_decision_id": case["current_decision_id"], "initial_decision_id": case["initial_decision_id"],
            "decision_labels": case["decision_labels"], "current_selection": sel, "current_package_id": case["current_package_id"],
            "latest_receipt_id": case["latest_receipt_id"], "stale_reasons": case["stale_reasons"],
            "pending_change_ids": (sub or {}).get("pending_change_ids", []), "active_generation_id": case["active_generation_id"],
            "tasks": self.tasks(rid, case_id, gen), "event_cursor": case["event_seq"],
            "events_url": f"/api/v1/cases/{case_id}/events?after={case['event_seq']}&run_id={rid}",
            "allowed_visual_actions": self.s.scenario.allowed_next(case["visual_state"], case["state"]),
            "scenario_now": run["scenario_now"],
            "provenance": {"mode": case["mode"], "fixture_version": run["fixture_version"], "manifest_version": run["manifest_version"],
                           "label": {"seeded": "Seeded scenario (synthetic demo data)", "live": "Live connectors + seeded offers",
                                     "replay": "Replay"}.get(case["mode"], case["mode"]),
                           "data_origin": "synthetic_demo", "evidence_source": self.s.evidence_source,
                           "extraction_backend": self.s.extractor.last_mode, "model": self.s.model.model if self.s.model.available else "deterministic fallback"},
            "monitoring": sub, "data_origin": "synthetic_demo",
        }

    def evidence(self, version_id: str, run_id: Optional[str] = None) -> dict:
        rid = self.run_id(run_id)
        ev = self.s.run_state.evidence(version_id, rid)
        if not ev:
            raise not_found(f"evidence {version_id}")
        facts = self.s.store.cached_facts(ev["hash"], ev["doc_type"])
        fact_list = []
        if facts:
            for fld, f in facts["facts"].items():
                fact_list.append({**f, "evidence_version_id": version_id, "fact_id": f"fact:{version_id}:{fld}"})
        used_by = []
        for case in self.s.store.list_cases(rid):
            if case["current_decision_id"]:
                d = self.s.decisions.get(case["current_decision_id"])
                used_by += [c["check_id"] for c in d["checks"] if version_id in c["evidence_refs"]]
        superseded_by = None
        status = self.s.run_state.evidence_status(rid)
        if status.get(version_id) == "superseded":
            superseded_by = next((v for v, s in status.items() if s == "active" and self.s.catalog.evidence.get(v, {}).get("supersedes_version_id") == version_id), None)
        public = {k: v for k, v in ev.items() if k not in ("expected_facts",)}
        return {"evidence": public, "facts": fact_list, "used_by_checks": used_by, "preview_text": ev.get("content_text"),
                "superseded_by": superseded_by, "status": status.get(version_id, "not_active_in_run")}
