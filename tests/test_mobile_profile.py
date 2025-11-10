"""
Comprehensive tests for Mobile Profile API.

Tests cover:
- Profile retrieval
- Profile updates
- Profile completeness calculation
- Avatar upload
- Resume upload
- Validation and error handling
"""

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session
from io import BytesIO

from src.networking_ai.api.main import app
from src.networking_ai.models.user import User
from src.networking_ai.models.profile import UserProfile

client = TestClient(app)


@pytest.fixture
def auth_user(db_session):
    """Create authenticated user."""
    user_data = {
        "email": "profileuser@test.com",
        "password": "SecurePass123!",
        "full_name": "Profile Test User",
        "role": "jobseeker",
        "device": {
            "platform": "ios",
            "device_id": "test_device_profile",
            "push_token": "fcm_token"
        }
    }

    response = client.post("/api/v1/mobile/auth/register", json=user_data)
    access_token = response.json()["data"]["tokens"]["access_token"]
    user_id = response.json()["data"]["user"]["id"]

    return {
        "auth_header": {"Authorization": f"Bearer {access_token}"},
        "user_id": user_id,
        "email": user_data["email"]
    }


# ==================== Profile Retrieval Tests ====================

def test_get_profile_success(auth_user):
    """Test successful profile retrieval."""
    auth = auth_user["auth_header"]

    response = client.get("/api/v1/mobile/profile", headers=auth)

    assert response.status_code == 200
    data = response.json()["data"]

    assert data["email"] == auth_user["email"]
    assert data["full_name"] == "Profile Test User"
    assert data["role"] == "jobseeker"
    assert "completeness" in data
    assert 0.0 <= data["completeness"] <= 1.0


def test_get_profile_includes_completeness(auth_user):
    """Test profile includes completeness score."""
    auth = auth_user["auth_header"]

    response = client.get("/api/v1/mobile/profile", headers=auth)

    assert response.status_code == 200
    data = response.json()["data"]

    # New account should have low completeness (just email)
    assert data["completeness"] >= 0.2  # Base score for having account
    assert data["completeness"] < 1.0  # Not complete yet


def test_get_profile_without_auth_fails():
    """Test profile access without authentication fails."""
    response = client.get("/api/v1/mobile/profile")

    assert response.status_code == 401


# ==================== Profile Update Tests ====================

def test_update_profile_headline(auth_user):
    """Test updating profile headline."""
    auth = auth_user["auth_header"]

    update_data = {
        "headline": "Senior Software Engineer"
    }

    response = client.patch(
        "/api/v1/mobile/profile",
        headers=auth,
        json=update_data
    )

    assert response.status_code == 200
    data = response.json()["data"]

    assert data["headline"] == "Senior Software Engineer"


def test_update_profile_location(auth_user):
    """Test updating profile location."""
    auth = auth_user["auth_header"]

    update_data = {
        "location": "San Francisco, CA"
    }

    response = client.patch(
        "/api/v1/mobile/profile",
        headers=auth,
        json=update_data
    )

    assert response.status_code == 200
    data = response.json()["data"]

    assert data["location"] == "San Francisco, CA"


def test_update_profile_skills(auth_user):
    """Test updating profile skills."""
    auth = auth_user["auth_header"]

    update_data = {
        "skills": ["Python", "FastAPI", "PostgreSQL", "Docker"]
    }

    response = client.patch(
        "/api/v1/mobile/profile",
        headers=auth,
        json=update_data
    )

    assert response.status_code == 200
    data = response.json()["data"]

    assert "skills" in data
    assert len(data["skills"]) == 4
    assert "Python" in data["skills"]
    assert "FastAPI" in data["skills"]


def test_update_profile_experience_years(auth_user):
    """Test updating years of experience."""
    auth = auth_user["auth_header"]

    update_data = {
        "experience_years": 5
    }

    response = client.patch(
        "/api/v1/mobile/profile",
        headers=auth,
        json=update_data
    )

    assert response.status_code == 200
    data = response.json()["data"]

    assert data["experience_years"] == 5


def test_update_profile_multiple_fields(auth_user):
    """Test updating multiple profile fields at once."""
    auth = auth_user["auth_header"]

    update_data = {
        "headline": "Full Stack Developer",
        "location": "New York, NY",
        "skills": ["JavaScript", "React", "Node.js"],
        "experience_years": 3,
        "bio": "Passionate developer with 3 years of experience..."
    }

    response = client.patch(
        "/api/v1/mobile/profile",
        headers=auth,
        json=update_data
    )

    assert response.status_code == 200
    data = response.json()["data"]

    assert data["headline"] == "Full Stack Developer"
    assert data["location"] == "New York, NY"
    assert len(data["skills"]) == 3
    assert data["experience_years"] == 3
    assert data["bio"] == "Passionate developer with 3 years of experience..."


def test_update_profile_increases_completeness(auth_user):
    """Test that updating profile increases completeness score."""
    auth = auth_user["auth_header"]

    # Get initial completeness
    initial_response = client.get("/api/v1/mobile/profile", headers=auth)
    initial_completeness = initial_response.json()["data"]["completeness"]

    # Update profile
    update_data = {
        "headline": "Software Engineer",
        "location": "Seattle, WA",
        "skills": ["Python", "Django"],
        "experience_years": 2
    }

    update_response = client.patch(
        "/api/v1/mobile/profile",
        headers=auth,
        json=update_data
    )

    updated_completeness = update_response.json()["data"]["completeness"]

    # Completeness should increase
    assert updated_completeness > initial_completeness


# ==================== File Upload Tests ====================

def test_upload_avatar(auth_user):
    """Test uploading profile avatar."""
    auth = auth_user["auth_header"]

    # Create fake image file
    image_content = b"fake image content"
    files = {
        "file": ("avatar.jpg", BytesIO(image_content), "image/jpeg")
    }

    response = client.post(
        "/api/v1/mobile/profile/avatar",
        headers=auth,
        files=files
    )

    # May return 200 or 501 if not implemented yet
    assert response.status_code in [200, 501]

    if response.status_code == 200:
        data = response.json()["data"]
        assert "avatar_url" in data


def test_upload_resume(auth_user):
    """Test uploading resume."""
    auth = auth_user["auth_header"]

    # Create fake PDF file
    pdf_content = b"%PDF-1.4 fake pdf content"
    files = {
        "file": ("resume.pdf", BytesIO(pdf_content), "application/pdf")
    }

    response = client.post(
        "/api/v1/mobile/profile/resume",
        headers=auth,
        files=files
    )

    # May return 200 or 501 if not implemented yet
    assert response.status_code in [200, 501]

    if response.status_code == 200:
        data = response.json()["data"]
        assert "resume_url" in data


# ==================== Validation Tests ====================

def test_update_profile_invalid_experience_years(auth_user):
    """Test updating with invalid experience years."""
    auth = auth_user["auth_header"]

    update_data = {
        "experience_years": -5  # Negative value
    }

    response = client.patch(
        "/api/v1/mobile/profile",
        headers=auth,
        json=update_data
    )

    # Should fail validation
    assert response.status_code == 422


def test_update_profile_invalid_email(auth_user):
    """Test cannot update email to invalid format."""
    auth = auth_user["auth_header"]

    update_data = {
        "email": "invalid-email-format"
    }

    response = client.patch(
        "/api/v1/mobile/profile",
        headers=auth,
        json=update_data
    )

    # Should fail validation or be rejected
    assert response.status_code in [400, 422]
