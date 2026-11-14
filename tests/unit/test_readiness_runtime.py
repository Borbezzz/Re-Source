"""Readiness reports the active store and runtime rather than configuration guesses."""

from types import SimpleNamespace

import pytest
from recovery.services import readiness


@pytest.fixture(autouse=True)
def databricks_host(monkeypatch):
    monkeypatch.setattr(readiness, "settings", SimpleNamespace(databricks_host="https://example.invalid", databricks_server_hostname=""))


def test_lakebase_probe_uses_active_postgres_store(monkeypatch):
    monkeypatch.setattr(readiness, "_rest_get", lambda _: {"database_instances": [{"name": "resource-ops"}]})
    services = SimpleNamespace(store=SimpleNamespace(is_sqlite=False))
    result = readiness._probe_lakebase(services)
    assert result["ok"] is True
    assert "app uses Postgres" in result["detail"]


def test_lakebase_probe_reports_sqlite_even_if_postgres_is_configured(monkeypatch):
    monkeypatch.setattr(readiness, "_rest_get", lambda _: {"database_instances": [{"name": "resource-ops"}]})
    services = SimpleNamespace(store=SimpleNamespace(is_sqlite=True))
    result = readiness._probe_lakebase(services)
    assert result["ok"] is False
    assert "app does not use Postgres" in result["detail"]


def test_lakebase_probe_without_store_does_not_claim_sqlite(monkeypatch):
    monkeypatch.setattr(readiness, "_rest_get", lambda _: {"database_instances": [{"name": "resource-ops"}]})
    result = readiness._probe_lakebase(SimpleNamespace(store=None))
    assert result["ok"] is False
    assert "not initialised" in result["detail"]


def test_agent_runtime_identifies_active_execution_backend(monkeypatch):
    monkeypatch.setenv("VERCEL", "1")
    result = readiness._agent_runtime(SimpleNamespace(checkpointer_kind="postgres"))
    assert "Vercel" in result["detail"]
    assert "postgres" in result["detail"]
    assert "Databricks App target" not in result["detail"]
