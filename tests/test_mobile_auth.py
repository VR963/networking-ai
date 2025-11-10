"""
Comprehensive tests for Mobile Authentication API.

Tests cover:
- User registration
- Login flow
- Token refresh
- Logout
- Error handling
- Security validations
"""

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session
from datetime import datetime, timedelta
import jwt

from src.networking_ai.api.main import app
from src.networking_ai.database import get_db
from src.networking_ai.models.user import User, UserRole, AccountStatus
from src.networking_ai.models.mobile import MobileDevice, RefreshToken
from src.networking_ai.config import get_settings

client = TestClient(app)
settings = get_settings()


@pytest.fixture
def db_session(db_session):
    """Override db_session fixture."""
    return db_session


@pytest.fixture
def test_user_data():
    """Sample user registration data."""
    return {
        "email": "test@example.com",
        "password": "SecurePass123!",
        "full_name": "Test User",
        "role": "jobseeker",
        "device": {
            "platform": "ios",
            "device_id": "test_device_123",
            "push_token": "fcm_token_xyz",
            "app_version": "1.0.0",
            "os_version": "iOS 17.0"
        }
    }


# ==================== Registration Tests ====================

def test_register_success(db_session, test_user_data):
    """Test successful user registration."""
    response = client.post("/api/v1/mobile/auth/register", json=test_user_data)

    assert response.status_code == 201
    data = response.json()

    assert "data" in data
    assert "user" in data["data"]
    assert "tokens" in data["data"]

    # Check user data
    user_data = data["data"]["user"]
    assert user_data["email"] == test_user_data["email"]
    assert user_data["full_name"] == test_user_data["full_name"]
    assert user_data["role"] == test_user_data["role"]

    # Check tokens
    tokens = data["data"]["tokens"]
    assert "access_token" in tokens
    assert "refresh_token" in tokens
    assert tokens["token_type"] == "bearer"
    assert tokens["expires_in"] == 900  # 15 minutes

    # Verify user created in database
    user = db_session.query(User).filter(User.email == test_user_data["email"]).first()
    assert user is not None
    assert user.role == UserRole.JOBSEEKER
    assert user.status == AccountStatus.ACTIVE


def test_register_duplicate_email(db_session, test_user_data):
    """Test registration with duplicate email fails."""
    # First registration
    client.post("/api/v1/mobile/auth/register", json=test_user_data)

    # Second registration with same email
    response = client.post("/api/v1/mobile/auth/register", json=test_user_data)

    assert response.status_code == 409
    data = response.json()
    assert "error" in data
    assert data["error"]["code"] == "ALREADY_EXISTS"


def test_register_invalid_email(db_session, test_user_data):
    """Test registration with invalid email fails."""
    test_user_data["email"] = "invalid-email"

    response = client.post("/api/v1/mobile/auth/register", json=test_user_data)

    assert response.status_code == 422  # Validation error


def test_register_weak_password(db_session, test_user_data):
    """Test registration with weak password."""
    test_user_data["password"] = "123"  # Too short

    response = client.post("/api/v1/mobile/auth/register", json=test_user_data)

    assert response.status_code == 422  # Validation error


def test_register_invalid_role(db_session, test_user_data):
    """Test registration with invalid role fails."""
    test_user_data["role"] = "invalid_role"

    response = client.post("/api/v1/mobile/auth/register", json=test_user_data)

    assert response.status_code == 400
    data = response.json()
    assert "error" in data


def test_register_creates_device(db_session, test_user_data):
    """Test registration creates device record."""
    response = client.post("/api/v1/mobile/auth/register", json=test_user_data)

    assert response.status_code == 201

    # Verify device created
    device = db_session.query(MobileDevice).filter(
        MobileDevice.device_id == test_user_data["device"]["device_id"]
    ).first()

    assert device is not None
    assert device.platform == test_user_data["device"]["platform"]
    assert device.push_token == test_user_data["device"]["push_token"]
    assert device.is_active is True


# ==================== Login Tests ====================

def test_login_success(db_session, test_user_data):
    """Test successful login."""
    # Register user first
    client.post("/api/v1/mobile/auth/register", json=test_user_data)

    # Login
    login_data = {
        "email": test_user_data["email"],
        "password": test_user_data["password"],
        "device": test_user_data["device"]
    }

    response = client.post("/api/v1/mobile/auth/login", json=login_data)

    assert response.status_code == 200
    data = response.json()

    assert "data" in data
    assert "user" in data["data"]
    assert "tokens" in data["data"]

    # Check tokens
    tokens = data["data"]["tokens"]
    assert "access_token" in tokens
    assert "refresh_token" in tokens


