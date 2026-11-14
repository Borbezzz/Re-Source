"""Run-scoped overlay on the immutable catalog: scenario clock, active evidence version manifest,
follow-up evidence, active signals and run-added relationships."""

from __future__ import annotations

import hashlib
from datetime import datetime, timezone
from typing import Optional

from ..adapters import store as st
from ..adapters.store import OperationalStore
from ..domain.catalog import Catalog
from ..domain.impact import Graph


def parse_ts(v: str | datetime | None) -> Optional[datetime]:
    if v is None:
        return None
    if isinstance(v, datetime):
        return v if v.tzinfo else v.replace(tzinfo=timezone.utc)
    return datetime.fromisoformat(v.replace("Z", "+00:00"))


def iso(dt: datetime) -> str:
    return dt.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")


class RunState:
    def __init__(self, store: OperationalStore, catalog: Catalog):
        self.store = store
        self.catalog = catalog

    # ------------------------------------------------------------------ clock
    def now(self, run_id: str) -> datetime:
        run = self.store.get_run(run_id)
        return parse_ts(run["scenario_now"])

    # ------------------------------------------------------------------ evidence manifest
    def evidence_overrides(self, run_id: str) -> list[dict]:
        return self.store.find(st.evidence_state, run_id=run_id)

    def evidence_status(self, run_id: str) -> dict[str, str]:
        """version_id -> 'active' | 'superseded' | 'staged' | 'followup' (global view)."""
        status = {vid: "active" for vid in self.catalog.initial_evidence_ids}
        for row in self.evidence_overrides(run_id):
            if row["candidate_id"] in (None, "*"):
                status[row["version_id"]] = row["status"]
            elif row["status"] == "active":
                status.setdefault(row["version_id"], "followup")
        return status

    def evidence(self, version_id: str, run_id: Optional[str] = None) -> Optional[dict]:
        ev = self.catalog.evidence.get(version_id)
        if ev is None:
            return None
        ev = dict(ev)
        if run_id:
            s = self.evidence_status(run_id).get(version_id)
            if s == "superseded":
                ev["validation_state"] = "superseded"
        return ev

    def candidate_docs(self, run_id: str, offer: dict, status: Optional[dict[str, str]] = None) -> list[dict]:
        status = status or self.evidence_status(run_id)
        by_doc: dict[str, dict] = {}
        doc_ids: list[str] = []
        for vid in offer["evidence_ids"]:
            ev = self.catalog.evidence.get(vid)
            if ev:
                doc_ids.append(ev["document_id"])
        # current active version for each referenced document (a new revision replaces the old one)
        for vid, s in status.items():
            if s != "active":
                continue
            ev = self.catalog.evidence.get(vid)
            if ev and ev["document_id"] in doc_ids:
                cur = by_doc.get(ev["document_id"])
                if cur is None or (ev.get("effective_at") or "") > (cur.get("effective_at") or ""):
                    by_doc[ev["document_id"]] = ev
        # follow-up evidence retrieved for this candidate
        for row in self.evidence_overrides(run_id):
            if row["candidate_id"] == offer["candidate_id"] and row["status"] == "active":
                ev = self.catalog.evidence.get(row["version_id"])
                if ev:
                    by_doc[ev["document_id"]] = ev
        return [dict(e) for e in by_doc.values()]

    def activate_followup(self, run_id: str, candidate_id: str, version_id: str) -> None:
        ev = self.catalog.evidence[version_id]
        self.store.put(st.evidence_state, f"{run_id}:{version_id}:{candidate_id}", run_id, {"reason": "gap follow-up"},
                       status="active", version_id=version_id, document_id=ev["document_id"], candidate_id=candidate_id)

    def set_global_evidence(self, run_id: str, version_id: str, status: str, reason: str) -> None:
        ev = self.catalog.evidence[version_id]
        self.store.put(st.evidence_state, f"{run_id}:{version_id}:*", run_id, {"reason": reason}, status=status,
                       version_id=version_id, document_id=ev["document_id"], candidate_id="*")

    def evidence_set_hash(self, docs_by_candidate: dict[str, list[dict]]) -> tuple[str, str]:
        items = sorted({(d["version_id"], d["hash"]) for docs in docs_by_candidate.values() for d in docs})
        h = hashlib.sha256("|".join(f"{v}:{x}" for v, x in items).encode()).hexdigest()
        return f"evset-{h[:16]}", f"sha256:{h}"

    # ------------------------------------------------------------------ signals
    def signal_rows(self, run_id: str) -> list[dict]:
        return self.store.find(st.signals, run_id=run_id, order_by="created_at")

    def active_signals(self, run_id: str, now: Optional[datetime] = None) -> list[dict]:
        now = now or self.now(run_id)
        latest: dict[str, dict] = {}
        for row in self.signal_rows(run_id):
            if row["status"] not in ("active", "superseded"):
                continue  # staged signals are not yet authoritative
            sig = row["payload"]
            cur = latest.get(sig["source_event_id"])
            if cur is None or sig["version"] > cur["version"]:
                latest[sig["source_event_id"]] = sig
        out = []
        for sig in latest.values():
            if sig["status"] == "retracted":
                continue
            eff = parse_ts(sig["effective_from"])
            exp = parse_ts(sig.get("expiry_at"))
            if eff and eff > now:
                continue
            if exp and exp <= now:
                continue
            out.append(sig)
        return sorted(out, key=lambda s: s["signal_id"])

    # ------------------------------------------------------------------ relationships
    def relationships(self, run_id: str) -> list[dict]:
        extra = self.store.kv_get(f"rels:{run_id}") or []
        return self.catalog.relationships + extra

    def add_relationships(self, run_id: str, rels: list[dict]) -> None:
        extra = self.store.kv_get(f"rels:{run_id}") or []
        known = {r["relationship_id"] for r in extra}
        for r in rels:
            if r["relationship_id"] not in known:
                extra.append(r)
        self.store.kv_set(f"rels:{run_id}", extra)

    def graph(self, run_id: str) -> Graph:
        return Graph(self.relationships(run_id))
