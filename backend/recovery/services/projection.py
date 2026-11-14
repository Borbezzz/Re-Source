"""Delta schema + operational→analytical projection worker (PRD §5.2, §5.3).

Lakebase/the operational store is authoritative for mutable state; committed outbox items drive
idempotent projections of decisions, checks, selections, packages, receipts and change events into
versioned Delta tables in `workspace.resource` (all prefixed `rs_`). Projections carry the source
revision they were produced from. Reference fixtures (evidence, facts, relationships, …) are loaded
by data/ingestion/load_delta.py using the same DDL defined here.
"""

from __future__ import annotations

import json
import logging
from datetime import datetime, timedelta, timezone
from decimal import Decimal
from typing import Any, Optional

from ..adapters import store as st
from ..adapters.databricks_sql import databricks_sql
from ..config import settings

log = logging.getLogger("recovery.projection")

SYNTHETIC_COMMENT = "Re-Source synthetic demo data (fixture seed-v1). Not real companies, parts or measured performance."
PROJECTION_COMMENT = "Re-Source operational projection (outbox-driven, labelled with source revision). Demo runs use synthetic data."

# name -> (column DDL list, primary key column, comment, tblproperties)
DELTA_TABLES: dict[str, tuple[list[str], str, str, dict[str, str]]] = {
    # ---- reference / evidence (loaded from fixtures) ----
    "rs_evidence_versions": ([
        "version_id STRING NOT NULL", "document_id STRING", "title STRING", "doc_type STRING", "hash STRING", "source_url STRING",
        "storage_uri STRING", "authority STRING", "authority_rank INT", "issuer STRING", "subject_ids_json STRING", "site_id STRING",
        "revision STRING", "effective_at TIMESTAMP", "expiry_at TIMESTAMP", "retrieved_at TIMESTAMP", "data_origin STRING",
        "validation_state STRING", "supersedes_version_id STRING", "content_text STRING", "initially_active BOOLEAN",
        "fixture_version STRING", "ingested_at TIMESTAMP",
    ], "version_id", SYNTHETIC_COMMENT + " Immutable evidence versions (authoritative for ingested evidence).",
        {"delta.enableChangeDataFeed": "true"}),
    "rs_extracted_facts": ([
        "fact_id STRING NOT NULL", "evidence_version_id STRING", "field STRING", "typed_value_json STRING", "unit STRING",
        "original_value STRING", "locator_json STRING", "confidence DOUBLE", "validation_state STRING", "validation_note STRING",
        "extraction_mode STRING", "fixture_version STRING", "ingested_at TIMESTAMP",
    ], "fact_id", SYNTHETIC_COMMENT + " Typed facts from the deterministic structured-form parser.", {}),
    "rs_relationships": ([
        "relationship_id STRING NOT NULL", "from_id STRING", "from_type STRING", "to_id STRING", "to_type STRING", "relation_type STRING",
        "evidence_ids_json STRING", "effective_from TIMESTAMP", "effective_to TIMESTAMP", "recorded_at TIMESTAMP", "revision INT",
        "data_origin STRING", "fixture_version STRING",
    ], "relationship_id", SYNTHETIC_COMMENT + " Evidence-graph relationship rows (FR-11).", {}),
    "rs_requirements": ([
        "requirement_key STRING NOT NULL", "requirement_id STRING", "requirement_set_id STRING", "version STRING", "template_code STRING",
        "title STRING", "plain_language STRING", "category STRING", "routes_json STRING", "mandatory BOOLEAN", "evaluator_id STRING",
        "evaluator_version STRING", "fact_inputs_json STRING", "params_json STRING", "evidence_authority_policy STRING",
        "feasibility_only BOOLEAN", "requirements_version STRING",
    ], "requirement_key", SYNTHETIC_COMMENT + " Versioned requirement sets (scenario design pending DISC-02).", {}),
    "rs_offers": ([
        "candidate_id STRING NOT NULL", "case_id STRING", "route STRING", "label STRING", "part_id STRING", "revision STRING",
        "supplier_id STRING", "site_id STRING", "manufacturer_id STRING", "seller_id STRING", "quantity INT", "condition STRING",
        "quote_version STRING", "price_amount DECIMAL(18,2)", "price_currency STRING", "stock INT", "capacity_json STRING",
        "logistics_route_id STRING", "plan_id STRING", "evidence_ids_json STRING", "route_specific_json STRING", "source_adapter STRING",
        "data_origin STRING", "fixture_version STRING",
    ], "candidate_id", SYNTHETIC_COMMENT + " Normalised candidate offers (BUY/MAKE).", {}),
    "rs_suppliers": ([
        "supplier_id STRING NOT NULL", "legal_entity_name STRING", "registry_json STRING", "roles_json STRING", "data_origin STRING",
        "fixture_version STRING",
    ], "supplier_id", SYNTHETIC_COMMENT + " Supplier legal entities (distinct from sites).", {}),
    "rs_sites": ([
        "site_id STRING NOT NULL", "supplier_id STRING", "name STRING", "address STRING", "country STRING", "geo_id STRING", "lat DOUBLE",
        "lon DOUBLE", "roles_json STRING", "capabilities_json STRING", "metric_refs_json STRING", "data_origin STRING", "fixture_version STRING",
    ], "site_id", SYNTHETIC_COMMENT + " Physical supplier sites.", {}),
    "rs_routes": ([
        "route_id STRING NOT NULL", "from_site_id STRING", "mode STRING", "label STRING", "base_transport_days DOUBLE",
        "freight_amount DECIMAL(18,2)", "freight_currency STRING", "baseline_exposure DOUBLE", "passes_through_json STRING",
        "destination STRING", "data_origin STRING", "fixture_version STRING",
    ], "route_id", SYNTHETIC_COMMENT + " Logistics routes with geographic dependencies.", {}),
    "rs_reliability_metrics": ([
        "metric_id STRING NOT NULL", "subject_id STRING", "site_id STRING", "metric_name STRING", "label STRING", "value DOUBLE",
        "unit STRING", "numerator DOUBLE", "denominator DOUBLE", "observation_window STRING", "source_evidence_id STRING", "data_origin STRING",
        "fixture_note STRING", "fixture_version STRING",
    ], "metric_id", SYNTHETIC_COMMENT + " Favourable scenario reliability fixtures — not measured real-world performance.", {}),
    "rs_signals": ([
        "signal_id STRING NOT NULL", "fixture_id STRING", "source STRING", "source_event_id STRING", "version INT", "category STRING",
        "title STRING", "scope_json STRING", "assertion_json STRING", "published_at TIMESTAMP", "observed_at TIMESTAMP",
        "effective_from TIMESTAMP", "expiry_at TIMESTAMP", "provenance_json STRING", "confidence DOUBLE", "status STRING",
        "data_origin STRING", "label STRING", "fixture_version STRING",
    ], "signal_id", SYNTHETIC_COMMENT + " Scenario risk signals (presenter-injected through the normal ingestion path).", {}),
    # ---- projections (outbox-driven) ----
    "rs_decision_snapshots": ([
        "decision_id STRING NOT NULL", "run_id STRING", "case_id STRING", "label STRING", "case_revision INT", "input_revision INT",
        "generation_id STRING", "status STRING", "preferred_candidate_id STRING", "evidence_set_id STRING", "evidence_hash STRING",
        "ranking_config_version STRING", "requirements_version STRING", "trigger_id STRING", "summary STRING", "created_at TIMESTAMP",
        "source_revision INT", "payload_json STRING", "projected_at TIMESTAMP",
    ], "decision_id", PROJECTION_COMMENT + " Immutable decision snapshots.", {}),
    "rs_check_results": ([
        "check_key STRING NOT NULL", "check_id STRING", "decision_id STRING", "run_id STRING", "case_id STRING", "candidate_id STRING",
        "requirement_id STRING", "result STRING", "mandatory BOOLEAN", "explanation STRING", "evidence_refs_json STRING",
        "fingerprint STRING", "reused_from_decision_id STRING", "rule_version STRING", "evaluated_at TIMESTAMP", "source_revision INT",
        "projected_at TIMESTAMP",
    ], "check_key", PROJECTION_COMMENT + " Check results per decision (check_key = decision_id:check_id).", {}),
    "rs_selections": ([
        "selection_id STRING NOT NULL", "run_id STRING", "case_id STRING", "candidate_id STRING", "decision_id STRING",
        "accepted_case_revision INT", "evidence_hash STRING", "actor STRING", "accepted_at TIMESTAMP", "status STRING",
        "source_revision INT", "payload_json STRING", "projected_at TIMESTAMP",
    ], "selection_id", PROJECTION_COMMENT + " Accepted selections.", {}),
    "rs_document_packages": ([
        "package_id STRING NOT NULL", "run_id STRING", "case_id STRING", "version INT", "selection_id STRING", "package_hash STRING",
        "review_state STRING", "status STRING", "destination_type STRING", "created_at TIMESTAMP", "source_revision INT",
        "payload_json STRING", "projected_at TIMESTAMP",
    ], "package_id", PROJECTION_COMMENT + " Immutable document package versions.", {}),
    "rs_receipts": ([
        "receipt_id STRING NOT NULL", "run_id STRING", "case_id STRING", "selection_id STRING", "package_id STRING", "package_version INT",
        "package_hash STRING", "destination_type STRING", "payload_hash STRING", "status STRING", "simulated_at TIMESTAMP",
        "source_revision INT", "payload_json STRING", "projected_at TIMESTAMP",
    ], "receipt_id", PROJECTION_COMMENT + " SIMULATED submission receipts (no real submission is ever made).", {}),
    "rs_change_events": ([
        "change_id STRING NOT NULL", "run_id STRING", "trigger_type STRING", "trigger_id STRING", "dedup_key STRING",
        "activation_state STRING", "fanout_state STRING", "affected_case_ids_json STRING", "received_at TIMESTAMP", "source_revision INT",
        "payload_json STRING", "projected_at TIMESTAMP",
    ], "change_id", PROJECTION_COMMENT + " Normalised change events (signals, evidence, clock).", {}),
}

