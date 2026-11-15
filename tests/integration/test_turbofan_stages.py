"""Every prepared engine stage uses real jobs, scoped demo offers and simulated fulfilment."""


def test_all_turbofan_stage_cases_research_and_new_stage_can_complete_demo(svc, monkeypatch):
    jobs = []
    monkeypatch.setattr(svc.products, "_dispatch", jobs.append)
    project = svc.products.create("turbofan")
    pid = project["project_id"]
    assert len(project["parts"]) == 35
    assert project["model"]["mapping_status"] == "mapped"
    svc.products.review(pid, project["parts"], True, project["version"])
    svc.products.investigate(pid, mode="demo")
    assert len(jobs) == 35
    for jid in jobs:
        svc.jobs._perform(svc.store.kv_get(f"job:{jid}"))
    result = svc.products.get(pid)
    assert len(result["research"]) == 35
    for research in result["research"]:
        assert research["status"] == "complete"
        assert research["providers_used"] == ["prepared_demo"]
        assert len(research["candidates"]) >= 7
        assert all(c["data_origin"] == "synthetic_demo" for c in research["candidates"])
        assert {c["country"] for c in research["candidates"]} >= {"Canada", "Singapore", "Poland"}
        assert all(c["part_id"] == research["part_id"] for c in research["candidates"])
    stage = next(r for r in result["research"] if r["part_id"] == "rs-tf-cp-rotor-03")
    svc.products.select_candidate(pid, stage["part_id"], stage["candidates"][0]["candidate_id"])
    package = svc.products.build_package(pid)["package"]
    assert len(package["items"]) == 1
    assert "fictional" in package["items"][0]["rfq_text"].lower()
    svc.products.approve_package(pid, True, package["package_id"])
    completed = svc.products.simulate_package(pid, package["package_id"])
    assert completed["package"]["status"] == "simulated"
    assert completed["package"]["approval_scope"] == "simulation_only"
