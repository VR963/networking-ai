"""
Comprehensive tests for Mobile Notifications API.

Tests cover:
- Notification listing
- Marking notifications as read
- Notification filtering
- Notification preferences
- Unread count tracking
"""

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session
from datetime import datetime

from src.networking_ai.api.main import app
from src.networking_ai.models.user import User
from src.networking_ai.models.notification import Notification, NotificationStatus, NotificationType

client = TestClient(app)


@pytest.fixture
def auth_user_with_notifications(db_session):
    """Create authenticated user with notifications."""
    # Register user
    user_data = {
        "email": "notifuser@test.com",
        "password": "SecurePass123!",
        "full_name": "Notification Test User",
        "role": "jobseeker",
        "device": {
            "platform": "ios",
            "device_id": "test_device_notif",
            "push_token": "fcm_token"
        }
    }

    response = client.post("/api/v1/mobile/auth/register", json=user_data)
    access_token = response.json()["data"]["tokens"]["access_token"]
    user_id = response.json()["data"]["user"]["id"]

    # Create notifications
    notifications = [
        Notification(
            user_id=user_id,
            type=NotificationType.APPLICATION_UPDATE,
            title="Application Update",
            message="Your application has been reviewed",
            status=NotificationStatus.UNREAD,
            created_at=datetime.utcnow()
        ),
        Notification(
            user_id=user_id,
            type=NotificationType.MESSAGE,
            title="New Message",
            message="You have a new message from TechCorp",
            status=NotificationStatus.UNREAD,
            created_at=datetime.utcnow()
        ),
        Notification(
            user_id=user_id,
            type=NotificationType.INTERVIEW_REMINDER,
            title="Interview Reminder",
            message="Your interview is tomorrow at 2 PM",
            status=NotificationStatus.READ,
            created_at=datetime.utcnow()
        )
    ]

    for notif in notifications:
        db_session.add(notif)

    db_session.commit()

    return {
        "auth_header": {"Authorization": f"Bearer {access_token}"},
        "user_id": user_id,
        "notifications": notifications
    }


# ==================== Notification Listing Tests ====================

def test_list_notifications_success(auth_user_with_notifications):
    """Test successful notification listing."""
    auth = auth_user_with_notifications["auth_header"]

    response = client.get("/api/v1/mobile/notifications", headers=auth)

    assert response.status_code == 200
    data = response.json()["data"]

    assert "data" in data
    assert "meta" in data
    assert "unread_count" in data["meta"]

    notifications = data["data"]
    assert len(notifications) == 3

    # Check notification structure
    notif = notifications[0]
    assert "id" in notif
    assert "type" in notif
    assert "title" in notif
    assert "message" in notif
    assert "is_read" in notif
    assert "created_at" in notif


def test_list_notifications_unread_only(auth_user_with_notifications):
    """Test filtering notifications to show only unread."""
    auth = auth_user_with_notifications["auth_header"]

    response = client.get(
        "/api/v1/mobile/notifications?unread_only=true",
        headers=auth
    )

    assert response.status_code == 200
    data = response.json()["data"]

    notifications = data["data"]
    # Should only return unread notifications
    assert all(not notif["is_read"] for notif in notifications)
    assert len(notifications) == 2  # Two unread notifications


def test_list_notifications_shows_unread_count(auth_user_with_notifications):
    """Test unread count is included in response."""
    auth = auth_user_with_notifications["auth_header"]

    response = client.get("/api/v1/mobile/notifications", headers=auth)

    assert response.status_code == 200
    data = response.json()["data"]

    assert data["meta"]["unread_count"] == 2


def test_list_notifications_limit(auth_user_with_notifications):
    """Test limiting number of notifications returned."""
    auth = auth_user_with_notifications["auth_header"]

    response = client.get(
        "/api/v1/mobile/notifications?limit=2",
        headers=auth
    )

    assert response.status_code == 200
    data = response.json()["data"]

    notifications = data["data"]
    assert len(notifications) <= 2


# ==================== Mark as Read Tests ====================

def test_mark_notification_as_read(auth_user_with_notifications, db_session):
    """Test marking single notification as read."""
    auth = auth_user_with_notifications["auth_header"]
    notifications = auth_user_with_notifications["notifications"]

    # Get an unread notification
    unread_notif = next(n for n in notifications if n.status == NotificationStatus.UNREAD)

    response = client.post(
        f"/api/v1/mobile/notifications/{unread_notif.id}/read",
        headers=auth
    )

    assert response.status_code == 204

    # Verify notification marked as read in database
    db_session.refresh(unread_notif)
    assert unread_notif.status == NotificationStatus.READ
    assert unread_notif.read_at is not None


def test_mark_all_notifications_as_read(auth_user_with_notifications, db_session):
    """Test marking all notifications as read."""
    auth = auth_user_with_notifications["auth_header"]

    response = client.post(
        "/api/v1/mobile/notifications/read-all",
        headers=auth
    )

    assert response.status_code == 204

    # Verify all notifications marked as read
    user_id = auth_user_with_notifications["user_id"]
    unread_count = db_session.query(Notification).filter(
        Notification.user_id == user_id,
        Notification.status == NotificationStatus.UNREAD
    ).count()

    assert unread_count == 0


def test_mark_nonexistent_notification_as_read(auth_user_with_notifications):
    """Test marking non-existent notification returns 404."""
    auth = auth_user_with_notifications["auth_header"]

    response = client.post(
        "/api/v1/mobile/notifications/99999/read",
        headers=auth
    )

    assert response.status_code == 404
    data = response.json()
    assert "error" in data
    assert data["error"]["code"] == "NOT_FOUND"


# ==================== Notification Settings Tests ====================

def test_get_notification_settings(auth_user_with_notifications):
    """Test retrieving notification preferences."""
    auth = auth_user_with_notifications["auth_header"]

    response = client.get(
        "/api/v1/mobile/notifications/settings",
        headers=auth
    )

    assert response.status_code == 200
    data = response.json()["data"]

    assert "email" in data
    assert "push" in data

    # Check email settings structure
    assert "application_updates" in data["email"]
    assert "interview_reminders" in data["email"]
    assert "new_matches" in data["email"]
    assert "messages" in data["email"]

    # Check push settings structure
    assert "application_updates" in data["push"]
    assert "interview_reminders" in data["push"]


def test_update_notification_settings(auth_user_with_notifications):
    """Test updating notification preferences."""
    auth = auth_user_with_notifications["auth_header"]

    update_data = {
        "email": {
            "application_updates": True,
            "interview_reminders": True,
            "new_matches": False,
            "messages": True
        },
        "push": {
            "application_updates": True,
            "interview_reminders": True,
            "new_matches": True,
            "messages": False
        }
    }

    response = client.patch(
        "/api/v1/mobile/notifications/settings",
        headers=auth,
        json=update_data
    )

    assert response.status_code == 200
    data = response.json()["data"]

    # Verify settings updated
    assert "email" in data
    assert "push" in data
