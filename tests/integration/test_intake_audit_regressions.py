"""Regression probes for the real-document intake audit (provenance and failed confirmations)."""

from __future__ import annotations

import copy
import importlib
from types import SimpleNamespace

import pytest

from recovery.adapters import store as st
from recovery.config import settings
from recovery.domain.errors import DomainError
from test_intake import BLUEPRINT_TEXT, GOOD, REQ_TEXT, make_glb, sourced_nodes
from wf_helpers import investigate


@pytest.fixture()
def run(svc):
    return svc.scenario.create_run()["scenario_run_id"]


def _job(svc, nodes):
    up = svc.intake.upload(make_glb(nodes), "assembly.glb", "mesh_glb")
    return svc.intake.create_mesh_job({"upload_id": up["upload_id"]})


def _source(svc, **kwargs):
    return svc.intake.upload(BLUEPRINT_TEXT.encode(), "source.txt", "blueprint", **kwargs)


def _draft(svc, text=REQ_TEXT):
    up = svc.intake.upload(text.encode(), "requirements.txt", "part_requirements", component_id="component-primary")
    draft = svc.intake.start_part_requirements(up["upload_id"], "component-primary")
    assert svc.intake.wait_idle(30)
    return svc.intake.get_draft(draft["draft_id"])


def test_fabricated_source_is_rejected_even_for_a_previously_succeeded_job(svc, run):
    job = _job(svc, GOOD)
    assert job["status"] == "failed"
    assert not any(check["has_source_ref"] for check in job["validation"]["checks"])
    # A job saved by the vulnerable build must not bypass fresh activation validation.
    job["status"] = "succeeded"
    svc.intake._put(f"intake:job:{job['job_id']}", job)
    with pytest.raises(DomainError, match="source provenance"):
        svc.intake.activate_job(job["job_id"])
    assert svc.intake.provenance()["kind"] == "procedural"


def test_document_provenance_cannot_cross_runs_or_components(svc, run):
    source = _source(svc, component_id="component-primary")
    job = _job(svc, sourced_nodes(source["upload_id"]))
    checks = job["validation"]["checks"]
    assert checks[0]["ok"] and not checks[1]["has_source_ref"]
    svc.scenario.create_run()
    other = _job(svc, sourced_nodes(source["upload_id"]))
    assert other["status"] == "failed"
    assert all("not accessible" in " ".join(c["problems"]) for c in other["validation"]["checks"])


@pytest.mark.parametrize("patch", [
    {"upload_id": None}, {"page": 0}, {"page": True}, {"page": 2}, {"line": -1}, {"line": 999},
    {"bbox": [0, 0, -1, 1]}, {"bbox": [0, 0, float("inf"), 1]}, {"bbox": [0, 1]},
    {"excerpt": "invented material specification"}, {"element_id": {"bad": True}},
    {"page": None, "line": None, "excerpt": None, "note": "a note alone is not a citation"},
])
def test_mesh_rejects_invalid_or_unverifiable_source_locators(svc, run, patch):
    nodes = sourced_nodes(_source(svc)["upload_id"])
    nodes[0]["extras"]["source_ref"].update(patch)
    job = _job(svc, nodes)
    assert job["status"] == "failed"
    assert not job["validation"]["checks"][0]["has_source_ref"]


def test_mesh_rejects_wrong_kind_and_rechecks_source_at_activation(svc, run):
    wrong_kind = svc.intake.upload(make_glb(GOOD), "another.glb", "mesh_glb")
    assert _job(svc, sourced_nodes(wrong_kind["upload_id"]))["status"] == "failed"
    source = _source(svc)
    job = _job(svc, sourced_nodes(source["upload_id"]))
    assert job["status"] == "succeeded"
    rec = svc.intake.get_upload(source["upload_id"])
    rec["kind"] = "mesh_glb"
    svc.intake._put(f"intake:upload:{source['upload_id']}", rec)
    with pytest.raises(DomainError):
        svc.intake.activate_job(job["job_id"])
    assert svc.intake.provenance()["kind"] == "procedural"


def test_activation_requires_source_bytes_and_rebuilds_manifest_provenance(svc, run):
    from recovery.adapters.blob_store import blob_store

    source = _source(svc)
    job = _job(svc, sourced_nodes(source["upload_id"]))
    job["manifest_candidate"]["components"]["component-primary"]["source_ref"]["upload_id"] = "fabricated"
    svc.intake._put(f"intake:job:{job['job_id']}", job)
    active = svc.intake.activate_job(job["job_id"])
    assert active["source_refs"]["component-primary"]["upload_id"] == source["upload_id"]
    rec = svc.intake.get_upload(source["upload_id"])
    blob_store.local_path(rec["sha256"], rec["ext"]).unlink()
    with pytest.raises(DomainError):
        svc.intake.activate_job(job["job_id"])


