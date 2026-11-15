"""Idempotent loader: seed-v1 fixtures → Delta tables in `workspace.resource` (all prefixed `rs_`).

Usage (from the repo):
    cd backend && uv run python ../data/ingestion/load_delta.py            # create tables + MERGE rows
    cd backend && uv run python ../data/ingestion/load_delta.py --dry-run  # build rows/statements only

Creates (IF NOT EXISTS) every table in recovery.services.projection.DELTA_TABLES, MERGEs reference data
by primary key (re-running is a no-op apart from `ingested_at`), and prints row counts. Projection
tables are created empty; the outbox ProjectionWorker fills them at runtime.

All rows are SYNTHETIC demo data (data_origin = synthetic_demo). Credentials come from the gitignored
.env through recovery.config — nothing secret is printed.
"""

from __future__ import annotations

import argparse
import json
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

BACKEND = Path(__file__).resolve().parents[2] / "backend"
if str(BACKEND) not in sys.path:
    sys.path.insert(0, str(BACKEND))

from recovery.adapters.databricks_sql import databricks_sql  # noqa: E402
from recovery.domain.catalog import load_catalog  # noqa: E402
from recovery.domain.extraction import FIELD_SCHEMAS, coerce, parse_structured_form  # noqa: E402
from recovery.services.projection import (  # noqa: E402
    DELTA_TABLES, PROJECTION_TABLES, REFERENCE_TABLES, create_table_sql, merge_statements,
)


def _now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.%fZ")


def structured_facts(ev: dict, fixture_version: str, ingested_at: str) -> list[dict]:
    """Deterministic structured-form parse of a fixture document (same fact IDs as the runtime extractor)."""
    schema = FIELD_SCHEMAS.get(ev["doc_type"], {})
    parsed = parse_structured_form(ev.get("content_text") or "")
    rows = []
    for fld, type_code in schema.items():
        if fld not in parsed:
            continue
        raw, line = parsed[fld]
        value, state, note = coerce(type_code, raw)
        rows.append({
            "fact_id": f"fact:{ev['version_id']}:{fld}", "evidence_version_id": ev["version_id"], "field": fld,
            "typed_value_json": json.dumps(value), "unit": "days" if fld.endswith("_days") else None, "original_value": raw,
            "locator_json": {"line": line, "excerpt": f"{fld.upper().replace('_', ' ')}: {raw}"[:200]},
            "confidence": 0.9 if state == "valid" else None, "validation_state": state, "validation_note": note,
            "extraction_mode": "structured_parse", "fixture_version": fixture_version, "ingested_at": ingested_at,
        })
    return rows


