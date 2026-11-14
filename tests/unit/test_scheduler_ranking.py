"""Recovery scheduling and transparent ranking against independently computed expectations
(PRD FR-08, FR-09, §10 primary fixture, AC-06)."""

from __future__ import annotations

from decimal import Decimal

import pytest
import yaml

from domain_helpers import evaluate_candidate, signal
from recovery.config import settings
from recovery.domain.ranking import rank, score_candidate
from recovery.domain.scheduler import build_plan, exposure_for

CFG = yaml.safe_load((settings.rules_dir / "ranking" / "default-v1.yaml").read_text())


# ------------------------------------------------------------------------- independent reference implementation
def ref_days(plan_fixture: dict, delay: float = 0.0, windows: list | None = None, slot_step: str | None = None) -> float:
    """Longest path over the fixture steps; transport gets the signal delay; a slotted step starts no earlier than
    the first window that can hold it."""
    dur = {s["step_id"]: s["duration"]["value"] + (delay if s["kind"] == "transport" else 0.0) for s in plan_fixture["steps"]}
    finish: dict[str, float] = {}
    for s in plan_fixture["steps"]:  # fixtures list steps in dependency order
        start = max([finish[d] for d in s["depends_on"]], default=0.0)
        if windows and s["step_id"] == slot_step:
            start = next(max(start, lo) for lo, hi in windows if max(start, lo) + dur[s["step_id"]] <= hi)
        finish[s["step_id"]] = start + dur[s["step_id"]]
    return max(finish.values())


def ref_landed(cat, cid: str, surcharge: Decimal = Decimal(0)) -> Decimal:
    o = cat.offers[cid]
    rate = Decimal(cat.fx["rates"][o["price"]["currency"]])
    total = (Decimal(o["price"]["amount"]) * o["quantity"] * rate).quantize(Decimal("0.01"))
    total += Decimal(cat.routes[o["logistics_route_id"]]["freight"]["amount"])
    total += sum(Decimal(x["amount"]) for x in cat.plans[cid]["extra_costs"])
    return total + surcharge


def ref_score(case_id: str, days: float, cost: float, otd: float, exposure: float) -> float:
    n = CFG["normalisation"]
    cb = n["landed_cost"]["per_case"][case_id]
    clamp = lambda x: max(0.0, min(1.0, x))  # noqa: E731
    speed = clamp((n["recovery_speed"]["worst"] - days) / (n["recovery_speed"]["worst"] - n["recovery_speed"]["best"]))
    c = clamp((cb["worst"] - cost) / (cb["worst"] - cb["best"]))
    rel = clamp((otd - 0.80) / (1.0 - 0.80))
    return 100 * (0.45 * speed + 0.25 * c + 0.20 * rel + 0.10 * (1 - exposure))


def plan_for(cat, cid, sigs=()):
    o = cat.offers[cid]
    site, route = cat.sites[o["site_id"]], cat.routes[o["logistics_route_id"]]
    return build_plan(o, cat.plans[cid], route, site, list(sigs), cat.fx), exposure_for(route, site, list(sigs))


def ranked_case(cat, case_id, sigs=(), extra=None):
    rows = []
    for cid, o in sorted(cat.offers.items()):
        if o["case_id"] != case_id:
            continue
        elig, feasible, _ = evaluate_candidate(cat, cid, signals=list(sigs), extra_version_ids=(extra or {}).get(cid, ()))
        plan, exp = plan_for(cat, cid, sigs)
        otd = cat.metric(o["site_id"], "on_time_delivery_rate")["value"]
        sc = score_candidate(case_id, plan, otd, exp["value"], cat.ranking) if elig == "eligible" else None
        rows.append({"candidate": o, "eligibility": elig, "feasible": feasible, "score": sc, "plan": plan})
    return rank(rows), rows


# ------------------------------------------------------------------------- plans (FR-09)
@pytest.mark.parametrize("cid,days,landed", [
    ("OFF-PA", 4.0, "48000.00"), ("OFF-PB", 6.0, "56000.00"), ("OFF-PC", 21.0, "74000.00"),
    ("OFF-SA1", 5.0, "32150.00"), ("OFF-SB1", 18.0, "14200.00"), ("OFF-SB3", 12.0, "15400.00"),
])
def test_seed_plans_match_independent_calculation(cat, cid, days, landed):
    plan, _ = plan_for(cat, cid)
    slot = cat.plans[cid].get("capacity_slots")
    expected_days = ref_days(cat.plans[cid], windows=slot and slot["windows"], slot_step=slot and slot["step_id"])
    assert plan["finish_day"] == pytest.approx(expected_days) == pytest.approx(days)
    assert Decimal(plan["landed_cost"]["amount"]) == ref_landed(cat, cid) == Decimal(landed)
    assert plan["landed_cost"]["currency"] == "GBP"


