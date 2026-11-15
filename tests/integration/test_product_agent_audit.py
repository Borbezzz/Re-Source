"""Independent RFQ grounding, mandate, stale-work and demo-dispatch regressions."""
from __future__ import annotations

import copy
import importlib
import json
from concurrent.futures import ThreadPoolExecutor
from contextlib import nullcontext
from types import SimpleNamespace

import pytest
from fastapi.testclient import TestClient
from recovery.config import settings
from recovery.domain.errors import DomainError
from recovery.runtime.context import visitor_id
from recovery.services.product_grounding import grounded_part_issues


def _field_quote(key, value):
    return json.dumps({key: value}, ensure_ascii=False)[1:-1]


def _grounded_fixture():
    row = {"name": "Drive shaft", "quantity": 2, "part_number": "SHAFT-10", "requirements": {"material": "Steel", "diameter": "8 mm"}}
    project = {"_documents": {"spec": {"kind": "requirements", "text": json.dumps({"parts": [row]}, indent=2, ensure_ascii=False)}}}
    ref = lambda quote: {"document_id": "spec", "quote": quote}
    part = {"part_id": "shaft", "name": row["name"], "quantity": row["quantity"], "part_number": row["part_number"],
            "identity_source": ref(_field_quote("name", row["name"])), "quantity_source": ref(_field_quote("quantity", row["quantity"])),
            "part_number_source": ref(_field_quote("part_number", row["part_number"])),
            "requirements": [{"key": "material", "label": "Material", "value": "Steel", "source": ref("Steel")},
                             {"key": "diameter", "label": "Diameter", "value": "8", "unit": "mm", "source": ref("8 mm")}]}
    return project, part


def test_exact_custom_bom_is_grounded_without_mutating_or_claiming_compliance():
    project, part = _grounded_fixture()
    before = copy.deepcopy((project, part))
    assert grounded_part_issues(project, [part]) == []
    assert (project, part) == before


@pytest.mark.parametrize("field", ["identity_source", "quantity_source", "part_number_source"])
def test_agent_requires_independent_identity_quantity_and_asserted_number_provenance(field):
    project, part = _grounded_fixture()
    part[field] = None
    issues = grounded_part_issues(project, [part])
    assert issues and any(i["code"] == "source_required" for i in issues)
    assert all(i["part_ids"] == ["shaft"] for i in issues)


def test_schema_default_quantity_cannot_become_an_asserted_order_count():
    project, part = _grounded_fixture()
    body = json.loads(project["_documents"]["spec"]["text"])
    body["parts"][0].pop("quantity")
    project["_documents"]["spec"]["text"] = json.dumps(body)
    part.update(quantity=1, quantity_source=None)
    assert any(i["code"] == "source_required" and "quantity" in i["message"] for i in grounded_part_issues(project, [part]))


def test_a_number_somewhere_in_document_is_not_an_explicit_quantity_field():
    project, part = _grounded_fixture()
    part["quantity_source"]["quote"] = "2"
    assert any(i["code"] == "quantity_required" for i in grounded_part_issues(project, [part]))


def test_cropped_quote_cannot_turn_a_larger_count_into_a_supported_quantity():
    project, part = _grounded_fixture()
    project["_documents"]["spec"]["text"] = "Drive shaft\nQty: 20\nPart number: SHAFT-10\nSteel\n8 mm"
    part["identity_source"]["quote"] = "Drive shaft"
    part["quantity_source"]["quote"] = "Qty: 2"
    part["part_number_source"]["quote"] = "Part number: SHAFT-10"
    assert any(i["code"] == "source_unverifiable" and "quantity" in i["message"] for i in grounded_part_issues(project, [part]))


def test_drawing_id_is_not_accepted_as_an_oem_part_number():
    project, part = _grounded_fixture()
    body = json.loads(project["_documents"]["spec"]["text"])
    row = body["parts"][0]
    row["drawing_number"] = row.pop("part_number")
    project["_documents"]["spec"]["text"] = json.dumps(body)
    part["part_number_source"]["quote"] = _field_quote("drawing_number", part["part_number"])
    assert any(i["code"] == "part_number_unverified" for i in grounded_part_issues(project, [part]))


