"""Product workspace contracts, independent of the legacy engine catalog.

Prepared demo geometry, uploaded geometry and a future generation provider have
different provenance. Public supplier research is discovery, never certification.
"""
from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


class ProductContract(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True, allow_inf_nan=False)


class ProductSource(ProductContract):
    document_id: str
    quote: str = Field(min_length=1, max_length=2000)
    page: int | None = Field(default=None, ge=1)


class ProductRequirement(ProductContract):
    key: str = Field(min_length=1, max_length=100, pattern=r"^[a-zA-Z0-9_-]+$")
    label: str = Field(min_length=1, max_length=160)
    value: str = Field(min_length=1, max_length=2000)
    unit: str | None = Field(default=None, max_length=50)
    source: ProductSource | None = None
    status: Literal["proposed", "confirmed"] = "proposed"


class ProductPart(ProductContract):
    part_id: str = Field(min_length=1, max_length=100, pattern=r"^[a-zA-Z0-9_-]+$")
    name: str = Field(min_length=1, max_length=160)
    quantity: int = Field(default=1, ge=1, le=1000000)
    part_number: str | None = Field(default=None, max_length=150)
    requirements: list[ProductRequirement] = Field(default_factory=list, max_length=40)
    node_names: list[str] = Field(default_factory=list, max_length=100)
    explode: tuple[float, float, float] | None = None
    status: Literal["proposed", "confirmed"] = "proposed"
    identity_source: ProductSource | None = None
    quantity_source: ProductSource | None = None
    part_number_source: ProductSource | None = None
    confirmation_origin: Literal["user_review", "agent_grounded"] | None = None


class ProductModel(ProductContract):
    origin: Literal["prepared_demo", "uploaded", "generated"] = "uploaded"
    status: Literal["missing", "ready", "provider_required"] = "missing"
    asset_url: str | None = None
    document_id: str | None = None
    license: str | None = None
    source_url: str | None = None
    notes: str | None = None
    node_names: list[str] = Field(default_factory=list)
    mapping_status: Literal["mapped", "unmapped", "partial"] = "unmapped"


class ProductDocument(ProductContract):
    document_id: str
    name: str
    kind: Literal["blueprint", "requirements", "model"]
    data_origin: Literal["synthetic_demo", "provided_document"]
    media_type: str = "text/plain"
    size_bytes: int = 0
    content_url: str | None = None
    extraction_status: Literal["pending", "complete", "unavailable"] = "pending"
    extraction_method: str | None = None
    excerpt: str | None = None


class ProductEvidence(ProductContract):
    requirement_key: str
    status: Literal["supported", "unknown", "conflict"] = "unknown"
    note: str
    source_url: str | None = None


class ProductCandidate(ProductContract):
    candidate_id: str
    part_id: str
    supplier_name: str
    route: Literal["buy", "make"] = "buy"
    country: str | None = None
    price: float | None = Field(default=None, ge=0)
    currency: str | None = None
    lead_time_days: int | None = Field(default=None, ge=0)
    summary: str
    source_url: str | None = None
    data_origin: Literal["synthetic_demo", "public_web"] = "synthetic_demo"
    eligibility: Literal["unverified"] = "unverified"
    evidence: list[ProductEvidence] = Field(default_factory=list)
    retrieved_at: str | None = None


class ProductInvestigation(ProductContract):
    part_id: str
    job_id: str
    status: Literal["queued", "running", "complete", "failed"]
    stage: str
    mode: Literal["demo", "live"] = "demo"
    summary: str | None = None
    candidates: list[ProductCandidate] = Field(default_factory=list)
    started_at: str | None = None
    completed_at: str | None = None
    error: str | None = None
    providers_used: list[str] = Field(default_factory=list)


class ProductEvent(ProductContract):
    sequence: int
    type: str
    summary: str
    part_id: str | None = None
    created_at: str


class ProductPackageItem(ProductContract):
    part_id: str
    part_name: str
    quantity: int
    supplier_name: str
    candidate_id: str
    data_origin: Literal["synthetic_demo", "public_web"]
    requirements: list[ProductRequirement]
    evidence_gaps: list[str]
    rfq_text: str


class ProductPackage(ProductContract):
    package_id: str
    status: Literal["draft", "approved", "simulated"] = "draft"
    input_version: int
    items: list[ProductPackageItem]
    created_at: str
    approved_at: str | None = None
    approved_by: str | None = None
    approval_scope: Literal["simulation_only"] = "simulation_only"
    simulated_at: str | None = None
    receipt: str | None = None
    notice: str = "Draft RFQs only. No supplier has been contacted and no order has been placed."


class ProductCapabilities(ProductContract):
    document_parsing: str
    requirement_extraction: str
    supplier_discovery: str
    model_generation: Literal["provider_required"] = "provider_required"
    storage: Literal["lakebase_postgres", "local_sqlite"]
    execution: Literal["durable_queue", "local_worker"]


