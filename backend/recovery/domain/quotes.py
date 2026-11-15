"""Supplier statements and buyer review, scoped to a project and part."""
from __future__ import annotations

from typing import Literal
from pydantic import Field
from .products import ProductContract, ProductPart

QuoteField = Literal[
    "part_number", "revision", "material", "quantity", "unit_price", "currency",
    "minimum_order", "lead_time", "delivery_date", "quote_date", "valid_until",
    "shipping", "destination", "certificates", "exceptions",
]


class QuoteTerm(ProductContract):
    value: str = Field(max_length=1000)
    excerpt: str | None = None
    page: int | None = None
    origin: Literal["extracted", "buyer_review"] = "extracted"


class SupplierQuote(ProductContract):
    quote_id: str
    part_id: str
    supplier: str
    filename: str
    source_kind: Literal["pdf", "reply"]
    source_url: str
    source_text: str
    created_at: str
    input_version: int
    version: int
    reviewed: bool = False
    terms: dict[QuoteField, QuoteTerm]
    issues: list[str] = Field(default_factory=list)
    follow_up: str = ""


class QuoteCollection(ProductContract):
    project_name: str
    parts: list[ProductPart]
    quotes: list[SupplierQuote]


class QuoteReview(ProductContract):
    expected_version: int = Field(ge=1)
    terms: dict[QuoteField, str] = Field(max_length=15)
