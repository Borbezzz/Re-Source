"""Task summaries reflect persisted events for the correct generation."""

from recovery.domain.models import TaskStatus


def test_task_summary_accumulates_real_tool_and_evidence_for_its_generation(svc):
    run = svc.scenario.create_run()["scenario_run_id"]
    publish = svc.bus.publish
    publish(run, "case-primary", "task.started", "Research started", {"task": "Research", "status": "running"},
            task_id="research", invocation_id="gen-a")
    publish(run, "case-primary", "tool.started", "Searching catalogue", {"tool": "query_candidate_offers", "call_id": "call-a"},
            task_id="research", invocation_id="gen-a")
    publish(run, "case-primary", "tool.completed", "Found evidence", {"tool": "query_candidate_offers", "call_id": "call-a"},
            task_id="research", invocation_id="gen-a", evidence_refs=["ev-a", "ev-b"])
    publish(run, "case-primary", "evidence.ingested", "Read evidence", {}, task_id="research", invocation_id="gen-a", evidence_refs=["ev-b", "ev-c"])
    publish(run, "case-primary", "tool.failed", "Other generation", {"tool": "other", "call_id": "call-b"},
            task_id="research", invocation_id="gen-b", evidence_refs=["wrong-generation"])
    publish(run, "case-primary", "task.completed", "Research complete", {"task": "Research", "status": "completed"},
            task_id="research", invocation_id="gen-a")
    task = TaskStatus.model_validate(svc.views.tasks(run, "case-primary", "gen-a")[0])
    assert task.status == "completed" and task.name == "Research"
    assert task.latest_tool.name == "query_candidate_offers" and task.latest_tool.status == "completed"
    assert task.latest_tool.call_id == "call-a" and task.latest_tool.summary == "Found evidence"
    assert task.evidence_refs == ["ev-a", "ev-b", "ev-c"]


def test_task_summary_reads_past_first_history_page(svc, monkeypatch):
    calls = []
    page = [{"sequence": index, "type": "case.state_changed", "invocation_id": None, "task_id": None}
            for index in range(1, 5001)]
    final = {"sequence": 5001, "type": "task.completed", "invocation_id": "gen-a", "task_id": "late-task",
             "occurred_at": "2026-11-14T00:00:00Z", "summary": "Finished", "data": {"task": "Late task", "status": "completed"}}

    def events_after(run_id, case_id, after, limit):
        calls.append(after)
        return page if after == 0 else [final] if after == 5000 else []

    monkeypatch.setattr(svc.store, "events_after", events_after)
    result = svc.views.tasks("run", "case", "gen-a")
    assert calls == [0, 5000]
    assert TaskStatus.model_validate(result[0]).task_id == "late-task"