def test_make_plan_uses_cp_sat_with_capacity_window(cat):
    plan, _ = plan_for(cat, "OFF-PC")
    assert plan["solver"] == "cp_sat" and plan["solver_status"] == "OPTIMAL"
    assert plan["solver_detail"]["chosen_window"] == [5, 13]
    machine = next(s for s in plan["steps"] if s["step_id"] == "machine")
    assert machine["start_day"] >= 5 and machine["finish_day"] <= 13


def test_critical_path_and_elapsed_vs_labour(cat):
    plan, _ = plan_for(cat, "OFF-PA")
    assert plan["critical_path"] == ["alloc", "ship", "recv", "ready"]  # docs review (0.5 d) runs in parallel with allocation
    assert plan["elapsed_days"] == 4.0 and plan["labour_days"] == 4.5  # summed labour ≠ elapsed recovery time
    by = {s["step_id"]: s for s in plan["steps"]}
    assert by["docs"]["on_critical_path"] is False and by["ship"]["on_critical_path"] is True
    for s in plan["steps"]:
        for d in s["depends_on"]:
            assert by[d]["finish_day"] <= s["start_day"]


def test_fx_conversion_is_recorded(cat):
    plan, _ = plan_for(cat, "OFF-SA2")
    part = plan["cost_breakdown"][0]
    assert part["original"] == {"amount": "50575.00", "currency": "EUR"}
    assert part["converted"] == {"amount": "44000.25", "currency": "GBP"} and part["fx_version"] == cat.fx["fx_version"]
    assert Decimal(plan["landed_cost"]["amount"]) == ref_landed(cat, "OFF-SA2")


def test_signal_changes_dependent_completion_time_and_cost(cat):
    rtm = signal(cat, "SIG-RTM-CLOSURE")
    plan, exp = plan_for(cat, "OFF-PA", [rtm])
    assert plan["finish_day"] == pytest.approx(ref_days(cat.plans["OFF-PA"], delay=7.0)) == 11.0
    assert Decimal(plan["landed_cost"]["amount"]) == ref_landed(cat, "OFF-PA", Decimal("2500.00")) == Decimal("50500.00")
    assert next(s for s in plan["steps"] if s["step_id"] == "ship")["adjusted_by"] == ["sig-rtm-closure-v1"]
    assert exp["value"] == 0.8
    # unaffected candidate is unchanged
    pb, pb_exp = plan_for(cat, "OFF-PB", [rtm])
    assert pb == plan_for(cat, "OFF-PB")[0] and pb_exp["value"] == 0.05


# ------------------------------------------------------------------------- ranking (FR-08, §10)
def test_primary_d1_order_and_scores(cat):
    ranked, _ = ranked_case(cat, "case-primary")
    assert [r["candidate"]["candidate_id"] for r in ranked] == ["OFF-PA", "OFF-PB", "OFF-PC"]
    expected = {"OFF-PA": ref_score("case-primary", 4, 48000, 0.97, 0.10), "OFF-PB": ref_score("case-primary", 6, 56000, 0.98, 0.05),
                "OFF-PC": ref_score("case-primary", 21, 74000, 0.95, 0.10)}
    for r in ranked:
        assert r["score"]["score"] == pytest.approx(round(expected[r["candidate"]["candidate_id"]], 2), abs=0.005)
    assert [round(expected[k], 2) for k in ("OFF-PA", "OFF-PB", "OFF-PC")] == [85.79, 82.07, 49.96]


def test_primary_d2_reorders_after_port_closure(cat):
    ranked, _ = ranked_case(cat, "case-primary", [signal(cat, "SIG-RTM-CLOSURE")])
    assert [r["candidate"]["candidate_id"] for r in ranked] == ["OFF-PB", "OFF-PA", "OFF-PC"]
    a = next(r for r in ranked if r["candidate"]["candidate_id"] == "OFF-PA")
    assert a["score"]["score"] == pytest.approx(round(ref_score("case-primary", 11, 50500, 0.97, 0.8), 2), abs=0.005)
    assert round(ref_score("case-primary", 11, 50500, 0.97, 0.8), 2) == 66.91
    # historical reliability does not drop because of the disruption (FR-06)
    assert a["score"]["historical_reliability"] == ranked_case(cat, "case-primary")[0][0]["score"]["historical_reliability"]


def test_unrelated_signal_changes_nothing(cat):
    base, _ = ranked_case(cat, "case-primary")
    after, _ = ranked_case(cat, "case-primary", [signal(cat, "SIG-KHH-TYPHOON")])
    assert [(r["candidate"]["candidate_id"], r["score"]) for r in base] == [(r["candidate"]["candidate_id"], r["score"]) for r in after]


