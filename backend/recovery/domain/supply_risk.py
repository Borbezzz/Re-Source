"""Evidence-backed supply risk contracts. Unknown identity never becomes a match."""
from __future__ import annotations

from datetime import date
from typing import Literal
from urllib.parse import urlsplit

from pydantic import Field, field_validator

from .products import ProductContract


class RiskNeed(ProductContract):
    part_id: str = Field(min_length=1, max_length=100)
    quantity: int = Field(ge=1, le=1000000)
    destination: str = Field(min_length=2, max_length=200)
    need_by: date


class RiskConfirm(ProductContract):
    expected_project_version: int = Field(ge=1)
    needs: list[RiskNeed] = Field(min_length=1, max_length=200)


class RiskEvidence(ProductContract):
    evidence_id: str = Field(min_length=1, max_length=200)
    part_id: str = Field(min_length=1, max_length=100)
    kind: Literal["quote", "backorder", "shipment", "delivery", "route_disruption", "material_trend", "freight_pressure"]
    title: str = Field(min_length=1, max_length=200)
    source_url: str | None = Field(default=None, max_length=2000)
    source_document_id: str | None = Field(default=None, max_length=200)
    source_version: str = Field(default="1", min_length=1, max_length=100)
    excerpt: str = Field(min_length=1, max_length=4000)
    issued_on: date | None = None
    valid_until: date | None = None
    unverified_reason: str | None = Field(default=None, max_length=400)
    supplier: str | None = Field(default=None, max_length=200)
    part_number: str | None = Field(default=None, max_length=150)
    revision: str | None = Field(default=None, max_length=100)
    quantity: int | None = Field(default=None, ge=1, le=1000000)
    destination: str | None = Field(default=None, max_length=200)
    route: str | None = Field(default=None, max_length=200)
    arrival_on: date | None = None
    event: str | None = Field(default=None, max_length=300)
    origin: Literal["provided_document", "synthetic_demo"] = "provided_document"

    @field_validator("source_url")
    @classmethod
    def safe_url(cls, value: str | None) -> str | None:
        if value:
            parsed = urlsplit(value)
            if parsed.scheme not in {"https", "http"} or not parsed.hostname or parsed.username or parsed.password:
                raise ValueError("Use a public http(s) document URL without credentials.")
        return value


class RiskEvidenceRequest(ProductContract):
    expected_scan_version: int = Field(ge=1)
    evidence: RiskEvidence


class RiskSource(ProductContract):
    title: str
    url: str
    excerpt: str
    publisher: str
    published_on: str | None = None
    retrieved_at: str
    provider: str


class RiskProvider(ProductContract):
    name: str
    status: Literal["searched", "unavailable", "not_configured"]
    source_count: int


class RiskObservation(ProductContract):
    evidence: RiskEvidence
    level: Literal["alert", "watchlist", "matched", "superseded"]
    applies_because: str
    days_late: int | None = None


class RiskPart(ProductContract):
    part_id: str
    name: str
    part_number: str | None
    revision: str | None
    need: RiskNeed
    status: Literal["at_risk", "watchlist", "unknown", "on_time", "received"]
    summary: str
    missing: list[str]
    exposure: list[str]
    observations: list[RiskObservation]
    actions: list[str]


class RiskScan(ProductContract):
    project_id: str
    project_version: int
    version: int
    status: Literal["not_started", "current", "needs_confirmation"]
    evaluated_at: str
    searched_at: str | None = None
    parts: list[RiskPart] = Field(default_factory=list)
    sources: list[RiskSource] = Field(default_factory=list)
    providers: list[RiskProvider] = Field(default_factory=list)
