"""Domain evaluation for the seeded fixture (PRD §12.1).

Runs the deterministic domain directly (no server) over tests/evaluations/expected_seed_v1.json, scores the
outputs with the code scorers in scorers.py and, when MLflow tracking is configured (MLFLOW_TRACKING_URI and
MLFLOW_EXPERIMENT_ID in the environment or the repo's gitignored .env), logs an MLflow run with metrics.

Usage (from backend/):
    uv run python ../tests/evaluations/run_eval.py            # evaluate + log to MLflow if configured
    uv run python ../tests/evaluations/run_eval.py --no-mlflow
    uv run python ../tests/evaluations/run_eval.py --out /tmp/eval.json
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import time
from datetime import timedelta
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent))  # tests/ → conftest helpers
sys.path.insert(0, str(HERE.parents[1] / "backend"))
sys.path.insert(0, str(HERE))
os.environ.setdefault("MLFLOW_DISABLE_AGENT_HINT", "1")

from domain_helpers import evaluate_candidate, scenario_start, structured_facts  # noqa: E402
from recovery.config import settings  # noqa: E402  (loads .env)
from recovery.domain.catalog import load_catalog  # noqa: E402
from recovery.domain.impact import Graph, scope_entities  # noqa: E402
from recovery.domain.ranking import rank, score_candidate  # noqa: E402
from recovery.domain.scheduler import build_plan, exposure_for  # noqa: E402
import scorers as S  # noqa: E402

ROW_SCORERS = {
    "eligibility": ["mandatory_gate_correctness", "unsupported_eligibility", "citation_version_integrity"],
    "ranking": ["ranking_schedule_correctness", "unsupported_eligibility", "citation_version_integrity"],
    "impact": ["change_impact_correctness"],
    "form_fields": ["form_field_accuracy"],
}


def _now(cat, offset_days: float = 0):
    return scenario_start(cat) + timedelta(hours=1, days=offset_days)


def _candidates(cat, ids, inputs):
    sigs = [cat.signals[s] for s in inputs.get("signals", [])]
    now = _now(cat, inputs.get("clock_offset_days", 0))
    replace = inputs.get("replace_evidence") or {}
    extra = inputs.get("extra_evidence") or {}
    out, superseded = [], set(replace)
    for cid in ids:
        elig, feasible, checks = evaluate_candidate(cat, cid, now=now, signals=sigs, extra_version_ids=tuple(extra.get(cid, ())), replace=replace)
        out.append({"candidate_id": cid, "eligibility": elig, "feasible": feasible, "checks": checks})
    return out, superseded, sigs


def eval_eligibility(cat, row):
    ids = sorted(row["expectations"]["eligibility"])
    cands, superseded, _ = _candidates(cat, ids, row["inputs"])
    return {"eligibility": {c["candidate_id"]: c["eligibility"] for c in cands},
            "feasible": {c["candidate_id"]: c["feasible"] for c in cands},
            "candidates": cands, "checks": [chk for c in cands for chk in c["checks"]],
            "known_versions": sorted(cat.evidence), "superseded_versions": sorted(superseded)}


def eval_ranking(cat, row):
    case_id = row["case_id"]
    ids = sorted(cid for cid, o in cat.offers.items() if o["case_id"] == case_id)
    cands, superseded, sigs = _candidates(cat, ids, row["inputs"])
    rows = []
    for c in cands:
        o = cat.offers[c["candidate_id"]]
        site, route = cat.sites[o["site_id"]], cat.routes[o["logistics_route_id"]]
        plan = build_plan(o, cat.plans[o["candidate_id"]], route, site, sigs, cat.fx)
        exp = exposure_for(route, site, sigs)
        otd = cat.metric(site["site_id"], "on_time_delivery_rate")["value"]
        sc = score_candidate(case_id, plan, otd, exp["value"], cat.ranking) if c["eligibility"] == "eligible" else None
        rows.append({"candidate": o, "eligibility": c["eligibility"], "score": sc, "plan": plan})
    ranked = rank(rows)
    return {"order": [r["candidate"]["candidate_id"] for r in ranked],
            "scores": {r["candidate"]["candidate_id"]: r["score"]["score"] for r in ranked},
            "schedules": {r["candidate"]["candidate_id"]: {"finish_day": r["plan"]["finish_day"], "landed_cost": r["plan"]["landed_cost"]["amount"]} for r in rows},
            "candidates": cands, "checks": [chk for c in cands for chk in c["checks"]],
            "known_versions": sorted(cat.evidence), "superseded_versions": sorted(superseded)}


def eval_impact(cat, row):
    g = Graph(cat.relationships)
    if "signal" in row["inputs"]:
        ids, hint = scope_entities(cat.signals[row["inputs"]["signal"]], cat.sites)
    else:
        ids, hint = [row["inputs"]["evidence"]], {row["inputs"]["evidence"]: "evidence"}
    res = g.impact(ids, hint)
    return {"offers": res["offers"], "cases": res["cases"], "paths": res["paths"]}


def eval_form_fields(cat, row):
    """Resolve the template's fact:/const: sources from validated extracted facts of the candidate's evidence.

    Exercises the template field mapping + extraction; DocumentService output can be scored with the same scorer
    in integration runs."""
    tpl = cat.templates[row["inputs"]["template_id"]]
    offer = cat.offers[row["inputs"]["candidate_id"]]
    facts: dict[str, dict] = {}
    for vid in offer["evidence_ids"]:
        ev = cat.evidence[vid]
        for fld, f in structured_facts(ev).items():
            if f["validation_state"] == "valid":
                facts.setdefault(f"{ev['doc_type']}.{fld}", f)
    fields = []
    for fd in tpl["fields"]:
        src = fd["source"]
        value = None
        if src.startswith("fact:"):
            f = facts.get(src[5:])
            value = f["typed_value"] if f else None
        elif src.startswith("const:"):
            value = src[6:]
        fields.append({"field_id": fd["field_id"], "value": value})
    return {"fields": fields}


EVALUATORS = {"eligibility": eval_eligibility, "ranking": eval_ranking, "impact": eval_impact, "form_fields": eval_form_fields}


def run(log_mlflow: bool = True, out_path: str | None = None) -> dict:
    cat = load_catalog()
    spec = json.loads((HERE / "expected_seed_v1.json").read_text())
    started = time.time()
    results, data = [], []
    for row in spec["rows"]:
        outputs = EVALUATORS[row["kind"]](cat, row)
        scores = {}
        for name in ROW_SCORERS[row["kind"]]:
            value, rationale = S.IMPLS[name](outputs, row["expectations"])
            scores[name] = {"value": value, "rationale": rationale}
        results.append({"id": row["id"], "kind": row["kind"], "held_out": row.get("held_out", False), "scores": scores})
        data.append({"inputs": {"row_id": row["id"], "kind": row["kind"], **row["inputs"]},
                     "outputs": outputs,
                     "expectations": row["expectations"]})
    latency = time.time() - started
    metrics: dict[str, float] = {}
    for name in S.IMPLS:
        vals = [r["scores"][name]["value"] for r in results if name in r["scores"]]
        if vals:
            metrics[f"{name}/mean"] = sum(vals) / len(vals)
    for split in (False, True):
        vals = [v["value"] for r in results if r["held_out"] == split for v in r["scores"].values()]
        if vals:
            metrics[f"{'held_out' if split else 'tuning'}/mean_score"] = sum(vals) / len(vals)
    failed = [{"id": r["id"], "scorer": n, "rationale": s["rationale"]} for r in results for n, s in r["scores"].items() if s["value"] < 1.0]
    summary = {
        "dataset_version": spec["dataset_version"], "fixture_version": spec["fixture_version"], "rows": len(results),
        "held_out_rows": sum(1 for r in results if r["held_out"]), "requirements_version": cat.requirements_version,
        "ranking_config_version": cat.ranking["ranking_config_version"], "applicability_version": cat.applicability["catalogue_version"],
        "templates_version": cat.templates_version, "model": "none (deterministic domain; no LLM in these scorers)",
        "latency_s": round(latency, 3), "metrics": metrics, "failed": failed, "duplicate_side_effects": "not evaluated here (needs a service run with receipts)",
        "rows_detail": results, "mlflow": None,
    }
    if log_mlflow and settings.mlflow_tracking_uri and settings.mlflow_experiment_id:
        summary["mlflow"] = _log_mlflow(summary, data)
    if out_path:
        Path(out_path).write_text(json.dumps(summary, indent=2, default=str))
    return summary


def _log_mlflow(summary: dict, data: list[dict]) -> dict:
    try:
        import mlflow

        mlflow.set_tracking_uri(settings.mlflow_tracking_uri)
        mlflow.set_experiment(experiment_id=settings.mlflow_experiment_id)
        with mlflow.start_run(run_name=f"domain-eval-{summary['dataset_version']}") as run:
            mlflow.log_params({k: summary[k] for k in ("dataset_version", "fixture_version", "rows", "held_out_rows", "requirements_version",
                                                         "ranking_config_version", "applicability_version", "templates_version", "model")})
            mlflow.log_metrics({k.replace("/", "_"): v for k, v in summary["metrics"].items()})
            mlflow.log_metric("latency_s", summary["latency_s"])
            mlflow.log_dict({k: v for k, v in summary.items() if k != "mlflow"}, "domain_eval_summary.json")
            mlflow.set_tags({"project": "ReSource", "eval_type": "domain_code_scorers", "data_origin": "synthetic_demo"})
            genai = None
            try:  # per-row assessments through MLflow GenAI evaluation with the same code scorers
                res = mlflow.genai.evaluate(data=data, scorers=S.mlflow_scorers())
                genai = {"run_id": getattr(res, "run_id", None), "metrics": {k: v for k, v in (getattr(res, "metrics", {}) or {}).items()}}
            except Exception as exc:  # noqa: BLE001
                genai = {"error": f"{type(exc).__name__}: {str(exc)[:300]}"}
            return {"run_id": run.info.run_id, "experiment_id": settings.mlflow_experiment_id, "genai_evaluate": genai}
    except Exception as exc:  # noqa: BLE001
        return {"error": f"{type(exc).__name__}: {str(exc)[:300]}"}


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--no-mlflow", action="store_true")
    ap.add_argument("--out")
    args = ap.parse_args()
    s = run(log_mlflow=not args.no_mlflow, out_path=args.out)
    print(f"dataset {s['dataset_version']} ({s['rows']} rows, {s['held_out_rows']} held out) in {s['latency_s']}s")
    for k, v in sorted(s["metrics"].items()):
        print(f"  {k:45s} {v:.3f}")
    for f in s["failed"]:
        print(f"  FAIL {f['id']} {f['scorer']}: {f['rationale']}")
    print("mlflow:", json.dumps(s["mlflow"]))
    return 0 if not s["failed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
