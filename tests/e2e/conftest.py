"""Pytest configuration and shared fixtures for E2E tests.

Provides global mocks for service dependencies to ensure E2E tests do not
attempt to establish live connections to Redis, S3, or NATS.
"""

from unittest.mock import AsyncMock, MagicMock

import pytest


@pytest.fixture(autouse=True)
def mock_dependencies(monkeypatch) -> None:
    """Mock Redis, S3, and NATS clients to prevent real network connections in E2E tests."""
    # 1. Mock Redis Client
    mock_redis = MagicMock()
    mock_redis.aclose = AsyncMock()

    # 2. Mock S3 Client
    mock_s3 = MagicMock()

    # 3. Mock NATS Client
    mock_nats = MagicMock()
    mock_nats.connect = AsyncMock()
    mock_nats.close = AsyncMock()

    # Apply monkeypatch overrides to return synchronous callables
    monkeypatch.setattr("configuration.dependencies.get_redis_client", lambda: mock_redis)
    monkeypatch.setattr("configuration.dependencies.get_s3_client", lambda: mock_s3)
    monkeypatch.setattr("configuration.dependencies.get_nats_client", lambda: mock_nats)

    # Patch the direct imports in presentation.main to avoid import binding issues
    monkeypatch.setattr("presentation.main.get_redis_client", lambda: mock_redis)
    monkeypatch.setattr("presentation.main.get_s3_client", lambda: mock_s3)
    monkeypatch.setattr("presentation.main.get_nats_client", lambda: mock_nats)
