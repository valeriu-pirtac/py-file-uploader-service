"""End-to-end tests for the health and index endpoints."""

import pytest
from fastapi.testclient import TestClient


@pytest.mark.e2e
class TestHealthEndpoint:
    """Tests for GET /v1/health."""

    def test_health_returns_200(self, client: TestClient) -> None:
        response = client.get("/v1/health")
        assert response.status_code == 200

    def test_health_returns_healthy_status(self, client: TestClient) -> None:
        response = client.get("/v1/health")
        assert response.json() == {"status": "healthy"}


@pytest.mark.e2e
class TestIndexEndpoint:
    """Tests for GET /v1/."""

    def test_index_returns_200(self, client: TestClient) -> None:
        response = client.get("/v1/")
        assert response.status_code == 200

    def test_index_returns_service_info(self, client: TestClient) -> None:
        data = client.get("/v1/").json()
        assert data["service"] == "python-project-template"
        assert data["status"] == "ok"
        assert "version" in data