def test_login_wrong_password(db_session, test_user_data):
    """Test login with wrong password fails."""
    # Register user first
    client.post("/api/v1/mobile/auth/register", json=test_user_data)

    # Login with wrong password
    login_data = {
        "email": test_user_data["email"],
        "password": "WrongPassword123!",
        "device": test_user_data["device"]
    }

    response = client.post("/api/v1/mobile/auth/login", json=login_data)

    assert response.status_code == 401
    data = response.json()
    assert "error" in data
    assert data["error"]["code"] == "UNAUTHORIZED"


def test_login_nonexistent_user(db_session, test_user_data):
    """Test login with non-existent user fails."""
    login_data = {
        "email": "nonexistent@example.com",
        "password": "SomePassword123!",
        "device": test_user_data["device"]
    }

    response = client.post("/api/v1/mobile/auth/login", json=login_data)

    assert response.status_code == 401


def test_login_updates_device(db_session, test_user_data):
    """Test login updates device information."""
    # Register user
    client.post("/api/v1/mobile/auth/register", json=test_user_data)

    # Login with updated device info
    login_data = {
        "email": test_user_data["email"],
        "password": test_user_data["password"],
        "device": {
            **test_user_data["device"],
            "app_version": "2.0.0",  # Updated version
            "push_token": "new_fcm_token"
        }
    }

    response = client.post("/api/v1/mobile/auth/login", json=login_data)

    assert response.status_code == 200

    # Verify device updated
    device = db_session.query(MobileDevice).filter(
        MobileDevice.device_id == test_user_data["device"]["device_id"]
    ).first()

    assert device.app_version == "2.0.0"
    assert device.push_token == "new_fcm_token"


# ==================== Token Refresh Tests ====================

def test_refresh_token_success(db_session, test_user_data):
    """Test successful token refresh."""
    # Register and get tokens
    register_response = client.post("/api/v1/mobile/auth/register", json=test_user_data)
    refresh_token = register_response.json()["data"]["tokens"]["refresh_token"]

    # Refresh token
    response = client.post(
        "/api/v1/mobile/auth/refresh",
        json={"refresh_token": refresh_token}
    )

    assert response.status_code == 200
    data = response.json()

    assert "data" in data
    assert "access_token" in data["data"]
    assert "token_type" in data["data"]
    assert "expires_in" in data["data"]


def test_refresh_invalid_token(db_session):
    """Test refresh with invalid token fails."""
    response = client.post(
        "/api/v1/mobile/auth/refresh",
        json={"refresh_token": "invalid_token"}
    )

    assert response.status_code == 401


def test_refresh_expired_token(db_session, test_user_data):
    """Test refresh with expired token fails."""
    # Create an expired refresh token
    expired_payload = {
        "sub": "123",
        "device_id": "test_device",
        "exp": datetime.utcnow() - timedelta(days=1),  # Expired
        "iat": datetime.utcnow() - timedelta(days=2),
        "type": "refresh"
    }

    expired_token = jwt.encode(
        expired_payload,
        settings.JWT_SECRET_KEY,
        algorithm=settings.JWT_ALGORITHM
    )

    response = client.post(
        "/api/v1/mobile/auth/refresh",
        json={"refresh_token": expired_token}
    )

    assert response.status_code == 401
    data = response.json()
    assert data["error"]["code"] == "TOKEN_EXPIRED"


# ==================== Logout Tests ====================

def test_logout_single_device(db_session, test_user_data):
    """Test logout from single device."""
    # Register user
    response = client.post("/api/v1/mobile/auth/register", json=test_user_data)

    # Logout specific device
    logout_data = {"device_id": test_user_data["device"]["device_id"]}
    response = client.post("/api/v1/mobile/auth/logout", json=logout_data)

    assert response.status_code == 204

    # Verify device marked as inactive
    device = db_session.query(MobileDevice).filter(
        MobileDevice.device_id == test_user_data["device"]["device_id"]
    ).first()

    assert device.is_active is False


# ==================== JWT Token Validation Tests ====================

def test_access_token_structure(db_session, test_user_data):
    """Test access token has correct structure."""
    response = client.post("/api/v1/mobile/auth/register", json=test_user_data)
    access_token = response.json()["data"]["tokens"]["access_token"]

    # Decode token
    payload = jwt.decode(
        access_token,
        settings.JWT_SECRET_KEY,
        algorithms=[settings.JWT_ALGORITHM]
    )

    assert "sub" in payload  # User ID
    assert "exp" in payload  # Expiration
    assert "iat" in payload  # Issued at
    assert payload.get("type") == "access"


def test_refresh_token_is_hashed_in_db(db_session, test_user_data):
    """Test refresh token is stored hashed in database."""
    response = client.post("/api/v1/mobile/auth/register", json=test_user_data)
    refresh_token_str = response.json()["data"]["tokens"]["refresh_token"]

    # Token should exist in database but hashed
    stored_token = db_session.query(RefreshToken).first()

    assert stored_token is not None
    assert stored_token.token_hash != refresh_token_str  # Should be hashed
    assert len(stored_token.token_hash) == 64  # SHA256 hash length
