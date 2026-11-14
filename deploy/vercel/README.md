# Public Vercel deployment

Yixin authorized Vercel for **frontend and API**, replacing Databricks Apps hosting (D-019). Databricks remains the data platform. Do not delete or proxy the public browser through the existing private App.

Verified target: Vercel account `borbez2`, team `borbez2s-projects` (`team_gDiuAkntLhXx0IvmLnFwyRZV`), project `resource` (`prj_mZXdvRTrUVXyVzoUs0lDvQyjlzrm`). CLI 65.16.0. Existing unrelated projects were not changed. Services is beta; both API and subscriber builds have been verified on this project.

## Server configuration

Set Production and Preview variables in Vercel project settings. Never put these in `VITE_*`, client code, git, issue comments or screenshots. Do not copy local `.env` into a deployment.

| Variable | Purpose |
|---|---|
| `DATABRICKS_HOST` | Existing workspace URL |
| `DATABRICKS_CLIENT_ID`, `DATABRICKS_CLIENT_SECRET` | Dedicated approved service principal, OAuth M2M |
| `PGHOST`, `PGUSER`, `PGDATABASE` | Existing `resource-ops` Lakebase connection; PGUSER must be the authorized database role |
| `PGPORT`, `PGSSLMODE` | Optional; 5432 and require by default |
| `RS_USE_LAKEBASE` | Set 1 explicitly; Vercel with PGHOST also selects it by default |
| `RS_LAKEBASE_INSTANCE`, `RS_LAKEBASE_SCHEMA` | Defaults resource-ops, resource_ops |
| `RS_WAREHOUSE_ID` | Existing SQL warehouse; derives HTTP path |
| `OPENAI_API_KEY`, `OPENAI_MODEL` | Runtime model credentials; model defaults to gpt-5.4-mini |
| `LINKUP_API_KEY`, `COMPANIES_HOUSE_API_KEY` | Live public research adapters |
| `MLFLOW_TRACKING_URI`, `MLFLOW_EXPERIMENT_ID` | Optional approved tracing destination |

The service principal needs Lakebase connection/schema/table access, warehouse use, UC catalog/schema/table permissions, and READ/WRITE VOLUME on `workspace.resource.rs_uploads`. Existing App identity/grants do not automatically transfer. OAuth passwords are minted and refreshed server-side. Missing Lakebase fails startup rather than silently storing state in ephemeral SQLite.

Vercel defaults: `RS_PUBLIC_DEMO=1`, `RS_JOB_BACKEND=vercel`, `RS_PREWARM=0`, `RS_VAR_DIR=/tmp/resource`, `RS_SSE_MAX_SECONDS=50`. The job queue uses the deployment's Vercel OIDC credential, not a client key. No cron/polling daemon is required. Local development uses threads/SQLite unless explicitly configured otherwise.

## Build and deploy

From the repository root:

```sh
npx --yes vercel@65.16.0 deploy --scope borbez2s-projects --project resource --prod --skip-domain --yes --no-wait --json
npx --yes vercel@65.16.0 inspect <deployment-url> --scope borbez2s-projects
```

The first command stages production without assigning the normal production domains. After connected verification, promote that exact deployment with the CLI. Current project Vercel Authentication was disabled under the lead's explicit public-access requirement; anonymous requests must not rely on a bypass token.

`vercel.json` builds `frontend/` with Vite and the root `pyproject.toml` with Python. The latter declares both `app:app` and `queue_worker`. Inspection must show **two Python functions**, including `_py_subscribers/queue__worker`. `.vercelignore` excludes all `.env*`, virtualenvs, caches, screenshots and local runtime files. The generated frontend has no server credentials.

## Runtime and limits

- API writes, queue job payloads, event cursors and LangGraph checkpoints live in Lakebase. The queue carries only job IDs. A Postgres advisory lock plus completed-job record prevents concurrent duplicate execution. Generation/job intent writes share a transaction. A request retry repairs committed intents whose queue publication failed. A cold API instance never declares another active worker interrupted.
- The private subscriber has three concurrent deliveries, five attempts and a 15-second retry delay. Each function has a 300-second budget. A terminated generation resumes its persisted graph checkpoint on redelivery. After exhausted attempts, inspect the queue and case state and replay deliberately; no claim of unlimited retries. External effects remain idempotent outbox operations.
- SSE checks persisted events, not only process-local notifications. It ends after 50 seconds; EventSource reconnects with the last sequence ID. The browser's run/case filters suppress stale events.
- Uploads are limited to 4 MB to fit the function request body. A serverless upload is acknowledged only after UC mirroring. `/tmp` caches may disappear safely. Larger assets need a direct durable-upload contract, not an increased in-code limit.
- An opaque HttpOnly cookie scopes anonymous runs, uploads and manifests. No Databricks forwarded-user header is trusted. Draft review actors are explicitly unverified demo visitors. Clearing the cookie creates a new visitor; it is not a recoverable account.
- Blueprint jobs return `provider_required` until an actual generation adapter exists. Uploaded material/dimensions/tolerances/certification comparisons remain manual-review unknowns. No geometry or simulated receipt provides engineering approval.

## Verification status and release gate

Local automated coverage: typed/idempotent commands, SSE replay and case isolation, source/mesh guards, intake extraction review/reload, supplier evidence, versioned draft approval invalidation, simulated receipts, mobile/reduced-motion, reversible scroll, D1→D2 disruption. Runtime regressions cover two anonymous visitors, replay/upload isolation, failed queue publication retry, duplicate completion, cross-instance persisted SSE and rejection of serverless SQLite.

Vercel build verified: frontend, FastAPI and private queue subscriber. **Not yet verified:** authenticated server-to-Lakebase access, real queue redelivery/checkpoint restart, durable upload across instances, and complete anonymous public browser flow. Runtime variables were absent at the last check and Yixin is configuring them. Build success is not a tested public application.

Before promoting, use a fresh browser context (no cookies initially, no Vercel bypass) to load `/`, create an anonymous run, upload/review sources, select a part, watch real queue events/SSE reconnect, compare supplier evidence, approve/edit/reapprove a draft, simulate submission, and reload. A second fresh context must not read the first visitor's run/upload. Confirm that the first visitor's state survives a new API invocation and that queue consumers use Postgres checkpoints.

Official references: [Services](https://vercel.com/docs/services), [service configuration](https://vercel.com/docs/services/config-reference), [FastAPI](https://vercel.com/docs/frameworks/backend/fastapi), [Python queue consumers](https://vercel.com/kb/guide/python-and-vercel-queues), [function limits](https://vercel.com/docs/functions/limitations).
