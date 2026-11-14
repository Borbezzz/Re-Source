"""Recovery scheduling (PRD FR-09): deterministic dependency/critical-path scheduling, with OR-Tools
CP-SAT when capacity windows constrain a step. Code computes; the model only explains.
"""

from __future__ import annotations

from decimal import ROUND_HALF_UP, Decimal
from typing import Any, Optional

SCALE = 10  # tenths of a day for the integer CP-SAT model


def _q(v: Decimal) -> Decimal:
    return v.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)


def convert(amount: str, currency: str, fx: dict) -> tuple[Decimal, Optional[str]]:
    base = fx["base"]
    if currency == base:
        return _q(Decimal(amount)), None
    rate = Decimal(fx["rates"][currency])
    return _q(Decimal(amount) * rate), fx["fx_version"]


def signal_matches_route(signal: dict, route: dict, site: dict) -> bool:
    scope = signal.get("scope", {})
    if set(scope.get("geo_ids", [])) & set(route.get("passes_through", [])):
        return True
    if route["route_id"] in scope.get("route_ids", []):
        return True
    if site["site_id"] in scope.get("site_ids", []) or site["geography"].get("geo_id") in scope.get("geo_ids", []):
        return True
    if site["supplier_id"] in scope.get("entity_ids", []):
        return True
    if site["geography"].get("country") in scope.get("origin_countries", []):
        return True
    return False


def _cpm(steps: list[dict]) -> dict[str, tuple[float, float]]:
    times: dict[str, tuple[float, float]] = {}
    remaining = {s["step_id"]: s for s in steps}
    while remaining:
        progressed = False
        for sid, s in list(remaining.items()):
            if all(d in times for d in s["depends_on"]):
                start = max([times[d][1] for d in s["depends_on"]], default=0.0)
                times[sid] = (start, start + s["duration"]["value"])
                del remaining[sid]
                progressed = True
        if not progressed:
            raise ValueError(f"dependency cycle in plan: {sorted(remaining)}")
    return times


def _cp_sat(steps: list[dict], slot: dict) -> tuple[dict[str, tuple[float, float]], str, dict]:
    try:
        from ortools.sat.python import cp_model
    except Exception as exc:  # pragma: no cover - ortools is a declared dependency
        return {}, f"UNAVAILABLE ({exc})", {}
    model = cp_model.CpModel()
    horizon = int(sum(s["duration"]["value"] for s in steps) * SCALE + max(w[1] for w in slot["windows"]) * SCALE + 10)
    start, end = {}, {}
    for s in steps:
        d = int(round(s["duration"]["value"] * SCALE))
        start[s["step_id"]] = model.NewIntVar(0, horizon, f"s_{s['step_id']}")
        end[s["step_id"]] = model.NewIntVar(0, horizon, f"e_{s['step_id']}")
        model.Add(end[s["step_id"]] == start[s["step_id"]] + d)
    for s in steps:
        for dep in s["depends_on"]:
            model.Add(start[s["step_id"]] >= end[dep])
    sid = slot["step_id"]
    choices = []
    for i, (lo, hi) in enumerate(slot["windows"]):
        b = model.NewBoolVar(f"w{i}")
        model.Add(start[sid] >= int(lo * SCALE)).OnlyEnforceIf(b)
        model.Add(end[sid] <= int(hi * SCALE)).OnlyEnforceIf(b)
        choices.append(b)
    model.AddExactlyOne(choices)
    makespan = model.NewIntVar(0, horizon, "makespan")
    model.AddMaxEquality(makespan, list(end.values()))
    model.Minimize(makespan)
    solver = cp_model.CpSolver()
    solver.parameters.max_time_in_seconds = 5.0
    solver.parameters.num_workers = 1
    status = solver.Solve(model)
    name = solver.StatusName(status)
    if status not in (cp_model.OPTIMAL, cp_model.FEASIBLE):
        return {}, name, {"objective": None}
    times = {k: (solver.Value(start[k]) / SCALE, solver.Value(end[k]) / SCALE) for k in start}
    chosen = next(i for i, b in enumerate(choices) if solver.Value(b))
    return times, name, {
        "objective": "minimise elapsed recovery time (makespan)",
        "objective_value_days": solver.Value(makespan) / SCALE,
        "constraints": [f"precedence between {sum(len(s['depends_on']) for s in steps)} step pairs",
                        f"step '{sid}' must fit one capacity window {slot['windows']}"],
        "chosen_window": slot["windows"][chosen],
    }


