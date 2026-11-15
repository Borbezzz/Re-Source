# Re-Source — frontend ↔ backend interface contract

**Canonical source:** `backend/recovery/domain/models.py` (Pydantic, `SCHEMA_VERSION = "1.0"`). Generated artefacts:
- `contracts/schemas/*.json` and `contracts/schemas/all.json`: JSON Schema per model.
- `contracts/openapi/openapi.json`: FastAPI OpenAPI. It is written by `backend/scripts/export_contracts.py` once `recovery.api.app` exists.
- `contracts/generated-types/api.ts`: TypeScript types, plus the `EVENT_TYPES` and `SCHEMA_VERSION` constants.

Regenerate with `cd backend && uv run python scripts/export_contracts.py`. Contract changes need a version bump, a regeneration, an update to this file **and** a board post before dependent work diverges (PRD §14).

Model names below (e.g. `CaseView`) are the Pydantic/TS type names.

---

## 1. Conventions

- **Base URL:** `/api/v1`, served by the same origin as the frontend (the FastAPI BFF mounts `frontend/dist` at `/`). In local development the backend is `http://localhost:8000`; configure Vite's dev proxy for `/api` to point there.
- **IDs:** strings. Run, command and event IDs are UUIDs.
- **Timestamps:** UTC ISO-8601 with `Z`.
- **Money:** `Money {amount: "48000.00", currency: "GBP"}`. The amount is a **decimal string**, so never use float arithmetic on it in the UI.
- **Durations:** have explicit units (`Duration {value, unit: "days"|"hours"}`).
- **Mutations:** every mutation accepts an **`Idempotency-Key`** header (a UUID per user action; reuse it on retry). The body field `idempotency_key` is also accepted; the header wins. Reusing a key with a *different* payload returns `409 IDEMPOTENCY_CONFLICT`. Reusing it with the same payload returns the original response.
- **Start-like calls** (investigations) return **202** with `CommandAccepted` (`command_id`, `generation_id`, `events_url`). Synchronous changes return the committed revision.
- **Optimistic concurrency:** case mutations carry `expected_revision` (from `CaseView.revision`), and document patches carry `expected_version`.
- **Error envelope** (`ApiError`) on every non-2xx:
  ```json
  {"code": "STALE_DECISION", "message": "Decision D1 is no longer current", "retryable": false,
   "case_revision": 9, "details": {"current_decision_id": "dec-…", "latest_revision": 9}, "correlation_id": "c0b4…"}
  ```
  Status codes: `404 NOT_FOUND`, `409 STALE_DECISION` / `IDEMPOTENCY_CONFLICT` / `CHANGE_PENDING` / `VERSION_CONFLICT` / `NOT_READY`, `422 INVALID_INPUT`, `403` forbidden (team-only diagnostics), `503 DEPENDENCY_UNAVAILABLE` (`retryable: true`). A failed *run* is reported through events and case state, not through HTTP status.
- **Correlation:** send `X-Correlation-Id` (UUID) and the backend echoes it in errors, events and MLflow spans.
- **Run scoping:** `GET /cases/{case_id}` and the other case routes use the **current scenario run** by default. Pass `?run_id=` to read a previous run's history, which is read-only.

## 2. Routes

