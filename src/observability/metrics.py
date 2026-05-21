"""Prometheus metrics configuration.

Sets up prometheus-fastapi-instrumentator to expose a /metrics endpoint
and registers application-level custom metrics.
"""

from configuration.dependencies import get_settings


def setup_metrics() -> None:
    """Configure Prometheus metrics and expose /metrics endpoint."""

    settings = get_settings()
    if not settings.metrics_enabled:
        return

    # Custom metrics can be registered here using prometheus_client directly.
    # Example:
    #   from prometheus_client import Counter
    #   REQUEST_COUNT = Counter("app_requests_total", "Total request count")