def test_ai_drawing_identifier_and_unsupported_engineering_claims_remain_unknown(svc, run, monkeypatch):
    module = importlib.import_module("recovery.services.intake")
    generated = {"part_number": "S-81367", "revision": "A", "description": "Turbine rotor blade section",
                 "mating_interfaces": "Leading edge, trailing edge", "key_dimensions": "Thickness 0.086 in",
                 "drawing_units": "in", "certifications": ["AS9100D", "INVENTED"]}
    monkeypatch.setattr(module, "model_client", SimpleNamespace(available=True, extract=lambda *args: generated))
    object.__setattr__(settings, "extraction_backend", "openai")
    draft = _draft(svc, "S-81367\nFigure 5-5. Turbine rotor blade section\nLeading edge\nTrailing edge\nAS9100D\n")
    fields = {f["name"]: f for f in draft["fields"]}
    for name in generated.keys() - {"description"}:
        assert fields[name]["validation_state"] == "unknown", fields[name]
        assert fields[name]["source_ref"] is None and fields[name]["confidence"] is None
    assert fields["description"]["validation_state"] == "valid"
    assert fields["description"]["source_ref"]["line"] == 2
    with pytest.raises(DomainError, match="missing or invalid"):
        svc.intake.patch_draft(draft["draft_id"], {"expected_version": 1, "action": "confirm"})
    reviewed = svc.intake.patch_draft(draft["draft_id"], {"expected_version": 1, "action": "confirm", "actor": "reviewer",
                                      "field_edits": {"part_number": "RS-FN-1002", "revision": "A", "material": "Inconel 625"}})
    material = next(f for f in reviewed["fields"] if f["name"] == "material")
    assert reviewed["status"] == "confirmed" and material["validation_state"] == "valid"
    assert material["source_ref"] is None and material["edited_by"] == "reviewer"


def test_confirmation_failure_rolls_back_edits_and_same_request_can_retry(svc, run, monkeypatch):
    draft = _draft(svc)
    command = {"expected_version": 1, "action": "confirm", "field_edits": {"material": "Haynes 230"}}
    original = svc.changes.inject_requirement_change
    monkeypatch.setattr(svc.changes, "inject_requirement_change", lambda *args: (_ for _ in ()).throw(RuntimeError("gateway outage")))
    with pytest.raises(RuntimeError, match="gateway outage"):
        svc.intake.patch_draft(draft["draft_id"], command)
    saved = svc.intake.get_draft(draft["draft_id"])
    assert saved["status"] == "needs_review" and saved["version"] == 1 and saved["change_id"] is None
    assert svc.store.kv_get(f"req_overlay:{run}:component-primary") is None
    monkeypatch.setattr(svc.changes, "inject_requirement_change", original)
    result = svc.intake.patch_draft(draft["draft_id"], command)
    assert result["status"] == "confirmed" and result["version"] == 2 and result["change_id"]
    revision = svc.store.get_case(run, "case-primary")["input_revision"]
    assert svc.intake.patch_draft(draft["draft_id"], command) == result
    assert svc.store.get_case(run, "case-primary")["input_revision"] == revision
    assert len(svc.store.find(st.change_events, run_id=run)) == 1


def test_reassessment_never_launches_before_outer_commit_or_after_rollback(svc, run, monkeypatch):
    investigate(svc, "case-primary")
    draft = _draft(svc)
    launched = []

    def launch(*args, **kwargs):
        launched.append({"in_transaction": getattr(svc.store._local, "conn", None) is not None,
                         "draft": svc.intake.get_draft(draft["draft_id"]),
                         "overlay": svc.store.kv_get(f"req_overlay:{run}:component-primary")})

    monkeypatch.setattr(svc.coordinator, "_launch", launch)
    command = {"expected_version": 1, "action": "confirm"}
    with pytest.raises(RuntimeError, match="abort outer transaction"):
        with svc.store.tx():
            svc.intake.patch_draft(draft["draft_id"], command)
            assert launched == []
            raise RuntimeError("abort outer transaction")
    assert launched == []
    assert svc.intake.get_draft(draft["draft_id"])["status"] == "needs_review"
    assert svc.store.get_case(run, "case-primary")["input_revision"] == 1
    with svc.store.tx():
        svc.intake.patch_draft(draft["draft_id"], command)
        assert launched == []
    assert len(launched) == 1 and not launched[0]["in_transaction"]
    assert launched[0]["draft"]["status"] == "confirmed" and launched[0]["overlay"]["draft_id"] == draft["draft_id"]


def test_gateway_resumes_historical_partial_fanout_without_invalidating_twice(svc, run):
    draft = _draft(svc)
    component = svc.catalog.components["component-primary"]
    part = component["part_identity"]
    dedup = f"requirement:component-primary:{draft['draft_id']}:v1"
    change = svc.changes._register(run, "requirement", draft["draft_id"], "historical-partial", dedup, {},
                                   title="Interrupted confirmation", effective_at=draft["created_at"],
                                   scope={"component_id": "component-primary", "part_id": part})
    svc.changes._fanout_case(run, change, "case-primary", [], [])
    assert svc.store.get_case(run, "case-primary")["input_revision"] == 2
    result = svc.intake.patch_draft(draft["draft_id"], {"expected_version": 1, "action": "confirm"})
    assert result["change_id"] == change["change_id"] and result["affected_case_ids"] == ["case-primary"]
    assert svc.store.get_case(run, "case-primary")["input_revision"] == 2
    assert svc.store.get_run(run)["barrier_count"] == 0
    assert svc.store.kv_get(f"req_overlay:{run}:component-primary")["draft_id"] == draft["draft_id"]


def test_historical_confirmed_draft_without_change_can_be_repaired(svc, run):
    draft = _draft(svc)
    overlay = {"part_identity": {"part_number": "RS-FN-1002", "revision": "A"}, "draft_version": 1,
               "draft_id": draft["draft_id"], "documented": {}}
    draft.update(status="confirmed", overlay=copy.deepcopy(overlay))
    svc.intake._put(f"intake:draft:{draft['draft_id']}", draft)
    result = svc.intake.patch_draft(draft["draft_id"], {"expected_version": 1, "action": "confirm"})
    assert result["change_id"] and svc.store.kv_get(f"req_overlay:{run}:component-primary")["draft_id"] == draft["draft_id"]
