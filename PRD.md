# Re-Source — Aerospace Recovery PRD

Version: 1.2 — standalone repository edition, 14 November 2026  
Product: Re-Source; aerospace recovery demonstration  
Team repository: https://github.com/Borbezzz/Re-Source  
Status: approved product direction; technical specification prepared for implementation. Workspace provisioning, component/asset selection and regulatory-document discovery are implementation gates. No product code or integration has been tested by authoring this document.

## 1. Product outcome

Aerospace Recovery helps an aerospace maintenance/procurement team recover from a failed jet-engine component. It finds replacement options, checks the evidence for their applicability and supplier/site suitability, compares buying a spare with commissioning manufacture, and prepares the selected route's documentation. When technical evidence, supplier information or monitored disruption signals change, it identifies affected cases, reruns affected checks and updates the recovery plan.

The user sees the engine, the affected component, the investigation and the resulting action in one interface. Every recommendation and populated document field can be traced to its inputs. The product's central demonstration is a credible initial recommendation that changes visibly after a newly introduced risk signal.

### 1.1 Approved decisions

| Decision | Requirement |
|---|---|
| Aerospace product | Jet engine with an exploded assembly and three clickable component hotspots. |
| Demo cases | One primary, deeply developed component case; two nearby components with real executable case flows. |
| Components | Select after evaluating available 3D assets and supporting technical documents. Component IDs remain stable while names are configured. |
| Main story | Initial recommendation → new monitored risk signal → targeted reassessment → changed recovery plan → acceptance → paperwork → simulated submission → animated replacement/restoration. |
| Routes | Explore BUY existing spare and MAKE commissioned manufacture; assess supplier and site reliability for both. |
| Jurisdiction | UK Civil Aviation Authority (CAA); document discovery determines the actual applicable route and forms. |
| Data platform | Databricks equivalents of the technologies used by the reference repository. |
| Code foundation | Reuse and adapt the reference application's source, workflow patterns and UI patterns. Runtime storage, search and data operations use Databricks. |
| Transparency | Frontend shows task progress, tools, evidence, checks, before/after decisions, form fields and simulated receipts. |
| Reliability presentation | Use favourable, explicitly identified demo fixture values. Scenario disruption changes exposure/delivery/cost while supplier reliability may remain favourable. |
| Discovery timing | This document defines asset/manual/form discovery as implementation work; it does not claim those documents have been found. |
| Build planning | Sequence by dependencies and observable milestones rather than restricting ambition to an arbitrary time limit. |

### 1.2 User and job

Primary user: a maintenance/procurement coordinator investigating how to restore an engine after a component failure. Supporting reviewers: engineering and quality/compliance staff. Hackathon judges act as these users through the demonstration.

User question: “Which replacement route can recover this engine, what supports that conclusion, and what must happen next?”

### 1.3 Success at demonstration

- A judge understands the failed component and operational consequence from the engine scene.
- A real backend investigation produces a ranked shortlist with evidence and a transparent calculation.
- A new signal can be traced through a facility or route to an offer, component and case.
- A before/after comparison shows why the preferred plan changed, including checks reused and rerun.
- Selection creates versioned paperwork populated from accepted evidence; the simulated submission returns a persistent receipt.
- All three component hotspots open distinct cases using the same engine, schemas and workflow.
- Reconnecting the UI or retrying a request preserves the investigation and prevents duplicate actions.

## 2. Demo scenarios and presentation

### 2.1 Stable scenario identities

Use engine ID `engine-demo-001` and component IDs `component-primary`, `component-secondary-a`, `component-secondary-b`. Asset discovery supplies real display names, mesh mappings, configuration and document identifiers through a manifest. Do not embed a guessed real engine/part identity in application logic.

| Case | Required decision story | Data requirements |
|---|---|---|
| Primary | Strong initial recommendation; disruption changes its recovery schedule and preferred candidate; user accepts revised option. | At least three candidate offers across at least two supplier/site combinations, two eligible initial alternatives, mapped disruption exposure, complete selected-route evidence and paperwork. |
| Secondary A | An existing spare gives the preferred recovery plan after technical and supplier checks. | At least two offers; documented route-specific checks; independent case state; complete selection-to-paperwork flow. |
| Secondary B | Compare BUY with MAKE, including qualification/manufacturing/inspection dependencies. | At least one offer per route; documented distinction between feasibility and ready-to-select eligibility; complete chosen-route flow. |

An agent may execute one route as a workflow even when evidence ultimately makes it pending or unsuitable. For the judge-facing successful script, curate evidence-complete eligible offers and favourable reliability fixtures. At least one secondary case must be able to complete the same final workflow, and both secondary cases must support the shared full workflow when their eligible route is accepted.

### 2.2 Approved primary script

1. Present the complete engine with a short explanation of its purpose and current state.
2. Explode the assembly; focus the three nearby selectable components.
3. Select the primary component. Animate its failure state and explain the consequence using scenario data.
4. Start investigation. Show parallel BUY/MAKE sourcing and evidence work, then engineering, supplier/site and regulatory checks.
5. Present initial decision snapshot D1 and ranked offers. Judge can inspect evidence, schedule, cost and favourable reliability figures.
6. Presenter introduces a labelled scenario risk signal through the same normalised signal-ingestion path used by monitored signals. The initial recommendation remains visible until this action.
7. Show signal → affected site/route → exposed offer → affected component/case. Reassess only invalidated dependencies and affected downstream outputs.
8. Present D2 beside D1. Explain the material change, changed delivery/cost/exposure, rank movements and retained checks. Both leading suppliers can remain reliable; the risk is a changed recovery plan.
9. User accepts an eligible offer from D2. Revalidate its decision/evidence versions atomically.
10. Generate the applicable document package. Display the actual template/field layout, values and field provenance; allow review/edit where appropriate.
11. Run simulated submission. Display destination type, submitted document versions, timestamp and clearly labelled simulated receipt.
12. Animate replacement into the assembly and return to the working-engine visual state. Tie the selected visual part to the accepted candidate.
13. Invite judges to click either secondary component; switch cases without losing primary-case history.

Presentation targets, to verify on the actual demo laptop: a rehearsed primary narrative of roughly 3–5 minutes with operator-controlled pacing; interactions remain responsive while real work completes. These are presentation targets, not restrictions on scope or claimed measured performance.

### 2.3 Modes and reproducibility

- `live`: permitted connectors supply current data; store retrieval times and source versions.
- `seeded`: normal workflow executes on curated, versioned demo data with deterministic disruption inputs and a scenario clock. AI calls may still run.
- `replay`: recorded domain events/results are replayed with a visible replay label. This is a presentation recovery option; the live execution path must also be demonstrated during verification.

Mode and data provenance are available in the case header/detail. Seeded signal injection is labelled “Scenario signal”; a recorded run is labelled “Replay”. Demo reset creates a new isolated run namespace; it preserves prior run history.

## 3. Product experience

### 3.1 Main workspace

Use a single coherent workspace, not disconnected pages:

