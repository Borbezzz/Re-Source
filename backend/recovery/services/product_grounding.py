"""Deterministic permission to reuse supplied facts in a non-binding RFQ.

This verifies source support, not engineering compliance or supplier eligibility.
It neither changes the project nor calls a model, provider or external service.
"""
from __future__ import annotations

import json
import re
from typing import Any


def _compact(value: Any) -> str:
    return " ".join(str(value).split())


def _literal(value: Any, text: str, *, case_sensitive: bool = False) -> bool:
    value = _compact(value)
    if not value:
        return False
    pattern = re.escape(value).replace(r"\ ", r"\s+")
    return bool(re.search(r"(?<![\w.])" + pattern + r"(?!\w|[-.]\w)", text,
                          flags=0 if case_sensitive else re.IGNORECASE))


def _requirement_value(requirement: dict) -> str:
    value, unit = _compact(requirement.get("value", "")), _compact(requirement.get("unit") or "")
    if unit and not re.search(r"(?:^|[\s\d])" + re.escape(unit) + r"$", value):
        value = f"{value} {unit}"
    return value


def _comparison(value: Any) -> str:
    # Ignore case and presentation whitespace, without converting units or guessing equivalents.
    return re.sub(r"(?<=\d)\s+(?=[A-Za-zµμ°])", "", _compact(value)).casefold()


def _document_parts(text: str) -> list[dict]:
    """Read only explicit JSON BOM rows and Part:/Component: blocks for scope/conflict checks."""
    try:
        value = json.loads(text)
        rows = value.get("parts", []) if isinstance(value, dict) else value if isinstance(value, list) else []
    except (ValueError, TypeError):
        rows = []
    if isinstance(rows, list) and rows:
        facts = []
        for row in rows:
            if not isinstance(row, dict) or not isinstance(row.get("name"), str):
                continue
            requirements = row.get("requirements") or {}
            if isinstance(requirements, list):
                requirements = {r["key"]: _requirement_value(r) for r in requirements
                                if isinstance(r, dict) and r.get("key") and r.get("value") is not None}
            if not isinstance(requirements, dict):
                requirements = {}
            facts.append({"name": row["name"], "part_number": row.get("part_number"), "quantity": row.get("quantity"),
                          "requirements": {str(k): str(v) for k, v in requirements.items()}})
        return facts
    facts, current = [], None
    for line in text.splitlines():
        match = re.match(r"^\s*(?:#{1,4}\s*)?(?:Part|Component)\s*:\s*(.+?)\s*$", line, re.IGNORECASE)
        if match:
            current = {"name": match[1], "part_number": None, "quantity": None, "requirements": {}}
            facts.append(current)
            continue
        match = re.match(r"^\s*([\w /-]{2,60})\s*:\s*(.+?)\s*$", line)
        if current is None or not match:
            continue
        key = re.sub(r"[^a-z0-9]+", "_", match[1].strip().lower()).strip("_")
        if key in {"qty", "quantity"}:
            current["quantity"] = match[2]
        elif key in {"part_number", "part_no", "p_n"}:
            current["part_number"] = match[2]
        else:
            current["requirements"][key] = match[2]
    return facts


def _same_identity(part: dict, fact: dict) -> bool:
    number, other_number = part.get("part_number"), fact.get("part_number")
    if number and other_number:
        return _comparison(number) == _comparison(other_number)
    return bool(part.get("name")) and _comparison(part["name"]) == _comparison(fact.get("name", ""))


