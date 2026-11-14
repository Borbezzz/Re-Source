"""Canonical domain contracts (PRD §6, §7).

This module is the single schema source: OpenAPI, JSON Schema (contracts/schemas) and the generated
TypeScript types (contracts/generated-types) are all exported from these Pydantic models by
`backend/scripts/export_contracts.py`. Change a contract here, bump SCHEMA_VERSION, re-export, and
announce it on the board.
"""

from __future__ import annotations

from datetime import datetime, timezone
from decimal import Decimal
from enum import Enum
from typing import Any, Literal, Optional

from pydantic import BaseModel, ConfigDict, Field

SCHEMA_VERSION = "1.0"


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


class Contract(BaseModel):
    model_config = ConfigDict(extra="forbid", populate_by_name=True)


# ----------------------------------------------------------------------------------------------
# Enumerations
# ----------------------------------------------------------------------------------------------


class Route(str, Enum):
    BUY = "BUY"
    MAKE = "MAKE"


class DataOrigin(str, Enum):
    synthetic_demo = "synthetic_demo"
    public_source = "public_source"
    provided_document = "provided_document"
    computed = "computed"


class Mode(str, Enum):
    live = "live"
    seeded = "seeded"
    replay = "replay"


class CaseState(str, Enum):
    ready = "ready"
    investigating = "investigating"
    recommendations_ready = "recommendations_ready"
    reassessing = "reassessing"
    selected = "selected"
    documents_preparing = "documents_preparing"
    documents_ready = "documents_ready"
    submission_simulated = "submission_simulated"
    installation_visualized = "installation_visualized"
    restored_visualized = "restored_visualized"
    # auxiliary
    waiting_for_evidence = "waiting_for_evidence"
    interrupted = "interrupted"
    failed = "failed"
    selection_stale = "selection_stale"
    documents_stale = "documents_stale"


class VisualState(str, Enum):
    assembled = "assembled"
    exploded = "exploded"
    failed = "failed"
    removed = "removed"
    replacement_ready = "replacement_ready"
    installed = "installed"
    running = "running"


class CheckOutcome(str, Enum):
    pass_ = "pass"
    fail = "fail"
    unknown = "unknown"


class Eligibility(str, Enum):
    eligible = "eligible"  # all mandatory checks pass: ready-to-select
    pending = "pending"  # at least one mandatory unknown, none failed (feasibility may be shown)
    ineligible = "ineligible"  # at least one mandatory check failed


class MonitoringStatus(str, Enum):
    active = "active"
    paused = "paused"
    closed = "closed"


class SignalStatus(str, Enum):
    active = "active"
    corrected = "corrected"
    retracted = "retracted"


# ----------------------------------------------------------------------------------------------
# Value objects
# ----------------------------------------------------------------------------------------------


class Money(Contract):
    amount: Decimal = Field(description="Decimal amount as a string-safe decimal")
    currency: str = Field(min_length=3, max_length=3, description="ISO 4217 code")


class Duration(Contract):
    value: float
    unit: Literal["hours", "days"] = "days"


class Locator(Contract):
    page: Optional[int] = None
    section: Optional[str] = None
    line: Optional[int] = None
    bbox: Optional[list[float]] = None
    excerpt: Optional[str] = None


# ----------------------------------------------------------------------------------------------
# Entities (PRD §6.1)
# ----------------------------------------------------------------------------------------------


class MeshMapping(Contract):
    node_name: str
    hotspot_anchor: list[float] = Field(description="[x,y,z] world-space anchor for the hotspot")
    exploded_offset: list[float] = Field(description="[x,y,z] offset applied in exploded view")
    camera_focus: dict[str, list[float]] = Field(description="{position:[x,y,z], target:[x,y,z]}")
    removal_vector: list[float] = Field(description="[x,y,z] direction used by the removal animation")


class ComponentInstance(Contract):
    engine_id: str
    component_id: str
    case_id: str
    display_name: str
    short_description: str
    part_identity: str
    revision: str
    position: str
    requirement_set_id: str
    mesh_mapping: MeshMapping
    failure_story: dict[str, Any]
    data_origin: DataOrigin = DataOrigin.synthetic_demo


class EngineConfiguration(Contract):
    engine_id: str
    display_name: str
    representative_note: str
    configuration_revision: str
    component_instance_ids: list[str]
    scenario_manifest_version: str
    asset: dict[str, Any]
    data_origin: DataOrigin = DataOrigin.synthetic_demo


