"""Domain code scorers (PRD §12.1), MLflow-3 compatible.

Each scorer has the MLflow genai keyword signature (inputs, outputs, expectations) and returns a float in
[0, 1] (plain mode) or an `mlflow.entities.Feedback` with a rationale (when wrapped for MLflow). The pure
implementations (`*_impl`) return (value, rationale) so they can be unit-tested without MLflow.
"""

from __future__ import annotations

from decimal import Decimal
from typing import Any, Callable, Optional

ROUTE_ONLY_TEMPLATES = {"LOG"}  # route viability is backed by signals/relationships rather than documents


# ---------------------------------------------------------------------------------------- implementations
def mandatory_gate_correctness_impl(outputs: dict, expectations: dict) -> tuple[float, str]:
    exp = expectations.get("eligibility", {})
    got = outputs.get("eligibility", {})
    if not exp:
        return 1.0, "no eligibility labels"
    wrong = {cid: (got.get(cid), e) for cid, e in exp.items() if got.get(cid) != e}
    return (len(exp) - len(wrong)) / len(exp), ("all gates correct" if not wrong else f"mismatches (got, expected): {wrong}")


def unsupported_eligibility_impl(outputs: dict, expectations: Optional[dict] = None) -> tuple[float, str]:
    """1.0 when no candidate is eligible/accepted without every mandatory check passing on source evidence."""
    problems = []
    by_id = {c["candidate_id"]: c for c in outputs.get("candidates", [])}
    for c in by_id.values():
        if c["eligibility"] != "eligible":
            continue
        for chk in c.get("checks", []):
            if not chk.get("mandatory"):
                continue
            if chk["result"] != "pass":
                problems.append(f"{c['candidate_id']}:{chk.get('requirement_id')} is {chk['result']}")
            elif not chk.get("evidence_refs") and chk.get("template_code") not in ROUTE_ONLY_TEMPLATES:
                problems.append(f"{c['candidate_id']}:{chk.get('requirement_id')} passes without evidence")
    sel = outputs.get("selection")
    if sel and by_id.get(sel["candidate_id"], {}).get("eligibility") != "eligible":
        problems.append(f"selection of non-eligible candidate {sel['candidate_id']}")
    return (0.0 if problems else 1.0), ("no unsupported eligibility" if not problems else "; ".join(problems[:10]))


def citation_version_integrity_impl(outputs: dict, expectations: Optional[dict] = None) -> tuple[float, str]:
    """Share of cited evidence versions that exist in the snapshot and are not superseded."""
    known = set(outputs.get("known_versions", []))
    superseded = set(outputs.get("superseded_versions", []))
    cited = [ref for chk in outputs.get("checks", []) for ref in chk.get("evidence_refs", [])]
    if not cited:
        return 1.0, "no citations"
    bad = [r for r in cited if r not in known or r in superseded]
    return (len(cited) - len(bad)) / len(cited), ("all citations resolve to current versions" if not bad else f"bad citations: {sorted(set(bad))[:10]}")


def ranking_schedule_correctness_impl(outputs: dict, expectations: dict) -> tuple[float, str]:
    """Average of exact eligible order match and per-candidate schedule (finish day, landed cost) matches."""
    parts, notes = [], []
    if "order" in expectations:
        ok = outputs.get("order") == expectations["order"]
        parts.append(1.0 if ok else 0.0)
        if not ok:
            notes.append(f"order {outputs.get('order')} != {expectations['order']}")
    for cid, exp in expectations.get("schedules", {}).items():
        got = outputs.get("schedules", {}).get(cid, {})
        ok = abs(float(got.get("finish_day", -1)) - float(exp["finish_day"])) < 1e-6 and \
            Decimal(str(got.get("landed_cost", "-1"))) == Decimal(str(exp["landed_cost"]))
        parts.append(1.0 if ok else 0.0)
        if not ok:
            notes.append(f"{cid}: got {got}, expected {exp}")
    for cid, exp in expectations.get("scores", {}).items():
        got = outputs.get("scores", {}).get(cid)
        ok = got is not None and abs(float(got) - float(exp)) <= 0.005
        parts.append(1.0 if ok else 0.0)
        if not ok:
            notes.append(f"{cid}: score {got} != {exp}")
    if not parts:
        return 1.0, "nothing to compare"
    return sum(parts) / len(parts), ("ranking and schedule match" if not notes else "; ".join(notes))


