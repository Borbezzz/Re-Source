"""Change activation and publication protocol (PRD §5.3.1, FR-10) — the single invalidation gateway
for signal, evidence, clock (effective/expiry) and reconciliation changes.

1. register change + namespace pending_change barrier (atomic)
2. stage the immutable new version; resolve impact over old ∪ new relationship paths
3. durable, idempotent per-case fan-out (input revision++, stale outputs, selection/doc invalidation)
4. activate the version manifest and clear the barrier
5. schedule coalesced per-case reassessments
"""

from __future__ import annotations

import hashlib
import logging
from datetime import datetime, timedelta, timezone
from typing import Any, Optional

from ..adapters import store as st
from ..domain.errors import invalid, not_found
from ..domain.impact import scope_entities
from ..domain.models import RiskSignal
from .run_state import iso, parse_ts

log = logging.getLogger("recovery.changes")


def _now() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def _label_path(path: list[dict], catalog: Any) -> list[dict]:
    return [{"id": n["id"], "type": n["type"], "label": catalog.label(n["id"]), **({"via": n["via"]} if n.get("via") else {})} for n in path]


class ChangeService:
    def __init__(self, services: Any):
        self.s = services
        self.fail_fanout_after: Optional[int] = None  # test hook (AC-20): simulate partial fan-out failure

    # ------------------------------------------------------------------ public entry points
    def inject_signal(self, run_id: str, fixture_signal_id: Optional[str] = None, signal: Optional[dict] = None) -> dict:
        if fixture_signal_id:
            fx = self.s.catalog.signals.get(fixture_signal_id)
            if not fx:
                raise not_found(f"scenario signal {fixture_signal_id}")
            sig = {k: v for k, v in fx.items() if k != "fixture_id"}
        elif signal:
            sig = dict(signal)
        else:
            raise invalid("Provide fixture_signal_id or signal")
        sig = RiskSignal.model_validate(sig).model_dump(mode="json")  # normalisation contract
        dedup = f"signal:{sig['source']}:{sig['source_event_id']}:v{sig['version']}"
        existing = self._existing(run_id, dedup)
        if existing:
            self.s.bus.publish(run_id, "__run__", "signal.received", f"Duplicate signal ignored: {sig['title']}",
                               {"signal_id": sig["signal_id"], "duplicate_of": existing["change_id"]})
            return {"change": existing, "duplicate": True, "affected_case_ids": existing.get("affected_case_ids", [])}
        now = self.s.run_state.now(run_id)
        # previous versions of the same source event: their scope is part of the impact union
        prev_versions = [r["payload"] for r in self.s.run_state.signal_rows(run_id) if r["source_event_id"] == sig["source_event_id"]]
        start_ids, hint = scope_entities(sig, self.s.catalog.sites)
        for pv in prev_versions:
            ids, h = scope_entities(pv, self.s.catalog.sites)
            start_ids += [i for i in ids if i not in start_ids]
            hint.update(h)
        scheduled = parse_ts(sig["effective_from"]) > now
        change = self._register(run_id, "signal", sig["signal_id"], f"{sig['source_event_id']}@v{sig['version']}", dedup, sig,
                                title=sig["title"], effective_at=sig["effective_from"], scope=sig["scope"])
        self.s.store.put(st.signals, f"{run_id}:{sig['signal_id']}", run_id, {**sig, "received_at": _now()}, status="staged",
                         source_event_id=sig["source_event_id"], version=sig["version"])
        self.s.bus.publish(run_id, "__run__", "signal.received", f"{sig.get('label') or 'Signal'}: {sig['title']}",
                           {"signal_id": sig["signal_id"], "change_id": change["change_id"], "category": sig["category"], "status": sig["status"],
                            "scheduled": scheduled, "data_origin": sig["data_origin"]})
        if scheduled:
            self._timer(run_id, f"timer-activate-{sig['signal_id']}", sig["effective_from"], "signal_activate", {"signal_id": sig["signal_id"]})
            return self._finish(run_id, change, [], {"offers": [], "cases": [], "paths": []}, activation_state="scheduled",
                                activate=lambda: None)
        impact = self.s.run_state.graph(run_id).impact(start_ids, hint)
        return self._propagate(run_id, change, impact, activate=lambda: self._activate_signal(run_id, sig))

    def inject_evidence_change(self, run_id: str, fixture_change_id: str) -> dict:
        ch = self.s.catalog.evidence_changes.get(fixture_change_id)
        if not ch:
            raise not_found(f"evidence change {fixture_change_id}")
        new_ev = ch["new_evidence"]
        dedup = f"evidence:{new_ev['document_id']}:{new_ev['version_id']}:{new_ev['hash'][:23]}"
        existing = self._existing(run_id, dedup)
        if existing:
            return {"change": existing, "duplicate": True, "affected_case_ids": existing.get("affected_case_ids", [])}
        change = self._register(run_id, "evidence", new_ev["version_id"], new_ev["version_id"], dedup, ch, title=ch["title"],
                                effective_at=new_ev.get("effective_at") or iso(self.s.run_state.now(run_id)),
                                scope={"document_id": new_ev["document_id"], "supersedes": ch["supersedes_version_id"]})
        self.s.run_state.set_global_evidence(run_id, new_ev["version_id"], "staged", fixture_change_id)
        rels = [{"relationship_id": f"rel-{run_id[:8]}-{new_ev['version_id']}-{i}", **r, "evidence_ids": [new_ev["version_id"]],
                 "effective_from": new_ev.get("effective_at"), "effective_to": None, "recorded_at": _now(), "revision": 1,
                 "data_origin": "synthetic_demo"} for i, r in enumerate(ch.get("relationships", []))]
        old_graph = self.s.run_state.graph(run_id)
        self.s.run_state.add_relationships(run_id, rels)
        new_graph = self.s.run_state.graph(run_id)
        # union of old and new dependency paths: the superseded version's dependants and the new version's
        imp_old = old_graph.impact([ch["supersedes_version_id"]], {ch["supersedes_version_id"]: "evidence"})
        imp_new = new_graph.impact([new_ev["version_id"]], {new_ev["version_id"]: "evidence"})
        impact = {"offers": sorted(set(imp_old["offers"]) | set(imp_new["offers"])), "cases": sorted(set(imp_old["cases"]) | set(imp_new["cases"])),
                  "paths": imp_new["paths"] + imp_old["paths"]}
        self.s.bus.publish(run_id, "__run__", "evidence.ingested", f"Evidence change: {ch['title']}",
                           {"version_id": new_ev["version_id"], "supersedes": ch["supersedes_version_id"], "change_id": change["change_id"]})

        def activate() -> None:
            self.s.run_state.set_global_evidence(run_id, new_ev["version_id"], "active", fixture_change_id)
            self.s.run_state.set_global_evidence(run_id, ch["supersedes_version_id"], "superseded", f"superseded by {new_ev['version_id']}")

        return self._propagate(run_id, change, impact, activate=activate)

    def advance_clock(self, run_id: str, hours: float) -> dict:
        run = self.s.store.get_run(run_id)
        if not run:
            raise not_found(f"run {run_id}")
        new_now = parse_ts(run["scenario_now"]) + timedelta(hours=hours)
        self.s.store.update_run(run_id, scenario_now=iso(new_now))
        executed = []
        for row in self.s.store.find(st.timers, run_id=run_id, status="pending", order_by="due_at"):
            if parse_ts(row["due_at"]) > new_now:
                continue
            t = row["payload"]
            self.s.store.set_status(st.timers, row["id"], "fired", {"fired_at": _now()})
            executed.append(row["id"])
            try:
                self._fire(run_id, row["id"], t)
            except Exception:  # noqa: BLE001
                log.exception("timer %s failed", row["id"])
        self.s.bus.publish(run_id, "__run__", "signal.received", f"Scenario clock advanced {hours:g} h to {iso(new_now)}",
                           {"scenario_now": iso(new_now), "executed_transitions": executed, "kind": "clock"})
        return {"scenario_run_id": run_id, "scenario_now": iso(new_now), "executed_transitions": executed}

    # ------------------------------------------------------------------ timers
    def _timer(self, run_id: str, timer_id: str, due_at: str, kind: str, payload: dict) -> None:
        if self.s.store.get(st.timers, f"{run_id}:{timer_id}"):
            return
        self.s.store.put(st.timers, f"{run_id}:{timer_id}", run_id, {"timer_id": timer_id, "kind": kind, **payload}, status="pending",
                         due_at=due_at, kind=kind)

    def register_evidence_expiry_timers(self, run_id: str, start: datetime, horizon_days: int = 90) -> None:
        for ev in self.s.catalog.evidence.values():
            exp = parse_ts(ev.get("expiry_at"))
            if exp and start < exp <= start + timedelta(days=horizon_days) and ev["version_id"] in self.s.catalog.initial_evidence_ids:
                self._timer(run_id, f"timer-expire-{ev['version_id']}", iso(exp), "evidence_expire", {"version_id": ev["version_id"]})

    def _fire(self, run_id: str, timer_row_id: str, t: dict) -> None:
        kind = t["kind"]
        if kind == "signal_activate":
            row = self.s.store.get(st.signals, f"{run_id}:{t['signal_id']}")
            sig = row["payload"]
            start_ids, hint = scope_entities(sig, self.s.catalog.sites)
            change = self._register(run_id, "clock", sig["signal_id"], f"activate:{sig['source_event_id']}@v{sig['version']}",
                                    f"clock:{timer_row_id}", {"timer": t}, title=f"Scheduled signal takes effect: {sig['title']}",
                                    effective_at=sig["effective_from"], scope=sig["scope"])
            impact = self.s.run_state.graph(run_id).impact(start_ids, hint)
            self._propagate(run_id, change, impact, activate=lambda: self._activate_signal(run_id, sig))
        elif kind == "signal_expire":
            row = self.s.store.get(st.signals, f"{run_id}:{t['signal_id']}")
            sig = row["payload"]
            start_ids, hint = scope_entities(sig, self.s.catalog.sites)
            change = self._register(run_id, "clock", sig["signal_id"], f"expire:{sig['source_event_id']}@v{sig['version']}",
                                    f"clock:{timer_row_id}", {"timer": t}, title=f"Signal expired: {sig['title']}",
                                    effective_at=sig.get("expiry_at") or _now(), scope=sig["scope"])
            impact = self.s.run_state.graph(run_id).impact(start_ids, hint)
            self._propagate(run_id, change, impact, activate=lambda: None)
        elif kind == "evidence_expire":
            vid = t["version_id"]
            ev = self.s.catalog.evidence[vid]
            change = self._register(run_id, "clock", vid, f"expire:{vid}", f"clock:{timer_row_id}", {"timer": t},
                                    title=f"Evidence expired: {ev['title']}", effective_at=ev["expiry_at"], scope={"version_id": vid})
            impact = self.s.run_state.graph(run_id).impact([vid], {vid: "evidence"})
            self._propagate(run_id, change, impact, activate=lambda: None)

    # ------------------------------------------------------------------ protocol steps
    def _existing(self, run_id: str, dedup: str) -> Optional[dict]:
        rows = self.s.store.find(st.change_events, run_id=run_id, dedup_key=dedup)
        return rows[0]["payload"] if rows else None

    def _register(self, run_id: str, trigger_type: str, trigger_id: str, source_version: str, dedup: str, payload: dict, *,
                  title: str, effective_at: str, scope: dict) -> dict:
        s = self.s
        change_id = f"chg-{hashlib.sha256(f'{run_id}|{dedup}'.encode()).hexdigest()[:12]}"
        with s.store.tx() as c:
            run = s.store.lock_run(c, run_id)
            seq = len(s.store.find(st.change_events, run_id=run_id)) + 1
            change = {"change_id": change_id, "scenario_run_id": run_id, "trigger_type": trigger_type, "trigger_id": trigger_id,
                      "source_version": source_version, "affected_entity_ids": [], "scope": scope, "effective_at": effective_at,
                      "received_at": _now(), "revision": seq, "dedup_key": dedup, "activation_state": "registered", "fanout_state": "pending",
                      "affected_case_ids": [], "impact_paths": [], "title": title, "fanout_done": []}
            s.store.put(st.change_events, change_id, run_id, change, status="registered", dedup_key=dedup, seq=seq)
            s.store.put(st.barriers, f"{run_id}:{change_id}", run_id, {"change_id": change_id, "since": _now()}, status="active")
            s.store.update_run(run_id, barrier_count=run["barrier_count"] + 1)
        return change

    def _propagate(self, run_id: str, change: dict, impact: dict, activate) -> dict:  # noqa: ANN001
        s = self.s
        cat = s.catalog
        paths = [_label_path(p, cat) for p in impact["paths"]]
        change["impact_paths"] = paths
        change["affected_entity_ids"] = impact["offers"]
        change["fanout_state"] = "partial" if impact["cases"] else "not_required"
        s.store.put(st.change_events, change["change_id"], run_id, change, status="staged", dedup_key=change["dedup_key"], seq=change["revision"])
        matched: list[str] = []
        queued: list[str] = []
        for i, case_id in enumerate(impact["cases"]):
            if self.fail_fanout_after is not None and i >= self.fail_fanout_after:
                raise RuntimeError(f"simulated fan-out failure after {i} case(s); barrier remains active for retry")
            res = self._fanout_case(run_id, change, case_id, [o for o in impact["offers"] if cat.offers.get(o, {}).get("case_id") == case_id],
                                    [p for p in paths if p and p[-1]["id"] == case_id])
            if res == "queued":
                queued.append(case_id)
            elif res:
                matched.append(case_id)
        return self._finish(run_id, change, matched, impact, activation_state="active", activate=activate, queued=queued)

    def retry_fanout(self, run_id: str, change_id: str) -> dict:
        """Idempotent retry of a partially failed fan-out (per-case keys prevent double invalidation)."""
        row = self.s.store.get(st.change_events, change_id)
        change = row["payload"]
        trig = change.get("trigger_type")
        if trig == "signal":
            sig = self.s.store.get(st.signals, f"{run_id}:{change['trigger_id']}")["payload"]
            start_ids, hint = scope_entities(sig, self.s.catalog.sites)
            impact = self.s.run_state.graph(run_id).impact(start_ids, hint)
            return self._propagate(run_id, change, impact, activate=lambda: self._activate_signal(run_id, sig))
        raise invalid(f"retry not supported for trigger type {trig}")

    def _fanout_case(self, run_id: str, change: dict, case_id: str, offers: list[str], paths: list[list[dict]]) -> Optional[str]:
        s = self.s
        sub = s.monitoring.get(run_id, case_id)
        key = f"{change['change_id']}:{case_id}"
        if key in change.get("fanout_done", []):
            return "already"
        if not sub or sub["status"] == "closed":
            return None
        if sub["status"] == "paused":
            s.monitoring.queue_while_paused(run_id, case_id, change["change_id"], offers)
            change.setdefault("fanout_done", []).append(key)
            return "queued"
        with s.store.tx() as c:
            case = s.store.lock_case(c, run_id, case_id)
            new_rev = case["revision"] + 1
            stale = list(case["stale_reasons"])
            stale.append({"kind": "decision", "change_id": change["change_id"], "summary": change["title"], "affected_candidate_ids": offers})
            values: dict[str, Any] = {"input_revision": case["input_revision"] + 1, "revision": new_rev, "stale_reasons": stale}
            if case["current_decision_id"] and case["state"] not in ("reassessing", "investigating"):
                values["prior_stable_state"] = case["state"]
                values["state"] = "reassessing"
            s.store.update_case(c, run_id, case_id, **values)
            s.bus.publish(run_id, case_id, "signal.matched" if change["trigger_type"] in ("signal", "clock") else "evidence.validated",
                          f"Change matched this case: {change['title']}", {"change_id": change["change_id"], "trigger_id": change["trigger_id"],
                                                                          "affected_candidate_ids": offers}, case_revision=new_rev)
            s.bus.publish(run_id, case_id, "impact.detected", f"Impact: " + " → ".join(n["label"] for n in (paths[0] if paths else []))[:300],
                          {"change_id": change["change_id"], "impact_paths": paths, "affected_candidate_ids": offers,
                           "stale_outputs": ["decision"] + (["selection", "documents"] if case["current_selection_id"] else [])},
                          case_revision=new_rev)
            if values.get("state") == "reassessing":
                s.bus.publish(run_id, case_id, "case.state_changed", "Reassessing affected outputs", {"state": "reassessing"}, case_revision=new_rev)
            if case["current_selection_id"]:
                sel = s.store.get(st.selections, case["current_selection_id"])
                if sel and sel["status"] == "current" and sel["payload"]["candidate_id"] in offers:
                    s.store.set_status(st.selections, sel["id"], "stale", {"stale_reason": change["title"]})
                    s.bus.publish(run_id, case_id, "selection.stale", f"Selection is stale: {change['title']}",
                                  {"selection_id": sel["id"], "change_id": change["change_id"]}, case_revision=new_rev)
                    if case["current_package_id"] and getattr(s, "documents", None) is not None:
                        s.documents.mark_stale(c, run_id, case_id, f"Selection invalidated by {change['title']}")
            change.setdefault("fanout_done", []).append(key)
            s.store.put(st.change_events, change["change_id"], run_id, change, status="staged", dedup_key=change["dedup_key"], seq=change["revision"])
        return "matched"

    def _finish(self, run_id: str, change: dict, matched: list[str], impact: dict, *, activation_state: str, activate, queued: Optional[list] = None) -> dict:  # noqa: ANN001
        s = self.s
        with s.store.tx() as c:
            run = s.store.lock_run(c, run_id)
            activate()
            change["activation_state"] = activation_state
            change["fanout_state"] = "complete" if impact["cases"] else "not_required"
            change["affected_case_ids"] = matched
            change["queued_case_ids"] = queued or []
            s.store.put(st.change_events, change["change_id"], run_id, change, status=activation_state, dedup_key=change["dedup_key"], seq=change["revision"])
            s.store.set_status(st.barriers, f"{run_id}:{change['change_id']}", "cleared", {"cleared_at": _now()})
            s.store.update_run(run_id, barrier_count=max(0, run["barrier_count"] - 1))
            s.bus.publish(run_id, "__run__", "signal.matched", f"{change['title']}: {len(matched)} case(s) affected"
                          + (f", {len(queued)} queued (monitoring paused)" if queued else ""),
                          {"change_id": change["change_id"], "affected_case_ids": matched, "queued_case_ids": queued or [],
                           "impact_paths": change["impact_paths"], "activation_state": activation_state})
        for case_id in matched:
            s.coordinator.request_reassessment(run_id, case_id, {"trigger_id": change["trigger_id"], "change_id": change["change_id"],
                                                                 "trigger_type": change["trigger_type"], "title": change["title"],
                                                                 "impact_paths": [p for p in change["impact_paths"] if p and p[-1]["id"] == case_id]},
                                               [o for o in impact["offers"] if s.catalog.offers.get(o, {}).get("case_id") == case_id])
        return {"change": change, "duplicate": False, "affected_case_ids": matched}

    def _activate_signal(self, run_id: str, sig: dict) -> None:
        s = self.s
        for row in s.run_state.signal_rows(run_id):
            if row["source_event_id"] == sig["source_event_id"] and row["payload"]["version"] < sig["version"] and row["status"] == "active":
                s.store.set_status(st.signals, row["id"], "superseded")
        s.store.set_status(st.signals, f"{run_id}:{sig['signal_id']}", "active")
        if sig.get("expiry_at"):
            self._timer(run_id, f"timer-expire-{sig['signal_id']}", sig["expiry_at"], "signal_expire", {"signal_id": sig["signal_id"]})