class Supplier(Contract):
    supplier_id: str
    legal_entity_name: str
    registry: Optional[dict[str, Any]] = None
    roles: list[str]
    data_origin: DataOrigin = DataOrigin.synthetic_demo


class Site(Contract):
    site_id: str
    supplier_id: str
    name: str
    address: str
    geography: dict[str, Any]
    roles: list[str]
    capabilities: list[str] = []
    qualified_scope_refs: list[str] = []
    metric_refs: list[str] = []
    data_origin: DataOrigin = DataOrigin.synthetic_demo


class ReliabilityMetric(Contract):
    metric_id: str
    subject_id: str
    site_id: Optional[str] = None
    metric_name: str
    label: str
    value: float
    unit: str
    numerator: Optional[float] = None
    denominator: Optional[float] = None
    window: str
    source_evidence_id: Optional[str] = None
    data_origin: DataOrigin = DataOrigin.synthetic_demo
    fixture_note: Optional[str] = None


class CandidateOffer(Contract):
    candidate_id: str
    case_id: str
    route: Route
    label: str
    part_id: str
    revision: str
    supplier_id: str
    site_id: str
    manufacturer_id: Optional[str] = None
    seller_id: Optional[str] = None
    quantity: int = 1
    condition: Optional[str] = None
    quote_version: str
    price: Money
    stock: Optional[int] = None
    capacity: Optional[dict[str, Any]] = None
    logistics_route_id: Optional[str] = None
    plan_id: Optional[str] = None
    evidence_ids: list[str] = []
    route_specific: dict[str, Any] = {}
    source_adapter: str = "seeded_offers"
    data_origin: DataOrigin = DataOrigin.synthetic_demo


class EvidenceVersion(Contract):
    version_id: str
    document_id: str
    title: str
    doc_type: str
    hash: str
    source_url: Optional[str] = None
    storage_uri: Optional[str] = None
    authority: str
    authority_rank: int = Field(description="Higher wins in conflict resolution")
    issuer: Optional[str] = None
    subject_ids: list[str] = []
    site_id: Optional[str] = None
    revision: Optional[str] = None
    effective_at: Optional[datetime] = None
    expiry_at: Optional[datetime] = None
    retrieved_at: datetime
    data_origin: DataOrigin = DataOrigin.synthetic_demo
    validation_state: Literal["valid", "invalid", "unvalidated", "superseded"] = "unvalidated"
    supersedes_version_id: Optional[str] = None
    content_text: Optional[str] = None


class ExtractedFact(Contract):
    fact_id: str
    evidence_version_id: str
    field: str
    typed_value: Any
    unit: Optional[str] = None
    original_value: Optional[str] = None
    locator: Optional[Locator] = None
    confidence: Optional[float] = None
    validation_state: Literal["valid", "invalid", "unvalidated"] = "unvalidated"
    validation_note: Optional[str] = None
    extraction_mode: str = "fixture"


class Requirement(Contract):
    requirement_id: str
    requirement_set_id: str
    version: str
    title: str
    plain_language: str
    category: Literal["technical", "supplier_site", "regulatory", "logistics"]
    routes: list[Route]
    mandatory: bool
    evaluator_id: str
    evaluator_version: str
    fact_inputs: list[str]
    params: dict[str, Any] = {}
    evidence_authority_policy: str
    feasibility_only: bool = Field(False, description="Pending result still counts as 'feasible' (MAKE)")


class CheckResult(Contract):
    check_id: str
    case_id: str
    candidate_id: str
    requirement_id: str
    requirement_version: str
    requirement_title: str
    category: str
    mandatory: bool
    result: CheckOutcome
    explanation: str
    evidence_refs: list[str] = []
    fact_refs: list[str] = []
    input_versions: dict[str, str] = {}
    dependency_ids: list[str] = []
    fingerprint: str
    rule_version: str
    evaluated_at: datetime
    reused_from_decision_id: Optional[str] = None
    contradictions: list[dict[str, Any]] = []
    feasible_if_unknown: bool = False
    gap: Optional[dict[str, Any]] = None
    template_code: Optional[str] = None
    plain_language: Optional[str] = None
    rerun_reason: Optional[str] = None


class Relationship(Contract):
    relationship_id: str
    from_id: str
    from_type: str
    to_id: str
    to_type: str
    relation_type: str
    evidence_ids: list[str] = []
    effective_from: Optional[datetime] = None
    effective_to: Optional[datetime] = None
    recorded_at: datetime
    revision: int = 1
    data_origin: DataOrigin = DataOrigin.synthetic_demo