def change_impact_correctness_impl(outputs: dict, expectations: dict) -> tuple[float, str]:
    """Exact-set match of impacted offers and cases (no spurious or missed impact)."""
    exp_o, exp_c = set(expectations.get("offers", [])), set(expectations.get("cases", []))
    got_o, got_c = set(outputs.get("offers", [])), set(outputs.get("cases", []))
    ok_o, ok_c = got_o == exp_o, got_c == exp_c
    score = (int(ok_o) + int(ok_c)) / 2
    return score, ("impact scope exact" if score == 1 else f"offers got {sorted(got_o)} expected {sorted(exp_o)}; cases got {sorted(got_c)} expected {sorted(exp_c)}")


def duplicate_side_effects_impl(outputs: dict, expectations: Optional[dict] = None) -> tuple[float, str]:
    """1.0 when receipts contain no duplicated operation: one receipt per (package, version, approved hash) and per idempotency key."""
    receipts = outputs.get("receipts", [])
    seen_ops, seen_keys, dups = {}, {}, []
    for r in receipts:
        op = r.get("operation_key") or f"{r.get('package_id')}:{r.get('package_version')}:{r.get('package_hash')}"
        if op in seen_ops and seen_ops[op] != r.get("receipt_id"):
            dups.append(f"operation {op}")
        seen_ops.setdefault(op, r.get("receipt_id"))
        k = r.get("idempotency_key")
        if k and k in seen_keys and seen_keys[k] != r.get("receipt_id"):
            dups.append(f"idempotency key {k}")
        if k:
            seen_keys.setdefault(k, r.get("receipt_id"))
    return (0.0 if dups else 1.0), ("no duplicate side effects" if not dups else f"duplicates: {dups}")


def form_field_accuracy_impl(outputs: dict, expectations: dict) -> tuple[float, str]:
    """Share of expected form fields whose populated value matches (case/whitespace-insensitive)."""
    exp = expectations.get("fields", {})
    if not exp:
        return 1.0, "no field labels"
    got = {f["field_id"]: f.get("value") for f in outputs.get("fields", [])}
    norm = lambda v: " ".join(str(v).split()).upper() if v is not None else None  # noqa: E731
    wrong = {k: (got.get(k), v) for k, v in exp.items() if norm(got.get(k)) != norm(v)}
    return (len(exp) - len(wrong)) / len(exp), ("all fields match" if not wrong else f"mismatches (got, expected): {wrong}")


IMPLS: dict[str, Callable[..., tuple[float, str]]] = {
    "mandatory_gate_correctness": mandatory_gate_correctness_impl,
    "unsupported_eligibility": unsupported_eligibility_impl,
    "citation_version_integrity": citation_version_integrity_impl,
    "ranking_schedule_correctness": ranking_schedule_correctness_impl,
    "change_impact_correctness": change_impact_correctness_impl,
    "duplicate_side_effects": duplicate_side_effects_impl,
    "form_field_accuracy": form_field_accuracy_impl,
}


# ---------------------------------------------------------------------------------------- MLflow wrappers
def _make(name: str, impl: Callable[..., tuple[float, str]]):  # noqa: ANN202
    def plain(inputs: Any = None, outputs: Optional[dict] = None, expectations: Optional[dict] = None, **_: Any) -> float:
        return impl(outputs or {}, expectations or {})[0]

    plain.__name__ = name
    return plain


def mlflow_scorers() -> list[Any]:
    """MLflow genai scorers (Feedback with rationale). Raises ImportError when MLflow genai is unavailable."""
    from mlflow.entities import Feedback
    from mlflow.genai.scorers import scorer

    out = []
    for name, impl in IMPLS.items():
        def fn(inputs=None, outputs=None, expectations=None, _impl=impl):  # noqa: ANN001, ANN202
            value, rationale = _impl(outputs or {}, expectations or {})
            return Feedback(value=value, rationale=rationale)

        out.append(scorer(name=name)(fn))
    return out


mandatory_gate_correctness = _make("mandatory_gate_correctness", mandatory_gate_correctness_impl)
unsupported_eligibility = _make("unsupported_eligibility", unsupported_eligibility_impl)
citation_version_integrity = _make("citation_version_integrity", citation_version_integrity_impl)
ranking_schedule_correctness = _make("ranking_schedule_correctness", ranking_schedule_correctness_impl)
change_impact_correctness = _make("change_impact_correctness", change_impact_correctness_impl)
duplicate_side_effects = _make("duplicate_side_effects", duplicate_side_effects_impl)
form_field_accuracy = _make("form_field_accuracy", form_field_accuracy_impl)
