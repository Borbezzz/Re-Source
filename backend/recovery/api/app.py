"""FastAPI BFF (PRD §7): browser-safe API, case projections, commands, SSE event bridge, downloads.

Server credentials stay server-side. All mutations accept an `Idempotency-Key` header (or body
`idempotency_key`); a reused key with a different payload returns 409. Errors use the envelope
{code,message,retryable,case_revision,details,correlation_id}.
"""

from __future__ import annotations

import asyncio
import hashlib
import json
import logging
import uuid
import threading
import time
from contextlib import asynccontextmanager
from datetime import datetime, timezone
from typing import Any, Callable, Optional

from fastapi import FastAPI, File, Form, Header, Query, Request, UploadFile
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse, JSONResponse, Response, StreamingResponse
from fastapi.staticfiles import StaticFiles
from starlette.concurrency import run_in_threadpool

from ..adapters import store as st
from ..config import settings
from ..domain import models as M
from ..domain.errors import DomainError, conflict, invalid, not_found, unavailable
from ..runtime.tracing import init_tracing, tracing_state

log = logging.getLogger("recovery.api")
SERVICES: Any = None
_SERVICE_LOCK = threading.Lock()

def initialise_services() -> Any:
    global SERVICES
    with _SERVICE_LOCK:
        if SERVICES is None:
            from ..services.container import Services
            SERVICES = Services()
    return SERVICES


def services() -> Any:
    if SERVICES is None:
        raise unavailable("services not initialised")
    return SERVICES


@asynccontextmanager
async def lifespan(app: FastAPI):  # noqa: ANN201
    global SERVICES
    logging.basicConfig(level=logging.INFO)
    if not settings.serverless:
        await run_in_threadpool(init_tracing)
    # Remote diagnostic setup must not block every public HTTP cold start.
    # Serverless investigation workers initialise tracing with a bounded wait.
    started = time.monotonic()
    log.info("Startup: initialising durable services")
    SERVICES = await run_in_threadpool(initialise_services)
    log.info("Startup: durable services ready in %.2fs", time.monotonic() - started)
    if not settings.public_demo:
        await run_in_threadpool(SERVICES.scenario.ensure_run)
    await run_in_threadpool(SERVICES.coordinator.recover_interrupted)
    if settings.prewarm:
        import threading

        threading.Thread(target=SERVICES.prewarm, name="prewarm", daemon=True).start()
    yield
    SERVICES.stop()


app = FastAPI(title="Re-Source Aerospace Recovery API", version=M.SCHEMA_VERSION, lifespan=lifespan,
              description="Backend-for-frontend for the Re-Source aerospace recovery demonstration. Synthetic demo data is labelled data_origin=synthetic_demo.")
app.add_middleware(CORSMiddleware, allow_origins=["http://localhost:5173", "http://127.0.0.1:5173", "http://localhost:4173"],
                   allow_credentials=False, allow_methods=["*"], allow_headers=["*"])


@app.exception_handler(DomainError)
async def domain_error(request: Request, exc: DomainError) -> JSONResponse:
    return JSONResponse(status_code=exc.status, content={"code": exc.code, "message": exc.message, "retryable": exc.retryable,
                                                        "case_revision": exc.case_revision, "details": exc.details,
                                                        "correlation_id": request.headers.get("x-correlation-id") or str(uuid.uuid4())})


@app.exception_handler(RequestValidationError)
async def validation_error(request: Request, exc: RequestValidationError) -> JSONResponse:
    return JSONResponse(status_code=422, content={"code": "INVALID_INPUT", "message": "Request failed validation", "retryable": False,
                                                 "case_revision": None, "details": {"errors": json.loads(json.dumps(exc.errors(), default=str))},
                                                 "correlation_id": request.headers.get("x-correlation-id") or str(uuid.uuid4())})


@app.exception_handler(Exception)
async def unhandled(request: Request, exc: Exception) -> JSONResponse:
    log.exception("unhandled error")
    return JSONResponse(status_code=500, content={"code": "INTERNAL", "message": "An internal operation failed. Please retry.", "retryable": True, "case_revision": None,
                                                 "details": {}, "correlation_id": str(uuid.uuid4())})