class PlanStep(Contract):
    step_id: str
    name: str
    kind: Literal["procurement", "manufacture", "qualification", "transport", "inspection", "installation", "documentation"]
    duration: Duration
    depends_on: list[str] = []
    duration_range: Optional[list[float]] = None
    assumption: Optional[str] = None
    source: str
    start_day: Optional[float] = None
    finish_day: Optional[float] = None
    on_critical_path: bool = False
    adjusted_by: list[str] = []


class CostLine(Contract):
    label: str
    original: Money
    converted: Money
    fx_version: Optional[str] = None
    source: str


class RecoveryPlan(Contract):
    plan_id: str
    candidate_id: str
    steps: list[PlanStep]
    assumptions: list[str]
    finish_day: float
    elapsed_days: float
    labour_days: float
    critical_path: list[str]
    cost_breakdown: list[CostLine]
    landed_cost: Money
    solver: Literal["dependency_cpm", "cp_sat"]
    solver_status: str
    solver_detail: dict[str, Any] = {}
    input_versions: dict[str, str] = {}
    data_origin: DataOrigin = DataOrigin.synthetic_demo


class RiskSignal(Contract):
    signal_id: str
    source: str
    source_event_id: str
    version: int = 1
    category: Literal["geopolitical_tariff", "climate", "logistics", "port_facility", "evidence", "business"]
    title: str
    scope: dict[str, Any] = Field(description="{entity_ids:[], site_ids:[], geo_ids:[], route_ids:[], materials:[]}")
    assertion: dict[str, Any]
    published_at: datetime
    observed_at: datetime
    effective_from: datetime
    expiry_at: Optional[datetime] = None
    provenance: dict[str, Any] = {}
    confidence: float = 1.0
    status: SignalStatus = SignalStatus.active
    data_origin: DataOrigin = DataOrigin.synthetic_demo
    label: Optional[str] = None


class ChangeEvent(Contract):
    change_id: str
    scenario_run_id: str
    trigger_type: Literal["signal", "evidence", "requirement", "template", "relationship", "clock"]
    trigger_id: str
    source_version: str
    affected_entity_ids: list[str]
    scope: dict[str, Any]
    effective_at: datetime
    received_at: datetime
    revision: int
    dedup_key: str
    activation_state: Literal["registered", "staged", "active", "superseded", "scheduled"]
    fanout_state: Literal["pending", "partial", "complete", "not_required"]
    affected_case_ids: list[str] = []
    impact_paths: list[list[dict[str, str]]] = []
    title: Optional[str] = None
    fanout_done: list[str] = Field([], description="Idempotent per-case fan-out keys already applied")
    queued_case_ids: list[str] = Field([], description="Cases whose monitoring was paused; reconciled on resume")


class CaseSubscription(Contract):
    subscription_id: str
    scenario_run_id: str
    case_id: str
    dependency_ids: list[str]
    dependency_revision: int
    status: MonitoringStatus
    owner: str
    reconciled_change_cursor: int = 0
    updated_at: datetime


class ScoreBreakdown(Contract):
    recovery_speed: float
    landed_cost: float
    historical_reliability: float
    current_resilience: float
    weights: dict[str, float]
    inputs: dict[str, Any]
    thresholds: dict[str, Any]
    score: float


class RankedCandidate(Contract):
    candidate: CandidateOffer
    eligibility: Eligibility
    feasible: bool
    rank: Optional[int] = None
    score: Optional[ScoreBreakdown] = None
    plan: Optional[RecoveryPlan] = None
    check_ids: list[str] = []
    gaps: list["EvidenceGap"] = []
    reliability: list[ReliabilityMetric] = []
    exposure: dict[str, Any] = {}
    evidence_coverage: dict[str, Any] = {}
    supplier: Optional[Supplier] = None
    site: Optional[Site] = None
    summary: str = ""


class EvidenceGap(Contract):
    gap_id: str
    case_id: str
    candidate_id: str
    site_id: Optional[str] = None
    requirement_id: str
    desired: str
    allowed_sources: list[str]
    priority: int = 1
    status: Literal["open", "resolved", "exhausted"] = "open"
    attempts: list[dict[str, Any]] = []


