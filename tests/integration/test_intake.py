"""Intake & mesh contract v1.1: uploads, part-requirements extraction/review/confirm through the change
gateway, segmented-GLB validation/activation with provenance, and blueprint jobs that need a provider."""

from __future__ import annotations

import json
import struct

import pytest

from recovery.domain import models as M
from recovery.domain.errors import DomainError

from wf_helpers import current, investigate, ranked

SRC = {"upload_id": "upl-blueprint-test", "page": 1, "bbox": [10.0, 20.0, 110.0, 80.0], "excerpt": "Item 30 fuel nozzle"}


def make_glb(nodes: list[dict]) -> bytes:
    """nodes: {name, translation, min, max, extras?, mesh: bool}. Builds a valid glTF 2.0 binary."""
    bin_data = bytearray()
    gltf = {"asset": {"version": "2.0", "generator": "re-source-test"}, "scene": 0, "scenes": [{"nodes": []}], "nodes": [], "meshes": [],
            "accessors": [], "bufferViews": [], "buffers": []}
    for spec in nodes:
        node = {"name": spec["name"], "translation": spec["translation"]}
        if spec.get("extras"):
            node["extras"] = spec["extras"]
        if spec.get("mesh", True):
            lo, hi = spec["min"], spec["max"]
            verts = [lo, hi, [lo[0], hi[1], lo[2]]]
            offset = len(bin_data)
            for v in verts:
                bin_data += struct.pack("<3f", *v)
            gltf["bufferViews"].append({"buffer": 0, "byteOffset": offset, "byteLength": 36})
            gltf["accessors"].append({"bufferView": len(gltf["bufferViews"]) - 1, "componentType": 5126, "count": 3, "type": "VEC3",
                                      "min": lo, "max": hi})
            gltf["meshes"].append({"primitives": [{"attributes": {"POSITION": len(gltf["accessors"]) - 1}}]})
            node["mesh"] = len(gltf["meshes"]) - 1
        gltf["nodes"].append(node)
        gltf["scenes"][0]["nodes"].append(len(gltf["nodes"]) - 1)
    gltf["buffers"].append({"byteLength": len(bin_data)})
    js = json.dumps(gltf).encode()
    js += b" " * ((4 - len(js) % 4) % 4)
    bin_data += b"\x00" * ((4 - len(bin_data) % 4) % 4)
    total = 12 + 8 + len(js) + 8 + len(bin_data)
    return (struct.pack("<III", 0x46546C67, 2, total) + struct.pack("<II", len(js), 0x4E4F534A) + js
            + struct.pack("<II", len(bin_data), 0x004E4942) + bytes(bin_data))


GOOD = [
    {"name": "Component_FuelNozzle_07", "translation": [0.05, 0.62, 0.18], "min": [-0.03, -0.03, -0.1], "max": [0.03, 0.03, 0.1],
     "extras": {"source_ref": SRC}},
    {"name": "Component_NGV_Segment_12", "translation": [0.42, 0.48, -0.12], "min": [-0.05, -0.04, -0.02], "max": [0.05, 0.04, 0.02],
     "extras": {"source_ref": {**SRC, "excerpt": "Item 10 NGV segment"}}},
    {"name": "Component_BleedDuct_HP", "translation": [-0.3, 0.7, 0.35], "min": [-0.15, -0.02, -0.02], "max": [0.15, 0.02, 0.02],
     "extras": {"source_ref": {**SRC, "excerpt": "Item 5 bleed duct"}}},
    {"name": "Module_Combustor", "translation": [0.1, 0, 0], "min": [-0.25, -0.5, -0.5], "max": [0.25, 0.5, 0.5]},
]
BROKEN = [
    {"name": "Component_FuelNozzle_07", "translation": [0.05, 0.62, 0.18], "min": [-0.03, -0.03, -0.1], "max": [0.03, 0.03, 0.1]},  # no source_ref
    {"name": "Component_BleedDuct_HP", "translation": [-0.3, 0.7, 0.35], "min": [-0.15, 0.0, 0.0], "max": [0.15, 0.0, 0.0],
     "extras": {"source_ref": SRC}},  # degenerate (flat on 2 axes); NGV node missing entirely
]
PNG = b"\x89PNG\r\n\x1a\n" + b"\x00" * 64

REQ_TEXT = """PART REQUIREMENTS — fuel nozzle replacement (integration test)
PART NUMBER: RS-FN-1002
REVISION: A
DESCRIPTION: Fuel nozzle assembly, revised swirler
MATERIAL: Inconel 625
MATING INTERFACES: Manifold flange F-12; combustor boss B-7
KEY DIMENSIONS: Tip OD 18.20 mm +/- 0.02
APPLICABLE STANDARDS: AS9100D; AMS 5666
INSPECTION REQUIREMENTS: Flow test per CMM 73-10-05
EFFECTIVITY: RS-TF2-CFG-A
"""


@pytest.fixture()
def run(svc):
    return svc.scenario.create_run()["scenario_run_id"]


