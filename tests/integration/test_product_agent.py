"""Autonomous product sourcing completes routine work under one bounded mandate."""
import json
from contextlib import nullcontext

import pytest
from recovery.domain.errors import DomainError


def drain(svc, pending):
    executed = []
    while pending:
        assert len(executed) < 80, "Agent scheduling did not converge"
        jid = pending.pop(0)
        svc.jobs.execute(jid)
        executed.append(jid)
    return executed


@pytest.fixture
def agent_jobs(svc, monkeypatch):
    pending = []
    monkeypatch.setattr(svc.products, "_dispatch", pending.append)
    monkeypatch.setattr(svc.jobs, "lock", lambda _: nullcontext())
    return pending


def test_prepared_demo_runs_to_recommendation_without_manual_gates(svc, agent_jobs):
    p = svc.products.create("desk-lamp")
    started = svc.products.agent_start(p["project_id"], p["version"], "demo")
    assert started["agent"]["status"] == "queued"
    drain(svc, agent_jobs)
    result = svc.products.get(p["project_id"])
    assert result["agent"]["status"] == "recommendation_ready", result["agent"]
    assert result["agent"]["mandate"]["purchase_authorized"] is False
    assert result["agent"]["sent_count"] == result["agent"]["reply_count"] == 3
    assert len(result["mailbox"]) == 6
    assert all(part["confirmation_origin"] == "agent_grounded" for part in result["parts"])
    assert result["package"]["status"] == "draft" and result["package"]["receipt"] is None
    assert all(m["delivery"] == "simulated" and m["data_origin"] == "synthetic_demo" for m in result["mailbox"])
    assert all(c["eligibility"] == "unverified" for r in result["research"] for c in r["candidates"])
    summary = svc.products.list_projects()["projects"][0]
    assert summary["agent_status"] == "recommendation_ready" and summary["agent_stage"] == "complete"


def test_grounded_custom_bom_extracts_and_drafts_without_manual_confirmation(svc, agent_jobs, monkeypatch):
    from recovery.adapters.external import LinkupClient, linkup
    monkeypatch.setattr(LinkupClient, "available", property(lambda _: True))
    monkeypatch.setattr(linkup, "search", lambda *args, **kwargs: {"ok": True, "results": [
        {"url": "https://supplier.example/shafts", "title": "Steel shafts", "snippet": "Steel shaft manufacturing. Contact sales for quotations."}]})
    p = svc.products.create(name="Gearbox")
    p = svc.products.upload(p["project_id"], json.dumps({"parts": [{"name": "Drive shaft", "quantity": 2,
        "part_number": "SHAFT-2", "requirements": {"material": "Steel", "diameter": "8 mm"}}]}).encode(), "bom.json", "requirements")
    svc.products.agent_start(p["project_id"], p["version"], "live")
    drain(svc, agent_jobs)
    result = svc.products.get(p["project_id"])
    assert result["parts"][0]["confirmation_origin"] == "agent_grounded", result["agent"]
    assert result["parts"][0]["quantity"] == 2
    assert result["agent"]["status"] == "needs_attention"
    assert any(a["code"] == "contact_required" for a in result["agent"]["attention"])
    assert result["package"]["status"] == "draft"
    assert result["mailbox"] == [] and result["agent"]["sent_count"] == 0


def test_missing_explicit_quantity_is_actionable_not_assumed(svc, agent_jobs):
    p = svc.products.create(name="Quantity missing")
    p = svc.products.upload(p["project_id"], b"Part: Shaft\nMaterial: Steel\n", "spec.txt", "requirements")
    svc.products.agent_start(p["project_id"], p["version"], "live")
    drain(svc, agent_jobs)
    result = svc.products.get(p["project_id"])
    assert result["agent"]["status"] == "needs_attention"
    assert any("quantity" in a["message"].lower() for a in result["agent"]["attention"])
    assert result["parts"][0]["status"] == "proposed"
    assert result["research"] == [] and result["mailbox"] == []


def test_pause_after_progress_then_resume_current_mandate(svc, agent_jobs):
    p = svc.products.create("engine")
    started = svc.products.agent_start(p["project_id"], p["version"], "demo")
    svc.jobs.execute(agent_jobs.pop(0))
    progressed = svc.products.get(p["project_id"])
    assert progressed["version"] > started["version"]
    paused = svc.products.agent_pause(p["project_id"], started["agent"]["run_id"], started["version"])
    assert paused["agent"]["status"] == "paused"
    drain(svc, agent_jobs)
    paused = svc.products.get(p["project_id"])
    assert paused["mailbox"] == []
    svc.products.agent_resume(p["project_id"], paused["agent"]["run_id"], paused["version"])
    drain(svc, agent_jobs)
    assert svc.products.get(p["project_id"])["agent"]["status"] == "recommendation_ready"


def test_duplicate_jobs_and_old_start_retry_cannot_duplicate_mail(svc, agent_jobs):
    p = svc.products.create("engine")
    first = svc.products.agent_start(p["project_id"], p["version"], "demo")
    duplicate = svc.products.agent_start(p["project_id"], p["version"], "demo")
    assert duplicate["agent"]["run_id"] == first["agent"]["run_id"] and len(agent_jobs) == 1
    executed = drain(svc, agent_jobs)
    for jid in executed:
        svc.jobs.execute(jid)
    result = svc.products.get(p["project_id"])
    svc.products.run_agent(p["project_id"], first["agent"]["run_id"], first["input_version"], "duplicate")
    assert svc.products.get(p["project_id"])["mailbox"] == result["mailbox"]
    assert len({m["message_id"] for m in result["mailbox"]}) == 6


def test_changed_inputs_stop_old_run_and_require_new_mandate(svc, agent_jobs):
    p = svc.products.create("engine")
    started = svc.products.agent_start(p["project_id"], p["version"], "demo")
    svc.jobs.execute(agent_jobs.pop(0))
    current = svc.products.get(p["project_id"])
    svc.products.review(p["project_id"], current["parts"], False)
    drain(svc, agent_jobs)
    current = svc.products.get(p["project_id"])
    assert current["agent"]["status"] == "needs_attention" and current["mailbox"] == []
    with pytest.raises(DomainError) as error:
        svc.products.agent_resume(p["project_id"], started["agent"]["run_id"], current["version"])
    assert error.value.code == "AGENT_INPUTS_CHANGED"
