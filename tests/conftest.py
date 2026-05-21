"""Root test configuration and shared fixtures.

Provides:
- FastAPI TestClient fixture with dependency overrides
- Settings override fixture for test isolation
- Async HTTP client fixture for async tests
"""

import os


# Force testing environment before importing FastAPI app or settings
os.environ["APP_ENV"] = "test"

from collections.abc import AsyncGenerator, Generator
from typing import Any

import pytest
from fastapi.testclient import TestClient
from httpx import ASGITransport, AsyncClient

from configuration.dependencies import get_settings
from configuration.settings import AppSettings
from presentation.main import app


@pytest.fixture(scope="session")
def test_settings() -> AppSettings:
    """Return a settings instance configured for tests."""
    return AppSettings(
        app_env="test",
        log_level="DEBUG",
        log_format="console",
        metrics_enabled=False,
        host="127.0.0.1",
        port=8000,
        workers=1,
    )


@pytest.fixture
def client(test_settings: AppSettings) -> Generator[TestClient, Any, Any]:
    """Return a synchronous TestClient with test settings injected."""
    app.dependency_overrides[get_settings] = lambda: test_settings
    with TestClient(app, raise_server_exceptions=True) as c:
        yield c
    app.dependency_overrides.clear()


@pytest.fixture
async def async_client(test_settings: AppSettings) -> AsyncGenerator[AsyncClient, Any]:
    """Return an async HTTPX client for async endpoint tests."""
    app.dependency_overrides[get_settings] = lambda: test_settings
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://testserver") as ac:
        yield ac
    app.dependency_overrides.clear()
