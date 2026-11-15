"""Bounded quote intake with literal extraction and durable source provenance."""
from __future__ import annotations

import hashlib
import io
import re
from pathlib import Path

from pypdf import PdfReader

from ..adapters.blob_store import blob_store
from ..adapters.databricks_sql import databricks_sql
from ..adapters import store as st
from ..config import settings
from ..domain.errors import DomainError, conflict, invalid, not_found
from ..domain.quotes import QuoteCollection, QuoteReview

MAX_BYTES = 4 * 1024 * 1024
LABELS = {
    "part_number": r"part\s*(?:number|no\.?|#)|p/n",
    "revision": r"revision|rev\.?",
    "material": r"material",
    "quantity": r"quantity|qty",
    "unit_price": r"unit\s*price|price\s*per\s*(?:unit|piece)|price\s*each",
    "currency": r"currency",
    "minimum_order": r"minimum\s*order(?:\s*quantity)?|moq",
    "lead_time": r"lead\s*time",
    "delivery_date": r"delivery\s*date|arrival\s*date",
    "quote_date": r"quote\s*date|date\s*issued|issued\s*on",
    "valid_until": r"valid\s*until|quote\s*expiry|expires",
    "shipping": r"shipping|freight|delivery\s*terms|incoterms",
    "destination": r"destination|ship\s*to|deliver\s*to",
    "certificates": r"certificates?|certification|documents",
    "exceptions": r"exceptions?|deviations?",
}
MONEY = r"(?:GBP|USD|EUR|CAD|AUD|CHF|JPY|£|€|\$)\s*\d[\d,.]*(?:\s*(?:each|per\s*(?:unit|piece)|/\s*(?:unit|piece)))?"
ALL_LABELS = "|".join(LABELS.values())
LABEL_PATTERNS = {
    key: re.compile(
        rf"(?:^|[;|\t]|\s{{2,}})\s*(?:{labels})\s*[:=]\s*(.+?)(?=\s*(?:;|\||\t)|\s+(?:{ALL_LABELS})\s*[:=]|$)",
        re.I,
    )
    for key, labels in LABELS.items()
}
REPLY_PATTERNS = {
    "unit_price": re.compile(rf"\b(?:at|price(?:d)?\s+at)\s+({MONEY}\s*(?:each|per\s*(?:unit|piece)))", re.I),
    "quantity": re.compile(r"\b(?:supply|offer|quote\s+for)\s+(\d+\s*(?:units|pieces))\b", re.I),
    "lead_time": re.compile(r"\b(?:lead\s*time\s*(?:is|of)?\s*|dispatch\s+in\s+)(\d+(?:\s*[-–]\s*\d+)?\s*(?:(?:working|business|calendar)\s*)?(?:days?|weeks?))\b", re.I),
}


def extract_terms(pages: list[str]) -> dict:
    """Extract literal labels and common reply phrases; ambiguous fields stay open."""
    matches: dict[str, list[dict]] = {}
    for page_number, text in enumerate(pages, 1):
        for line in text.splitlines():
            line = line.strip()
            labels_found = set()
            for patterns in (LABEL_PATTERNS, REPLY_PATTERNS):
                for key, pattern in patterns.items():
                    if key in labels_found:
                        continue
                    for match in pattern.finditer(line):
                        value = match[1].strip()
                        if len(value) <= 1000:
                            matches.setdefault(key, []).append({"value": value, "excerpt": line, "page": page_number, "origin": "extracted"})
                        labels_found.add(key)
    terms = {}
    for key, candidates in matches.items():
        distinct = {candidate["value"].casefold(): candidate for candidate in candidates}
        if len(distinct) == 1:
            terms[key] = next(iter(distinct.values()))
    price = terms.get("unit_price")
    if price and "currency" not in terms:
        match = re.search(r"\b(GBP|USD|EUR|CAD|AUD|CHF|JPY)\b|([£€])", price["value"], re.I)
        if match:
            currency = match[1].upper() if match[1] else {"£": "GBP", "€": "EUR"}[match[2]]
            terms["currency"] = {**price, "value": currency}
    return terms


