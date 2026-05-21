"""Health router."""

import structlog
from fastapi import APIRouter


log = structlog.get_logger(__name__)

router = APIRouter(prefix="/v1", tags=["health"])


@router.get("/health")
async def health() -> dict[str, str]:
    """Health check endpoint for liveness probes."""
    return {
        "status": "healthy",
    }
