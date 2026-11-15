"""Quote imports remain independent of engineering requirement uploads."""
from typing import Annotated
from fastapi import APIRouter, File, Form, UploadFile
from fastapi.responses import Response
from starlette.concurrency import run_in_threadpool
from ..domain.errors import DomainError, invalid
from ..domain.quotes import QuoteCollection, QuoteReview
from ..services.supplier_quotes import MAX_BYTES, SupplierQuotes


def quote_router(service_provider) -> APIRouter:
    router = APIRouter(prefix="/api/v1/products/{project_id}/quotes", tags=["Supplier quotes"])

    def service():
        return SupplierQuotes(service_provider().products)

    @router.get("", response_model=QuoteCollection)
    async def quotes(project_id: str, response: Response):
        response.headers["Cache-Control"] = "private, no-store"
        return await run_in_threadpool(service().list, project_id)

    @router.post("", response_model=QuoteCollection, status_code=201)
    async def upload(project_id: str, part_id: Annotated[str, Form()], supplier: Annotated[str, Form()],
                     reply: Annotated[str | None, Form()] = None, file: Annotated[UploadFile | None, File()] = None):
        if bool(file) == bool(reply and reply.strip()):
            raise invalid("Upload one PDF or paste one supplier reply.")
        if file:
            data = bytearray()
            while chunk := await file.read(1024 * 1024):
                data.extend(chunk)
                if len(data) > MAX_BYTES:
                    raise DomainError(413, "PAYLOAD_TOO_LARGE", "Quote PDFs must be at most 4 MB.")
            return await run_in_threadpool(service().import_quote, project_id, part_id, supplier, bytes(data), file.filename or "quote.pdf", "pdf")
        return await run_in_threadpool(service().import_quote, project_id, part_id, supplier, reply.encode(), "Supplier reply.txt", "reply")

    @router.patch("/{quote_id}", response_model=QuoteCollection)
    async def review(project_id: str, quote_id: str, body: QuoteReview):
        return await run_in_threadpool(service().review, project_id, quote_id, body)

    @router.get("/{quote_id}/content", response_class=Response)
    async def content(project_id: str, quote_id: str):
        data, media = await run_in_threadpool(service().content, project_id, quote_id)
        return Response(data, media_type=media, headers={"Cache-Control": "private, no-store", "X-Content-Type-Options": "nosniff"})

    return router
