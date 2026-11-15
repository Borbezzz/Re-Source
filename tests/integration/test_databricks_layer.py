"""Databricks data layer integration tests (PRD §5.3, AC-15, DISC-04).

Offline tests always run. Live tests skip cleanly unless Databricks SQL is configured
(DATABRICKS_SERVER_HOSTNAME / DATABRICKS_HTTP_PATH / token) and RS_SKIP_DATABRICKS is not set.
Run: cd backend && uv run pytest ../tests/integration/test_databricks_layer.py -q
"""

from __future__ import annotations

import importlib.util
import os
import uuid
from pathlib import Path
from types import SimpleNamespace

import pytest

from recovery.adapters import store as st
from recovery.adapters.databricks_sql import databricks_sql
from recovery.adapters.search import EvidenceSearch
from recovery.adapters.store import OperationalStore, now_iso
from recovery.domain.catalog import load_catalog
from recovery.services.projection import DELTA_TABLES, PROJECTION_TABLES, ProjectionWorker, merge_statements, rows_for

LIVE = databricks_sql.configured and not os.getenv("RS_SKIP_DATABRICKS")
live = pytest.mark.skipif(not LIVE, reason="Databricks SQL not configured (or RS_SKIP_DATABRICKS set)")
LOADER = Path(__file__).resolve().parents[2] / "data" / "ingestion" / "load_delta.py"


@pytest.fixture()
def services(tmp_path):
    svc = SimpleNamespace(store=OperationalStore(f"sqlite:///{tmp_path}/op.sqlite3"), catalog=load_catalog())
    svc.search = EvidenceSearch(svc)
    svc.projection = ProjectionWorker(svc)
    return svc


def _loader():
    spec = importlib.util.spec_from_file_location("load_delta", LOADER)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


# ---------------------------------------------------------------------------------- offline
def test_loader_builds_rows_for_every_reference_table():
    rows = _loader().build_rows()
    cat = load_catalog()
    assert len(rows["rs_evidence_versions"]) == len(cat.evidence)
    assert len(rows["rs_relationships"]) == len(cat.relationships)
    assert len(rows["rs_offers"]) == len(cat.offers)
    assert all(r["data_origin"] == "synthetic_demo" for r in rows["rs_evidence_versions"])
    # follow-up and evidence-change versions are loaded but not initially active
    flags = {r["version_id"]: r["initially_active"] for r in rows["rs_evidence_versions"]}
    assert flags["ev-tr-sa1"] is False and flags["ev-sb-fn-0042-b"] is False and flags["ev-q-pa"] is True
    fact_ids = {r["fact_id"] for r in rows["rs_extracted_facts"]}
    assert "fact:ev-f1-pa:part_number" in fact_ids


def test_merge_statements_respect_param_cap_and_quote_identifiers():
    rows = _loader().build_rows()["rs_relationships"]
    stmts = merge_statements("rs_relationships", rows)
    assert sum(len(p) for _, p in stmts) == len(rows) * len(DELTA_TABLES["rs_relationships"][0])
    assert all(len(p) <= 240 for _, p in stmts)
    assert all("MERGE INTO" in s and "`relationship_id`" in s for s, _ in stmts)


def test_projection_rows_strip_facts_and_label_source_revision():
    rec = {"decision_id": "d1", "scenario_run_id": "r1", "case_id": "case-primary", "case_revision": 4, "facts": {"x": 1},
           "checks": [{"check_id": "c1", "candidate_id": "OFF-PA", "requirement_id": "REQ", "result": "pass", "mandatory": True}]}
    out = dict(rows_for("project_decision", {"record": rec}))
    assert out["rs_decision_snapshots"][0]["source_revision"] == 4
    assert "facts" not in out["rs_decision_snapshots"][0]["payload_json"]
    assert out["rs_check_results"][0]["check_key"] == "d1:c1"


def test_in_memory_search_fallback_and_follow_up_visibility(services, monkeypatch):
    monkeypatch.setattr(EvidenceSearch, "_delta_available", lambda self: False)
    res = services.search.search("fuel nozzle release certificate", filters={"doc_type": "release_certificate"})
    assert res["retrieval_mode"] == "in_memory_keyword"
    assert "not provisioned" in res["ai_search"]
    assert "ev-f1-pa" in [r["version_id"] for r in res["results"]]
    # follow-up evidence is not discoverable until a run activates it, but exact-ID retrieval always resolves it
    hidden = services.search.search("trace pack NG4410 back to birth")
    assert "ev-tr-sa1" not in [r["version_id"] for r in hidden["results"]]
    assert services.search.get_exact("ev-tr-sa1")["found"] is True


def test_projection_skips_when_not_configured(services, monkeypatch):
    monkeypatch.setattr(type(databricks_sql), "configured", property(lambda self: False))
    services.store.put(st.outbox, "op-x", "run-x", {"record": {"selection_id": "s1"}}, status="pending", op_type="project_selection",
                       attempts=0, available_at=now_iso())
    services.store.put(st.outbox, "op-docs", "run-x", {}, status="pending", op_type="generate_documents", attempts=0, available_at=now_iso())
    res = services.projection.process_once()
    assert res["skipped"] == 1
    assert services.store.get(st.outbox, "op-x")["status"] == "done"
    assert services.store.get(st.outbox, "op-docs")["status"] == "pending"  # not owned by the projection worker


# ---------------------------------------------------------------------------------- live
@live
def test_delta_reference_tables_match_catalog(services):
    detail = services.search.evidence_source_detail(refresh=True)
    assert detail["source"] == "delta", detail
    assert detail["in_sync"] is True


@live
def test_delta_keyword_search_returns_release_certificates(services):
    res = services.search.search("fuel nozzle release certificate", filters={"doc_type": "release_certificate"})
    assert res["retrieval_mode"] == "delta_sql_keyword"
    assert {"ev-f1-pa", "ev-f1-pb"} <= {r["version_id"] for r in res["results"]}


@live
def test_projection_worker_merges_idempotently(services):
    run_id = f"test-int-{uuid.uuid4().hex[:8]}"
    rec = {"decision_id": f"dec-{run_id}", "label": "D1", "case_id": "case-primary", "scenario_run_id": run_id, "case_revision": 2,
           "input_revision": 1, "generation_id": "g", "status": "current", "created_at": now_iso(), "summary": "integration test",
           "checks": [{"check_id": "c1", "candidate_id": "OFF-PA", "requirement_id": "REQ-FN-ID-01", "result": "pass", "mandatory": True,
                       "evidence_refs": ["ev-q-pa"], "evaluated_at": now_iso()}]}
    try:
        for _ in range(2):
            services.store.put(st.outbox, f"op-{run_id}", run_id, {"record": rec}, case_id="case-primary", status="pending",
                               op_type="project_decision", attempts=0, available_at=now_iso())
            assert services.projection.process_once()["processed"] == 1
        n = databricks_sql.query(f"SELECT COUNT(*) AS n FROM {databricks_sql.table('rs_decision_snapshots')} WHERE run_id = :r", {"r": run_id})[0]["n"]
        assert n == 1
    finally:
        for t in ("rs_decision_snapshots", "rs_check_results"):
            databricks_sql.query(f"DELETE FROM {databricks_sql.table(t)} WHERE run_id = :r", {"r": run_id})


@live
def test_projection_tables_exist():
    rows = databricks_sql.query(f"SHOW TABLES IN {databricks_sql.fq_schema} LIKE 'rs_*'")
    present = {r.get("tableName") or r.get("table_name") for r in rows}
    assert set(PROJECTION_TABLES) <= present
