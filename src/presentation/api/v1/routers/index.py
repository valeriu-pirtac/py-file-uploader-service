"""Index (root) router."""

import importlib.metadata
from typing import Annotated

import structlog
from fastapi import APIRouter, Depends

from configuration.dependencies import get_settings
from configuration.settings import AppSettings


log = structlog.get_logger(__name__)

router = APIRouter(prefix="/v1", tags=["index"])


@router.get("/")
async def root(app_settings: Annotated[AppSettings, Depends(get_settings)]) -> dict[str, str]:
    """Root endpoint - returns service identity and version."""
    version = importlib.metadata.version(app_settings.app_name)
    return {
        "service": app_settings.app_name,
        "status": "ok",
        "version": version,
    }