class ProductAgentMandate(ProductContract):
    objective: Literal["source_and_request_quotes"] = "source_and_request_quotes"
    outreach: Literal["demo_mailbox", "draft_only"]
    purchase_authorized: Literal[False] = False


class ProductAgentAttention(ProductContract):
    code: str
    message: str
    part_ids: list[str] = Field(default_factory=list)


class ProductAgentTarget(ProductContract):
    part_id: str
    candidate_id: str
    reason: str
    readiness: Literal["demo_ready", "contact_required"]


class ProductAgentRun(ProductContract):
    run_id: str
    input_version: int
    mode: Literal["demo", "live"]
    status: Literal["queued", "running", "paused", "needs_attention", "recommendation_ready", "failed"]
    stage: Literal["requirements", "research", "shortlist", "rfq", "outreach", "complete"]
    summary: str
    mandate: ProductAgentMandate
    attention: list[ProductAgentAttention] = Field(default_factory=list)
    targets: list[ProductAgentTarget] = Field(default_factory=list)
    sent_count: int = 0
    reply_count: int = 0
    created_at: str
    updated_at: str
    completed_at: str | None = None


class ProductMailboxQuote(ProductContract):
    price: float | None = None
    currency: str | None = None
    lead_time_days: int | None = None


class ProductMailboxMessage(ProductContract):
    message_id: str
    run_id: str
    part_id: str
    candidate_id: str
    direction: Literal["outbound", "inbound"]
    delivery: Literal["simulated"] = "simulated"
    data_origin: Literal["synthetic_demo"] = "synthetic_demo"
    intended_supplier: str
    from_label: str
    to_label: str
    subject: str
    body: str
    in_reply_to: str | None = None
    created_at: str
    quote: ProductMailboxQuote | None = None


class ProductProject(ProductContract):
    project_id: str
    name: str
    demo_id: str | None = None
    product_type: str = "custom"
    version: int
    input_version: int
    status: Literal["draft", "extracting", "review", "ready", "investigating", "results", "packaged"]
    documents: list[ProductDocument]
    parts: list[ProductPart]
    model: ProductModel
    research: list[ProductInvestigation]
    selections: dict[str, str]
    package: ProductPackage | None = None
    events: list[ProductEvent]
    capabilities: ProductCapabilities
    created_at: str
    updated_at: str
    agent: ProductAgentRun | None = None
    mailbox: list[ProductMailboxMessage] = Field(default_factory=list)


class ProductProjectSummary(ProductContract):
    """Dashboard fields only; project contents remain behind the owned detail route."""
    project_id: str
    name: str
    demo_id: str | None
    product_type: str
    status: Literal["draft", "extracting", "review", "ready", "investigating", "results", "packaged"]
    created_at: str
    updated_at: str
    part_count: int = Field(ge=0)
    confirmed_part_count: int = Field(ge=0)
    research_count: int = Field(ge=0)
    active_research_count: int = Field(ge=0, description="Investigations currently queued or running.")
    completed_research_count: int = Field(ge=0)
    failed_research_count: int = Field(ge=0)
    selected_count: int = Field(ge=0)
    package_status: Literal["draft", "approved", "simulated"] | None
    agent_status: Literal["queued", "running", "paused", "needs_attention", "recommendation_ready", "failed"] | None = None
    agent_stage: Literal["requirements", "research", "shortlist", "rfq", "outreach", "complete"] | None = None


class ProductProjectList(ProductContract):
    projects: list[ProductProjectSummary]


class DemoProduct(ProductContract):
    demo_id: str
    name: str
    description: str
    product_type: str
    model: ProductModel
    part_count: int
    data_origin: Literal["synthetic_demo"] = "synthetic_demo"


class ProductCreateRequest(ProductContract):
    demo_id: str | None = None
    name: str | None = Field(default=None, min_length=1, max_length=160)


class ProductPartsRequest(ProductContract):
    parts: list[ProductPart] = Field(min_length=1, max_length=50)
    confirm: bool = False
    expected_version: int | None = None


class ProductModelRequest(ProductContract):
    origin: Literal["prepared_demo", "uploaded", "generated"]
    document_id: str | None = None


class ProductInvestigateRequest(ProductContract):
    part_ids: list[str] | None = Field(default=None, max_length=50)
    mode: Literal["demo", "live"] | None = None


class ProductSelectionRequest(ProductContract):
    part_id: str
    candidate_id: str


class ProductApprovalRequest(ProductContract):
    expected_package_id: str
    acknowledge_unverified: bool = False


class ProductSimulationRequest(ProductContract):
    expected_package_id: str


class ProductAgentStartRequest(ProductContract):
    expected_version: int
    mode: Literal["demo", "live"]


class ProductAgentControlRequest(ProductContract):
    expected_run_id: str
    expected_version: int
