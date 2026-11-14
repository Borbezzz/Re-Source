# Deploying to the Databricks App `resource`

The workspace already has an App named `resource` (compute stopped, no deployment) with resources:
`sql-warehouse` (CAN_USE), `linkup-key` and `companies-house-key` (secrets in scope `resource`), and
`agent-traces` (MLflow experiment, CAN_EDIT). `app.yaml` and `requirements.txt` at the repo root are the
App entrypoint and dependencies.

**Status 2026-11-14: deployed and RUNNING** (steps 1–3 done: secret `resource/openai_key` + App resource `openai-key`, UC grants for the App service principal, Lakebase instance `resource-ops` + App resource `lakebase`). Without the Databricks CLI, sync with the SDK (`WorkspaceClient().workspace.upload(...)`) and deploy via `POST /api/2.0/apps/resource/deployments`.

Original checklist:
1. Add a secret `openai_key` to scope `resource` and an App resource named `openai-key` pointing at it
   (the app's runtime OpenAI key; never commit it).
2. Grant the App service principal `app-3eov8h resource` SELECT/MODIFY on `workspace.resource.rs_*` and USE on the
   catalog/schema (projection writes and evidence reads), and CAN_USE on the warehouse (already granted).
3. Optional, for durability across restarts: provision Lakebase and set `RS_OPERATIONAL_DB_URL` to its Postgres URL
   (the LangGraph checkpointer then uses Postgres too). Without it, operational state lives in `/tmp` and resets when
   the App restarts.
4. Build the frontend (`frontend/dist`); the BFF mounts it at `/`.

From the repository root, sync the runtime files and redeploy with the SDK. It uses
your normal Databricks credentials or the local, ignored `.env`. If
`frontend/dist/index.html` exists, the static build is included. Run with
`--dry-run` to preview the file list.

```bash
uv run --project backend python deploy/databricks/redeploy.py
```

Verify: `GET https://resource-7474650863346302.aws.databricksapps.com/api/v1/readiness` (OAuth-protected).
