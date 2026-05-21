"""FastAPI application entry point.

This module initializes the FastAPI application with lifespan management,
routers, middleware, and observability setup.
"""

import importlib.metadata
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

import structlog
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from configuration.dependencies import (
    get_nats_client,
    get_redis_client,
    get_s3_client,
    get_settings,
)
from observability.logging import setup_logging
from observability.metrics import setup_metrics
from presentation.api.middleware.error_handler import register_exception_handlers
from presentation.api.middleware.request_logging import RequestLoggingMiddleware
from presentation.api.v1.routers import health, index, uploads


log = structlog.get_logger(__name__)

# Load settings at startup (with validation)
settings = get_settings()

_VERSION = importlib.metadata.version(settings.app_name)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    """Manage application startup and shutdown lifecycle."""
    log.info("application.starting", version=_VERSION)
    setup_logging()
    setup_metrics()

    log.info("application.services.connecting")

    # 1. Warm up Redis connection (lazy pool initialization)
    redis = get_redis_client()
    # 2. Warm up S3 connection
    get_s3_client()
    # 3. Warm up NATS connection (establish connection)
    nats = get_nats_client()
    await nats.connect(servers=[settings.nats_url], connect_timeout=settings.nats_connect_timeout)

    log.info("application.started", version=_VERSION)
    yield

    # Clean up connections
    log.info("application.stopping", version=_VERSION)
    await redis.aclose()
    await nats.close()
    log.info("application.stopped", version=_VERSION)


app = FastAPI(
    title=settings.app_name,
    description=f"{settings.app_name} - FastAPI Service",
    version=_VERSION,
    lifespan=lifespan,
)

# Middleware (registered in reverse order of execution)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.add_middleware(RequestLoggingMiddleware)

# Exception handlers
register_exception_handlers(app)

# Routers
app.include_router(health.router)
app.include_router(index.router)
app.include_router(uploads.router)
