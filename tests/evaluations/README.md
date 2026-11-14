# Domain evaluation (PRD §12.1)

Code scorers and independent labels for the deterministic Re-Source domain on the seeded fixture.

## Dataset

- **Version:** `seed-v1-domain-eval-1` (`expected_seed_v1.json`), fixture `seed-v1` (`data/fixtures/seed-v1`, all `synthetic_demo`).
- **Rows:** 17, of which 6 are marked `held_out` (evidence revision, clock expiry, signal correction and retraction, evidence impact, a second form). No prompts are tuned against any row: the scored path is deterministic code.
- **Label basis:** the labels are written from the PRD (§2.1 decision stories, §10 primary ranking fixture, FR-02/05/06/07/08/09/10) and from hand calculation of the FR-08 score `100 × (0.45 speed + 0.25 cost + 0.20 reliability + 0.10 resilience)` using `rules/ranking/default-v1.yaml`. They are not produced by running the ranking code. The unit tests (`tests/unit/test_scheduler_ranking.py`) hold a second, independent reference implementation of the schedule, cost and score.

| Kind | What is checked |
|---|---|
| `eligibility` | Mandatory-gate outcome per candidate (eligible / pending / ineligible), feasibility, citation integrity |
| `ranking` | Eligible order, scores (±0.005), finish day and landed GBP cost per candidate |
| `impact` | Offers and cases reached from a signal or an evidence version through relationship rows |
| `form_fields` | CAA Form 1 MO block values resolved from the template registry and validated facts |

## Scorers (`scorers.py`)

`mandatory_gate_correctness`, `unsupported_eligibility`, `citation_version_integrity`, `ranking_schedule_correctness`, `change_impact_correctness`, `duplicate_side_effects`, `form_field_accuracy`.

Each scorer exists in three forms:

- a pure `*_impl(outputs, expectations) -> (value, rationale)`
- a plain callable with the MLflow keyword signature
- an MLflow GenAI scorer that returns `Feedback`, from `mlflow_scorers()`

`test_scorers.py` checks that each one detects the failure it exists for.

`duplicate_side_effects` takes the receipts produced by a service run. This domain-only run does not evaluate it; the integration tests or a demo run should feed it receipts.

`form_field_accuracy` here scores the template mapping plus extraction. Feed it the DocumentService drafts in integration runs to score the populated drafts themselves.

## Run

```bash
cd backend
uv run pytest ../tests/unit ../tests/evaluations -q
uv run python ../tests/evaluations/run_eval.py --no-mlflow          # local only
uv run python ../tests/evaluations/run_eval.py                      # + MLflow run in MLFLOW_EXPERIMENT_ID
```

When `MLFLOW_TRACKING_URI`/`MLFLOW_EXPERIMENT_ID` are configured (in the gitignored `.env`), the runner logs a run with params, metrics, the full summary JSON and a GenAI evaluation (`mlflow.genai.evaluate`) with per-row assessments from the same code scorers.

Note: GenAI evaluation applies every scorer to every row. A scorer with no labels for a row returns 1.0 with the rationale "no … labels". The runner's own metrics apply only the relevant scorers per row kind.

## Recorded runs

| Date | Dataset | MLflow run | Result |
|---|---|---|---|
| 2026-11-14 | seed-v1-domain-eval-1 | `2934d58d1e14432ca1f1753d1667f897` (experiment 2648868221488633) | all scorer means 1.000, 17 rows, latency ≈0.8 s |

An earlier run, `964c2934f9724761b62f868734cc12d0`, had a payload bug in the runner: it stripped the known versions, so its GenAI citation metric reads 0.35. Disregard that run.

## Not covered here

- Signal version selection (latest version wins; retracted or expired signals are inactive) lives in `services/run_state.py` and needs the operational store, so integration tests must cover it.
- Coalescing, barriers and stale-decision 409s: integration/e2e (AC-09, AC-19 to AC-22).
- LLM explanation quality (LLM judge): supplementary. Not part of these code scorers.