def test_upload_dedupe_allowlist_and_magic(svc, run):
    glb = make_glb(GOOD)
    a = svc.intake.upload(glb, "engine.glb", "mesh_glb")
    b = svc.intake.upload(glb, "engine-copy.glb", "mesh_glb")
    assert b["upload_id"] == a["upload_id"] and b["duplicate_of"] == a["upload_id"]
    M.IntakeUpload.model_validate(a)
    assert a["sha256"] and a["storage_uri"].startswith("local://uploads/")  # offline: honest local storage
    with pytest.raises(DomainError) as e:
        svc.intake.upload(b"%PDF-1.7 ...", "engine.exe", "blueprint")
    assert e.value.status == 422
    with pytest.raises(DomainError):
        svc.intake.upload(b"not a glb", "engine.glb", "mesh_glb")  # magic bytes checked
    data, media, _ = svc.intake.content(a["upload_id"])
    assert data == glb and media == "model/gltf-binary"


def test_valid_glb_validates_activates_and_resets(svc, run):
    up = svc.intake.upload(make_glb(GOOD), "engine.glb", "mesh_glb")
    job = svc.intake.create_mesh_job({"upload_id": up["upload_id"], "engine_id": "engine-demo-001"})
    M.MeshJob.model_validate(job)
    assert job["status"] == "succeeded" and job["provider"] == "uploaded_glb", job["message"]
    assert {c["component_id"] for c in job["validation"]["checks"]} == {"component-primary", "component-secondary-a", "component-secondary-b"}
    assert all(c["ok"] and c["has_source_ref"] and c["vertex_count"] == 3 for c in job["validation"]["checks"])
    assert "Module_Combustor" in job["manifest_candidate"]["other_nodes"]
    prov = svc.intake.activate_job(job["job_id"])
    M.ManifestProvenance.model_validate({k: v for k, v in prov.items() if k != "anchors"})
    eng = svc.views.engine("engine-demo-001", run)
    M.EngineView.model_validate(eng)
    assert eng["engine"]["asset"]["kind"] == "generated"
    assert eng["engine"]["asset"]["glb_path"] == f"/api/v1/intake/uploads/{up['upload_id']}/content"
    assert eng["engine"]["asset"]["provenance"]["source_refs"]["component-primary"]["excerpt"] == "Item 30 fuel nozzle"
    assert [c["component_id"] for c in eng["components"]] == ["component-primary", "component-secondary-a", "component-secondary-b"]
    assert [c["case_id"] for c in eng["components"]] == ["case-primary", "case-secondary-a", "case-secondary-b"]  # IDs stable
    events = [e["type"] for e in svc.store.events_after(run, "__run__", 0, 500)]
    assert {"intake.uploaded", "intake.validated", "manifest.updated"} <= set(events)
    reset = svc.intake.reset_manifest()
    assert reset["kind"] == "procedural" and reset["previous_manifest_version"] == prov["manifest_version"]
    assert svc.views.engine("engine-demo-001", run)["engine"]["asset"]["kind"] == "procedural"


def test_broken_glb_fails_with_reasons_and_cannot_activate(svc, run):
    up = svc.intake.upload(make_glb(BROKEN), "broken.glb", "mesh_glb")
    job = svc.intake.create_mesh_job({"upload_id": up["upload_id"], "engine_id": "engine-demo-001"})
    assert job["status"] == "failed"
    checks = {c["component_id"]: c for c in job["validation"]["checks"]}
    assert not checks["component-secondary-a"]["present"]
    assert checks["component-secondary-b"]["non_degenerate_axes"] < 2 and not checks["component-secondary-b"]["ok"]
    assert not checks["component-primary"]["has_source_ref"]
    with pytest.raises(DomainError) as e:
        svc.intake.activate_job(job["job_id"])
    assert e.value.status == 409
    assert svc.intake.provenance()["kind"] == "procedural"


def test_blueprint_mesh_job_never_fakes_generation(svc, run, monkeypatch):
    monkeypatch.delenv("RS_MESH_PROVIDER", raising=False)
    up = svc.intake.upload(PNG, "blueprint.png", "blueprint")
    job = svc.intake.create_mesh_job({"upload_id": up["upload_id"], "engine_id": "engine-demo-001"})
    assert job["status"] == "provider_required" and job["validation"] is None and "no mesh was generated" in job["message"]
    assert svc.intake.get_job(job["job_id"])["status"] == "provider_required"
    with pytest.raises(DomainError) as e:
        svc.intake.activate_job(job["job_id"])
    assert e.value.status == 409
    with pytest.raises(DomainError):
        svc.intake.create_mesh_job({"upload_id": up["upload_id"], "engine_id": "engine-demo-001",
                                    "expected": [{"component_id": "component-invented", "node_name": "X"}]})