- Engine viewport: orbit, explode/reassemble, camera focus, three hotspots, failure/replacement highlights and restoration animation.
- Case overview: component identity, engine configuration, consequence, workflow state, current decision version and mode.
- Activity panel: parallel tasks, tool status, concise conclusions, evidence links and timestamps; expandable engineering detail.
- Recommendations: ranked cards/table with BUY/MAKE route, part/revision, supplier/site, technical status, qualification status, reliability, price/currency, recovery time, relevant risk and evidence coverage.
- Change comparison: initial/current snapshots, triggering signal, dependency path, changed fields/ranks and checks rerun/reused.
- Evidence inspector: source title, revision/date, page/section or bounding box, extracted value, source link, retrieval time and applicable check.
- Documents panel: route explanation, required package, field values/provenance, editable drafts, review status and simulated submission receipt.

The summary is understandable to a non-specialist; technical detail is one click away. Show concise observable actions and evidence rather than requiring hidden model reasoning to explain a result.

### 3.2 Interaction rules

- All three components are clickable from the exploded view and from a keyboard-accessible list.
- Switching component loads its own case and event cursor; updates cannot leak into another component's state.
- Initial loading, active work, waiting for evidence, interruption, retry, completion and stale decisions have explicit states.
- The current recommendation and initial snapshot remain legible during reassessment.
- “Accept option” is enabled only for currently eligible candidates in the current decision version.
- Evidence and document panels support back navigation without resetting the scene.
- 3D animation is driven by domain state; success in the animation corresponds to the scripted completed workflow and evidence-based applicability result.
- Support keyboard focus, meaningful labels, non-colour status indicators and reduced motion. At narrow widths, stack scene and panels while preserving selection and status.

## 4. Functional requirements

Every requirement below is part of the complete product specification. Delivery order is in section 15.

### FR-01 Engine and component cases

Load a manifest with engine/configuration identity, asset paths, mesh names, camera anchors, component transforms, labels, case IDs and demonstration failure/restoration states. Each component maps to one independently persisted case. Store required part identities and technical parameters separately from mesh geometry.

Acceptance: three hotspots work by pointer and keyboard; all map to the correct case; switching and refresh preserve state. The primary component animates removal and the selected replacement's insertion.

### FR-02 Requirement and evidence model

Create a versioned requirement set per engine/component/configuration and route. Include exact identity/revision/effectivity, documented interchangeability, relevant technical interfaces, applicable supplier/site conditions and applicable regulatory/documentation requirements. Discovery supplies the actual parameter list and authoritative evidence.

Each check returns `pass`, `fail` or `unknown`, with requirement ID, evidence reference(s), rule version and explanation. Mandatory unknowns remain pending; preference scores apply after eligibility is established. Normalize units and maintain original values. Conflict resolution follows recorded authority/revision rules; preserve superseded evidence and contradictory findings.

Acceptance: every eligible candidate passes all applicable mandatory checks; every displayed compatibility claim links to the underlying check results and source evidence.

### FR-03 Parallel BUY and MAKE sourcing

BUY workers find offers for existing spare parts and collect identity, condition/traceability, quantity, seller/site, stock, price, delivery and applicable supporting records. MAKE workers find capable manufacturing sites and collect design/document basis, capability/process evidence, capacity, tooling, qualification dependencies, inspection, quote and delivery inputs. Discovery defines route-specific evidentiary requirements before eligibility is awarded.

Use source adapters for supplier catalogues, search results, seeded offers and replies. Normalize to a shared CandidateOffer schema, with distinct route-specific fields. Separate the supplier legal entity from the physical site, manufacturer, seller and logistics route.

Acceptance: same case can contain BUY and MAKE offers; source-specific records are normalized; a promising MAKE capability is distinguishable from an eligible, fully supported plan.

### FR-04 Document intelligence

Ingest source files into governed storage with hashes, versions and provenance. Use document parsing and schema extraction to produce typed facts, citations and extraction confidence where supported. Validate identifiers, date formats, units, entity/site association and required fields in code. Evidence status reflects validation and source authority as well as extraction output.

Acceptance: document → extracted fact → check → recommendation can be followed in the UI. Reprocessing identical content is deduplicated; a new revision creates a new evidence version.

### FR-05 Adaptive evidence investigation (improvement B)

A checker can emit an EvidenceGap specifying the unresolved requirement, candidate/site, desired document/fact, allowed sources and priority. The coordinator dispatches a focused follow-up, records its outcome and reruns affected checks. Default configurable budget: two follow-up attempts per candidate per investigation, with a total run-level tool/time budget. Stop when evidence is sufficient or budget is reached; expose remaining gaps as pending work.

Acceptance: at least one verification case resolves a gap through targeted retrieval; another retains a clear pending result when evidence is insufficient. The judge-facing scripted case may use complete favourable evidence.

### FR-06 Supplier/site reliability

Separate historical reliability (such as delivery/quality measures with a stated observation window) from current exposure (such as a port closure). Store metric value, unit, denominator/period, source and demo-fixture flag. Show favourable values in the curated demo. The new disruption may change schedule or exposure without reducing a supplier's historical reliability score.

Acceptance: metric labels explain what numbers mean; favourable fixtures are not represented as measured real-world company performance; site-specific evidence cannot silently qualify every site of the same company.

### FR-07 Regulatory route and form applicability

Maintain a UK CAA-focused applicability catalogue populated by the discovery agent. Requirements and forms are associated with the transaction/engineering route, relevant organisation role, activity and component/configuration. Distinguish supplier onboarding/internal quality records, supporting release/traceability records, and an actual authority application where applicable.

For each required document record: authority/owner, exact current title/template/version, source URL, applicability rule, responsible applicant/signatory, required supporting evidence and completion rules. The frontend explains why each item belongs in this case. The actual set is a discovery output, not an assumed universal “new supplier” form.

Acceptance: every generated item has a validated applicability rule and template reference. If research finds no authority application for the selected route, show the actual applicable package and simulate its correct destination. If an authority-application branch is required to demonstrate that capability, discovery must establish a credible applicable branch before enabling it.

### FR-08 Eligibility and transparent ranking

Eligibility is evaluated using deterministic mandatory gates backed by the versioned requirements. Rank only eligible offers in the ready-to-select shortlist. Show pending/unqualified offers separately with their gaps. Retrieval relevance orders evidence discovery; it does not establish technical eligibility.

Default preference score: `100 × (0.45 recovery_speed + 0.25 landed_cost + 0.20 historical_reliability + 0.10 current_resilience)`, each term normalized to [0,1] using versioned scenario thresholds. Higher is better. Store thresholds, inputs, conversions, weights and tie-breaking. This is a product default, editable in configuration; confirm it against fixtures before freeze. Ties: lower recovery time, then lower landed cost, then stable candidate ID. Missing required preference inputs produce a disclosed pending comparison or explicit documented estimate.

Show score components and estimated recovery time/cost in their original units. Evidence coverage is shown separately from likelihood of physical suitability. Recompute only affected values after a change.

Acceptance: the UI and API reproduce the same ranking from saved inputs; order remains stable on rerun; a low-price offer cannot compensate for a mandatory failed/unknown check.

### FR-09 Recovery scheduling and what-if comparison (improvement D)