def _hash(body: Any) -> str:
    return hashlib.sha256(json.dumps(body, sort_keys=True, default=str).encode()).hexdigest()


async def idempotent(scope: str, key: Optional[str], body: Any, fn: Callable[[], Any], status_code: int = 200) -> JSONResponse:
    s = services()
    if settings.job_backend == "vercel":
        await run_in_threadpool(s.jobs.recover_dispatches)
    if settings.public_demo:
        from ..runtime.context import visitor_id
        scope = f"visitor:{visitor_id.get()}:{scope}"
    if not key:
        key = f"auto-{uuid.uuid4()}"
    prior = await run_in_threadpool(s.store.idem_get, scope, key)
    h = _hash(body)
    if prior:
        if prior["request_hash"] != h:
            raise conflict("IDEMPOTENCY_KEY_REUSED", "Idempotency-Key was already used with a different payload")
        return JSONResponse(status_code=prior["status_code"], content=json.loads(prior["response"]), headers={"Idempotent-Replay": "true"})
    result = await run_in_threadpool(fn)
    content = json.loads(st.dumps(result))

    def save() -> None:
        try:
            with s.store.tx() as c:
                s.store.idem_put(c, scope, key, h, content, status_code)
        except Exception:  # noqa: BLE001 - a concurrent identical request already stored it
            pass

    await run_in_threadpool(save)
    return JSONResponse(status_code=status_code, content=content)


def _key(header: Optional[str], body: Optional[dict]) -> Optional[str]:
    return header or (body or {}).get("idempotency_key")


# ---------------------------------------------------------------------------------------------- health
@app.get("/api/v1/health")
async def health() -> dict:
    s = SERVICES
    return {"status": "ok" if s else "starting", "time": datetime.now(timezone.utc).isoformat(), "schema_version": M.SCHEMA_VERSION,
            "workers": s.coordinator.active_count() if s else 0}


@app.get("/api/v1/readiness", response_model=None, responses={200: {"model": M.Readiness}, 409: {"model": M.ApiError}, 422: {"model": M.ApiError}})
async def readiness(refresh: bool = False, detail: bool = False) -> dict:
    s = services()
    try:
        from ..services.readiness import capability_matrix

        matrix = await run_in_threadpool(capability_matrix, s, refresh)
    except Exception as exc:  # noqa: BLE001
        matrix = {"status": "degraded", "capabilities": {"readiness_module": {"ok": False, "detail": str(exc)[:200]}}}
    matrix.setdefault("capabilities", {})
    matrix["capabilities"].update({
        "operational_store": {"ok": True, "detail": "Lakebase Postgres" if not s.store.is_sqlite else "local SQLite (Lakebase not provisioned)"},
        "checkpointer": {"ok": True, "detail": s.checkpointer_kind},
        "tracing": tracing_state(),
        "model": {"ok": s.model.available, "model": s.model.model, "usage": s.model.usage, "last_error": s.model.last_error},
        "extraction": {"ok": True, "backend": s.extractor.last_mode, "last_error": s.extractor.last_error},
    })
    if not detail or settings.public_demo:  # public visitors cannot request internal errors
        for v in matrix["capabilities"].values():
            if isinstance(v, dict):
                v.pop("last_error", None)
    matrix["checked_at"] = matrix.get("checked_at") or datetime.now(timezone.utc).isoformat()
    return matrix


# ---------------------------------------------------------------------------------------------- engine / cases
@app.get("/api/v1/engines/{engine_id}", response_model=None, responses={200: {"model": M.EngineView}, 409: {"model": M.ApiError}, 422: {"model": M.ApiError}})
async def get_engine(engine_id: str, run_id: Optional[str] = None) -> dict:
    return await run_in_threadpool(services().views.engine, engine_id, run_id)


@app.get("/api/v1/cases/{case_id}", response_model=None, responses={200: {"model": M.CaseView}, 409: {"model": M.ApiError}, 422: {"model": M.ApiError}})
async def get_case(case_id: str, run_id: Optional[str] = None) -> dict:
    return await run_in_threadpool(services().views.case, case_id, run_id)