def test_part_requirements_review_confirm_reassesses_case_through_gateway(svc, run):
    d1 = investigate(svc, "case-primary")
    assert ranked(d1) == ["OFF-PA", "OFF-PB", "OFF-PC"]
    up = svc.intake.upload(REQ_TEXT.encode(), "fuel-nozzle-requirements.txt", "part_requirements", component_id="component-primary")
    draft = svc.intake.start_part_requirements(up["upload_id"], "component-primary")
    assert draft["status"] == "extracting"
    assert svc.intake.wait_idle(30)
    draft = svc.intake.get_draft(draft["draft_id"])
    M.PartRequirementDraft.model_validate(draft)
    assert draft["status"] == "needs_review"
    f = {x["name"]: x for x in draft["fields"]}
    assert f["part_number"]["value"] == "RS-FN-1002" and f["part_number"]["validation_state"] == "valid"
    assert f["part_number"]["source_ref"]["line"] == 2 and "RS-FN-1002" in f["part_number"]["source_ref"]["excerpt"]
    assert f["applicable_standards"]["value"] == ["AS9100D", "AMS 5666"]
    with pytest.raises(DomainError) as e:
        svc.intake.patch_draft(draft["draft_id"], {"expected_version": 99, "field_edits": {"material": "Haynes 230"}})
    assert e.value.status == 409
    draft = svc.intake.patch_draft(draft["draft_id"], {"expected_version": 1, "field_edits": {"material": "Haynes 230"}, "actor": "reviewer-1"})
    m = next(x for x in draft["fields"] if x["name"] == "material")
    assert draft["version"] == 2 and m["edited_by"] == "reviewer-1" and m["extraction_mode"] == "user_edit"
    with pytest.raises(DomainError):
        svc.intake.patch_draft(draft["draft_id"], {"expected_version": 2, "field_edits": {"part_number": "??"}, "action": "confirm"})
    draft = svc.intake.patch_draft(draft["draft_id"], {"expected_version": 2, "action": "confirm", "actor": "reviewer-1"})
    assert draft["status"] == "confirmed" and draft["change_id"] and draft["affected_case_ids"] == ["case-primary"]
    assert svc.coordinator.wait_idle(60)
    case, d2 = current(svc, "case-primary")
    assert d2["label"] == "D2" and ranked(d2) == []  # every offer is RS-FN-1001: none meets the confirmed RS-FN-1002 requirement
    id_checks = [c for c in d2["checks"] if c["requirement_id"] == "REQ-FN-ID-01"]
    assert id_checks and all(c["result"] == "fail" and "RS-FN-1002" in c["explanation"] for c in id_checks)
    assert all(draft["draft_id"] in c["requirement_version"] for c in id_checks)
    diff = svc.decisions.get_diff(run, "case-primary", d1["decision_id"], d2["decision_id"])
    assert diff["reused_check_ids"] and diff["impact_paths"][0][0]["id"] == "RS-FN-1001"
    assert svc.store.get_case(run, "case-secondary-a")["input_revision"] == 1  # other components untouched
    types = [e["type"] for e in svc.store.events_after(run, "__run__", 0, 500)]
    assert "intake.extracted" in types and "intake.confirmed" in types


def test_intake_routes_over_http(svc, run):
    from fastapi.testclient import TestClient

    from recovery.api import app as api

    api.SERVICES = svc
    try:
        client = TestClient(api.app)  # no lifespan: uses the test container
        glb = make_glb(GOOD)
        r = client.post("/api/v1/intake/uploads", data={"kind": "mesh_glb", "engine_id": "engine-demo-001"},
                        files={"file": ("engine.glb", glb, "model/gltf-binary")})
        assert r.status_code == 201, r.text
        up = r.json()
        assert client.get(f"/api/v1/intake/uploads/{up['upload_id']}").json()["sha256"] == up["sha256"]
        c = client.get(f"/api/v1/intake/uploads/{up['upload_id']}/content")
        assert c.status_code == 200 and c.content == glb and c.headers["content-type"] == "model/gltf-binary"
        r = client.post("/api/v1/intake/mesh-jobs", json={"upload_id": up["upload_id"], "engine_id": "engine-demo-001"},
                        headers={"Idempotency-Key": "mesh-1"})
        assert r.status_code == 201 and r.json()["status"] == "succeeded"
        job_id = r.json()["job_id"]
        assert client.get(f"/api/v1/intake/mesh-jobs/{job_id}").json()["status"] == "succeeded"
        assert client.post(f"/api/v1/intake/mesh-jobs/{job_id}/activate").json()["kind"] == "generated"
        assert client.get("/api/v1/intake/manifest").json()["job_id"] == job_id
        r = client.post("/api/v1/intake/uploads", data={"kind": "mesh_glb"}, files={"file": ("x.exe", b"MZ", "application/octet-stream")})
        assert r.status_code == 422 and r.json()["code"] == "INVALID_INPUT"
        up2 = client.post("/api/v1/intake/uploads", data={"kind": "part_requirements", "component_id": "component-primary"},
                          files={"file": ("req.txt", REQ_TEXT.encode(), "text/plain")}).json()
        r = client.post("/api/v1/intake/part-requirements", json={"upload_id": up2["upload_id"], "component_id": "component-primary"})
        assert r.status_code == 202
        assert svc.intake.wait_idle(30)
        d = client.get(f"/api/v1/intake/part-requirements/{r.json()['draft_id']}").json()
        assert d["status"] == "needs_review"
        assert client.post("/api/v1/intake/manifest/reset").json()["kind"] == "procedural"
    finally:
        api.SERVICES = None