| Method & path | Request | Response | Notes |
|---|---|---|---|
| GET `/assemblies` | — | `AssemblyProfile[]` | Lists the current engine demo and configured assembly previews, including component-to-node mappings and `investigation_available`. |
| GET `/assemblies/{assembly_id}` | — | `AssemblyProfile` | Preview one profile. `toy-car-demo` has eight components, `requirements_status: source_required`, and `investigation_available: false`; its preview cannot launch engine investigations. |
| GET `/engines/{engine_id}` | — | `EngineView` | Manifest, component instances, case summaries for the current run, `scenario_run_id`, mode. `engine_id = engine-demo-001`. |
| GET `/cases/{case_id}` | `?run_id=` | `CaseView` | Current projection: state, revision, input revision, visual state, monitoring, current/initial decision IDs, `decision_labels` (`{"dec-…": "D1"}`), current selection/package/receipt, stale reasons (`{kind, summary, change_id?, change_ids?, affected_candidate_ids?}`), tasks, `event_cursor`, `events_url`, provenance (mode, fixture version, data origin). |
| POST `/cases/{case_id}/investigations` | `StartInvestigationRequest {expected_revision?, mode, idempotency_key?}` | **202** `CommandAccepted` | Starts or resumes. `status`: `accepted` / `already_running` / `duplicate`. |
| POST `/batches` | `BatchInvestigationRequest {assembly_id, component_ids, mode}`, required `Idempotency-Key` | **202** `BatchInvestigation` | Starts independent case investigations for distinct components in the current run. Current assembly ID is the engine's `engine_id`. All case starts commit together; each part has its own generation ID and case event URL. Identical keyed retries return the original response and `Idempotent-Replay: true`. Different payloads return 409. |
| GET `/batches/{batch_id}` | — | `BatchInvestigation` | Returns the original component mappings with current generation statuses and durable per-part task summaries. Each task can include the latest observed tool action/status/time and deduplicated evidence references from that task’s persisted events; absent activity stays null/empty. Public visitors can only read batches belonging to their own run. |
| GET `/cases/{case_id}/decisions` | — | `DecisionSnapshot[]` (summary fields) | History, newest first, with labels D1, D2, …; superseded results included with `status`. |
| GET `/cases/{case_id}/decisions/{decision_id}` | — | `DecisionSnapshot` | Immutable: `candidates: RankedCandidate[]`, `checks: CheckResult[]`, score breakdowns, plans, evidence refs, `evidence_hash` (required to accept). |
| GET `/cases/{case_id}/diff?from={id}&to={id}` | — | `DecisionDiff` | Trigger, `impact_paths`, changed fields, rank moves, rerun/reused check IDs, downstream invalidations, explanation. |
| POST `/scenario-runs` | `ScenarioRunRequest {mode, manifest_id, fixture_version, replay_source_run_id?}` | `ScenarioRunView` | Demo reset: a new isolated run namespace. The previous run's history is preserved read-only and its monitoring paused. `mode: replay` replays a recorded run with the "Replay" label. |
| GET `/scenario-runs/current` | — | `ScenarioRunView` | Includes `scenario_now` (scenario clock) and `case_map`. |
| GET `/scenario-runs/{run_id}/signals/catalog` | — | `{signals: [...], evidence_changes: [...]}` | Injectable seeded scenario signals (`fixture_id`, title, category, label "Scenario signal") and evidence changes, for the presenter control panel. |
| POST `/scenario-runs/{run_id}/signals` | `SignalInjectionRequest {fixture_signal_id \| signal}` | `SignalInjectionResult` | Uses the same normalised ingestion path as monitored signals. Idempotent; a duplicate returns `duplicate: true` with the original change. |
| POST `/scenario-runs/{run_id}/evidence-changes` | `EvidenceChangeRequest {fixture_evidence_change_id}` | `SignalInjectionResult` | For example `EVC-SB-0042-REVB` (a new SB revision supersedes the old one). |
| POST `/scenario-runs/{run_id}/clock` | `ClockAdvanceRequest {hours}` | `ClockState` | Seeded mode only: advances the scenario clock and executes due timers (effective/expiry transitions). |
| POST `/scenario-runs/{run_id}/template-changes` | `TemplateChangeRequest {template_id, revision, note}` | `SignalInjectionResult` | Template/applicability revision through the same invalidation gateway: current packages using the template go stale, submission is blocked, drafts regenerate for the still-current selection (FR-13, AC-22). |
| GET `/scenario-runs/{run_id}/signal-sources` | — | list | Monitored signal sources with polling policy, health and freshness (FR-10). |
| POST `/scenario-runs/{run_id}/signal-sources/linkup-news/poll?ingest=false` | — | `{candidates, ingested}` | Live public-news monitoring (Linkup + model normalisation, `data_origin: public_source`, label "Live public signal"). Returns candidates; ingests through the normal gateway only with `ingest=true`. |
| GET `/scenario-runs/{run_id}/events?after=` | — | SSE | Run-level stream (`case_id: "__run__"`): signal received/matched, clock moves, evidence changes. |
| GET `/cases/{case_id}/events/history?after=` | — | `DomainEvent[]` | Same events as the SSE stream, as JSON (for replaying the activity panel on load). |
| GET `/evidence?q=&doc_type=` | — | search result | Evidence search (Delta SQL keyword; AI Search not provisioned — `retrieval_mode` recorded). |
| POST `/cases/{case_id}/selections` | `SelectionRequest {candidate_id, decision_id, evidence_hash, expected_revision, actor}` | `Selection` or `409 STALE_DECISION` / `409 CHANGE_PENDING` | Only for a currently `eligible` candidate in the **current** decision. Triggers document generation automatically. |
| GET `/cases/{case_id}/documents` | — | `DocumentsView` | Current package and drafts, history, receipts, `generation_status`, readiness, applicable templates (with `why_included`). |
| PATCH `/documents/{id}` | `DocumentPatchRequest {expected_version, field_edits?, review_action?, actor}` | `DocumentsView` | `id` = draft ID (one document) or package ID (the review action applies to every draft). Edits create new immutable versions with `user_edit` provenance and reset review. `review_action`: `submit_for_review` / `approve` / `request_changes`. Approval binds the exact package hash. |
| GET `/packages/{package_id}/download` | — | `text/html` | Reviewable rendered package (fields, values, provenance, completion tasks, "SIMULATED" banner where relevant). |
| POST `/cases/{case_id}/simulated-submissions` | `SubmissionRequest {selection_id, package_id, package_version}` | `SimulatedReceipt` or `409 NOT_READY` / `STALE_DECISION` | Requires the current selection and the approved current package. The same operation returns the same receipt (no duplicates). |
| GET `/evidence/{version_id}` | — | `EvidenceView` | Source metadata, `facts: ExtractedFact[]` with locators, the checks that use it, preview text, `superseded_by`. |
| GET `/cases/{case_id}/events?after={sequence}` | `Accept: text/event-stream` | SSE of `DomainEvent` | See §3. |
| PATCH `/cases/{case_id}/monitoring` | `MonitoringRequest {status: active\|paused\|closed, expected_revision}` | `CaseView` | Versioned and audited (`monitoring.updated`). Resume reconciles pending changes. |
| POST `/cases/{case_id}/visual-actions` | `VisualActionRequest {action}` | `VisualActionResult {visual_state, case_state, allowed_next, selected_candidate_id}` | `focus`, `explode`, `reassemble`, `show_failure`, `remove`, `install`, `restore`, `reset_view`. The server validates domain prerequisites (see §5). |
| GET `/health` | — | `{status, version}` | Process liveness. |
| GET `/readiness` | — | `Readiness {status, capabilities{…}}` | Dependency capability summary (SQL warehouse, ai_extract, model, Linkup, Companies House, MLflow, operational store, search mode). Detailed diagnostics are team-only. |

