# DISC-04 — Databricks workspace capability spike

Date: 2026-11-14 (UTC). Workspace host `dbc-449c2cd9-2bf6.cloud.databricks.com`, catalog `workspace`, schema `resource`,
SQL warehouse `8617c97c3ad572c6` ("Serverless Starter Warehouse", serverless PRO). The naming suggests Free Edition, but this is
not confirmed. Credentials came from the gitignored `.env`. No tokens are recorded here.

How it was observed: `recovery.services.readiness.capability_matrix(refresh=True)`, `data/ingestion/load_delta.py`, and the smoke and
integration tests in `tests/integration/test_databricks_layer.py` (9 passed against the live workspace). The latencies below come from a
laptop over the public internet with a warm warehouse. They are indicative only and are not performance claims.

## Capability matrix (observed)

| Capability | Result | Observation |
|---|---|---|
| SQL warehouse (Delta read/write) | ✅ works | `SELECT current_user()` ≈2.3 s warm. DBSQL 4.2.0. Parameterised MERGE ≈3 s per statement. |
| Unity Catalog tables in `workspace.resource` | ✅ works | Created 16 `rs_*` Delta tables (see below). The 4 pre-existing team-lead tables were not touched. |
| AI Functions — `ai_extract` | ✅ works | Probe returned the expected field. Round trip ≈5.7 s for one row. The batch path groups by document type, up to 20 rows per statement. |
| AI Functions — `ai_query` | ✅ works | Verified earlier in the session: `ai_query('databricks-gpt-oss-20b', …)` returned `OK`. |
| Model serving endpoints | ✅ present | 11 Databricks-hosted endpoints (gpt-oss, Llama, Qwen, Gemma, embeddings). No Claude endpoint, so the app model is OpenAI (see decisions.md). |
| MLflow tracking + tracing | ✅ works | Experiment `/Shared/ReSource/agent-traces` (id 2648868221488633) is active. `mlflow.set_experiment` and tracing init succeeded. |
| Databricks App `resource` | ✅ exists | Compute STOPPED, no active deployment. Resources: sql-warehouse, linkup-key and companies-house-key (secret scope `resource`), agent-traces experiment. |
| AI Search (Vector Search) | ❌ none provisioned | `GET /api/2.0/vector-search/endpoints` returns 0 endpoints. The user's permission system declined creating one. |
| Lakebase (Postgres) | ❌ none provisioned | `GET /api/2.0/database/instances` returns 0 instances. The user's permission system declined creating one. |
| Agent Bricks Agent Runtime / AgentKit | ❌ not used | Not verified. No Claude endpoint, and the Agent Bricks CLI is Beta. Not attempted. |
| Linkup | ✅ works | A live search returned results in ≈1.4 s. |
| Companies House | ✅ works | A live search for "Rolls-Royce" returned ROLLS-ROYCE PLC (active) in ≈0.1 s. |
| OpenAI (app model) | ✅ configured | `gpt-5.4-mini` via the Responses API. The readiness check spends no tokens. |

## Delta tables created (`workspace.resource`) and row counts after the first load

| Table | Rows | | Table | Rows |
|---|---|---|---|---|
| rs_evidence_versions | 68 | | rs_signals | 6 |
| rs_extracted_facts | 439 | | rs_decision_snapshots | 0 (projection) |
| rs_relationships | 201 | | rs_check_results | 0 (projection) |
| rs_requirements | 39 | | rs_selections | 0 (projection) |
| rs_offers | 11 | | rs_document_packages | 0 (projection) |
| rs_suppliers | 9 | | rs_receipts | 0 (projection) |
| rs_sites | 11 | | rs_change_events | 0 (projection) |
| rs_routes | 11 | | rs_reliability_metrics | 22 |

A full load took 237.7 s. The 68 evidence versions in Delta match the fixture catalog by hash (`evidence_source() == "delta"`,
`in_sync: true`). The projection smoke test merged a synthetic decision with 3 checks in ≈9 s. A rerun was idempotent (still 1 row), and
the test rows were deleted afterwards.

## Gaps and chosen alternatives (no change to the user-visible contract)

| PRD component | Status | Alternative in use | How to switch later |
|---|---|---|---|
| Lakebase operational store (§5.3) | Not provisioned (creation declined) | `OperationalStore` on local SQLite with serialised write transactions (`BEGIN IMMEDIATE`) and compare-and-swap on case rows. Postgres-ready code paths (`SELECT … FOR UPDATE`, pool recycle for OAuth token rotation). | Provision a Lakebase instance, set `RS_OPERATIONAL_DB_URL=postgresql+psycopg://…`, and add it as an App resource. The LangGraph checkpointer moves to Postgres automatically. |
| AI Search hybrid + reranker (§5.1, AC-15) | Not provisioned (creation declined) | `EvidenceSearch`: parameterised Delta SQL keyword scoring over `rs_evidence_versions` (`retrieval_mode = delta_sql_keyword`). It falls back to in-memory keyword scoring (`in_memory_keyword`). Exact-ID retrieval (`get_exact`) resolves fresh evidence before any index sync. | Create an endpoint plus a Delta Sync index on `rs_evidence_versions` (Change Data Feed is already enabled). Add an AI Search branch in `EvidenceSearch.search` and record `retrieval_mode = ai_search_hybrid`. |
| Agent Runtime / AgentKit durable server (§5.1, FR-14) | Not used | FastAPI BFF plus LangGraph with a persistent checkpointer, run in-process, targeting the existing Databricks App `resource`. | Wrap the same graph with the Agent Bricks CLI once a supported model path is chosen. |
| Claude via Databricks model interface | No Claude endpoint | OpenAI `gpt-5.4-mini` with the app's own key, behind a single `ModelClient`. | Swap the `ModelClient` implementation. |
| `ai_parse_document` on volumes | Not exercised | Evidence is structured text, so `ai_extract` plus a deterministic structured-form parser cross-check is enough. | Create a UC volume, upload PDFs, and add a parse step before `ai_extract`. |

## Open items

- Deployed durability test (§9 DISC-04: interruption plus reconnect on the deployed App) has not been run yet. The App compute is stopped.
- Lakebase OAuth token rotation is untested (no instance).
- Edition, quotas and region are not confirmed beyond what the APIs above returned.
