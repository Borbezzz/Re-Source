from copy import deepcopy

import pytest

from recovery.domain.errors import DomainError
from recovery.domain.supply_risk import RiskConfirm, RiskEvidence
from recovery.runtime.context import visitor_id
from recovery.services.supply_risk import SupplyRiskService, evaluate_part


@pytest.fixture
def risk(svc):
    p = svc.products.create("turbofan")
    p = svc.products.review(p["project_id"], p["parts"], True, p["version"])
    service = SupplyRiskService(svc.products)
    scan = service.confirm(p["project_id"], RiskConfirm(expected_project_version=p["version"], needs=[
        dict(part_id=part["part_id"], quantity=2, destination="Bristol, UK", need_by="2026-11-24") for part in p["parts"]
    ]))
    return service, p, scan


def evidence(p, **updates):
    part = p["parts"][0]
    return RiskEvidence.model_validate(dict(
        evidence_id="quote-v1", part_id=part["part_id"], kind="quote", title="Supplier quote Q-17",
        excerpt="Revision B, quantity 2, Bristol UK. Revised arrival 30 November 2026.",
        issued_on="2026-11-10", supplier="Supplier A", part_number=part["part_number"], revision="B",
        quantity=2, destination="Bristol, UK", arrival_on="2026-11-30", **updates,
    ))


def changed(p, **updates):
    value = evidence(p).model_dump(mode="json")
    value.update(updates)
    return RiskEvidence.model_validate(value)


def test_scan_requires_confirmation_and_all_needs(svc):
    p = svc.products.create("turbofan")
    service = SupplyRiskService(svc.products)
    assert service.get(p["project_id"])["status"] == "not_started"
    body = dict(expected_project_version=p["version"], needs=[dict(part_id=p["parts"][0]["part_id"], quantity=1, destination="UK", need_by="2026-11-24")])
    with pytest.raises(DomainError, match="Confirm"):
        service.confirm(p["project_id"], RiskConfirm(**body))
    p = svc.products.review(p["project_id"], p["parts"], True)
    body["expected_project_version"] = p["version"]
    with pytest.raises(DomainError, match="every confirmed part"):
        service.confirm(p["project_id"], RiskConfirm(**body))


def test_late_quote_marks_exact_part_and_retains_source(risk):
    service, p, scan = risk
    result = service.record_evidence(p["project_id"], evidence(p), scan["version"])
    part = result["parts"][0]
    assert part["status"] == "at_risk"
    assert part["observations"][0]["days_late"] == 6
    assert part["observations"][0]["evidence"]["issued_on"] == "2026-11-10"
    assert all(x["status"] != "at_risk" for x in result["parts"][1:])
    reloaded = SupplyRiskService(service.products).get(p["project_id"])
    assert {k: v for k, v in reloaded.items() if k != "evaluated_at"} == {k: v for k, v in result.items() if k != "evaluated_at"}


@pytest.mark.parametrize("field,value", [("revision", None), ("revision", "C"), ("part_number", "WRONG"), ("quantity", 1), ("quantity", None), ("destination", "Paris"), ("destination", None), ("supplier", None)])
def test_unmatched_quote_stays_watchlist(risk, field, value):
    service, p, _ = risk
    result = service.record_evidence(p["project_id"], changed(p, **{field: value}))
    assert result["parts"][0]["status"] == "watchlist"
    assert result["parts"][0]["observations"][0]["level"] == "watchlist"


def test_material_and_freight_never_escalate_from_keyword_match(risk):
    service, p, _ = risk
    for kind in ("material_trend", "freight_pressure"):
        result = service.record_evidence(p["project_id"], changed(p, evidence_id=kind, kind=kind))
    assert result["parts"][0]["status"] == "watchlist"