def grounded_part_issues(project: dict, parts: list[dict]) -> list[dict]:
    """Return actionable issues; an empty list permits agent source confirmation only.

    Callers still enforce ownership, mandate/revision checks and allowed transport.
    An omitted quantity source never authenticates the schema's default quantity=1.
    """
    issues: list[dict] = []
    documents = project.get("_documents", {})
    document_facts = {did: _document_parts(doc.get("text") or "") for did, doc in documents.items()
                      if doc.get("kind") in {"blueprint", "requirements"}}

    def issue(code: str, message: str, part: dict) -> None:
        item = {"code": code, "message": message, "part_ids": [part["part_id"]] if part.get("part_id") else []}
        if item not in issues:
            issues.append(item)

    def source(part: dict, value: Any, reference: Any, label: str) -> tuple[str, str] | None:
        if not isinstance(reference, dict):
            issue("source_required", f"{part.get('name', 'Part')}: supply a source for {label}, or explicitly review the value.", part)
            return None
        did, quote = reference.get("document_id"), reference.get("quote")
        doc = documents.get(did) if isinstance(did, str) else None
        if (not doc or doc.get("kind") not in {"blueprint", "requirements"} or not isinstance(quote, str)
                or not quote.strip() or not _literal(quote, doc.get("text") or "", case_sensitive=True)):
            issue("source_unverifiable", f"{part.get('name', 'Part')}: the cited {label} passage is not present in an accessible specification.", part)
            return None
        if not _literal(value, quote, case_sensitive=label.startswith("requirement ")):
            issue("source_value_mismatch", f"{part.get('name', 'Part')}: the source does not establish {label} as {value}.", part)
            return None
        return did, quote

    if not parts:
        return [{"code": "parts_required", "message": "Identify at least one part before requesting quotations.", "part_ids": []}]
    for part in parts:
        name = part.get("name") or ""
        identity = source(part, name, part.get("identity_source"), "part identity")
        quantity = part.get("quantity")
        quantity_ref = source(part, quantity, part.get("quantity_source"), "quantity")
        if type(quantity) is not int or quantity < 1:
            issue("quantity_required", f"{name}: provide an explicit positive whole-number quantity.", part)
        elif quantity_ref and not re.search(r'(?<![\w-])(?:quantity|qty)["\s:=]+["\s]*' + re.escape(str(quantity)) + r'(?![\w.])', quantity_ref[1], re.IGNORECASE):
            issue("quantity_required", f"{name}: cite an explicit Quantity or Qty field; a default count is not source evidence.", part)
        number = part.get("part_number")
        number_ref = source(part, number, part.get("part_number_source"), "OEM part number") if number else None
        if number_ref and not re.search(r'(?<![\w-])(?:part[ _-]*(?:number|no\.?|#)|p\s*/\s*n)["\s:=]+["\s]*'
                                        + re.escape(str(number)) + r'(?![\w.-])', number_ref[1], re.IGNORECASE):
            issue("part_number_unverified", f"{name}: a drawing or document identifier is not an explicitly labelled OEM part number.", part)
        requirements = part.get("requirements") or []
        if not requirements:
            issue("requirements_required", f"{name}: supply at least one specification or explicitly review the part before requesting a quote.", part)
        keys = set()
        requirement_refs = []
        for requirement in requirements:
            key = requirement.get("key", "")
            if key in keys:
                issue("specification_conflict", f"{name}: more than one value is supplied for requirement {key}; resolve the duplicate field.", part)
            keys.add(key)
            value = _requirement_value(requirement)
            requirement_refs.append((key, value, source(part, value, requirement.get("source"), f"requirement {key}")))

        # Explicit rows elsewhere in this same project can directly contradict a
        # proposed value. A public search snippet never participates in this check.
        facts = [(did, fact) for did, rows in document_facts.items() for fact in rows if _same_identity(part, fact)]
        for did, fact in facts:
            if (identity and _comparison(fact.get("name", "")) == _comparison(name)
                    and fact.get("quantity") is not None and _comparison(quantity) != _comparison(fact["quantity"])):
                issue("specification_conflict", f"{name}: explicit source records disagree on its quantity.", part)
            for requirement in requirements:
                key = requirement.get("key")
                if key in fact["requirements"] and _comparison(_requirement_value(requirement)) != _comparison(fact["requirements"][key]):
                    issue("specification_conflict", f"{name}: explicit source records disagree on {key}; resolve the values before outreach.", part)
        # An unrelated row's quantity/identifier must not be borrowed just because
        # the same number happens to occur elsewhere in the uploaded BOM.
        for reference, field, value in ((quantity_ref, "quantity", quantity), (number_ref, "part_number", number)):
            if reference and document_facts.get(reference[0]):
                matching = [fact for did, fact in facts if did == reference[0]]
                if not any(fact.get(field) is not None and _comparison(fact[field]) == _comparison(value) for fact in matching):
                    issue("source_scope_mismatch", f"{name}: the cited {field.replace('_', ' ')} belongs to another part or is absent from its explicit source record.", part)
        for key, value, reference in requirement_refs:
            if reference and document_facts.get(reference[0]):
                matching = [fact for did, fact in facts if did == reference[0]]
                if not any(key in fact["requirements"] and _comparison(fact["requirements"][key]) == _comparison(value) for fact in matching):
                    issue("source_scope_mismatch", f"{name}: requirement {key} is not supported by that part's explicit source record.", part)
    return issues