Represent each route as a dependency plan: procurement/manufacture, applicable qualification, transport, inspection and installation readiness. Store durations with units, assumptions, ranges and source. Parallel steps use a critical-path calculation; currency/cost totals use a recorded FX version when conversion is required. Distinguish elapsed recovery time from summed labour time.

Start with deterministic dependency scheduling. Add OR-Tools CP-SAT when capacity slots, calendars or resource constraints affect a decision; its result includes feasibility, constraints, solve status and objective. If estimates are scenario fixtures, label them. The LLM explains a calculation; code/solver computes it.

Acceptance: a changed shipping or manufacturing input changes the dependent completion time correctly; BUY/MAKE plans expose their dependencies and assumptions; the preferred plan follows the saved preference configuration.

### FR-10 Continuous monitoring and impact propagation (improvement C, hero feature)

Monitor both evidence/business changes and the reference project's signal categories: geopolitical/tariff, climate, logistics and port/facility disruption. Implement Databricks-native adapters and normalisation. Each source has a polling/ingestion policy, source identity, freshness, publication/observation/effective timestamps and health. Scheduled ingestion uses Lakeflow/jobs where suitable; immediate scripted injection uses the same ingestion service.

Resolve a signal to affected entities, sites, geographies/routes or materials using explicit relationships. Record assertions and their evidence/confidence separately. The primary scripted signal uses a verified scenario relationship so the impact is reproducible. Deduplicate source IDs/hashes and preserve revisions/retractions/expiry.

For every change:

1. Persist the normalized ChangeEvent and immutable input revision.
2. Traverse dependencies to identify affected offers, checks, schedules, documents and cases.
3. Mark dependent current outputs stale immediately; leave independent checks reusable.
4. Schedule targeted work with bounded retry/concurrency and a per-case revision target.
5. Recompute and persist a new immutable decision snapshot.
6. Publish a diff with trigger, impact path, changed inputs/checks/ranks and user action needed.
7. If selection/paperwork already exists, invalidate affected downstream versions and request reconfirmation before a new simulated submission.

Monitoring lifecycle: persist CaseSubscription records scoped by scenario run, case, dependency IDs/scope, dependency revision, owner and status `active|paused|closed`. Create initial subscriptions at case creation; read already-active signals into the first requirement/input snapshot. Reconcile subscriptions after sourcing, every published decision and reselection using both previous and new dependencies. A restored visual case remains actively monitored until the user pauses/closes its monitoring. Reset creates a new run namespace and pauses the earlier run's subscriptions while preserving its read-only history; signal injection targets one run. Shared entities may affect several active cases inside a run, but never implicitly cross isolated run namespaces. A monitoring-status command is versioned and auditable.

Effective-time and expiry transitions are scheduled changes: register timers for future-effective signals/rules/documents and expiry/retraction boundaries; emit idempotent ChangeEvents through the same invalidation gateway at the transition. Seeded mode advances the scenario clock and executes due transitions deterministically. Paused cases reconcile all active changes and expired evidence before resuming or becoming selectable. Source health/freshness is part of currentness policy.

Acceptance: primary script changes D1 → D2 and visibly reorders the shortlist; an unrelated signal leaves the case decision unchanged; a repeated signal does not duplicate work; evidence changes can trigger the same mechanism; a corrected/retracted signal can lead to a new version that restores earlier conditions.

### FR-11 Evidence graph and provenance (improvement A)

Represent the connected evidence model in normalized Delta tables and relationship rows: EngineConfiguration → ComponentRequirement → CandidatePart/Offer → Supplier/Site/Route → Evidence → CheckResult → Decision → FormField. Relationship rows include type, source evidence, valid/effective time and recorded time. Graph traversal may use SQL/Python adjacency queries; the PRD does not require a separate graph database.

Acceptance: every recommendation can display its supporting chain; impact propagation reaches only dependent records; engine/part revisions and supplier sites are distinct entities.

### FR-12 Acceptance and version control

Acceptance requests include candidate, decision ID, evidence snapshot hash, expected case revision and idempotency key. In one operational transaction, confirm current eligibility and versions, then persist the accepted selection and outbox work item. Concurrent changes return `409 STALE_DECISION` with the latest revision. Repeating the same request/key returns the same selection.

Acceptance: a stale UI cannot accept a superseded recommendation; concurrent signal processing and acceptance cannot create contradictory current selections; selection records identify the user and accepted snapshot.

### FR-13 Applicable documentation and simulated submission

Acceptance triggers document planning and autofill automatically. Populate actual discovered templates or a faithful field representation linked to the official online form version. Each field stores source fact/evidence/check, transform, value, origin, review state and document version. User edits retain attribution and trigger relevant validation. Missing attestations or signatures remain explicit completion tasks for the responsible person.

Submission operates through a simulation adapter. It rechecks current selection/evidence/template versions and required-field readiness, then persists a payload hash, destination type, package version, timestamp and unique simulated receipt. Render/download a reviewable package and receipt. Completing the simulation can advance the demonstration's installation/restoration state.

Drafts and packages are immutable versions with transactional current pointers. Generation uses a stable generation ID and binds selection, evidence set, template/applicability versions, starting draft version and case revision. It conditionally publishes only if these still match and no currentness barrier exists. A delayed generator preserves its result as superseded instead of overwriting a newer edit or reviewed package. User edits create new draft/package versions and reset affected review states; review approval binds the exact package hash/version. Template and applicability-rule updates enter the same invalidation gateway as evidence changes.

Simulated submission commits in a Lakebase transaction that validates the current reviewed package hash/version, current selection and case revision, required-field readiness and absence of currentness barriers, then creates the unique receipt and outbox state. A conflicting edit/change wins or loses atomically; it cannot create a receipt for a package that was stale at commit. A later change preserves the historical receipt and invalidates only subsequent/current actions. Stable operation keys prevent retry duplication; a new operation requires a newly valid reviewed version.

Acceptance: selected values match displayed populated fields; duplicate requests produce one receipt; stale drafts are regenerated/reviewed after relevant changes; the user can inspect what was simulated as submitted.

### FR-14 Durable execution, activity and case isolation

Persist graph checkpoints and register AgentKit recovery handling. Emit typed domain events that the frontend can reconnect and replay in order. Separate application events from MLflow's diagnostic traces; link them by IDs. Implement stable side-effect IDs, uniqueness constraints and an outbox for selections/document generation/simulated submissions. Recovery handlers bound attempts; application errors have their own retry policy.

Acceptance: deployed worker interruption plus UI reconnect resumes from a valid checkpoint, displays coherent progress and creates no duplicated final actions. Primary and secondary case events remain isolated.

## 5. Technical architecture

### 5.1 Target stack

