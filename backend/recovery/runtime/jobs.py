"""Durable Vercel queue deliveries. Messages carry IDs; payload/state stay in Lakebase.

A session advisory lock prevents concurrent duplicate execution. A killed worker
releases the lock; queue redelivery resumes the graph from its Postgres checkpoint.
"""
from __future__ import annotations

import uuid
from contextlib import contextmanager
from datetime import timedelta
from typing import Any

from sqlalchemy import text, select
from vercel.queue import Topic
from vercel.queue.sync import send
from pydantic import BaseModel

from .context import job_run_id, visitor_id


class JobMessage(BaseModel):
    job_id: str


topic = Topic[JobMessage]("resource-jobs")


class DurableJobs:
    def __init__(self, services: Any):
        self.s = services

    def enqueue(self, kind: str, run_id: str, payload: dict, key: str | None = None) -> str:
        job_id = key or str(uuid.uuid4())
        self.prepare(kind, run_id, payload, job_id)
        self.dispatch(job_id)
        return job_id

    def prepare(self, kind: str, run_id: str, payload: dict, job_id: str) -> None:
        """Write in the caller's transaction; publication happens after commit."""
        record_key = f"job:{job_id}"
        prior = self.s.store.kv_get(record_key)
        if not prior:
            self.s.store.kv_set(record_key, {"kind": kind, "run_id": run_id, "payload": payload, "status": "pending",
                                           "visitor_id": visitor_id.get()})

    def dispatch(self, job_id: str) -> None:
        job = self.s.store.kv_get(f"job:{job_id}")
        if not job or job["status"] == "done" or self.s.store.kv_get(f"dispatched:{job_id}"):
            return
        send(topic, JobMessage(job_id=job_id), idempotency_key=job_id, retention=timedelta(days=1))
        # Separate key avoids racing a fast worker's completed record.
        self.s.store.kv_set(f"dispatched:{job_id}", True)

    def recover_dispatches(self) -> None:
        """Bounded request-time recovery of committed but unpublished work.

        No resident polling thread. Queue retries own already-published work.
        """
        from ..adapters import store as st
        with self.s.store.engine.connect() as conn:
            rows = conn.execute(select(st.kv.c.key, st.kv.c.value).where(st.kv.c.key.like("job:%"))).all()
        recovered = 0
        for key, value in rows:
            job = st.loads(value)
            job_id = key[4:]
            if job.get("visitor_id") == visitor_id.get() and job["status"] == "pending" and not self.s.store.kv_get(f"dispatched:{job_id}"):
                self.dispatch(job_id)
                recovered += 1
                if recovered == 10:
                    break

    @contextmanager
    def lock(self, key: str):
        if self.s.store.is_sqlite:
            raise RuntimeError("Durable queue execution requires Postgres")
        with self.s.store.engine.connect() as conn:
            acquired = conn.execute(text("SELECT pg_try_advisory_lock(hashtextextended(:key, 0))"), {"key": key}).scalar()
            conn.commit()
            if not acquired:
                raise RuntimeError("Job is already owned by another worker; retry delivery")
            try:
                yield
            finally:
                conn.execute(text("SELECT pg_advisory_unlock(hashtextextended(:key, 0))"), {"key": key})
                conn.commit()

    def execute(self, job_id: str) -> None:
        key = f"job:{job_id}"
        job = self.s.store.kv_get(key)
        if not job:
            raise ValueError("Unknown durable job")
        lock_key = "resource:outbox" if job["kind"] == "outbox" else key
        with self.lock(lock_key):
            job = self.s.store.kv_get(key)
            if job["status"] == "done":
                return
            owner = visitor_id.set(job.get("visitor_id"))
            run = job_run_id.set(None if job["run_id"] == "__system__" else job["run_id"])
            try:
                self._perform(job)
                if job["kind"].startswith("product_"):
                    from ..config import settings
                    if settings.job_backend == "vercel":
                        # A committed continuation must be published before the
                        # parent delivery is acknowledged. If publication fails,
                        # queue redelivery retries without requiring an open tab.
                        self.recover_dispatches()
                self.s.store.kv_set(key, {**job, "status": "done"})
            finally:
                visitor_id.reset(owner)
                job_run_id.reset(run)

    def _perform(self, job: dict) -> None:
        from ..adapters import store as st
        p = job["payload"]
        if job["kind"] == "generation":
            row = self.s.store.get(st.generations, p["gen_id"])
            if row and row["status"] == "running":
                inputs = self.s.store.kv_get(f"gen_inputs:{p['gen_id']}")
                if inputs and inputs.get("triggers"):
                    trigger = dict(inputs["triggers"][-1])
                    if len(inputs["triggers"]) > 1:
                        trigger["coalesced_trigger_ids"] = [t.get("trigger_id") for t in inputs["triggers"]]
                        trigger["impact_paths"] = [path for t in inputs["triggers"] for path in t.get("impact_paths", [])]
                    p = {**p, "trigger": trigger, "affected": inputs.get("affected")}
                self.s.coordinator._run(run_id=job["run_id"], **p, resume=True)
        elif job["kind"] == "extract":
            draft = self.s.intake.get_draft(p["draft_id"])
            if draft["status"] == "extracting":
                self.s.intake._extract_safe(p["draft_id"])
        elif job["kind"] == "product_extract":
            self.s.products.extract_project(**p)
        elif job["kind"] == "product_research":
            self.s.products.research_part(**p)
        elif job["kind"] == "product_agent":
            self.s.products.run_agent(**p)
        elif job["kind"] == "outbox":
            self.s.process_outbox_once()
            if self.s.store.find(st.outbox, status="pending", op_type="generate_documents"):
                raise RuntimeError("Document outbox still contains retryable work")
        elif job["kind"] == "replay":
            self.s.scenario._replay(p["source_run_id"], job["run_id"])
        else:
            raise ValueError("Unsupported job kind")
