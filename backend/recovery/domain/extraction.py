"""Field schemas per evidence document type, the deterministic structured-form parser and code-side
validation of extracted values (PRD FR-04: identifiers, dates, units, entity/site association and
required fields are validated in code; extraction output alone never establishes evidence status)."""

from __future__ import annotations

import re
from datetime import date, datetime
from decimal import Decimal, InvalidOperation
from typing import Any

# type codes: str | int | decimal | ratio | date | bool | list | currency | partno | revision | site
FIELD_SCHEMAS: dict[str, dict[str, str]] = {
    "release_certificate": {
        "form_type": "str", "tracking_number": "str", "approving_authority": "str", "organisation": "str",
        "approval_reference": "str", "part_number": "partno", "revision": "revision", "serial_number": "str",
        "quantity": "int", "status_work": "str", "remarks": "str", "release_date": "date",
    },
    "quote": {
        "part_number": "partno", "revision": "revision", "quantity": "int", "unit_price": "decimal", "currency": "currency",
        "lead_time_days": "decimal", "condition": "str", "quote_valid_until": "date", "ship_from_site": "site",
    },
    "trace_pack": {
        "part_number": "partno", "serial_number": "str", "back_to_birth": "bool", "last_operator": "str",
        "non_incident_statement": "bool",
    },
    "quality_certificate": {
        "standard": "str", "certificate_number": "str", "certified_site": "site", "site_name": "str",
        "expiry_date": "date", "certification_body": "str",
    },
    "registry_extract": {"legal_entity_name": "str", "company_number": "str", "status": "str", "jurisdiction": "str"},
    "ipc_extract": {
        "part_number": "partno", "description": "str", "interchangeable_revisions": "list",
        "non_interchangeable_revisions": "list", "effectivity": "list", "figure": "str",
    },
    "service_bulletin": {
        "sb_number": "str", "revision": "revision", "applicable_part_number": "partno", "min_drawing_revision": "revision",
        "effective_date": "date", "instruction": "str",
    },
    "poa_certificate": {"approval_reference": "str", "organisation": "str", "scope": "list", "approved_sites": "list"},
    "design_licence": {
        "design_holder": "str", "part_number": "partno", "drawing_number": "str", "drawing_revision": "revision",
        "licence_reference": "str", "licensee": "str",
    },
    "special_process_accreditation": {"site": "site", "processes": "list", "expiry_date": "date"},
    "fai_report": {
        "part_number": "partno", "revision": "revision", "drawing_revision": "revision", "site": "site",
        "report_number": "str", "result": "str",
    },
    "metrics_report": {
        "site": "site", "on_time_deliveries": "int", "deliveries": "int", "on_time_delivery_rate": "ratio",
        "quality_escapes_ppm": "decimal", "window": "str",
    },
}

LABEL_DESCRIPTIONS = {
    "part_number": "manufacturer part number", "serial_number": "serial number", "revision": "part or document revision letter",
    "status_work": "status/work performed (block 11)", "quote_valid_until": "quote validity end date (YYYY-MM-DD)",
    "expiry_date": "expiry date (YYYY-MM-DD)", "release_date": "release date (YYYY-MM-DD)",
}

_PARTNO = re.compile(r"^[A-Z0-9][A-Z0-9\-]{3,30}$")
_REV = re.compile(r"^[A-Z][0-9]?$")
_SITE = re.compile(r"^SITE-[A-Z0-9\-]+$")
_CURRENCIES = {"GBP", "EUR", "USD"}
_NONE_WORDS = {"", "unknown", "not provided", "n/a", "none", "null"}


def field_key(raw: str) -> str:
    return re.sub(r"[^a-z0-9]+", "_", raw.strip().lower()).strip("_")


def parse_structured_form(text: str) -> dict[str, tuple[str, int]]:
    """Deterministic parser for the structured `FIELD: value` body. Returns {field: (raw, line_no)}."""
    out: dict[str, tuple[str, int]] = {}
    for i, line in enumerate(text.splitlines(), start=1):
        if ":" not in line:
            continue
        k, v = line.split(":", 1)
        key = field_key(k)
        if not key or key in {"record_type"}:
            continue
        out[key] = (v.strip(), i)
    return out


def coerce(type_code: str, raw: Any) -> tuple[Any, str, str | None]:
    """Return (typed_value, validation_state, note)."""
    if raw is None:
        return None, "invalid", "missing"
    if isinstance(raw, (list, bool, int, float)) and type_code not in {"str"}:
        value = raw
    else:
        value = str(raw).strip()
    if isinstance(value, str) and value.lower() in _NONE_WORDS:
        return None, "invalid", f"value '{value}' is not usable evidence"
    try:
        if type_code == "str":
            return str(value), "valid", None
        if type_code == "int":
            return int(Decimal(str(value))), "valid", None
        if type_code in {"decimal"}:
            return str(Decimal(str(value).replace(",", ""))), "valid", None
        if type_code == "ratio":
            d = Decimal(str(value))
            if not (Decimal(0) <= d <= Decimal(1)):
                return None, "invalid", "ratio outside [0,1]"
            return float(d), "valid", None
        if type_code == "date":
            if isinstance(value, (date, datetime)):
                return value.isoformat()[:10], "valid", None
            d = datetime.strptime(str(value)[:10], "%Y-%m-%d").date()
            return d.isoformat(), "valid", None
        if type_code == "bool":
            if isinstance(value, bool):
                return value, "valid", None
            v = str(value).lower()
            if v in {"yes", "true", "y", "1"}:
                return True, "valid", None
            if v in {"no", "false", "n", "0"}:
                return False, "valid", None
            return None, "invalid", f"'{value}' is not a yes/no value"
        if type_code == "list":
            if isinstance(value, list):
                items = [str(x).strip() for x in value if str(x).strip()]
            else:
                items = [x.strip() for x in re.split(r"[;,]", str(value)) if x.strip()]
            return items, "valid", None
        if type_code == "currency":
            v = str(value).upper()
            return (v, "valid", None) if v in _CURRENCIES else (None, "invalid", f"unsupported currency {v}")
        if type_code == "partno":
            v = str(value).upper().replace(" ", "")
            return (v, "valid", None) if _PARTNO.match(v) else (None, "invalid", f"malformed part number {value}")
        if type_code == "revision":
            v = str(value).upper().strip()
            return (v, "valid", None) if _REV.match(v) else (None, "invalid", f"malformed revision {value}")
        if type_code == "site":
            v = str(value).upper().strip()
            return (v, "valid", None) if _SITE.match(v) else (str(value), "valid", "free-text site name")
    except (InvalidOperation, ValueError) as exc:
        return None, "invalid", f"could not parse {type_code}: {exc}"
    return value, "unvalidated", None


def normalise_for_compare(v: Any) -> Any:
    if isinstance(v, list):
        return sorted(str(x).strip().upper() for x in v)
    if isinstance(v, bool) or v is None:
        return v
    s = str(v).strip().upper()
    try:
        return str(Decimal(s.replace(",", "")).normalize())
    except InvalidOperation:
        return s
