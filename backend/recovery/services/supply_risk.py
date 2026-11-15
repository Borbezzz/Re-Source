"""Deterministic part/deadline assessment; public news is discovery, not proof.

The private project envelope uses the existing tenant check and transaction lock.
Evidence is append-only and scoped to a source version. GET re-evaluates it, so
quote importers can append through record_evidence without a second scan job.
"""
from __future__ import annotations

import hashlib
import json
import os
import re
from concurrent.futures import ThreadPoolExecutor
from datetime import date, datetime
from urllib.parse import urlsplit

import httpx

from ..adapters.store import now_iso
from ..config import settings
from ..domain.errors import conflict, invalid
from ..domain.supply_risk import RiskConfirm, RiskEvidence, RiskScan

REFERENCES = [
    ("IMF PortWatch", "https://portwatch.imf.org/", "Port and route activity. Apply a disruption only after matching a documented shipment route."),
    ("USGS Mineral Commodity Summaries", "https://www.usgs.gov/centers/national-minerals-information-center/mineral-commodity-summaries", "Material exposure context. A mineral trend alone does not establish a delay for this part."),
    ("New York Fed Global Supply Chain Pressure Index", "https://www.newyorkfed.org/research/policy/gscpi", "Global freight and manufacturing pressure. Context only until a supplier or shipment is affected."),
]


def _norm(value) -> str:
    return " ".join(str(value or "").casefold().split())


def revision(part: dict) -> str | None:
    return next((r["value"] for r in part.get("requirements", []) if r["key"] in {"revision", "rev"}), None)


def _fingerprint(project: dict) -> str:
    # Sourcing activity may increment project.version without changing requirements.
    return hashlib.sha256(json.dumps(project["parts"], sort_keys=True).encode()).hexdigest()


def _scope(e: dict, part: dict, need: dict, *, check_validity: bool = True) -> tuple[bool, str]:
    if e.get("origin") == "synthetic_demo":
        return False, "Illustrative evidence cannot establish a project delivery commitment."
    if e.get("unverified_reason"):
        return False, e["unverified_reason"]
    if not e.get("issued_on"):
        return False, "The document issue date is missing. The import date cannot establish a dated supplier commitment."
    if check_validity and e.get("valid_until") and e["valid_until"] < date.today().isoformat():
        return False, "This quote has expired. Request a current supplier commitment."
    if not part.get("part_number") or not revision(part):
        return False, "Part number or revision is missing; only broader exposure can be assessed."
    if not e.get("part_number") or _norm(e["part_number"]) != _norm(part["part_number"]):
        return False, "The source does not establish the required part number."
    if not e.get("revision") or _norm(e["revision"]) != _norm(revision(part)):
        return False, "Revision compatibility still needs verification."
    if not e.get("supplier"):
        return False, "The supplying organization is missing."
    if not e.get("quantity") or e["quantity"] < need["quantity"]:
        return False, "The source does not cover the required purchase quantity."
    if not e.get("destination") or _norm(e["destination"]) != _norm(need["destination"]):
        return False, "The source does not confirm delivery to the project destination."
    return True, "Required part, revision, purchase quantity and destination match the dated source."


