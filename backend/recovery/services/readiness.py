"""Readiness / capability matrix (PRD §7 GET /api/v1/readiness, DISC-04).

Read-only probes of the dependencies the product uses, cached ~60 s. Never provisions anything and never
spends model tokens. `refresh=True` additionally makes one cheap live call each to Companies House and
Linkup. Detailed diagnostics are for the team view; secrets are never included.
"""

from __future__ import annotations

import threading
import time
from datetime import datetime, timezone
from typing import Any, Optional

from ..adapters.databricks_sql import databricks_sql
from ..adapters.external import companies_house, linkup
from ..adapters.model_client import model_client
from ..config import settings
from ..runtime.tracing import tracing_state

_CACHE: dict[str, Any] = {"at": 0.0, "value": None}
_LOCK = threading.Lock()
TTL_S = 60.0


def _workspace_client():  # noqa: ANN202
    from databricks.sdk import WorkspaceClient

    if settings.databricks_token:
        return WorkspaceClient(host=settings.databricks_host, token=settings.databricks_token, auth_type="pat")
    if settings.databricks_client_id and settings.databricks_client_secret:
        return WorkspaceClient(host=settings.databricks_host or f"https://{settings.databricks_server_hostname}",
                               client_id=settings.databricks_client_id, client_secret=settings.databricks_client_secret, auth_type="oauth-m2m")
    return WorkspaceClient()


def _rest_get(path: str) -> dict:
    return _workspace_client().api_client.do("GET", path) or {}


def _timed(fn) -> dict[str, Any]:  # noqa: ANN001
    t0 = time.time()
    try:
        out = fn()
    except Exception as exc:  # noqa: BLE001
        out = {"ok": False, "detail": f"{type(exc).__name__}: {str(exc)[:240]}"}
    out.setdefault("latency_ms", int((time.time() - t0) * 1000))
    return out


def _probe_store(services: Any) -> dict:
    store = getattr(services, "store", None)
    if store is None:
        return {"ok": False, "detail": "operational store not initialised", "critical": True}
    store.list_runs()
    backend = "sqlite (local file)" if store.is_sqlite else "postgres (Lakebase-compatible)"
    return {"ok": True, "detail": backend, "critical": True,
            "note": "Authoritative for case revision, commands, selections, outbox, receipts (PRD §5.3)."}


def _probe_sql() -> dict:
    if not databricks_sql.configured:
        return {"ok": False, "detail": "not configured", "critical": False}
    p = databricks_sql.probe()
    return {"ok": p.get("ok", False), "detail": p.get("detail") or f"DBSQL {p.get('dbsql_version', '?')}", "warehouse_http_path": settings.databricks_http_path,
            "catalog": settings.databricks_catalog, "schema": settings.databricks_schema, "critical": False}


def _probe_ai_functions() -> dict:
    if not databricks_sql.configured:
        return {"ok": False, "detail": "not configured"}
    out = databricks_sql.ai_extract_batch([("probe", "PART NUMBER: RS-FN-1001", ["part_number"])])
    value = (out.get("probe") or {}).get("part_number")
    return {"ok": value == "RS-FN-1001", "detail": f"ai_extract returned {value!r}", "function": "ai_extract"}


def _probe_delta() -> dict:
    if not databricks_sql.configured:
        return {"ok": False, "detail": "not configured"}
    from .projection import DELTA_TABLES

    rows = databricks_sql.query(f"SHOW TABLES IN {databricks_sql.fq_schema} LIKE 'rs_*'")
    present = sorted(r.get("tableName") or r.get("table_name") for r in rows)
    missing = sorted(set(DELTA_TABLES) - set(present))
    counts = {}
    if "rs_evidence_versions" in present:
        counts["rs_evidence_versions"] = databricks_sql.query(f"SELECT COUNT(*) AS n FROM {databricks_sql.table('rs_evidence_versions')}")[0]["n"]
    return {"ok": not missing, "detail": f"{len(present)}/{len(DELTA_TABLES)} rs_* tables present", "present": present, "missing": missing,
            "counts": counts}


def _probe_ai_search() -> dict:
    if not settings.databricks_host and not settings.databricks_server_hostname:
        return {"ok": False, "detail": "not configured"}
    data = _rest_get("/api/2.0/vector-search/endpoints")
    eps = [e.get("name") for e in data.get("endpoints", [])]
    return {"ok": bool(eps), "endpoints": eps,
            "detail": f"{len(eps)} endpoint(s)" if eps else "none provisioned — using Delta SQL keyword retrieval (recorded retrieval_mode)",
            "alternative": "delta_sql_keyword / in_memory_keyword"}


def _probe_lakebase() -> dict:
    if not settings.databricks_host and not settings.databricks_server_hostname:
        return {"ok": False, "detail": "not configured"}
    data = _rest_get("/api/2.0/database/instances")
    inst = [i.get("name") for i in data.get("database_instances", [])]
    using = bool(settings.operational_db_url.startswith("postgresql"))
    return {"ok": bool(inst) and using, "instances": inst,
            "detail": (f"{len(inst)} instance(s); app {'uses' if using else 'does not use'} Postgres") if inst
            else "none provisioned — operational store runs on SQLite (Postgres/Lakebase-ready via RS_OPERATIONAL_DB_URL)",
            "alternative": "sqlite operational store"}


