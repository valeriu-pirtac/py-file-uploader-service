"""Global exception handlers.

Maps domain and application exceptions to appropriate HTTP responses,
ensuring consistent error response shapes across the entire API.
"""

import structlog
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from application.exceptions import ApplicationError
from domain.exceptions import DomainError, EntityNotFoundError


log = structlog.get_logger(__name__)


def register_exception_handlers(app: FastAPI) -> None:
    """Register all global exception handlers on the FastAPI app."""

    @app.exception_handler(EntityNotFoundError)
    async def entity_not_found_handler(request: Request, exc: EntityNotFoundError) -> JSONResponse:
        log.warning("entity.not_found", detail=str(exc), path=request.url.path)
        return JSONResponse(status_code=404, content={"detail": str(exc)})

    @app.exception_handler(DomainError)
    async def domain_error_handler(request: Request, exc: DomainError) -> JSONResponse:
        log.warning("domain.error", detail=str(exc), path=request.url.path)
        return JSONResponse(status_code=422, content={"detail": str(exc)})

    @app.exception_handler(ApplicationError)
    async def application_error_handler(request: Request, exc: ApplicationError) -> JSONResponse:
        log.error("application.error", detail=str(exc), path=request.url.path)
        return JSONResponse(status_code=500, content={"detail": str(exc)})
