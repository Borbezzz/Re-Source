"""The code scorers must detect the failures they exist for (not just return 1.0)."""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import scorers as S  # noqa: E402


def test_mandatory_gate_correctness_detects_mismatch():
    v, why = S.mandatory_gate_correctness_impl({"eligibility": {"A": "eligible", "B": "eligible"}}, {"eligibility": {"A": "eligible", "B": "pending"}})
    assert v == 0.5 and "B" in why


def test_unsupported_eligibility_flags_unknown_mandatory_and_bad_selection():
    outputs = {"candidates": [
        {"candidate_id": "A", "eligibility": "eligible", "checks": [{"mandatory": True, "result": "unknown", "requirement_id": "R1", "evidence_refs": ["e"]}]},
        {"candidate_id": "B", "eligibility": "pending", "checks": []}],
        "selection": {"candidate_id": "B"}}
    v, why = S.unsupported_eligibility_impl(outputs)
    assert v == 0.0 and "R1" in why and "selection" in why
    ok = {"candidates": [{"candidate_id": "A", "eligibility": "eligible",
                          "checks": [{"mandatory": True, "result": "pass", "evidence_refs": [], "template_code": "LOG"}]}]}
    assert S.unsupported_eligibility_impl(ok)[0] == 1.0
    no_ev = {"candidates": [{"candidate_id": "A", "eligibility": "eligible",
                             "checks": [{"mandatory": True, "result": "pass", "evidence_refs": [], "template_code": "REL", "requirement_id": "R2"}]}]}
    assert S.unsupported_eligibility_impl(no_ev)[0] == 0.0


def test_citation_integrity_rejects_superseded_and_unknown_versions():
    outputs = {"checks": [{"evidence_refs": ["ev-a", "ev-old", "ev-ghost"]}], "known_versions": ["ev-a", "ev-old"], "superseded_versions": ["ev-old"]}
    v, why = S.citation_version_integrity_impl(outputs)
    assert abs(v - 1 / 3) < 1e-9 and "ev-ghost" in why and "ev-old" in why


def test_ranking_schedule_correctness_partial_credit():
    exp = {"order": ["A", "B"], "schedules": {"A": {"finish_day": 4.0, "landed_cost": "48000.00"}}, "scores": {"A": 85.79}}
    good = {"order": ["A", "B"], "schedules": {"A": {"finish_day": 4.0, "landed_cost": "48000.00"}}, "scores": {"A": 85.786}}
    assert S.ranking_schedule_correctness_impl(good, exp)[0] == 1.0
    bad = {"order": ["B", "A"], "schedules": {"A": {"finish_day": 11.0, "landed_cost": "50500.00"}}, "scores": {"A": 66.91}}
    assert S.ranking_schedule_correctness_impl(bad, exp)[0] == 0.0


def test_change_impact_detects_spurious_case():
    v, _ = S.change_impact_correctness_impl({"offers": ["OFF-PA"], "cases": ["case-primary", "case-secondary-a"]},
                                            {"offers": ["OFF-PA"], "cases": ["case-primary"]})
    assert v == 0.5


def test_duplicate_side_effects():
    one = [{"receipt_id": "r1", "operation_key": "pkg:1:h", "idempotency_key": "k1"},
           {"receipt_id": "r1", "operation_key": "pkg:1:h", "idempotency_key": "k1"}]  # replayed response, same receipt
    assert S.duplicate_side_effects_impl({"receipts": one})[0] == 1.0
    dup = [{"receipt_id": "r1", "operation_key": "pkg:1:h", "idempotency_key": "k1"},
           {"receipt_id": "r2", "operation_key": "pkg:1:h", "idempotency_key": "k2"}]
    assert S.duplicate_side_effects_impl({"receipts": dup})[0] == 0.0


def test_form_field_accuracy():
    v, why = S.form_field_accuracy_impl({"fields": [{"field_id": "b8", "value": "rs-fn-1001"}, {"field_id": "b10", "value": "X"}]},
                                        {"fields": {"b8": "RS-FN-1001", "b10": "FN8102"}})
    assert v == 0.5 and "b10" in why


def test_plain_wrappers_have_mlflow_keyword_signature():
    assert S.form_field_accuracy(outputs={"fields": []}, expectations={"fields": {"x": 1}}) == 0.0
    assert S.duplicate_side_effects(inputs={}, outputs={"receipts": []}) == 1.0
