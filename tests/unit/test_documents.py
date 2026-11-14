"""FR-13 / AC-10 / AC-11 / AC-22: applicable package planning, autofill provenance, readiness, versioned
review and the simulated submission adapter (duplicate, stale and barrier handling)."""

from __future__ import annotations

import copy
from datetime import datetime, timezone
from types import SimpleNamespace

import pytest

from recovery.adapters import store as st
from recovery.adapters.store import OperationalStore
from recovery.domain import documents as D
from recovery.domain import rules as R
from recovery.domain.catalog import load_catalog
from recovery.domain.errors import DomainError
from recovery.domain.extraction import FIELD_SCHEMAS, coerce, parse_structured_form
from recovery.domain.scheduler import build_plan, exposure_for
from recovery.runtime.events import EventBus
from recovery.services.documents import DocumentService

NOW = datetime(2026, 11, 16, 8, 0, tzinfo=timezone.utc)


@pytest.fixture(scope="module")
def cat():
    return load_catalog()


def _facts(vids, cat):
    out = {}
    for vid in vids:
        ev = cat.evidence[vid]
        parsed = parse_structured_form(ev["content_text"])
        fm = {}
        for fld, typ in FIELD_SCHEMAS[ev["doc_type"]].items():
            if fld in parsed:
                raw, line = parsed[fld]
                val, state, note = coerce(typ, raw)
                fm[fld] = {"fact_id": f"fact:{vid}:{fld}", "evidence_version_id": vid, "field": fld, "typed_value": val,
                           "original_value": raw, "locator": {"line": line}, "validation_state": state, "validation_note": note}
        out[vid] = fm
    return out


def make_decision(cat, case_id, cids, label="D1"):
    comp = cat.component_for_case(case_id)
    req_set = cat.requirement_sets[comp["requirement_set_id"]]
    candidates, checks, facts, cand_ev = [], [], {}, {}
    for cid in cids:
        offer = cat.offers[cid]
        site, route = cat.sites[offer["site_id"]], cat.routes[offer["logistics_route_id"]]
        vids = list(offer["evidence_ids"])
        f = _facts(vids, cat)
        facts.update(f)
        cand_ev[cid] = vids
        ctx = R.CandidateContext(case_id=case_id, offer=offer, site=site, supplier=cat.suppliers[offer["supplier_id"]], route=route,
                                 component=comp, docs=[dict(cat.evidence[v]) for v in vids], facts=f, now=NOW, signals=[],
                                 applicability=cat.applicability, requirement_set=req_set)
        cand_checks = []
        for req in cat.requirements_for(comp["requirement_set_id"]):
            if offer["route"] not in req["routes"]:
                continue
            out = R.evaluate(ctx, req)
            cand_checks.append({"check_id": f"chk-{cid}-{req['requirement_id']}", "case_id": case_id, "candidate_id": cid,
                                "requirement_id": req["requirement_id"], "template_code": req["template_code"], "mandatory": req["mandatory"],
                                "requirement_title": req["title"], "result": out.result, "explanation": out.explanation,
                                "evidence_refs": out.evidence_refs, "fact_refs": out.fact_refs, "feasible_if_unknown": out.feasible_if_unknown})
        checks += cand_checks
        elig, feasible = R.eligibility_from(cand_checks)
        candidates.append({"candidate": offer, "eligibility": elig, "feasible": feasible, "rank": None, "score": None,
                           "plan": build_plan(offer, cat.plans[cid], route, site, [], cat.fx), "check_ids": [c["check_id"] for c in cand_checks],
                           "gaps": [], "reliability": [m for m in cat.metrics if m["site_id"] == site["site_id"]],
                           "exposure": exposure_for(route, site, []), "evidence_coverage": {}, "supplier": cat.suppliers[offer["supplier_id"]],
                           "site": site, "summary": ""})
    return {"decision_id": f"dec-{label.lower()}-{case_id}", "label": label, "case_id": case_id, "scenario_run_id": "run-test",
            "case_revision": 3, "input_revision": 1, "generation_id": "gen-1", "candidates": candidates, "checks": checks,
            "evidence_set_id": "evset-test", "evidence_hash": "sha256:test", "preferred_candidate_id": cids[0],
            "facts": facts, "candidate_evidence": cand_ev}


def fields_by_id(fields):
    return {f["field_id"]: f for f in fields}


