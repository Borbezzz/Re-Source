"""Supplier findings are attributable, scoped and replayable without invented coordinates."""

from recovery.domain.models import SupplierDiscoveryEvent
from recovery.services.batches import BatchService


def test_supplier_findings_preserve_component_evidence_and_replay(svc):
    run = svc.scenario.create_run()["scenario_run_id"]
    request = {"assembly_id": svc.catalog.engine["engine_id"],
               "component_ids": ["component-primary", "component-secondary-a"], "mode": "seeded"}
    batch, _ = BatchService(svc).create(run, request, "finding-events")
    assert svc.coordinator.wait_idle(60)
    for part in batch["components"]:
        events = svc.store.events_after(run, part["case_id"], 0, 5000)
        findings = [event for event in events if event["type"] == "supplier.discovered"]
        assert findings
        for event in findings:
            finding = SupplierDiscoveryEvent.model_validate(event)
            offer = svc.catalog.offers[finding.data.candidate_id]
            site = svc.catalog.sites[offer["site_id"]]
            assert finding.invocation_id == part["generation_id"]
            assert finding.data.component_id == part["component_id"]
            assert offer["case_id"] == part["case_id"]
            assert finding.data.supplier_id == offer["supplier_id"]
            assert finding.data.location.site_id == site["site_id"]
            assert finding.data.location.data_origin.value == "synthetic_demo"
            assert finding.data.location.precision == "representative"
            assert finding.data.location.source == f"fixture:{svc.catalog.fixture_version}/sites.json#{site['site_id']}"
            assert set(finding.evidence_refs) <= {d["version_id"] for d in svc.run_state.candidate_docs(run, offer)}
            assert finding.evidence_refs
        first = findings[0]
        resumed = svc.store.events_after(run, part["case_id"], first["sequence"] - 1, 5000)
        assert resumed[0] == first
        assert all(event["sequence"] > first["sequence"] for event in svc.store.events_after(run, part["case_id"], first["sequence"], 5000))


def test_unattributed_coordinates_are_not_exposed_as_location_findings(svc, monkeypatch):
    run = svc.scenario.create_run()["scenario_run_id"]
    site = svc.catalog.sites["SITE-NVA-RTM"]
    monkeypatch.setitem(site, "data_origin", "public_source")
    request = {"assembly_id": svc.catalog.engine["engine_id"], "component_ids": ["component-primary"], "mode": "seeded"}
    batch, _ = BatchService(svc).create(run, request, "no-fake-precision")
    assert svc.coordinator.wait_idle(60)
    events = svc.store.events_after(run, batch["components"][0]["case_id"], 0, 5000)
    finding = next(e for e in events if e["type"] == "supplier.discovered" and e["data"]["location"]["site_id"] == site["site_id"])
    location = SupplierDiscoveryEvent.model_validate(finding).data.location
    assert location.latitude is None and location.longitude is None
    assert location.precision is None and location.confidence is None and location.source is None
    assert location.data_origin.value == "public_source"


def test_scenario_replay_preserves_typed_supplier_finding(svc, monkeypatch):
    monkeypatch.setitem(svc.catalog.sites["SITE-NVA-RTM"], "data_origin", "public_source")
    source_run = svc.scenario.create_run()["scenario_run_id"]
    request = {"assembly_id": svc.catalog.engine["engine_id"], "component_ids": ["component-primary"], "mode": "seeded"}
    batch, _ = BatchService(svc).create(source_run, request, "source-for-replay")
    assert svc.coordinator.wait_idle(60)
    case_id = batch["components"][0]["case_id"]
    source = next(event for event in svc.store.events_after(source_run, case_id, 0, 5000)
                  if event["type"] == "supplier.discovered" and event["data"]["location"]["site_id"] == "SITE-NVA-RTM")
    target_run = svc.scenario.create_run()["scenario_run_id"]
    monkeypatch.setattr("recovery.services.scenario.time.sleep", lambda _: None)
    svc.scenario._replay(source_run, target_run)
    replayed = next(event for event in svc.store.events_after(target_run, case_id, 0, 5000)
                    if event["type"] == "supplier.discovered" and event["data"].get("replay_of_event") == source["event_id"])
    typed = SupplierDiscoveryEvent.model_validate(replayed)
    assert typed.data.replay is True
    assert typed.data.component_id == source["data"]["component_id"]
    assert typed.data.location.source == source["data"]["location"]["source"]
    assert typed.data_origin.value == "public_source" == typed.data.location.data_origin.value
    assert typed.data.location.latitude is None and typed.data.location.longitude is None
    assert typed.evidence_refs == source["evidence_refs"]