class DecisionSnapshot(Contract):
    decision_id: str
    label: str
    case_id: str
    scenario_run_id: str
    case_revision: int
    input_revision: int
    generation_id: str
    candidates: list[RankedCandidate]
    checks: list[CheckResult]
    evidence_set_id: str
    evidence_hash: str
    requirements_version: str
    ranking_config_version: str
    relationship_versions: dict[str, int] = {}
    signal_versions: dict[str, int] = {}
    preferred_candidate_id: Optional[str] = None
    trigger_id: Optional[str] = None
    summary: str
    status: Literal["current", "superseded", "historical"] = "current"
    created_at: datetime
    mode: Mode
    trace_id: Optional[str] = None
    tool_usage: dict[str, int] = {}
    summary_origin: Optional[str] = None
    superseded_reason: Optional[str] = None
    active_signals: list[dict[str, Any]] = []
    facts: Optional[dict[str, Any]] = Field(None, description="Only with ?include_facts=true")
    candidate_evidence: dict[str, list[str]] = {}
    public_leads: dict[str, list[dict[str, Any]]] = Field({}, description="Linkup public leads per route (context only, never eligible)")
    gaps: list["EvidenceGap"] = []
    extraction_modes: dict[str, str] = {}
    scenario_now: Optional[str] = None
    downstream_invalidations: list[str] = []


class RankMove(Contract):
    candidate_id: str
    label: str
    from_rank: Optional[int]
    to_rank: Optional[int]
    from_score: Optional[float]
    to_score: Optional[float]


class FieldChange(Contract):
    candidate_id: str
    field: str
    before: Any
    after: Any
    unit: Optional[str] = None


class DecisionDiff(Contract):
    diff_id: str
    case_id: str
    from_decision_id: str
    to_decision_id: str
    trigger_id: Optional[str]
    trigger: Optional[dict[str, Any]] = None
    impact_paths: list[list[dict[str, str]]] = []
    changed_fields: list[FieldChange]
    rank_moves: list[RankMove]
    rerun_check_ids: list[str]
    reused_check_ids: list[str]
    preferred_before: Optional[str]
    preferred_after: Optional[str]
    downstream_invalidations: list[str] = []
    explanation: str
    user_action_needed: Optional[str] = None


class Selection(Contract):
    selection_id: str
    case_id: str
    scenario_run_id: str
    candidate_id: str
    decision_id: str
    accepted_case_revision: int
    evidence_hash: str
    actor: str
    accepted_at: datetime
    idempotency_key: str
    status: Literal["current", "stale", "superseded"] = "current"
    decision_label: Optional[str] = None
    candidate_label: Optional[str] = None
    route: Optional[Route] = None
    stale_reason: Optional[str] = None
    replayed: Optional[bool] = None


class FieldProvenance(Contract):
    source_fact_ids: list[str] = []
    evidence_refs: list[str] = []
    check_refs: list[str] = []
    transform: str = "copy"
    origin: Literal["evidence", "selection", "decision", "case", "computed", "user_edit", "completion_task"] = "evidence"
    edited_by: Optional[str] = None
    edited_at: Optional[datetime] = None


class DraftField(Contract):
    field_id: str
    label: str
    block: Optional[str] = None
    value: Any = None
    required: bool = True
    editable: bool = True
    status: Literal["filled", "missing", "completion_task", "invalid"] = "filled"
    responsible: Optional[str] = None
    note: Optional[str] = None
    provenance: FieldProvenance = FieldProvenance()


class FormTemplate(Contract):
    template_id: str
    title: str
    owner: str
    authority: str
    version: str
    source_url: str
    kind: Literal["release_certificate", "internal_quality_record", "authority_application"]
    applicability_rule_id: str
    responsible_applicant: str
    signatory: str
    supporting_evidence: list[str]
    completion_rules: list[str]
    destination_type: str
    fields: list[dict[str, Any]]
    why_included: Optional[str] = None


class DocumentDraft(Contract):
    draft_id: str
    case_id: str
    scenario_run_id: str
    template_id: str
    template_version: str
    template_title: str
    version: int
    selection_id: str
    generation_id: str
    fields: list[DraftField]
    validation: dict[str, Any]
    review_state: Literal["draft", "in_review", "approved", "changes_requested"] = "draft"
    status: Literal["current", "superseded", "stale"] = "current"
    why_included: str
    applicability: dict[str, Any]
    created_at: datetime