@pytest.mark.parametrize("quote", ["18 mm", "8 in"])
def test_source_grounding_requires_complete_dimensions_and_matching_units(quote):
    project, part = _grounded_fixture()
    project["_documents"]["spec"]["text"] = project["_documents"]["spec"]["text"].replace("8 mm", quote)
    part["requirements"][1]["source"]["quote"] = quote
    assert any(i["code"] == "source_value_mismatch" for i in grounded_part_issues(project, [part]))


@pytest.mark.parametrize("kind", ["missing", "model"])
def test_agent_cannot_borrow_inaccessible_or_geometry_only_sources(kind):
    project, part = _grounded_fixture()
    if kind == "missing":
        part["identity_source"]["document_id"] = "another-visitors-document"
    else:
        project["_documents"]["spec"]["kind"] = "model"
    assert any(i["code"] == "source_unverifiable" for i in grounded_part_issues(project, [part]))


def test_explicit_conflicting_source_values_stop_even_if_second_part_was_not_proposed():
    project, part = _grounded_fixture()
    body = json.loads(project["_documents"]["spec"]["text"])
    body["parts"][0]["requirements"]["material"] = "Aluminum"
    project["_documents"]["conflicting-spec"] = {"kind": "requirements", "text": json.dumps(body)}
    assert any(i["code"] == "specification_conflict" and "material" in i["message"] for i in grounded_part_issues(project, [part]))


def test_unrelated_part_source_values_do_not_create_speculative_conflicts():
    project, part = _grounded_fixture()
    other = {"name": "Enclosure", "quantity": 4, "part_number": "BOX-20", "requirements": {"material": "Aluminum"}}
    project["_documents"]["other-spec"] = {"kind": "requirements", "text": json.dumps({"parts": [other]})}
    assert grounded_part_issues(project, [part]) == []


def test_cited_quantity_and_requirement_cannot_come_from_another_bom_row():
    project, part = _grounded_fixture()
    body = json.loads(project["_documents"]["spec"]["text"])
    body["parts"].append({"name": "Enclosure", "quantity": 9, "part_number": "BOX-20", "requirements": {"finish": "Anodized"}})
    project["_documents"]["spec"]["text"] = json.dumps(body)
    part.update(quantity=9, quantity_source={"document_id": "spec", "quote": _field_quote("quantity", 9)})
    part["requirements"].append({"key": "finish", "value": "Anodized", "source": {"document_id": "spec", "quote": "Anodized"}})
    issues = grounded_part_issues(project, [part])
    assert any(i["code"] == "source_scope_mismatch" and "quantity" in i["message"] for i in issues)
    assert any(i["code"] == "source_scope_mismatch" and "finish" in i["message"] for i in issues)


def test_duplicate_conflicting_requirement_fields_are_actionable():
    project, part = _grounded_fixture()
    part["requirements"].append(copy.deepcopy(part["requirements"][0]))
    assert any(i["code"] == "specification_conflict" for i in grounded_part_issues(project, [part]))


@pytest.fixture
def deliveries(svc, monkeypatch):
    queued = []
    monkeypatch.setattr(svc.products, "_dispatch", queued.append)
    monkeypatch.setattr(svc.jobs, "lock", lambda _: nullcontext())
    return queued


def _drain(svc, queued):
    for _ in range(100):
        if not queued:
            return
        svc.jobs.execute(queued.pop(0))
    raise AssertionError("Agent continuations did not settle in 100 deliveries")


def _start_demo(svc):
    p = svc.products.create("desk-lamp")
    return svc.products.agent_start(p["project_id"], p["version"], "demo"), p["version"]


