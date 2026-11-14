"""Mandatory gates and evidence rules (PRD FR-02, FR-05, FR-06, FR-07, FR-08 gates, AC-07)."""

from __future__ import annotations

from datetime import timedelta

import pytest

from domain_helpers import evaluate_candidate, make_ctx, scenario_start, signal
from recovery.domain import rules as R

EXPECTED = {
    # case-primary
    "OFF-PA": ("eligible", True),
    "OFF-PB": ("eligible", True),
    "OFF-PC": ("eligible", True),
    "OFF-PD": ("pending", False),
    "OFF-PE": ("ineligible", False),
    # case-secondary-a (before gap follow-up)
    "OFF-SA1": ("pending", False),
    "OFF-SA2": ("eligible", True),
    "OFF-SA3": ("ineligible", False),
    # case-secondary-b
    "OFF-SB1": ("eligible", True),
    "OFF-SB2": ("pending", True),
    "OFF-SB3": ("eligible", True),
}


def _by_code(checks):
    return {c["template_code"]: c for c in checks}


@pytest.mark.parametrize("cid", sorted(EXPECTED))
def test_seed_eligibility(cat, cid):
    elig, feasible, checks = evaluate_candidate(cat, cid)
    assert (elig, feasible) == EXPECTED[cid], [(c["template_code"], c["result"], c["explanation"]) for c in checks if c["result"] != "pass"]


def test_every_eligible_candidate_passes_all_mandatory_checks_with_evidence(cat):
    for cid, (elig, _) in EXPECTED.items():
        if elig != "eligible":
            continue
        _, _, checks = evaluate_candidate(cat, cid)
        for c in checks:
            assert c["result"] == "pass", (cid, c)
            if c["template_code"] != "LOG":  # route viability is backed by signals/relationships, not documents
                assert c["evidence_refs"], (cid, c["template_code"])
                assert all(ref in cat.evidence for ref in c["evidence_refs"])


def test_route_specific_requirements_apply_only_to_their_route(cat):
    _, _, buy = evaluate_candidate(cat, "OFF-PA")
    _, _, make = evaluate_candidate(cat, "OFF-PC")
    assert {"REL", "TRC"} <= set(_by_code(buy)) and not {"POA", "DD", "SPC", "FAI"} & set(_by_code(buy))
    assert {"POA", "DD", "SPC", "FAI"} <= set(_by_code(make)) and not {"REL", "TRC"} & set(_by_code(make))


# ---------------------------------------------------------------------------------------- AC-07
def test_missing_release_certificate_is_mandatory_unknown_with_gap(cat):
    _, _, checks = evaluate_candidate(cat, "OFF-PD")
    rel = _by_code(checks)["REL"]
    assert rel["result"] == "unknown" and rel["gap"] and "supplier_replies" in rel["gap"]["allowed_sources"]
    assert _by_code(checks)["TRC"]["result"] == "unknown"  # "unknown"/"not provided" values are not usable evidence
    assert _by_code(checks)["REG"]["result"] == "unknown"


def test_near_match_wrong_revision_fails_and_contradiction_is_preserved(cat):
    ctx = make_ctx(cat, "OFF-PE")
    req = next(r for r in cat.requirements_for("RS-REQ-FN-1001") if r["template_code"] == "ID")
    out = R.evaluate(ctx, req)
    assert out.result == "fail" and "Near-match" in out.explanation
    # quote says RS-FN-1001-C, release certificate says RS-FN-1001: higher authority kept, other value preserved
    assert any(c["field"] == "part_number" and c["kept"]["value"] == "RS-FN-1001" and c["other"]["value"] == "RS-FN-1001-C"
               for c in out.contradictions)
    _, _, checks = evaluate_candidate(cat, "OFF-PE")
    assert _by_code(checks)["IC"]["result"] == "fail"