@app.post("/api/v1/cases/{case_id}/investigations", status_code=202, response_model=None, responses={202: {"model": M.CommandAccepted}, 409: {"model": M.ApiError}, 422: {"model": M.ApiError}})
async def start_investigation(case_id: str, body: M.StartInvestigationRequest, idempotency_key: Optional[str] = Header(None)) -> JSONResponse:
    s = services()
    rid = await run_in_threadpool(s.views.run_id, None)
    if not s.store.get_case(rid, case_id):
        raise not_found(f"case {case_id}")

    def run() -> dict:
        res = s.coordinator.start_investigation(rid, case_id, body.mode.value, body.expected_revision)
        return {"command_id": str(uuid.uuid4()), "run_id": rid, "case_id": case_id, "generation_id": res["generation_id"], "status": res["status"],
                "events_url": f"/api/v1/cases/{case_id}/events?run_id={rid}", "case_revision": res["case_revision"]}

    return await idempotent(f"investigate:{rid}:{case_id}", _key(idempotency_key, body.model_dump()), body.model_dump(mode="json"), run, 202)


@app.post("/api/v1/batches", status_code=202, response_model=None,
          responses={202: {"model": M.BatchInvestigation}, 409: {"model": M.ApiError}, 422: {"model": M.ApiError}})
async def create_batch(body: M.BatchInvestigationRequest, idempotency_key: str = Header(...)) -> JSONResponse:
    from ..services.batches import BatchService

    s = services()
    if settings.job_backend == "vercel":
        await run_in_threadpool(s.jobs.recover_dispatches)
    run_id = await run_in_threadpool(s.views.run_id, None)
    batch, replay = await run_in_threadpool(BatchService(s).create, run_id, body.model_dump(mode="json"), idempotency_key)
    headers = {"Idempotent-Replay": "true"} if replay else {}
    return JSONResponse(status_code=202, content=batch, headers=headers)


@app.get("/api/v1/batches/{batch_id}", response_model=None,
         responses={200: {"model": M.BatchInvestigation}, 404: {"model": M.ApiError}})
async def get_batch(batch_id: str) -> dict:
    from ..services.batches import BatchService

    return await run_in_threadpool(BatchService(services()).get, batch_id)


@app.get("/api/v1/cases/{case_id}/decisions")
async def list_decisions(case_id: str, run_id: Optional[str] = None) -> list[dict]:
    s = services()
    rid = await run_in_threadpool(s.views.run_id, run_id)
    rows = await run_in_threadpool(s.decisions.list, rid, case_id)
    return [{k: d[k] for k in ("decision_id", "label", "status", "created_at", "preferred_candidate_id", "trigger_id", "summary", "input_revision",
                               "case_revision", "evidence_hash")} for d in rows]


@app.get("/api/v1/cases/{case_id}/decisions/{decision_id}", response_model=None, responses={200: {"model": M.DecisionSnapshot}, 409: {"model": M.ApiError}, 422: {"model": M.ApiError}})
async def get_decision(case_id: str, decision_id: str, include_facts: bool = False) -> dict:
    d = await run_in_threadpool(services().decisions.get, decision_id)
    if not d or d["case_id"] != case_id:
        raise not_found(f"decision {decision_id}")
    if settings.public_demo:
        from ..runtime.context import visitor_id
        if services().store.kv_get(f"run_owner:{d['scenario_run_id']}") != visitor_id.get():
            raise not_found("decision")
    if not include_facts:
        d = {k: v for k, v in d.items() if k != "facts"}
    return d


@app.get("/api/v1/cases/{case_id}/diff", response_model=None, responses={200: {"model": M.DecisionDiff}, 409: {"model": M.ApiError}, 422: {"model": M.ApiError}})
async def get_diff(case_id: str, from_: str = Query(..., alias="from"), to: str = Query(...), run_id: Optional[str] = None) -> dict:
    s = services()
    rid = await run_in_threadpool(s.views.run_id, run_id)
    d = await run_in_threadpool(s.decisions.get_diff, rid, case_id, from_, to)
    if not d:
        raise not_found("diff")
    return d


