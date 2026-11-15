"""Databricks SQL warehouse adapter: Delta reads/writes, AI Functions (ai_extract) and capability
probes. Uses typed, parameterised SQL only (PRD §11)."""

from __future__ import annotations

import logging
import threading
import time
from contextlib import contextmanager
from typing import Any, Iterator, Optional

from ..config import settings

log = logging.getLogger("recovery.databricks")


class DatabricksSQL:
    def __init__(self) -> None:
        self._lock = threading.Lock()
        self.last_error: Optional[str] = None
        self.stats = {"queries": 0, "failures": 0, "last_latency_ms": None}

    @property
    def configured(self) -> bool:
        return settings.databricks_configured

    @property
    def fq_schema(self) -> str:
        return f"`{settings.databricks_catalog}`.`{settings.databricks_schema}`"

    def table(self, name: str) -> str:
        return f"{self.fq_schema}.`{name}`"

    @contextmanager
    def _connect(self) -> Iterator[Any]:
        from databricks import sql

        kwargs: dict[str, Any] = {"server_hostname": settings.databricks_server_hostname, "http_path": settings.databricks_http_path,
                                  "_socket_timeout": 120}
        if settings.databricks_token:
            kwargs["access_token"] = settings.databricks_token
        else:  # Databricks Apps service principal (OAuth M2M)
            from databricks.sdk.core import Config, oauth_service_principal

            cfg = Config(host=f"https://{settings.databricks_server_hostname}", client_id=settings.databricks_client_id,
                         client_secret=settings.databricks_client_secret)
            kwargs["credentials_provider"] = lambda: oauth_service_principal(cfg)
        conn = sql.connect(**kwargs)
        try:
            yield conn
        finally:
            conn.close()

    def query(self, statement: str, params: Optional[dict] = None) -> list[dict]:
        if not self.configured:
            raise RuntimeError("Databricks SQL not configured")
        started = time.time()
        try:
            with self._connect() as conn, conn.cursor() as cur:
                cur.execute(statement, params or {})
                rows = cur.fetchall() if cur.description else []
                cols = [d[0] for d in cur.description] if cur.description else []
            self.stats["queries"] += 1
            self.stats["last_latency_ms"] = int((time.time() - started) * 1000)
            return [dict(zip(cols, r)) for r in rows]
        except Exception as exc:  # noqa: BLE001
            self.stats["failures"] += 1
            self.last_error = f"{type(exc).__name__}: {str(exc)[:300]}"
            raise

    def execute_many(self, statements: list[tuple[str, dict]]) -> None:
        with self._connect() as conn, conn.cursor() as cur:
            for stmt, params in statements:
                cur.execute(stmt, params)
        self.stats["queries"] += len(statements)

    # ------------------------------------------------------------------ AI Functions
    def ai_extract_batch(self, items: list[tuple[str, str, list[str]]]) -> dict[str, dict]:
        """items: (row_id, text, labels). Returns {row_id: {label: value}} using Databricks ai_extract."""
        import json

        out: dict[str, dict] = {}
        # group by label set: one statement per doc type
        groups: dict[tuple[str, ...], list[tuple[str, str]]] = {}
        for rid, text, labels in items:
            groups.setdefault(tuple(labels), []).append((rid, text))
        for labels, rows in groups.items():
            for start in range(0, len(rows), 20):
                chunk = rows[start:start + 20]
                values, params = [], {}
                for i, (rid, text) in enumerate(chunk):
                    values.append(f"(:id{i}, :t{i})")
                    params[f"id{i}"] = rid
                    params[f"t{i}"] = text
                label_sql = ", ".join(f"'{lbl}'" for lbl in labels)  # labels are code constants, not user input
                stmt = (f"SELECT id, ai_extract(txt, array({label_sql})) AS x FROM VALUES {', '.join(values)} AS t(id, txt)")
                for row in self.query(stmt, params):
                    raw = row["x"]
                    out[row["id"]] = json.loads(raw) if isinstance(raw, str) else dict(raw or {})
        return out

    def probe(self) -> dict[str, Any]:
        if not self.configured:
            return {"ok": False, "detail": "not configured"}
        try:
            rows = self.query("SELECT current_user() AS u, current_catalog() AS c, version() AS v")
            return {"ok": True, "user": rows[0]["u"], "catalog": rows[0]["c"], "dbsql_version": rows[0]["v"],
                    "latency_ms": self.stats["last_latency_ms"]}
        except Exception as exc:  # noqa: BLE001
            return {"ok": False, "detail": str(exc)[:300]}


databricks_sql = DatabricksSQL()
