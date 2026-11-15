"""Additive product API; legacy engine routes and contracts are unchanged."""
from __future__ import annotations

import logging
from collections.abc import Callable
from typing import Annotated

from fastapi import APIRouter, File, Form, Header, UploadFile
from fastapi.responses import Response
from starlette.concurrency import run_in_threadpool

from ..config import settings
from ..domain import products as P
from ..domain.errors import DomainError

log = logging.getLogger("recovery.api.products")


def product_router(service_provider: Callable, idempotent: Callable) -> APIRouter:
    router = APIRouter(prefix="/api/v1/products", tags=["Product projects"])

    def service():
        return service_provider().products

    async def command(project_id: str, action: str, key: str | None, body: dict, fn: Callable, status: int = 200):
        return await idempotent(f"product:{project_id}:{action}", key, body, fn, status)

    @router.get("/demos", response_model=list[P.DemoProduct])
    async def demos():
        return await run_in_threadpool(service().demos)

    @router.post("", response_model=P.ProductProject, status_code=201)
    async def create(body: P.ProductCreateRequest, idempotency_key: str | None = Header(None)):
        return await command("new", "create", idempotency_key, body.model_dump(), lambda: service().create(body.demo_id, body.name), 201)

    @router.get("/{project_id}", response_model=P.ProductProject)
    async def project(project_id: str):
        # Check ownership before dispatch recovery. Every returned record is scoped
        # by the opaque visitor session, even if a project ID is guessed.
        result = await run_in_threadpool(service().get, project_id)
        if settings.job_backend == "vercel":
            try:
                await run_in_threadpool(service_provider().jobs.recover_dispatches)
            except Exception:  # noqa: BLE001 - read access must survive a temporarily unavailable queue
                log.warning("Product queue dispatch recovery deferred")
        return result

    @router.post("/{project_id}/documents", response_model=P.ProductProject, status_code=201)
    async def upload(project_id: str, file: Annotated[UploadFile, File()], kind: Annotated[str, Form()]):
        from ..services.intake import MAX_UPLOAD_BYTES
        buf = bytearray()
        while chunk := await file.read(1024 * 1024):
            buf.extend(chunk)
            if len(buf) > MAX_UPLOAD_BYTES:
                raise DomainError(413, "PAYLOAD_TOO_LARGE", "The file exceeds the upload limit.")
        return await run_in_threadpool(service().upload, project_id, bytes(buf), file.filename or "upload", kind)

    @router.get("/{project_id}/documents/{document_id}/content", response_class=Response)
    async def content(project_id: str, document_id: str):
        data, media, _ = await run_in_threadpool(service().content, project_id, document_id)
        return Response(data, media_type=media, headers={"Cache-Control": "private, no-store", "X-Content-Type-Options": "nosniff"})

    @router.post("/{project_id}/extract", response_model=P.ProductProject, status_code=202)
    async def extract(project_id: str, idempotency_key: str | None = Header(None)):
        return await command(project_id, "extract", idempotency_key, {}, lambda: service().start_extraction(project_id), 202)

    @router.patch("/{project_id}/parts", response_model=P.ProductProject)
    async def review(project_id: str, body: P.ProductPartsRequest, idempotency_key: str | None = Header(None)):
        payload = body.model_dump(mode="json")
        return await command(project_id, "parts", idempotency_key, payload, lambda: service().review(project_id, **payload))

    @router.post("/{project_id}/model", response_model=P.ProductProject)
    async def model(project_id: str, body: P.ProductModelRequest, idempotency_key: str | None = Header(None)):
        return await command(project_id, "model", idempotency_key, body.model_dump(), lambda: service().set_model(project_id, body.origin, body.document_id))

    @router.post("/{project_id}/investigations", response_model=P.ProductProject, status_code=202)
    async def investigate(project_id: str, body: P.ProductInvestigateRequest, idempotency_key: str | None = Header(None)):
        return await command(project_id, "investigate", idempotency_key, body.model_dump(), lambda: service().investigate(project_id, body.part_ids, body.mode), 202)

    @router.patch("/{project_id}/selections", response_model=P.ProductProject)
    async def select(project_id: str, body: P.ProductSelectionRequest, idempotency_key: str | None = Header(None)):
        return await command(project_id, "select", idempotency_key, body.model_dump(), lambda: service().select_candidate(project_id, body.part_id, body.candidate_id))

    @router.post("/{project_id}/package", response_model=P.ProductProject)
    async def package(project_id: str, idempotency_key: str | None = Header(None)):
        return await command(project_id, "package", idempotency_key, {}, lambda: service().build_package(project_id))

    @router.post("/{project_id}/package/approve", response_model=P.ProductProject)
    async def approve(project_id: str, body: P.ProductApprovalRequest, idempotency_key: str | None = Header(None)):
        return await command(project_id, "approve", idempotency_key, body.model_dump(), lambda: service().approve_package(project_id, body.acknowledge_unverified, body.expected_package_id))

    @router.post("/{project_id}/package/simulate", response_model=P.ProductProject)
    async def simulate(project_id: str, body: P.ProductSimulationRequest, idempotency_key: str | None = Header(None)):
        return await command(project_id, "simulate", idempotency_key, body.model_dump(), lambda: service().simulate_package(project_id, body.expected_package_id))

    return router