def test_expired_certificate_fails(cat):
    _, _, checks = evaluate_candidate(cat, "OFF-SA3")
    qms = _by_code(checks)["QMS"]
    assert qms["result"] == "fail" and "expired" in qms["explanation"]


def test_wrong_site_certificate_cannot_qualify_another_site(cat):
    _, _, checks = evaluate_candidate(cat, "OFF-SB2")
    by = _by_code(checks)
    assert by["QMS"]["result"] == "unknown" and "SITE-PEN-SHF" in by["QMS"]["explanation"]
    assert by["POA"]["result"] == "unknown"
    assert by["FAI"]["result"] == "unknown"
    assert all(c["feasible_if_unknown"] for c in checks if c["result"] == "unknown")


def test_secondary_b_make_without_poa_uses_form_60_authority_branch(cat):
    ctx = make_ctx(cat, "OFF-SB2")
    res = R.resolve_applicability(ctx)
    assert res["rule"]["rule_id"] == "APP-MAKE-NO-POA"
    assert res["rule"]["package"] == ["TPL-CAA-FORM-60"] and res["rule"]["authority_application"] is True
    ok = R.resolve_applicability(make_ctx(cat, "OFF-SB3"))
    assert ok["rule"]["rule_id"] == "APP-MAKE-POA" and ok["rule"]["authority_application"] is False
    buy = R.resolve_applicability(make_ctx(cat, "OFF-PA"))
    assert buy["rule"]["rule_id"] == "APP-BUY-RELEASED" and buy["rule"]["destination_type"] == "internal_quality_records"


def test_certificate_expiry_during_scenario_invalidates_on_clock_advance(cat):
    start = scenario_start(cat)
    assert evaluate_candidate(cat, "OFF-SA2", now=start + timedelta(days=1))[0] == "eligible"
    elig, _, checks = evaluate_candidate(cat, "OFF-SA2", now=start + timedelta(days=6))
    assert elig == "ineligible" and _by_code(checks)["QMS"]["result"] == "fail"


# ---------------------------------------------------------------------------------------- FR-05
def test_gap_resolution_by_follow_up_evidence(cat):
    elig, _, checks = evaluate_candidate(cat, "OFF-SA1")
    trc = _by_code(checks)["TRC"]
    assert elig == "pending" and trc["result"] == "unknown" and trc["gap"]
    elig2, _, checks2 = evaluate_candidate(cat, "OFF-SA1", extra_version_ids=("ev-tr-sa1",))
    assert elig2 == "eligible" and "ev-tr-sa1" in _by_code(checks2)["TRC"]["evidence_refs"]


def test_supplier_reply_fixture_supports_one_resolved_and_one_pending_gap(cat):
    replies = cat.supplier_replies
    assert any(r["candidate_id"] == "OFF-SA1" and r["evidence"] for r in replies)
    sa3 = [r for r in replies if r["candidate_id"] == "OFF-SA3"]
    assert len(sa3) >= 2 and not any(r["evidence"] for r in sa3)  # exhausts the default 2-attempt budget


# ---------------------------------------------------------------------------------------- FR-04/AC-05 evidence change
def test_new_service_bulletin_revision_invalidates_make_design_basis(cat):
    replace = {"ev-sb-fn-0042-a": "ev-sb-fn-0042-b"}
    elig, _, checks = evaluate_candidate(cat, "OFF-PC", replace=replace)
    dd = _by_code(checks)["DD"]
    assert elig == "ineligible" and dd["result"] == "fail" and "ev-sb-fn-0042-b" in dd["evidence_refs"]
    for cid in ("OFF-PA", "OFF-PB"):
        e, _, cs = evaluate_candidate(cat, cid, replace=replace)
        assert e == "eligible"
        assert "ev-sb-fn-0042-b" in _by_code(cs)["IC"]["evidence_refs"]


