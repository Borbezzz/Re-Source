"""Additive, tenant-scoped supply-risk endpoints."""
from fastapi import APIRouter, Header, Response
from starlette.concurrency import run_in_threadpool

from ..domain.supply_risk import RiskConfirm, RiskEvidenceRequest, RiskScan
from ..services.supply_risk import SupplyRiskService


def supply_risk_router(service_provider, idempotent):
    router = APIRouter(prefix="/api/v1/products/{project_id}/supply-risk", tags=["Supply risk"])

    def service():
        return SupplyRiskService(service_provider().products)

    @router.get("", response_model=RiskScan)
    async def get(project_id: str, response: Response):
        response.headers["Cache-Control"] = "private, no-store"
        return await run_in_threadpool(service().get, project_id)

    @router.post("/confirm", response_model=RiskScan)
    async def confirm(project_id: str, body: RiskConfirm, idempotency_key: str | None = Header(None)):
        return await idempotent(f"risk:{project_id}:confirm", idempotency_key, body.model_dump(mode="json"), lambda: service().confirm(project_id, body))

    @router.post("/refresh", response_model=RiskScan)
    async def refresh(project_id: str, idempotency_key: str | None = Header(None)):
        return await idempotent(f"risk:{project_id}:refresh", idempotency_key, {}, lambda: service().refresh(project_id))

    @router.post("/evidence", response_model=RiskScan)
    async def evidence(project_id: str, body: RiskEvidenceRequest, idempotency_key: str | None = Header(None)):
        return await idempotent(f"risk:{project_id}:evidence", idempotency_key, body.model_dump(mode="json"), lambda: service().record_evidence(project_id, body.evidence, body.expected_scan_version))

    return router