def _probe_apps() -> dict:
    name = settings_app_name()
    data = _rest_get(f"/api/2.0/apps/{name}")
    compute = (data.get("compute_status") or {}).get("state")
    resources = [r.get("name") for r in data.get("resources", [])]
    return {"ok": bool(data.get("name")), "app": data.get("name"), "url": data.get("url"), "compute_state": compute,
            "active_deployment": bool(data.get("active_deployment")), "resources": resources,
            "detail": f"app '{data.get('name')}' compute {compute}"}


def settings_app_name() -> str:
    import os

    return os.getenv("DATABRICKS_APP_NAME", "resource")


def _probe_mlflow() -> dict:
    ts = tracing_state()
    detail: dict[str, Any] = {"tracing_enabled": ts.get("enabled"), "tracing_error": ts.get("error"), "experiment_id": settings.mlflow_experiment_id}
    if settings.mlflow_experiment_id and (settings.databricks_host or settings.databricks_server_hostname):
        exp = _rest_get(f"/api/2.0/mlflow/experiments/get?experiment_id={settings.mlflow_experiment_id}").get("experiment", {})
        detail.update(experiment_name=exp.get("name"), lifecycle=exp.get("lifecycle_stage"))
        return {"ok": exp.get("lifecycle_stage") == "active", "detail": f"experiment {exp.get('name')}", **detail}
    return {"ok": False, "detail": "MLflow experiment not configured", **detail}


def _probe_model() -> dict:
    return {"ok": model_client.available and model_client.usage.get("failures", 0) <= model_client.usage.get("calls", 0),
            "configured": model_client.available, "provider": "openai", "model": model_client.model, "usage": dict(model_client.usage),
            "last_error": model_client.last_error, "detail": f"{model_client.model} via OpenAI Responses API" if model_client.available else "OPENAI_API_KEY not set",
            "note": "No tokens are spent by readiness checks."}


def _probe_linkup(refresh: bool) -> dict:
    out = {"configured": linkup.available, "stats": dict(linkup.stats), "last_error": linkup.last_error}
    if refresh and linkup.available:
        r = linkup.search("UK CAA Form 1 authorised release certificate guidance", max_results=2, timeout=20)
        out.update(ok=r.get("ok", False), detail=f"live search returned {len(r.get('results', []))} result(s)" if r.get("ok") else r.get("detail"),
                   latency_ms=r.get("latency_ms"))
    else:
        out.update(ok=linkup.available and not linkup.last_error, detail="configured (no live call; refresh=true to test)" if linkup.available else "not configured")
    return out


def _probe_companies_house(refresh: bool) -> dict:
    out = {"configured": companies_house.available, "stats": dict(companies_house.stats), "last_error": companies_house.last_error}
    if refresh and companies_house.available:
        r = companies_house.search("Rolls-Royce", limit=1)
        top = (r.get("items") or [{}])[0]
        out.update(ok=r.get("ok", False), detail=f"live search ok: {top.get('title')} ({top.get('status')})" if r.get("ok") else r.get("detail"))
    else:
        out.update(ok=companies_house.available and not companies_house.last_error,
                   detail="configured (no live call; refresh=true to test)" if companies_house.available else "not configured")
    return out


def capability_matrix(services: Any, refresh: bool = False) -> dict[str, Any]:
    with _LOCK:
        if not refresh and _CACHE["value"] and time.time() - _CACHE["at"] < TTL_S:
            return _CACHE["value"]
    probes = {
        "operational_store": lambda: _probe_store(services),
        "sql_warehouse": _probe_sql,
        "ai_functions": _probe_ai_functions,
        "delta_tables": _probe_delta,
        "ai_search": _probe_ai_search,
        "lakebase": _probe_lakebase,
        "databricks_app": _probe_apps,
        "mlflow": _probe_mlflow,
        "model": _probe_model,
        "linkup": lambda: _probe_linkup(refresh),
        "companies_house": lambda: _probe_companies_house(refresh),
    }
    from concurrent.futures import ThreadPoolExecutor

    with ThreadPoolExecutor(max_workers=len(probes)) as pool:
        futures = {name: pool.submit(_timed, fn) for name, fn in probes.items()}
        caps: dict[str, dict] = {name: f.result() for name, f in futures.items()}
    caps["agent_runtime"] = {"ok": False, "detail": "Agent Bricks Agent Runtime / AgentKit DurableAgentServer not used: FastAPI BFF + LangGraph "
                             "with a persistent checkpointer runs in-process (Databricks App target)", "alternative": "fastapi_langgraph_checkpointer"}
    search = getattr(services, "search", None)
    if search is not None:
        try:
            caps["evidence_source"] = {"ok": True, **search.evidence_source_detail(refresh=refresh)}
        except Exception as exc:  # noqa: BLE001
            caps["evidence_source"] = {"ok": False, "detail": str(exc)[:200]}
    proj = getattr(services, "projection", None)
    if proj is not None:
        try:
            caps["delta_projection"] = {"ok": proj.status()["counts"].get("failed", 0) == 0, **proj.status()}
        except Exception as exc:  # noqa: BLE001
            caps["delta_projection"] = {"ok": False, "detail": str(exc)[:200]}
    if not caps["operational_store"].get("ok"):
        status = "unavailable"
    elif all(caps[k].get("ok") for k in ("sql_warehouse", "delta_tables", "mlflow", "model")):
        status = "ok"
    else:
        status = "degraded"
    value = {"status": status, "capabilities": caps, "checked_at": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")}
    with _LOCK:
        _CACHE.update(at=time.time(), value=value)
    return value


def health() -> dict[str, Any]:
    return {"status": "ok", "checked_at": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")}
