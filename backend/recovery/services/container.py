"""Service container: wires repositories/adapters behind the PRD §5.4 interface boundaries."""

from __future__ import annotations

import logging
import threading
from typing import Optional

from ..adapters.extractor import DocumentExtractor
from ..adapters.model_client import model_client
from ..adapters.store import OperationalStore
from ..adapters import store as st
from ..agents.graph import build_graph, make_checkpointer
from ..config import settings
from ..domain.catalog import load_catalog
from ..runtime.events import EventBus
from ..runtime.tracing import current_trace_id
from .changes import ChangeService
from .coordinator import Coordinator
from .decisions import DecisionService
from .monitoring import MonitoringService
from .run_state import RunState
from .scenario import ScenarioService
from .selection import SelectionService
from .views import Views

log = logging.getLogger("recovery.container")


class Services:
    def __init__(self, db_url: Optional[str] = None, start_worker: bool = True):
        self.store = OperationalStore(db_url or settings.db_url)
        self.catalog = load_catalog()
        self.bus = EventBus(self.store)
        self.bus.trace_lookup = current_trace_id
        self.run_state = RunState(self.store, self.catalog)
        self.extractor = DocumentExtractor(self.store)
        self.model = model_client
        self.monitoring = MonitoringService(self)
        self.decisions = DecisionService(self)
        self.changes = ChangeService(self)
        self.selection = SelectionService(self)
        self.scenario = ScenarioService(self)
        self.views = Views(self)
        self.evidence_source = "fixture_snapshot"
        self.documents = None
        self.search = None
        self.projection = None
        try:
            from .documents import DocumentService

            self.documents = DocumentService(self)
        except Exception as exc:  # noqa: BLE001
            log.warning("document service unavailable: %s", exc)
        try:
            from ..adapters.search import EvidenceSearch

            self.search = EvidenceSearch(self)
        except Exception as exc:  # noqa: BLE001
            log.warning("evidence search unavailable: %s", exc)
        try:
            from .projection import ProjectionWorker

            self.projection = ProjectionWorker(self)
        except Exception as exc:  # noqa: BLE001
            log.warning("projection worker unavailable: %s", exc)
        from .intake import IntakeService

        self.intake = IntakeService(self)
        self.checkpointer, self.checkpointer_kind = make_checkpointer()
        self.graph = build_graph(self, self.checkpointer)
        self.coordinator = Coordinator(self, self.graph)
        self._kick = threading.Event()
        self._stop = threading.Event()
        self._worker: Optional[threading.Thread] = None
        if start_worker:
            self.start_worker()

    def prewarm(self) -> dict:
        """Warm the SQL warehouse and the content-hash extraction cache so the live demo path is responsive.
        Facts produced here are identical to the ones an investigation would extract (same backend, same hash)."""
        import time as _t

        started = _t.time()
        if self.search is not None:
            try:
                self.evidence_source = self.search.evidence_source()
            except Exception as exc:  # noqa: BLE001
                log.warning("evidence source check failed: %s", exc)
        evs = list(self.catalog.evidence.values())
        try:
            out = self.extractor.extract(evs)
            result = {"ok": True, "documents": len(evs), "cached": len(out["cached"]), "backend": out["backend"],
                      "seconds": round(_t.time() - started, 1)}
        except Exception as exc:  # noqa: BLE001
            result = {"ok": False, "error": str(exc)[:200]}
        self.store.kv_set("prewarm", result)
        log.info("prewarm: %s", result)
        return result

    # ------------------------------------------------------------------ outbox worker
    def worker_kick(self) -> None:
        self._kick.set()

    def start_worker(self) -> None:
        if self._worker and self._worker.is_alive():
            return
        self._worker = threading.Thread(target=self._worker_loop, name="outbox-worker", daemon=True)
        self._worker.start()

    def stop(self) -> None:
        self._stop.set()
        self._kick.set()

    def _worker_loop(self) -> None:
        while not self._stop.is_set():
            self._kick.wait(timeout=1.0)
            self._kick.clear()
            try:
                self.process_outbox_once()
            except Exception:  # noqa: BLE001
                log.exception("outbox processing failed")

    def process_outbox_once(self) -> int:
        """Document generation is processed here; analytical projections are delegated to ProjectionWorker."""
        done = 0
        for row in self.store.find(st.outbox, status="pending", op_type="generate_documents"):
            p = row["payload"]
            attempts = (row.get("attempts") or 0) + 1
            try:
                if self.documents is None:
                    raise RuntimeError("document service not available")
                self.documents.generate(p["run_id"], p["case_id"], p["selection_id"])
                self.store.put(st.outbox, row["id"], row["run_id"], p, case_id=row["case_id"], status="done", op_type=row["op_type"],
                               attempts=attempts, available_at=row["available_at"], last_error=None)
                done += 1
            except Exception as exc:  # noqa: BLE001
                status = "failed" if attempts >= settings.outbox_max_attempts else "pending"
                self.store.put(st.outbox, row["id"], row["run_id"], p, case_id=row["case_id"], status=status, op_type=row["op_type"],
                               attempts=attempts, available_at=row["available_at"], last_error=str(exc)[:500])
                log.warning("generate_documents failed (attempt %s): %s", attempts, exc)
        if self.projection is not None:
            try:
                res = self.projection.process_once()
                done += int((res or {}).get("done", 0)) if isinstance(res, dict) else 0
            except Exception:  # noqa: BLE001
                log.exception("projection failed")
        return done