| Layer | Default choice | Responsibility |
|---|---|---|
| Product frontend | React + TypeScript + Vite | Main workspace and typed API/event client; existing source UI patterns may be ported. |
| 3D | Three.js via React Three Fiber + Drei; glTF/GLB assets | Assembly, hotspots, camera, replacement animation; mesh manifest from discovery. |
| API/BFF | FastAPI + Pydantic | Browser-safe API, auth, case projections, commands, event bridge and downloads. |
| Orchestration | LangGraph | Explicit state machine with focused agent/tool loops and parallel sourcing branches. |
| Agent hosting | Current Agent Bricks CLI + AgentKit DurableAgentServer + Agent Runtime | Invocation execution, event persistence, deployment and recovery integration. |
| Models | Claude through an enabled Databricks model interface | Investigation, schema interpretation and explanations; model ID chosen in preflight. |
| Evidence/data | Delta Lake + Unity Catalog tables/volumes; SQL warehouse | Versioned entities, facts, relationships, requirements, checks and analytical history. |
| Retrieval | AI Search with Delta Sync, hybrid query and reranking | Evidence discovery with metadata filters and version references. |
| Operational storage | Lakebase Postgres native tables | Cases, commands, selections, current revision pointers, documents, outbox, event projections and receipts. |
| Execution state | AgentKit Runtime Store plus supported LangGraph/session checkpoint integration | Invocation state and graph progress; configure one graph-checkpoint authority. |
| Ingestion | Lakeflow Jobs/pipelines and connector workers | Document parsing/extraction, external changes and scheduled signal ingestion. |
| Document AI | ai_parse_document + ai_extract through available SQL/REST interfaces | Typed extraction and source localization. |
| Observability/evaluation | MLflow 3 tracing and custom scorers | Run inspection, tool traces, comparisons and domain correctness measures. |
| External discovery | Linkup adapter, subject to access/preflight | Fresh supplier/risk evidence; seeded connector shares the same contract. |
| Scheduling | Python dependency scheduler; optional OR-Tools | Recovery-plan calculations and constrained scheduling. |
| Design | Figma | Reviewed interaction/design system and product-design submission evidence. |

Dependency versions must be resolved and locked after a small integration spike. The reference repository pins Python 3.13; Databricks recommends 3.12 for current CLI projects. Prefer 3.12 for the migration spike and explicitly adapt the package constraint; retain another version only after integration checks. Code reuse is at the workflow/service/UI level; MongoDB queries and drivers are replaced.

### 5.2 Flow

Browser → FastAPI BFF → Agent Runtime invocation → LangGraph nodes/tools → SQL/AI Search/AI Functions/external connectors. Domain events return through the event bridge to the browser. MLflow records diagnostic execution. Operational commands commit to Lakebase; outbox records drive asynchronous side effects and versioned analytical projections into Delta. Evidence ingestion writes Delta/volumes, synchronizes search and publishes a change only when its usable evidence version is known.

### 5.3 Storage authority and consistency

- Lakebase is authoritative for mutable case revision, command status, selection, document version pointer, outbox and simulated receipt. Use native writable tables, not Delta-synced read-only tables, for these writes.
- Delta/volumes are authoritative for immutable ingested evidence versions, normalized facts, requirements/rules, relationship versions and analytical snapshots. Lakebase stores immutable evidence-set IDs/hashes and decision payloads used by transactional acceptance.
- Managed Runtime Store records invocations/events; graph checkpoints record graph state. Their meanings are distinct. Application records do not depend solely on agent conversation memory.
- A decision binds an explicit `input_revision`, `evidence_set_id`, `requirements_version`, `ranking_config_version` and relationship/signal versions. A transactional case revision in Lakebase sequences invalidations/acceptances; relevant Delta changes first register an invalidation command there. Every change producer uses this gateway.
- Search index freshness is observable. Queries return evidence-version IDs. Exact facts and final gates are resolved from the authoritative snapshot; an unsynchronized index must not make a fresh document appear absent. Provide exact-ID/SQL retrieval for newly ingested evidence while indexing completes.
- Use transactional outbox and idempotent consumers for operational-to-analytical projection. Persist delivery status, retry count and last error. Projections are labelled with their source revision.

### 5.3.1 Change activation and publication protocol

All evidence, signal, requirement, template and relationship change producers use this protocol. Its consistency boundary is observed/registered input; an external event not yet received is represented by source freshness, rather than retroactive knowledge.

1. Register the incoming change and a conservative run-namespace `pending_change` barrier in Lakebase atomically before activating a new authoritative version. Selection, current-decision publication and simulated submission check this barrier inside their own commit transaction.
2. Stage immutable new versions in Delta/volumes and their operational version manifest. Resolve impacted active subscriptions using the union of old and new relationship paths, including removed dependencies and newly exposed cases. If scope is uncertain, retain the conservative namespace barrier.
3. Durably fan out per-case invalidation commands; each increments the case input revision and records the target evidence/rule/signal/template versions and downstream invalidations. Fan-out uses stable change/case keys. A partially failed fan-out is retried idempotently while the namespace barrier remains active; health shows the pending change.
4. Once every affected subscription has a durable invalidation, atomically activate the new version manifest and mark registration complete; clear the namespace barrier. Affected cases retain their own stale/pending-reassessment status. Unaffected cases can continue. In the small demo namespace this is one transactional publication of the operational manifest and fan-out completion; Delta files have already been staged.
5. Schedule/coalesce per-case reassessments against the newest pending revision. One coordinator owns the execution generation; older tasks can finish but cannot become current. Search synchronization can complete asynchronously if exact authoritative evidence retrieval is used and recorded.

`persist_decision` uses a Lakebase transaction/compare-and-swap: verify target case input revision, dependency-version manifest, active execution generation and no pending change barrier. Persist an immutable decision and advance current pointers/events only if all match. Outdated results are retained as historical/superseded, return a superseded status and never emit a current `decision.updated` event. Record durable pending target revisions so a crash cannot lose the newest reassessment. Publish domain events through the committed outbox, not before transaction success.

Selections and simulated submissions take compatible row locks or serializable transactions on the case/namespace version records so a concurrent barrier/invalidation cannot pass unnoticed. The implementation spike must test the chosen locking/isolation strategy, including a run-wide change affecting multiple cases.

### 5.4 Migration map and source pin

Reference repository: https://github.com/mongodb-industry-solutions/retail-supply-chain-management  
Reviewed source commit: `c8cebc3c8924b2355fbb63d3878e34616fefd460`.

Reuse/adapt FastAPI route patterns, LangGraph graph organization, sourcing/audit logic, bounded retrieval, rank explanation, typed events and useful frontend components. Replace `core/db.py`, Motor/PyMongo calls, Atlas aggregation stages, embedding/index setup, memory persistence and database-specific telemetry through explicit service interfaces. Rewrite retail signal/requirement models for aerospace. Existing hybrid retrieval, citation audits, expiry checks, memory, human selection and streamed progress are baseline capabilities; the product extensions are part/configuration applicability, two sourcing routes, connected evidence, adaptive investigation, continuous reassessment and selection-to-paperwork execution.

Interface boundaries: `EvidenceRepository`, `OfferRepository`, `SignalRepository`, `CaseRepository`, `EvidenceSearch`, `ModelClient`, `DocumentExtractor`, `DocumentRenderer`, `SubmissionSimulator`, `EventPublisher`, `RecoveryScheduler`. Domain code receives these interfaces, not a database driver's collection object.

## 6. Domain contracts

All IDs are strings; UUIDs for run/command/event IDs. All timestamps use UTC ISO-8601 with timezone; monetary values use decimal representations plus ISO currency; durations have explicit units. JSON examples are contracts to be formalized in Pydantic and generated TypeScript, not an implementation claim.