### Example — accept an offer

```http
POST /api/v1/cases/case-primary/selections
Idempotency-Key: 6f1c2d0e-0c55-4c1e-9a8b-4f0d3a6b9e21
Content-Type: application/json

{"candidate_id": "OFF-PB", "decision_id": "dec-2b7e…", "evidence_hash": "sha256:9c1f…", "expected_revision": 12, "actor": "demo-operator"}
```
```json
{"selection_id": "sel-…", "case_id": "case-primary", "scenario_run_id": "…", "candidate_id": "OFF-PB", "decision_id": "dec-2b7e…",
 "accepted_case_revision": 13, "evidence_hash": "sha256:9c1f…", "actor": "demo-operator", "accepted_at": "2026-11-14T15:02:11Z",
 "idempotency_key": "6f1c2d0e-…", "status": "current"}
```

### Example — `RankedCandidate` (abridged)

```json
{"candidate": {"candidate_id": "OFF-PA", "route": "BUY", "label": "Offer A — overhauled spare, Rotterdam stock", "part_id": "RS-FN-1001",
               "revision": "D", "supplier_id": "SUP-NVA", "site_id": "SITE-NVA-RTM", "price": {"amount": "46200.00", "currency": "GBP"},
               "logistics_route_id": "R-RTM-HWC", "data_origin": "synthetic_demo"},
 "eligibility": "eligible", "feasible": true, "rank": 1,
 "score": {"recovery_speed": 0.9286, "landed_cost": 0.72, "historical_reliability": 0.85, "current_resilience": 0.9,
           "weights": {"recovery_speed": 0.45, "landed_cost": 0.25, "historical_reliability": 0.2, "current_resilience": 0.1},
           "inputs": {"elapsed_recovery_days": 4.0, "landed_cost_gbp": "48000.00", "on_time_delivery_rate": 0.97, "current_exposure": 0.1},
           "thresholds": {"recovery_speed_days": [2.0, 30.0], "landed_cost_gbp": [20000, 120000], "on_time_delivery_rate": [1.0, 0.8],
                          "ranking_config_version": "ranking-default-v1"}, "score": 85.79},
 "plan": {"finish_day": 4.0, "critical_path": ["alloc", "ship", "recv", "ready"], "solver": "dependency_cpm", "landed_cost": {"amount": "48000.00", "currency": "GBP"}, "…": "…"},
 "reliability": [{"metric_name": "on_time_delivery_rate", "label": "On-time delivery (share of deliveries within the promised date)", "value": 0.97,
                  "numerator": 194, "denominator": 200, "window": "12 months to 2026-10-31", "data_origin": "synthetic_demo",
                  "fixture_note": "Favourable scenario fixture value — not measured real-world performance"}],
 "exposure": {"value": 0.1, "baseline": 0.1, "signals": [], "label": "Current exposure (0 = none, 1 = severe) …"},
 "evidence_coverage": {"mandatory_checks": 9, "passed": 9, "with_source_evidence": 8, "ratio": 0.889, "label": "Evidence coverage: … (not a likelihood of physical suitability)"},
 "check_ids": ["chk-…"], "gaps": [], "summary": "Rank 1: ready by day 4, £48,000 landed, score 85.79"}
```