# ------------------------------------------------------------------------------------------- pure functions
def test_buy_package_rule_and_templates(cat):
    dec = make_decision(cat, "case-primary", ["OFF-PB"])
    plan = D.plan_package(dec, "OFF-PB", cat)
    assert plan["rule"]["rule_id"] == "APP-BUY-RELEASED"
    assert [t["template"]["template_id"] for t in plan["templates"]] == ["TPL-CAA-FORM1-MO", "TPL-COMPONENT-ACCEPTANCE", "TPL-SUPPLIER-APPROVAL"]
    assert plan["destination_type"] == "internal_quality_records" and plan["authority_application"] is False
    assert all("APP-BUY-RELEASED" in t["why_included"] for t in plan["templates"])


def test_decision_derived_applicability_matches_rules_engine(cat):
    for case_id, cid in [("case-primary", "OFF-PB"), ("case-secondary-b", "OFF-SB3"), ("case-secondary-b", "OFF-SB2")]:
        dec = make_decision(cat, case_id, [cid])
        offer = cat.offers[cid]
        comp = cat.component_for_case(case_id)
        ctx = R.CandidateContext(case_id=case_id, offer=offer, site=cat.sites[offer["site_id"]], supplier=cat.suppliers[offer["supplier_id"]],
                                 route=cat.routes[offer["logistics_route_id"]], component=comp,
                                 docs=[dict(cat.evidence[v]) for v in offer["evidence_ids"]], facts=dec["facts"], now=NOW, signals=[],
                                 applicability=cat.applicability, requirement_set=cat.requirement_sets[comp["requirement_set_id"]])
        assert D.plan_package(dec, cid, cat, ctx)["rule"]["rule_id"] == D.plan_package(dec, cid, cat)["rule"]["rule_id"]


def test_form1_mo_autofill_values_and_provenance(cat):
    dec = make_decision(cat, "case-primary", ["OFF-PB"])
    tpl = cat.templates["TPL-CAA-FORM1-MO"]
    fields = fields_by_id(D.autofill(tpl, dec, "OFF-PB", D.case_info_for("case-primary", cat), cat, cat.scenario["operator"]))
    assert fields["b8"]["value"] == "RS-FN-1001"
    assert fields["b10"]["value"] == "FN8102"
    assert fields["b11"]["value"] == "INSPECTED/TESTED"
    assert fields["b4a"]["value"] == "UK.145.90012 (synthetic)"
    assert fields["b8"]["provenance"]["source_fact_ids"] == ["fact:ev-f1-pb:part_number"]
    assert fields["b8"]["provenance"]["evidence_refs"] == ["ev-f1-pb"]
    assert fields["b2"]["provenance"]["origin"] == "computed" and not fields["b2"]["editable"]
    assert fields["ver"]["status"] == "completion_task" and "receiving inspector" in fields["ver"]["responsible"].lower()
    v = D.validate_draft(list(fields.values()))
    assert v["ready"] and len(v["completion_tasks"]) == 1


def test_component_acceptance_checks_and_optional_sb(cat):
    case_info = D.case_info_for("case-primary", cat)
    dec = make_decision(cat, "case-primary", ["OFF-PB"])
    f = fields_by_id(D.autofill(cat.templates["TPL-COMPONENT-ACCEPTANCE"], dec, "OFF-PB", case_info, cat))
    assert f["ic"]["value"].startswith("PASS") and f["ic"]["provenance"]["check_refs"] == ["chk-OFF-PB-REQ-FN-IC-01"]
    assert f["rel"]["provenance"]["check_refs"] == ["chk-OFF-PB-REQ-FN-REL-01"]
    assert f["sb"]["value"] == "RS-SB-73-0042 Rev A reviewed"
    assert f["eta"]["value"] == "Day 6 of recovery plan"
    assert "D1" in f["decision"]["value"]
    # duct has no service bulletin: explicit "none applicable", not a blocking gap; REL_OR_POA picks POA for MAKE
    dec_b = make_decision(cat, "case-secondary-b", ["OFF-SB3"])
    fb = fields_by_id(D.autofill(cat.templates["TPL-COMPONENT-ACCEPTANCE"], dec_b, "OFF-SB3", D.case_info_for("case-secondary-b", cat), cat))
    assert fb["sb"]["value"].startswith("None applicable") and fb["sb"]["status"] == "filled"
    assert fb["rel"]["provenance"]["check_refs"] == ["chk-OFF-SB3-REQ-BD-POA-01"] and fb["rel"]["value"].startswith("PASS")
    assert D.validate_draft(list(fb.values()))["ready"]