def read_pdf(data: bytes) -> list[str]:
    if not data.startswith(b"%PDF-"):
        raise invalid("Choose a valid PDF quote, or paste the supplier reply.")
    try:
        reader = PdfReader(io.BytesIO(data))
        if reader.is_encrypted:
            raise invalid("This PDF is password protected. Upload an unlocked copy or paste its text.")
        if len(reader.pages) > 30:
            raise invalid("Upload a quote of up to 30 pages.")
        pages = [page.extract_text() or "" for page in reader.pages]
    except DomainError:
        raise
    except Exception as exc:
        raise invalid("This PDF could not be read. Try another copy or paste the reply.") from exc
    if not "".join(pages).strip():
        raise invalid("This PDF contains no readable text. Paste the quote text from an OCR-enabled copy.")
    return pages


class SupplierQuotes:
    def __init__(self, products):
        self.products = products

    def list(self, project_id: str) -> dict:
        project = self.products._load(project_id)
        quotes = [self._view(quote, project) for quote in project.get("_supplier_quotes", [])]
        return QuoteCollection(project_name=project["name"], parts=project["parts"], quotes=quotes).model_dump(mode="json")

    def import_quote(self, project_id: str, part_id: str, supplier: str, data: bytes, filename: str, kind: str) -> dict:
        project = self.products._load(project_id)
        if not any(part["part_id"] == part_id for part in project["parts"]):
            raise invalid("Choose a part in this project before importing its quote.")
        supplier = supplier.strip()
        if not supplier or len(supplier) > 160:
            raise invalid("Enter a supplier name of up to 160 characters.")
        if not data or len(data) > MAX_BYTES:
            raise invalid("Upload a quote between 1 byte and 4 MB.")
        if kind == "pdf":
            pages = read_pdf(data)
        elif kind == "reply":
            try:
                pages = [data.decode("utf-8")]
            except UnicodeDecodeError as exc:
                raise invalid("Paste a text reply or upload a PDF.") from exc
        else:
            raise invalid("Choose a PDF or paste a reply.")
        source_text = "\n\n".join(pages)
        if not source_text.strip() or len(source_text) > 100000:
            raise invalid("Quote text must contain between 1 and 100,000 characters.")
        identity = f"{part_id}\0{supplier.casefold()}\0{kind}\0".encode() + data
        quote_id = "quote-" + hashlib.sha256(identity).hexdigest()[:24]
        if any(q["quote_id"] == quote_id for q in project.get("_supplier_quotes", [])):
            return self.list(project_id)
        terms = extract_terms(pages)
        ext = ".pdf" if kind == "pdf" else ".txt"
        sha, _ = blob_store.put_local(data, ext)
        volume = blob_store.mirror(sha, ext) if settings.serverless or databricks_sql.configured else None
        if settings.serverless and not volume:
            raise DomainError(503, "UPLOAD_STORAGE_UNAVAILABLE", "Quote storage is unavailable. Please retry.", retryable=True)
        with self.products._mutate(project_id) as current:
            quotes = current.setdefault("_supplier_quotes", [])
            if any(quote["quote_id"] == quote_id for quote in quotes):
                return self.list(project_id)
            if current["input_version"] != project["input_version"]:
                raise conflict("PRODUCT_CHANGED", "The part specification changed. Refresh and import against the current part.")
            if len(quotes) >= 24:
                raise invalid("This project supports up to 24 supplier quotes.")
            quotes.append({"quote_id": quote_id, "part_id": part_id, "supplier": supplier,
                           "filename": Path(filename).name[:200], "source_kind": kind, "source_text": source_text,
                           "source_url": f"/api/v1/products/{project_id}/quotes/{quote_id}/content",
                           "terms": terms, "input_version": current["input_version"],
                           "created_at": st.now_iso(), "reviewed": False, "version": 1,
                           "_sha": sha, "_ext": ext, "_volume": volume})
            self.products._event(current, "quote.imported", f"Imported a quote from {supplier}.", part_id)
        return self.list(project_id)

    def review(self, project_id: str, quote_id: str, review: QuoteReview) -> dict:
        with self.products._mutate(project_id) as project:
            quote = self._find(project, quote_id)
            if quote["version"] != review.expected_version:
                raise conflict("QUOTE_CHANGED", "This quote was reviewed elsewhere. Refresh before saving.")
            if any(len(value.strip()) > 1000 for value in review.terms.values()):
                raise invalid("Each quote term must be at most 1,000 characters.")
            for key, raw in review.terms.items():
                value = raw.strip()
                previous = quote["terms"].get(key, {})
                if value != previous.get("value", ""):
                    quote["terms"][key] = {**previous, "value": value, "origin": "buyer_review"}
            quote["reviewed"] = True
            quote["version"] += 1
            self.products._event(project, "quote.reviewed", f"Reviewed a quote from {quote['supplier']}.", quote["part_id"])
        return self.list(project_id)

    @staticmethod
    def _find(project: dict, quote_id: str) -> dict:
        quote = next((q for q in project.get("_supplier_quotes", []) if q["quote_id"] == quote_id), None)
        if not quote:
            raise not_found("quote")
        return quote

    def content(self, project_id: str, quote_id: str) -> tuple[bytes, str]:
        quote = self._find(self.products._load(project_id), quote_id)
        try:
            data = blob_store.read(quote["_sha"], quote["_ext"], quote.get("_volume"))
        except FileNotFoundError as exc:
            raise not_found("quote source") from exc
        return data, "application/pdf" if quote["source_kind"] == "pdf" else "text/plain; charset=utf-8"

    @staticmethod
    def _view(quote: dict, project: dict) -> dict:
        result = {key: value for key, value in quote.items() if not key.startswith("_")}
        part = next((p for p in project["parts"] if p["part_id"] == quote["part_id"]), None)
        terms = quote["terms"]
        issues = []
        missing = [key.replace("_", " ") for key in ("unit_price", "currency", "quantity", "minimum_order", "shipping", "certificates", "valid_until")
                   if not terms.get(key, {}).get("value")]
        if not (terms.get("lead_time", {}).get("value") or terms.get("delivery_date", {}).get("value")):
            missing.append("lead time or delivery date")
        if missing:
            issues.append("Please confirm " + ", ".join(missing) + ".")
        if quote["input_version"] != project["input_version"]:
            issues.append("The project specification has changed since this quote was imported. Request supplier reconfirmation.")
        if part:
            expected = {r["key"].lower(): r["value"] for r in part["requirements"]}
            expected["part_number"] = part.get("part_number")
            for key in ("part_number", "revision", "material"):
                offered = terms.get(key, {}).get("value")
                wanted = expected.get(key)
                if wanted and not offered:
                    issues.append(f"Please confirm the {key.replace('_', ' ')} for the requested specification ({wanted}).")
                if wanted and offered and offered.casefold().strip() != str(wanted).casefold().strip():
                    issues.append(f"{key.replace('_', ' ').capitalize()} differs. Requested {wanted}; offered {offered}.")
        quantity_pattern = r"(\d{1,9})(?:\s+(?:units|pieces))?"
        minimum = re.fullmatch(quantity_pattern, terms.get("minimum_order", {}).get("value", ""), re.I)
        quantity = re.fullmatch(quantity_pattern, terms.get("quantity", {}).get("value", ""), re.I)
        if minimum and quantity and int(minimum[1]) > int(quantity[1]):
            issues.append(f"Minimum order {minimum[1]} exceeds the quoted quantity {quantity[1]}.")
        if terms.get("exceptions", {}).get("value"):
            issues.append("Supplier exceptions: " + terms["exceptions"]["value"])
        result["issues"] = issues
        questions = issues or ["Please confirm availability and that the quoted specification and commercial terms remain current."]
        result["follow_up"] = f"Hello {quote['supplier']},\n\nThank you for your quote for {part['name'] if part else quote['part_id']}.\n\n" + "\n".join(f"- {question}" for question in questions) + "\n\nPlease provide supporting documents for any certification claims.\n\nThank you."
        return result
