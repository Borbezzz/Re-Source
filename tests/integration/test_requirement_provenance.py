"""Reviewed engineering fields retain their sources and unknowns without asserting compatibility."""

from recovery.services.intake import _dimensional_unit

DOCUMENT = """COMPONENT_ID: component-primary
PART NUMBER: RS-FN-1001
REVISION: D
MATERIAL: Inconel 625
KEY DIMENSIONS: Outside diameter 18.20 mm
TOLERANCES: +/- 0.02 mm
CERTIFICATIONS: ISO 9001; AS9100D
DRAWING UNITS: mm
"""


def test_reviewed_overlay_retains_source_units_and_unknowns(svc):
    run = svc.scenario.create_run()["scenario_run_id"]
    upload = svc.intake.upload(DOCUMENT.encode(), "requirements.txt", "blueprint")
    created = svc.intake.start_part_requirements(upload["upload_id"], "component-primary")
    assert svc.intake.wait_idle(30)
    draft = svc.intake.get_draft(created["draft_id"])
    fields = {field["name"]: field for field in draft["fields"]}
    assert fields["key_dimensions"]["unit"] == "mm"
    assert fields["key_dimensions"]["source_ref"]["line"] == 5
    assert fields["tolerances"]["unit"] == "mm" and fields["tolerances"]["source_ref"]["line"] == 6
    assert fields["certifications"]["value"] == ["ISO 9001", "AS9100D"]
    assert fields["certifications"]["source_ref"]["line"] == 7
    assert fields["inspection_requirements"]["validation_state"] == "unknown"
    confirmed = svc.intake.patch_draft(draft["draft_id"], {"expected_version": 1, "action": "confirm", "actor": "test reviewer"})
    overlay = svc.store.kv_get(f"req_overlay:{run}:component-primary")
    reviewed = {field["name"]: field for field in overlay["reviewed_fields"]}
    assert overlay["reviewed_by"] == "test reviewer" and overlay["reviewed_at"]
    assert reviewed["tolerances"]["source_ref"]["upload_id"] == upload["upload_id"]
    assert reviewed["inspection_requirements"]["validation_state"] == "unknown"
    assert confirmed["overlay"]["reviewed_fields"] == overlay["reviewed_fields"]


def test_dimension_unit_is_only_reported_when_unambiguous_and_updates_on_edit(svc):
    assert _dimensional_unit("diameter 2 mm / 0.08 in") is None
    assert _dimensional_unit("diameter 2") is None
    assert _dimensional_unit("diameter 0.08 inch") == "in"
    svc.scenario.create_run()
    upload = svc.intake.upload(DOCUMENT.encode(), "requirements.txt", "blueprint")
    created = svc.intake.start_part_requirements(upload["upload_id"], "component-primary")
    assert svc.intake.wait_idle(30)
    edited = svc.intake.patch_draft(created["draft_id"], {"expected_version": 1, "field_edits": {
        "key_dimensions": "diameter 2 mm / 0.08 in"}, "actor": "reviewer"})
    field = next(field for field in edited["fields"] if field["name"] == "key_dimensions")
    assert field["unit"] is None and field["edited_by"] == "reviewer"
    assert field["source_ref"] is None
    original = next(item for item in edited["history"][-1]["fields"] if item["name"] == "key_dimensions")
    assert original["source_ref"]["line"] == 5 and original["unit"] == "mm"
    confirmed = svc.intake.patch_draft(created["draft_id"], {"expected_version": edited["version"], "action": "confirm", "actor": "reviewer"})
    reviewed = next(item for item in confirmed["overlay"]["reviewed_fields"] if item["name"] == "key_dimensions")
    assert reviewed["source_ref"] is None and reviewed["edited_by"] == "reviewer"
    assert "key_dimensions" not in confirmed["overlay"]["source_refs"]