### 6.1 Entities and minimum fields

| Entity | Minimum fields beyond ID |
|---|---|
| EngineConfiguration | engine_id, display_name, configuration_revision, component_instance_ids, scenario_manifest_version |
| ComponentInstance | engine_id, component_id, part_identity, revision, position, requirement_set_id, mesh_mapping, case_id |
| Case | engine_id, component_id, state, revision, current_decision_id, initial_decision_id, mode, active_run_id |
| Supplier / Site | legal_entity_id/name; site_id/address/geography; roles/capabilities; qualified_scope references; metric references |
| CandidateOffer | route BUY/MAKE, part_id/revision, supplier_id, site_id, manufacturer/seller roles, quantity/condition, quote_version, price/currency, stock/capacity, logistics_route_id, plan_id, evidence_ids |
| EvidenceVersion | document_id, version_id, hash, source_url/storage_uri, authority/type, issuer/subject/site, revision, effective/expiry/retrieved_at, data_origin, validation_state, supersedes_version_id |
| ExtractedFact | evidence_version_id, field, typed_value, unit, original_value, locator/page/bbox, confidence, validation_state |
| Requirement | requirement_set/version, route/applicability expression, mandatory, fact inputs, evaluator_id/version, evidence authority policy |
| CheckResult | case/candidate, requirement_id/version, result, input/evidence versions, explanation, evaluated_at, dependency_ids |
| Relationship | from_id/type, to_id/type, relation_type, evidence_ids, effective_from/to, recorded_at, revision |
| ReliabilityMetric | subject_id/site_id, metric_name, value/unit, numerator/denominator/window, source_evidence_id, data_origin |
| RecoveryPlan | candidate_id, steps/dependencies/durations, assumptions, finish_time, cost breakdown, solver/status, input_versions |
| RiskSignal | source/source_event_id/version, category, scope/entity/site/geometry/route, assertion, published/observed/effective/expiry times, provenance, confidence, status active/corrected/retracted, data_origin |
| ChangeEvent | trigger_type, source_version, affected_entity_ids, scope, effective_at, received_at, revision/dedup_key, activation_state, fanout_state |
| CaseSubscription | scenario_run_id, case_id, dependency_ids/scope, dependency_revision, active/paused/closed, owner, reconciled_change_cursor |
| ChangeBarrier / VersionManifest | namespace, pending_change IDs, activation_version; authoritative version references and per-case target revisions |
| ExecutionGeneration | case_id, generation_id, target_input_revision, dependency_manifest_hash, pending_target_revision, status |
| DecisionSnapshot | case_id/revision, input_revision, immutable candidate/check/score/plan payload, evidence_set_id/hash, ranking_version, trigger_id, created_at |
| DecisionDiff | from/to decision IDs, trigger_id, affected paths, changed fields/ranks, rerun/reused checks, downstream invalidations |
| Selection | case/candidate/decision IDs, accepted_case_revision, evidence_hash, actor, accepted_at, idempotency_key |
| FormTemplate / Draft | title/owner/version/source, applicability_rule, field schema; selection/version, field_values/provenance, validation/review state, package hash |
| SimulatedReceipt | selection/package versions, destination_type, payload_hash, idempotency_key, status, simulated_at |
| OutboxItem | operation_id/type, aggregate_id/revision, payload, state, attempts, available_at, last_error |

Every fixture-derived entity carries `data_origin: synthetic_demo`; externally sourced entities carry `public_source`, `provided_document` or another explicit origin. An extracted confidence score is separate from a check result or a measured reliability metric.

### 6.2 Agent task output

Every agent capability returns structured output: `task_id`, `case_id`, `input_revision`, `status`, `facts`, `evidence_refs`, `check_refs`, `gaps`, `next_actions`, `summary`, `tool_usage`. Validate against schema before merging. Agent prose cannot directly mutate current eligibility or submission status; tools enforce domain transitions.

### 6.3 Workflow states

Case: `ready → investigating → recommendations_ready → reassessing → recommendations_ready → selected → documents_preparing → documents_ready → submission_simulated → installation_visualized → restored_visualized`.

Auxiliary states: `waiting_for_evidence`, `interrupted`, `failed`, `selection_stale`, `documents_stale`. A change can enter reassessment from any active state. Persist the prior stable state and revision. After selection-related invalidation, require renewed current-snapshot acceptance before new paperwork/submission. A previously created receipt remains historical and links to its old versions. A UI component switch does not change a workflow state.

Maintain a separate component visual state (`assembled`, `exploded`, `failed`, `removed`, `replacement_ready`, `installed`, `running`) and map it to explicit demo commands/domain prerequisites. This keeps animation and agent execution independently recoverable.

## 7. API and event contract

Browser calls the BFF; the BFF handles Databricks authentication and runtime protocol details. Generate OpenAPI and TypeScript from canonical schemas.

| Method and route | Contract |
|---|---|
| GET `/api/v1/engines/{engine_id}` | Engine manifest and component case summaries. |
| GET `/api/v1/cases/{case_id}` | Current case projection, revision, run state and event cursor. |
| POST `/api/v1/cases/{case_id}/investigations` | Start/resume command with expected_revision, mode, idempotency key; returns 202 command/run ID and event URL. |
| GET `/api/v1/cases/{case_id}/decisions/{decision_id}` | Immutable decision, candidates, score breakdown and evidence references. |
| GET `/api/v1/cases/{case_id}/diff?from={id}&to={id}` | DecisionDiff including dependency path. |
| POST `/api/v1/scenario-runs/{run_id}/signals` | Presenter-controlled labelled signal injection through normal signal service; idempotent. |
| POST `/api/v1/cases/{case_id}/selections` | Candidate/decision/evidence hash/expected_revision/idempotency key; returns selection or 409. |
| GET `/api/v1/cases/{case_id}/documents` | Current and historical packages/drafts, readiness and generation status. |
| PATCH `/api/v1/documents/{draft_id}` | Field edits/review actions with expected_version and idempotency key; retains provenance. |
| POST `/api/v1/cases/{case_id}/simulated-submissions` | Current selection/package versions and idempotency key; returns receipt or readiness/conflict details. |
| GET `/api/v1/evidence/{version_id}` | Authorized source metadata, locator and document-preview/download reference. |
| GET `/api/v1/cases/{case_id}/events?after={sequence}` | Ordered reconnectable domain SSE stream. |
| POST `/api/v1/scenario-runs` | Create/reset isolated demo run from manifest/fixture version; return case map. |
| PATCH `/api/v1/cases/{case_id}/monitoring` | Active/pause/close or resume reconciliation, expected_revision and idempotency key. |
| POST `/api/v1/cases/{case_id}/visual-actions` | Validated presentation action such as focus/explode/install/restore; returns visual state. |
| GET `/api/v1/health` and `/api/v1/readiness` | Process readiness and dependency capability summary; detailed diagnostics restricted to team view. |

