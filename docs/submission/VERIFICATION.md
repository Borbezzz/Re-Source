# Submission claim verification — 15 November 2026

Documentation baseline: `origin/main` at `cc61a5b` (merged cutaway selection, PR #55). This audit reads implementation and historical verification; it does not replace those reports with a new full application test run.

## Current public deployment

Checked [the public application](https://resource-borbez2s-projects.vercel.app/) through its existing `/api/v1/health` and `/api/v1/readiness` endpoints at **10:54 GMT on 15 November 2026**. No new sourcing project, supplier message or purchase was created.

| Observation | Result |
| --- | --- |
| Health | `status: ok`, schema version 1.5. |
| Readiness | `status: ok`. |
| Operational store | Lakebase Postgres. |
| SQL warehouse | Successful connection/query. |
| AI Functions | The readiness probe executed `ai_extract` and returned the expected fixture identifier. |
| Delta | All 16 application tables present; 68 evidence versions. |
| Evidence synchronization | 68 catalog versions / 68 Delta rows, no missing versions or hash mismatches. |
| Lakebase | Existing `resource-ops` instance; application uses Postgres. |
| Graph checkpoint store | Postgres. |
| Delta projection | 26 done, 0 pending, 0 failed at the time of the response. |
| MLflow | Active experiment exists; runtime tracing is disabled. |
| Linkup | Configured; readiness explicitly states that no live Linkup call was made. |
| Companies House | Configured; no live registry lookup in this check. |
| Databricks App | Retained App compute is stopped; public hosting is Vercel. |
| AI Search / Vector Search | No endpoint provisioned; keyword retrieval is used. |
| Agent Bricks / AgentKit runtime | Not used; FastAPI/LangGraph is the implemented recovery runtime. |

Readiness executes diagnostic SQL/AI probes, so this is not merely an environment-variable inspection. It still does not prove a fresh end-to-end sourcing run. Real Linkup and PDF parsing claims are supported by the recorded executions below.

## Connected execution evidence

| Claim | Evidence |
| --- | --- |
| Live Linkup plus Databricks extraction returned six leads | [Product result](../verification/product-workflow-20261115/deployed-product.json). |
| Databricks parsed a real archival drawing | [NASA PDF result](../verification/product-workflow-20261115/nasa-blueprint.json) and [fixture provenance](../../data/fixtures/intake/README.md). |
| Autonomous live research reached an RFQ and stopped at missing contact | [Staged live result](../verification/agent-outreach-20261115/staged-live.json). |
| Demo completed without continuous reads | [Autonomous verification report](../verification/agent-outreach-20261115/REPORT.md). |
| Prepared provider stages are honestly skipped | [Provider provenance report](../verification/provider-workflow-2026-11-15.md). |
| MLflow domain evaluation was exercised | [Evaluation README](../../tests/evaluations/README.md), including dataset limits and a superseded-run explanation. |

These observations are specific executions. They do not establish production reliability percentages, generalized extraction accuracy, real supplier compliance or actual email delivery.

## Newer-feature audit

| Feature | Implemented use | Claim boundary |
| --- | --- | --- |
| `ai_parse_document` | Binary document parsing via SQL. | No explicit parser version/options; no automatic CAD reconstruction. |
| `ai_extract` | `ai_extract(text, array(labels...))`, batched by label set. | Not rich-schema or built-in citation/confidence APIs; validation and provenance are application logic. |
| Lakebase | Durable Postgres state, graph checkpoints, credential-refresh support. | No demonstrated branching, scale-to-zero or autoscaling-control workflow. |
| Unity Catalog | Volume storage and catalog/schema-scoped Delta tables. | No claim of automatic lineage or a complete governance deployment. |
| Delta CDF | Enabled in the evidence-table DDL. | No active Vector Search sync/index consumer. |
| MLflow 3 | Optional spans/autologging and recorded evaluation. | Current public tracing disabled. |
| Linkup standard agentic search | Actual `/v1/search`, `standard`, `searchResults`. | No observed internal Linkup planning trace; no Deep/Flash/Fast mode claims. |
| Linkup Fetch/Research/Tasks/Extract or structured output | Not called in this build. | Future possibilities only. |
| Databricks Agent Bricks, Genie, Lakeflow Jobs | Not the implemented runtime/query/job path. | Vercel Queues and application services/LangGraph own execution. |

The API comparison used official [Databricks parsing](https://docs.databricks.com/aws/en/sql/language-manual/functions/ai_parse_document), [extraction](https://docs.databricks.com/aws/en/sql/language-manual/functions/ai_extract), [Lakebase](https://docs.databricks.com/aws/en/oltp/projects) and [Linkup Search](https://docs.linkup.so/pages/documentation/endpoints/search/overview) documentation. This establishes feature names and interfaces, not feature release dates.

## Track positioning

The [hackathon rules](https://imperial-ai-hackathon.devpost.com/rules) emphasize working autonomous tasks and technical depth, and judge bounties on the centrality of the partner tool. The supported positioning is therefore:

> Linkup discovers supplier evidence; Databricks makes it structured and durable; Re::Source turns it into a traceable sourcing action.

Demonstrate those dependencies on screen, especially a real live investigation. The prepared ZIP experience alone cannot establish live Linkup or AI Function usage.
