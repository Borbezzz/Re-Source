# Re-Source — decision log

Versioned decision notes (PRD §16). Each entry records the decision, its rationale, the alternatives considered and the contracts/data it affects. Add new entries at the bottom; never rewrite history. Mark superseded entries as `Superseded by D-xxx`.

Status values: **Accepted** (in force) · **Proposed** (needs team lead / human confirmation) · **Superseded**.

---

### D-001 — App model provider: OpenAI Responses API, default `gpt-5.4-mini`
- Date: 2026-11-14 · Status: **Proposed (material change, escalate to @Borbezzz)**
- Decision: the app's agent/explanation/extraction-fallback calls use the OpenAI Responses API with the app's own runtime key (`OPENAI_API_KEY`). The model comes from `OPENAI_MODEL`, default `gpt-5.4-mini` (a dated snapshot family with structured outputs; fast and cheap for short summaries and schema extraction).
- Rationale: the PRD prefers Claude through a Databricks model interface. The workspace's serving endpoints are only `databricks-gpt-oss-120b/20b`, `databricks-qwen3-next-80b-a3b-instruct`, `databricks-qwen35-122b-a10b`, `databricks-gemma-3-12b`, `databricks-llama-4-maverick`, `databricks-meta-llama-3-1-8b/3-3-70b-instruct`, plus embedding models; there is no Claude endpoint. The user supplied an OpenAI key specifically for the app. Model availability was confirmed by listing `/v1/models` (no tokens spent).
- Alternatives: Databricks-hosted gpt-oss/llama through `ai_query`, which works and is a viable fallback; adding an external-model Claude endpoint, which needs workspace provisioning and an Anthropic key; `gpt-6-astra`, which is overkill for summaries and costly.
- Rule: the key is for the running app only, never for building it.
- Affects: `backend/recovery/adapters/model_client.py`, `config.py` (`OPENAI_MODEL`, `RS_MODEL_ENABLED`, `RS_MODEL_TIMEOUT_S`).

### D-002 — One model integration path; deterministic fallbacks everywhere
- Date: 2026-11-14 · Status: Accepted
- Decision: a single `ModelClient` path (PRD §8.2: "one selected model integration path initially"). Every model use has a deterministic fallback: summaries fall back to templated text, extraction falls back to the structured parse. The model never decides eligibility, schedules, ranks or submission status (PRD §6.2).
- Rationale: correctness must not depend on model availability, and the demo must survive a model outage.
- Affects: `agents/investigation.py` (records the `summary_origin` of each summary), `adapters/extractor.py`.

### D-003 — Observed Databricks workspace capabilities (DISC-04 partial)
- Date: 2026-11-14 · Status: Accepted (observation)
- Observed with the provided token. The workspace owner is the team lead's account and looks like a Free Edition-style workspace.
  - SQL warehouse `8617c97c3ad572c6` "Serverless Starter Warehouse" (PRO, serverless; auto-starts on query). `SELECT current_user()` works; DBSQL 4.2.0.
  - AI Functions: `ai_extract(...)` works (it returned correct JSON for a part/revision/serial string) and `ai_query('databricks-gpt-oss-20b', ...)` works.
  - Unity Catalog: catalog `workspace`, schemas `default`, `information_schema`, `resource`. `workspace.resource` already holds the lead's tables `cost_estimates`, `evidence`, `sourcing_runs` and `suppliers`. No volumes yet.
  - Lakebase: no database instances or projects exist. AI Search (vector search): no endpoints exist.
  - Databricks App `resource` exists with compute STOPPED and no deployment yet. It has service principal `app-3eov8h resource` and resources: SQL warehouse (CAN_USE), secrets `resource/linkup_key` and `resource/companies_house_key` (READ), MLflow experiment `2648868221488633` `/Shared/ReSource/agent-traces` (CAN_EDIT).
  - Genie space `01f1e035b5591c43a9bccebde3df2119` "ReSource — Supplier Evidence" is on the same warehouse.
- Affects: deployment design, D-004 to D-008. The full capability matrix goes in `docs/verification/disc-04-capability-spike.md` (data-layer fork).

