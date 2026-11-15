"""EventPublisher (PRD §7.1, FR-14): typed domain events persisted with a per-case sequence inside the
same transaction as the state change, and pushed to live SSE subscribers only after commit."""

from __future__ import annotations

import asyncio
import threading
import uuid
from collections import defaultdict
from datetime import datetime, timezone
from typing import Any, Optional

from ..adapters.store import OperationalStore
from ..domain.models import SCHEMA_VERSION


def _now() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


class EventBus:
    def __init__(self, store: OperationalStore):
        self.store = store
        self._subs: dict[tuple[str, str], set[tuple[asyncio.AbstractEventLoop, asyncio.Queue]]] = defaultdict(set)
        self._lock = threading.Lock()
        self.trace_lookup: Optional[callable] = None  # returns current MLflow trace id if any

    def publish(self, run_id: str, case_id: str, type_: str, summary: str, data: Optional[dict] = None, *, case_revision: Optional[int] = None,
                task_id: Optional[str] = None, invocation_id: Optional[str] = None, evidence_refs: Optional[list[str]] = None,
                trace_id: Optional[str] = None, data_origin: str = "synthetic_demo") -> dict:
        event = {
            "schema_version": SCHEMA_VERSION,
            "event_id": str(uuid.uuid4()),
            "sequence": 0,
            "occurred_at": _now(),
            "scenario_run_id": run_id,
            "case_id": case_id,
            "case_revision": 0,
            "invocation_id": invocation_id,
            "task_id": task_id,
            "type": type_,
            "summary": summary,
            "data": data or {},
            "evidence_refs": evidence_refs or [],
            "trace_id": trace_id or (self.trace_lookup() if self.trace_lookup else None),
            "data_origin": data_origin,
        }
        with self.store.tx() as c:
            if case_id != "__run__":
                case = self.store.lock_case(c, run_id, case_id)
                event["case_revision"] = case_revision if case_revision is not None else case["revision"]
            self.store.append_event(c, run_id, case_id, event)
            self.store.after_commit(lambda: self._notify(run_id, case_id, event))
        return event

    # ------------------------------------------------------------------ live subscribers
    def subscribe(self, run_id: str, case_id: str) -> asyncio.Queue:
        q: asyncio.Queue = asyncio.Queue(maxsize=5000)
        loop = asyncio.get_running_loop()
        with self._lock:
            self._subs[(run_id, case_id)].add((loop, q))
        return q

    def unsubscribe(self, run_id: str, case_id: str, q: asyncio.Queue) -> None:
        with self._lock:
            self._subs[(run_id, case_id)] = {(lp, qq) for lp, qq in self._subs[(run_id, case_id)] if qq is not q}

    def _notify(self, run_id: str, case_id: str, event: dict) -> None:
        with self._lock:
            targets = list(self._subs.get((run_id, case_id), ()))
        for loop, q in targets:
            try:
                loop.call_soon_threadsafe(q.put_nowait, event)
            except RuntimeError:
                pass

    def subscriber_count(self) -> int:
        with self._lock:
            return sum(len(v) for v in self._subs.values())