REFERENCE_TABLES = [t for t in DELTA_TABLES if t not in {
    "rs_decision_snapshots", "rs_check_results", "rs_selections", "rs_document_packages", "rs_receipts", "rs_change_events"}]
PROJECTION_TABLES = [t for t in DELTA_TABLES if t not in REFERENCE_TABLES]

OWNED_OPS = {"project_decision", "project_selection", "project_receipt", "project_change", "project_package"}
MAX_PARAMS_PER_STATEMENT = 240


# ----------------------------------------------------------------------------------------------
# DDL / MERGE helpers (shared with data/ingestion/load_delta.py)
# ----------------------------------------------------------------------------------------------

def column_names(table: str) -> list[str]:
    return [c.split()[0] for c in DELTA_TABLES[table][0]]


def column_types(table: str) -> dict[str, str]:
    out = {}
    for c in DELTA_TABLES[table][0]:
        parts = c.split()
        out[parts[0]] = parts[1]
    return out


def _q(name: str) -> str:
    return f"`{name}`"


def create_table_sql(table: str) -> str:
    cols, _pk, comment, props = DELTA_TABLES[table]
    col_sql = ", ".join(_q(c.split(" ", 1)[0]) + " " + c.split(" ", 1)[1] for c in cols)
    sql = f"CREATE TABLE IF NOT EXISTS {databricks_sql.table(table)} ({col_sql}) USING DELTA COMMENT '{comment}'"
    if props:
        sql += " TBLPROPERTIES (" + ", ".join(f"'{k}' = '{v}'" for k, v in props.items()) + ")"
    return sql


