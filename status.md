# Re-Source — build status

Living handoff document. **Update it at every milestone.** Any coding agent should be able to resume from this file plus [`decisions.md`](decisions.md), [`architecture.md`](architecture.md) and [`interface.md`](interface.md).

- Last updated: 2026-11-14, by Bede's Codex
- Spec: [`PRD.md`](PRD.md) v1.2
- Branch: `5-backend-recovery`, PR https://github.com/Borbezzz/Re-Source/pull/6 (closes #5). Base `main@ddceb8e`.
- Frontend delegation posted to the board: https://github.com/Borbezzz/Re-Source/issues/1#issuecomment-6880396173

## Deployment (2026-11-14)

- **Databricks App `resource` is RUNNING:** https://resource-7474650863346302.aws.databricksapps.com (OAuth: open it while signed in to the workspace; `/docs` for the API). Operational store on **Lakebase `resource-ops`**; Delta `rs_*`, `ai_extract`, MLflow, Linkup, Companies House and OpenAI wired through App resources (D-017, D-018).
- The private App is on snapshot `01f1e055423315c78a9fa2f49f0f029c` (SUCCEEDED). It includes intake and mesh validation v1.1 and stamps confirmed draft versions on decisions. The App principal has READ VOLUME and WRITE VOLUME on `workspace.resource.rs_uploads`. The deployed HTTP demo still needs a signed-in browser session.
- Redeploy the private App with `uv run --project backend python deploy/databricks/redeploy.py` from the repo root. It includes `frontend/dist` if built locally. See [deployment instructions](deploy/databricks/README.md).
- Public hosting moved to Vercel under Yixin's direction, with Databricks staying the data platform. Astra's staged homepage returned HTTP 200; `/api/v1/health` returned HTTP 500 while the server variables were pending. [Board update](https://github.com/Borbezzz/Re-Source/issues/1#issuecomment-6881881723)

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
| AC-01 | ⬜ | Frontend (delegated). Backend case isolation per run/case verified (AC-02/13 tests). |
| AC-02 | ✅ | `test_ac02_ac03_*`, live HTTP flow (local, not yet on the deployed App). |
| AC-03 | ✅ | Same; diff with rerun/reused checks and impact path. |
| AC-04 | ✅ | `test_ac04_unrelated_duplicate_correction_retraction`. |
| AC-05 | ✅ | `test_ac05_evidence_change_invalidates_checks_and_documents` (SB Rev B → Offer C ineligible, selection + package stale, regenerated). |
| AC-06 | ✅ | `tests/unit/test_scheduler_ranking.py` (independent reference calculation). |
| AC-07 | ✅ | `tests/unit/test_rules.py` (missing Form 1, expired cert, wrong-site cert, conflicting part numbers, near-match revision). |
| AC-08 | ✅ | `test_ac08_gap_resolved_by_followup_and_budget_respected`. |
| AC-09 | ✅ | `test_ac09_stale_and_concurrent_acceptance` (stale decision, wrong hash, 3-way race → exactly one selection). |
| AC-10 | 🟡 | `test_ac10_*`, `tests/unit/test_documents.py`; HTML download verified over HTTP. Frontend editing UI pending. |
| AC-11 | ✅ | `test_ac10_ac11_*`, `test_ac11_stale_package_cannot_be_submitted`. |
| AC-12 | 🟡 | `test_ac12_*` (checkpoint resume after simulated worker death, no duplicate decisions, ordered events). Not yet on a deployed worker. |
| AC-13 | ✅ | `test_ac13_secondary_cases_complete_full_workflow` (SA-1 BUY, SB-3 MAKE with CAA Form 1-21; SB-2 feasible-not-ready). |
| AC-14 | 🟡 | Backend visual state machine + prerequisites verified; animations are frontend. |
| AC-15 | 🟡 | `tests/integration/test_databricks_layer.py`: exact-ID retrieval + Delta keyword search; AI Search not provisioned (recorded mode). |
| AC-16 | 🟡 | Fallbacks exist (ai_extract → OpenAI → structured parse; model → deterministic text; Linkup failure → recorded); cold start measured. Quota interruption not exercised. |
| AC-17 | ⬜ | Frontend. |
| AC-18 | ✅ | `test_ac18_reset_creates_isolated_runs_with_same_outcome`. |
| AC-19 | ✅ | `test_ac19_newest_generation_wins_when_changes_overlap`. |
| AC-20 | ✅ | `test_ac20_barrier_blocks_commits_until_fanout_completes` (partial fan-out failure, barrier 409, idempotent retry). |
| AC-21 | ✅ | `test_ac21_active_change_before_open_clock_expiry_and_pause`. |
| AC-22 | ✅ | `test_ac22_template_change_guards_submission_and_regenerates` (template revision via gateway → stale package, 409 on submit, regenerated drafts, delayed generator cannot overwrite). |
| Contracts | ✅ | `tests/integration/test_contracts.py` validates real payloads against the published models. |

## Blockers / waiting on humans

0. **Repo description** — setting it was blocked (repo settings belong to the lead). Proposed: "Re-Source: aerospace recovery agent — finds, verifies and re-plans jet-engine part replacements (BUY/MAKE) with continuous risk monitoring, UK CAA paperwork and a 3D engine view. FastAPI + LangGraph + Databricks."
1. **Folder ownership + model provider** — @Borbezzz to confirm on the board (AGENTS.md: the lead assigns folders; D-001 OpenAI instead of Claude).
2. **AI Search** endpoint not provisioned (keyword retrieval in use). Lakebase is provisioned (D-017).
3. **Intake scope:** confirmation changes the part identity and the decision's `requirements_version`. Other extracted engineering fields are for manual review. Blueprint mesh jobs report `provider_required` until a generation provider is connected.
4. **Live demo:** the Databricks App requires browser sign-in. The public Vercel API and queue still need connected verification on Astra's deployment.
5. **DISC-03:** exact current issue numbers of the CAA Form 1 PDFs and CAA Form 60 unconfirmed.

## Next steps

1. Frontend (Borbezzz's agent) against `interface.md` + `contracts/generated-types/api.ts`.
2. Run the backend demo on the signed-in private App and coordinate with Astra on the connected Vercel demo.
3. Optional: AI Search endpoint for hybrid retrieval.
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
