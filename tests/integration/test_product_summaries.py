"""Private dashboard reads use persisted projects, including in-flight worker progress."""
from __future__ import annotations

import importlib
from contextlib import nullcontext

import pytest
from fastapi.testclient import TestClient
from recovery.config import settings
from recovery.runtime.context import visitor_id
from recovery.services.container import Services

SUMMARY_FIELDS = {
    "project_id", "name", "demo_id", "product_type", "status", "created_at", "updated_at",
    "part_count", "confirmed_part_count", "research_count", "active_research_count",
    "completed_research_count", "failed_research_count", "selected_count", "package_status",
    "agent_status", "agent_stage",
}


@pytest.fixture
def summary_api(svc, monkeypatch):
    module = importlib.import_module("recovery.api.app")
    original = settings.public_demo
    object.__setattr__(settings, "public_demo", True)
    monkeypatch.setattr(module, "SERVICES", svc)
    yield module
    object.__setattr__(settings, "public_demo", original)


def test_summary_api_is_private_bounded_and_newest_update_first(summary_api):
    with TestClient(summary_api.app) as owner, TestClient(summary_api.app) as other:
        assert owner.get("/api/v1/products").json() == {"projects": []}
        first = owner.post("/api/v1/products", json={"demo_id": "desk-lamp"}).json()
        second = owner.post("/api/v1/products", json={"name": "Private new prototype"}).json()
        other.post("/api/v1/products", json={"demo_id": "toy-car", "name": "Another visitor's confidential design"})
        response = owner.get("/api/v1/products")
        assert response.status_code == 200, response.text
        assert response.headers["cache-control"] == "private, no-store"
        rows = response.json()["projects"]
        assert [row["project_id"] for row in rows] == [second["project_id"], first["project_id"]]
        assert all(set(row) == SUMMARY_FIELDS for row in rows)
        assert [row["status"] for row in rows] == ["draft", "review"]
        assert rows[1]["part_count"] == 3 and rows[1]["confirmed_part_count"] == 0
        assert rows[0]["demo_id"] is None and rows[0]["package_status"] is None
        assert "confidential" not in response.text
        assert owner.get("/api/v1/products?limit=1").json()["projects"][0]["project_id"] == second["project_id"]
        reviewed = owner.patch(f"/api/v1/products/{first['project_id']}/parts", json={"parts": first["parts"], "confirm": True})
        assert reviewed.status_code == 200
        updated = owner.get("/api/v1/products?limit=1").json()["projects"]
        assert len(updated) == 1 and updated[0]["project_id"] == first["project_id"]
        assert updated[0]["status"] == "ready" and updated[0]["confirmed_part_count"] == 3
        assert len(other.get("/api/v1/products").json()["projects"]) == 1
        for limit in ("0", "101", "invalid"):
            assert owner.get(f"/api/v1/products?limit={limit}").status_code == 422


def test_summary_api_tracks_queued_running_complete_failed_and_package_progress(summary_api, svc, monkeypatch):
    jobs = []
    monkeypatch.setattr(svc.products, "_dispatch", jobs.append)
    monkeypatch.setattr(svc.jobs, "lock", lambda _: nullcontext())
    with TestClient(summary_api.app) as owner:
        p = owner.post("/api/v1/products", json={"demo_id": "toy-car"}).json()
        pid, parts = p["project_id"], p["parts"]
        path = f"/api/v1/products/{pid}"
        assert owner.patch(f"{path}/parts", json={"parts": parts, "confirm": True}).status_code == 200
        assert owner.post(f"{path}/investigations", json={"part_ids": [part["part_id"] for part in parts[:2]], "mode": "demo"}).status_code == 202
        assert owner.post(f"{path}/investigations", json={"part_ids": [parts[2]["part_id"]], "mode": "live"}).status_code == 202
        assert owner.post(f"{path}/investigations", json={"part_ids": [parts[3]["part_id"]], "mode": "demo"}).status_code == 202
        first_job = svc.store.kv_get(f"job:{jobs[0]}")["payload"]
        token = visitor_id.set(owner.cookies.get("resource_visitor"))
        try:
            svc.products._research_progress(**first_job, stage="planning", summary="Research is running.")
        finally:
            visitor_id.reset(token)
        svc.jobs.execute(jobs[1])  # Complete one demo comparison.
        svc.jobs.execute(jobs[2])  # Unconfigured live search has an honest failed result.
        row = owner.get("/api/v1/products").json()["projects"][0]
        assert row["status"] == "investigating"
        assert row["part_count"] == row["confirmed_part_count"] == 8
        assert row["research_count"] == 4
        assert row["active_research_count"] == 2  # One queued, one running.
        assert row["completed_research_count"] == row["failed_research_count"] == 1
        assert row["selected_count"] == 0 and row["package_status"] is None
        svc.jobs.execute(jobs[0])
        svc.jobs.execute(jobs[3])
        finished = owner.get("/api/v1/products").json()["projects"][0]
        assert finished["status"] == "results" and finished["active_research_count"] == 0
        assert finished["completed_research_count"] == 3 and finished["failed_research_count"] == 1
        detail = owner.get(path).json()
        result = next(r for r in detail["research"] if r["status"] == "complete")
        owner.patch(f"{path}/selections", json={"part_id": result["part_id"], "candidate_id": result["candidates"][0]["candidate_id"]})
        package = owner.post(f"{path}/package").json()["package"]
        draft = owner.get("/api/v1/products").json()["projects"][0]
        assert draft["status"] == "packaged" and draft["package_status"] == "draft" and draft["selected_count"] == 1
        owner.post(f"{path}/package/approve", json={"expected_package_id": package["package_id"], "acknowledge_unverified": True})
        assert owner.get("/api/v1/products").json()["projects"][0]["package_status"] == "approved"
        owner.post(f"{path}/package/simulate", json={"expected_package_id": package["package_id"]})
        assert owner.get("/api/v1/products").json()["projects"][0]["package_status"] == "simulated"


def test_refresh_after_service_restart_reads_saved_projects_and_pending_work(summary_api, svc, monkeypatch):
    monkeypatch.setattr(svc.products, "_dispatch", lambda _: None)
    restarted = None
    try:
        with TestClient(summary_api.app) as owner, TestClient(summary_api.app) as other:
            p = owner.post("/api/v1/products", json={"demo_id": "engine"}).json()
            path = f"/api/v1/products/{p['project_id']}"
            owner.patch(f"{path}/parts", json={"parts": p["parts"], "confirm": True})
            owner.post(f"{path}/investigations", json={"mode": "demo"})
            before = owner.get("/api/v1/products").json()
            detail_before = owner.get(path).json()
            restarted = Services(db_url=str(svc.store.engine.url), start_worker=False)
            monkeypatch.setattr(summary_api, "SERVICES", restarted)
            assert owner.get("/api/v1/products").json() == before
            row = before["projects"][0]
            assert row["status"] == "investigating" and row["active_research_count"] == 3
            assert other.get("/api/v1/products").json() == {"projects": []}
            assert owner.get(path).json() == detail_before
    finally:
        if restarted:
            restarted.stop()