def _param_value(v: Any) -> Any:
    """Every value is sent as a string (or NULL) and CAST in SQL — avoids type-unification issues in VALUES."""
    if v is None:
        return None
    if isinstance(v, bool):
        return "true" if v else "false"
    if isinstance(v, (dict, list)):
        return json.dumps(v, default=str, sort_keys=True)
    if isinstance(v, datetime):
        return v.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.%fZ")
    if isinstance(v, Decimal):
        return str(v)
    return str(v)


def merge_statements(table: str, rows: list[dict]) -> list[tuple[str, dict]]:
    """Parameterised MERGE statements keyed on the table's primary key, batched under the param cap."""
    if not rows:
        return []
    cols = column_names(table)
    types = column_types(table)
    pk = DELTA_TABLES[table][1]
    per_batch = max(1, MAX_PARAMS_PER_STATEMENT // len(cols))
    stmts: list[tuple[str, dict]] = []
    for start in range(0, len(rows), per_batch):
        chunk = rows[start:start + per_batch]
        params: dict[str, Any] = {}
        value_rows = []
        for i, row in enumerate(chunk):
            names = []
            for j, col in enumerate(cols):
                p = f"r{i}c{j}"
                params[p] = _param_value(row.get(col))
                names.append(f":{p}")
            value_rows.append("(" + ", ".join(names) + ")")
        select_cols = ", ".join(f"CAST(v.{_q(c)} AS {types[c]}) AS {_q(c)}" for c in cols)
        set_clause = ", ".join(f"t.{_q(c)} = s.{_q(c)}" for c in cols if c != pk)
        insert_cols = ", ".join(_q(c) for c in cols)
        insert_vals = ", ".join(f"s.{_q(c)}" for c in cols)
        sql = (
            f"MERGE INTO {databricks_sql.table(table)} AS t USING (SELECT {select_cols} FROM VALUES {', '.join(value_rows)} "
            f"AS v({', '.join(_q(c) for c in cols)})) AS s "
            f"ON t.{_q(pk)} = s.{_q(pk)} WHEN MATCHED THEN UPDATE SET {set_clause} WHEN NOT MATCHED THEN INSERT ({insert_cols}) VALUES ({insert_vals})"
        )
        stmts.append((sql, params))
    return stmts


def ensure_tables(tables: Optional[list[str]] = None) -> list[str]:
    tables = tables or list(DELTA_TABLES)
    stmts = [(create_table_sql(t), {}) for t in tables]
    databricks_sql.execute_many(stmts)
    return tables


# ----------------------------------------------------------------------------------------------
# Record → row mappers
# ----------------------------------------------------------------------------------------------

def _now() -> datetime:
    return datetime.now(timezone.utc)


def _iso_now() -> str:
    return _now().isoformat().replace("+00:00", "Z")


def _source_revision(payload: dict, record: dict) -> Optional[int]:
    for key in ("source_revision",):
        if payload.get(key) is not None:
            return int(payload[key])
    for key in ("case_revision", "accepted_case_revision", "revision", "version", "package_version"):
        if isinstance(record.get(key), int):
            return record[key]
    return None


def _strip_heavy(record: dict) -> dict:
    # facts are already authoritative in rs_extracted_facts; keep the projection payload compact
    return {k: v for k, v in record.items() if k not in {"facts"}}


def rows_for(op_type: str, payload: dict) -> list[tuple[str, list[dict]]]:
    record = payload.get("record", payload) if isinstance(payload, dict) else {}
    rev = _source_revision(payload, record)
    projected_at = _iso_now()
    if op_type == "project_decision":
        d = record
        run_id = d.get("scenario_run_id") or payload.get("run_id")
        decision_row = {
            "decision_id": d["decision_id"], "run_id": run_id, "case_id": d.get("case_id"), "label": d.get("label"),
            "case_revision": d.get("case_revision"), "input_revision": d.get("input_revision"), "generation_id": d.get("generation_id"),
            "status": d.get("status"), "preferred_candidate_id": d.get("preferred_candidate_id"), "evidence_set_id": d.get("evidence_set_id"),
            "evidence_hash": d.get("evidence_hash"), "ranking_config_version": d.get("ranking_config_version"),
            "requirements_version": d.get("requirements_version"), "trigger_id": d.get("trigger_id"), "summary": d.get("summary"),
            "created_at": d.get("created_at"), "source_revision": rev, "payload_json": _strip_heavy(d), "projected_at": projected_at,
        }
        checks = []
        for c in d.get("checks", []) or []:
            checks.append({
                "check_key": f"{d['decision_id']}:{c['check_id']}", "check_id": c["check_id"], "decision_id": d["decision_id"], "run_id": run_id,
                "case_id": c.get("case_id") or d.get("case_id"), "candidate_id": c.get("candidate_id"), "requirement_id": c.get("requirement_id"),
                "result": c.get("result"), "mandatory": c.get("mandatory"), "explanation": c.get("explanation"),
                "evidence_refs_json": c.get("evidence_refs", []), "fingerprint": c.get("fingerprint"),
                "reused_from_decision_id": c.get("reused_from_decision_id"), "rule_version": c.get("rule_version"),
                "evaluated_at": c.get("evaluated_at"), "source_revision": rev, "projected_at": projected_at,
            })
        return [("rs_decision_snapshots", [decision_row]), ("rs_check_results", checks)]
    if op_type == "project_selection":
        s = record
        return [("rs_selections", [{
            "selection_id": s["selection_id"], "run_id": s.get("scenario_run_id") or payload.get("run_id"), "case_id": s.get("case_id"),
            "candidate_id": s.get("candidate_id"), "decision_id": s.get("decision_id"), "accepted_case_revision": s.get("accepted_case_revision"),
            "evidence_hash": s.get("evidence_hash"), "actor": s.get("actor"), "accepted_at": s.get("accepted_at"), "status": s.get("status"),
            "source_revision": rev, "payload_json": s, "projected_at": projected_at,
        }])]
    if op_type == "project_package":
        p = record
        return [("rs_document_packages", [{
            "package_id": p["package_id"], "run_id": p.get("scenario_run_id") or payload.get("run_id"), "case_id": p.get("case_id"),
            "version": p.get("version"), "selection_id": p.get("selection_id"), "package_hash": p.get("package_hash"),
            "review_state": p.get("review_state"), "status": p.get("status"), "destination_type": p.get("destination_type"),
            "created_at": p.get("created_at"), "source_revision": rev, "payload_json": p, "projected_at": projected_at,
        }])]
    if op_type == "project_receipt":
        r = record
        return [("rs_receipts", [{
            "receipt_id": r["receipt_id"], "run_id": r.get("scenario_run_id") or payload.get("run_id"), "case_id": r.get("case_id"),
            "selection_id": r.get("selection_id"), "package_id": r.get("package_id"), "package_version": r.get("package_version"),
            "package_hash": r.get("package_hash"), "destination_type": r.get("destination_type"), "payload_hash": r.get("payload_hash"),
            "status": r.get("status"), "simulated_at": r.get("simulated_at"), "source_revision": rev, "payload_json": r,
            "projected_at": projected_at,
        }])]
    if op_type == "project_change":
        c = record
        return [("rs_change_events", [{
            "change_id": c["change_id"], "run_id": c.get("scenario_run_id") or payload.get("run_id"), "trigger_type": c.get("trigger_type"),
            "trigger_id": c.get("trigger_id"), "dedup_key": c.get("dedup_key"), "activation_state": c.get("activation_state"),
            "fanout_state": c.get("fanout_state"), "affected_case_ids_json": c.get("affected_case_ids", []), "received_at": c.get("received_at"),
            "source_revision": rev if rev is not None else c.get("revision"), "payload_json": c, "projected_at": projected_at,
        }])]
    raise ValueError(f"unsupported projection op {op_type}")


# ----------------------------------------------------------------------------------------------
# Worker
# ----------------------------------------------------------------------------------------------

def _parse(ts: Optional[str]) -> datetime:
    if not ts:
        return datetime.min.replace(tzinfo=timezone.utc)
    try:
        return datetime.fromisoformat(str(ts).replace("Z", "+00:00"))
    except ValueError:
        return datetime.min.replace(tzinfo=timezone.utc)


class ProjectionWorker:
    """Idempotent outbox consumer for Delta projections. Safe to call repeatedly (e.g. every few seconds)."""

    def __init__(self, services: Any):
        self.services = services
        self.store = services.store
        self.last_error: Optional[str] = None
        self.last_run_at: Optional[str] = None
        self._tables_ready = False
        self.processed = 0

    def _ensure(self) -> None:
        if not self._tables_ready:
            ensure_tables(PROJECTION_TABLES)
            self._tables_ready = True

    def _due(self, limit: int) -> list[dict]:
        rows = self.store.find(st.outbox, status="pending", order_by="created_at")
        now = _now()
        due = [r for r in rows if r.get("op_type") in OWNED_OPS and _parse(r.get("available_at")) <= now]
        return due[:limit]

    def process_once(self, limit: int = 20) -> dict:
        self.last_run_at = _iso_now()
        due = self._due(limit)
        result = {"processed": 0, "skipped": 0, "failed": 0, "retry_scheduled": 0, "ops": []}
        if not due:
            return result
        if not databricks_sql.configured or not settings.projection_enabled:
            for row in due:
                self.store.put(st.outbox, row["id"], row["run_id"], row["payload"], case_id=row.get("case_id"), status="done",
                               op_type=row["op_type"], attempts=row.get("attempts") or 0, available_at=row.get("available_at"),
                               last_error="skipped: not configured")
                result["skipped"] += 1
            return result
        try:
            self._ensure()
        except Exception as exc:  # noqa: BLE001
            self.last_error = f"ensure_tables: {str(exc)[:300]}"
            for row in due:
                self._fail(row, self.last_error, result)
            return result
        for row in due:
            try:
                stmts: list[tuple[str, dict]] = []
                for table, table_rows in rows_for(row["op_type"], row["payload"] or {}):
                    stmts += merge_statements(table, table_rows)
                if stmts:
                    databricks_sql.execute_many(stmts)
                self.store.put(st.outbox, row["id"], row["run_id"], row["payload"], case_id=row.get("case_id"), status="done",
                               op_type=row["op_type"], attempts=(row.get("attempts") or 0) + 1, available_at=row.get("available_at"),
                               last_error=None)
                result["processed"] += 1
                result["ops"].append({"id": row["id"], "op_type": row["op_type"], "statements": len(stmts)})
                self.processed += 1
            except Exception as exc:  # noqa: BLE001
                self._fail(row, f"{type(exc).__name__}: {str(exc)[:300]}", result)
        return result

    def _fail(self, row: dict, error: str, result: dict) -> None:
        attempts = (row.get("attempts") or 0) + 1
        self.last_error = error
        if attempts >= settings.outbox_max_attempts:
            status = "failed"
            available = row.get("available_at")
            result["failed"] += 1
        else:
            status = "pending"
            backoff = min(300, 5 * (2 ** (attempts - 1)))
            available = (_now() + timedelta(seconds=backoff)).isoformat().replace("+00:00", "Z")
            result["retry_scheduled"] += 1
        log.warning("projection %s (%s) attempt %s failed: %s", row["id"], row["op_type"], attempts, error)
        self.store.put(st.outbox, row["id"], row["run_id"], row["payload"], case_id=row.get("case_id"), status=status,
                       op_type=row["op_type"], attempts=attempts, available_at=available, last_error=error)

    def status(self) -> dict:
        rows = [r for r in self.store.find(st.outbox) if r.get("op_type") in OWNED_OPS]
        counts = {"pending": 0, "done": 0, "failed": 0}
        skipped = 0
        for r in rows:
            counts[r["status"]] = counts.get(r["status"], 0) + 1
            if (r.get("last_error") or "").startswith("skipped"):
                skipped += 1
        last_err = next((r["last_error"] for r in sorted(rows, key=lambda r: r["updated_at"], reverse=True)
                         if r.get("last_error") and not r["last_error"].startswith("skipped")), None)
        return {"counts": counts, "skipped_not_configured": skipped, "last_error": self.last_error or last_err,
                "last_run_at": self.last_run_at, "configured": databricks_sql.configured and settings.projection_enabled,
                "target_schema": f"{settings.databricks_catalog}.{settings.databricks_schema}", "tables": PROJECTION_TABLES}