### D-004 — Operational store: SQLite locally, Lakebase Postgres when provisioned
- Date: 2026-11-14 · Status: Accepted (Lakebase provisioning **Proposed**, needs approval)
- Decision: `OperationalStore` (SQLAlchemy Core) holds the authoritative mutable state: case revision, commands/idempotency, selections, document pointers, outbox, events, receipts, barriers, subscriptions and generations. If `RS_OPERATIONAL_DB_URL` is a `postgresql+psycopg://` URL (Lakebase native tables) it uses Postgres with row locks (`SELECT … FOR UPDATE`) and connection recycling for OAuth token rotation. Otherwise it uses `var/operational.sqlite3` with `BEGIN IMMEDIATE`, which serialises writers and makes every write transaction serialisable.
- Rationale: no Lakebase instance exists, and creating one (`resource-ops`, CU_1) in the lead's workspace was blocked pending explicit user approval. The SQLite fallback preserves the same transactional semantics for development and the demo laptop. In a Databricks App, local disk is ephemeral, so durability across app restarts needs Lakebase.
- Alternatives: Delta tables for operational writes were rejected (the PRD forbids them for mutable authority, and there is no row-level transactional CAS); an external Postgres was rejected (not a Databricks equivalent).
- Affects: `adapters/store.py`, `config.py`.

### D-005 — Graph checkpoints: LangGraph SqliteSaver (PostgresSaver with Lakebase)
- Date: 2026-11-14 · Status: Accepted
- Decision: one graph-checkpoint authority. `make_checkpointer()` returns `PostgresSaver` when the operational DB is Postgres (requires `langgraph-checkpoint-postgres`), otherwise `SqliteSaver` at `var/checkpoints.sqlite3`. `thread_id` is the execution `generation_id`. On startup, generations still marked running are resumed from their checkpoint, with `run.interrupted` and `run.recovered` events.
- Affects: `agents/graph.py`, coordinator.

### D-006 — No Agent Bricks Runtime/AgentKit; FastAPI BFF hosts the graph in the Databricks App
- Date: 2026-11-14 · Status: Proposed (gap vs PRD §5.1)
- Decision: the FastAPI BFF runs the LangGraph graph in background workers (bounded concurrency) inside the Databricks App `resource`. Durability comes from the operational store, the outbox and graph checkpoints. Domain events are our own (per-case sequence) rather than Agent Runtime `/api/invocations` events.
- Rationale: Agent Runtime/DurableAgentServer is Beta and not visible in this workspace. The user-visible contract (PRD §7) is unchanged.
- Alternatives: Agent Bricks CLI deployment, to revisit if the workspace gains it.
- Affects: `api/app.py`, coordinator, `deploy/databricks/`.

### D-007 — Document extraction: Databricks `ai_extract` cross-checked with a deterministic structured parse
- Date: 2026-11-14 · Status: Accepted
- Decision: `DocumentExtractor` chooses its backend with `RS_EXTRACTION_BACKEND=auto`: Databricks `ai_extract` on the SQL warehouse (batched per document type), then OpenAI structured output, then the deterministic parse. Every generative value is compared with the deterministic `FIELD: value` parse of the governed document. If they agree, the fact is valid at confidence 0.98. If they disagree, the structured field is kept, confidence drops to 0.6, and the disagreement is recorded in `validation_note`. Values are validated in code (part number and revision formats, ISO dates, currencies, site IDs, booleans). Results are cached by content hash and doc type, so reprocessing identical content is deduplicated (FR-04).
- Rationale: demo determinism plus genuine Databricks Document AI use. `ai_parse_document` over volume PDFs is a later upgrade once a volume exists.
- Affects: `adapters/extractor.py`, `domain/extraction.py` (`FIELD_SCHEMAS`).

### D-008 — Retrieval: keyword fallback until AI Search is provisioned
- Date: 2026-11-14 · Status: Accepted (AI Search endpoint **Proposed**, needs approval)
- Decision: final gates always resolve evidence by exact version ID from the authoritative snapshot (PRD §5.3). Discovery search uses AI Search hybrid search when an endpoint exists; otherwise SQL keyword search over `rs_evidence_versions` (Delta), otherwise an in-memory keyword index. The retrieval mode is always recorded (AC-15).
- Rationale: creating vector search endpoint `resource-evidence` was blocked pending approval.
- Affects: `adapters/search.py` (data-layer fork).

### D-009 — Representative engine and component identities (DISC-01 provisional)
- Date: 2026-11-14 · Status: Accepted (provisional until asset selection)
- Decision: engine `engine-demo-001` is a representative two-spool high-bypass turbofan, "RS-TF2", configuration `RS-TF2-CFG-A`. Components:
  - `component-primary`: combustor fuel nozzle position 7, `RS-FN-1001` rev D. Cracked swirler tip → hot streak → AOG. A strong, intuitive BUY-vs-MAKE story with plausible serviceable spares and certified manufacturers.
  - `component-secondary-a`: HPT stage-1 NGV segment, `RS-NGV-2040` rev B. An existing spare wins after checks, and it carries the gap follow-up story.
  - `component-secondary-b`: HP compressor bleed air duct, `RS-BD-3110` rev A. Fabricated sheet-metal part where MAKE is realistic, which suits the BUY-vs-MAKE qualification story.
  - The three components sit next to each other around the combustor section, so they can be focused together in the exploded view.