@app.post("/api/v1/cases/{case_id}/selections", response_model=None, responses={200: {"model": M.Selection}, 409: {"model": M.ApiError}, 422: {"model": M.ApiError}})
async def create_selection(case_id: str, body: M.SelectionRequest, idempotency_key: Optional[str] = Header(None),
                           x_forwarded_email: Optional[str] = Header(None)) -> JSONResponse:
    s = services()
    if x_forwarded_email and not settings.public_demo:  # Databricks Apps forward the signed-in user's identity; selections record the real actor
        body = body.model_copy(update={"actor": x_forwarded_email})
    if settings.public_demo:
        from ..runtime.context import PUBLIC_ACTOR
        body = body.model_copy(update={"actor": PUBLIC_ACTOR})
    rid = await run_in_threadpool(s.views.run_id, None)
    key = _key(idempotency_key, body.model_dump()) or f"auto-{uuid.uuid4()}"
    return await idempotent(f"select:{rid}:{case_id}", key, body.model_dump(mode="json", exclude={"idempotency_key"}),
                            lambda: s.selection.accept(rid, case_id, body.model_dump(mode="json"), key), 200)


@app.get("/api/v1/cases/{case_id}/documents", response_model=None, responses={200: {"model": M.DocumentsView}, 409: {"model": M.ApiError}, 422: {"model": M.ApiError}})
async def get_documents(case_id: str, run_id: Optional[str] = None) -> dict:
    s = services()
    if s.documents is None:
        raise unavailable("document service not available")
    rid = await run_in_threadpool(s.views.run_id, run_id)
    return await run_in_threadpool(s.documents.view, rid, case_id)


@app.patch("/api/v1/documents/{target_id}")
async def patch_document(target_id: str, body: M.DocumentPatchRequest, idempotency_key: Optional[str] = Header(None)) -> JSONResponse:
    s = services()
    if s.documents is None:
        raise unavailable("document service not available")
    if settings.public_demo:
        from ..runtime.context import PUBLIC_ACTOR
        body = body.model_copy(update={"actor": PUBLIC_ACTOR})
    rid = await run_in_threadpool(s.views.run_id, None)
    return await idempotent(f"doc:{rid}:{target_id}", _key(idempotency_key, body.model_dump()), body.model_dump(mode="json", exclude={"idempotency_key"}),
                            lambda: s.documents.patch(rid, target_id, body.model_dump(mode="json")))


@app.get("/api/v1/packages/{package_id}/download", response_class=HTMLResponse)
async def download_package(package_id: str, run_id: Optional[str] = None) -> HTMLResponse:
    s = services()
    if s.documents is None:
        raise unavailable("document service not available")
    rid = await run_in_threadpool(s.views.run_id, run_id)
    html = await run_in_threadpool(s.documents.render_package_html, rid, package_id)
    return HTMLResponse(html, headers={"Content-Disposition": f'inline; filename="{package_id}.html"'})


@app.post("/api/v1/cases/{case_id}/simulated-submissions", response_model=None, responses={200: {"model": M.SimulatedReceipt}, 409: {"model": M.ApiError}, 422: {"model": M.ApiError}})
async def simulate_submission(case_id: str, body: M.SubmissionRequest, idempotency_key: Optional[str] = Header(None)) -> JSONResponse:
    s = services()
    if s.documents is None:
        raise unavailable("document service not available")
    rid = await run_in_threadpool(s.views.run_id, None)
    return await idempotent(f"submit:{rid}:{case_id}", _key(idempotency_key, body.model_dump()), body.model_dump(mode="json", exclude={"idempotency_key"}),
                            lambda: s.documents.submit(rid, case_id, body.model_dump(mode="json")))


@app.get("/api/v1/evidence/{version_id}", response_model=None, responses={200: {"model": M.EvidenceView}, 409: {"model": M.ApiError}, 422: {"model": M.ApiError}})
async def get_evidence(version_id: str, run_id: Optional[str] = None) -> dict:
    return await run_in_threadpool(services().views.evidence, version_id, run_id)


@app.get("/api/v1/evidence")
async def search_evidence(q: str, doc_type: Optional[str] = None, run_id: Optional[str] = None, limit: int = 8) -> dict:
    s = services()
    if s.search is None:
        raise unavailable("evidence search not available")
    rid = await run_in_threadpool(s.views.run_id, run_id)
    return await run_in_threadpool(lambda: s.search.search(q, filters={"doc_type": doc_type} if doc_type else {}, run_id=rid, limit=limit))


