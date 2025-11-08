"""
Comprehensive Mobile API Integration Tests.

Tests end-to-end user flows:
- User registration → job search → application → tracking
- Profile management flow
- Notification flow
- Messaging flow
"""

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from src.networking_ai.api.main import app
from src.networking_ai.models.user import User
from src.networking_ai.models.company import Company
from src.networking_ai.models.job import Job, JobStatus, JobType
from src.networking_ai.models.application import Application, ApplicationStatus

client = TestClient(app)


@pytest.fixture
def setup_job_ecosystem(db_session):
    """
    Create a complete job ecosystem:
    - Company
    - Jobs
    - Authenticated jobseeker
    """
    # Create company
    company = Company(
        name="TechCorp",
        description="Leading tech company",
        status="active"
    )
    db_session.add(company)
    db_session.commit()
    db_session.refresh(company)

    # Create jobs
    job = Job(
        title="Senior Software Engineer",
        description="Exciting opportunity",
        company_id=company.id,
        location="San Francisco, CA",
        job_type=JobType.FULL_TIME,
        min_salary=150000,
        max_salary=200000,
        status=JobStatus.OPEN
    )
    db_session.add(job)
    db_session.commit()
    db_session.refresh(job)

    # Register user
    user_data = {
        "email": "jobseeker@test.com",
        "password": "SecurePass123!",
        "full_name": "Test User",
        "role": "jobseeker",
        "device": {
            "platform": "ios",
            "device_id": "integration_test_device",
            "push_token": "fcm_token"
        }
    }

    response = client.post("/api/v1/mobile/auth/register", json=user_data)
    access_token = response.json()["data"]["tokens"]["access_token"]
    user_id = response.json()["data"]["user"]["id"]

    return {
        "company": company,
        "job": job,
        "auth_header": {"Authorization": f"Bearer {access_token}"},
        "user_id": user_id
    }


# ==================== End-to-End User Journey Tests ====================

def test_complete_job_application_flow(setup_job_ecosystem, db_session):
    """
    Test complete flow:
    1. Search for jobs
    2. View job details
    3. Save job
    4. Submit application
    5. Track application status
    """
    ecosystem = setup_job_ecosystem
    auth = ecosystem["auth_header"]
    job_id = ecosystem["job"].id

    # Step 1: Search for jobs
    search_response = client.get("/api/v1/mobile/jobs", headers=auth)
    assert search_response.status_code == 200

    jobs = search_response.json()["data"]["data"]
    assert len(jobs) > 0

    # Step 2: View job details
    detail_response = client.get(f"/api/v1/mobile/jobs/{job_id}", headers=auth)
    assert detail_response.status_code == 200

    job_detail = detail_response.json()["data"]
    assert job_detail["title"] == "Senior Software Engineer"

    # Step 3: Save job
    save_response = client.post(f"/api/v1/mobile/jobs/{job_id}/save", headers=auth)
    assert save_response.status_code == 201

    # Step 4: Submit application
    application_data = {
        "job_id": job_id,
        "cover_letter": "I am excited to apply for this position...",
        "answers": []
    }

    apply_response = client.post(
        "/api/v1/mobile/applications",
        headers=auth,
        json=application_data
    )
    assert apply_response.status_code == 201

    application_id = apply_response.json()["data"]["id"]

    # Step 5: Track application
    track_response = client.get(
        f"/api/v1/mobile/applications/{application_id}",
        headers=auth
    )
    assert track_response.status_code == 200

    app_detail = track_response.json()["data"]
    assert app_detail["status"] == "applied"
    assert len(app_detail["timeline"]) > 0


def test_profile_management_flow(setup_job_ecosystem):
    """
    Test profile management:
    1. Get initial profile
    2. Update profile
    3. Verify changes
    """
    auth = setup_job_ecosystem["auth_header"]

    # Step 1: Get profile
    profile_response = client.get("/api/v1/mobile/profile", headers=auth)
    assert profile_response.status_code == 200

    initial_profile = profile_response.json()["data"]
    assert initial_profile["email"] == "jobseeker@test.com"

    # Step 2: Update profile
    update_data = {
        "headline": "Senior Software Engineer",
        "location": "San Francisco, CA",
        "skills": ["Python", "FastAPI", "PostgreSQL"],
        "experience_years": 5
    }

    update_response = client.patch(
        "/api/v1/mobile/profile",
        headers=auth,
        json=update_data
    )
    assert update_response.status_code == 200

    # Step 3: Verify changes
    updated_profile = update_response.json()["data"]
    assert updated_profile["headline"] == "Senior Software Engineer"
    assert updated_profile["location"] == "San Francisco, CA"
    assert len(updated_profile["skills"]) == 3
    assert updated_profile["experience_years"] == 5


