# Deploying to the Databricks App `resource`

The workspace already has an App named `resource` (compute stopped, no deployment) with resources:
`sql-warehouse` (CAN_USE), `linkup-key` and `companies-house-key` (secrets in scope `resource`), and
`agent-traces` (MLflow experiment, CAN_EDIT). `app.yaml` and `requirements.txt` at the repo root are the
App entrypoint and dependencies.

Before the first deployment (needs workspace-owner approval — team lead):
1. Add a secret `openai_key` to scope `resource` and an App resource named `openai-key` pointing at it
   (the app's runtime OpenAI key; never commit it).
2. Grant the App service principal `app-3eov8h resource` SELECT/MODIFY on `workspace.resource.rs_*` and USE on the
   catalog/schema (projection writes and evidence reads), and CAN_USE on the warehouse (already granted).
3. Optional, for durability across restarts: provision Lakebase and set `RS_OPERATIONAL_DB_URL` to its Postgres URL
   (the LangGraph checkpointer then uses Postgres too). Without it, operational state lives in `/tmp` and resets when
   the App restarts.
4. Build the frontend (`frontend/dist`); the BFF mounts it at `/`.

Deploy (Databricks CLI ≥ 0.250):

```bash
databricks sync . /Workspace/Shared/ReSource/app-src --exclude-from .gitignore
databricks apps deploy resource --source-code-path /Workspace/Shared/ReSource/app-src
databricks apps start resource
```

Verify: `GET https://resource-7474650863346302.aws.databricksapps.com/api/v1/readiness` (OAuth-protected).
