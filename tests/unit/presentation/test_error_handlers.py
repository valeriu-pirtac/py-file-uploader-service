"""Unit tests for global HTTP exception handlers."""

import pytest
from fastapi.testclient import TestClient


@pytest.mark.unit
class TestErrorHandlers:
    """Test that unknown paths return 404."""

    def test_unknown_path_returns_404(self, client: TestClient) -> None:
        """Verify that requests to unknown paths return HTTP 404."""
        response = client.get("/v1/nonexistent-path")
        assert response.status_code == 404
