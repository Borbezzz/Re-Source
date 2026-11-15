"""Transparent preference ranking (PRD FR-08). Only eligible offers are ranked; mandatory gates are
never compensated by price. Ties: lower recovery time, then lower landed cost, then candidate ID."""

from __future__ import annotations

from decimal import Decimal
from typing import Any, Optional


def _norm(value: float, best: float, worst: float) -> float:
    if best == worst:
        return 1.0
    x = (worst - value) / (worst - best)
    return max(0.0, min(1.0, x))


def score_candidate(case_id: str, plan: dict, otd: Optional[float], exposure: float, config: dict) -> Optional[dict]:
    w = config["weights"]
    n = config["normalisation"]
    if plan is None or otd is None:
        return None  # pending comparison: missing required preference inputs
    days = float(plan["elapsed_days"])
    cost = float(Decimal(plan["landed_cost"]["amount"]))
    cost_cfg = n["landed_cost"]["per_case"].get(case_id, n["landed_cost"]["default"])
    speed = _norm(days, n["recovery_speed"]["best"], n["recovery_speed"]["worst"])
    cost_term = _norm(cost, cost_cfg["best"], cost_cfg["worst"])
    rel = _norm(otd, n["historical_reliability"]["best"], n["historical_reliability"]["worst"])
    resil = max(0.0, min(1.0, 1.0 - exposure))
    raw = 100 * (w["recovery_speed"] * speed + w["landed_cost"] * cost_term + w["historical_reliability"] * rel + w["current_resilience"] * resil)
    d = config.get("rounding", {}).get("component_decimals", 4)
    return {
        "recovery_speed": round(speed, d),
        "landed_cost": round(cost_term, d),
        "historical_reliability": round(rel, d),
        "current_resilience": round(resil, d),
        "weights": dict(w),
        "inputs": {"elapsed_recovery_days": days, "landed_cost_gbp": f"{cost:.2f}", "on_time_delivery_rate": otd, "current_exposure": exposure},
        "thresholds": {"recovery_speed_days": [n["recovery_speed"]["best"], n["recovery_speed"]["worst"]],
                       "landed_cost_gbp": [cost_cfg["best"], cost_cfg["worst"]],
                       "on_time_delivery_rate": [n["historical_reliability"]["best"], n["historical_reliability"]["worst"]],
                       "ranking_config_version": config["ranking_config_version"]},
        "score": round(raw, config.get("rounding", {}).get("score_decimals", 2)),
        "score_unrounded": raw,
    }


def rank(candidates: list[dict]) -> list[dict]:
    """candidates: dicts with keys candidate_id, eligibility, score (dict|None), plan. Mutates rank."""
    eligible = [c for c in candidates if c["eligibility"] == "eligible" and c.get("score")]

    def key(c: dict) -> tuple:
        return (-c["score"]["score_unrounded"], float(c["plan"]["elapsed_days"]), float(c["plan"]["landed_cost"]["amount"]), c["candidate"]["candidate_id"])

    eligible.sort(key=key)
    for i, c in enumerate(eligible, start=1):
        c["rank"] = i
    for c in candidates:
        if c not in eligible:
            c["rank"] = None
    return eligible


def strip_internal(score: Optional[dict]) -> Optional[dict]:
    if score is None:
        return None
    return {k: v for k, v in score.items() if k != "score_unrounded"}


def evidence_coverage(checks: list[dict]) -> dict[str, Any]:
    mandatory = [c for c in checks if c["mandatory"]]
    passed = sum(1 for c in mandatory if c["result"] == "pass")
    with_evidence = sum(1 for c in mandatory if c["evidence_refs"])
    return {
        "mandatory_checks": len(mandatory),
        "passed": passed,
        "unknown": sum(1 for c in mandatory if c["result"] == "unknown"),
        "failed": sum(1 for c in mandatory if c["result"] == "fail"),
        "with_source_evidence": with_evidence,
        "label": "Evidence coverage: share of mandatory checks backed by validated source evidence (not a likelihood of physical suitability)",
        "ratio": round(with_evidence / len(mandatory), 3) if mandatory else 0.0,
    }
