"""Run-history lookup stays tenant-scoped without one database round trip per global run."""

from contextlib import contextmanager

import pytest
from sqlalchemy import event

from recovery.adapters.store import OperationalStore
from recovery.runtime.context import visitor_id


@pytest.fixture
def store(tmp_path):
    instance = OperationalStore(f"sqlite:///{tmp_path}/run-lookup.sqlite3")
    yield instance
    instance.engine.dispose()


@contextmanager
def visitor(identity):
    token = visitor_id.set(identity)
    try:
        yield
    finally:
        visitor_id.reset(token)


def create_run(store, run_id, owner, created_at="2026-11-14T00:00:00Z"):
    with visitor(owner):
        store.create_run({"run_id": run_id, "mode": "seeded", "fixture_version": "seed-v1",
                          "manifest_version": "v1", "scenario_now": "2026-11-14T00:00:00Z",
                          "status": "active"})
        store.update_run(run_id, created_at=created_at)


def counted_history(store):
    statements = []

    def capture(_connection, _cursor, statement, _parameters, _context, _many):
        if statement.lstrip().upper().startswith("SELECT"):
            statements.append(statement)

    event.listen(store.engine, "before_cursor_execute", capture)
    try:
        rows = store.list_runs()
    finally:
        event.remove(store.engine, "before_cursor_execute", capture)
    return rows, len(statements)


def test_history_is_private_and_ordered_without_changing_current_pointers(store):
    create_run(store, "internal", None)
    create_run(store, "a-first", "visitor-a", "2026-11-14T01:00:00Z")
    create_run(store, "b-only", "visitor-b", "2026-11-14T02:00:00Z")
    create_run(store, "a-second", "visitor-a", "2026-11-14T03:00:00Z")
    with visitor("visitor-a"):
        assert [r["run_id"] for r in store.list_runs()] == ["a-second", "a-first"]
        assert store.current_run()["run_id"] == "a-second"
    with visitor("visitor-b"):
        assert [r["run_id"] for r in store.list_runs()] == ["b-only"]
        assert store.current_run()["run_id"] == "b-only"
    with visitor("new-visitor"):
        assert store.list_runs() == []
        assert store.current_run() is None
    # Internal diagnostics and private deployments deliberately have no visitor context.
    with visitor(None):
        assert [r["run_id"] for r in store.list_runs()] == ["a-second", "b-only", "a-first", "internal"]
        assert store.current_run()["run_id"] == "internal"


def test_unrelated_run_growth_does_not_add_queries_or_expose_runs(store):
    create_run(store, "mine", "visitor-a")
    with visitor("visitor-a"):
        before, initial_queries = counted_history(store)
    for number in range(30):
        create_run(store, f"other-{number}", f"visitor-{number}")
    create_run(store, "unowned", None)
    with visitor("visitor-a"):
        after, later_queries = counted_history(store)
    assert [r["run_id"] for r in before] == ["mine"]
    assert after == before
    assert initial_queries == later_queries == 1


def test_owner_matching_uses_the_whole_serialized_identity(store):
    identity = 'visitor-"quoted"'
    create_run(store, "quoted-owner", identity)
    create_run(store, "similar-owner", "visitor-")
    with visitor(identity):
        assert [r["run_id"] for r in store.list_runs()] == ["quoted-owner"]