class DocumentPackage(Contract):
    package_id: str
    case_id: str
    scenario_run_id: str
    version: int
    selection_id: str
    decision_id: str
    generation_id: str
    evidence_set_id: str
    draft_ids: list[str]
    package_hash: str
    review_state: Literal["draft", "approved"] = "draft"
    approved_hash: Optional[str] = None
    readiness: dict[str, Any]
    status: Literal["current", "superseded", "stale"] = "current"
    destination_type: str
    route_explanation: str
    created_at: datetime


class SimulatedReceipt(Contract):
    receipt_id: str
    case_id: str
    scenario_run_id: str
    selection_id: str
    package_id: str
    package_version: int
    package_hash: str
    destination_type: str
    destination_label: str
    submitted_documents: list[dict[str, Any]]
    payload_hash: str
    idempotency_key: str
    status: Literal["accepted_simulated", "historical"] = "accepted_simulated"
    simulated_at: datetime
    label: str = "SIMULATED — no real submission was made"


class OutboxItem(Contract):
    operation_id: str
    op_type: str
    aggregate_id: str
    aggregate_revision: int
    payload: dict[str, Any]
    state: Literal["pending", "done", "failed"]
    attempts: int
    available_at: datetime
    last_error: Optional[str] = None


class AgentTaskOutput(Contract):
    """PRD §6.2 — every agent capability returns this shape, validated before merge."""

    task_id: str
    case_id: str
    input_revision: int
    status: Literal["completed", "pending", "failed"]
    facts: list[str] = []
    evidence_refs: list[str] = []
    check_refs: list[str] = []
    gaps: list[str] = []
    next_actions: list[str] = []
    summary: str
    tool_usage: dict[str, int] = {}


# ----------------------------------------------------------------------------------------------
# Events (PRD §7.1)
# ----------------------------------------------------------------------------------------------

EVENT_TYPES = [
    "case.started",
    "task.started", "task.completed", "task.failed",
    "tool.started", "tool.completed", "tool.failed",
    "evidence.ingested", "evidence.extracted", "evidence.validated",
    "gap.opened", "gap.resolved",
    "check.completed",
    "signal.received", "signal.matched",
    "impact.detected",
    "reassessment.started",
    "decision.created", "decision.updated",
    "selection.accepted", "selection.stale",
    "documents.preparing", "documents.ready", "documents.stale",
    "submission.simulated",
    "visual.updated",
    "monitoring.updated",
    "case.state_changed",
    "run.interrupted", "run.recovered", "run.completed", "run.failed",
    "control.snapshot_required",
]


class DomainEvent(Contract):
    schema_version: str = SCHEMA_VERSION
    event_id: str
    sequence: int
    occurred_at: datetime
    scenario_run_id: str
    case_id: str
    case_revision: int
    invocation_id: Optional[str] = None
    task_id: Optional[str] = None
    type: str
    summary: str
    data: dict[str, Any] = {}
    evidence_refs: list[str] = []
    trace_id: Optional[str] = None
    data_origin: DataOrigin = DataOrigin.synthetic_demo


# ----------------------------------------------------------------------------------------------
# API projections and commands (PRD §7)
# ----------------------------------------------------------------------------------------------


class ApiError(Contract):
    code: str
    message: str
    retryable: bool = False
    case_revision: Optional[int] = None
    details: dict[str, Any] = {}
    correlation_id: str


class CaseSummary(Contract):
    case_id: str
    component_id: str
    display_name: str
    state: CaseState
    revision: int
    visual_state: VisualState
    current_decision_id: Optional[str] = None
    preferred_candidate_label: Optional[str] = None
    stale: bool = False


class EngineView(Contract):
    engine: EngineConfiguration
    operating_story: Optional[dict[str, Any]] = None
    components: list[ComponentInstance]
    cases: list[CaseSummary]
    scenario_run_id: str
    mode: Mode
    visual_states: list[VisualState] = []


class TaskStatus(Contract):
    task_id: str
    name: str
    status: Literal["pending", "running", "completed", "failed", "reused"]
    started_at: Optional[datetime] = None
    finished_at: Optional[datetime] = None
    summary: Optional[str] = None


