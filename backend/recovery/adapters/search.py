"""EvidenceSearch (PRD §5.1 retrieval, §5.3 search freshness, AC-15).

Databricks AI Search (Vector Search) is NOT provisioned in this workspace (provisioning was declined),
so retrieval is honest about its mode:
  * delta_sql_keyword  — parameterised keyword scoring over Delta `rs_evidence_versions` (title/content ILIKE,
                         metadata filters) on the SQL warehouse
  * in_memory_keyword  — the same scoring over the fixture snapshot + run follow-up evidence (fallback)
Retrieval relevance only orders evidence discovery; exact facts and gates are always resolved from the
authoritative snapshot by exact ID (`get_exact`) so an unsynchronised index can never hide new evidence.
"""

from __future__ import annotations

import json
import logging
import re
import time
from typing import Any, Optional

from ..config import settings
from .databricks_sql import databricks_sql

log = logging.getLogger("recovery.search")

TABLE = "rs_evidence_versions"
AI_SEARCH_STATUS = "not provisioned (Vector Search endpoint creation declined; see decisions.md)"
_STOP = {"the", "a", "an", "of", "for", "and", "or", "to", "in", "on", "with", "by", "at", "is", "are", "from"}


def _tokens(query: str) -> list[str]:
    toks = [t for t in re.split(r"[^a-z0-9\-\.]+", query.lower()) if t and t not in _STOP and len(t) > 1]
    seen: list[str] = []
    for t in toks:
        if t not in seen:
            seen.append(t)
    return seen[:8]


