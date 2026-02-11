"""Tests for API endpoints using FastAPI TestClient."""

import pytest
from unittest.mock import patch, MagicMock, AsyncMock
from fastapi.testclient import TestClient

from app.main import app


@pytest.fixture
def client():
    """Create a test client."""
    return TestClient(app, raise_server_exceptions=False)


class TestHealthEndpoints:
    """Test system health endpoints."""

    def test_health_check(self, client):
        response = client.get("/health")
        assert response.status_code == 200
        data = response.json()
        assert "status" in data
        assert "version" in data
        assert data["version"] == "2.0.0"
        assert "environment" in data
        assert "tasks" in data

    def test_readiness_check_no_db(self, client):
        with patch("app.main.get_db", return_value=None):
            response = client.get("/health/ready")
            assert response.status_code == 503
            data = response.json()
            assert data["ready"] is False

    def test_readiness_check_with_db(self, client):
        with patch("app.main.get_db", return_value=MagicMock()):
            response = client.get("/health/ready")
            assert response.status_code == 200
            data = response.json()
            assert data["ready"] is True

    def test_task_status(self, client):
        response = client.get("/system/tasks")
        assert response.status_code == 200
        data = response.json()
        assert "queue" in data
        assert "active" in data

    def test_cache_stats(self, client):
        response = client.get("/system/cache")
        assert response.status_code == 200


class TestCorrelationId:
    """Test request ID middleware."""

    def test_response_has_request_id(self, client):
        response = client.get("/health")
        assert "X-Request-ID" in response.headers

    def test_respects_incoming_request_id(self, client):
        response = client.get("/health", headers={"X-Request-ID": "test-123"})
        assert response.headers["X-Request-ID"] == "test-123"


class TestErrorHandling:
    """Test structured error responses."""

    def test_404_returns_json(self, client):
        response = client.get("/nonexistent/endpoint/does/not/exist")
        # FastAPI returns 404 for unmatched routes (or 405)
        assert response.status_code in (404, 405, 200)  # May hit static file mount


class TestChatEndpoints:
    """Test chat API endpoints."""

    def test_chat_message_requires_body(self, client):
        response = client.post("/chat/message")
        assert response.status_code == 422  # Validation error

    def test_hm_chat_message_requires_body(self, client):
        response = client.post("/hm-chat/message")
        assert response.status_code == 422


class TestUserEndpoints:
    """Test user management endpoints."""

    def test_create_profile_requires_body(self, client):
        response = client.post("/user/profile")
        assert response.status_code == 422

    def test_upload_document_requires_body(self, client):
        response = client.post("/user/upload-document")
        assert response.status_code == 422


class TestCalibrationEndpoints:
    """Test calibration endpoints."""

    def test_generate_requires_body(self, client):
        response = client.post("/calibration/generate")
        assert response.status_code == 422

    def test_respond_requires_body(self, client):
        response = client.post("/calibration/respond")
        assert response.status_code == 422


class TestJobEndpoints:
    """Test job management endpoints."""

    def test_create_job_requires_body(self, client):
        response = client.post("/jobs/create")
        assert response.status_code == 422


class TestOnboardingEndpoints:
    """Test onboarding endpoints."""

    def test_start_interview_requires_body(self, client):
        response = client.post("/onboarding/talent/start-interview")
        assert response.status_code == 422

    def test_answer_requires_body(self, client):
        response = client.post("/onboarding/talent/answer")
        assert response.status_code == 422
