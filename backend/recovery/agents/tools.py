"""Core agent tools (PRD §8.2) with typed arguments, explicit permissions and validated outputs.

Each call emits tool.started/tool.completed (or tool.failed) domain events, opens an MLflow span and
counts usage against the run budget. Tools enforce domain transitions; agent prose cannot."""

from __future__ import annotations

import time
import uuid
from contextlib import contextmanager
from typing import Any, Callable, Iterator, Optional

from ..runtime.events import EventBus
from ..runtime.tracing import current_trace_id, span

TOOL_NAMES = [
    "get_requirement_set", "query_candidate_offers", "search_public_sources", "retrieve_evidence", "extract_document_fields",
    "resolve_part_identity", "evaluate_requirement", "get_supplier_site_metrics", "match_signal_exposure", "compute_impact",
    "build_recovery_plan", "rank_eligible_offers", "persist_decision", "prepare_document_package", "simulate_submission",
    "emit_domain_event", "request_supplier_followup", "verify_legal_entity",
]


class BudgetExceeded(RuntimeError):
    pass


class ToolRunner:
    def __init__(self, bus: EventBus, run_id: str, case_id: str, invocation_id: str, budget: int):
        self.bus = bus
        self.run_id = run_id
        self.case_id = case_id
        self.invocation_id = invocation_id
        self.budget = budget
        self.usage: dict[str, int] = {}

    @property
    def used(self) -> int:
        return sum(self.usage.values())

    @contextmanager
    def call(self, tool: str, task_id: str, summary: str, args: Optional[dict] = None, *, quiet: bool = False) -> Iterator[dict]:
        if tool not in TOOL_NAMES:
            raise ValueError(f"unknown tool {tool}")
        if self.used >= self.budget:
            raise BudgetExceeded(f"run tool budget of {self.budget} calls reached")
        self.usage[tool] = self.usage.get(tool, 0) + 1
        call_id = str(uuid.uuid4())[:8]
        result: dict[str, Any] = {"call_id": call_id}
        started = time.time()
        if not quiet:
            self.bus.publish(self.run_id, self.case_id, "tool.started", summary, {"tool": tool, "call_id": call_id, "args": args or {}},
                             task_id=task_id, invocation_id=self.invocation_id, trace_id=current_trace_id())
        with span(f"tool.{tool}", "TOOL", {"tool": tool, "case_id": self.case_id, "task_id": task_id}, inputs=args or {}) as sp:
            try:
                yield result
            except BudgetExceeded:
                raise
            except Exception as exc:
                self.bus.publish(self.run_id, self.case_id, "tool.failed", f"{tool} failed: {str(exc)[:160]}",
                                 {"tool": tool, "call_id": call_id, "error": str(exc)[:300]}, task_id=task_id, invocation_id=self.invocation_id)
                raise
            latency = int((time.time() - started) * 1000)
            if sp is not None:
                try:
                    sp.set_outputs({k: v for k, v in result.items() if k in ("summary", "count", "mode", "evidence_ids")})
                    sp.set_attributes({"latency_ms": latency, "retrieval_mode": result.get("mode", "")})
                except Exception:  # noqa: BLE001
                    pass
        if not quiet:
            self.bus.publish(self.run_id, self.case_id, "tool.completed", result.get("summary", f"{tool} completed"),
                             {"tool": tool, "call_id": call_id, "latency_ms": latency,
                              **{k: v for k, v in result.items() if k not in ("call_id",) and not callable(v)}},
                             task_id=task_id, invocation_id=self.invocation_id, evidence_refs=result.get("evidence_ids", [])[:20],
                             trace_id=current_trace_id())
