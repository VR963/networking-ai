"""
Comprehensive tests for Mobile Jobs API.

Tests cover:
- Job search with filters
- Pagination
- Job details
- Save/unsave jobs
- Authorization
"""

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from src.networking_ai.api.main import app
from src.networking_ai.models.user import User, UserRole
from src.networking_ai.models.company import Company
from src.networking_ai.models.job import Job, JobStatus, JobType, ExperienceLevel
from src.networking_ai.models.mobile import SavedJob

client = TestClient(app)


@pytest.fixture
def auth_user(db_session):
    """Create authenticated user and return auth header."""
    # Register user
    user_data = {
        "email": "jobseeker@example.com",
        "password": "SecurePass123!",
        "full_name": "Job Seeker",
        "role": "jobseeker",
        "device": {
            "platform": "ios",
            "device_id": "test_device_jobs",
            "push_token": "fcm_token"
        }
    }

    response = client.post("/api/v1/mobile/auth/register", json=user_data)
    access_token = response.json()["data"]["tokens"]["access_token"]

    return {"Authorization": f"Bearer {access_token}"}


@pytest.fixture
def test_company(db_session):
    """Create test company."""
    company = Company(
        name="TechCorp",
        description="Tech company",
        status="active"
    )
    db_session.add(company)
    db_session.commit()
    db_session.refresh(company)
    return company


@pytest.fixture
def test_jobs(db_session, test_company):
    """Create multiple test jobs."""
    jobs = [
        Job(
            title="Senior Software Engineer",
            description="Senior role in tech",
            company_id=test_company.id,
            location="San Francisco, CA",
            job_type=JobType.FULL_TIME,
            experience_level=ExperienceLevel.SENIOR,
            min_salary=150000,
            max_salary=200000,
            salary_currency="USD",
            status=JobStatus.OPEN
        ),
        Job(
            title="Junior Developer",
            description="Entry level position",
            company_id=test_company.id,
            location="New York, NY",
            job_type=JobType.FULL_TIME,
            experience_level=ExperienceLevel.ENTRY,
            min_salary=70000,
            max_salary=90000,
            salary_currency="USD",
            status=JobStatus.OPEN
        ),
        Job(
            title="Contract Engineer",
            description="6-month contract",
            company_id=test_company.id,
            location="Remote",
            job_type=JobType.CONTRACT,
            experience_level=ExperienceLevel.MID,
            min_salary=100000,
            max_salary=120000,
            salary_currency="USD",
            status=JobStatus.OPEN
        )
    ]

    for job in jobs:
        db_session.add(job)

    db_session.commit()

    for job in jobs:
        db_session.refresh(job)

    return jobs


# ==================== Job Search Tests ====================

def test_search_jobs_no_filters(auth_user, test_jobs):
    """Test job search without filters."""
    response = client.get("/api/v1/mobile/jobs", headers=auth_user)

    assert response.status_code == 200
    data = response.json()

    assert "data" in data
    assert "data" in data["data"]
    assert "meta" in data["data"]

    jobs = data["data"]["data"]
    assert len(jobs) == 3


def test_search_jobs_with_query(auth_user, test_jobs):
    """Test job search with text query."""
    response = client.get(
        "/api/v1/mobile/jobs?q=senior",
        headers=auth_user
    )

    assert response.status_code == 200
    data = response.json()

    jobs = data["data"]["data"]
    assert len(jobs) == 1
    assert "Senior" in jobs[0]["title"]


def test_search_jobs_by_location(auth_user, test_jobs):
    """Test job search by location."""
    response = client.get(
        "/api/v1/mobile/jobs?location=Remote",
        headers=auth_user
    )

    assert response.status_code == 200
    data = response.json()

    jobs = data["data"]["data"]
    assert len(jobs) == 1
    assert jobs[0]["location"] == "Remote"


def test_search_jobs_by_type(auth_user, test_jobs):
    """Test job search by job type."""
    response = client.get(
        "/api/v1/mobile/jobs?job_type=contract",
        headers=auth_user
    )

    assert response.status_code == 200
    data = response.json()

    jobs = data["data"]["data"]
    assert len(jobs) == 1
    assert jobs[0]["job_type"] == "contract"