Show pending and ineligible candidates **separately** from the ranked shortlist, with their gaps (`eligibility: pending`, `feasible: true` means "feasible but not ready to select"). Enable "Accept option" only when `eligibility == "eligible"` **and** the decision is current **and** `CaseView.pending_change_ids` is empty.

## 3. Events (SSE)

`GET /api/v1/cases/{case_id}/events?after={sequence}` streams `text/event-stream`:

```
id: 42
event: decision.updated
data: {"schema_version":"1.0","event_id":"…","sequence":42,"occurred_at":"2026-11-14T15:00:00Z","scenario_run_id":"…","case_id":"case-primary","case_revision":7,"invocation_id":"…","task_id":"task-persist","type":"decision.updated","summary":"Shipping disruption changes the preferred recovery plan","data":{"previous_decision_id":"dec-…","decision_id":"dec-…","label":"D2","trigger_id":"sig-rtm-closure-v1","diff_id":"diff-…"},"evidence_refs":[],"trace_id":"tr-…","data_origin":"synthetic_demo"}

: heartbeat
```

- `id` is the **per-case sequence**. On reconnect, send `Last-Event-ID` or `?after=` and the backend replays persisted events in order, then streams live ones. Deduplicate by `event_id` and order by `sequence` (PRD §7).
- Heartbeats are SSE comments (`: heartbeat`, every ~15 s) and are not domain events.
- `control.snapshot_required` means a gap in retained history: refetch `GET /cases/{id}` and resume from its `event_cursor`.
- Run-level events (for example an unrelated signal matching no case) go to the pseudo-case `__run__`: `GET /cases/__run__/events`.
- `supplier.discovered` carries a typed `SupplierDiscovery` in `data`: `component_id`, `candidate_id`, `supplier_id`, `route` and a `location` containing `site_id`, country, geo ID, nullable coordinates, precision, confidence, location type, source and data origin. The envelope's `invocation_id` identifies the generation and `task_id` identifies the evidence retrieval task. Its `evidence_refs` are resolved candidate documents, not proof of a site's coordinates or eligibility. Fixture locations are explicitly `synthetic_demo` and `representative`, with a fixture source; coordinates without a known source are withheld. Use batch component mappings to associate these per-case events with a batch.
- Switching component: close the old EventSource and open the new case's stream with its own cursor. Never mix streams (PRD §3.2).