@app.patch("/api/v1/cases/{case_id}/monitoring")
async def patch_monitoring(case_id: str, body: M.MonitoringRequest, idempotency_key: Optional[str] = Header(None)) -> JSONResponse:
    s = services()
    rid = await run_in_threadpool(s.views.run_id, None)
    return await idempotent(f"monitor:{rid}:{case_id}", _key(idempotency_key, body.model_dump()), body.model_dump(mode="json", exclude={"idempotency_key"}),
                            lambda: s.monitoring.set_status(rid, case_id, body.status.value, body.expected_revision))


@app.post("/api/v1/cases/{case_id}/visual-actions", response_model=None, responses={200: {"model": M.VisualActionResult}, 409: {"model": M.ApiError}, 422: {"model": M.ApiError}})
async def visual_action(case_id: str, body: M.VisualActionRequest, idempotency_key: Optional[str] = Header(None)) -> JSONResponse:
    s = services()
    rid = await run_in_threadpool(s.views.run_id, None)
    key = _key(idempotency_key, body.model_dump())
    if not key:
        return JSONResponse(content=json.loads(st.dumps(await run_in_threadpool(s.scenario.visual_action, rid, case_id, body.action))))
    return await idempotent(f"visual:{rid}:{case_id}", key, body.model_dump(mode="json", exclude={"idempotency_key"}),
                            lambda: s.scenario.visual_action(rid, case_id, body.action))


# ---------------------------------------------------------------------------------------------- scenario runs
@app.post("/api/v1/scenario-runs", status_code=201, response_model=None, responses={201: {"model": M.ScenarioRunView}, 409: {"model": M.ApiError}, 422: {"model": M.ApiError}})
async def create_run(body: M.ScenarioRunRequest, idempotency_key: Optional[str] = Header(None)) -> JSONResponse:
    s = services()
    return await idempotent("runs", _key(idempotency_key, body.model_dump()), body.model_dump(mode="json", exclude={"idempotency_key"}),
                            lambda: s.scenario.create_run(body.mode.value, body.manifest_id, body.fixture_version, body.replay_source_run_id), 201)


@app.get("/api/v1/scenario-runs/current", response_model=None, responses={200: {"model": M.ScenarioRunView}, 409: {"model": M.ApiError}, 422: {"model": M.ApiError}})
async def current_run() -> dict:
    return await run_in_threadpool(services().scenario.ensure_run)


@app.get("/api/v1/scenario-runs/{run_id}", response_model=None, responses={200: {"model": M.ScenarioRunView}, 409: {"model": M.ApiError}, 422: {"model": M.ApiError}})
async def get_run(run_id: str) -> dict:
    return await run_in_threadpool(services().scenario.view, run_id)


@app.get("/api/v1/scenario-runs/{run_id}/signals/catalog")
async def signal_catalog(run_id: str) -> dict:
    s = services()
    received = {r["payload"]["signal_id"]: r["status"] for r in s.run_state.signal_rows(run_id)}
    sigs = [{"fixture_signal_id": fid, "signal_id": x["signal_id"], "title": x["title"], "category": x["category"], "version": x["version"],
             "status": x["status"], "label": x.get("label", "Scenario signal"), "effective_from": x["effective_from"],
             "scope": x["scope"], "received_state": received.get(x["signal_id"]),
             "primary": fid == s.catalog.scenario.get("primary_signal_fixture_id")} for fid, x in s.catalog.signals.items()]
    changes = [{"fixture_evidence_change_id": fid, "title": c["title"], "note": c.get("note")} for fid, c in s.catalog.evidence_changes.items()]
    return {"signals": sigs, "evidence_changes": changes, "active_signals": s.run_state.active_signals(run_id)}


@app.post("/api/v1/scenario-runs/{run_id}/signals", response_model=None, responses={200: {"model": M.SignalInjectionResult}, 409: {"model": M.ApiError}, 422: {"model": M.ApiError}})
async def inject_signal(run_id: str, body: M.SignalInjectionRequest, idempotency_key: Optional[str] = Header(None)) -> JSONResponse:
    s = services()
    if not s.store.get_run(run_id):
        raise not_found(f"run {run_id}")
    if not body.fixture_signal_id and not body.signal:
        raise invalid("Provide fixture_signal_id or signal")
    return await idempotent(f"signal:{run_id}", _key(idempotency_key, body.model_dump()), body.model_dump(mode="json", exclude={"idempotency_key"}),
                            lambda: s.changes.inject_signal(run_id, body.fixture_signal_id, body.signal.model_dump(mode="json") if body.signal else None))


