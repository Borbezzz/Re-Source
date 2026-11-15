"""Independent review regressions for product ownership, grounding and stale requests."""

from types import SimpleNamespace
import importlib

import pytest


def test_generated_parts_cannot_borrow_identity_from_another_document(svc, monkeypatch):
    monkeypatch.setattr(svc.products, "_dispatch", lambda _: None)
    pid = svc.products.create(name="Two unrelated specifications")["project_id"]
    project = svc.products.upload(pid, b"A wheel assembly requires aluminum.", "wheel.txt", "requirements")
    wheel_document = project["documents"][0]["document_id"]
    svc.products.upload(pid, b"Bracket assembly.\nPart number: BRACKET-77", "bracket.txt", "requirements")
    result = {"parts": [
        {"name": "wheel assembly", "quantity": 1, "part_number": "BRACKET-77", "document_id": wheel_document,
         "requirements": [{"key": "material", "label": "Material", "value": "aluminum", "source_quote": "A wheel assembly requires aluminum."}]},
        {"name": "Bracket assembly", "quantity": 1, "part_number": None, "document_id": wheel_document,
         "requirements": [{"key": "material", "label": "Material", "value": "aluminum", "source_quote": "A wheel assembly requires aluminum."}]},
    ]}
    monkeypatch.setattr(svc, "model", SimpleNamespace(available=True, structured=lambda *args, **kwargs: result))
    svc.products.start_extraction(pid)
    job = svc.products._load(pid)
    svc.products.extract_project(pid, job["_extract_job"], job["input_version"])
    parts = svc.products.get(pid)["parts"]
    assert [p["name"] for p in parts] == ["wheel assembly"]
    assert parts[0]["part_number"] is None


def test_duplicate_upload_returns_the_current_version_without_invalidating_review(svc):
    pid = svc.products.create(name="A fixture")["project_id"]
    first = svc.products.upload(pid, b"Part: Wheel\nMaterial: Aluminum", "wheel.txt", "requirements")
    repeated = svc.products.upload(pid, b"Part: Wheel\nMaterial: Aluminum", "wheel.txt", "requirements")
    current = svc.products.get(pid)
    assert repeated["version"] == current["version"] == first["version"]
    assert repeated["input_version"] == first["input_version"]
    assert len(current["documents"]) == 1


def test_duplicate_extraction_request_and_stale_job_do_not_change_version(svc, monkeypatch):
    monkeypatch.setattr(svc.products, "_dispatch", lambda _: None)
    pid = svc.products.create(name="A fixture")["project_id"]
    svc.products.upload(pid, b"Part: Wheel\nMaterial: Aluminum", "wheel.txt", "requirements")
    first = svc.products.start_extraction(pid)
    repeated = svc.products.start_extraction(pid)
    assert repeated["version"] == svc.products.get(pid)["version"] == first["version"]
    svc.products.extract_project(pid, "stale-job", first["input_version"])
    assert svc.products.get(pid)["version"] == first["version"]


@pytest.mark.parametrize("label, number", [("Part number", "BRACKET-7"), ("Drawing_part_number", "BRACKET-77")])
def test_ai_oem_number_requires_an_exact_explicit_part_label(svc, monkeypatch, label, number):
    monkeypatch.setattr(svc.products, "_dispatch", lambda _: None)
    pid = svc.products.create(name="Bracket specification")["project_id"]
    project = svc.products.upload(pid, f"Bracket assembly requires steel.\n{label}: BRACKET-77".encode(), "bracket.txt", "requirements")
    document_id = project["documents"][0]["document_id"]
    generated = {"parts": [{"name": "Bracket assembly", "quantity": 1, "part_number": number, "document_id": document_id,
                             "requirements": [{"key": "material", "label": "Material", "value": "steel",
                                               "source_quote": "Bracket assembly requires steel."}]}]}
    monkeypatch.setattr(svc, "model", SimpleNamespace(available=True, structured=lambda *args, **kwargs: generated))
    svc.products.start_extraction(pid)
    job = svc.products._load(pid)
    svc.products.extract_project(pid, job["_extract_job"], job["input_version"])
    assert svc.products.get(pid)["parts"][0]["part_number"] is None


@pytest.mark.parametrize("value, unit, snippet", [("8 mm", None, "Diameter: 18 mm"), ("8", "mm", "Diameter: 8 in")])
def test_live_evidence_requires_complete_values_and_matching_units(svc, monkeypatch, value, unit, snippet):
    module = importlib.import_module("recovery.services.product_workers")
    monkeypatch.setattr(svc.products, "_dispatch", lambda _: None)
    monkeypatch.setattr(svc, "model", SimpleNamespace(available=False, structured=lambda *args, **kwargs: None))
    monkeypatch.setattr(module, "linkup", SimpleNamespace(available=True, search=lambda *args, **kwargs: {
        "ok": True, "results": [{"url": "https://supplier.example/wheel", "title": "Wheel supplier", "snippet": snippet}]}))
    pid = svc.products.create(name="Wheel sourcing")["project_id"]
    parts = [{"part_id": "wheel", "name": "Wheel", "requirements": [{"key": "diameter", "label": "Diameter", "value": value, "unit": unit}]}]
    svc.products.review(pid, parts, True)
    queued = svc.products.investigate(pid, mode="live")
    job = queued["research"][0]
    svc.products.research_part(pid, job["part_id"], job["job_id"], queued["input_version"])
    research = svc.products.get(pid)["research"][0]
    assert research["status"] == "complete", research
    assert research["candidates"][0]["evidence"][0]["status"] == "unknown"
    assert "does not establish" in research["candidates"][0]["evidence"][0]["note"]


def test_ai_supplier_and_country_claims_require_nonempty_whole_values(svc, monkeypatch):
    module = importlib.import_module("recovery.services.product_workers")
    monkeypatch.setattr(svc.products, "_dispatch", lambda _: None)
    monkeypatch.setattr(svc, "model", SimpleNamespace(available=False, structured=lambda *args, **kwargs: None))
    monkeypatch.setattr(module, "linkup", SimpleNamespace(available=True, search=lambda *args, **kwargs: {
        "ok": True, "results": [{"url": "https://supplier.example/components", "title": "Custom components", "snippet": "Wheels in steel."}]}))
    monkeypatch.setattr(module, "databricks_sql", SimpleNamespace(configured=True, ai_extract_batch=lambda *args: {
        "0": {"supplier_name": "", "country": "US"}}))
    pid = svc.products.create(name="Wheel sourcing")["project_id"]
    svc.products.review(pid, [{"part_id": "wheel", "name": "Wheel", "requirements": [{"key": "material", "label": "Material", "value": "steel"}]}], True)
    queued = svc.products.investigate(pid, mode="live")
    job = queued["research"][0]
    svc.products.research_part(pid, job["part_id"], job["job_id"], queued["input_version"])
    candidate = svc.products.get(pid)["research"][0]["candidates"][0]
    assert candidate["supplier_name"] == "supplier.example"
    assert candidate["country"] is None