def test_make_with_poa_package(cat):
    dec = make_decision(cat, "case-secondary-b", ["OFF-SB3"])
    plan = D.plan_package(dec, "OFF-SB3", cat)
    assert plan["rule"]["rule_id"] == "APP-MAKE-POA"
    assert [t["template"]["template_id"] for t in plan["templates"]] == ["TPL-CAA-FORM1-21", "TPL-FAI-ACCEPTANCE", "TPL-COMPONENT-ACCEPTANCE", "TPL-SUPPLIER-APPROVAL"]
    case_info = D.case_info_for("case-secondary-b", cat)
    f21 = fields_by_id(D.autofill(cat.templates["TPL-CAA-FORM1-21"], dec, "OFF-SB3", case_info, cat))
    assert f21["b4a"]["value"] == "UK.21G.99002 (synthetic)"
    assert f21["b12"]["value"] == "Manufactured to licensed drawing DWG-BD-3110 rev A"
    assert set(f21["b12"]["provenance"]["source_fact_ids"]) == {"fact:ev-dl-sb3:drawing_number", "fact:ev-dl-sb3:drawing_revision"}
    assert f21["b13b"]["status"] == "completion_task"
    sup = fields_by_id(D.autofill(cat.templates["TPL-SUPPLIER-APPROVAL"], dec, "OFF-SB3", case_info, cat))
    assert "scenario fixture" in sup["otd"]["value"] and sup["otd"]["provenance"]["evidence_refs"] == ["ev-metrics-site-kes-brs"]
    assert sup["qms"]["value"].startswith("AS9100D Q-90109")


def test_make_without_poa_authority_branch(cat):
    dec = make_decision(cat, "case-secondary-b", ["OFF-SB2"])
    assert dec["candidates"][0]["eligibility"] == "pending" and dec["candidates"][0]["feasible"] is True
    plan = D.plan_package(dec, "OFF-SB2", cat)
    assert plan["rule"]["rule_id"] == "APP-MAKE-NO-POA" and plan["authority_application"] is True
    assert [t["template"]["template_id"] for t in plan["templates"]] == ["TPL-CAA-FORM-60"]
    assert plan["destination_type"] == "caa_application_simulated"
    f = fields_by_id(D.autofill(cat.templates["TPL-CAA-FORM-60"], dec, "OFF-SB2", D.case_info_for("case-secondary-b", cat), cat))
    assert f["name"]["value"] == "Pennine Precision Components Ltd"
    assert f["design"]["value"] == "DDL-90032 (synthetic)"
    assert f["am"]["status"] == "completion_task"


def test_missing_required_fact_blocks_and_hash_sensitivity(cat):
    dec = make_decision(cat, "case-primary", ["OFF-PB"])
    broken = copy.deepcopy(dec)
    broken["facts"]["ev-f1-pb"]["serial_number"]["validation_state"] = "invalid"
    f = fields_by_id(D.autofill(cat.templates["TPL-CAA-FORM1-MO"], broken, "OFF-PB", D.case_info_for("case-primary", cat), cat))
    assert f["b10"]["status"] == "missing" and f["b10"]["value"] is None
    v = D.validate_draft(list(f.values()))
    assert not v["ready"] and [b["field_id"] for b in v["blocking"]] == ["b10"]
    d1 = {"template_id": "T", "template_version": "1", "fields": [{"field_id": "a", "value": "x"}]}
    d2 = {"template_id": "T", "template_version": "1", "fields": [{"field_id": "a", "value": "y"}]}
    assert D.package_hash([d1]) == D.package_hash([copy.deepcopy(d1)]) != D.package_hash([d2])