class EvidenceSearch:
    def __init__(self, services: Any):
        self.services = services
        self._source: Optional[dict] = None
        self._delta_ok_until = 0.0
        self._delta_state: Optional[bool] = None
        self.last_error: Optional[str] = None
        self.last_mode: Optional[str] = None

    # ------------------------------------------------------------------ helpers
    @property
    def catalog(self):  # noqa: ANN201
        return self.services.catalog

    def _run_status(self, run_id: Optional[str]) -> Optional[dict[str, str]]:
        rs = getattr(self.services, "run_state", None)
        if run_id and rs is not None:
            try:
                return rs.evidence_status(run_id)
            except Exception:  # noqa: BLE001
                return None
        return None

    def _visible(self, version_id: str, initially_active: bool, status: Optional[dict[str, str]]) -> bool:
        if status is None:
            return initially_active
        s = status.get(version_id)
        return s in ("active", "followup")

    def _delta_available(self) -> bool:
        if not databricks_sql.configured:
            return False
        if self._delta_state is not None and time.time() < self._delta_ok_until:
            return self._delta_state
        try:
            rows = databricks_sql.query(f"SHOW TABLES IN {databricks_sql.fq_schema} LIKE '{TABLE}'")
            self._delta_state = bool(rows)
        except Exception as exc:  # noqa: BLE001
            self.last_error = f"{type(exc).__name__}: {str(exc)[:200]}"
            self._delta_state = False
        self._delta_ok_until = time.time() + 120
        return self._delta_state

    # ------------------------------------------------------------------ search
    def search(self, query: str, *, filters: Optional[dict] = None, run_id: Optional[str] = None, limit: int = 8) -> dict[str, Any]:
        filters = filters or {}
        tokens = _tokens(query)
        status = self._run_status(run_id)
        started = time.time()
        if tokens and self._delta_available():
            try:
                results = self._search_delta(tokens, filters, status, limit)
                self.last_mode = "delta_sql_keyword"
                return self._wrap(results, "delta_sql_keyword", query, started)
            except Exception as exc:  # noqa: BLE001
                self.last_error = f"{type(exc).__name__}: {str(exc)[:200]}"
                log.warning("Delta keyword search failed, falling back: %s", self.last_error)
        results = self._search_memory(tokens, filters, status, limit)
        self.last_mode = "in_memory_keyword"
        return self._wrap(results, "in_memory_keyword", query, started, fallback_reason=self.last_error if databricks_sql.configured else "Databricks not configured")

    def _wrap(self, results: list[dict], mode: str, query: str, started: float, fallback_reason: Optional[str] = None) -> dict[str, Any]:
        return {
            "query": query,
            "results": results,
            "retrieval_mode": mode,
            "ai_search": AI_SEARCH_STATUS,
            "reranker": "none (keyword score; ties by authority rank then version_id)",
            "fallback_reason": fallback_reason if mode == "in_memory_keyword" else None,
            "latency_ms": int((time.time() - started) * 1000),
            "freshness": self.freshness(cached_only=True),
        }

    def _search_delta(self, tokens: list[str], filters: dict, status: Optional[dict[str, str]], limit: int) -> list[dict]:
        params: dict[str, Any] = {}
        score_terms = []
        match_terms = []
        for i, tok in enumerate(tokens):
            params[f"t{i}"] = f"%{tok}%"
            score_terms.append(f"(CASE WHEN lower(title) LIKE :t{i} THEN 2 ELSE 0 END + CASE WHEN lower(content_text) LIKE :t{i} THEN 1 ELSE 0 END)")
            match_terms.append(f"lower(title) LIKE :t{i} OR lower(content_text) LIKE :t{i}")
        where = [f"({' OR '.join(match_terms)})"]
        if filters.get("doc_type"):
            params["doc_type"] = filters["doc_type"]
            where.append("doc_type = :doc_type")
        if filters.get("site_id"):
            params["site_id"] = filters["site_id"]
            where.append("site_id = :site_id")
        for j, sid in enumerate(filters.get("subject_ids") or []):
            params[f"s{j}"] = f'%"{sid}"%'
            where.append(f"subject_ids_json LIKE :s{j}")
        sql = (f"SELECT version_id, title, doc_type, authority_rank, initially_active, ({' + '.join(score_terms)}) AS score "
               f"FROM {databricks_sql.table(TABLE)} WHERE {' AND '.join(where)} "
               f"ORDER BY score DESC, authority_rank DESC, version_id ASC LIMIT {int(max(limit * 4, 20))}")
        rows = databricks_sql.query(sql, params)
        out = []
        for r in rows:
            if not self._visible(r["version_id"], bool(r["initially_active"]), status):
                continue
            out.append({"version_id": r["version_id"], "title": r["title"], "doc_type": r["doc_type"], "score": float(r["score"]),
                        "source": "delta"})
            if len(out) >= limit:
                break
        return out

    def _search_memory(self, tokens: list[str], filters: dict, status: Optional[dict[str, str]], limit: int) -> list[dict]:
        scored = []
        initial = self.catalog.initial_evidence_ids
        for ev in self.catalog.evidence.values():
            if not self._visible(ev["version_id"], ev["version_id"] in initial, status):
                continue
            if filters.get("doc_type") and ev["doc_type"] != filters["doc_type"]:
                continue
            if filters.get("site_id") and ev.get("site_id") != filters["site_id"]:
                continue
            if filters.get("subject_ids") and not set(filters["subject_ids"]) & set(ev.get("subject_ids", [])):
                continue
            title, text = ev["title"].lower(), (ev.get("content_text") or "").lower()
            score = sum((2 if t in title else 0) + (1 if t in text else 0) for t in tokens)
            if tokens and score == 0:
                continue
            scored.append((score, ev.get("authority_rank", 0), ev["version_id"], ev))
        scored.sort(key=lambda x: (-x[0], -x[1], x[2]))
        return [{"version_id": ev["version_id"], "title": ev["title"], "doc_type": ev["doc_type"], "score": float(s), "source": "fixture_snapshot"}
                for s, _, _, ev in scored[:limit]]

    # ------------------------------------------------------------------ exact retrieval / freshness
    def get_exact(self, version_id: str) -> dict[str, Any]:
        """Exact-ID retrieval. Delta first; falls back to the authoritative snapshot for not-yet-synced evidence."""
        if self._delta_available():
            try:
                rows = databricks_sql.query(f"SELECT * FROM {databricks_sql.table(TABLE)} WHERE version_id = :v", {"v": version_id})
                if rows:
                    r = dict(rows[0])
                    r["subject_ids"] = json.loads(r.pop("subject_ids_json") or "[]")
                    for k in ("effective_at", "expiry_at", "retrieved_at", "ingested_at"):
                        if r.get(k) is not None and hasattr(r[k], "isoformat"):
                            r[k] = r[k].isoformat()
                    return {"found": True, "source": "delta", "evidence": r}
            except Exception as exc:  # noqa: BLE001
                self.last_error = f"{type(exc).__name__}: {str(exc)[:200]}"
        ev = self.catalog.evidence.get(version_id)
        if ev:
            return {"found": True, "source": "fixture_snapshot (exact-ID fallback while index/Delta sync completes)", "evidence": dict(ev)}
        return {"found": False, "source": None, "evidence": None}

    def freshness(self, cached_only: bool = False) -> dict[str, Any]:
        src = self._source if cached_only and self._source else self.evidence_source_detail()
        return {"index": "delta_table" if src.get("source") == "delta" else "fixture_snapshot", "in_sync": src.get("in_sync"),
                "delta_rows": src.get("delta_rows"), "catalog_versions": src.get("catalog_versions"),
                "missing_in_delta": src.get("missing_in_delta", [])[:10], "hash_mismatches": src.get("hash_mismatches", [])[:10],
                "checked_at": src.get("checked_at"), "ai_search": AI_SEARCH_STATUS}

    def evidence_source_detail(self, refresh: bool = False) -> dict[str, Any]:
        if self._source and not refresh:
            return self._source
        catalog_hashes = {vid: ev["hash"] for vid, ev in self.catalog.evidence.items()}
        detail: dict[str, Any] = {"source": "fixture_snapshot", "in_sync": False, "catalog_versions": len(catalog_hashes),
                                  "delta_rows": None, "checked_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())}
        if self._delta_available():
            try:
                rows = databricks_sql.query(f"SELECT version_id, hash FROM {databricks_sql.table(TABLE)}")
                delta = {r["version_id"]: r["hash"] for r in rows}
                missing = sorted(set(catalog_hashes) - set(delta))
                mismatch = sorted(v for v in catalog_hashes if v in delta and delta[v] != catalog_hashes[v])
                detail.update(delta_rows=len(delta), missing_in_delta=missing, hash_mismatches=mismatch,
                              in_sync=not missing and not mismatch)
                if detail["in_sync"]:
                    detail["source"] = "delta"
            except Exception as exc:  # noqa: BLE001
                self.last_error = f"{type(exc).__name__}: {str(exc)[:200]}"
                detail["error"] = self.last_error
        else:
            detail["reason"] = "Databricks not configured" if not databricks_sql.configured else f"{TABLE} not present"
        self._source = detail
        return detail

    def evidence_source(self, refresh: bool = False) -> str:
        """'delta' when every catalog evidence version is present in Delta with a matching hash, else 'fixture_snapshot'."""
        return self.evidence_source_detail(refresh)["source"]
