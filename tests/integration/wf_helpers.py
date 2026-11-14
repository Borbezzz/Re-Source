"""Shared helpers for service-level integration tests."""

from __future__ import annotations


def investigate(s, case_id: str, run_id: str | None = None) -> dict:
    run_id = run_id or s.store.current_run()["run_id"]
    s.coordinator.start_investigation(run_id, case_id, "seeded", None)
    assert s.coordinator.wait_idle(120)
    case = s.store.get_case(run_id, case_id)
    return s.decisions.get(case["current_decision_id"])


def current(s, case_id: str, run_id: str | None = None) -> tuple[dict, dict]:
    run_id = run_id or s.store.current_run()["run_id"]
    case = s.store.get_case(run_id, case_id)
    return case, s.decisions.get(case["current_decision_id"])


def ranked(decision: dict) -> list[str]:
    return [c["candidate"]["candidate_id"] for c in sorted([c for c in decision["candidates"] if c["rank"]], key=lambda c: c["rank"])]


def drain_outbox(s, case_id: str, run_id: str | None = None, want_package: bool = True) -> dict:
    import time

    run_id = run_id or s.store.current_run()["run_id"]
    for _ in range(50):
        s.process_outbox_once()
        case = s.store.get_case(run_id, case_id)
        if not want_package or case["current_package_id"]:
            return case
        time.sleep(0.05)
    raise AssertionError("documents were not generated")


def accept(s, case_id: str, candidate_id: str, key: str = "k", run_id: str | None = None) -> dict:
    run_id = run_id or s.store.current_run()["run_id"]
    case, d = current(s, case_id, run_id)
    return s.selection.accept(run_id, case_id, {"candidate_id": candidate_id, "decision_id": d["decision_id"], "evidence_hash": d["evidence_hash"],
                                                "expected_revision": case["revision"]}, key)


def approve_and_submit(s, case_id: str, run_id: str | None = None) -> dict:
    run_id = run_id or s.store.current_run()["run_id"]
    view = s.documents.view(run_id, case_id)
    pkg = view["current_package"]
    pkg = s.documents.patch(run_id, pkg["package_id"], {"expected_version": pkg["version"], "review_action": "approve"})["package"]
    case = s.store.get_case(run_id, case_id)
    return s.documents.submit(run_id, case_id, {"selection_id": case["current_selection_id"], "package_id": pkg["package_id"],
                                                "package_version": pkg["version"]})
