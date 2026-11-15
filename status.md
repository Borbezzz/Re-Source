# Re-Source — build status

Living handoff document. **Update it at every milestone.** Any coding agent should be able to resume from this file plus [`decisions.md`](decisions.md), [`architecture.md`](architecture.md) and [`interface.md`](interface.md).

- Last updated: 2026-11-15, by Bede’s Claude (local UI revamp; see below). Previously 2026-11-14, by Yixin’s Astra and Bede’s Codex.
- Active frontend/migration branch: `codex/jet-engine-frontend`, based on PR #6. Issue #7.
- Spec: [`PRD.md`](PRD.md) v1.2
- Branch: `5-backend-recovery`, PR https://github.com/Borbezzz/Re-Source/pull/6 (closes #5). Base `main@ddceb8e`.
- Frontend delegation posted to the board: https://github.com/Borbezzz/Re-Source/issues/1#issuecomment-6880396173

## Local UI revamp — Re::Source Studio (2026-11-15, Bede's Claude) — LOCAL ONLY, not deployed

Branch `bede/ui-revamp` (from `main@ad32217`), uncommitted. Implements the approved `frontend improve/` flow (screens 01–10) on the Mechanica package from `blueprint input/`, with a new gradient brand.

- **Run locally:** `.claude/launch.json` → backend `uvicorn … --port 8010` (port 8000 is used by another local project) and frontend `RS_API_TARGET=http://127.0.0.1:8010 npm run dev` (vite proxy target is now env-configurable). Open http://localhost:5173 → "Explore a sample assembly".
- **New app shell:** `#home` renders `frontend/src/studio/Studio.tsx` (one persistent spatial workspace). Old pages stay reachable via "Saved work" (`#investigations`, `#new`, `#project/…`) and now use the new logo.
- **Real processing:** `studio/data/package.ts` unzips the package in-browser (fflate), verifies every SHA-256 against `manifest.json`, resolves component node IDs inside the GLB JSON chunk and links requirement sets. The backend profile is chosen by verified `packageId`, never filename.
- **Backend profile:** new `data/demo-products/turbofan.json` (demo_id `turbofan`): 3 parts mapped to GLB stable IDs, requirements quoted from a generated spec document, 21 fictional sample offers. The journey uses the real `/api/v1/products` contract: create → confirm parts → investigate (demo) → select → package (RFQ) → approve → simulate (receipt).
- **Checks:** `studio/data/checks.ts` + `sites.ts` evaluate six per-candidate checks (identity/revision/condition, site, documents, availability, arrival vs required date, commercial) from fictional site-evidence fixtures joined to backend offers. Pins, counts (12 / 5 excluded / 4 awaiting / 3 eligible) and ranking derive from one state. The disruption is a labelled simulated signal (Derby dispatch hold) that reruns arrival and availability only, shows before/after and invalidates approval.
- **3D:** `studio/scene/EngineCanvas.tsx` renders `public/models/mechanica-turbofan.glb`: a thermal wireframe scan during processing, a solid sweep on confirmation, an intake-preserving cutaway, explode, per-part framing, opaque context isolation, a thermal Fresnel rim on the selection, and remove/insert reassembly. Art direction applied from an Astra (`gpt-6-astra`) review: `frontend/design/astra-review/astra-3d-review.md`.
- **Brand:** new rotor logo (8 crescent blades around a `::` hub), generated with `gpt-image-2.5-flare` then rebuilt as exact SVG geometry (`studio/brand/Logo.tsx`, `public/favicon.svg`, concepts in `frontend/design/logo-concepts/`). Thermal gradient `#38BDF8 → #8B5CF6 → #EC4899 → #FB923C` (cool intake to hot exhaust) on charcoal; tokens in `studio/studio.css`.
- **Parallel work:** another local agent added `studio/flow/` (an n8n-style "Sourcing agent" workflow panel) and wired it into `Studio.tsx`.
- **Workflow split is now side by side (at the user's request, 2026-11-15):** on screens ≥1100px wide, "Split" puts the scene on the left and a resizable workflow column on the right. That column has a step rail, a node canvas whose camera glides to the live step, a "Stage output" pane (the focused step's fields, in/out item counts, and that step's own events) and the execution log. Clicking a step or node pins it ("Back to live" or Esc returns). Any new live step unpins. Below 1100px it stays docked at the bottom. The scene's panels compact through `@container rs-studio` rules in `studio.css`. Step logic is in `flow/model.ts` (`STEPS`, `liveStep`, `stepGroup`).
- **Verified in browser (1440×900 + 375×812):** the full sample journey from intake to reassembly against the local backend, all three component cases, disruption and rerank, approve/send/receipt. `tsc` and `vite build` pass. Not run: Playwright e2e, accessibility audit, a real non-sample package upload.
- **Gaps:** the site-evidence fixtures are frontend-side; checks are deterministic over demo evidence, not live research. The Mechanica injector is a simplified shape. In dev, scene preparation is slow when the browser tab is hidden (timer throttling). Supplier messages and orders are simulated.

## V2 backend progress (2026-11-14)

Issue [#11](https://github.com/Borbezzz/Re-Source/issues/11) remains open. PR [#15](https://github.com/Borbezzz/Re-Source/pull/15) merged at `b375c1a`: atomic, idempotent multi-component batch creation and per-component status/event links for the current engine demo; requested mode is preserved in durable jobs. Backend tests: 156 passed, 4 skipped; Vercel preview checks and production deployment passed; the live batch endpoint returns validation errors as expected and the homepage and health endpoint returned HTTP 200. PR [#14](https://github.com/Borbezzz/Re-Source/pull/14) fixed dispatch before outer transaction commit.

A follow-up adds replayable typed catalogue supplier findings with component/candidate/supplier/site IDs, candidate evidence references, and explicitly sourced representative fixture locations; unattributed coordinates are withheld. The complete offline backend suite passed 178 tests (4 skipped); connected Databricks data-layer tests passed 9/9. A gated assembly profile preview exposes the agreed toy-car mapping with source-required requirements; toy-car investigations are unavailable, and requests for an unloaded run manifest are rejected rather than silently using engine rules. New runs and their manifest-only fingerprints are committed atomically with case setup; a fail-closed resolver is available but not yet wired into existing workflows, and legacy runs need a migration strategy. The fingerprint does not cover rules or evidence. Explicit `COMPONENT_ID` document sections now scope draft extraction and preserve source lines; detected ambiguity stays unknown, but arbitrary unstructured blueprints are not reliably segmented. Reviewed overlays retain fields, unknowns, units when unambiguous, and source/reviewer provenance; only part identity is currently checked for compatibility. Remaining: per-run non-engine catalog/rule isolation and investigations, broader reviewed source-linked multi-component requirements, richer structured task/location progress and relevant connected integration checks. Existing batch status only exposes task summaries and per-case SSE; do not present it as the complete v2 progress contract. Astra owns frontend and presentation assets. The `CaseView.stale_reasons` contract now describes the emitted change and resumed-monitoring objects; gating behavior is unchanged. Coordinate on the [agent board](https://github.com/Borbezzz/Re-Source/issues/1).

## Testing handoff (2026-11-14)

Start testing the seeded engine flow at https://resource-borbez2s-projects.vercel.app: select the fuel nozzle, allow the investigation to complete, introduce the port closure, review D2, select Offer B, and run the explicitly simulated approval/receipt and repair visualization. Seeded suppliers, locations, costs and events are synthetic. This flow was exercised in a browser through restored visualization; a warning display issue was reported to Astra, who said the frontend fix is in progress. Approval-pack sign-offs remain completion tasks; simulation does not constitute operational approval or a real order.

The toy-car model/profile may be previewed but its investigations are disabled: run-scoped catalog/rule isolation and source-reviewed requirements still need implementation. Explicit component sections support separate extraction drafts, but arbitrary blueprint segmentation and engineering compatibility evaluation remain incomplete. Consult the agent board for the frontend handoff and deployment status.

## Live seeded browser demo (2026-11-14)

On the public Vercel app, a fresh synthetic run completed D1 (Offer A), then the Rotterdam port closure triggered D2 (Offer B). The selected option produced a reviewed demo pack and simulated receipt, followed by install and restore visualization. The pack showed five outstanding sign-off completion tasks: this was a simulation, not operational approval or a real order/filing. During reassessment the UI rendered `[object Object]` in the warning; Astra reported a frontend fix and PR #21 corrected the backend contract. The broader non-engine v2 workflow remains incomplete.

## Public deployment update (2026-11-14)

Yixin superseded Databricks Apps hosting: **Vercel frontend AND API**; Databricks remains data/platform. Verified project: `borbez2s-projects/resource`. Public URL: https://resource-borbez2s-projects.vercel.app . Core flows passed on **81b8661**; diagnostics update **bd74f63** additionally reports the active Lakebase/Postgres store and Vercel/checkpointer accurately in live readiness. Both Python HTTP and private queue subscriber builds pass. The parent configured 24 Production variables using the existing verified Databricks PAT/Lakebase identity. Anonymous connected intake, queue research, comparison, approval/simulated receipt, reassessment, visitor isolation and SSE reconnect pass. Preview has no production credentials. See `deploy/vercel/README.md`. Do not redeploy the old App as the frontend delivery target.

Frontend is implemented with typed commands/SSE, intake v1.1, cited review, real procedural/loaded meshes, reversible Anime.js motion, supplier/map/evidence comparison and versioned approval/simulated receipts. Blueprint generation and full uploaded-spec compatibility evaluation remain explicit gaps.

## Retained Databricks deployment (historical)

- **Databricks App `resource` is RUNNING:** https://resource-7474650863346302.aws.databricksapps.com (OAuth: open it while signed in to the workspace; `/docs` for the API). Operational store on **Lakebase `resource-ops`**; Delta `rs_*`, `ai_extract`, MLflow, Linkup, Companies House and OpenAI wired through App resources (D-017, D-018).
- The private App is on snapshot `01f1e055423315c78a9fa2f49f0f029c` (SUCCEEDED). It includes intake and mesh validation v1.1 and stamps confirmed draft versions on decisions. The App principal has READ VOLUME and WRITE VOLUME on `workspace.resource.rs_uploads`. The deployed HTTP demo still needs a signed-in browser session.
- Redeploy the private App with `uv run --project backend python deploy/databricks/redeploy.py` from the repo root. It includes `frontend/dist` if built locally. See [deployment instructions](deploy/databricks/README.md).
- Public hosting moved to Vercel under Yixin's direction, with Databricks staying the data platform. Astra's staged homepage returned HTTP 200; `/api/v1/health` returned HTTP 500 while the server variables were pending. [Board update](https://github.com/Borbezzz/Re-Source/issues/1#issuecomment-6881881723)

## Frontend/migration verification

See [`docs/verification/frontend-vercel.md`](docs/verification/frontend-vercel.md): **140 backend tests passed (4 skipped)**, 9 frontend invariant tests, local browser checks and connected public flows pass. Real 3D renders before the API connects, with seven selectable modules and reversible scroll. Slow initial connection preserves selected source files; intake review resumes via `#sources`. Live forced-worker-termination testing remains unperformed; provider generation and full uploaded-spec rule evaluation remain gaps.

## Current gate (PRD §15)

Backend gates 1–5 are implemented and verified locally (seeded mode, live Databricks/OpenAI/Linkup/MLflow).
Gate 6 (integration/QA) is running iteratively. The **frontend is delegated** to Borbezzz's OpenAI agent (GPT-6 Astra + GPT Image 2.5,
Blender/Unity allowed for 3D asset generation); see `docs/handoff/frontend-brief-astra.md`. Bede has allowed that agent to simplify
the demo flow/inputs and to change the backend when the demo needs it (keep `interface.md`, contracts and tests green).

## Verified so far

| What | How | Result |
|---|---|---|
| Full test suite | `cd backend && RS_SKIP_DATABRICKS=1 uv run --locked pytest ../tests -q`; then `uv run --locked pytest ../tests/integration/test_databricks_layer.py -q` | **137 passed, 4 skipped** offline after the readiness diagnostics fix. All 9 Databricks integration tests passed separately, including the 4 live tests. |
| HTTP demo (local Uvicorn, isolated seeded run) | Commands and SSE over a local socket | D1 Offer A → Rotterdam signal → D2 Offer B; diff and SSE reconnect; selection → approved paperwork → simulated receipt → install/restore; upload → reviewed requirements → D3 with the confirmed version. Valid/invalid GLB and blueprint `provider_required` passed. |
| Primary D1 (seeded, live integrations) | HTTP + SSE flow against `uvicorn` | D1: A 85.79 > B 82.07 > C 49.96; PD pending, PE ineligible. `ai_extract` on the SQL warehouse, Linkup leads, OpenAI summaries, MLflow trace linked in events |
| Hero feature (AC-03) | `SIG-RTM-CLOSURE` | D2: B 82.07 > A 66.91 > C 49.96; A day 4→11, £48,000→£50,500; 1 check rerun, 46 reused; path NLRTM → R-RTM-HWC → Offer A → case-primary |
| Execution gate | select → documents → approve → submit → install/restore | CAA Form 1 MO + 145.A.42 acceptance + supplier approval; one receipt per operation; visual install/restore gated on the receipt |
| Responsiveness | measured locally (live Databricks/OpenAI/Linkup) | command ack <0.01 s; first progress event 1.2 s; **warm D1 7.8 s, signal → D2 5.6 s**; cold first extraction ≈100 s, now done once by the startup prewarm and cached by content hash (restart prewarm 3.6 s) |
| Databricks | `docs/verification/disc-04-capability-spike.md` | 16 `rs_*` Delta tables loaded (evidence hashes match the catalog); outbox → Delta projection works |
| MLflow evaluation | `tests/evaluations/run_eval.py` | run `2934d58d1e14432ca1f1753d1667f897`, all scorer means 1.000 (17 rows, 6 held out) |

## PRD acceptance matrix (§12)

✅ verified · 🟡 implemented, partially verified · ⬜ not verified (frontend or deployment pending)

| ID | Status | Where verified / notes |
|---|---|---|
| AC-01 | 🟡 | Real mesh/pin selection and case switching verified in public browser tests; all three mesh identities covered by frontend invariants. Full three-hotspot/refresh acceptance sweep remains. |
| AC-02 | ✅ | `test_ac02_ac03_*`, live HTTP flow (local, not yet on the deployed App). |
| AC-03 | ✅ | Same; diff with rerun/reused checks and impact path. |
| AC-04 | ✅ | `test_ac04_unrelated_duplicate_correction_retraction`. |
| AC-05 | ✅ | `test_ac05_evidence_change_invalidates_checks_and_documents` (SB Rev B → Offer C ineligible, selection + package stale, regenerated). |
| AC-06 | ✅ | `tests/unit/test_scheduler_ranking.py` (independent reference calculation). |
| AC-07 | ✅ | `tests/unit/test_rules.py` (missing Form 1, expired cert, wrong-site cert, conflicting part numbers, near-match revision). |
| AC-08 | ✅ | `test_ac08_gap_resolved_by_followup_and_budget_respected`. |
| AC-09 | ✅ | `test_ac09_stale_and_concurrent_acceptance` (stale decision, wrong hash, 3-way race → exactly one selection). |
| AC-10 | 🟡 | `test_ac10_*`, `tests/unit/test_documents.py`; HTML download verified over local HTTP. Public frontend pack generation/edit/approval invalidation/reapproval passed; public download acceptance sweep remains. |
| AC-11 | ✅ | `test_ac10_ac11_*`, `test_ac11_stale_package_cannot_be_submitted`. |
| AC-12 | 🟡 | `test_ac12_*` (checkpoint resume after simulated worker death, no duplicate decisions, ordered events). Not yet on a deployed worker. |
| AC-13 | ✅ | `test_ac13_secondary_cases_complete_full_workflow` (SA-1 BUY, SB-3 MAKE with CAA Form 1-21; SB-2 feasible-not-ready). |
| AC-14 | 🟡 | Backend visual state machine/prerequisites verified. Public scroll/reverse, selectable mesh and reduced-motion/direct controls pass; full receipt→install/restore visual acceptance sweep remains. |
| AC-15 | 🟡 | `tests/integration/test_databricks_layer.py`: exact-ID retrieval + Delta keyword search; AI Search not provisioned (recorded mode). |
| AC-16 | 🟡 | Fallbacks exist (ai_extract → OpenAI → structured parse; model → deterministic text; Linkup failure → recorded); cold start measured. Quota interruption not exercised. |
| AC-17 | ✅ | Public browser workflow has no page errors; mobile 390 px has no overflow, with source access, comparison and documents usable. Keyboard/direct and reduced-motion controls pass. |
| AC-18 | ✅ | `test_ac18_reset_creates_isolated_runs_with_same_outcome`. |
| AC-19 | ✅ | `test_ac19_newest_generation_wins_when_changes_overlap`. |
| AC-20 | ✅ | `test_ac20_barrier_blocks_commits_until_fanout_completes` (partial fan-out failure, barrier 409, idempotent retry). |
| AC-21 | ✅ | `test_ac21_active_change_before_open_clock_expiry_and_pause`. |
| AC-22 | ✅ | `test_ac22_template_change_guards_submission_and_regenerates` (template revision via gateway → stale package, 409 on submit, regenerated drafts, delayed generator cannot overwrite). |
| Contracts | ✅ | `tests/integration/test_contracts.py` validates real payloads against the published models. |

## Blockers / waiting on humans

0. **Repo description** — setting it was blocked (repo settings belong to the lead). Proposed: "Re-Source: aerospace recovery agent — finds, verifies and re-plans jet-engine part replacements (BUY/MAKE) with continuous risk monitoring, UK CAA paperwork and a 3D engine view. FastAPI + LangGraph + Databricks."
1. **Resolved:** Yixin assigned `frontend/**` and confirmed OpenAI D-001; later authorized the Vercel runtime migration.
2. **AI Search** endpoint not provisioned (keyword retrieval in use). Lakebase is provisioned (D-017).
3. **Intake scope:** confirmation changes the part identity and the decision's `requirements_version`. Other extracted engineering fields are for manual review. Blueprint mesh jobs report `provider_required` until a generation provider is connected.
4. **Private App:** Databricks App access requires workspace sign-in and an appropriate CAN_USE grant. Public Vercel does not depend on that App; its connected demo is verified.
5. **DISC-03:** exact current issue numbers of the CAA Form 1 PDFs and CAA Form 60 unconfirmed.

## Next steps

1. Frontend (Borbezzz's agent) against `interface.md` + `contracts/generated-types/api.ts`.
2. Public Vercel connected demo is deployed and verified. Follow-up resilience testing should force worker termination/redelivery and API cache replacement. Bede handles optional signed-in verification on the retained private App.
3. Lakebase is required for the serverless public runtime. AI Search remains optional; generation provider and full uploaded-spec rule evaluation remain open.
4. Re-run the §12 QA pass after the frontend lands (AC-01/14/17) and record results in `docs/verification/`.

## How to resume

```bash
cd /Users/bedelau/Desktop/ReSource/backend
uv sync                                          # Python 3.12 env from uv.lock
cp ../.env.example ../.env                       # only if .env is missing; fill values (never commit)
uv run python ../data/fixtures/build_seed.py     # regenerate seed-v1 fixtures (deterministic)
uv run python scripts/export_contracts.py        # regenerate contracts/schemas, openapi, TS types
uv run uvicorn recovery.api.app:app --port 8000  # BFF + SSE (prewarms extraction cache at startup)
RS_SKIP_DATABRICKS=1 uv run pytest ../tests -q   # full suite offline
uv run python ../data/ingestion/load_delta.py    # (re)load fixtures into workspace.resource.rs_* Delta tables
uv run python ../tests/evaluations/run_eval.py   # MLflow code-scorer evaluation
```

Flags: `RS_PACING_MS=0` (no presentation pacing), `RS_MODEL_ENABLED=false`, `RS_DATABRICKS_ENABLED=false`, `RS_EXTRACTION_BACKEND=structured`, `RS_PREWARM=false`.

Demo quick path (seeded): `POST /api/v1/cases/case-primary/investigations` → wait `decision.created` → `POST /api/v1/scenario-runs/{run}/signals {"fixture_signal_id":"SIG-RTM-CLOSURE"}` → wait `decision.updated` → `POST /cases/case-primary/selections` → `PATCH /documents/{package_id} {"review_action":"approve"}` → `POST /cases/case-primary/simulated-submissions` → `POST /cases/case-primary/visual-actions {"action":"install"}` then `restore`. Reset: `POST /api/v1/scenario-runs`.

Board: `tools/board read -n 20`; `tools/board post "[Bede's Claude] ..."`. Issue #1 is **public**: never paste keys.

## Change log

- 2026-11-14: Repo cloned; PRD read; Databricks probed; domain core, fixtures, rules, templates, store, adapters, graph, services, API written; 4 subagent forks delivered documents/submission, Databricks layer, tests/evaluations, handoff docs; full local verification; contracts exported with typed responses; frontend brief updated with Blender/Unity + change permissions.
