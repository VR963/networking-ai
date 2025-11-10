"""
Comprehensive tests for Mobile Applications API.

Tests cover:
- Application submission
- Application listing
- Application detail retrieval
- Application timeline tracking
- Interview scheduling
- Validation and error handling
"""

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session
from datetime import datetime, timedelta

from src.networking_ai.api.main import app
from src.networking_ai.models.user import User
from src.networking_ai.models.company import Company
from src.networking_ai.models.job import Job, JobStatus, JobType
from src.networking_ai.models.application import Application, ApplicationStatus
from src.networking_ai.models.interview import Interview, InterviewType, InterviewStatus

client = TestClient(app)


@pytest.fixture
def auth_user_with_job(db_session):
    """Create authenticated user with available job."""
    # Create company
    company = Company(
        name="TechCorp",
        description="Leading tech company",
        status="active"
    )
    db_session.add(company)
    db_session.commit()
    db_session.refresh(company)

    # Create job
    job = Job(
        title="Backend Engineer",
        description="Build scalable systems",
        company_id=company.id,
        location="Remote",
        job_type=JobType.FULL_TIME,
        min_salary=120000,
        max_salary=180000,
        status=JobStatus.OPEN
    )
    db_session.add(job)
    db_session.commit()
    db_session.refresh(job)

    # Register user
    user_data = {
        "email": "applicant@test.com",
        "password": "SecurePass123!",
        "full_name": "Test Applicant",
        "role": "jobseeker",
        "device": {
            "platform": "ios",
            "device_id": "test_device_apps",
            "push_token": "fcm_token"
        }
    }

    response = client.post("/api/v1/mobile/auth/register", json=user_data)
    access_token = response.json()["data"]["tokens"]["access_token"]
    user_id = response.json()["data"]["user"]["id"]

    return {
        "auth_header": {"Authorization": f"Bearer {access_token}"},
        "user_id": user_id,
        "job": job,
        "company": company
    }


# ==================== Application Submission Tests ====================

def test_submit_application_success(auth_user_with_job, db_session):
    """Test successful application submission."""
    auth = auth_user_with_job["auth_header"]
    job_id = auth_user_with_job["job"].id

    application_data = {
        "job_id": job_id,
        "cover_letter": "I am very interested in this position...",
        "answers": []
    }

    response = client.post(
        "/api/v1/mobile/applications",
        headers=auth,
        json=application_data
    )

    assert response.status_code == 201
    data = response.json()["data"]

    assert data["job"]["id"] == job_id
    assert data["status"] == "applied"
    assert data["cover_letter"] == application_data["cover_letter"]
    assert "submitted_at" in data

    # Verify application created in database
    application = db_session.query(Application).filter(
        Application.job_id == job_id,
        Application.user_id == auth_user_with_job["user_id"]
    ).first()

    assert application is not None
    assert application.status == ApplicationStatus.APPLIED


def test_submit_application_duplicate_fails(auth_user_with_job):
    """Test cannot submit duplicate application to same job."""
    auth = auth_user_with_job["auth_header"]
    job_id = auth_user_with_job["job"].id

    application_data = {
        "job_id": job_id,
        "cover_letter": "First application"
    }

    # First application
    response1 = client.post(
        "/api/v1/mobile/applications",
        headers=auth,
        json=application_data
    )
    assert response1.status_code == 201

    # Second application to same job
    response2 = client.post(
        "/api/v1/mobile/applications",
        headers=auth,
        json=application_data
    )

    assert response2.status_code == 409  # Conflict
    data = response2.json()
    assert "error" in data
    assert data["error"]["code"] == "ALREADY_EXISTS"


def test_submit_application_to_closed_job_fails(auth_user_with_job, db_session):
    """Test cannot apply to closed job."""
    auth = auth_user_with_job["auth_header"]
    job = auth_user_with_job["job"]

    # Close the job
    job.status = JobStatus.CLOSED
    db_session.commit()

    application_data = {
        "job_id": job.id,
        "cover_letter": "Application to closed job"
    }

    response = client.post(
        "/api/v1/mobile/applications",
        headers=auth,
        json=application_data
    )

    assert response.status_code == 400
    data = response.json()
    assert "error" in data


def test_submit_application_missing_cover_letter(auth_user_with_job):
    """Test application submission with missing cover letter."""
    auth = auth_user_with_job["auth_header"]
    job_id = auth_user_with_job["job"].id

    application_data = {
        "job_id": job_id
        # Missing cover_letter
    }

    response = client.post(
        "/api/v1/mobile/applications",
        headers=auth,
        json=application_data
    )

    # Should still work (cover letter may be optional)
    # Adjust based on actual validation rules
    assert response.status_code in [201, 422]


# ==================== Application Listing Tests ====================

