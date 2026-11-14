"""Impact propagation through explicit relationship rows (PRD FR-10, FR-11)."""

from __future__ import annotations

from domain_helpers import signal
from recovery.domain.impact import Graph, scope_entities


def _impact(cat, sig_fixture_id):
    g = Graph(cat.relationships)
    ids, hint = scope_entities(signal(cat, sig_fixture_id), cat.sites)
    return g.impact(ids, hint)


def test_rotterdam_closure_reaches_only_offer_a_and_primary_case(cat):
    res = _impact(cat, "SIG-RTM-CLOSURE")
    assert res["offers"] == ["OFF-PA"] and res["cases"] == ["case-primary"]
    path = res["paths"][0]
    assert [(n["id"], n["type"]) for n in path] == [("GEO-PORT-NLRTM", "geo"), ("R-RTM-HWC", "route"), ("OFF-PA", "offer"), ("case-primary", "case")]
    assert [n.get("via") for n in path[1:]] == ["passes_through", "ships_via", "candidate_for"]


def test_hamburg_strike_reaches_shared_site_in_two_cases(cat):
    res = _impact(cat, "SIG-HAM-STRIKE")
    assert res["offers"] == ["OFF-SA2", "OFF-SB1"]
    assert res["cases"] == ["case-secondary-a", "case-secondary-b"]
    assert len(res["paths"]) == 2


def test_unrelated_signal_reaches_nothing(cat):
    res = _impact(cat, "SIG-KHH-TYPHOON")
    assert res["offers"] == [] and res["cases"] == [] and res["paths"] == []


def test_origin_country_tariff_reaches_eu_sites_only(cat):
    res = _impact(cat, "SIG-TARIFF-EU-AERO")
    assert set(res["offers"]) == {"OFF-PA", "OFF-SA2", "OFF-SB1"}  # NL and DE sites


def test_evidence_change_reaches_all_primary_offers(cat):
    g = Graph(cat.relationships)
    res = g.impact(["ev-sb-fn-0042-a"], {"ev-sb-fn-0042-a": "evidence"})
    primary = sorted(cid for cid, o in cat.offers.items() if o["case_id"] == "case-primary")
    assert res["offers"] == primary and res["cases"] == ["case-primary"]


def test_new_evidence_relationship_union_with_old_paths(cat):
    change = cat.evidence_changes["EVC-SB-0042-REVB"]
    rels = cat.relationships + [dict(r, relationship_id=f"rel-new-{i}", evidence_ids=[], effective_from=None, effective_to=None,
                                     recorded_at="2026-11-16T08:00:00Z", revision=1, data_origin="synthetic_demo")
                                for i, r in enumerate(change["relationships"])]
    g = Graph(rels)
    new = g.impact(["ev-sb-fn-0042-b"], {"ev-sb-fn-0042-b": "evidence"})
    old = g.impact(["ev-sb-fn-0042-a"], {"ev-sb-fn-0042-a": "evidence"})
    assert set(new["offers"]) == set(old["offers"])  # new SB applies_to the part → every primary offer of that part
    assert new["cases"] == ["case-primary"]


def test_impact_does_not_leak_to_independent_records(cat):
    res = _impact(cat, "SIG-RTM-CLOSURE")
    assert not {"OFF-PB", "OFF-PC", "OFF-PD", "OFF-PE"} & set(res["offers"])
    assert "SITE-CAL-MAN" not in res["touched"]