def evaluate_part(part: dict, need: dict, evidence: list[dict]) -> dict:
    rows = sorted((e for e in evidence if e["part_id"] == part["part_id"]), key=lambda e: (e["issued_on"] or "", e.get("recorded_at", ""), e["evidence_id"]))
    scoped = {e["evidence_id"]: _scope(e, part, need) for e in rows}
    # Expiry must not revive an older estimate. A valid receipt covering the
    # whole need remains authoritative over subsequent arrival estimates.
    latest: dict[str, dict] = {}
    for e in rows:
        if _scope(e, part, need, check_validity=False)[0] and e["kind"] in {"quote", "backorder", "shipment", "delivery"}:
            supplier = _norm(e["supplier"])
            current = latest.get(supplier)
            if current and current["kind"] == "delivery" and scoped[current["evidence_id"]][0]:
                continue
            latest[supplier] = e
    routes = {_norm(e.get("route")) for e in latest.values() if e["kind"] == "shipment" and e.get("route") and scoped[e["evidence_id"]][0]}
    observations = []
    for e in rows:
        match, why = scoped[e["evidence_id"]]
        kind = e["kind"]
        days = (date.fromisoformat(e["arrival_on"]) - date.fromisoformat(need["need_by"])).days if e.get("arrival_on") else None
        level = "watchlist"
        if kind in {"material_trend", "freight_pressure"}:
            why = "Broader exposure only. No supplier commitment or shipment dependency has been established."
        elif kind == "route_disruption":
            if e.get("origin") == "synthetic_demo":
                why = "Illustrative evidence cannot establish a project route disruption."
            elif e.get("unverified_reason"):
                why = e["unverified_reason"]
            elif e.get("valid_until") and e["valid_until"] < date.today().isoformat():
                why = "This disruption evidence has expired. Verify current route conditions."
            elif e.get("issued_on") and e.get("route") and _norm(e["route"]) in routes:
                level, why = "alert", "The disrupted route matches a current shipment with the required part, revision, quantity and destination. Delay length remains unknown."
            else:
                why = "No current, matching shipment is documented on this route."
        elif match:
            current = latest.get(_norm(e["supplier"]))
            if current and current["evidence_id"] != e["evidence_id"]:
                level, why = "superseded", "A governing dated observation or matching receipt from this supplier supersedes this estimate."
            elif kind == "delivery":
                level, why = "matched", "Receipt covers the required part, revision, quantity and destination."
            elif kind == "backorder":
                level, why = "alert", "The supplier confirms a backorder on the required part and revision for this need."
            elif days is not None and days > 0:
                level, why = "alert", f"The quoted arrival is {days} day{'s' if days != 1 else ''} after the need-by date; identity, quantity and destination match."
            elif days is not None:
                level = "matched"
            else:
                why = "Dependency matches, but an arrival date is still needed to assess the deadline."
        observations.append({"evidence": {k: v for k, v in e.items() if k != "recorded_at"}, "level": level, "applies_because": why, "days_late": days})
    alerts = [o for o in observations if o["level"] == "alert"]
    received = any(o["level"] == "matched" and o["evidence"]["kind"] == "delivery" for o in observations)
    on_time = any(o["level"] == "matched" and o["days_late"] is not None and o["days_late"] <= 0 for o in observations)
    missing = []
    if not part.get("part_number"):
        missing.append("Part number")
    if not revision(part):
        missing.append("Required revision")
    if not any(o["level"] in {"matched", "alert"} and o["evidence"]["kind"] in {"quote", "shipment", "delivery"} and o["days_late"] is not None for o in observations):
        missing.append("Supplier-confirmed arrival date")
    exposure = [f'{r["label"]}: {r["value"]}' for r in part.get("requirements", []) if r["key"] in {"material", "process", "manufacturing_process"}]
    status = "received" if received else "at_risk" if alerts else "on_time" if on_time else "watchlist" if observations or exposure else "unknown"
    if received:
        summary = "A matching delivery receipt covers this need. Review the receipt date against the deadline."
    elif alerts:
        summary = alerts[-1]["applies_because"]
    elif on_time:
        summary = "The latest matching arrival estimate is on or before the deadline. Delivery is not yet confirmed."
    else:
        summary = "There is not enough matching delivery evidence to establish whether this part will meet the deadline."
    actions = (["Verify an earlier alternative quote and its revision compatibility.", "Ask the current supplier for an expedited, destination-specific commitment."] if alerts else ["Request a dated arrival commitment covering the required revision, quantity and destination."])
    if missing:
        actions.append("Confirm missing details: " + ", ".join(missing) + ".")
    if exposure:
        actions.append("Confirm the exact part and supplier before promoting material or process exposure to an alert.")
    return {"part_id": part["part_id"], "name": part["name"], "part_number": part.get("part_number"), "revision": revision(part), "need": need, "status": status, "summary": summary, "missing": missing, "exposure": exposure, "observations": observations, "actions": actions}


def _source_date(value: str) -> str | None:
    for pattern in ("%Y-%m-%d", "%d %B %Y", "%d %b %Y"):
        try:
            return datetime.strptime(value.strip(), pattern).date().isoformat()
        except ValueError:
            pass
    return None