# ------------------------------------------------------------------------------------------- service flow
@pytest.fixture()
def svc(tmp_path, cat):
    store = OperationalStore(f"sqlite:///{tmp_path}/op.sqlite3")
    services = SimpleNamespace(store=store, bus=EventBus(store), catalog=cat, run_state=None, model=None)
    run_id, case_id = "run-doc-1", "case-primary"
    store.create_run(dict(run_id=run_id, mode="seeded", fixture_version="seed-v1", manifest_version="engine-demo-001.v1",
                          scenario_now="2026-11-16T08:00:00Z", status="active", replay_source_run_id=None, barrier_count=0, manifest_version_counter=1))
    dec = make_decision(cat, case_id, ["OFF-PA", "OFF-PB"], label="D2")
    sel = {"selection_id": "sel-1", "case_id": case_id, "scenario_run_id": run_id, "candidate_id": "OFF-PB", "decision_id": dec["decision_id"],
           "accepted_case_revision": 5, "evidence_hash": dec["evidence_hash"], "actor": "tester", "accepted_at": "2026-11-16T09:00:00Z",
           "idempotency_key": "k-sel", "status": "current"}
    store.put(st.decisions, dec["decision_id"], run_id, dec, case_id=case_id, status="current", label="D2", generation_id="gen-1", input_revision=1)
    store.put(st.selections, "sel-1", run_id, sel, case_id=case_id, status="current", idem_key="k-sel")
    store.insert_case(dict(run_id=run_id, case_id=case_id, component_id="component-primary", state="selected", revision=5, input_revision=1,
                           mode="seeded", visual_state="exploded", monitoring_status="active", current_decision_id=dec["decision_id"],
                           initial_decision_id=dec["decision_id"], current_selection_id="sel-1", event_seq=0, stale_reasons="[]", decision_labels="{}"))
    return SimpleNamespace(service=DocumentService(services), store=store, run_id=run_id, case_id=case_id)


def _types(t):
    return [e["type"] for e in t.store.events_after(t.run_id, t.case_id, 0)]


def test_generate_review_submit_and_duplicate(svc):
    pkg = svc.service.generate(svc.run_id, svc.case_id, "sel-1")
    assert pkg["status"] == "current" and pkg["version"] == 1 and pkg["destination_type"] == "internal_quality_records"
    case = svc.store.get_case(svc.run_id, svc.case_id)
    assert case["current_package_id"] == pkg["package_id"] and case["state"] == "documents_ready"
    assert _types(svc)[:2] == ["documents.preparing", "documents.ready"]
    # retrying the outbox item returns the same package
    assert svc.service.generate(svc.run_id, svc.case_id, "sel-1")["package_id"] == pkg["package_id"]
    view = svc.service.view(svc.run_id, svc.case_id)
    assert view["generation_status"] == "ready" and len(view["current_drafts"]) == 3 and len(view["templates"]) == 3

    with pytest.raises(DomainError) as e:
        svc.service.submit(svc.run_id, svc.case_id, {"selection_id": "sel-1", "package_id": pkg["package_id"], "package_version": 1})
    assert e.value.code == "PACKAGE_NOT_APPROVED"

    out = svc.service.patch(svc.run_id, pkg["package_id"], {"expected_version": 1, "review_action": "approve", "actor": "qm"})
    assert out["package"]["review_state"] == "approved" and out["package"]["approved_hash"] == out["package"]["package_hash"]
    r1 = svc.service.submit(svc.run_id, svc.case_id, {"selection_id": "sel-1", "package_id": pkg["package_id"], "package_version": 1, "idempotency_key": "a"})
    r2 = svc.service.submit(svc.run_id, svc.case_id, {"selection_id": "sel-1", "package_id": pkg["package_id"], "package_version": 1, "idempotency_key": "b"})
    assert r1["receipt_id"] == r2["receipt_id"] and r1["label"].startswith("SIMULATED")
    assert len(svc.store.find(st.receipts, run_id=svc.run_id)) == 1
    case = svc.store.get_case(svc.run_id, svc.case_id)
    assert case["state"] == "submission_simulated" and case["visual_state"] == "replacement_ready" and case["latest_receipt_id"] == r1["receipt_id"]
    assert svc.store.find(st.outbox, run_id=svc.run_id, op_type="project_receipt")
    html = svc.service.render_package_html(svc.run_id, pkg["package_id"])
    assert "SIMULATED" in html and r1["receipt_id"] in html and "FN8102" in html