Event families (`EVENT_TYPES`): `case.started`, `task.started|completed|failed`, `tool.started|completed|failed`, `evidence.ingested|extracted|validated`, `gap.opened|resolved`, `check.completed`, `signal.received|matched`, `impact.detected`, `reassessment.started`, `decision.created|updated`, `selection.accepted|stale`, `documents.preparing|ready|stale`, `submission.simulated`, `visual.updated`, `monitoring.updated`, `case.state_changed`, `run.interrupted|recovered|completed|failed`, `control.snapshot_required`.

Typical `data` payloads:

| type | data |
|---|---|
| `task.started/completed` | `{task, status, counts?, summary_origin?: "model"\|"deterministic"}` (`task_id` such as `task-source-buy`, `task-extract`, `task-technical_checks`, `task-gaps`, `task-rank`, `task-persist`) |
| `tool.started/completed` | `{tool, call_id, args?, latency_ms, mode?, count?, evidence_ids?}`. Tool names follow PRD §8.2 (`query_candidate_offers`, `search_public_sources`, `extract_document_fields`, `request_supplier_followup`, `rank_eligible_offers`, …). |
| `evidence.ingested/extracted/validated` | `{version_id, hash?, doc_type?, facts?, mode?, invalid?}` |
| `check.completed` | `{candidate_id, category[], checks: [{check_id, requirement_id, result: pass\|fail\|unknown, reused}]}` |
| `gap.opened/resolved` | `EvidenceGap` fields, or `{gap_id, check_id, result}` |
| `signal.received/matched` | `{change_id, signal_id, label: "Scenario signal", affected_case_ids}` |
| `impact.detected` | `{change_id, trigger_id, impact_paths: [[{id,type,via?}, …]], affected_candidate_ids, stale: [...]}` |
| `decision.created/updated` | `{decision_id, label, previous_decision_id?, trigger_id?, diff_id?, preferred_candidate_id}` |
| `selection.accepted/stale` | `{selection_id, candidate_id, decision_id, reason?}` |
| `documents.preparing/ready/stale` | `{package_id?, version?, generation_id, reason?}` |
| `submission.simulated` | `{receipt_id, package_id, package_version, destination_type, label: "SIMULATED — no real submission was made"}` |
| `visual.updated` | `{visual_state, action, selected_candidate_id?}` |
| `run.*` | `{generation_id, kind, status, superseded?}` |

## 4. Demo script mapping (PRD §2.2)

| # | Script step | API / events | UI |
|---|---|---|---|
| 0 | Reset | `POST /scenario-runs {mode:"seeded"}` → `GET /engines/engine-demo-001` | Fresh run, engine assembled, mode badge "Seeded". |
| 1 | Engine + purpose/state | `EngineView.engine.operating_story` | Hero engine, short explanation, AOG status. |
| 2 | Explode, focus 3 components | `POST /cases/{id}/visual-actions {explode}` (per case or first case) | Exploded assembly, 3 hotspots plus a keyboard list. |
| 3 | Select primary, failure + consequence | `visual-actions {focus}`, `{show_failure}`; `ComponentInstance.failure_story` | Red failure state (with icon/text, not colour only), consequence text. |
| 4 | Start investigation | `POST /cases/case-primary/investigations` → SSE `task.*`, `tool.*`, `evidence.*`, `check.*`, `gap.*` | Activity panel with parallel BUY/MAKE tracks, then checks. |
| 5 | D1 + ranked offers | `decision.created` → `GET /decisions/{id}` | Ranked cards (A, B, C), pending (D) and ineligible (E) separately, score breakdown, plan, reliability (labelled fixture). |
| 6 | Inject scenario signal | `GET /scenario-runs/{run}/signals/catalog` → `POST /scenario-runs/{run}/signals {fixture_signal_id:"SIG-RTM-CLOSURE"}` | "Scenario signal" label; D1 stays visible. |
| 7 | Signal → path → offer → case | `signal.received`, `impact.detected` (`impact_paths`), `reassessment.started` | Animated path: Port of Rotterdam → route → Offer A → fuel nozzle case. Stale badge on D1. |
| 8 | D2 beside D1 | `decision.updated` → `GET /diff?from=D1&to=D2` | Side-by-side comparison, rank moves (B ↑1, A ↓1), changed delivery/cost/exposure, rerun vs reused checks. |
| 9 | Accept from D2 | `POST /selections` (409 path handled) → `selection.accepted` | Accept button only on eligible current candidates. |
| 10 | Document package | `documents.preparing/ready` → `GET /documents`; `PATCH /documents/{id}` for edits/approve; `GET /packages/{id}/download` | Template/field layout (CAA Form 1 blocks), values and provenance; completion tasks for signatures. |
| 11 | Simulated submission | `POST /simulated-submissions` → `submission.simulated` | Destination type, submitted versions, timestamp and a **SIMULATED** receipt. |
| 12 | Replacement animation | `visual-actions {install}` then `{restore}` → `visual.updated` | Selected part animates in, the engine returns to running, tied to the accepted candidate. |
| 13 | Secondary components | `GET /cases/case-secondary-a` etc. → their own investigations | Switch cases without losing primary history. |