@app.get("/api/v1/scenario-runs/{run_id}/signal-sources")
async def signal_sources(run_id: str) -> list[dict]:
    from ..services.signal_sources import SignalSources

    return await run_in_threadpool(SignalSources(services()).status, run_id)


@app.post("/api/v1/scenario-runs/{run_id}/signal-sources/linkup-news/poll")
async def poll_live_signals(run_id: str, ingest: bool = False) -> dict:
    """Live public-news monitoring through the same ingestion gateway (candidates only unless ingest=true)."""
    from ..services.signal_sources import SignalSources

    s = services()
    if not s.store.get_run(run_id):
        raise not_found(f"run {run_id}")
    return await run_in_threadpool(lambda: SignalSources(s).poll_live(run_id, ingest=ingest))


@app.post("/api/v1/scenario-runs/{run_id}/evidence-changes", response_model=None, responses={200: {"model": M.SignalInjectionResult}, 409: {"model": M.ApiError}, 422: {"model": M.ApiError}})
async def inject_evidence_change(run_id: str, body: M.EvidenceChangeRequest, idempotency_key: Optional[str] = Header(None)) -> JSONResponse:
    s = services()
    return await idempotent(f"evidence-change:{run_id}", _key(idempotency_key, body.model_dump()), body.model_dump(mode="json", exclude={"idempotency_key"}),
                            lambda: s.changes.inject_evidence_change(run_id, body.fixture_evidence_change_id))


@app.post("/api/v1/scenario-runs/{run_id}/template-changes")
async def inject_template_change(run_id: str, body: M.TemplateChangeRequest, idempotency_key: Optional[str] = Header(None)) -> JSONResponse:
    s = services()
    return await idempotent(f"template-change:{run_id}", _key(idempotency_key, body.model_dump()), body.model_dump(mode="json", exclude={"idempotency_key"}),
                            lambda: s.changes.inject_template_change(run_id, body.template_id, body.revision, body.note))


@app.post("/api/v1/scenario-runs/{run_id}/clock", response_model=None, responses={200: {"model": M.ClockState}, 409: {"model": M.ApiError}, 422: {"model": M.ApiError}})
async def advance_clock(run_id: str, body: M.ClockAdvanceRequest, idempotency_key: Optional[str] = Header(None)) -> JSONResponse:
    s = services()
    return await idempotent(f"clock:{run_id}", _key(idempotency_key, body.model_dump()), body.model_dump(mode="json", exclude={"idempotency_key"}),
                            lambda: s.changes.advance_clock(run_id, body.hours))


# ---------------------------------------------------------------------------------------------- events (SSE)
async def _sse(run_id: str, case_id: str, after: int, request: Request):  # noqa: ANN202
    s = services()
    q = s.bus.subscribe(run_id, case_id)
    last = after
    deadline = time.monotonic() + settings.sse_max_seconds
    try:
        yield "retry: 1000\n\n"
        max_seq = await run_in_threadpool(s.store.max_sequence, run_id, case_id)
        if after > max_seq:
            ctrl = {"type": "control.snapshot_required", "summary": "Event cursor is ahead of retained history; refresh the case projection",
                    "case_id": case_id, "scenario_run_id": run_id, "sequence": max_seq}
            yield f"event: control\ndata: {json.dumps(ctrl)}\n\n"
            last = max_seq
        backlog = await run_in_threadpool(s.store.events_after, run_id, case_id, last, 5000)
        for e in backlog:
            last = e["sequence"]
            yield f"id: {e['sequence']}\ndata: {st.dumps(e)}\n\n"
        while time.monotonic() < deadline:
            if await request.is_disconnected():
                break
            # Lakebase is authoritative across instances. Local notifications
            # only shorten the wait; they cannot be the delivery authority.
            try:
                await asyncio.wait_for(q.get(), timeout=1.0)
            except asyncio.TimeoutError:
                pass
            batch = await run_in_threadpool(s.store.events_after, run_id, case_id, last, 5000)
            for event in batch:
                last = event["sequence"]
                yield f"id: {last}\ndata: {st.dumps(event)}\n\n"
            if not batch:
                yield ": heartbeat\n\n"
    finally:
        s.bus.unsubscribe(run_id, case_id, q)