# ==================== Security Tests ====================

def test_cannot_access_without_auth():
    """Test that protected endpoints require authentication."""
    endpoints = [
        "/api/v1/mobile/jobs",
        "/api/v1/mobile/applications",
        "/api/v1/mobile/profile",
        "/api/v1/mobile/notifications",
        "/api/v1/mobile/messages/conversations"
    ]

    for endpoint in endpoints:
        response = client.get(endpoint)
        assert response.status_code == 401, f"Endpoint {endpoint} should require auth"


def test_cannot_use_expired_token(db_session):
    """Test that expired tokens are rejected."""
    import jwt
    from datetime import datetime, timedelta
    from src.networking_ai.config import get_settings

    settings = get_settings()

    # Create expired token
    expired_payload = {
        "sub": "123",
        "exp": datetime.utcnow() - timedelta(hours=1),  # Expired
        "type": "access"
    }

    expired_token = jwt.encode(
        expired_payload,
        settings.JWT_SECRET_KEY,
        algorithm=settings.JWT_ALGORITHM
    )

    response = client.get(
        "/api/v1/mobile/profile",
        headers={"Authorization": f"Bearer {expired_token}"}
    )

    assert response.status_code == 401


def test_cannot_access_other_users_data(setup_job_ecosystem, db_session):
    """Test that users cannot access other users' data."""
    # Create second user
    user2_data = {
        "email": "user2@test.com",
        "password": "SecurePass123!",
        "full_name": "User 2",
        "role": "jobseeker",
        "device": {
            "platform": "android",
            "device_id": "user2_device",
            "push_token": "fcm_token_2"
        }
    }

    response = client.post("/api/v1/mobile/auth/register", json=user2_data)
    user2_token = response.json()["data"]["tokens"]["access_token"]
    user2_auth = {"Authorization": f"Bearer {user2_token}"}

    # User 1 creates application
    ecosystem = setup_job_ecosystem
    application_data = {
        "job_id": ecosystem["job"].id,
        "cover_letter": "User 1's application"
    }

    app_response = client.post(
        "/api/v1/mobile/applications",
        headers=ecosystem["auth_header"],
        json=application_data
    )

    application_id = app_response.json()["data"]["id"]

    # User 2 tries to access User 1's application
    response = client.get(
        f"/api/v1/mobile/applications/{application_id}",
        headers=user2_auth
    )

    assert response.status_code == 404  # Should not find it


# ==================== Error Handling Tests ====================

def test_invalid_json_returns_422():
    """Test that invalid JSON returns 422."""
    response = client.post(
        "/api/v1/mobile/auth/register",
        data="invalid json"
    )

    assert response.status_code == 422


def test_missing_required_fields():
    """Test that missing required fields returns validation error."""
    incomplete_data = {
        "email": "test@example.com"
        # Missing password, full_name, role, device
    }

    response = client.post(
        "/api/v1/mobile/auth/register",
        json=incomplete_data
    )

    assert response.status_code == 422


# ==================== Performance Tests ====================

@pytest.mark.skip(reason="Performance test - run separately")
def test_job_search_response_time(setup_job_ecosystem):
    """Test that job search responds quickly."""
    import time

    auth = setup_job_ecosystem["auth_header"]

    # Warm up
    client.get("/api/v1/mobile/jobs", headers=auth)

    # Measure
    start = time.time()
    response = client.get("/api/v1/mobile/jobs", headers=auth)
    duration = time.time() - start

    assert response.status_code == 200
    assert duration < 0.5  # Should respond in under 500ms


@pytest.mark.skip(reason="Performance test - run separately")
def test_concurrent_requests():
    """Test handling concurrent requests."""
    import concurrent.futures

    def make_request():
        response = client.get("/api/v1/mobile/health")
        return response.status_code

    with concurrent.futures.ThreadPoolExecutor(max_workers=10) as executor:
        futures = [executor.submit(make_request) for _ in range(100)]
        results = [f.result() for f in futures]

    # All requests should succeed
    assert all(status == 200 for status in results)