## 5. State machines (PRD §6.3)

**Case workflow:** `ready → investigating → recommendations_ready → reassessing → recommendations_ready → selected → documents_preparing → documents_ready → submission_simulated → installation_visualized → restored_visualized`.
Auxiliary states: `waiting_for_evidence`, `interrupted`, `failed`, `selection_stale`, `documents_stale`. A change can enter `reassessing` from any active state (`prior_stable_state` is kept). After a selection-related invalidation the user must accept again before new paperwork or submission. Earlier receipts remain historical. Switching component never changes workflow state.

**Component visual state** (separate and independently recoverable): `assembled`, `exploded`, `failed`, `removed`, `replacement_ready`, `installed`, `running`.

| Action | From → to | Domain prerequisite |
|---|---|---|
| `focus` / `reset_view` | camera only | none |
| `explode` / `reassemble` | assembled ↔ exploded | none |
| `show_failure` | assembled/exploded → failed | none |
| `remove` | failed → removed | none |
| (automatic) | removed/failed → replacement_ready | `submission.simulated` |
| `install` | removed/replacement_ready → installed | case `submission_simulated`; sets case `installation_visualized` |
| `restore` | installed → running | case `installation_visualized`; sets case `restored_visualized` |

`VisualActionResult.allowed_next` tells the UI which controls to enable. Drive animations from `visual_state`, not from local guesses (PRD §3.2).

## 6. Engine manifest (`data/manifests/engine-demo-001.json`, served inside `EngineView`)

- `engine.asset`: `kind: "procedural"`, `glb_path: null`, units metres, centreline along +X (intake −X, exhaust +X). `modules[]`: `Module_Fan`, `Module_LPC`, `Module_HPC`, `Module_Combustor`, `Module_HPT`, `Module_LPT`, `Module_Exhaust`, each with an `x_range`. `explode: {axis: "x", module_spacing: 0.45, duration_ms: 1400}`.
- `components[]` (`ComponentInstance`): `component_id`, `case_id`, `display_name`, `part_identity`, `revision`, `position`, `failure_story {finding, effect, consequence, severity, visual{highlight, pulse, crack_overlay}}` and `mesh_mapping`:
  - `node_name`: `Component_FuelNozzle_07` (primary), `Component_NGV_Segment_12` (secondary A), `Component_BleedDuct_HP` (secondary B). The scene graph **must** contain nodes with exactly these names.
  - `hotspot_anchor [x,y,z]`, `exploded_offset [x,y,z]`, `camera_focus {position, target}`, `removal_vector [x,y,z]`.
- If a licensed GLB replaces the procedural geometry, keep these node names and update the anchors in the manifest via a board-coordinated PR (data/ is backend-owned).
- Visual identity is *representative*. Show the real case identity (synthetic part numbers) from the data, labelled "Representative assembly · synthetic demo data".

## 7. UX requirements (PRD §3, §11)