def build_plan(offer: dict, plan_fixture: dict, route: dict, site: dict, active_signals: list[dict], fx: dict) -> dict:
    steps = [dict(s, depends_on=list(s["depends_on"]), duration=dict(s["duration"])) for s in plan_fixture["steps"]]
    adjusted: dict[str, list[str]] = {}
    surcharges: list[dict] = []
    matched = [s for s in active_signals if signal_matches_route(s, route, site)]
    for sig in matched:
        delay = float(sig["assertion"].get("transport_delay_days", 0) or 0)
        for st in steps:
            if st["kind"] == "transport" and delay:
                st["duration"]["value"] = round(st["duration"]["value"] + delay, 2)
                adjusted.setdefault(st["step_id"], []).append(sig["signal_id"])
        sur = sig["assertion"].get("surcharge")
        if sur and Decimal(sur["amount"]) > 0:
            surcharges.append({"label": f"Disruption surcharge — {sig['title']}", "amount": sur["amount"], "currency": sur["currency"],
                               "source": sig["signal_id"]})

    slot = plan_fixture.get("capacity_slots")
    solver, status, detail = "dependency_cpm", "OPTIMAL", {}
    if slot:
        times, status, detail = _cp_sat(steps, slot)
        solver = "cp_sat"
        if not times:
            times = _cpm(steps)
            detail["fallback"] = "CP-SAT infeasible/unavailable; dependency CPM used"
    else:
        times = _cpm(steps)
    finish = max(t[1] for t in times.values())

    # critical path: walk back from the finishing step through zero-slack predecessors
    by_id = {s["step_id"]: s for s in steps}
    end_step = max(times, key=lambda k: times[k][1])
    critical = [end_step]
    cur = end_step
    while by_id[cur]["depends_on"]:
        preds = by_id[cur]["depends_on"]
        cur = max(preds, key=lambda p: times[p][1])
        critical.append(cur)
    critical.reverse()

    out_steps = []
    for s in steps:
        st, en = times[s["step_id"]]
        out_steps.append({**s, "start_day": round(st, 2), "finish_day": round(en, 2), "on_critical_path": s["step_id"] in critical,
                          "adjusted_by": adjusted.get(s["step_id"], [])})

    cost_lines = []
    unit = offer["price"]
    total_unit = str(Decimal(unit["amount"]) * offer.get("quantity", 1))
    conv, fxv = convert(total_unit, unit["currency"], fx)
    cost_lines.append({"label": f"Part price × {offer.get('quantity', 1)}", "original": {"amount": total_unit, "currency": unit["currency"]},
                       "converted": {"amount": str(conv), "currency": fx["base"]}, "fx_version": fxv, "source": offer["quote_version"]})
    freight = route["freight"]
    c, fxv = convert(freight["amount"], freight["currency"], fx)
    cost_lines.append({"label": f"Freight — {route['label']}", "original": freight, "converted": {"amount": str(c), "currency": fx["base"]},
                       "fx_version": fxv, "source": route["route_id"]})
    for extra in plan_fixture.get("extra_costs", []):
        c, fxv = convert(extra["amount"], extra["currency"], fx)
        cost_lines.append({"label": extra["label"], "original": {"amount": extra["amount"], "currency": extra["currency"]},
                           "converted": {"amount": str(c), "currency": fx["base"]}, "fx_version": fxv, "source": plan_fixture["plan_id"]})
    for sur in surcharges:
        c, fxv = convert(sur["amount"], sur["currency"], fx)
        cost_lines.append({"label": sur["label"], "original": {"amount": sur["amount"], "currency": sur["currency"]},
                           "converted": {"amount": str(c), "currency": fx["base"]}, "fx_version": fxv, "source": sur["source"]})
    landed = _q(sum(Decimal(cl["converted"]["amount"]) for cl in cost_lines))
    labour = round(sum(s["duration"]["value"] for s in steps), 2)
    assumptions = [s["assumption"] for s in steps if s.get("assumption")]
    assumptions.append("Durations are scenario fixture estimates (synthetic), not measured forecasts.")
    if matched:
        assumptions.append("Active disruption signals adjust transport duration and add surcharges: " + ", ".join(s["signal_id"] for s in matched))
    return {
        "plan_id": plan_fixture["plan_id"],
        "candidate_id": offer["candidate_id"],
        "steps": out_steps,
        "assumptions": assumptions,
        "finish_day": round(finish, 2),
        "elapsed_days": round(finish, 2),
        "labour_days": labour,
        "critical_path": critical,
        "cost_breakdown": cost_lines,
        "landed_cost": {"amount": str(landed), "currency": fx["base"]},
        "solver": solver,
        "solver_status": status,
        "solver_detail": detail,
        "input_versions": {"plan": plan_fixture["plan_id"], "route": route["route_id"], "fx": fx["fx_version"],
                           **{f"signal:{s['source_event_id']}": str(s["version"]) for s in matched}},
        "data_origin": "synthetic_demo",
    }


def exposure_for(route: dict, site: dict, active_signals: list[dict]) -> dict[str, Any]:
    matched = [s for s in active_signals if signal_matches_route(s, route, site)]
    base = float(route.get("baseline_exposure", 0.0))
    worst = max([float(s["assertion"].get("severity", 0)) for s in matched], default=0.0)
    value = max(base, worst)
    return {
        "value": round(value, 4),
        "baseline": base,
        "signals": [{"signal_id": s["signal_id"], "title": s["title"], "severity": s["assertion"].get("severity"), "status": s["status"]} for s in matched],
        "label": "Current exposure (0 = none, 1 = severe) from route baseline and active disruption signals",
    }