- All part numbers, approval references (`UK.145.9xxxx`, `UK.21G.99xxx`), company numbers and suppliers are **synthetic and fictional** (`data_origin: synthetic_demo`). Fictional suppliers: Northvale Aero Spares B.V., Calderbrook Aerospace Supply Ltd, Pennine Precision Components Ltd, Lowmarsh Trading Ltd, Esker Component Exchange Ltd, Harbourline Aero Components Ltd, Meridane Turbine Parts GmbH, Coastreach Surplus Ltd, Kestrelmoor Fabrication Ltd. They are never presented as real companies or measured performance (PRD DISC-02, FR-06).
- 3D: procedural geometry with the manifest node names (`Component_FuelNozzle_07`, `Component_NGV_Segment_12`, `Component_BleedDuct_HP`), unless the frontend owner selects a licensed GLB with separable meshes.
- Affects: `data/manifests/engine-demo-001.json`, `rules/requirements/*`, `data/fixtures/*`.

### D-010 — Primary scenario fixture and scoring thresholds
- Date: 2026-11-14 · Status: Accepted (freeze after independent recomputation in tests)
- Ranking config `ranking-default-v1`: score = 100 × (0.45 speed + 0.25 cost + 0.20 reliability + 0.10 resilience). Speed is normalised over [best 2, worst 30] days. Reliability is on-time-delivery rate over [best 1.00, worst 0.80]. Resilience = 1 − exposure. Cost is in GBP, per case: primary [20,000 → 120,000], secondary-a [10,000 → 60,000], secondary-b [5,000 → 30,000]. Ties go to lower elapsed days, then lower landed cost, then candidate ID. FX table `fx-2026-11-14-scenario` (EUR→GBP 0.87) is a scenario fixture.
- Primary (case-primary) expected values:

  | Offer | Route | Ready (day) | Landed £ | OTD | Exposure | Score D1 | After `SIG-RTM-CLOSURE` |
  |---|---|---|---|---|---|---|---|
  | OFF-PA Northvale, Rotterdam | BUY | 4 | 48,000 | 0.97 | 0.10 | **85.79 (1st)** | day 11, £50,500, exposure 0.80 → 66.91 (2nd) |
  | OFF-PB Calderbrook, Manchester | BUY | 6 | 56,000 | 0.98 | 0.05 | 82.07 (2nd) | unchanged → **82.07 (1st)** |
  | OFF-PC Pennine, Sheffield | MAKE | 21 (CP-SAT machining window 5–13) | 74,000 | 0.95 | 0.10 | 49.96 (3rd) | unchanged (3rd) |
  | OFF-PD Lowmarsh, Luton | BUY | — | — | — | — | pending: no Form 1, trace unknown | — |
  | OFF-PE Esker, Birmingham | BUY | — | — | — | — | ineligible: revision C non-interchangeable (near-match) | — |

- Signal: Port of Rotterdam closure, severity 0.8, +7 days transport, +£2,500 surcharge. It affects route `R-RTM-HWC` through `GEO-PORT-NLRTM`. Both leading suppliers stay reliable; the plan changes. Durations are scenario fixtures, not forecasts.
- Secondary A expected: SA-1 eligible after its trace-pack follow-up (day 5, £32,150), SA-2 eligible (day 8, EUR 50,575 → GBP), SA-3 ineligible (expired certificate). Secondary B expected: SB-3 MAKE (day 12) ranks above SB-1 BUY (day 18); SB-2 is pending but feasible (wrong-site certificate, site not in POA scope, no FAI → Form 60 branch).
- Affects: `rules/ranking/default-v1.yaml`, `data/fixtures/build_seed.py`, `tests/evaluations`.

### D-011 — UK CAA document package mapping (DISC-03 provisional)
- Date: 2026-11-14 · Status: Accepted (exact current issue numbers **not yet confirmed**; DISC-03 open)
- Operator role: a UK Part 145 maintenance organisation (with CAMO support). Catalogue `uk-caa-v1`:
  - `APP-BUY-RELEASED`: CAA Form 1 MO incoming-certificate verification (UK Reg 1321/2014 Part-M Appendix II; caa.co.uk/media/kg1krs55/caa-form-1-mo.pdf), component acceptance/receiving inspection (UK 145.A.42, AMC1 145.A.42(a)(i)) and supplier/site approval record. **No authority application.** Destination `internal_quality_records`.
  - `APP-BUY-NO-CERT`: blocks selection (no release certificate).
  - `APP-MAKE-POA`: CAA Form 1 Part 21 version (UK Reg 748/2012 Part 21 Appendix I), expected from the POA holder, plus FAI acceptance (AS9102 review), component acceptance and supplier approval. No authority application.
  - `APP-MAKE-NO-POA`: authority-application branch, CAA Form 60 "Application for agreement of production under Part 21 Subpart F" (letter of agreement issued as CAA Form 65). The route is feasible but not selectable until agreement. Simulated destination `caa_application_simulated`.
