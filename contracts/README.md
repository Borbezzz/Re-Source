# contracts/

Generated, not hand-edited. The single schema source is `backend/recovery/domain/models.py` (Pydantic, `SCHEMA_VERSION`). See [`../interface.md`](../interface.md) for the human-readable contract (routes, events, state machines, demo mapping).

| Path | Content | Generator |
|---|---|---|
| `schemas/<Model>.json` | JSON Schema for each public model | `model.model_json_schema()` |
| `schemas/all.json` | Combined schema (`$defs` for every model, plus `x-event-types` and `x-enums`) | same |
| `openapi/openapi.json` | FastAPI OpenAPI 3 document for `/api/v1` | `recovery.api.app:app.openapi()` (written once the API module exists) |
| `generated-types/api.ts` | TypeScript types, plus `SCHEMA_VERSION`, `EVENT_TYPES` and `DomainEventType` | `openapi-typescript@7.4.4` when the OpenAPI file exists, otherwise `json-schema-to-typescript@15.0.2` over `all.json` |

## Regenerate

```bash
cd backend
uv run python scripts/export_contracts.py          # schemas + OpenAPI (if available) + TypeScript (needs Node/npx)
uv run python scripts/export_contracts.py --no-ts  # skip the TypeScript step
```

## Rules

1. Change the Pydantic model first, then regenerate. Never edit these files by hand.
2. Bump `SCHEMA_VERSION` for breaking changes. Events carry `schema_version`.
3. Update `interface.md` and post the change on the board (`tools/board post "[<human>'s <agent>] contract change: …"`) before frontend and backend work diverge (PRD §14).
4. The frontend imports types from `contracts/generated-types/api.ts` (or copies them into `frontend/src/api/` at build time). Do not fork the types.
