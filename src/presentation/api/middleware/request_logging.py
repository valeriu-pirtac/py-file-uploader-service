"""Request logging middleware.

Logs every incoming HTTP request and outgoing response using structlog,
including method, path, status code, and elapsed time.
"""

import time

import structlog
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response


log = structlog.get_logger(__name__)


class RequestLoggingMiddleware(BaseHTTPMiddleware):
    """Middleware that logs each request/response cycle."""

    async def dispatch(self, request: Request, call_next: object) -> Response:
        """Log the request and delegate to the next handler."""
        start = time.perf_counter()
        response: Response = await call_next(request)  # type: ignore[operator]
        elapsed_ms = round((time.perf_counter() - start) * 1000, 2)
        log.info(
            "http.request",
            method=request.method,
            path=request.url.path,
            status_code=response.status_code,
            elapsed_ms=elapsed_ms,
        )
        return response
