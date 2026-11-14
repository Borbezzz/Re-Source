"""Assembly previews cannot silently launch the engine's research rules."""

import importlib
import json
from types import SimpleNamespace

import pytest
from fastapi.testclient import TestClient

from recovery.domain.errors import DomainError
from recovery.services import assembly_profiles
from recovery.services.batches import BatchService

TOY_NODES = {
    "toycar-body": "ToyCar_Body", "toycar-glazing": "ToyCar_Glazing",
    "toycar-wheel-fl": "ToyCar_Wheel_FL", "toycar-wheel-fr": "ToyCar_Wheel_FR",
    "toycar-wheel-rl": "ToyCar_Wheel_RL", "toycar-wheel-rr": "ToyCar_Wheel_RR",
    "toycar-bumper-f": "ToyCar_Bumper_F", "toycar-bumper-r": "ToyCar_Bumper_R",
}


def test_profiles_expose_agreed_toy_mapping_without_engine_research(svc, monkeypatch):
    api = importlib.import_module("recovery.api.app")
    monkeypatch.setattr(api, "SERVICES", svc)
    client = TestClient(api.app)
    response = client.get("/api/v1/assemblies")
    assert response.status_code == 200
    profiles = {row["assembly_id"]: row for row in response.json()}
    assert profiles["engine-demo-001"]["investigation_available"] is True
    toy = profiles["toy-car-demo"]
    assert {c["component_id"]: c["node_name"] for c in toy["components"]} == TOY_NODES
    assert toy["requirements_status"] == "source_required" and toy["investigation_available"] is False
    assert client.get("/api/v1/assemblies/toy-car-demo").json() == toy
    assert client.get("/api/v1/assemblies/missing").status_code == 404
    assert client.post("/api/v1/scenario-runs", json={"manifest_id": "toy-car-demo"}).status_code == 422
    run = svc.scenario.create_run()["scenario_run_id"]
    with pytest.raises(DomainError):
        BatchService(svc).create(run, {"assembly_id": "toy-car-demo", "component_ids": ["toycar-body"], "mode": "seeded"}, "key")


def test_configured_profiles_reject_unsafe_enablement_and_duplicate_mappings(svc, monkeypatch, tmp_path):
    directory = tmp_path / "assembly-profiles"
    directory.mkdir()
    monkeypatch.setattr(assembly_profiles, "settings", SimpleNamespace(data_dir=tmp_path))
    profile = {"assembly_id": "custom", "display_name": "Custom", "product_type": "other", "description": "preview",
               "requirements_status": "source_required", "investigation_available": False, "data_origin": "synthetic_demo",
               "components": [{"component_id": "a", "display_name": "A", "node_name": "Node_A"}]}
    path = directory / "custom.json"
    path.write_text(json.dumps(profile))
    assert assembly_profiles.get_profile(svc, "custom")["components"][0]["node_name"] == "Node_A"
    profile["investigation_available"] = True
    path.write_text(json.dumps(profile))
    with pytest.raises(ValueError, match="must require reviewed sources"):
        assembly_profiles.profiles(svc)
    profile["investigation_available"] = False
    profile["components"].append({"component_id": "b", "display_name": "B", "node_name": "Node_A"})
    path.write_text(json.dumps(profile))
    with pytest.raises(ValueError, match="invalid component mapping"):
        assembly_profiles.profiles(svc)