def test_single_mandate_finishes_demo_rfq_without_claiming_purchase_or_verified_suppliers(svc, deliveries):
    started, version = _start_demo(svc)
    pid = started["project_id"]
    _drain(svc, deliveries)
    result = svc.products.get(pid)
    assert result["agent"]["status"] == "recommendation_ready"
    assert result["agent"]["mandate"] == {"objective": "source_and_request_quotes", "outreach": "demo_mailbox", "purchase_authorized": False}
    assert all(p["confirmation_origin"] == "agent_grounded" for p in result["parts"])
    assert result["package"]["status"] == "draft" and result["package"]["approved_at"] is None
    assert result["package"]["receipt"] is None
    assert result["agent"]["sent_count"] == result["agent"]["reply_count"] == len(result["parts"])
    assert len(result["mailbox"]) == 2 * len(result["parts"])
    assert all(m["delivery"] == "simulated" and m["data_origin"] == "synthetic_demo" for m in result["mailbox"])
    assert all("SIMULATED" in m["body"] and m["intended_supplier"] for m in result["mailbox"])
    assert all(m["to_label"] != m["intended_supplier"] for m in result["mailbox"])
    assert all(c["eligibility"] == "unverified" for r in result["research"] for c in r["candidates"])
    # Recover a lost start response after completion without opening another run.
    replay = svc.products.agent_start(pid, version, "demo")
    assert replay["agent"]["run_id"] == started["agent"]["run_id"]
    assert replay["mailbox"] == result["mailbox"] and deliveries == []


def test_concurrent_final_continuations_and_duplicate_deliveries_publish_one_message_pair(svc, deliveries):
    started, _ = _start_demo(svc)
    pid, agent = started["project_id"], started["agent"]
    svc.jobs.execute(deliveries.pop(0))  # Requirements checked; research fan-out committed.
    research = list(deliveries)
    deliveries.clear()
    for jid in research:
        svc.jobs.execute(jid)
        svc.jobs.execute(jid)  # Same queue delivery twice.
    with ThreadPoolExecutor(max_workers=2) as pool:
        futures = [pool.submit(svc.products.run_agent, pid, agent["run_id"], agent["input_version"], f"race:{i}") for i in range(2)]
        for future in futures:
            future.result(timeout=20)
    _drain(svc, deliveries)
    result = svc.products.get(pid)
    ids = [m["message_id"] for m in result["mailbox"]]
    assert len(ids) == len(set(ids)) == 2 * len(result["parts"])


def test_partial_failure_resume_sends_only_new_quotes_under_same_mandate(svc, deliveries):
    started, _ = _start_demo(svc)
    pid = started["project_id"]
    svc.jobs.execute(deliveries.pop(0))
    failed_id = deliveries.pop(0)
    failed_job = svc.store.kv_get(f"job:{failed_id}")
    part_id = failed_job["payload"]["part_id"]
    with svc.products._mutate(pid) as p:
        record = next(r for r in p["research"] if r["part_id"] == part_id)
        record.update(status="failed", stage="failed", error="Injected provider outage")
        svc.products._queue_agent_continuation(p, f"research:{failed_id}")
    svc.store.kv_set(f"job:{failed_id}", {**failed_job, "status": "done"})
    _drain(svc, deliveries)
    partial = svc.products.get(pid)
    assert partial["agent"]["status"] == "needs_attention"
    old_ids = {m["message_id"] for m in partial["mailbox"]}
    assert len(old_ids) == 2 * (len(partial["parts"]) - 1)
    svc.products.agent_resume(pid, partial["agent"]["run_id"], partial["version"])
    _drain(svc, deliveries)
    result = svc.products.get(pid)
    new_ids = [m["message_id"] for m in result["mailbox"]]
    assert result["agent"]["run_id"] == partial["agent"]["run_id"]
    assert result["agent"]["status"] == "recommendation_ready"
    assert old_ids < set(new_ids) and len(new_ids) == len(set(new_ids)) == 2 * len(result["parts"])


def test_source_edit_invalidates_queued_agent_and_cannot_resume_old_input(svc, deliveries):
    started, _ = _start_demo(svc)
    pid, run = started["project_id"], started["agent"]["run_id"]
    svc.jobs.execute(deliveries.pop(0))
    p = svc.products.get(pid)
    parts = p["parts"]
    parts[0]["quantity"] += 1
    svc.products.review(pid, parts, True, p["version"])
    _drain(svc, deliveries)
    changed = svc.products.get(pid)
    assert changed["agent"]["status"] == "needs_attention" and changed["mailbox"] == []
    assert changed["agent"]["input_version"] != changed["input_version"]
    with pytest.raises(DomainError) as error:
        svc.products.agent_resume(pid, run, changed["version"])
    assert error.value.code == "AGENT_INPUTS_CHANGED"