All mutations accept `Idempotency-Key`; a reused key with different payload returns conflict. Start-like asynchronous calls return 202 and polling/event references. Synchronous changes return committed revisions. Errors use `{code,message,retryable,case_revision,details,correlation_id}`. Distinguish invalid input (422), forbidden (403), stale/conflicting (409), unavailable dependency (503) and failed run status. Frontend deduplicates events by ID and orders per-case sequence.

### 7.1 Domain event envelope

```json
{
  "schema_version": "1.0",
  "event_id": "uuid",
  "sequence": 42,
  "occurred_at": "2026-11-14T15:00:00Z",
  "scenario_run_id": "uuid",
  "case_id": "case-primary",
  "case_revision": 7,
  "invocation_id": "uuid",
  "task_id": "task-id",
  "type": "decision.updated",
  "summary": "Shipping disruption changes the preferred recovery plan",
  "data": {"previous_decision_id": "D1", "decision_id": "D2", "trigger_id": "signal-1"},
  "evidence_refs": [],
  "trace_id": "mlflow-trace-id",
  "data_origin": "synthetic_demo"
}
```

Required event families: `case.started`, `task.started/completed/failed`, `tool.started/completed/failed`, `evidence.ingested/extracted/validated`, `gap.opened/resolved`, `check.completed`, `signal.received/matched`, `impact.detected`, `reassessment.started`, `decision.created/updated`, `selection.accepted/stale`, `documents.preparing/ready/stale`, `submission.simulated`, `visual.updated`, `run.interrupted/recovered/completed/failed`.

SSE `id` is the case sequence; heartbeats are separate from persisted domain events. On a retained-history gap send a snapshot-required control event and refresh the case. Persist enough domain history to reconstruct every demo run. Runtime native events use `/api/invocations`; model endpoints are a separate API. BFF adapts these surfaces to this product contract.

## 8. Agent workflow implementation

### 8.1 Graph outline

`load_case → snapshot_requirements → parallel(source_buy, source_make) → normalize_offers → parallel(extract_and_validate, supplier_site_checks, technical_checks, regulatory_route) → resolve_gaps_if_budget → evaluate_eligibility → schedule_and_rank → persist_decision → await_commands`.

Checks declare prerequisites; technical/regulatory workers may first produce pending checks and resume after evidence extraction. “Parallel” means independent work may overlap, not that workers bypass dependency readiness. A reassessment entry point loads the change impact, reuses unaffected results with version references, runs the affected subgraph and persists a new snapshot. Selection starts `revalidate_selection → plan_documents → autofill → validate_package → await_review → simulate_submission`.

The coordinator owns canonical graph state. Workers return typed patches; merge by candidate/task IDs with deterministic reducers. Bound per-case workers, model/tool concurrency, retries and token/tool budgets through configuration. Preserve task-level status rather than blocking the whole UI on one worker.

### 8.2 Core tools

`get_requirement_set`, `query_candidate_offers`, `search_public_sources`, `retrieve_evidence`, `extract_document_fields`, `resolve_part_identity`, `evaluate_requirement`, `get_supplier_site_metrics`, `match_signal_exposure`, `compute_impact`, `build_recovery_plan`, `rank_eligible_offers`, `persist_decision`, `prepare_document_package`, `simulate_submission`, `emit_domain_event`.

Use typed arguments, explicit permissions and validated outputs. Small known data operations can call Python/SQL adapters directly; MCP is useful where a managed/external tool interface helps. Use one selected model integration path initially, then add model routing only with measured benefit.

## 9. Discovery work packages

These are implementation discovery tasks. The PRD is complete as a product specification while the chosen assets, identities, evidence and forms remain explicit dependencies.

### DISC-01 Engine/3D/component discovery

Compare candidate assets for licence, separable mesh structure, performance, coherent engine identity, three nearby component meshes and supporting document availability. Select a primary component with a strong credible replacement story; name the two nearby components. Provide `asset_manifest.json`, asset source/licence notes, mesh inventory, camera/transform mappings, component identity mapping and the reason for selection. If visual asset identity differs from evidence identity, describe it explicitly as a representative assembly and preserve the actual case identity in the data/UI.

Completion gate: all three components can be independently focused/removed/reinserted, and the evidence investigation identifies a plausible evidence set for each. Generated imagery may support presentation, but the clickable assembly requires an actual inspectable mesh structure.

### DISC-02 Engineering and supplier evidence discovery

Identify legally accessible engine/component manuals, illustrated parts/effectivity or interchangeability sources, relevant drawings/specifications, supplier capability/site records, quotation/stock/capacity information, quality/traceability/release records and required process/inspection evidence. Determine the exact minimum evidence per route and component, document authority/revision precedence and any evidence gaps. Deliver an evidence inventory with URLs/access status, versions, locators, usage conditions, source confidence, required field schemas and a gap register. Use clearly identified scenario fixtures for unavailable commercial values; do not silently assign fabricated documents to real companies.

Completion gate: primary selected route has an evidence-complete favourable demo dataset, all mandatory rules have a source basis, and secondary routes have defined complete/pending outcomes.

### DISC-03 UK CAA applicability and actual form discovery

Research current official UK CAA material for the chosen organisation roles, BUY/MAKE routes and component/configuration. Identify which actions need internal onboarding/quality approval, supporting documents, engineering/production/maintenance processes or an authority application. Verify exact current form/online-service titles, responsible applicants/signatories, fields, supporting attachments and applicability rules. Deliver versioned template registry, field mapping, applicability decision tree and example package manifest. Actual searches/downloads belong to this work package, not PRD authoring.

Completion gate: every enabled generated document has a current authoritative reference and correct route; the displayed government application branch, if any, is demonstrably applicable. Simulation can faithfully represent an online application without automating its real submission.

### DISC-04 Databricks workspace capability spike

Verify serverless/Unity Catalog, chosen model and region, SQL read/write, volume access, AI Functions, AI Search, Lakebase, Apps/Runtime, managed checkpoint/session stores, OAuth and external connector egress. Record actual workspace features, quotas, package versions and results. Do not put tokens in records. Account for current CLI Beta status and Free Edition limits if this is that edition.

Run a minimal deployed LangGraph invocation that calls the model, SQL and search; writes/resumes a checkpoint; records an MLflow trace; emits and reconnects events. Test a permitted external search call and Lakebase token rotation. Configure tool identity explicitly: recoverable background tools use app identity where supported; current request-user MCP credentials have different recovery constraints. Confirm both recovery handler and checkpoint adapter operate together. Local in-process development state is not a deployed durability test.

Completion gate: capability matrix and lockfile support the chosen deployment. If a feature is unavailable, record the gap and select an alternative Databricks-supported path without changing the user-visible contract; escalate a material product change to the team lead.

## 10. Seeded fixture specification

Deliver versioned scenario manifests and ingestion scripts, reproducible IDs/clock/seed, complete source provenance and expected outputs. Each case has its own data and can run independently. Shared supplier/site/route dependencies can affect multiple cases and should be demonstrable in an optional expanded impact view.

Illustrative primary ranking fixture, to instantiate with consistent cost/schedule inputs and the actual component identity:

