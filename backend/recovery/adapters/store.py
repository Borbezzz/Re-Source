"""Operational store (PRD §5.3): authoritative for mutable case revision, commands/idempotency,
selections, document version pointers, outbox, events and simulated receipts.

Backed by Lakebase Postgres when RS_OPERATIONAL_DB_URL is set (native writable tables), otherwise a
local SQLite file with serialised write transactions (BEGIN IMMEDIATE) for development and tests.
Every multi-row command runs inside `tx()`; conditional publication uses compare-and-swap on the
case row (`lock_case`).
"""

from __future__ import annotations

import json
import threading
from contextlib import contextmanager
from datetime import datetime, timezone
from decimal import Decimal
from typing import Any, Iterator, Optional

from sqlalchemy import (
    Column, Integer, MetaData, Table, Text, UniqueConstraint, and_, create_engine, event, func, insert, select, update,
)
from sqlalchemy.engine import Connection, Engine

metadata = MetaData()


def _json_default(o: Any) -> Any:
    if isinstance(o, datetime):
        return o.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")
    if isinstance(o, Decimal):
        return str(o)
    if hasattr(o, "model_dump"):
        return o.model_dump(mode="json")
    if isinstance(o, (set, frozenset)):
        return sorted(o)
    raise TypeError(f"not JSON serialisable: {type(o)}")


def dumps(v: Any) -> str:
    return json.dumps(v, default=_json_default, sort_keys=True)


def loads(v: Optional[str]) -> Any:
    return json.loads(v) if v else None


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


runs = Table(
    "runs", metadata,
    Column("run_id", Text, primary_key=True),
    Column("mode", Text, nullable=False),
    Column("fixture_version", Text, nullable=False),
    Column("manifest_version", Text, nullable=False),
    Column("scenario_now", Text, nullable=False),
    Column("status", Text, nullable=False),
    Column("is_current", Integer, nullable=False, default=0),
    Column("replay_source_run_id", Text),
    Column("barrier_count", Integer, nullable=False, default=0),
    Column("manifest_version_counter", Integer, nullable=False, default=1),
    Column("created_at", Text, nullable=False),
)

cases = Table(
    "cases", metadata,
    Column("run_id", Text, primary_key=True),
    Column("case_id", Text, primary_key=True),
    Column("component_id", Text, nullable=False),
    Column("state", Text, nullable=False),
    Column("prior_stable_state", Text),
    Column("revision", Integer, nullable=False, default=0),
    Column("input_revision", Integer, nullable=False, default=0),
    Column("mode", Text, nullable=False),
    Column("visual_state", Text, nullable=False),
    Column("monitoring_status", Text, nullable=False),
    Column("current_decision_id", Text),
    Column("initial_decision_id", Text),
    Column("current_selection_id", Text),
    Column("current_package_id", Text),
    Column("latest_receipt_id", Text),
    Column("active_generation_id", Text),
    Column("pending_target_revision", Integer),
    Column("stale_reasons", Text, nullable=False, default="[]"),
    Column("decision_labels", Text, nullable=False, default="{}"),
    Column("event_seq", Integer, nullable=False, default=0),
    Column("updated_at", Text, nullable=False),
)

events = Table(
    "events", metadata,
    Column("run_id", Text, primary_key=True),
    Column("case_id", Text, primary_key=True),
    Column("sequence", Integer, primary_key=True),
    Column("event_id", Text, nullable=False, unique=True),
    Column("type", Text, nullable=False),
    Column("payload", Text, nullable=False),
    Column("occurred_at", Text, nullable=False),
)

idempotency = Table(
    "idempotency", metadata,
    Column("scope", Text, primary_key=True),
    Column("key", Text, primary_key=True),
    Column("request_hash", Text, nullable=False),
    Column("response", Text, nullable=False),
    Column("status_code", Integer, nullable=False),
    Column("created_at", Text, nullable=False),
)