def test_pause_allows_inflight_research_to_finish_but_blocks_quote_publication(svc, deliveries):
    started, _ = _start_demo(svc)
    pid = started["project_id"]
    svc.jobs.execute(deliveries.pop(0))
    # A pause from the currently visible run must still work after progress events.
    svc.products.agent_pause(pid, started["agent"]["run_id"], started["version"])
    _drain(svc, deliveries)
    paused = svc.products.get(pid)
    assert paused["agent"]["status"] == "paused" and paused["mailbox"] == []
    assert all(r["status"] == "complete" for r in paused["research"])
    svc.products.agent_resume(pid, paused["agent"]["run_id"], paused["version"])
    _drain(svc, deliveries)
    assert svc.products.get(pid)["agent"]["status"] == "recommendation_ready"


def test_new_unresolved_source_cannot_be_ignored_by_prepared_defaults(svc, deliveries):
    project = svc.products.create("desk-lamp")
    pid = project["project_id"]
    project = svc.products.upload(pid, b"Replacement specifications: the frame is aluminum rather than the previous steel. Quantity is not provided.", "changed-design.txt", "requirements")
    svc.products.agent_start(pid, project["version"], "demo")
    _drain(svc, deliveries)
    result = svc.products.get(pid)
    assert result["agent"]["status"] == "needs_attention"
    assert result["mailbox"] == [] and result["research"] == []


@pytest.mark.parametrize("quantity", [2, None])
def test_custom_bom_agent_checks_explicit_quantity_and_only_drafts_live_outreach(svc, deliveries, monkeypatch, quantity):
    module = importlib.import_module("recovery.services.product_workers")
    monkeypatch.setattr(svc, "model", SimpleNamespace(available=False, structured=lambda *args, **kwargs: None))
    monkeypatch.setattr(module, "linkup", SimpleNamespace(available=True, search=lambda *args, **kwargs: {
        "ok": True, "results": [{"url": "https://supplier.example/shafts", "title": "Shaft supplier", "snippet": "Drive shaft components in Steel, diameter 8 mm."}]}))
    row = {"name": "Drive shaft", "part_number": "SHAFT-10", "requirements": {"material": "Steel", "diameter": "8 mm"}}
    if quantity is not None:
        row["quantity"] = quantity
    pid = svc.products.create(name="Custom shafts")["project_id"]
    p = svc.products.upload(pid, json.dumps({"parts": [row]}).encode(), "shafts.json", "requirements")
    svc.products.agent_start(pid, p["version"], "live")
    _drain(svc, deliveries)
    result = svc.products.get(pid)
    assert result["mailbox"] == [] and result["agent"]["mandate"]["outreach"] == "draft_only"
    if quantity is None:
        assert result["agent"]["status"] == "needs_attention" and not result["research"]
        assert any("quantity" in item["message"].lower() for item in result["agent"]["attention"])
        assert result["parts"][0]["confirmation_origin"] is None
    else:
        assert result["parts"][0]["confirmation_origin"] == "agent_grounded"
        assert result["research"][0]["status"] == "complete" and result["package"]["status"] == "draft"
        assert result["agent"]["status"] == "needs_attention"
        assert all(t["readiness"] == "contact_required" for t in result["agent"]["targets"])
        assert any(item["code"] == "contact_required" for item in result["agent"]["attention"])


@pytest.mark.parametrize("problem", ["identity_missing", "conflicting_material"])
def test_missing_identity_or_direct_source_conflict_stops_before_research(svc, deliveries, problem):
    row = {"name": "Drive shaft", "quantity": 2, "part_number": "SHAFT-10", "requirements": {"material": "Steel"}}
    if problem == "identity_missing":
        row.pop("name")
    pid = svc.products.create(name="Ambiguous design")["project_id"]
    p = svc.products.upload(pid, json.dumps({"parts": [row]}).encode(), "first.json", "requirements")
    if problem == "conflicting_material":
        row["requirements"]["material"] = "Aluminum"
        p = svc.products.upload(pid, json.dumps({"parts": [row]}).encode(), "second.json", "requirements")
    svc.products.agent_start(pid, p["version"], "live")
    _drain(svc, deliveries)
    result = svc.products.get(pid)
    assert result["agent"]["status"] == "needs_attention"
    assert not result["research"] and not result["mailbox"]
    if problem == "conflicting_material":
        assert any(i["code"] == "specification_conflict" for i in result["agent"]["attention"])


