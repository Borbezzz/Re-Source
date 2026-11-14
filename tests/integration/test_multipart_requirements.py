"""Multi-component documents must not leak one part's fields into another draft."""

import pytest

from recovery.domain.errors import DomainError

DOCUMENT = """Assembly specification
COMPONENT_ID: component-primary
PART NUMBER: RS-FN-1001
REVISION: D
MATERIAL: Alloy A
COMPONENT_ID: component-secondary-a
PART NUMBER: RS-NGV-2040
REVISION: B
MATERIAL: Alloy B
"""


def drafts_for(svc, text, components):
    svc.scenario.create_run()
    upload = svc.intake.upload(text.encode(), "assembly-spec.txt", "blueprint")
    drafts = [svc.intake.start_part_requirements(upload["upload_id"], component) for component in components]
    assert svc.intake.wait_idle(30)
    return [svc.intake.get_draft(draft["draft_id"]) for draft in drafts]


def test_explicit_component_sections_keep_values_and_original_source_lines(svc):
    first, second = drafts_for(svc, DOCUMENT, ["component-primary", "component-secondary-a"])
    a = {field["name"]: field for field in first["fields"]}
    b = {field["name"]: field for field in second["fields"]}
    assert a["part_number"]["value"] == "RS-FN-1001"
    assert a["material"]["value"] == "Alloy A"
    assert a["part_number"]["source_ref"]["line"] == 3
    assert b["part_number"]["value"] == "RS-NGV-2040"
    assert b["material"]["value"] == "Alloy B"
    assert b["part_number"]["source_ref"]["line"] == 7
    assert "RS-NGV-2040" in b["part_number"]["source_ref"]["excerpt"]


@pytest.mark.parametrize("text,component", [
    (DOCUMENT, "component-secondary-b"),
    ("COMPONENT_ID: component-primary\nPART NUMBER: RS-FN-1001\nCOMPONENT_ID: component-primary\nPART NUMBER: RS-FN-1002\n", "component-primary"),
    ("PART NUMBER: RS-FN-1001\nREVISION: D\nPART NUMBER: RS-NGV-2040\nREVISION: B\n", "component-primary"),
    ("COMPONENT_ID: component-primary\nPART NUMBER: RS-FN-1001\nPART NUMBER: RS-NGV-2040\n", "component-primary"),
])
def test_ambiguous_document_fields_stay_unknown(svc, text, component):
    draft = drafts_for(svc, text, [component])[0]
    assert draft["status"] == "needs_review"
    assert "manual review" in draft["extraction"]["note"]
    assert all(field["value"] is None and field["validation_state"] == "unknown" for field in draft["fields"])
    assert all(field["source_ref"] is None for field in draft["fields"])


def test_component_bound_upload_cannot_be_used_for_another_part(svc):
    svc.scenario.create_run()
    upload = svc.intake.upload(b"PART NUMBER: RS-FN-1001\nREVISION: D\n", "part.txt", "part_requirements",
                               component_id="component-primary")
    with pytest.raises(DomainError) as error:
        svc.intake.start_part_requirements(upload["upload_id"], "component-secondary-a")
    assert error.value.status == 422