def _payload_table(name: str, *cols: Column, unique: tuple[str, ...] | None = None) -> Table:
    args: list[Any] = [
        Column("id", Text, primary_key=True),
        Column("run_id", Text, nullable=False, index=True),
        Column("case_id", Text, index=True),
        *cols,
        Column("status", Text),
        Column("payload", Text, nullable=False),
        Column("created_at", Text, nullable=False),
        Column("updated_at", Text, nullable=False),
    ]
    if unique:
        args.append(UniqueConstraint(*unique, name=f"uq_{name}_{'_'.join(unique)}"))
    return Table(name, metadata, *args)


decisions = _payload_table("decisions", Column("label", Text), Column("generation_id", Text), Column("input_revision", Integer))
diffs = _payload_table("diffs", Column("from_id", Text), Column("to_id", Text))
selections = _payload_table("selections", Column("idem_key", Text), unique=("run_id", "case_id", "idem_key"))
drafts = _payload_table("drafts", Column("package_id", Text), Column("version", Integer))
packages = _payload_table("packages", Column("version", Integer), Column("generation_id", Text), unique=("run_id", "case_id", "version"))
receipts = _payload_table("receipts", Column("idem_key", Text), Column("operation_key", Text),
                          unique=("run_id", "operation_key"))
outbox = _payload_table("outbox", Column("op_type", Text), Column("attempts", Integer, default=0),
                        Column("available_at", Text), Column("last_error", Text))
subscriptions = _payload_table("subscriptions", Column("dependency_revision", Integer, default=0))
change_events = _payload_table("change_events", Column("dedup_key", Text), Column("seq", Integer),
                               unique=("run_id", "dedup_key"))
barriers = _payload_table("barriers")
signals = _payload_table("signals", Column("source_event_id", Text), Column("version", Integer),
                         unique=("run_id", "source_event_id", "version"))
evidence_state = _payload_table("evidence_state", Column("version_id", Text), Column("document_id", Text),
                                Column("candidate_id", Text), unique=("run_id", "version_id", "candidate_id"))
generations = _payload_table("generations", Column("target_input_revision", Integer), Column("kind", Text))
gaps = _payload_table("gaps", Column("candidate_id", Text), Column("requirement_id", Text))
timers = _payload_table("timers", Column("due_at", Text), Column("kind", Text))
facts_cache = Table(
    "facts_cache", metadata,
    Column("content_hash", Text, primary_key=True),
    Column("doc_type", Text, primary_key=True),
    Column("extraction_mode", Text, nullable=False),
    Column("payload", Text, nullable=False),
    Column("created_at", Text, nullable=False),
)
kv = Table("kv", metadata, Column("key", Text, primary_key=True), Column("value", Text, nullable=False))


