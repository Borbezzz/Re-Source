"""Lakebase (Databricks managed Postgres) credentials: short-lived OAuth tokens used as the Postgres
password, cached and refreshed before expiry (PRD §11: refresh expiring Lakebase OAuth connections)."""

from __future__ import annotations

import threading
import time
import uuid

from ..config import settings

_lock = threading.Lock()
_cache = {"token": None, "expires": 0.0, "mode": None}


def token_provider() -> str:
    with _lock:
        if _cache["token"] and time.time() < _cache["expires"]:
            return _cache["token"]
        from databricks.sdk import WorkspaceClient

        w = WorkspaceClient()
        token, mode = None, None
        try:
            cred = w.database.generate_database_credential(request_id=str(uuid.uuid4()), instance_names=[settings.lakebase_instance])
            token, mode = cred.token, "database_credential"
        except Exception:  # noqa: BLE001 - App service principals can use their workspace OAuth token directly
            token, mode = w.config.oauth_token().access_token, "workspace_oauth"
        _cache.update(token=token, expires=time.time() + 40 * 60, mode=mode)
        return token


def token_mode() -> str | None:
    return _cache["mode"]