def imported_quote_evidence(project: dict) -> list[dict]:
    """Read the quote-import module's saved contract without a cross-service write.

    A reviewed term is a buyer assertion, not a new supplier document. Only
    literal source-backed fields can establish a dependency. Import timestamps
    are deliberately never substituted for quote issue dates.
    """
    result = []
    for quote in project.get("_supplier_quotes", []):
        terms = quote.get("terms", {})
        value = lambda key: str(terms.get(key, {}).get("value") or "").strip()
        quantity = re.fullmatch(r"(\d{1,7})(?:\s+(?:units|pieces))?", value("quantity"), re.I)
        critical = ["part_number", "revision", "quantity", "destination", "delivery_date", "quote_date", "valid_until"]
        why = None
        if quote.get("input_version") != project.get("input_version"):
            why = "Project requirements changed since this quote was imported. Ask the supplier to reconfirm."
        elif any(terms.get(key, {}).get("origin") == "buyer_review" for key in critical):
            why = "Buyer-edited terms require supplier confirmation before they can establish delivery scope."
        issued = _source_date(value("quote_date"))
        if issued and issued > date.today().isoformat():
            why = "The stated issue date is in the future and needs verification."
        valid_until = _source_date(value("valid_until"))
        if value("valid_until") and valid_until is None:
            why = "The quote expiry date is ambiguous and needs supplier verification."
        evidence = RiskEvidence(
            evidence_id=f'import:{quote["quote_id"]}:v{quote["version"]}', part_id=quote["part_id"], kind="quote",
            title=f'{quote["supplier"]} · {quote["filename"]}'[:200], source_document_id=quote["quote_id"], source_version=str(quote["version"]),
            excerpt=str(quote.get("source_text") or "Open the source document to review the quoted terms.")[:4000], issued_on=issued,
            supplier=quote["supplier"], part_number=value("part_number")[:150] or None, revision=value("revision")[:100] or None,
            quantity=int(quantity[1]) if quantity and 0 < int(quantity[1]) <= 1000000 else None,
            destination=value("destination")[:200] or None, arrival_on=_source_date(value("delivery_date")),
            valid_until=valid_until, unverified_reason=why,
        ).model_dump(mode="json")
        result.append(evidence)
    return result


def search_public_context() -> tuple[list[dict], list[dict]]:
    """Only a generic public query leaves the server; project data is never sent."""
    query = f"Latest {date.today().year} supply chain disruption freight pressure port shipping mineral supply IMF PortWatch USGS New York Fed GSCPI"
    retrieved = now_iso()

    def search(name: str):
        key = os.getenv("TAVILY_API_KEY", "") if name == "Tavily" else settings.linkup_api_key
        if not key:
            return {"name": name, "status": "not_configured", "source_count": 0}, []
        try:
            url = "https://api.tavily.com/search" if name == "Tavily" else "https://api.linkup.so/v1/search"
            body = {"query": query, "search_depth": "basic", "max_results": 5, "include_domains": ["imf.org", "usgs.gov", "newyorkfed.org"]} if name == "Tavily" else {"q": query + " primary sources only: imf.org, usgs.gov, newyorkfed.org", "depth": "standard", "outputType": "searchResults"}
            response = httpx.post(url, headers={"Authorization": f"Bearer {key}"}, json=body, timeout=10)
            response.raise_for_status()
            sources = []
            for row in response.json().get("results", [])[:8]:
                link = row.get("url") or ""
                parsed = urlsplit(link)
                host = parsed.hostname or ""
                if parsed.scheme not in {"https", "http"} or parsed.username or parsed.password or not any(host == d or host.endswith("." + d) for d in ("imf.org", "usgs.gov", "newyorkfed.org")):
                    continue
                preview = " ".join(str(row.get("content") or row.get("snippet") or "No excerpt supplied; open the source.").split()[:25])
                sources.append({"title": str(row.get("title") or row.get("name") or host)[:200], "url": link, "excerpt": preview, "publisher": host, "published_on": row.get("published_date") or None, "retrieved_at": retrieved, "provider": name})
            return {"name": name, "status": "searched", "source_count": len(sources)}, sources
        except (httpx.HTTPError, ValueError, TypeError, AttributeError):
            # Never return provider response bodies or authorization details.
            return {"name": name, "status": "unavailable", "source_count": 0}, []

    with ThreadPoolExecutor(max_workers=2) as executor:
        results = list(executor.map(search, ["Tavily", "Linkup"]))
    sources = {}
    for _, rows in results:
        for row in rows:
            parsed = urlsplit(row["url"])
            canonical = f'https://{parsed.hostname}{parsed.path.removesuffix(".html").rstrip("/")}'
            sources.setdefault(canonical, row)
    for title, url, excerpt in REFERENCES:
        canonical = url.rstrip("/")
        # Reference cards describe the dataset's scope, not a scraped navigation menu.
        sources[canonical] = {"title": title, "url": url, "excerpt": excerpt, "publisher": urlsplit(url).hostname, "published_on": None, "retrieved_at": retrieved, "provider": "Reference"}
    return [result[0] for result in results], list(sources.values())