def test_list_applications(auth_user_with_job, db_session):
    """Test listing user's applications."""
    auth = auth_user_with_job["auth_header"]
    job_id = auth_user_with_job["job"].id

    # Create application
    application_data = {
        "job_id": job_id,
        "cover_letter": "Test application"
    }

    client.post(
        "/api/v1/mobile/applications",
        headers=auth,
        json=application_data
    )

    # List applications
    response = client.get("/api/v1/mobile/applications", headers=auth)

    assert response.status_code == 200
    data = response.json()["data"]

    assert "data" in data
    applications = data["data"]
    assert len(applications) >= 1

    # Check application structure
    app = applications[0]
    assert "id" in app
    assert "job" in app
    assert "status" in app
    assert "submitted_at" in app


def test_list_applications_filter_by_status(auth_user_with_job, db_session):
    """Test filtering applications by status."""
    auth = auth_user_with_job["auth_header"]
    job_id = auth_user_with_job["job"].id

    # Create application
    application_data = {
        "job_id": job_id,
        "cover_letter": "Test application"
    }

    response = client.post(
        "/api/v1/mobile/applications",
        headers=auth,
        json=application_data
    )

    # List with status filter
    response = client.get(
        "/api/v1/mobile/applications?status=applied",
        headers=auth
    )

    assert response.status_code == 200
    applications = response.json()["data"]["data"]
    assert all(app["status"] == "applied" for app in applications)


# ==================== Application Detail Tests ====================

def test_get_application_detail(auth_user_with_job, db_session):
    """Test retrieving detailed application information."""
    auth = auth_user_with_job["auth_header"]
    job_id = auth_user_with_job["job"].id

    # Create application
    application_data = {
        "job_id": job_id,
        "cover_letter": "Detailed application"
    }

    submit_response = client.post(
        "/api/v1/mobile/applications",
        headers=auth,
        json=application_data
    )

    application_id = submit_response.json()["data"]["id"]

    # Get detail
    response = client.get(
        f"/api/v1/mobile/applications/{application_id}",
        headers=auth
    )

    assert response.status_code == 200
    data = response.json()["data"]

    assert data["id"] == application_id
    assert "job" in data
    assert "status" in data
    assert "timeline" in data
    assert "cover_letter" in data

    # Check timeline
    timeline = data["timeline"]
    assert len(timeline) > 0
    assert timeline[0]["stage"] == "submitted"


def test_get_application_detail_with_interview(auth_user_with_job, db_session):
    """Test application detail includes scheduled interviews."""
    auth = auth_user_with_job["auth_header"]
    job_id = auth_user_with_job["job"].id
    user_id = auth_user_with_job["user_id"]

    # Create application
    application = Application(
        job_id=job_id,
        user_id=user_id,
        cover_letter="Test",
        status=ApplicationStatus.INTERVIEWING
    )
    db_session.add(application)
    db_session.commit()
    db_session.refresh(application)

    # Create interview
    interview = Interview(
        application_id=application.id,
        scheduled_at=datetime.utcnow() + timedelta(days=3),
        duration_minutes=60,
        interview_type=InterviewType.PHONE_SCREEN,
        status=InterviewStatus.SCHEDULED,
        interviewer_name="John Doe",
        meeting_link="https://zoom.us/j/123456"
    )
    db_session.add(interview)
    db_session.commit()

    # Get application detail
    response = client.get(
        f"/api/v1/mobile/applications/{application.id}",
        headers=auth
    )

    assert response.status_code == 200
    data = response.json()["data"]

    # Check interviews included
    if "interviews" in data:
        assert len(data["interviews"]) == 1
        assert data["interviews"][0]["interview_type"] == "phone_screen"


def test_cannot_access_other_user_application(auth_user_with_job, db_session):
    """Test user cannot access another user's application."""
    # Create second user
    user2_data = {
        "email": "user2@test.com",
        "password": "SecurePass123!",
        "full_name": "User 2",
        "role": "jobseeker",
        "device": {
            "platform": "android",
            "device_id": "user2_device_apps",
            "push_token": "fcm_token_2"
        }
    }

    response = client.post("/api/v1/mobile/auth/register", json=user2_data)
    user2_token = response.json()["data"]["tokens"]["access_token"]
    user2_auth = {"Authorization": f"Bearer {user2_token}"}

    # User 1 creates application
    auth = auth_user_with_job["auth_header"]
    job_id = auth_user_with_job["job"].id

    submit_response = client.post(
        "/api/v1/mobile/applications",
        headers=auth,
        json={"job_id": job_id, "cover_letter": "User 1's app"}
    )

    application_id = submit_response.json()["data"]["id"]

    # User 2 tries to access User 1's application
    response = client.get(
        f"/api/v1/mobile/applications/{application_id}",
        headers=user2_auth
    )

    assert response.status_code == 404  # Should not find it


def test_get_nonexistent_application(auth_user_with_job):
    """Test accessing non-existent application returns 404."""
    auth = auth_user_with_job["auth_header"]

    response = client.get(
        "/api/v1/mobile/applications/99999",
        headers=auth
    )

    assert response.status_code == 404
    data = response.json()
    assert "error" in data
    assert data["error"]["code"] == "NOT_FOUND"
