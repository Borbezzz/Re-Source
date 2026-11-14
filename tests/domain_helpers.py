"""Shared, generic test helpers for the deterministic domain (no service wiring here).

Service/API fixtures belong in tests/integration/conftest.py.
"""

from __future__ import annotations

import os
import sys
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional

# `pytest ../tests` run from backend/ does not pick up backend/pyproject.toml (not an ancestor of tests/),
# so make the backend package importable explicitly.
_BACKEND = Path(__file__).resolve().parents[1] / "backend"
if str(_BACKEND) not in sys.path:
    sys.path.insert(0, str(_BACKEND))
os.environ.setdefault("MLFLOW_DISABLE_AGENT_HINT", "1")


from recovery.domain import rules as R
from recovery.domain.catalog import Catalog, load_catalog
from recovery.domain.extraction import FIELD_SCHEMAS, coerce, parse_structured_form
from recovery.domain.scheduler import signal_matches_route


def structured_facts(ev: dict) -> dict[str, dict]:
    """Deterministic facts for one evidence version (structured parse + code validation)."""
    parsed = parse_structured_form(ev["content_text"] or "")
    out: dict[str, dict] = {}
    for fld, type_code in FIELD_SCHEMAS[ev["doc_type"]].items():
        if fld not in parsed:
            continue
        raw, line = parsed[fld]
        value, state, note = coerce(type_code, raw)
        out[fld] = {
            "fact_id": f"fact:{ev['version_id']}:{fld}",
            "evidence_version_id": ev["version_id"],
            "field": fld,
            "typed_value": value,
            "original_value": raw,
            "locator": {"line": line},
            "confidence": 0.9,
            "validation_state": state,
            "validation_note": note,
            "extraction_mode": "structured_parse",
        }
    return out


def scenario_start(cat: Catalog) -> datetime:
    return datetime.fromisoformat(cat.scenario["scenario_clock_start"].replace("Z", "+00:00"))


def signal(cat: Catalog, fixture_id: str) -> dict:
    return dict(cat.signals[fixture_id])


def candidate_docs(cat: Catalog, offer: dict, extra_version_ids: tuple[str, ...] = (), replace: Optional[dict[str, str]] = None) -> list[dict]:
    """Offer evidence (initial versions), optionally replacing versions by document (e.g. SB Rev A → Rev B) and adding follow-ups."""
    replace = replace or {}
    docs = []
    for vid in offer["evidence_ids"]:
        docs.append(dict(cat.evidence[replace.get(vid, vid)]))
    for vid in extra_version_ids:
        docs.append(dict(cat.evidence[vid]))
    return docs


def make_ctx(cat: Catalog, cid: str, *, now: Optional[datetime] = None, signals: Optional[list[dict]] = None,
             extra_version_ids: tuple[str, ...] = (), replace: Optional[dict[str, str]] = None) -> R.CandidateContext:
    offer = cat.offers[cid]
    site = cat.sites[offer["site_id"]]
    route = cat.routes[offer["logistics_route_id"]]
    docs = candidate_docs(cat, offer, extra_version_ids, replace)
    facts = {d["version_id"]: structured_facts(d) for d in docs}
    comp = cat.component_for_case(offer["case_id"])
    sigs = [s for s in (signals or []) if signal_matches_route(s, route, site)]
    return R.CandidateContext(
        case_id=offer["case_id"], offer=offer, site=site, supplier=cat.suppliers[offer["supplier_id"]], route=route, component=comp,
        docs=docs, facts=facts, now=now or (scenario_start(cat) + timedelta(hours=1)), signals=sigs,
        applicability=cat.applicability, requirement_set=cat.requirement_sets[comp["requirement_set_id"]],
    )


def evaluate_candidate(cat: Catalog, cid: str, **kw) -> tuple[str, bool, list[dict]]:
    """Run every applicable requirement; return (eligibility, feasible, checks)."""
    ctx = make_ctx(cat, cid, **kw)
    offer = cat.offers[cid]
    comp = cat.component_for_case(offer["case_id"])
    checks = []
    for req in cat.requirements_for(comp["requirement_set_id"]):
        if offer["route"] not in req["routes"]:
            continue
        out = R.evaluate(ctx, req)
        checks.append({"requirement_id": req["requirement_id"], "template_code": req["template_code"], "mandatory": req["mandatory"],
                       "result": out.result, "explanation": out.explanation, "evidence_refs": out.evidence_refs,
                       "fact_refs": out.fact_refs, "feasible_if_unknown": out.feasible_if_unknown, "gap": out.gap,
                       "dependency_ids": out.dependency_ids})
    elig, feasible = R.eligibility_from(checks)
    return elig, feasible, checks