- **One coherent workspace:** engine viewport, case overview, activity panel, recommendations (ranked plus separately pending/ineligible), change comparison (D1|D2), evidence inspector (title, revision/date, locator, extracted value, source link, retrieval time, applicable check), and documents panel (route explanation, package, field values with provenance, editable drafts, review status, receipt).
- Non-specialist summary first, technical detail one click away. Show observable actions and evidence, never hidden reasoning.
- Explicit states for initial loading, active work, waiting for evidence, interrupted, retry, completed and stale decision. The current recommendation and D1 stay legible during reassessment.
- Back navigation in the evidence/document panels must not reset the 3D scene.
- **Accessibility:** keyboard-accessible component list and focus management, meaningful labels, non-colour status indicators (icon + text: ✓ pass, ✕ fail, ? unknown), `prefers-reduced-motion` support (crossfades instead of fly-throughs), and textual equivalents for 3D status. At narrow widths, stack the scene and panels while keeping selection and status.
- **Labels that must be visible:** mode badge (`Seeded` / `Live` / `Replay`), "Scenario signal" on injected signals, "Replay" on replayed runs, "SIMULATED — no real submission was made" on receipts, `synthetic_demo` data origin (for example "Synthetic demo data"), and "Scenario fixture value — not measured real-world performance" on reliability figures.
- **Performance targets** (to verify, not claim): command acknowledgement < 2 s warm, first progress event < 3 s, ≥ 30 fps during the main animation on the demo laptop.

## 7a. Intake & mesh (v1.1, additive)

Agreed with Yixin's Astra on the board (issue #1). Nothing in §2 changes. All models live in `backend/recovery/domain/models.py`
(`SourceRef`, `IntakeUpload`, `RequirementField`, `PartRequirementDraft`, `PartRequirementPatch`, `MeshExpectation`, `MeshNodeCheck`,
`MeshValidation`, `MeshJobRequest`, `MeshJob`, `ManifestProvenance`) and are in `contracts/generated-types/api.ts`.

| Method and route | Request | Response | Notes |
|---|---|---|---|
| POST `/intake/uploads` | multipart: `file`, `kind` = `blueprint` \| `part_requirements` \| `mesh_glb`, `engine_id`, optional `component_id` | `IntakeUpload` (201; 200 with `duplicate_of` when identical bytes already exist) | Content-addressed by sha256. Allowlist: blueprint/part_requirements → pdf, png, jpg, txt, md, json; mesh_glb → glb, gltf. Magic bytes checked, 50 MB cap. `storage_uri` is the UC volume path `/Volumes/workspace/resource/rs_uploads/<sha256><ext>` once mirrored, else `local://uploads/...`. |
| GET `/intake/uploads/{upload_id}` | — | `IntakeUpload` | Status `received` → `mirrored` (or `mirror_failed`). |
| GET `/intake/uploads/{upload_id}/content` | — | raw bytes | Stored media type (`model/gltf-binary` for GLB). Use as the GLTF loader URL for an activated mesh. |
| POST `/intake/part-requirements` | `{upload_id, component_id}` | `PartRequirementDraft` (202, `status: extracting`) | Background extraction: text files read directly; PDF/PNG/JPG → Databricks `ai_parse_document` (pages + bboxes) then `ai_extract` (OpenAI fallback, then structured `KEY: value` parse). Fields: `part_number`, `revision` (required), `description`, `material`, `mating_interfaces`, `key_dimensions`, `tolerances`, `certifications`, `drawing_units`, `applicable_standards`, `inspection_requirements`, `effectivity`; each with `source_ref {upload_id, page, bbox, excerpt, line}`, `confidence`, `validation_state` (`valid`/`invalid`/`unknown`). |
| GET `/intake/part-requirements/{draft_id}` | — | `PartRequirementDraft` | Poll until `needs_review` (or watch `intake.extracted` on the run stream). |