def test_agent_run_and_mailbox_remain_owner_scoped_even_when_ids_are_known(svc, deliveries):
    token = visitor_id.set("audit-owner")
    try:
        started, _ = _start_demo(svc)
        _drain(svc, deliveries)
        pid, agent = started["project_id"], started["agent"]
        visitor_id.set("different-visitor")
        for work in (lambda: svc.products.get(pid), lambda: svc.products.agent_start(pid, started["version"], "demo"),
                     lambda: svc.products.agent_pause(pid, agent["run_id"], started["version"]),
                     lambda: svc.products.agent_resume(pid, agent["run_id"], started["version"]),
                     lambda: svc.products.run_agent(pid, agent["run_id"], agent["input_version"])):
            with pytest.raises(DomainError) as error:
                work()
            assert error.value.status == 404
        assert svc.products.list_projects()["projects"] == []
    finally:
        visitor_id.reset(token)


def test_agent_api_replays_mandate_and_rejects_external_recipient_or_purchase_fields(svc, deliveries, monkeypatch):
    api = importlib.import_module("recovery.api.app")
    monkeypatch.setattr(api, "SERVICES", svc)
    before = settings.public_demo
    object.__setattr__(settings, "public_demo", True)
    try:
        with TestClient(api.app) as owner, TestClient(api.app) as other:
            p = owner.post("/api/v1/products", json={"demo_id": "desk-lamp"}).json()
            path = f"/api/v1/products/{p['project_id']}/agent/start"
            body = {"expected_version": p["version"], "mode": "demo"}
            assert owner.post(path, json={**body, "recipient": "outside@example.com", "purchase_authorized": True}).status_code == 422
            first = owner.post(path, json=body, headers={"Idempotency-Key": "one-mandate"})
            replay = owner.post(path, json=body, headers={"Idempotency-Key": "one-mandate"})
            assert first.status_code == replay.status_code == 202
            assert first.json()["agent"]["run_id"] == replay.json()["agent"]["run_id"] and len(deliveries) == 1
            assert other.post(path, json=body, headers={"Idempotency-Key": "one-mandate"}).status_code == 404
            _drain(svc, deliveries)
            assert other.get(f"/api/v1/products/{p['project_id']}").status_code == 404
            finished = owner.get(f"/api/v1/products/{p['project_id']}").json()
            assert finished["agent"]["status"] == "recommendation_ready"
    finally:
        object.__setattr__(settings, "public_demo", before)


def test_completed_research_retries_unpublished_continuation_without_an_open_browser(svc, monkeypatch):
    jobs_module = importlib.import_module("recovery.runtime.jobs")
    sent, fail = [], {"continuation": False}

    def publish(_topic, message, **kwargs):
        if fail["continuation"] and message.job_id.startswith("agent-"):
            raise RuntimeError("Injected queue publish outage")
        sent.append(message.job_id)

    monkeypatch.setattr(jobs_module, "send", publish)
    monkeypatch.setattr(svc.jobs, "lock", lambda _: nullcontext())
    prior_backend = settings.job_backend
    object.__setattr__(settings, "job_backend", "vercel")
    try:
        started, _ = _start_demo(svc)
        svc.jobs.execute(sent[0])
        research_id = next(jid for jid in sent if jid.startswith("research-product-"))
        fail["continuation"] = True
        with pytest.raises(RuntimeError, match="publish outage"):
            svc.jobs.execute(research_id)
        assert svc.store.kv_get(f"job:{research_id}")["status"] == "pending"
        p = svc.products.get(started["project_id"])
        assert any(r["job_id"] == research_id and r["status"] == "complete" for r in p["research"])
        successful_sends = len(sent)
        fail["continuation"] = False
        svc.jobs.execute(research_id)
        assert svc.store.kv_get(f"job:{research_id}")["status"] == "done"
        assert len(sent) == successful_sends + 1
        continuation_id = sent[-1]
        assert continuation_id.startswith("agent-")
        svc.jobs.execute(research_id)
        assert sent.count(continuation_id) == 1
    finally:
        object.__setattr__(settings, "job_backend", prior_backend)
