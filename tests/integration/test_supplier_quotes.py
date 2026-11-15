"""Exercise both quote imports and their private source and review routes."""
from concurrent.futures import ThreadPoolExecutor
from importlib import import_module
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from recovery.services.supplier_quotes import SupplierQuotes

PDF = Path(__file__).resolve().parents[1] / "fixtures" / "quotes" / "sample-quote.pdf"
REPLY = """Hello, we can supply 4 units at EUR 142 each and dispatch in 12 working days.
Part number: RS-DEMO-FB-001
Revision: C
Quote date: 2026-11-13
Deliver to: Bristol
Minimum order: 5 units
Exceptions: inspection charged separately"""


@pytest.fixture
def quote_api(svc, offline_settings, monkeypatch):
    module = import_module("recovery.api.app")
    monkeypatch.setattr(module, "SERVICES", svc)
    original = offline_settings.public_demo
    object.__setattr__(offline_settings, "public_demo", True)
    try:
        yield module.app
    finally:
        object.__setattr__(offline_settings, "public_demo", original)


def test_pdf_and_reply_comparison_review_and_source_privacy(quote_api):
    with TestClient(quote_api) as owner, TestClient(quote_api) as other:
        project = owner.post("/api/v1/products", json={"demo_id": "turbofan"}).json()
        project_url = f"/api/v1/products/{project['project_id']}"
        url = f"{project_url}/quotes"
        part = next(p for p in project["parts"] if p["part_number"] == "RS-DEMO-FB-001")
        a = {"supplier": "Northline", "part_id": part["part_id"]}
        upload = {"file": ("supplier.pdf", PDF.read_bytes(), "application/pdf")}
        response = owner.post(url, data=a, files=upload)
        assert response.status_code == 201, response.text
        pdf_quote = response.json()["quotes"][0]
        assert pdf_quote["terms"]["unit_price"]["value"] == "GBP 125.50"
        assert pdf_quote["terms"]["lead_time"] == {
            "value": "8 working days", "excerpt": "Lead time: 8 working days", "page": 2, "origin": "extracted"
        }
        assert owner.get(pdf_quote["source_url"]).content == PDF.read_bytes()
        assert owner.post(url, data=a, files=upload).json()["quotes"] == [pdf_quote]

        b = {"supplier": "Westmoor", "part_id": part["part_id"], "reply": REPLY}
        response = owner.post(url, data=b)
        assert response.status_code == 201, response.text
        first, reply = response.json()["quotes"]
        assert first == pdf_quote
        assert reply["terms"]["unit_price"]["value"] == "EUR 142 each"
        assert reply["terms"]["currency"]["value"] == "EUR"
        assert reply["terms"]["lead_time"]["value"] == "12 working days"
        assert reply["terms"]["quote_date"]["value"] == "2026-11-13"
        assert reply["terms"]["destination"]["value"] == "Bristol"
        assert "certificates" not in reply["terms"]
        assert "Revision differs. Requested B; offered C." in reply["issues"]
        assert any("Minimum order 5" in issue for issue in reply["issues"])
        assert "Revision differs" in reply["follow_up"]
        assert owner.get(reply["source_url"]).text == REPLY
        assert other.get(url).status_code == 404
        assert other.get(reply["source_url"]).status_code == 404

        quote_url = f"{url}/{reply['quote_id']}"
        review = {"expected_version": 1, "terms": {"revision": "B"}}
        response = owner.patch(quote_url, json=review)
        assert response.status_code == 200, response.text
        saved = owner.get(url).json()["quotes"][1]
        assert saved["reviewed"] and saved["version"] == 2
        assert saved["terms"]["revision"] == {"value": "B", "excerpt": "Revision: C", "page": 1, "origin": "buyer_review"}
        assert saved["terms"]["unit_price"] == reply["terms"]["unit_price"]
        assert owner.patch(quote_url, json=review).status_code == 409
        current = owner.get(project_url).json()
        assert current["input_version"] == project["input_version"]
        assert current["documents"] == project["documents"]
        assert current["parts"] == project["parts"]


def test_invalid_and_ambiguous_quote_sources(quote_api):
    with TestClient(quote_api) as client:
        project = client.post("/api/v1/products", json={"demo_id": "turbofan"}).json()
        url = f"/api/v1/products/{project['project_id']}/quotes"
        fields = {"part_id": project["parts"][0]["part_id"], "supplier": "Buyer fixture"}
        assert client.post(url, data=fields).status_code == 422
        assert client.post(url, data=fields, files={"file": ("bad.pdf", b"wrong format", "application/pdf")}).status_code == 422
        assert client.get(url).json()["quotes"] == []
        response = client.post(url, data={**fields, "reply": "Unit price: $18\nUnit price: $20\nRevision: B"})
        assert response.status_code == 201
        quote = response.json()["quotes"][0]
        assert set(quote["terms"]) == {"revision"}
        assert "unit price" in quote["follow_up"]


def test_concurrent_duplicate_imports_store_one_quote(svc):
    project = svc.products.create("turbofan")
    service = SupplierQuotes(svc.products)
    args = (project["project_id"], project["parts"][0]["part_id"], "Northline", PDF.read_bytes(), "quote.pdf", "pdf")
    with ThreadPoolExecutor(max_workers=4) as workers:
        responses = list(workers.map(lambda _: service.import_quote(*args), range(4)))
    assert all(len(result["quotes"]) == 1 for result in responses)
    assert [event["type"] for event in svc.products.get(project["project_id"])["events"]].count("quote.imported") == 1