- Offer A: eligible BUY, favourable reliability, initial estimated readiness day 4.
- Offer B: eligible BUY, favourable reliability, initial readiness day 6.
- Offer C: MAKE route with a longer plan and documented route-specific conditions.
- The initial saved preference inputs make A rank first.
- A scenario port/route disruption changes A's readiness to day 11 while B stays day 6; other score inputs are configured so B becomes preferred. Keep cost/reliability values transparent and consistent with the scoring function.

These numbers are scenario design examples, not measured forecasts. Freeze the actual fixtures only after recomputing the expected rank/schedule using an independent calculation. Signal scope and offer route must share an explicit dependency. A second fixture changes document evidence to test the same invalidation pipeline.

## 11. Non-functional requirements and deployment checks

- Responsiveness targets: scene controls remain interactive, command acknowledgment under 2 seconds when dependencies are warm, first progress event under 3 seconds, at least 30 fps during the main animation on the demonstration laptop. Measure and report actual warm/cold performance; do not represent targets as observed results.
- Backend scales work through bounded async queues; SQL/AI extraction operations do not block the browser request. Poll long-running operations with recorded status and deadlines.
- Observability: correlation IDs from browser command through task/tool/check/decision/receipt; MLflow spans include tool latency, retrieval mode, evidence IDs and model/package version. Log sanitized metadata, costs/tokens where available and dependency errors.
- Auth: browser uses a controlled app/BFF session; server credentials remain server-side. Agent Runtime Apps authentication uses supported OAuth. Grant service identity access to required schemas, indexes, volumes and tools. Refresh expiring Lakebase OAuth connections.
- Source documents are untrusted data; tool access is authorized by application policy. Parse/extract validated fields and use typed, parameterized SQL. External instructions inside documents cannot change workflow permissions.
- Resource behaviour: prewarm supported endpoints, observe quota/status, show dependency failures and resume safely. Store artifacts and run history durably across app restarts.
- Data quality: foreign key/entity checks, unique evidence hashes/versions, compatible units, explicit dates/timezones, site identity checks and unresolved conflict reporting.
- Accessibility: keyboard-accessible component list, readable text, focus management, reduced motion and textual equivalents for 3D status.

## 12. Verification and acceptance matrix

Verification fixtures include representative adverse/edge cases; the curated presentation can remain favourable. Record commands, environment, fixture version, expected/actual result, trace/run IDs and unresolved issues. A passing smoke test is not a claim of regulatory or engineering certification.

| ID | Observable check | Expected result |
|---|---|---|
| AC-01 | Drive all three hotspots/list items in browser. | Correct mesh focus and isolated case; state survives switching/refresh. |
| AC-02 | Run primary investigation using actual deployed integrations. | D1 produced with at least two eligible offers and source-backed checks. |
| AC-03 | Inject mapped scenario disruption after D1. | Correct path shown; affected outputs reassessed; D2 changes preferred offer as fixture specifies. |
| AC-04 | Inject unrelated, duplicate, corrected and retracted signals. | Correct invalidation scope, deduplication and new versions; no spurious case changes. |
| AC-05 | Update technical evidence/version while a case is active. | Affected checks/drafts become stale and are refreshed against the new version. |
| AC-06 | Compare ranking/schedule against independently calculated fixture expectations. | Eligible set, score order, critical path and monetary units match. |
| AC-07 | Missing/expired/wrong-site/conflicting evidence and a near-match wrong part. | Exact expected pass/fail/unknown; mandatory unknown/fail cannot be accepted. |
| AC-08 | Resolve one evidence gap through a focused follow-up. | New evidence reference, rerun affected check, updated decision; bounded attempts respected. |
| AC-09 | Accept current and stale decisions, including concurrent change. | One valid selection or 409; retained decision/evidence hash is exact. |
| AC-10 | Auto-generate applicable forms; inspect edited fields and download package. | Correct template/route, field provenance, readiness, versioning and visible values. |
| AC-11 | Repeat simulated-submission request; change evidence before submission. | One receipt per valid operation; stale package requires current review/selection. |
| AC-12 | Interrupt a deployed worker; reconnect browser stream. | Recovery from checkpoint, ordered/deduplicated activity, no repeated side effects. |
| AC-13 | Run both secondary component workflows through an eligible accepted route. | Shared graph/contracts; distinct inputs, decisions and completed packages. |
| AC-14 | Drive replace/restore animations. | Correct selected visual part and successful workflow prerequisites; keyboard/reduced-motion path works. |
| AC-15 | Verify search freshness after Delta update and a reranker fallback. | Correct evidence version resolved; actual retrieval mode recorded. |
| AC-16 | Cold start, connector failure, extraction timeout and quota/resource interruption. | Actionable state, retry/resume path, durable case; mode/replay provenance stays visible. |
| AC-17 | Browser console, narrow viewport and keyboard navigation. | No uncaught flow-breaking errors; usable complete flow. |
| AC-18 | Reset and run the demo twice. | Fresh isolated runs, same expected seeded outcome, retained prior history. |
| AC-19 | Two changes arrive while D2 computes; finish workers out of order. | Only newest valid generation becomes current; old results are historical; no stale current event or acceptance. |
| AC-20 | Shared-site change affects two cases; race acceptance/submission with delayed or failed fan-out and a relationship update. | Barrier blocks conflicting commits until complete registration; old/new dependency union reaches both cases; retries are deduplicated. |
| AC-21 | Open case after active disruption; advance clock through evidence expiry; pause/resume and reset runs. | Initial snapshot includes active change, timers invalidate correctly, resumed cases reconcile, namespaces remain isolated. |
| AC-22 | Race form generation, field edit/review, template change and simulated submission. | Immutable versions, guarded publication and atomic reviewed-hash checks preserve edits and prevent stale/duplicate receipts. |

### 12.1 MLflow evaluation

Use code scorers for mandatory-gate correctness, unsupported eligibility/acceptance, exact citation-version integrity, form-field accuracy, expected change impact, duplicate side effects and seeded ranking/schedule correctness. Use independent expected labels/calculations, including cases held out from prompt tuning. Use an LLM judge for explanation clarity/grounding as a supplementary signal. Report dataset size/version, model/prompt/rule versions, actual metrics, latency/cost and failed cases. Compare the adapted baseline and extended graph on applicable common tasks before making performance-improvement claims; separately report new capability coverage.

## 13. Hackathon alignment and sponsor tools

Recommended main track: **Autonomous Agents**. The core demonstration is autonomous evidence/tool work, changing-state monitoring and an executable recovery workflow. The 3D scene supports the product story. Cross-cutting target: **Best-Designed AI Product**, with actual Figma design/prototype evidence. Consider the Adaption cross-cutting prize only if the team genuinely fine-tunes a model and evaluates its improvement under that prize's current rules; it is an optional extension rather than a dependency of the product.

Databricks is the core platform; Claude is the preferred model family; Linkup is the preferred sponsor search integration subject to access; Figma supports product design. Databricks/Linkup sub-bounty choices and exact entry criteria require checking the current guide/organizer instructions before submission. The supplied opening-ceremony slide establishes one main track, up to two sub-bounties and cross-cutting tracks; an optional integration is not itself proof of prize eligibility.