def test_edit_creates_new_version_and_resets_approval(svc):
    pkg = svc.service.generate(svc.run_id, svc.case_id, "sel-1")
    svc.service.patch(svc.run_id, pkg["package_id"], {"expected_version": 1, "review_action": "approve"})
    form1 = next(d for d in svc.service.view(svc.run_id, svc.case_id)["current_drafts"] if d["template_id"] == "TPL-CAA-FORM1-MO")
    out = svc.service.patch(svc.run_id, form1["draft_id"], {"expected_version": 1, "field_edits": {"ver": "J. Inspector"}, "actor": "inspector-1"})
    new_pkg = out["package"]
    assert new_pkg["version"] == 2 and new_pkg["review_state"] == "draft" and new_pkg["approved_hash"] is None
    assert new_pkg["package_hash"] != pkg["package_hash"]
    edited = next(d for d in out["drafts"] if d["template_id"] == "TPL-CAA-FORM1-MO")
    ver = next(f for f in edited["fields"] if f["field_id"] == "ver")
    assert ver["value"] == "J. Inspector" and ver["provenance"]["origin"] == "user_edit" and ver["provenance"]["edited_by"] == "inspector-1"
    assert edited["version"] == 2
    assert svc.store.get(st.drafts, form1["draft_id"])["status"] == "superseded"
    with pytest.raises(DomainError) as e:  # stale UI still on version 1
        svc.service.patch(svc.run_id, pkg["package_id"], {"expected_version": 1, "review_action": "approve"})
    assert e.value.code == "PACKAGE_STALE"
    with pytest.raises(DomainError) as e:
        svc.service.patch(svc.run_id, new_pkg["package_id"], {"expected_version": 1, "review_action": "approve"})
    assert e.value.code == "VERSION_CONFLICT"
    with pytest.raises(DomainError) as e:  # non-editable constant field
        svc.service.patch(svc.run_id, new_pkg["package_id"], {"expected_version": 2, "field_edits": {"TPL-CAA-FORM1-MO.b2": "X"}})
    assert e.value.status == 422
    with pytest.raises(DomainError) as e:  # submitting the old approved version is rejected
        svc.service.submit(svc.run_id, svc.case_id, {"selection_id": "sel-1", "package_id": pkg["package_id"], "package_version": 1})
    assert e.value.code == "PACKAGE_STALE"


def test_barrier_and_stale_block_submission_and_publication(svc):
    pkg = svc.service.generate(svc.run_id, svc.case_id, "sel-1")
    svc.service.patch(svc.run_id, pkg["package_id"], {"expected_version": 1, "review_action": "approve"})
    svc.store.update_run(svc.run_id, barrier_count=1)
    with pytest.raises(DomainError) as e:
        svc.service.submit(svc.run_id, svc.case_id, {"selection_id": "sel-1", "package_id": pkg["package_id"], "package_version": 1})
    assert e.value.code == "BARRIER_ACTIVE" and e.value.retryable
    svc.store.update_run(svc.run_id, barrier_count=0)
    with svc.store.tx() as c:
        ids = svc.service.mark_stale(c, svc.run_id, svc.case_id, "SB Rev B supersedes evidence")
    assert pkg["package_id"] in ids and len(ids) == 4
    assert svc.store.get_case(svc.run_id, svc.case_id)["state"] == "documents_stale"
    assert "documents.stale" in _types(svc)
    with pytest.raises(DomainError) as e:
        svc.service.submit(svc.run_id, svc.case_id, {"selection_id": "sel-1", "package_id": pkg["package_id"], "package_version": 1})
    assert e.value.code == "PACKAGE_STALE"
    assert svc.service.view(svc.run_id, svc.case_id)["generation_status"] == "stale"


def test_generation_superseded_when_barrier_appears(svc, monkeypatch):
    original = svc.service.build_drafts

    def slow_build(*a, **kw):  # a change registers while the generator is working
        out = original(*a, **kw)
        svc.store.update_run(svc.run_id, barrier_count=1)
        return out

    monkeypatch.setattr(svc.service, "build_drafts", slow_build)
    pkg = svc.service.generate(svc.run_id, svc.case_id, "sel-1")
    assert pkg["status"] == "superseded"
    case = svc.store.get_case(svc.run_id, svc.case_id)
    assert case["current_package_id"] is None and "documents.ready" not in _types(svc)


def test_stale_selection_rejected(svc):
    pkg = svc.service.generate(svc.run_id, svc.case_id, "sel-1")
    svc.service.patch(svc.run_id, pkg["package_id"], {"expected_version": 1, "review_action": "approve"})
    svc.store.set_status(st.selections, "sel-1", "stale")
    with pytest.raises(DomainError) as e:
        svc.service.submit(svc.run_id, svc.case_id, {"selection_id": "sel-1", "package_id": pkg["package_id"], "package_version": 1})
    assert e.value.code == "STALE_DECISION" and e.value.status == 409