| PATCH `/intake/part-requirements/{draft_id}` | `PartRequirementPatch {expected_version, field_edits{name: value}, action?: confirm\|reject, actor}` | `PartRequirementDraft` | Edits bump `version`, keep history, set `extraction_mode: user_edit` and `edited_by`. Version mismatch → 409. `confirm` needs valid `part_number` + `revision` (else 422 `NOT_READY`), stores a run-scoped requirement overlay and sends a `requirement` change through the normal gateway → affected cases reassess (D-n+1). Response carries `change_id` and `affected_case_ids`. |
| POST `/intake/mesh-jobs` | `MeshJobRequest {upload_id, engine_id, expected?: [{component_id, node_name, source_ref?}]}` | `MeshJob` (201) | `expected` defaults to the manifest's three nodes. **mesh_glb** → provider `uploaded_glb`, synchronous validation: node present + unique, mesh (or mesh children), ≥ 3 vertices, bbox non-degenerate on ≥ 2 axes, centre inside engine bounds (module x-range ± 0.5 m, \|y\|,\|z\| ≤ 1.5 m), `source_ref` from `node.extras.source_ref` or `expected[].source_ref`. Status `succeeded`/`failed` with `validation` + `manifest_candidate` (bboxes, suggested hotspot anchors). **blueprint** → `provider_required` unless a server-side provider is configured (`RS_MESH_PROVIDER`); **no mesh is ever reported as generated without a provider.** Unknown `component_id` → 422 (IDs are stable). |
| GET `/intake/mesh-jobs/{job_id}` | — | `MeshJob` | For refresh/reconnect. |
| POST `/intake/mesh-jobs/{job_id}/activate` | — | `ManifestProvenance` | Only `succeeded` jobs (else 409 `MESH_JOB_NOT_ACTIVATABLE`). Publishes manifest version `engine-demo-001.v1+genN`; `GET /engines/{id}` then returns `engine.asset.kind = "generated"`, `asset.glb_path`, `asset.provider`, `asset.job_id`, `asset.provenance` (source refs per component) and the validated node names/anchors in each component's `mesh_mapping`. Component and case IDs never change. |
| GET `/intake/manifest` | — | `ManifestProvenance` | Current provenance (`kind: procedural` by default). |
| POST `/intake/manifest/reset` | — | `ManifestProvenance` | Back to procedural geometry (`+resetN`); history kept via `previous_manifest_version`. |

For one document covering multiple components, create a draft per component from the same unbound upload and use distinct `COMPONENT_ID: <component_id>` sections. Extraction is restricted to the matching section, and source line references retain their positions in the original document. Missing or duplicated sections, or multiple distinct structured part numbers without a unique section, produce unknown fields for manual review. Component-bound uploads cannot be used for another component. This deterministic convention does not reliably identify every ambiguous unstructured blueprint; reviewers must verify each source reference.

Dimension and tolerance fields expose a unit only when their text contains a single unambiguous numeric length unit; mixed or missing units remain unknown. Confirmed overlays retain the reviewed field snapshots, including unknowns, source references, reviewer and review time. A reviewer edit clears the old field source reference and preserves it in version history. Engineering compatibility checks still use the existing identity rules; these recorded dimensions, materials, tolerances and certifications are not automatically evaluated.

Run-stream events (`GET /scenario-runs/{run_id}/events`): `intake.uploaded`, `intake.extracted`, `intake.validated`, `intake.confirmed`,
`manifest.updated` (all `data_origin: provided_document`). Scroll-explode is presentation-only; install/restore stay server-gated via
`/cases/{id}/visual-actions`.

## 8. Change process

1. Edit `backend/recovery/domain/models.py` (bump `SCHEMA_VERSION` for breaking changes).
2. `uv run python scripts/export_contracts.py`.
3. Update this file and post on the board (`[Bede's Claude] contract change: …`) before merging.

## Public Vercel runtime (D-019/D-020)

The browser uses same-origin `/api/v1` on Vercel; it never calls the private Databricks App. Public anonymous visitors receive a secure HttpOnly `resource_visitor` cookie. Current runs, intake records/active manifests and idempotency keys are visitor-scoped; cross-visitor run/replay access returns 404. Cross-origin mutations return 403. Forwarded user headers do not establish reviewer identity; actors are unverified demo visitors.

No generated payload shapes changed for this hosting migration. The fallback HTML root is excluded from OpenAPI so the contract does not vary with frontend build presence. SSE responses reconnect after a bounded 50-second window and replay committed Lakebase events using the existing sequence cursor. Long operations are durable queue jobs, not resident API threads. On Vercel, multipart uploads are limited to 4 MB and must mirror to the UC volume before acknowledgement. Local backend upload limits remain 50 MB. See `deploy/vercel/README.md` for configuration and verification status.