class OperationalStore:
    def __init__(self, url: str):
        self.url = url
        self.is_sqlite = url.startswith("sqlite")
        kwargs: dict[str, Any] = {"future": True}
        if self.is_sqlite:
            kwargs["connect_args"] = {"check_same_thread": False, "timeout": 30}
        else:
            kwargs["pool_pre_ping"] = True
            kwargs["pool_recycle"] = 1800  # Lakebase OAuth tokens rotate; recycle connections
            kwargs["pool_size"] = 8
            kwargs["max_overflow"] = 8
        self.engine: Engine = create_engine(url, **kwargs)
        self.pg_schema: Optional[str] = None
        if not self.is_sqlite:
            from ..config import settings as _settings

            self.pg_schema = _settings.lakebase_schema
            if "@" in url and ":" not in url.split("://", 1)[1].split("@", 1)[0]:  # no static password → Lakebase OAuth token
                from .lakebase import token_provider

                @event.listens_for(self.engine, "do_connect")
                def _provide_token(dialect, conn_rec, cargs, cparams):  # noqa: ANN001
                    cparams["password"] = token_provider()

            schema = self.pg_schema

            @event.listens_for(self.engine, "connect")
            def _search_path(dbapi_conn, _):  # noqa: ANN001
                cur = dbapi_conn.cursor()
                cur.execute(f'CREATE SCHEMA IF NOT EXISTS "{schema}"')
                cur.execute(f'SET search_path TO "{schema}"')
                cur.close()
                dbapi_conn.commit()
        if self.is_sqlite:
            @event.listens_for(self.engine, "connect")
            def _connect(dbapi_conn, _):  # noqa: ANN001
                dbapi_conn.isolation_level = None
                cur = dbapi_conn.cursor()
                cur.execute("PRAGMA journal_mode=WAL")
                cur.execute("PRAGMA busy_timeout=30000")
                cur.close()

            @event.listens_for(self.engine, "begin")
            def _begin(conn):  # noqa: ANN001
                conn.exec_driver_sql("BEGIN IMMEDIATE")
        self._local = threading.local()
        metadata.create_all(self.engine)
        if not self.is_sqlite:
            self._migrate_postgres()

    def _migrate_postgres(self) -> None:
        """Idempotent schema migration: earlier deployments created bounded VARCHAR columns; widen them to TEXT."""
        from sqlalchemy import text as sql_text

        with self.engine.begin() as conn:
            rows = conn.execute(sql_text(
                "SELECT table_name, column_name FROM information_schema.columns "
                "WHERE table_schema = current_schema() AND data_type = 'character varying'")).all()
            for table, column in rows:
                if table in metadata.tables:
                    conn.execute(sql_text(f'ALTER TABLE "{table}" ALTER COLUMN "{column}" TYPE TEXT'))

    # ------------------------------------------------------------------ transactions
    @contextmanager
    def tx(self) -> Iterator[Connection]:
        existing: Optional[Connection] = getattr(self._local, "conn", None)
        if existing is not None:  # nested: join the outer transaction
            yield existing
            return
        self._local.after_commit = []
        try:
            with self.engine.begin() as conn:
                self._local.conn = conn
                try:
                    yield conn
                finally:
                    self._local.conn = None
        except BaseException:
            self._local.after_commit = []
            raise
        callbacks, self._local.after_commit = self._local.after_commit, []
        for cb in callbacks:
            try:
                cb()
            except Exception:  # noqa: BLE001 - notification failures never undo a commit
                pass

    def after_commit(self, cb) -> None:  # noqa: ANN001
        """Run `cb` once the outermost transaction commits (immediately when not in a transaction)."""
        if getattr(self._local, "conn", None) is None:
            cb()
        else:
            self._local.after_commit.append(cb)

    # ------------------------------------------------------------------ generic payload rows
    def put(self, table: Table, row_id: str, run_id: str, payload: Any, *, case_id: str | None = None, status: str | None = None, **cols: Any) -> None:
        ts = now_iso()
        with self.tx() as c:
            exists = c.execute(select(table.c.id).where(table.c.id == row_id)).first()
            values = {"run_id": run_id, "case_id": case_id, "status": status, "payload": dumps(payload), "updated_at": ts, **cols}
            if exists:
                c.execute(update(table).where(table.c.id == row_id).values(**values))
            else:
                c.execute(insert(table).values(id=row_id, created_at=ts, **values))

    def get(self, table: Table, row_id: str) -> Optional[dict]:
        with self.tx() as c:
            row = c.execute(select(table).where(table.c.id == row_id)).mappings().first()
        return self._row(row)

    def find(self, table: Table, *, order_by: str = "created_at", desc: bool = False, limit: int | None = None, **filters: Any) -> list[dict]:
        conds = [getattr(table.c, k) == v for k, v in filters.items() if v is not None]
        q = select(table).where(and_(*conds)) if conds else select(table)
        col = getattr(table.c, order_by)
        q = q.order_by(col.desc() if desc else col.asc())
        if limit:
            q = q.limit(limit)
        with self.tx() as c:
            rows = c.execute(q).mappings().all()
        return [self._row(r) for r in rows]

    def set_status(self, table: Table, row_id: str, status: str, payload_patch: dict | None = None, *, sync_payload_status: bool = True) -> None:
        with self.tx() as c:
            row = c.execute(select(table).where(table.c.id == row_id)).mappings().first()
            if not row:
                return
            payload = loads(row["payload"]) or {}
            if payload_patch:
                payload.update(payload_patch)
            if sync_payload_status and isinstance(payload, dict) and "status" in payload and table.name != "signals":
                payload["status"] = status
            c.execute(update(table).where(table.c.id == row_id).values(status=status, payload=dumps(payload), updated_at=now_iso()))

    @staticmethod
    def _row(row: Any) -> Optional[dict]:
        if row is None:
            return None
        d = dict(row)
        if "payload" in d:
            d["payload"] = loads(d["payload"])
        return d

    # ------------------------------------------------------------------ runs
    def create_run(self, run: dict) -> None:
        with self.tx() as c:
            c.execute(update(runs).values(is_current=0))
            c.execute(insert(runs).values(**run, is_current=1, created_at=now_iso()))

    def current_run(self) -> Optional[dict]:
        with self.tx() as c:
            row = c.execute(select(runs).where(runs.c.is_current == 1)).mappings().first()
        return dict(row) if row else None

    def get_run(self, run_id: str) -> Optional[dict]:
        with self.tx() as c:
            row = c.execute(select(runs).where(runs.c.run_id == run_id)).mappings().first()
        return dict(row) if row else None

    def list_runs(self) -> list[dict]:
        with self.tx() as c:
            rows = c.execute(select(runs).order_by(runs.c.created_at.desc())).mappings().all()
        return [dict(r) for r in rows]

    def update_run(self, run_id: str, **values: Any) -> None:
        with self.tx() as c:
            c.execute(update(runs).where(runs.c.run_id == run_id).values(**values))

    def lock_run(self, c: Connection, run_id: str) -> dict:
        row = c.execute(select(runs).where(runs.c.run_id == run_id).with_for_update()).mappings().first()
        if not row:
            raise KeyError(run_id)
        return dict(row)

    # ------------------------------------------------------------------ cases
    def insert_case(self, values: dict) -> None:
        with self.tx() as c:
            c.execute(insert(cases).values(updated_at=now_iso(), **values))

    def get_case(self, run_id: str, case_id: str) -> Optional[dict]:
        with self.tx() as c:
            row = c.execute(select(cases).where(and_(cases.c.run_id == run_id, cases.c.case_id == case_id))).mappings().first()
        return self._case(row)

    def list_cases(self, run_id: str) -> list[dict]:
        with self.tx() as c:
            rows = c.execute(select(cases).where(cases.c.run_id == run_id).order_by(cases.c.case_id)).mappings().all()
        return [self._case(r) for r in rows]

    def lock_case(self, c: Connection, run_id: str, case_id: str) -> dict:
        row = c.execute(select(cases).where(and_(cases.c.run_id == run_id, cases.c.case_id == case_id)).with_for_update()).mappings().first()
        if not row:
            raise KeyError(case_id)
        return self._case(row)

    def update_case(self, c: Connection, run_id: str, case_id: str, **values: Any) -> None:
        if "stale_reasons" in values and not isinstance(values["stale_reasons"], str):
            values["stale_reasons"] = dumps(values["stale_reasons"])
        if "decision_labels" in values and not isinstance(values["decision_labels"], str):
            values["decision_labels"] = dumps(values["decision_labels"])
        c.execute(update(cases).where(and_(cases.c.run_id == run_id, cases.c.case_id == case_id)).values(updated_at=now_iso(), **values))

    @staticmethod
    def _case(row: Any) -> Optional[dict]:
        if row is None:
            return None
        d = dict(row)
        d["stale_reasons"] = loads(d["stale_reasons"]) or []
        d["decision_labels"] = loads(d["decision_labels"]) or {}
        return d

    # ------------------------------------------------------------------ events
    def append_event(self, c: Connection, run_id: str, case_id: str, event: dict) -> dict:
        """Assigns the per-case sequence inside the caller's transaction."""
        if case_id == "__run__":
            self.lock_run(c, run_id)  # serialise run-level sequence allocation (Postgres row lock)
            row = c.execute(select(func.max(events.c.sequence)).where(and_(events.c.run_id == run_id, events.c.case_id == case_id))).scalar()
            seq = int(row or 0) + 1
        else:
            case = self.lock_case(c, run_id, case_id)
            seq = case["event_seq"] + 1
            c.execute(update(cases).where(and_(cases.c.run_id == run_id, cases.c.case_id == case_id)).values(event_seq=seq))
        event["sequence"] = seq
        c.execute(insert(events).values(run_id=run_id, case_id=case_id, sequence=seq, event_id=event["event_id"], type=event["type"],
                                        payload=dumps(event), occurred_at=event["occurred_at"]))
        return event

    def events_after(self, run_id: str, case_id: str, after: int, limit: int = 1000) -> list[dict]:
        with self.tx() as c:
            rows = c.execute(select(events.c.payload).where(and_(events.c.run_id == run_id, events.c.case_id == case_id, events.c.sequence > after))
                             .order_by(events.c.sequence).limit(limit)).all()
        return [loads(r[0]) for r in rows]

    def max_sequence(self, run_id: str, case_id: str) -> int:
        with self.tx() as c:
            v = c.execute(select(func.max(events.c.sequence)).where(and_(events.c.run_id == run_id, events.c.case_id == case_id))).scalar()
        return int(v or 0)

    # ------------------------------------------------------------------ idempotency
    def idem_get(self, scope: str, key: str) -> Optional[dict]:
        with self.tx() as c:
            row = c.execute(select(idempotency).where(and_(idempotency.c.scope == scope, idempotency.c.key == key))).mappings().first()
        return dict(row) if row else None

    def idem_put(self, c: Connection, scope: str, key: str, request_hash: str, response: Any, status_code: int) -> None:
        c.execute(insert(idempotency).values(scope=scope, key=key, request_hash=request_hash, response=dumps(response),
                                             status_code=status_code, created_at=now_iso()))

    # ------------------------------------------------------------------ facts cache
    def cached_facts(self, content_hash: str, doc_type: str) -> Optional[dict]:
        with self.tx() as c:
            row = c.execute(select(facts_cache).where(and_(facts_cache.c.content_hash == content_hash, facts_cache.c.doc_type == doc_type))).mappings().first()
        return {"mode": row["extraction_mode"], "facts": loads(row["payload"])} if row else None

    def cache_facts(self, content_hash: str, doc_type: str, mode: str, facts: Any) -> None:
        with self.tx() as c:
            exists = c.execute(select(facts_cache.c.content_hash).where(and_(facts_cache.c.content_hash == content_hash, facts_cache.c.doc_type == doc_type))).first()
            if not exists:
                c.execute(insert(facts_cache).values(content_hash=content_hash, doc_type=doc_type, extraction_mode=mode, payload=dumps(facts), created_at=now_iso()))

    def kv_get(self, key: str) -> Optional[Any]:
        with self.tx() as c:
            row = c.execute(select(kv.c.value).where(kv.c.key == key)).first()
        return loads(row[0]) if row else None

    def kv_set(self, key: str, value: Any) -> None:
        with self.tx() as c:
            if c.execute(select(kv.c.key).where(kv.c.key == key)).first():
                c.execute(update(kv).where(kv.c.key == key).values(value=dumps(value)))
            else:
                c.execute(insert(kv).values(key=key, value=dumps(value)))
