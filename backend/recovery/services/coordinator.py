"""Execution coordinator (PRD §5.3.1 step 5, FR-14).

Owns execution generations per case: one active generation; reassessment requests coalesce to the
newest pending input revision (durably recorded on the case row so a crash cannot lose it). Graph runs
use a persistent checkpointer; on startup, interrupted generations resume from their last checkpoint.
"""

from __future__ import annotations

import asyncio
import logging
import threading
import uuid
from contextvars import copy_context
from datetime import datetime, timezone
from typing import Any, Optional

from ..adapters import store as st
from ..config import settings
from ..domain.errors import conflict
from ..runtime.tracing import span

log = logging.getLogger("recovery.coordinator")


def _now() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


class Coordinator:
    def __init__(self, services: Any, graph: Any):
        self.s = services
        self.graph = graph
        self._sem = threading.Semaphore(settings.max_case_workers)
        self._threads: dict[str, threading.Thread] = {}
        self._lock = threading.Lock()

    # ------------------------------------------------------------------ commands
    def start_investigation(self, run_id: str, case_id: str, mode: str, expected_revision: Optional[int]) -> dict:
        s = self.s
        with s.store.tx() as c:
            case = s.store.lock_case(c, run_id, case_id)
            if expected_revision is not None and expected_revision != case["revision"]:
                raise conflict("REVISION_MISMATCH", f"Case is at revision {case['revision']}, request expected {expected_revision}",
                               case_revision=case["revision"])
            if case["active_generation_id"]:
                return {"status": "already_running", "generation_id": case["active_generation_id"], "case_revision": case["revision"]}
            if case["current_decision_id"] and case["state"] not in ("failed", "interrupted"):
                return {"status": "duplicate", "generation_id": None, "case_revision": case["revision"]}
            gen_id = self._new_generation(c, run_id, case_id, "investigation", case["input_revision"], None, mode=mode)
            new_rev = case["revision"] + 1
            s.store.update_case(c, run_id, case_id, state="investigating", active_generation_id=gen_id, revision=new_rev, mode=mode)
            s.bus.publish(run_id, case_id, "case.state_changed", "Investigation started", {"state": "investigating", "generation_id": gen_id}, case_revision=new_rev)
        s.store.after_commit(lambda: self._launch(run_id, case_id, gen_id, kind="investigation", mode=mode))
        return {"status": "accepted", "generation_id": gen_id, "case_revision": new_rev}

    def request_reassessment(self, run_id: str, case_id: str, trigger: dict, affected_candidate_ids: Optional[list[str]]) -> Optional[str]:
        """Called after fan-out committed. Records the pending target durably, then starts or coalesces."""
        s = self.s
        with s.store.tx() as c:
            case = s.store.lock_case(c, run_id, case_id)
            key = f"pending_reassess:{run_id}:{case_id}"
            pending = s.store.kv_get(key) or {"affected": [], "triggers": []}
            pending["affected"] = sorted(set(pending["affected"]) | set(affected_candidate_ids or []))
            pending["triggers"].append(trigger)
            s.store.kv_set(key, pending)
            s.store.update_case(c, run_id, case_id, pending_target_revision=case["input_revision"])
        return self._start_pending(run_id, case_id)

    def _start_pending(self, run_id: str, case_id: str) -> Optional[str]:
        s = self.s
        key = f"pending_reassess:{run_id}:{case_id}"
        with s.store.tx() as c:
            case = s.store.lock_case(c, run_id, case_id)
            pending = s.store.kv_get(key) or {"affected": [], "triggers": []}
            if not pending["triggers"]:
                return None
            if case["active_generation_id"]:
                return None  # coalesce: picked up when the running generation finishes
            if not case["current_decision_id"]:
                # never investigated: the first investigation reads the active change directly
                s.store.kv_set(key, {"affected": [], "triggers": []})
                s.store.update_case(c, run_id, case_id, pending_target_revision=None)
                return None
            gen_id = self._new_generation(c, run_id, case_id, "reassessment", case["input_revision"],
                                          pending["triggers"][-1].get("trigger_id"), mode=case["mode"])
            s.store.update_case(c, run_id, case_id, active_generation_id=gen_id, pending_target_revision=None)
            s.store.kv_set(key, {"affected": [], "triggers": []})
            s.store.kv_set(f"gen_inputs:{gen_id}", pending)
        trig = dict(pending["triggers"][-1])
        if len(pending["triggers"]) > 1:
            trig["coalesced_trigger_ids"] = [t.get("trigger_id") for t in pending["triggers"]]
            trig["impact_paths"] = [p for t in pending["triggers"] for p in t.get("impact_paths", [])]
        s.store.after_commit(lambda: self._launch(run_id, case_id, gen_id, kind="reassessment", mode=case["mode"],
                                                trigger=trig, affected=pending["affected"]))
        return gen_id

    def _new_generation(self, c: Any, run_id: str, case_id: str, kind: str, target_rev: int, trigger_id: Optional[str], *, mode: str) -> str:
        gen_id = f"gen-{uuid.uuid4().hex[:12]}"
        self.s.store.put(st.generations, gen_id, run_id, {"generation_id": gen_id, "case_id": case_id, "kind": kind, "target_input_revision": target_rev,
                                                          "trigger_id": trigger_id, "status": "running", "started_at": _now()},
                         case_id=case_id, status="running", target_input_revision=target_rev, kind=kind)
        if settings.job_backend == "vercel":
            self.s.jobs.prepare("generation", run_id, dict(case_id=case_id, gen_id=gen_id, kind=kind,
                                mode=mode, trigger=None, affected=None), gen_id)
        return gen_id

    # ------------------------------------------------------------------ execution
    def _launch(self, run_id: str, case_id: str, gen_id: str, *, kind: str, mode: str, trigger: Optional[dict] = None,
                affected: Optional[list] = None, resume: bool = False) -> None:
        if settings.job_backend == "vercel":
            self.s.jobs.enqueue("generation", run_id, dict(case_id=case_id, gen_id=gen_id, kind=kind, mode=mode, trigger=trigger, affected=affected), key=gen_id)
            return
        from ..runtime.context import job_run_id
        context = copy_context()
        context.run(job_run_id.set, run_id)
        t = threading.Thread(target=context.run, args=(self._run,), name=f"gen-{gen_id}", daemon=True,
                             kwargs=dict(run_id=run_id, case_id=case_id, gen_id=gen_id, kind=kind, mode=mode, trigger=trigger,
                                         affected=affected, resume=resume))
        with self._lock:
            self._threads[gen_id] = t
        t.start()

    def _run(self, *, run_id: str, case_id: str, gen_id: str, kind: str, mode: str, trigger: Optional[dict], affected: Optional[list],
             resume: bool) -> None:
        s = self.s
        config = {"configurable": {"thread_id": gen_id}, "recursion_limit": 60}
        with self._sem:
            try:
                with span(f"{kind}:{case_id}", "AGENT", {"run_id": run_id, "case_id": case_id, "generation_id": gen_id, "mode": mode}):
                    if resume:
                        snap = self.graph.get_state(config)
                        with s.store.tx() as c:
                            cur = s.store.lock_case(c, run_id, case_id)
                            if cur["state"] == "interrupted":
                                before = s.store.kv_get(f"interrupted_state:{run_id}:{case_id}")
                                s.store.update_case(c, run_id, case_id, state=before or ("reassessing" if kind == "reassessment" else "investigating"),
                                                    revision=cur["revision"] + 1)
                        if snap and snap.next:
                            s.bus.publish(run_id, case_id, "run.recovered", f"Resuming {kind} from checkpoint after interruption",
                                          {"generation_id": gen_id, "next_nodes": list(snap.next)})
                            self.graph.invoke(None, config)
                        else:
                            # no checkpoint progress recorded: restart this generation from the beginning
                            s.bus.publish(run_id, case_id, "run.recovered", f"Restarting {kind}: no checkpoint found", {"generation_id": gen_id})
                            self.graph.invoke(self._initial(run_id, case_id, gen_id, kind, mode, trigger, affected), config)
                    else:
                        self.graph.invoke(self._initial(run_id, case_id, gen_id, kind, mode, trigger, affected), config)
                final = self.graph.get_state(config).values
                status = final.get("decision_status", "completed")
                s.store.set_status(st.generations, gen_id, "completed" if status == "current" else "superseded",
                                   {"finished_at": _now(), "decision_id": final.get("decision_id")})
                s.bus.publish(run_id, case_id, "run.completed", f"{kind.capitalize()} finished ({status})",
                              {"generation_id": gen_id, "decision_id": final.get("decision_id"), "decision_status": status,
                               "tool_usage": final.get("tool_usage", {})})
            except Exception as exc:  # noqa: BLE001
                log.exception("generation %s failed", gen_id)
                s.store.set_status(st.generations, gen_id, "failed", {"error": str(exc)[:500], "finished_at": _now()})
                with s.store.tx() as c:
                    case = s.store.lock_case(c, run_id, case_id)
                    if case["active_generation_id"] == gen_id:
                        s.store.update_case(c, run_id, case_id, active_generation_id=None, revision=case["revision"] + 1,
                                            state="failed" if not case["current_decision_id"] else case["state"])
                    s.bus.publish(run_id, case_id, "run.failed", f"{kind.capitalize()} failed: {str(exc)[:200]}",
                                  {"generation_id": gen_id, "error": str(exc)[:500], "retryable": True})
            finally:
                with self._lock:
                    self._threads.pop(gen_id, None)
        self._after_generation(run_id, case_id, gen_id)

    def _initial(self, run_id: str, case_id: str, gen_id: str, kind: str, mode: str, trigger: Optional[dict], affected: Optional[list]) -> dict:
        return {"run_id": run_id, "case_id": case_id, "generation_id": gen_id, "kind": kind, "mode": mode,
                "trigger_id": (trigger or {}).get("trigger_id"), "trigger": trigger,
                "affected_candidate_ids": affected if kind == "reassessment" else None,
                "offers": {}, "public_leads": {}, "docs": {}, "facts": {}, "extraction_modes": {}, "checks": {}, "gaps": {},
                "followups_used": {}, "tasks": {}, "tool_usage": {}}

    def _after_generation(self, run_id: str, case_id: str, gen_id: str) -> None:
        """If newer changes arrived while this generation ran, start the coalesced reassessment."""
        s = self.s
        with s.store.tx() as c:
            case = s.store.lock_case(c, run_id, case_id)
            if case["active_generation_id"] == gen_id:
                s.store.update_case(c, run_id, case_id, active_generation_id=None)
        self._start_pending(run_id, case_id)

    def recover_interrupted(self) -> list[str]:
        """On process start: running generations were interrupted by the previous process."""
        s = self.s
        resumed = []
        if settings.job_backend == "vercel":
            # Another function may own a running generation. Queue redelivery and
            # database locks recover work; a cold API instance must not steal it.
            return resumed
        for row in s.store.find(st.generations, status="running"):
            gen = row["payload"]
            run_id, case_id = row["run_id"], row["case_id"]
            case = s.store.get_case(run_id, case_id)
            if not case or case["active_generation_id"] != gen["generation_id"]:
                s.store.set_status(st.generations, gen["generation_id"], "superseded", {"note": "not active at restart"})
                continue
            with s.store.tx() as c:
                cur = s.store.lock_case(c, run_id, case_id)
                s.store.kv_set(f"interrupted_state:{run_id}:{case_id}", cur["state"])
                s.store.update_case(c, run_id, case_id, state="interrupted", revision=cur["revision"] + 1)
                s.bus.publish(run_id, case_id, "run.interrupted", "Worker interrupted; recovering from last checkpoint",
                              {"generation_id": gen["generation_id"], "state_before": cur["state"]})
                s.bus.publish(run_id, case_id, "case.state_changed", "Case is now interrupted (resuming)", {"state": "interrupted"})
            inputs = s.store.kv_get(f"gen_inputs:{gen['generation_id']}") or {"affected": None, "triggers": []}
            self._launch(run_id, case_id, gen["generation_id"], kind=gen["kind"], mode=case["mode"],
                         trigger=inputs["triggers"][-1] if inputs.get("triggers") else None, affected=inputs.get("affected"), resume=True)
            resumed.append(gen["generation_id"])
        return resumed

    def wait_idle(self, timeout: float = 120.0) -> bool:
        """Test helper: wait for all generation threads to finish."""
        import time

        end = time.time() + timeout
        while time.time() < end:
            with self._lock:
                threads = list(self._threads.values())
            if not threads:
                time.sleep(0.05)
                with self._lock:
                    if not self._threads:
                        return True
                continue
            for t in threads:
                t.join(timeout=max(0.0, end - time.time()))
        return False

    def active_count(self) -> int:
        with self._lock:
            return len(self._threads)
