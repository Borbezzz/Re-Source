"""Create and inspect run-scoped batches of independent investigations."""

from __future__ import annotations

import hashlib
import json
import uuid
from typing import Any

from ..adapters import store as st
from ..config import settings
from ..domain.errors import conflict, invalid, not_found
from ..domain.models import Mode
from ..runtime.context import visitor_id


class BatchService:
    def __init__(self, services: Any):
        self.s = services

    def create(self, run_id: str, request: dict, key: str) -> tuple[dict, bool]:
        if not key:
            raise invalid("Idempotency-Key is required")
        selected = request["component_ids"]
        if not selected or len(selected) != len(set(selected)):
            raise invalid("Select one or more distinct components")
        if request["assembly_id"] != self.s.catalog.engine["engine_id"]:
            raise not_found("assembly")
        if request["mode"] not in {mode.value for mode in Mode}:
            raise invalid("Unknown investigation mode")

        request_hash = hashlib.sha256(st.dumps(request).encode()).hexdigest()
        scope = f"batch:{run_id}"
        with self.s.store.tx() as connection:
            self.s.store.lock_run(connection, run_id)
            owner = self.s.store.kv_get(f"run_owner:{run_id}")
            if (settings.public_demo and not visitor_id.get()) or (settings.public_demo or owner) and owner != visitor_id.get():
                raise not_found("run")
            previous = self.s.store.idem_get(scope, key)
            if previous:
                if previous["request_hash"] != request_hash:
                    raise conflict("IDEMPOTENCY_KEY_REUSED", "Idempotency-Key was already used with a different payload")
                return json.loads(previous["response"]), True

            cases = {row["component_id"]: row for row in self.s.store.list_cases(run_id)}
            if any(component_id not in cases for component_id in selected):
                raise invalid("Every component must belong to the current assembly and run")
            batch_id = f"batch-{uuid.uuid4().hex}"
            components = []
            for component_id in selected:
                case = cases[component_id]
                generation = self.s.coordinator.start_investigation(run_id, case["case_id"], request["mode"], None)
                components.append({
                    "component_id": component_id,
                    "case_id": case["case_id"],
                    "generation_id": generation["generation_id"],
                    "status": generation["status"],
                    "events_url": f"/api/v1/cases/{case['case_id']}/events?run_id={run_id}",
                })
            batch = {"batch_id": batch_id, "run_id": run_id, "assembly_id": request["assembly_id"],
                     "mode": request["mode"], "created_at": st.now_iso(), "components": components}
            self.s.store.kv_set(f"batch:{batch_id}", batch)
            self.s.store.idem_put(connection, scope, key, request_hash, batch, 202)
        return batch, False

    def get(self, batch_id: str) -> dict:
        batch = self.s.store.kv_get(f"batch:{batch_id}")
        if not batch:
            raise not_found("batch")
        run_id = batch["run_id"]
        owner = self.s.store.kv_get(f"run_owner:{run_id}")
        if (settings.public_demo and not visitor_id.get()) or (settings.public_demo or owner) and owner != visitor_id.get():
            raise not_found("batch")
        components = []
        for part in batch["components"]:
            generation_id = part["generation_id"]
            generation = self.s.store.get(st.generations, generation_id) if generation_id else None
            components.append({
                **part,
                "generation_status": generation["status"] if generation else None,
                "tasks": self.s.views.tasks(run_id, part["case_id"], generation_id),
            })
        return {**batch, "components": components}