def test_route_requires_current_matching_shipment(risk):
    service, p, _ = risk
    pid = p["project_id"]
    disruption = changed(p, evidence_id="port", kind="route_disruption", route="Port of Felixstowe", arrival_on=None)
    assert service.record_evidence(pid, disruption)["parts"][0]["status"] == "watchlist"
    service.record_evidence(pid, changed(p, evidence_id="ship", kind="shipment", route="Port of Felixstowe", arrival_on="2026-11-23"))
    assert service.get(pid)["parts"][0]["status"] == "at_risk"
    service.record_evidence(pid, changed(p, evidence_id="reroute", kind="shipment", route="Dover", arrival_on="2026-11-23", issued_on="2026-11-12"))
    port = next(o for o in service.get(pid)["parts"][0]["observations"] if o["evidence"]["evidence_id"] == "port")
    assert port["level"] == "watchlist"


def test_newer_quote_supersedes_alert_without_erasing_history(risk):
    service, p, _ = risk
    service.record_evidence(p["project_id"], evidence(p))
    result = service.record_evidence(p["project_id"], changed(p, evidence_id="quote-v2", issued_on="2026-11-12", arrival_on="2026-11-22", event="Expedited shipment confirmed"))
    assert result["parts"][0]["status"] == "on_time"
    assert [o["level"] for o in result["parts"][0]["observations"]] == ["superseded", "matched"]


def test_unverified_alternative_does_not_clear_original_alert(risk):
    service, p, _ = risk
    service.record_evidence(p["project_id"], evidence(p))
    result = service.record_evidence(p["project_id"], changed(p, evidence_id="alternative", supplier="Supplier B", revision=None, arrival_on="2026-11-23"))
    assert result["parts"][0]["status"] == "at_risk"
    assert any("compatibility" in o["applies_because"] for o in result["parts"][0]["observations"])


def test_delivery_receipt_resolves_and_partial_delivery_does_not(risk):
    service, p, _ = risk
    service.record_evidence(p["project_id"], evidence(p))
    partial = changed(p, evidence_id="partial", kind="delivery", issued_on="2026-11-12", arrival_on="2026-11-12", quantity=1)
    assert service.record_evidence(p["project_id"], partial)["parts"][0]["status"] == "at_risk"
    receipt = changed(p, evidence_id="received", kind="delivery", issued_on="2026-11-13", arrival_on="2026-11-13")
    assert service.record_evidence(p["project_id"], receipt)["parts"][0]["status"] == "received"


def test_immutable_idempotent_and_concurrent_evidence(risk):
    service, p, scan = risk
    first = service.record_evidence(p["project_id"], evidence(p), scan["version"])
    assert service.record_evidence(p["project_id"], evidence(p))["version"] == first["version"]
    with pytest.raises(DomainError) as error:
        service.record_evidence(p["project_id"], changed(p, arrival_on="2026-11-20"))
    assert error.value.code == "EVIDENCE_IMMUTABLE"
    with pytest.raises(DomainError) as error:
        service.record_evidence(p["project_id"], changed(p, evidence_id="another"), scan["version"])
    assert error.value.code == "RISK_SCAN_CHANGED"


def test_requirement_edits_stale_scan_and_reconfirmation_reassesses(risk):
    service, p, _ = risk
    service.record_evidence(p["project_id"], evidence(p))
    parts = deepcopy(p["parts"])
    parts[0]["requirements"] = [{**r, "value": "C", "source": None} if r["key"] == "revision" else r for r in parts[0]["requirements"]]
    current = service.products.review(p["project_id"], parts, True)
    scan = service.get(p["project_id"])
    assert scan["status"] == "needs_confirmation"
    with pytest.raises(DomainError, match="Confirm"):
        service.record_evidence(p["project_id"], changed(p, evidence_id="new"))
    result = service.confirm(p["project_id"], RiskConfirm(expected_project_version=current["version"], needs=[x["need"] for x in scan["parts"]]))
    assert result["status"] == "current"
    assert result["parts"][0]["status"] == "watchlist"


def test_other_visitor_cannot_read_write_or_search(risk, monkeypatch):
    service, p, _ = risk
    token = visitor_id.set("unrelated-visitor")
    monkeypatch.setattr("recovery.services.supply_risk.search_public_context", lambda: pytest.fail("Search must not run before ownership check"))
    try:
        for fn in (lambda: service.get(p["project_id"]), lambda: service.record_evidence(p["project_id"], evidence(p)), lambda: service.refresh(p["project_id"])):
            with pytest.raises(DomainError) as error:
                fn()
            assert error.value.status == 404
    finally:
        visitor_id.reset(token)


