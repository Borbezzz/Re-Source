# Re-Source — build status

Living handoff document. **Update it at every milestone.** Any coding agent should be able to resume from this file plus [`decisions.md`](decisions.md), [`architecture.md`](architecture.md) and [`interface.md`](interface.md).

- Last updated: 2026-11-14 16:40 UTC, by Bede's Claude
- Spec: [`PRD.md`](PRD.md) v1.2
- Branch: work is on a feature branch with an open PR (see the board, issue #1). Base `main@ddceb8e`.

## Current gate (PRD §15)

Backend gates 1–5 are implemented and verified locally (seeded mode, live Databricks/OpenAI/Linkup/MLflow).
Gate 6 (integration/QA) is running iteratively. The **frontend is delegated** to Borbezzz's OpenAI agent (GPT-6 Astra + GPT Image 2.5,
Blender/Unity allowed for 3D asset generation); see `docs/handoff/frontend-brief-astra.md`. Bede has allowed that agent to simplify
the demo flow/inputs and to change the backend when the demo needs it (keep `interface.md`, contracts and tests green).

## Verified so far

| What | How | Result |
|---|---|---|
| Full test suite | `cd backend && RS_SKIP_DATABRICKS=1 uv run pytest ../tests -q` | **126 passed, 4 skipped** (the 4 need live Databricks; they pass with credentials) |
| Primary D1 (seeded, live integrations) | HTTP + SSE flow against `uvicorn` | D1: A 85.79 > B 82.07 > C 49.96; PD pending, PE ineligible. `ai_extract` on the SQL warehouse, Linkup leads, OpenAI summaries, MLflow trace linked in events |
| Hero feature (AC-03) | `SIG-RTM-CLOSURE` | D2: B 82.07 > A 66.91 > C 49.96; A day 4→11, £48,000→£50,500; 1 check rerun, 46 reused; path NLRTM → R-RTM-HWC → Offer A → case-primary |
| Execution gate | select → documents → approve → submit → install/restore | CAA Form 1 MO + 145.A.42 acceptance + supplier approval; one receipt per operation; visual install/restore gated on the receipt |
| Responsiveness | measured locally | command ack 0.01 s; first progress event 1.2 s; warm signal → D2 ≈ 8 s; cold D1 ≈ 86 s before prewarm (prewarm now caches all 68 documents at startup, ~100 s once) |
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
| AC-22 | 🟡 | Immutable versions, guarded publication and approved-hash checks tested; template-change race not yet tested. |
| Contracts | ✅ | `tests/integration/test_contracts.py` validates real payloads against the published models. |

## Blockers / waiting on humans

1. **Folder ownership + model provider** — @Borbezzz to confirm on the board (AGENTS.md: the lead assigns folders; D-001 OpenAI instead of Claude).
2. **Lakebase + AI Search provisioning** was denied by the permission system pending explicit approval (it creates resources in the lead's workspace). Without Lakebase the operational store is SQLite (durable locally; ephemeral in the Databricks App).
3. **Databricks App deployment** needs: an `openai-key` secret resource, grants for the App service principal on `rs_*`, and approval to start App compute. See `deploy/databricks/README.md`.
4. **DISC-03:** exact current issue numbers of the CAA Form 1 PDFs and CAA Form 60 unconfirmed.

## Next steps

1. Frontend (Borbezzz's agent) against `interface.md` + `contracts/generated-types/api.ts`.
2. Deploy the BFF + `frontend/dist` to the Databricks App `resource` once approvals land; run AC-02/12 on the deployed worker.
3. Optional: Lakebase for durable operational state; AI Search endpoint for hybrid retrieval.
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