def build_rows() -> dict[str, list[dict]]:
    cat = load_catalog()
    fv = cat.fixture_version
    ts = _now()
    rows: dict[str, list[dict]] = {t: [] for t in REFERENCE_TABLES}
    for ev in cat.evidence.values():
        rows["rs_evidence_versions"].append({
            "version_id": ev["version_id"], "document_id": ev["document_id"], "title": ev["title"], "doc_type": ev["doc_type"],
            "hash": ev["hash"], "source_url": ev.get("source_url"), "storage_uri": ev.get("storage_uri"), "authority": ev["authority"],
            "authority_rank": ev["authority_rank"], "issuer": ev.get("issuer"), "subject_ids_json": ev.get("subject_ids", []),
            "site_id": ev.get("site_id"), "revision": ev.get("revision"), "effective_at": ev.get("effective_at"), "expiry_at": ev.get("expiry_at"),
            "retrieved_at": ev.get("retrieved_at"), "data_origin": ev.get("data_origin"), "validation_state": ev.get("validation_state"),
            "supersedes_version_id": ev.get("supersedes_version_id"), "content_text": ev.get("content_text"),
            "initially_active": ev["version_id"] in cat.initial_evidence_ids, "fixture_version": fv, "ingested_at": ts,
        })
        rows["rs_extracted_facts"] += structured_facts(ev, fv, ts)
    for r in cat.relationships:
        rows["rs_relationships"].append({**{k: r.get(k) for k in ("relationship_id", "from_id", "from_type", "to_id", "to_type", "relation_type",
                                                                  "effective_from", "effective_to", "recorded_at", "revision", "data_origin")},
                                         "evidence_ids_json": r.get("evidence_ids", []), "fixture_version": fv})
    for spec in cat.requirement_sets.values():
        for q in spec["resolved"]:
            rows["rs_requirements"].append({
                "requirement_key": f"{q['requirement_id']}@{q['version']}", "requirement_id": q["requirement_id"],
                "requirement_set_id": q["requirement_set_id"], "version": q["version"], "template_code": q["template_code"], "title": q["title"],
                "plain_language": q["plain_language"], "category": q["category"], "routes_json": q["routes"], "mandatory": q["mandatory"],
                "evaluator_id": q["evaluator_id"], "evaluator_version": q["evaluator_version"], "fact_inputs_json": q["fact_inputs"],
                "params_json": q["params"], "evidence_authority_policy": q["evidence_authority_policy"], "feasibility_only": q["feasibility_only"],
                "requirements_version": cat.requirements_version,
            })
    for o in cat.offers.values():
        rows["rs_offers"].append({
            **{k: o.get(k) for k in ("candidate_id", "case_id", "route", "label", "part_id", "revision", "supplier_id", "site_id", "manufacturer_id",
                                     "seller_id", "quantity", "condition", "quote_version", "stock", "logistics_route_id", "plan_id",
                                     "source_adapter", "data_origin")},
            "price_amount": o["price"]["amount"], "price_currency": o["price"]["currency"], "capacity_json": o.get("capacity"),
            "evidence_ids_json": o.get("evidence_ids", []), "route_specific_json": o.get("route_specific", {}), "fixture_version": fv,
        })
    for s in cat.suppliers.values():
        rows["rs_suppliers"].append({"supplier_id": s["supplier_id"], "legal_entity_name": s["legal_entity_name"], "registry_json": s.get("registry"),
                                     "roles_json": s.get("roles", []), "data_origin": s.get("data_origin"), "fixture_version": fv})
    for s in cat.sites.values():
        g = s.get("geography", {})
        rows["rs_sites"].append({"site_id": s["site_id"], "supplier_id": s["supplier_id"], "name": s["name"], "address": s["address"],
                                 "country": g.get("country"), "geo_id": g.get("geo_id"), "lat": g.get("lat"), "lon": g.get("lon"),
                                 "roles_json": s.get("roles", []), "capabilities_json": s.get("capabilities", []),
                                 "metric_refs_json": s.get("metric_refs", []), "data_origin": s.get("data_origin"), "fixture_version": fv})
    for r in cat.routes.values():
        rows["rs_routes"].append({"route_id": r["route_id"], "from_site_id": r["from_site_id"], "mode": r["mode"], "label": r["label"],
                                  "base_transport_days": r["base_transport_days"], "freight_amount": r["freight"]["amount"],
                                  "freight_currency": r["freight"]["currency"], "baseline_exposure": r["baseline_exposure"],
                                  "passes_through_json": r.get("passes_through", []), "destination": r.get("destination"),
                                  "data_origin": r.get("data_origin"), "fixture_version": fv})
    for m in cat.metrics:
        rows["rs_reliability_metrics"].append({**{k: m.get(k) for k in ("metric_id", "subject_id", "site_id", "metric_name", "label", "value", "unit",
                                                                        "numerator", "denominator", "source_evidence_id", "data_origin", "fixture_note")},
                                               "observation_window": m.get("window"), "fixture_version": fv})
    for s in cat.signals.values():
        rows["rs_signals"].append({
            **{k: s.get(k) for k in ("signal_id", "fixture_id", "source", "source_event_id", "version", "category", "title", "published_at",
                                     "observed_at", "effective_from", "expiry_at", "confidence", "status", "data_origin", "label")},
            "scope_json": s.get("scope", {}), "assertion_json": s.get("assertion", {}), "provenance_json": s.get("provenance", {}), "fixture_version": fv,
        })
    return rows


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--dry-run", action="store_true", help="build rows and statements without touching Databricks")
    ap.add_argument("--tables", nargs="*", help="limit to these rs_* tables")
    args = ap.parse_args()

    rows = build_rows()
    tables = args.tables or list(DELTA_TABLES)
    plan = {t: merge_statements(t, rows.get(t, [])) for t in tables if t in REFERENCE_TABLES}
    summary = {t: {"rows": len(rows.get(t, [])), "merge_statements": len(plan.get(t, []))} for t in tables}
    if args.dry_run:
        print(json.dumps({"dry_run": True, "target": databricks_sql.fq_schema, "tables": summary}, indent=2))
        return 0
    if not databricks_sql.configured:
        print("Databricks SQL is not configured (DATABRICKS_SERVER_HOSTNAME / HTTP_PATH / auth). Nothing loaded.", file=sys.stderr)
        return 2

    started = time.time()
    ddl = [(create_table_sql(t), {}) for t in tables]
    databricks_sql.execute_many(ddl)
    print(f"created/verified {len(ddl)} tables in {databricks_sql.fq_schema} ({time.time() - started:.1f}s)")
    for t, stmts in plan.items():
        t0 = time.time()
        if stmts:
            databricks_sql.execute_many(stmts)
        print(f"  {t}: merged {summary[t]['rows']} rows in {len(stmts)} statement(s) ({time.time() - t0:.1f}s)")
    counts = {}
    for t in tables:
        counts[t] = databricks_sql.query(f"SELECT COUNT(*) AS n FROM {databricks_sql.table(t)}")[0]["n"]
    print(json.dumps({"target": databricks_sql.fq_schema, "row_counts": counts, "projection_tables": [t for t in tables if t in PROJECTION_TABLES],
                      "elapsed_s": round(time.time() - started, 1), "loaded_at": _now()}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