class SupplyRiskService:
    def __init__(self, products):
        self.products = products

    def get(self, project_id: str) -> dict:
        project = self.products._load(project_id)
        state = project.get("_supply_risk")
        result = {"project_id": project_id, "project_version": project["version"], "version": state["version"] if state else 0, "status": "not_started", "evaluated_at": now_iso()}
        if state:
            needs = {n["part_id"]: n for n in state["needs"]}
            evidence = state["evidence"] + imported_quote_evidence(project)
            result.update(status="current" if state["fingerprint"] == _fingerprint(project) else "needs_confirmation", searched_at=state.get("searched_at"), sources=state.get("sources", []), providers=state.get("providers", []), parts=[evaluate_part(p, needs[p["part_id"]], evidence) for p in project["parts"] if p["part_id"] in needs])
        return RiskScan.model_validate(result).model_dump(mode="json")

    def confirm(self, project_id: str, body: RiskConfirm) -> dict:
        with self.products._mutate(project_id, body.expected_project_version) as project:
            if not project["parts"] or any(p["status"] != "confirmed" for p in project["parts"]):
                raise invalid("Confirm the parts list before running the supply-risk scan.")
            needs = [n.model_dump(mode="json") for n in body.needs]
            if len({n["part_id"] for n in needs}) != len(needs) or {n["part_id"] for n in needs} != {p["part_id"] for p in project["parts"]}:
                raise invalid("Provide one quantity, destination and need-by date for every confirmed part.")
            old = project.get("_supply_risk", {})
            project["_supply_risk"] = {**old, "version": old.get("version", 0) + 1, "needs": needs, "fingerprint": _fingerprint(project), "evidence": old.get("evidence", [])}
        return self.get(project_id)

    def refresh(self, project_id: str) -> dict:
        before = self.get(project_id)
        if before["status"] != "current":
            raise invalid("Confirm the current parts and project needs before searching.")
        providers, sources = search_public_context()
        with self.products._mutate(project_id) as project:
            state = project["_supply_risk"]
            if state["version"] != before["version"] or state["fingerprint"] != _fingerprint(project):
                raise conflict("RISK_SCAN_CHANGED", "The scan changed during research. Refresh and try again.")
            state.update(providers=providers, sources=sources, searched_at=now_iso(), version=state["version"] + 1)
        return self.get(project_id)

    def record_evidence(self, project_id: str, evidence: RiskEvidence, expected_version: int | None = None) -> dict:
        with self.products._mutate(project_id) as project:
            state = project.get("_supply_risk")
            if not state or state["fingerprint"] != _fingerprint(project):
                raise invalid("Confirm the current parts and project needs before adding evidence.")
            if expected_version is not None and state["version"] != expected_version:
                raise conflict("RISK_SCAN_CHANGED", "New evidence arrived. Refresh before saving.")
            if evidence.part_id not in {p["part_id"] for p in project["parts"]}:
                raise invalid("This evidence does not belong to a confirmed part in this project.")
            data = evidence.model_dump(mode="json")
            if evidence.issued_on and evidence.issued_on > date.today():
                raise invalid("The source date cannot be in the future.")
            if evidence.kind == "delivery" and (evidence.issued_on is None or evidence.arrival_on is None or evidence.arrival_on > evidence.issued_on):
                raise invalid("A delivery receipt needs an actual receipt date on or before the source date.")
            existing = next((e for e in state["evidence"] if e["evidence_id"] == evidence.evidence_id), None)
            if existing:
                if {k: v for k, v in existing.items() if k != "recorded_at"} != data:
                    raise conflict("EVIDENCE_IMMUTABLE", "A source version is immutable. Add the revised document as a new observation.")
            else:
                if len(state["evidence"]) >= 1000:
                    raise invalid("This scan has reached its 1,000-observation limit.")
                state["evidence"].append({**data, "recorded_at": now_iso()})
                state["version"] += 1
        return self.get(project_id)