Sponsor value should be observable: Databricks data/query/extraction/search/runtime/MLflow outputs, model-assisted agent tasks, actual search-tool outputs and Figma design assets. Capture real run screenshots, trace IDs, architecture and measured verification for the submission. Final registration/Devpost publication is a team-lead action.

Guide: https://imperialaihack.com/#guide. At PRD authoring the guide could not be reread successfully through available browser/web tooling; sponsor details above use supplied slides and prior conversation, so exact bounty rules remain a submission discovery task.

## 14. Implementation contracts and integration

This PRD is self-contained. Implementers use the requirements, discovery packages, domain schemas, API/events, acceptance checks and delivery gates in this document. Team responsibilities and folder ownership follow the repository's current coordination rules and the team lead's decisions.

Use one canonical schema source for Pydantic/OpenAPI and generated TypeScript. Contract changes have explicit versions and are coordinated before dependent frontend/backend work diverges. Keep rendering, orchestration, evidence/rule content and transactional command processing behind the service boundaries in section 5.4. Requirement/applicability content and ranking/scheduling configuration remain distinct versioned concerns.

Suggested implementation layout:

```text
frontend/src/{scene,workspace,evidence,decisions,documents,api}
backend/{api,domain,agents,adapters,runtime}
contracts/{schemas,openapi,generated-types}
data/{manifests,fixtures,ingestion,evidence-inventory}
rules/{requirements,applicability,ranking}
templates/{registry,fields,renderers}
deploy/{databricks,resources}
tests/{unit,integration,e2e,evaluations}
docs/{decisions,verification,demo}
```

Follow existing repository conventions where they provide equivalent boundaries. Record actual commands, versions, checks, run/trace IDs, remaining dependencies and next integration actions alongside implementation work. The first executable slice and subsequent gates are specified below; no separate starting guide or assignment document is required.

## 15. Delivery sequence and integration gates

1. **Contract and capability gate:** freeze IDs/schemas/events; start platform spike and joint component/asset/evidence selection. Frontend builds against typed fixtures while preflight runs. Record exact runtime versions and chosen model/API.
2. **First vertical slice:** one primary component → deployed investigation → evidence-backed D1 → displayed shortlist. Use an actual Databricks SQL/search/model call and MLflow trace. This establishes the executable backbone.
3. **Hero feature gate:** normalised risk signal → explicit impact path → selective invalidation → D2 → before/after frontend. Verify expected rank change and preserved unaffected checks.
4. **Execution gate:** current selection → actual applicable template autofill → review → simulated submission receipt → replacement/restoration animation. Verify stale versions and duplicate requests.
5. **Generalisation gate:** both secondary cases run the same workflow with different data and route emphasis. Add evidence-change invalidation, gap follow-up and scheduling constraints as specified.
6. **Integration and quality gate:** run section 12, resolve material failures, perform a fresh independent review of the exact release, record results and rehearse the presentation/reset on the actual laptop.
7. **Submission gate:** verify current track/bounty rules, prepare explanation of adapted baseline and product extensions, architecture/trace screenshots, demo video and reproducible setup. Team lead reviews and publishes.

Shared contracts, source versions and observable behaviour take precedence over extra agent count or unnecessary framework changes. Improvements A–D all belong in the product; C receives the strongest presentation emphasis.

## 16. Decisions requiring discovery

| Item | Required before |
| --- | --- |
| Exact engine/three components, asset rights and mesh mappings | Freeze final scenario identity and animation. |
| Authoritative technical documents and applicability/units | Award technical eligibility and publish compatibility detail. |
| Correct UK CAA route/current form package and applicant roles | Enable route-specific generated authority paperwork. |
| Actual workspace edition/region/quotas/Runtime/AI Function access | Commit deployment design and declare integrations operational. |
| Model/API, package/checkpointer versions and auth identity | Lock dependencies and run durability test. |
| Primary input values and independently expected D1/D2 | Freeze scripted risk reveal. |
| Final name, visual design and delivery URL | Freeze demo/submission. |
| Exact current sub-bounty requirements | Choose and submit entries. |

Each discovery result is recorded in a versioned decision note with evidence, selected option, rationale, unresolved gaps and affected contract/data versions. These decisions do not require reopening the approved product flow.

## 17. Reference sources and verification status

Technical capabilities were checked in official documentation and source on 14 November 2026. Platform features are documented support, not proof of availability in this team's workspace. This document defines the storage, runtime, event and workflow responsibilities without requiring companion artifacts.

- [Reference application, pinned source](https://github.com/mongodb-industry-solutions/retail-supply-chain-management/tree/c8cebc3c8924b2355fbb63d3878e34616fefd460): source structure, workflows and database migration basis.
- [Agent Bricks CLI](https://docs.databricks.com/aws/en/agents/custom-agents/agent-bricks-cli): current code-first LangGraph migration/deployment, Python and authentication details; Beta at research date.
- [Agent Runtime](https://docs.databricks.com/aws/en/agents/deploy/agent-runtime) and [Agent Server](https://docs.databricks.com/aws/en/agents/deploy/agent-server): hosting, invocation/events and explicit recovery handling.
- [Databricks model APIs](https://docs.databricks.com/aws/en/ai-gateway/query-model-services): unified/provider-native integration surfaces.
- [Information Extraction](https://docs.databricks.com/aws/en/agents/agent-bricks/info-extraction): schema extraction, SQL/REST and evidence localization options.
- [AI Search querying](https://docs.databricks.com/aws/en/ai-search/query-ai-search): hybrid retrieval, reranking, filters and endpoint-specific semantics.
- [Lakebase synced tables](https://docs.databricks.com/aws/en/oltp/projects/sync-tables): analytical copies versus native operational writes.
- [Free Edition limits](https://docs.databricks.com/aws/en/getting-started/free-edition-limitations): workspace-dependent feasibility and quotas.
- [MLflow code scorers](https://docs.databricks.com/aws/en/mlflow3/genai/eval-monitor/custom-scorer-reference): domain evaluation implementation.
- [LangGraph persistence](https://docs.langchain.com/oss/python/langgraph/persistence): checkpoint/store responsibilities.
- [Google OR-Tools](https://developers.google.com/optimization/cp/): optional constrained recovery scheduling.
- [Anthropic multi-agent research architecture](https://www.anthropic.com/research/multi-agent-research-system): scoped parallel investigation and evidence follow-up pattern.
- [Palantir AIP Logic](https://www.palantir.com/docs/foundry/logic/core-concepts): connected objects and explicit actions pattern.
- [Altana supply-chain product](https://altana.ai/defense-supply-chain-compliance): continuous product-level monitoring analogy, not a source of UK CAA requirements.
- User-provided track/sponsor slides and approved conversation decisions: product scope and demonstration requirements.

Verification at authoring: The reviewed v1.1 content passed local checks for requirement/discovery/acceptance coverage, balanced code fences, valid example JSON and consistent Markdown tables. Independent review confirmed that all four material specification findings were resolved and identified no remaining material specification blocker; no engineering/regulatory document collection, asset selection, software build, live Databricks integration or product acceptance test has been performed as part of writing this PRD. Version 1.2 preserves those fixes and removes companion-artifact dependencies and prescribed contributor assignments.
