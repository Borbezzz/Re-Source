# Workflow provider provenance

The Studio graph and step rail now name Linkup Search and Databricks `ai_extract`. The save-case node identifies Databricks Lakebase when the API reports `lakebase_postgres`, and local SQLite during offline development. Request output also explains Databricks `ai_parse_document` and reports whether a document actually records that extraction method.

## Actual responsibilities

| Feature | Implementation | Current prepared Studio run |
| --- | --- | --- |
| Linkup Search | Standard search returns supplier page titles, snippets and source URLs in `product_workers._live_candidates` | Skipped; prepared offers are used |
| Databricks AI Functions: `ai_extract` | SQL warehouse extracts supplier name, country, materials and certification claims from Linkup snippets | Skipped; prepared claims are used |
| Databricks AI Functions: `ai_parse_document` | Document intake extracts text/layout from document bytes mirrored to a Unity Catalog volume | Skipped; ZIP supplies prepared parts/model |
| Databricks Lakebase | Operational Postgres store persists project state, research, selection, RFQ and approval | Used in production; SQLite locally |
| Re::Source checks/ranking | Deterministic checks and weighted delivery/cost/evidence scoring | Runs against prepared site evidence |
| Vercel Queues | Executes durable background jobs where configured | Reported independently of Databricks |

Configured credentials alone never produce a successful provider badge. Supplier research status is derived from the selected part's `providers_used`, mode and stage. An extraction fallback keeps original source snippets and is not presented as a successful AI call. Extracted public-web claims remain unverified. The disruption replay and supplier mailbox remain simulated. No live research was enabled by this change; the existing prepared demo is preserved.

## Validation

- `npm run build`: passed.
- `npm test`: all 30 tests passed, including five provenance tests covering demo bypass, successful calls, active/failed calls, local persistence, document parsing and isolation between parts.
- `e2e/workflow-providers.spec.ts`: uploads the prepared ZIP and runs discovery through RFQ creation using the real local API. Checks provider names/status, persistence provenance and clean stage output on desktop and mobile, including no toolbar overlap or page errors.
- Read-only production readiness check confirmed Lakebase Postgres and configured Linkup. MLflow tracing was disabled; it is not claimed by this UI.

No backend contract, extraction behavior or external messaging changed.
