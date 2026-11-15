"""Code-side validation of extracted values and the structured-form parser (PRD FR-04)."""

from __future__ import annotations

import pytest

from domain_helpers import structured_facts
from recovery.domain.extraction import FIELD_SCHEMAS, coerce, field_key, normalise_for_compare, parse_structured_form


@pytest.mark.parametrize("type_code,raw,value,state", [
    ("partno", "rs-fn-1001", "RS-FN-1001", "valid"),
    ("partno", "RS FN 1001", "RSFN1001", "valid"),
    ("partno", "??", None, "invalid"),
    ("revision", "d", "D", "valid"),
    ("revision", "rev D", None, "invalid"),
    ("date", "2026-12-15", "2026-12-15", "valid"),
    ("date", "15/12/2026", None, "invalid"),
    ("bool", "yes", True, "valid"),
    ("bool", "unknown", None, "invalid"),
    ("bool", "maybe", None, "invalid"),
    ("str", "not provided", None, "invalid"),
    ("int", "1", 1, "valid"),
    ("decimal", "46,200.00", "46200.00", "valid"),
    ("ratio", "0.97", 0.97, "valid"),
    ("ratio", "1.4", None, "invalid"),
    ("currency", "gbp", "GBP", "valid"),
    ("currency", "XYZ", None, "invalid"),
    ("list", "D; D1", ["D", "D1"], "valid"),
    ("site", "SITE-PEN-SHF", "SITE-PEN-SHF", "valid"),
])
def test_coerce(type_code, raw, value, state):
    v, s, _ = coerce(type_code, raw)
    assert (v, s) == (value, state)


def test_missing_value_is_invalid():
    assert coerce("str", None)[1] == "invalid"


def test_structured_parse_records_line_locators(cat):
    ev = cat.evidence["ev-f1-pa"]
    parsed = parse_structured_form(ev["content_text"])
    lines = ev["content_text"].splitlines()
    raw, line_no = parsed["serial_number"]
    assert raw == "FN7731" and lines[line_no - 1].startswith("SERIAL NUMBER:")
    assert "record_type" not in parsed


def test_every_fixture_document_matches_its_schema_and_expected_facts(cat):
    for vid, ev in cat.evidence.items():
        facts = structured_facts(ev)
        schema = FIELD_SCHEMAS[ev["doc_type"]]
        assert set(facts) <= set(schema), vid
        for fld, expected in ev["expected_facts"].items():
            key = field_key(fld)
            if key not in schema:
                continue
            f = facts[key]
            if f["validation_state"] == "valid":
                assert normalise_for_compare(f["typed_value"]) == normalise_for_compare(
                    coerce(schema[key], expected)[0]), (vid, key)


def test_unusable_values_are_flagged_not_dropped(cat):
    facts = structured_facts(cat.evidence["ev-tr-pd"])
    assert facts["back_to_birth"]["validation_state"] == "invalid"
    assert facts["non_incident_statement"]["validation_state"] == "invalid"
    assert facts["back_to_birth"]["original_value"] == "unknown"


def test_content_hash_identifies_identical_content(cat):
    hashes = [ev["hash"] for ev in cat.evidence.values()]
    assert len(hashes) == len(set(hashes))  # each evidence version has distinct content
    assert cat.evidence["ev-sb-fn-0042-a"]["document_id"] == cat.evidence["ev-sb-fn-0042-b"]["document_id"]
    assert cat.evidence["ev-sb-fn-0042-b"]["supersedes_version_id"] == "ev-sb-fn-0042-a"
