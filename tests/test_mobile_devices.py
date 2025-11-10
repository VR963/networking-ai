"""
Comprehensive tests for Mobile Device Management API.

Tests cover:
- Device listing
- Device updates
- Push token management
- Device deactivation
- Multi-device support
"""

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from src.networking_ai.api.main import app
from src.networking_ai.models.user import User
from src.networking_ai.models.mobile import MobileDevice

client = TestClient(app)


@pytest.fixture
def auth_user_with_devices(db_session):
    """Create authenticated user with multiple devices."""
    # Register user with first device
    user_data = {
        "email": "deviceuser@test.com",
        "password": "SecurePass123!",
        "full_name": "Device Test User",
        "role": "jobseeker",
        "device": {
            "platform": "ios",
            "device_id": "iphone_device",
            "push_token": "fcm_token_ios",
            "app_version": "1.0.0",
            "os_version": "iOS 17.0"
        }
    }

    response = client.post("/api/v1/mobile/auth/register", json=user_data)
    access_token = response.json()["data"]["tokens"]["access_token"]
    user_id = response.json()["data"]["user"]["id"]

    # Add second device manually
    second_device = MobileDevice(
        user_id=user_id,
        platform="android",
        device_id="android_device",
        push_token="fcm_token_android",
        app_version="1.0.0",
        os_version="Android 14",
        is_active=True
    )
    db_session.add(second_device)
    db_session.commit()

    return {
        "auth_header": {"Authorization": f"Bearer {access_token}"},
        "user_id": user_id
    }


# ==================== Device Listing Tests ====================

def test_list_devices_success(auth_user_with_devices):
    """Test successful device listing."""
    auth = auth_user_with_devices["auth_header"]

    response = client.get("/api/v1/mobile/devices", headers=auth)

    assert response.status_code == 200
    data = response.json()["data"]

    assert "data" in data
    devices = data["data"]
    assert len(devices) >= 2

    # Check device structure
    device = devices[0]
    assert "id" in device
    assert "platform" in device
    assert "device_id" in device
    assert "is_active" in device
    assert "last_used_at" in device


def test_list_devices_shows_platform_info(auth_user_with_devices):
    """Test device listing includes platform information."""
    auth = auth_user_with_devices["auth_header"]

    response = client.get("/api/v1/mobile/devices", headers=auth)

    assert response.status_code == 200
    devices = response.json()["data"]["data"]

    # Should have both iOS and Android devices
    platforms = {d["platform"] for d in devices}
    assert "ios" in platforms
    assert "android" in platforms


def test_list_devices_without_auth_fails():
    """Test device listing without authentication fails."""
    response = client.get("/api/v1/mobile/devices")

    assert response.status_code == 401


# ==================== Device Update Tests ====================

def test_update_device_push_token(auth_user_with_devices, db_session):
    """Test updating device push token."""
    auth = auth_user_with_devices["auth_header"]

    update_data = {
        "device_id": "iphone_device",
        "push_token": "new_fcm_token_ios",
        "app_version": "1.1.0"
    }

    response = client.patch(
        "/api/v1/mobile/devices",
        headers=auth,
        json=update_data
    )

    assert response.status_code == 200

    # Verify device updated in database
    device = db_session.query(MobileDevice).filter(
        MobileDevice.device_id == "iphone_device"
    ).first()

    assert device is not None
    assert device.push_token == "new_fcm_token_ios"
    assert device.app_version == "1.1.0"


def test_update_device_app_version(auth_user_with_devices, db_session):
    """Test updating device app version."""
    auth = auth_user_with_devices["auth_header"]

    update_data = {
        "device_id": "android_device",
        "app_version": "2.0.0",
        "os_version": "Android 15"
    }

    response = client.patch(
        "/api/v1/mobile/devices",
        headers=auth,
        json=update_data
    )

    assert response.status_code == 200

    # Verify update
    device = db_session.query(MobileDevice).filter(
        MobileDevice.device_id == "android_device"
    ).first()

    assert device.app_version == "2.0.0"
    assert device.os_version == "Android 15"


# ==================== Device Deactivation Tests ====================

def test_deactivate_device(auth_user_with_devices, db_session):
    """Test deactivating a device."""
    auth = auth_user_with_devices["auth_header"]

    response = client.delete(
        "/api/v1/mobile/devices/android_device",
        headers=auth
    )

    assert response.status_code == 204

    # Verify device marked as inactive
    device = db_session.query(MobileDevice).filter(
        MobileDevice.device_id == "android_device"
    ).first()

    assert device is not None
    assert device.is_active is False


def test_deactivate_nonexistent_device(auth_user_with_devices):
    """Test deactivating non-existent device fails gracefully."""
    auth = auth_user_with_devices["auth_header"]

    response = client.delete(
        "/api/v1/mobile/devices/nonexistent_device",
        headers=auth
    )

    # Should return 404 or handle gracefully
    assert response.status_code in [204, 404]


def test_cannot_deactivate_other_users_device(auth_user_with_devices, db_session):
    """Test user cannot deactivate another user's device."""
    # Create second user
    user2_data = {
        "email": "user2dev@test.com",
        "password": "SecurePass123!",
        "full_name": "User 2 Device",
        "role": "jobseeker",
        "device": {
            "platform": "ios",
            "device_id": "user2_iphone",
            "push_token": "fcm_token_user2"
        }
    }

    response = client.post("/api/v1/mobile/auth/register", json=user2_data)
    user2_token = response.json()["data"]["tokens"]["access_token"]
    user2_auth = {"Authorization": f"Bearer {user2_token}"}

    # User 2 tries to deactivate User 1's device
    auth = auth_user_with_devices["auth_header"]

    response = client.delete(
        "/api/v1/mobile/devices/iphone_device",
        headers=user2_auth
    )

    # Should fail or return 404 (not found in user2's devices)
    # Either way, the device should still be active
    device = db_session.query(MobileDevice).filter(
        MobileDevice.device_id == "iphone_device"
    ).first()

    assert device.is_active is True


# ==================== Multi-Device Tests ====================

def test_multiple_devices_can_be_active(auth_user_with_devices, db_session):
    """Test user can have multiple active devices simultaneously."""
    user_id = auth_user_with_devices["user_id"]

    active_devices = db_session.query(MobileDevice).filter(
        MobileDevice.user_id == user_id,
        MobileDevice.is_active == True
    ).count()

    # Should have at least 2 active devices
    assert active_devices >= 2