# ---------------------------------------------------------------------------------------- signals & gates
def test_route_viability_reflects_disruption_but_stays_open(cat):
    rtm = signal(cat, "SIG-RTM-CLOSURE")
    elig, _, checks = evaluate_candidate(cat, "OFF-PA", signals=[rtm])
    log = _by_code(checks)["LOG"]
    assert elig == "eligible" and log["result"] == "pass" and "+7" in log["explanation"]
    assert "sig-rtm-closure-v1" in log["dependency_ids"]
    # unrelated offer is untouched by the signal
    assert "sig-rtm-closure-v1" not in _by_code(evaluate_candidate(cat, "OFF-PB", signals=[rtm])[2])["LOG"]["dependency_ids"]


def test_blocked_route_fails_the_mandatory_gate(cat):
    blocked = dict(signal(cat, "SIG-RTM-CLOSURE"))
    blocked["assertion"] = {**blocked["assertion"], "type": "route_blocked"}
    elig, _, checks = evaluate_candidate(cat, "OFF-PA", signals=[blocked])
    assert elig == "ineligible" and _by_code(checks)["LOG"]["result"] == "fail"


def test_eligibility_gates_are_strict():
    mk = lambda r, m=True, f=False: {"mandatory": m, "result": r, "feasible_if_unknown": f}  # noqa: E731
    assert R.eligibility_from([mk("pass"), mk("pass")]) == ("eligible", True)
    assert R.eligibility_from([mk("pass"), mk("fail"), mk("unknown", f=True)]) == ("ineligible", False)
    assert R.eligibility_from([mk("pass"), mk("unknown", f=True)]) == ("pending", True)
    assert R.eligibility_from([mk("unknown", f=True), mk("unknown", f=False)]) == ("pending", False)
    assert R.eligibility_from([mk("pass"), mk("fail", m=False)]) == ("eligible", True)  # non-mandatory never gates


def test_check_fingerprint_is_stable_and_input_sensitive(cat):
    ctx = make_ctx(cat, "OFF-PA")
    req = next(r for r in cat.requirements_for("RS-REQ-FN-1001") if r["template_code"] == "LOG")
    a = R.check_fingerprint(req, R.evaluate(ctx, req))
    assert a == R.check_fingerprint(req, R.evaluate(make_ctx(cat, "OFF-PA"), req))
    b = R.check_fingerprint(req, R.evaluate(make_ctx(cat, "OFF-PA", signals=[signal(cat, "SIG-RTM-CLOSURE")]), req))
    assert a != b


# ---------------------------------------------------------------------------------------- FR-06 / FR-11 data contracts
def test_reliability_metrics_are_labelled_fixtures_and_site_specific(cat):
    for m in cat.metrics:
        assert m["data_origin"] == "synthetic_demo" and m["fixture_note"] and m["label"] and m["window"]
        assert m["site_id"] in cat.sites and m["source_evidence_id"] in cat.evidence
    otd = [m for m in cat.metrics if m["metric_name"] == "on_time_delivery_rate"]
    for m in otd:
        assert m["value"] == round(m["numerator"] / m["denominator"], 4)
    assert cat.metric("SITE-CAL-MAN", "on_time_delivery_rate")["value"] != cat.metric("SITE-CAL-GLA", "on_time_delivery_rate")["value"]


def test_relationship_rows_carry_provenance_fields(cat):
    for r in cat.relationships:
        for k in ("from_id", "from_type", "to_id", "to_type", "relation_type", "evidence_ids", "effective_from", "recorded_at", "revision"):
            assert k in r
    sites = {r["from_id"] for r in cat.relationships if r["from_type"] == "site"}
    suppliers = {r["to_id"] for r in cat.relationships if r["relation_type"] == "operated_by"}
    assert sites.isdisjoint(suppliers)  # supplier legal entity and physical site are distinct entities


def test_all_fixture_entities_are_marked_synthetic(cat):
    for coll in (cat.offers.values(), cat.suppliers.values(), cat.sites.values(), cat.evidence.values()):
        for item in coll:
            assert item["data_origin"] == "synthetic_demo"