def test_corrected_signal_adjusts_and_retraction_restores(cat):
    corrected, _ = ranked_case(cat, "case-primary", [signal(cat, "SIG-RTM-CLOSURE-CORRECTION")])
    a = next(r for r in corrected if r["candidate"]["candidate_id"] == "OFF-PA")
    assert a["plan"]["finish_day"] == 7.0 and a["plan"]["landed_cost"]["amount"] == "49000.00"
    assert a["score"]["score"] == pytest.approx(round(ref_score("case-primary", 7, 49000, 0.97, 0.5), 2), abs=0.005)
    assert [r["candidate"]["candidate_id"] for r in corrected][0] == "OFF-PB"
    # a retraction carries no delay/surcharge/severity: results equal the undisturbed baseline
    restored, _ = ranked_case(cat, "case-primary", [signal(cat, "SIG-RTM-CLOSURE-RETRACTION")])
    base, _ = ranked_case(cat, "case-primary")
    assert [(r["candidate"]["candidate_id"], r["score"]["score"], r["plan"]["finish_day"]) for r in restored] == \
           [(r["candidate"]["candidate_id"], r["score"]["score"], r["plan"]["finish_day"]) for r in base]


def test_secondary_rankings(cat):
    b, _ = ranked_case(cat, "case-secondary-b")
    assert [r["candidate"]["candidate_id"] for r in b] == ["OFF-SB3", "OFF-SB1"]  # MAKE preferred over backordered BUY
    a_before, _ = ranked_case(cat, "case-secondary-a")
    assert [r["candidate"]["candidate_id"] for r in a_before] == ["OFF-SA2"]
    a_after, _ = ranked_case(cat, "case-secondary-a", extra={"OFF-SA1": ("ev-tr-sa1",)})
    assert [r["candidate"]["candidate_id"] for r in a_after] == ["OFF-SA1", "OFF-SA2"]


def test_low_price_cannot_compensate_failed_or_unknown_mandatory_check(cat):
    ranked, rows = ranked_case(cat, "case-primary")
    by = {r["candidate"]["candidate_id"]: r for r in rows}
    # D and E would out-score A on preference inputs alone, but they are not eligible
    for cid in ("OFF-PD", "OFF-PE"):
        plan = by[cid]["plan"]
        otd = cat.metric(cat.offers[cid]["site_id"], "on_time_delivery_rate")["value"]
        raw = score_candidate("case-primary", plan, otd, 0.05, cat.ranking)["score"]
        assert raw > by["OFF-PA"]["score"]["score"]
        assert by[cid]["rank"] is None and by[cid] not in ranked


def test_rank_is_stable_and_ties_break_by_time_then_cost_then_id(cat):
    first, _ = ranked_case(cat, "case-primary")
    second, _ = ranked_case(cat, "case-primary")
    assert [r["candidate"]["candidate_id"] for r in first] == [r["candidate"]["candidate_id"] for r in second]

    def row(cid, days, cost):
        return {"candidate": {"candidate_id": cid}, "eligibility": "eligible", "score": {"score_unrounded": 70.0, "score": 70.0},
                "plan": {"elapsed_days": days, "landed_cost": {"amount": cost}}}

    rows = [row("C-3", 5, "100.00"), row("C-1", 5, "100.00"), row("C-2", 5, "90.00"), row("C-4", 4, "500.00")]
    assert [r["candidate"]["candidate_id"] for r in rank(rows)] == ["C-4", "C-2", "C-1", "C-3"]


def test_missing_preference_input_gives_pending_comparison(cat):
    plan, _ = plan_for(cat, "OFF-PA")
    assert score_candidate("case-primary", plan, None, 0.1, cat.ranking) is None
    assert score_candidate("case-primary", None, 0.97, 0.1, cat.ranking) is None


def test_score_breakdown_is_reproducible_from_saved_inputs(cat):
    plan, exp = plan_for(cat, "OFF-PB")
    sc = score_candidate("case-primary", plan, 0.98, exp["value"], cat.ranking)
    i = sc["inputs"]
    assert sc["score_unrounded"] == pytest.approx(ref_score("case-primary", i["elapsed_recovery_days"], float(i["landed_cost_gbp"]),
                                                            i["on_time_delivery_rate"], i["current_exposure"]))
    w = sc["weights"]
    recomposed = 100 * sum(w[k] * sc[k] for k in ("recovery_speed", "landed_cost", "historical_reliability", "current_resilience"))
    assert recomposed == pytest.approx(sc["score_unrounded"], abs=0.01)
    assert sc["thresholds"]["ranking_config_version"] == "ranking-default-v1"
