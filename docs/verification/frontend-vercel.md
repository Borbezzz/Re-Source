# Frontend and Vercel verification — 2026-11-14

Branch: `codex/jet-engine-frontend`, based on backend PR #6 at `5c4c79f`.

## Verified locally

- Backend: `PYTHON_DOTENV_DISABLED=1 uv run pytest ../tests -q` → **138 passed, 4 skipped**. Added deployment regressions cover anonymous run/upload/replay boundaries, queue publication retry and duplicate suppression, persisted events from another bus, and refusal of ephemeral SQLite on Vercel.
- Frontend: `npm run build` and `npm test` → production build succeeds, **9 tests pass**. Three.js and the supplier map are lazy chunks; their sizes still trigger Vite's advisory warning.
- Browser: **4 Playwright flows pass**, first in local threaded mode and again with `RS_PUBLIC_DEMO=1`. Covers intake cited extraction/edit/confirm/reload/provider-required, actual mesh/pin selection, evidence dialog, supplier comparison, draft approval invalidation/reapproval/simulated receipt, reduced-motion/mobile controls, scroll forward/reverse, D1→D2 and case isolation. The extended intake test also passes real GLB upload, source-review guard, activation, binary rendering and part selection; it caught and fixed a stale event refresh replacing the current job.
- Fresh anonymous-mode testing found and fixed development proxy origin rewriting. HTTP mutation origin checks now work through Vite without weakening the backend check.
- Generated contracts refreshed. Payload schemas are unchanged; the fallback HTML root is excluded from OpenAPI so generated API types are independent of whether `frontend/dist` exists.
- Figma screens and tokens exist in file `o4G1HFAyQybcPuBG1nV2lL`; node ledger in `frontend/design/figma-ledger.json`.
- Fresh Impeccable finish review used the supplied degraded reviewer definition in a separate agent because the named packaged reviewer was unavailable. Verdict **ship** covers its five scored fixes: scroll reversal, seed provenance, separated procedural part presentation, visible mobile table-scroll affordance, and 4 MB upload copy. The QUALITY BAR card was unavailable, so this is not a whole-surface ceiling certification. Raster provenance scan: 1 raster, 0 missing.

## Verified on Vercel

Verified team/project `borbez2s-projects/resource`. Deployment builds include both `services/backend/fastapi` and `services/backend/_py_subscribers/queue__worker`. Staged production `resource-dz519okz3-borbez2s-projects.vercel.app` returned HTTP 200 at `/` with ordinary curl, no cookies or deployment bypass token. Vercel Authentication is disabled for this explicitly public project. Later staged builds carry current source; none is promoted as a fully working product yet.

## Not yet verified

Vercel server variables were absent at last inspection; Yixin chose to configure them. API startup therefore fails closed rather than fall back to SQLite. A public frontend 200 is **not** full deployment success. Remaining connected checks: M2M/Lakebase grants, queue delivery and restart from Postgres checkpoint, UC upload read on another instance, SSE reconnect across instances, complete anonymous supplier/approval workflow, and cross-visitor denial on the public URL.

Blueprint-to-segmented-mesh provider is unconfigured. The backend honestly returns `provider_required`; this build does not solve PDF-to-engine reconstruction. Uploaded engineering fields beyond identity/revision remain manual-review unknowns. These are product gaps, separate from deployment credentials.
