# Delta ingestion

`load_delta.py` loads the versioned seeded fixture (`data/fixtures/seed-v1`) into Delta tables in
`workspace.resource`. All tables are prefixed `rs_`. The team lead's pre-existing tables
(`cost_estimates`, `evidence`, `sourcing_runs`, `suppliers`) are never touched.

```bash
cd backend && uv run python ../data/ingestion/load_delta.py --dry-run   # build rows only
cd backend && uv run python ../data/ingestion/load_delta.py             # CREATE IF NOT EXISTS + MERGE
```

- Idempotent: every table is MERGEd on its primary key. Re-running updates `ingested_at` only.
- Credentials come from the gitignored `.env` through `backend/recovery/config.py`. Nothing secret is printed.
- Table DDL lives in `backend/recovery/services/projection.py` (`DELTA_TABLES`). Both the loader and the runtime
  projection worker use it.
- Every value is sent as a native named parameter and `CAST` in SQL. Statements are batched at ≤240 parameters.
  On the serverless starter warehouse each MERGE takes about 3 s, and a full load takes about 4 minutes.

| Table | Contents | Key |
|---|---|---|
| rs_evidence_versions | Immutable evidence versions incl. `content_text`, `hash`, authority, `initially_active` (follow-up/evidence-change versions are loaded but inactive until a run activates them). Change Data Feed enabled for a future AI Search Delta Sync index. | version_id |
| rs_extracted_facts | Structured-parse facts (same `fact:<version>:<field>` IDs as the runtime extractor) | fact_id |
| rs_relationships | Evidence-graph edges (FR-11) | relationship_id |
| rs_requirements | Resolved requirement sets | requirement_key = id@version |
| rs_offers, rs_suppliers, rs_sites, rs_routes, rs_reliability_metrics, rs_signals | Scenario reference data | natural IDs |
| rs_decision_snapshots, rs_check_results, rs_selections, rs_document_packages, rs_receipts, rs_change_events | Outbox-driven projections written by `ProjectionWorker` (empty after load) | natural IDs |

All rows are synthetic demo data (`data_origin = synthetic_demo`).
