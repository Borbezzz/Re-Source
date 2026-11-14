# Frontend and Vercel verification — 2026-11-14

Branch: `codex/jet-engine-frontend`, based on backend PR #6 at `c5b2b68` (including the confirmed requirements-version fix).

## Verified locally

- Backend: `PYTHON_DOTENV_DISABLED=1 RS_SKIP_DATABRICKS=1 uv run pytest ../tests -q` → **140 passed, 4 skipped**. Added deployment regressions cover anonymous run/upload/replay/activated-manifest boundaries, queue publication retry and duplicate suppression, persisted events from another bus, refusal of ephemeral SQLite on Vercel, and HTTP startup without remote tracing.
- Frontend: `npm run build` and `npm test` → production build succeeds, **9 tests pass**. Three.js and the supplier map are lazy chunks; their sizes still trigger Vite's advisory warning.
- Browser: **4 original Playwright flows pass**, first in local threaded mode and again with `RS_PUBLIC_DEMO=1`. Covers intake cited extraction/edit/confirm/reload/provider-required, actual mesh/pin selection, evidence dialog, supplier comparison, draft approval invalidation/reapproval/simulated receipt, reduced-motion/mobile controls, scroll forward/reverse, D1→D2 and case isolation. The extended intake test also passes real GLB upload, source-review guard, activation, binary rendering and part selection; it caught and fixed a stale event refresh replacing the current job.
- Fresh anonymous-mode testing found and fixed development proxy origin rewriting. HTTP mutation origin checks now work through Vite without weakening the backend check.
- Generated contracts refreshed. Payload schemas are unchanged; the fallback HTML root is excluded from OpenAPI so generated API types are independent of whether `frontend/dist` exists.
- Figma screens and tokens exist in file `o4G1HFAyQybcPuBG1nV2lL`; node ledger in `frontend/design/figma-ledger.json`.
- Fresh Impeccable finish review used the supplied degraded reviewer definition in a separate agent because the named packaged reviewer was unavailable. Verdict **ship** covers its five scored fixes: scroll reversal, seed provenance, separated procedural part presentation, visible mobile table-scroll affordance, and 4 MB upload copy. The QUALITY BAR card was unavailable, so this is not a whole-surface ceiling certification. Raster provenance scan: 1 raster, 0 missing.

## Verified on Vercel

Verified team/project `borbez2s-projects/resource`. Core connected browser checks passed on **81b8661** (`resource-lm0ngyhrs-borbez2s-projects.vercel.app`). The diagnostics-only update **bd74f63**, deployment **dpl_9gUX6tYPFGTr4y4tDUmZLMc2WJn5**, also passes anonymous detailed readiness. Public URL: https://resource-borbez2s-projects.vercel.app . Updated immutable URL: https://resource-fuq3iezev-borbez2s-projects.vercel.app . Builds include both `services/backend/fastapi` and `services/backend/_py_subscribers/queue__worker`. Tests use fresh anonymous browser contexts, ordinary requests and no bypass token.

| Connected check | Result / evidence |
|---|---|
| First paint and actual 3D | HTTP 200, one canvas; separation 0.000 → 0.452 → 1.000 → 0.000. Mobile 390 px has no page overflow. No page errors. Final screenshots: `/tmp/resource-visual-review/final/{assembled,mid,exploded,reverse,mobile}.png`. Parent independently verified the preceding visual-identical build. |
| API and persistent runtime | Health and readiness JSON return 200; readiness reports Lakebase Postgres, Postgres graph checkpoints and available OpenAI `gpt-5.4-mini`. Moving remote tracing out of HTTP startup resolved the observed public startup timeout. |
| Anonymous boundaries | Two fresh visitors get distinct runs. Owner upload survives reload; another visitor receives 404 for the run, upload content and replay source. Passed on `45a184a`, whose backend is identical to production `81b8661`. |
| SSE reconnect | Native EventSource reconnects after the bounded 50-second response with Last-Event-ID, then receives a new persisted event. Passed on the same backend. |
| Intake | Delayed initial engine connection preserves both selected files; explicit new run resets them. Full source upload → cited review → edit → confirm → truthful provider-required → reload passes. Synthetic segmented GLB upload/validation/source-review/activation renders real binary geometry and supports component selection. Both tests pass publicly (26 s and 2.4 min). |
| Queued sourcing and approval | Real queue delivery → supplier research/evidence/map comparison → selection → draft pack → approve → edit invalidates approval → reapprove → simulated receipt passes publicly (2.3 min). Runtime logs record successful OpenAI, Linkup and Databricks requests. No external RFQ was sent. |
| Reassessment | Port closure produces D2 and a decision diff; second-component investigation stays isolated; install/restore remain gated. Public test passes (2.1 min). |

The first cold supplier check exceeded the old 60-second assertion window. Connected tests now allow real provider/queue latency (180-second assertions, seven-minute total test budget); local checks retain their shorter limits. The initial intake test exposed a genuine remount race, fixed in `81b8661` with a delayed-response regression. Local and public runs use separate output directories when concurrent to preserve trace artifacts.

## Limits and remaining verification

Production uses the parent-configured PAT route; Preview has no production credentials. API startup fails closed rather than falling back to SQLite. Queue delivery and persisted SSE reconnect are verified, but **forced termination/redelivery of a live Vercel worker has not been exercised**. Checkpoint restart and duplicate suppression have local regression coverage. Upload mirroring and reload succeeded; the tests did not force an API instance replacement to prove a cache miss. SSE reconnect did not force placement on a different instance. No claim of chaos/failover certification is made.

Readiness descriptions were corrected by Bede in `2219a60`, integrated as `bd74f63`. Four regression tests, one contract test and seven Vercel runtime tests pass. Live anonymous JSON now reports `operational_store: Lakebase Postgres`, `lakebase: 1 instance(s); app uses Postgres`, and `agent_runtime: FastAPI BFF + LangGraph on Vercel, with postgres checkpointer`. The existing `agent_runtime.ok=false` means the optional Agent Bricks/AgentKit runtime is not used; it is not a failure of the configured LangGraph runtime. AI Search is unprovisioned and keyword retrieval is used. The prior full-suite count above predates these four added diagnostic tests; only the relevant 12 tests were rerun for this narrow change.

Blueprint-to-segmented-mesh provider is unconfigured. The backend honestly returns `provider_required`; this build does not solve PDF-to-engine reconstruction. Uploaded engineering fields beyond identity/revision remain manual-review unknowns. These are product gaps, separate from deployment credentials.


## Engine-first correction

User review replaced the upload-form/PNG first impression with an independent real 3D introduction. Local screenshots cover assembled, intermediate, exploded and reverse states, plus narrow-screen details. A browser regression aborts every API request and verifies the canvas, seven modules, disabled supplier actions, module selection, source upload access and mobile overflow. Source navigation now persists in the URL to preserve intake resume. These checks do not claim a working public API.

Historical production `resource-f66xoilk4-borbez2s-projects.vercel.app` built with configured credentials but health/readiness timed out. Startup logs reached MLflow initialization. `ff5b767` moved non-critical tracing to queue-worker initialization with a three-second wait limit and logged durable-service startup duration. Subsequent public health, readiness and connected flows pass; no database credential change was needed.