def test_search_jobs_by_experience_level(auth_user, test_jobs):
    """Test job search by experience level."""
    response = client.get(
        "/api/v1/mobile/jobs?experience_level=entry",
        headers=auth_user
    )

    assert response.status_code == 200
    data = response.json()

    jobs = data["data"]["data"]
    assert len(jobs) == 1
    assert jobs[0]["experience_level"] == "entry"


def test_search_jobs_pagination(auth_user, test_jobs):
    """Test job search pagination."""
    # Get first page
    response = client.get(
        "/api/v1/mobile/jobs?limit=2",
        headers=auth_user
    )

    assert response.status_code == 200
    data = response.json()

    jobs = data["data"]["data"]
    meta = data["data"]["meta"]

    assert len(jobs) == 2
    assert "cursor" in meta
    assert meta["count"] == 2


def test_search_jobs_unauthorized(test_jobs):
    """Test job search without authorization fails."""
    response = client.get("/api/v1/mobile/jobs")

    assert response.status_code == 401


# ==================== Job Detail Tests ====================

def test_get_job_detail(auth_user, test_jobs):
    """Test get job details."""
    job_id = test_jobs[0].id

    response = client.get(
        f"/api/v1/mobile/jobs/{job_id}",
        headers=auth_user
    )

    assert response.status_code == 200
    data = response.json()

    assert "data" in data
    job = data["data"]

    assert job["id"] == job_id
    assert job["title"] == test_jobs[0].title
    assert job["description"] == test_jobs[0].description
    assert "company" in job
    assert "salary_range" in job


def test_get_nonexistent_job(auth_user):
    """Test get non-existent job returns 404."""
    response = client.get(
        "/api/v1/mobile/jobs/99999",
        headers=auth_user
    )

    assert response.status_code == 404


# ==================== Save/Unsave Jobs Tests ====================

def test_save_job(auth_user, test_jobs, db_session):
    """Test saving a job."""
    job_id = test_jobs[0].id

    response = client.post(
        f"/api/v1/mobile/jobs/{job_id}/save",
        headers=auth_user
    )

    assert response.status_code == 201
    data = response.json()

    assert "data" in data
    assert data["data"]["job_id"] == job_id

    # Verify saved in database
    saved = db_session.query(SavedJob).filter(
        SavedJob.job_id == job_id
    ).first()

    assert saved is not None


def test_save_already_saved_job(auth_user, test_jobs):
    """Test saving already saved job returns conflict."""
    job_id = test_jobs[0].id

    # Save first time
    client.post(f"/api/v1/mobile/jobs/{job_id}/save", headers=auth_user)

    # Save again
    response = client.post(
        f"/api/v1/mobile/jobs/{job_id}/save",
        headers=auth_user
    )

    assert response.status_code == 409


def test_unsave_job(auth_user, test_jobs, db_session):
    """Test unsaving a job."""
    job_id = test_jobs[0].id

    # Save first
    client.post(f"/api/v1/mobile/jobs/{job_id}/save", headers=auth_user)

    # Unsave
    response = client.delete(
        f"/api/v1/mobile/jobs/{job_id}/save",
        headers=auth_user
    )

    assert response.status_code == 204

    # Verify removed from database
    saved = db_session.query(SavedJob).filter(
        SavedJob.job_id == job_id
    ).first()

    assert saved is None


def test_unsave_not_saved_job(auth_user, test_jobs):
    """Test unsaving non-saved job returns 404."""
    job_id = test_jobs[0].id

    response = client.delete(
        f"/api/v1/mobile/jobs/{job_id}/save",
        headers=auth_user
    )

    assert response.status_code == 404


def test_job_list_shows_saved_status(auth_user, test_jobs):
    """Test job list shows correct saved status."""
    job_id = test_jobs[0].id

    # Save one job
    client.post(f"/api/v1/mobile/jobs/{job_id}/save", headers=auth_user)

    # Get job list
    response = client.get("/api/v1/mobile/jobs", headers=auth_user)

    assert response.status_code == 200
    jobs = response.json()["data"]["data"]

    # Find the saved job
    saved_job = next(j for j in jobs if j["id"] == job_id)
    assert saved_job["is_saved"] is True

    # Other jobs should not be saved
    other_jobs = [j for j in jobs if j["id"] != job_id]
    for job in other_jobs:
        assert job["is_saved"] is False