class CaseView(Contract):
    case_id: str
    scenario_run_id: str
    engine_id: str
    component: ComponentInstance
    state: CaseState
    prior_stable_state: Optional[CaseState] = None
    revision: int
    input_revision: int
    mode: Mode
    visual_state: VisualState
    monitoring_status: MonitoringStatus
    current_decision_id: Optional[str]
    initial_decision_id: Optional[str]
    decision_labels: dict[str, str] = {}
    current_selection: Optional[Selection] = None
    current_package_id: Optional[str] = None
    latest_receipt_id: Optional[str] = None
    stale_reasons: list[str] = []
    pending_change_ids: list[str] = []
    active_generation_id: Optional[str] = None
    tasks: list[TaskStatus] = []
    event_cursor: int
    events_url: str
    provenance: dict[str, Any]
    allowed_visual_actions: list[str] = []
    scenario_now: Optional[str] = None
    monitoring: Optional[dict[str, Any]] = None
    data_origin: DataOrigin = DataOrigin.synthetic_demo


class StartInvestigationRequest(Contract):
    expected_revision: Optional[int] = None
    mode: Mode = Mode.seeded
    idempotency_key: Optional[str] = None


class CommandAccepted(Contract):
    command_id: str
    run_id: str
    case_id: str
    generation_id: Optional[str] = None
    status: Literal["accepted", "already_running", "duplicate"]
    events_url: str
    case_revision: int


class SignalInjectionRequest(Contract):
    fixture_signal_id: Optional[str] = Field(None, description="ID of a seeded scenario signal")
    signal: Optional[RiskSignal] = Field(None, description="A full normalized signal (live adapters)")
    idempotency_key: Optional[str] = None


class SignalInjectionResult(Contract):
    change: ChangeEvent
    duplicate: bool
    affected_case_ids: list[str]


class EvidenceChangeRequest(Contract):
    fixture_evidence_change_id: str
    idempotency_key: Optional[str] = None


class ClockAdvanceRequest(Contract):
    hours: float = Field(gt=0, le=24 * 60)
    idempotency_key: Optional[str] = None


class ClockState(Contract):
    scenario_run_id: str
    scenario_now: datetime
    executed_transitions: list[str]


class SelectionRequest(Contract):
    candidate_id: str
    decision_id: str
    evidence_hash: str
    expected_revision: int
    idempotency_key: Optional[str] = None
    actor: str = "demo-operator"


class DocumentPatchRequest(Contract):
    expected_version: int
    idempotency_key: Optional[str] = None
    field_edits: dict[str, Any] = {}
    review_action: Optional[Literal["submit_for_review", "approve", "request_changes"]] = None
    actor: str = "demo-operator"


class DocumentsView(Contract):
    case_id: str
    current_package: Optional[DocumentPackage]
    current_drafts: list[DocumentDraft]
    history: list[DocumentPackage]
    receipts: list[SimulatedReceipt]
    generation_status: Literal["none", "preparing", "ready", "stale", "failed"]
    readiness: dict[str, Any]
    templates: list[FormTemplate]


class SubmissionRequest(Contract):
    selection_id: str
    package_id: str
    package_version: int
    idempotency_key: Optional[str] = None


class ScenarioRunRequest(Contract):
    mode: Mode = Mode.seeded
    manifest_id: str = "engine-demo-001"
    fixture_version: str = "seed-v1"
    replay_source_run_id: Optional[str] = None
    idempotency_key: Optional[str] = None


class ScenarioRunView(Contract):
    scenario_run_id: str
    mode: Mode
    fixture_version: str
    manifest_version: str
    scenario_now: datetime
    case_map: dict[str, str]
    created_at: datetime
    previous_run_ids: list[str] = []
    replay_source_run_id: Optional[str] = None
    barrier_count: int = 0


class MonitoringRequest(Contract):
    status: MonitoringStatus
    expected_revision: int
    idempotency_key: Optional[str] = None


class VisualActionRequest(Contract):
    action: Literal["focus", "explode", "reassemble", "show_failure", "remove", "install", "restore", "reset_view"]
    idempotency_key: Optional[str] = None


class VisualActionResult(Contract):
    case_id: str
    visual_state: VisualState
    case_state: CaseState
    allowed_next: list[str]
    selected_candidate_id: Optional[str] = None


class EvidenceView(Contract):
    evidence: EvidenceVersion
    facts: list[ExtractedFact]
    used_by_checks: list[str] = []
    preview_text: Optional[str] = None
    superseded_by: Optional[str] = None
    status: Optional[str] = None


class Readiness(Contract):
    status: Literal["ok", "degraded", "unavailable"]
    capabilities: dict[str, dict[str, Any]]
    checked_at: datetime


RankedCandidate.model_rebuild()
DecisionSnapshot.model_rebuild()