- Signatures and attestations are explicit completion tasks for named roles. Simulation never automates a real submission.
- Affects: `rules/applicability/uk-caa-v1.yaml`, `templates/registry/registry.yaml`, documents service.

### D-012 — External data: Companies House only for live GB entities; Linkup for public leads
- Date: 2026-11-14 · Status: Accepted
- Companies House (`COMPANIES_HOUSE_API_KEY`) verifies the legal entity status and registered office of real GB suppliers discovered in `live` mode (`verify_legal_entity`). Synthetic suppliers are **never** looked up, so fabricated records are never associated with real companies. In seeded mode the legal-entity check uses synthetic registry extracts, labelled as such.
- Linkup (`LINKUP_API_KEY`) runs one bounded, cached search per route per investigation. Results are stored as `public_source` leads with "not assessed — lead only" and **never** make an offer eligible. Linkup also supplies live context for signals in live mode.
- Live-mode gap: no live supplier catalogue/quote connector exists, so offers remain seeded fixtures in every mode. Live mode adds current public context and is labelled accordingly.
- Affects: `adapters/external.py`, `agents/investigation.py`.

### D-013 — Frontend delegated to Borbezzz's OpenAI agent (GPT-6 Astra + GPT Image 2.5)
- Date: 2026-11-14 · Status: **Proposed (lead must confirm folder ownership per AGENTS.md §4)**
- Decision: at Bede's request, the React + TypeScript + Vite + React Three Fiber frontend is built by Borbezzz's OpenAI coding agent. It uses `gpt-6-astra` for UI/UX and 3D, and `gpt-image-2.5-flare` / `gpt-image-2.5-sunburst` for presentation imagery. Proposed ownership: their agent owns `frontend/**`; Bede's Claude owns `backend/`, `contracts/`, `data/`, `rules/`, `templates/`, `deploy/`, `tests/`, `docs/` (except frontend docs) and the handoff files. Contract changes go through `interface.md` and the board.
- Brief: `docs/handoff/frontend-brief-astra.md`; post text: `docs/handoff/board-post-frontend.md`.
- Constraint: image generation uses the frontend owner's own build key, never the app's runtime key.
- Affects: `interface.md`, `contracts/*`, the BFF static mount of `frontend/dist`.

### D-014 — Delta table naming: `rs_` prefix in `workspace.resource`
- Date: 2026-11-14 · Status: Accepted
- Decision: product Delta tables use the `rs_` prefix (`rs_evidence_versions`, `rs_extracted_facts`, `rs_relationships`, `rs_requirements`, `rs_offers`, `rs_signals`, `rs_change_events`, `rs_decision_snapshots`, `rs_check_results`, `rs_selections`, `rs_document_packages`, `rs_receipts`, …), so they never collide with the lead's existing `cost_estimates`, `evidence`, `sourcing_runs` and `suppliers`. Those four tables are left untouched.
- Affects: `data/ingestion/load_delta.py`, `services/projection.py`.

### D-015 — Secrets policy
- Date: 2026-11-14 · Status: Accepted
- Secrets live only in the environment or the gitignored `.env` (file mode 600). `.env.example` lists names only. In the Databricks App they come from secret scope `resource` (`linkup_key`, `companies_house_key`; add the OpenAI key as a secret before deploying) and the app service principal (OAuth M2M), never from committed files. Keys never go in board posts (issue #1 is public), logs, events, traces, Delta rows or decision notes. PRD DISC-04: "Do not put tokens in records."

### D-016 — Change activation protocol as implemented (PRD §5.3.1)
- Date: 2026-11-14 · Status: Accepted
- Every producer (signal, evidence change, clock/timer, template/relationship) goes through one gateway:
  1. Register the ChangeEvent and a run-namespace barrier atomically (dedup key per run).
  2. Stage the new version (`signals.status=staged`, `evidence_state=staged`).
  3. Resolve impact over the union of old and new relationship paths.
  4. Fan out idempotent per-case invalidations: input revision +1, stale reasons recorded, selection and documents marked stale when affected, prior stable state saved.
  5. Activate the version manifest and clear the barrier.
  6. Schedule coalesced per-case reassessments.
- Selection, decision publication and simulated submission check the barrier inside their own transaction. Decisions persist with compare-and-swap on (active generation, input revision, no barrier); outdated results are stored as `superseded` and never emit `decision.updated`.
- Affects: services (main session), `adapters/store.py`.