@app.get("/api/v1/cases/{case_id}/events")
async def case_events(case_id: str, request: Request, after: int = 0, run_id: Optional[str] = None,
                      last_event_id: Optional[str] = Header(None)) -> StreamingResponse:
    s = services()
    rid = await run_in_threadpool(s.views.run_id, run_id)
    if not s.store.get_case(rid, case_id):
        raise not_found(f"case {case_id}")
    if last_event_id and last_event_id.isdigit():
        after = max(after, int(last_event_id))
    return StreamingResponse(_sse(rid, case_id, after, request), media_type="text/event-stream",
                             headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"})


@app.get("/api/v1/scenario-runs/{run_id}/events")
async def run_events(run_id: str, request: Request, after: int = 0, last_event_id: Optional[str] = Header(None)) -> StreamingResponse:
    if last_event_id and last_event_id.isdigit():
        after = max(after, int(last_event_id))
    return StreamingResponse(_sse(run_id, "__run__", after, request), media_type="text/event-stream", headers={"Cache-Control": "no-cache"})


@app.get("/api/v1/cases/{case_id}/events/history", response_model=None,
         responses={200: {"model": list[M.DomainEvent | M.SupplierDiscoveryEvent]}})
async def case_event_history(case_id: str, after: int = 0, run_id: Optional[str] = None, limit: int = 1000) -> list[dict]:
    s = services()
    rid = await run_in_threadpool(s.views.run_id, run_id)
    return await run_in_threadpool(s.store.events_after, rid, case_id, after, limit)


# ============================================================================================== intake & mesh (contract v1.1)
_ERR = {404: {"model": M.ApiError}, 409: {"model": M.ApiError}, 413: {"model": M.ApiError}, 422: {"model": M.ApiError}}


def _intake() -> Any:
    s = services()
    if getattr(s, "intake", None) is None:
        raise unavailable("intake service not available")
    return s.intake


@app.post("/api/v1/intake/uploads", status_code=201, response_model=None, responses={201: {"model": M.IntakeUpload}, **_ERR})
async def intake_upload(file: UploadFile = File(...), kind: str = Form(...), engine_id: str = Form("engine-demo-001"),
                        component_id: Optional[str] = Form(None)) -> JSONResponse:
    """Upload a blueprint, part-requirements document or segmented GLB. Content-addressed: identical bytes return the existing upload."""
    from ..services.intake import MAX_UPLOAD_BYTES

    buf = bytearray()
    while chunk := await file.read(1024 * 1024):
        buf.extend(chunk)
        if len(buf) > MAX_UPLOAD_BYTES:
            raise DomainError(413, "PAYLOAD_TOO_LARGE", f"upload exceeds {MAX_UPLOAD_BYTES // (1024 * 1024)} MB")
    rec = await run_in_threadpool(_intake().upload, bytes(buf), file.filename or "upload", kind, engine_id, component_id or None)
    return JSONResponse(status_code=201 if not rec.get("duplicate_of") else 200, content=json.loads(st.dumps(rec)))


@app.get("/api/v1/intake/uploads/{upload_id}", response_model=None, responses={200: {"model": M.IntakeUpload}, **_ERR})
async def intake_get_upload(upload_id: str) -> dict:
    svc = _intake()
    return svc.public_upload(await run_in_threadpool(svc.get_upload, upload_id))


@app.get("/api/v1/intake/uploads/{upload_id}/content", response_class=Response)
async def intake_upload_content(upload_id: str) -> Response:
    """Raw bytes with the stored media type (e.g. an activated GLB for the 3D scene)."""
    data, media_type, filename = await run_in_threadpool(_intake().content, upload_id)
    return Response(content=data, media_type=media_type, headers={"Content-Disposition": f'inline; filename="{filename}"',
                                                                  "Cache-Control": "private, max-age=3600", "X-Content-Type-Options": "nosniff"})


@app.post("/api/v1/intake/part-requirements", status_code=202, response_model=None, responses={202: {"model": M.PartRequirementDraft}, **_ERR})
async def intake_part_requirements(body: M.PartRequirementRequest, idempotency_key: Optional[str] = Header(None)) -> JSONResponse:
    svc = _intake()
    return await idempotent("intake:preq", _key(idempotency_key, body.model_dump()), body.model_dump(mode="json", exclude={"idempotency_key"}),
                            lambda: svc.start_part_requirements(body.upload_id, body.component_id), 202)


@app.get("/api/v1/intake/part-requirements/{draft_id}", response_model=None, responses={200: {"model": M.PartRequirementDraft}, **_ERR})
async def intake_get_draft(draft_id: str) -> dict:
    return await run_in_threadpool(_intake().get_draft, draft_id)


@app.patch("/api/v1/intake/part-requirements/{draft_id}", response_model=None, responses={200: {"model": M.PartRequirementDraft}, **_ERR})
async def intake_patch_draft(draft_id: str, body: M.PartRequirementPatch, idempotency_key: Optional[str] = Header(None)) -> JSONResponse:
    svc = _intake()
    if settings.public_demo:
        from ..runtime.context import PUBLIC_ACTOR
        body = body.model_copy(update={"actor": PUBLIC_ACTOR})
    return await idempotent(f"intake:preq:{draft_id}", _key(idempotency_key, body.model_dump()), body.model_dump(mode="json", exclude={"idempotency_key"}),
                            lambda: svc.patch_draft(draft_id, body.model_dump(mode="json")))


@app.post("/api/v1/intake/mesh-jobs", status_code=201, response_model=None, responses={201: {"model": M.MeshJob}, **_ERR})
async def intake_mesh_job(body: M.MeshJobRequest, idempotency_key: Optional[str] = Header(None)) -> JSONResponse:
    svc = _intake()
    payload = body.model_dump(mode="json", exclude={"idempotency_key"})
    return await idempotent("intake:mesh", _key(idempotency_key, body.model_dump()), payload, lambda: svc.create_mesh_job(payload), 201)


@app.get("/api/v1/intake/mesh-jobs/{job_id}", response_model=None, responses={200: {"model": M.MeshJob}, **_ERR})
async def intake_get_mesh_job(job_id: str) -> dict:
    return await run_in_threadpool(_intake().get_job, job_id)


@app.post("/api/v1/intake/mesh-jobs/{job_id}/activate", response_model=None, responses={200: {"model": M.ManifestProvenance}, **_ERR})
async def intake_activate_mesh_job(job_id: str) -> dict:
    prov = await run_in_threadpool(_intake().activate_job, job_id)
    return {k: v for k, v in prov.items() if k != "anchors"}


@app.get("/api/v1/intake/manifest", response_model=None, responses={200: {"model": M.ManifestProvenance}})
async def intake_manifest() -> dict:
    prov = await run_in_threadpool(_intake().provenance)
    return {k: v for k, v in prov.items() if k != "anchors"}


@app.post("/api/v1/intake/manifest/reset", response_model=None, responses={200: {"model": M.ManifestProvenance}})
async def intake_manifest_reset() -> dict:
    prov = await run_in_threadpool(_intake().reset_manifest)
    return {k: v for k, v in prov.items() if k != "anchors"}
# ============================================================================================== end intake & mesh


# ---------------------------------------------------------------------------------------------- frontend bundle
if settings.frontend_dist.exists():
    app.mount("/", StaticFiles(directory=str(settings.frontend_dist), html=True), name="frontend")
else:
    @app.get("/", response_class=HTMLResponse, include_in_schema=False)
    async def root() -> str:
        return ("<html><body style='font-family:system-ui;padding:2rem'><h1>Re-Source API</h1><p>The frontend bundle (frontend/dist) is not built yet. "
                "API docs: <a href='/docs'>/docs</a>. Contract: interface.md.</p></body></html>")

from ..runtime.public_demo import PublicDemoSession
app.add_middleware(PublicDemoSession, service_provider=initialise_services)