def test_material_only_identity_exposes_gap():
    part = dict(part_id="housing", name="Housing", part_number=None, requirements=[dict(key="material", label="Material", value="Aluminium")])
    need = dict(part_id="housing", quantity=1, destination="UK", need_by="2026-11-24")
    result = evaluate_part(part, need, [])
    assert result["exposure"] == ["Material: Aluminium"]
    assert {"Part number", "Required revision"} <= set(result["missing"])
    assert result["status"] == "watchlist"


def test_refresh_sources_cannot_promote_alerts(risk, monkeypatch):
    service, p, _ = risk
    monkeypatch.setattr("recovery.services.supply_risk.search_public_context", lambda: ([dict(name="Tavily", status="unavailable", source_count=0)], []))
    result = service.refresh(p["project_id"])
    assert result["providers"][0]["status"] == "unavailable"
    assert all(part["status"] != "at_risk" for part in result["parts"])


@pytest.mark.parametrize("arrival", [None, "2026-11-30"])
def test_receipt_requires_a_date_no_later_than_its_source(risk, arrival):
    service, p, _ = risk
    with pytest.raises(DomainError, match="receipt"):
        service.record_evidence(p["project_id"], changed(p, kind="delivery", arrival_on=arrival))


def _quote(p, **term_updates):
    values = dict(part_number=p["parts"][0]["part_number"], revision="B", quantity="2 units", destination="Bristol, UK", delivery_date="30 November 2026", quote_date="10 November 2026")
    values.update(term_updates)
    return dict(quote_id="quote-imported", part_id=p["parts"][0]["part_id"], supplier="Imported Supplier", filename="reply.txt", source_kind="reply",
                source_text="The supplier's original reply.", created_at="2026-11-15T10:00:00Z", version=1, input_version=p["input_version"], terms={key: dict(value=value, origin="extracted") for key, value in values.items()})


def test_quote_import_is_reassessed_without_manual_scan_or_import_date_substitution(risk):
    service, p, _ = risk
    with service.products._mutate(p["project_id"]) as project:
        project["_supplier_quotes"] = [_quote(p)]
    result = service.get(p["project_id"])
    assert result["parts"][0]["status"] == "at_risk"
    source = result["parts"][0]["observations"][0]["evidence"]
    assert source["issued_on"] == "2026-11-10"
    assert source["source_document_id"] == "quote-imported"
    with service.products._mutate(p["project_id"]) as project:
        project["_supplier_quotes"][0]["terms"]["quote_date"]["value"] = ""
    result = service.get(p["project_id"])
    assert result["parts"][0]["status"] == "watchlist"
    assert result["parts"][0]["observations"][0]["evidence"]["issued_on"] is None


def test_buyer_correction_and_expired_quote_cannot_become_supplier_commitments(risk):
    service, p, _ = risk
    quote = _quote(p)
    quote["terms"]["revision"]["origin"] = "buyer_review"
    with service.products._mutate(p["project_id"]) as project:
        project["_supplier_quotes"] = [quote]
    assert service.get(p["project_id"])["parts"][0]["status"] == "watchlist"
    with service.products._mutate(p["project_id"]) as project:
        project["_supplier_quotes"] = [_quote(p, valid_until="2026-01-01")]
    assert service.get(p["project_id"])["parts"][0]["status"] == "watchlist"


def test_ambiguous_quote_dates_and_quantities_stay_unknown(risk):
    service, p, _ = risk
    with service.products._mutate(p["project_id"]) as project:
        project["_supplier_quotes"] = [_quote(p, delivery_date="10/11/26", quantity="approximately 2")]
    result = service.get(p["project_id"])
    source = result["parts"][0]["observations"][0]["evidence"]
    assert source["quantity"] is None and source["arrival_on"] is None
    assert result["parts"][0]["status"] == "watchlist"
