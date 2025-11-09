"""
Tests for Realtime Notification Service - Phase 11

Tests WebSocket notification broadcasting and real-time delivery.
"""

import pytest
from datetime import datetime, timedelta
from unittest.mock import Mock, AsyncMock, MagicMock

from src.networking_ai.services.realtime_notification_service import (
    RealtimeNotificationService,
    notify_user,
    update_notification_count
)
from src.networking_ai.websocket.notification_events import (
    NotificationCreatedEvent,
    NotificationReadEvent,
    NotificationDismissedEvent,
    NotificationClickedEvent,
    NotificationBatchEvent,
    NotificationCountUpdatedEvent,
    PriorityNotificationEvent
)
from src.networking_ai.models.notification import (
    Notification,
    NotificationType,
    NotificationPriority,
    NotificationStatus
)


class MockConnectionManager:
    """Mock connection manager for testing."""

    def __init__(self):
        self.sent_messages = []
        self.user_messages = {}
        self.online_users = set()

    async def send_to_user(self, user_id: int, message: dict):
        """Record sent messages."""
        if user_id not in self.user_messages:
            self.user_messages[user_id] = []
        self.user_messages[user_id].append(message)
        self.sent_messages.append((user_id, message))

    def is_user_online(self, user_id: int) -> bool:
        """Check if user is online."""
        return user_id in self.online_users

    def add_online_user(self, user_id: int):
        """Add user to online set."""
        self.online_users.add(user_id)


@pytest.fixture
def mock_connection_manager():
    """Create mock connection manager."""
    return MockConnectionManager()


@pytest.fixture
def realtime_service(mock_connection_manager):
    """Create realtime notification service with mock connection manager."""
    return RealtimeNotificationService(connection_manager=mock_connection_manager)


@pytest.fixture
def sample_notification():
    """Create a sample notification."""
    notification = Mock(spec=Notification)
    notification.id = 123
    notification.user_id = 1
    notification.notification_type = NotificationType.MATCH_NEW
    notification.priority = NotificationPriority.HIGH
    notification.title = "🎯 New Match Found!"
    notification.message = "You have a new 85% match: Software Engineer at TechCorp"
    notification.action_url = "/matches/123"
    notification.action_text = "View Match"
    notification.extra_data = {"match_score": 0.85, "job_title": "Software Engineer"}
    notification.expires_at = datetime.utcnow() + timedelta(days=30)
    notification.created_at = datetime.utcnow()
    notification.is_read = Mock(return_value=False)
    return notification


# ==================== Notification Broadcast Tests ====================

@pytest.mark.asyncio
async def test_broadcast_notification_normal(realtime_service, mock_connection_manager, sample_notification):
    """Test broadcasting a normal notification."""
    sample_notification.priority = NotificationPriority.NORMAL

    await realtime_service.broadcast_notification(sample_notification)

    # Check message was sent
    assert len(mock_connection_manager.sent_messages) == 1
    user_id, message = mock_connection_manager.sent_messages[0]

    assert user_id == 1
    assert message["event"] == "notification.new"
    assert message["data"]["notification_id"] == 123
    assert message["data"]["title"] == "🎯 New Match Found!"


@pytest.mark.asyncio
async def test_broadcast_notification_priority(realtime_service, mock_connection_manager, sample_notification):
    """Test broadcasting a priority notification."""
    sample_notification.priority = NotificationPriority.URGENT

    await realtime_service.broadcast_notification(sample_notification)

    user_id, message = mock_connection_manager.sent_messages[0]

    # Should use priority event
    assert message["event"] == "notification.priority"
    assert message["data"]["priority"] == "urgent"
    assert message["data"]["requires_action"] is True


@pytest.mark.asyncio
async def test_broadcast_notification_with_override(realtime_service, mock_connection_manager, sample_notification):
    """Test broadcasting notification with priority override."""
    sample_notification.priority = NotificationPriority.NORMAL

    await realtime_service.broadcast_notification(sample_notification, priority_override="urgent")

    user_id, message = mock_connection_manager.sent_messages[0]

    # Should use priority event despite normal priority
    assert message["event"] == "notification.priority"
    assert message["data"]["sound"] == "alert"
    assert message["data"]["vibrate"] is True


# ==================== Notification Read Tests ====================

@pytest.mark.asyncio
async def test_broadcast_notification_read(realtime_service, mock_connection_manager):
    """Test broadcasting notification read event."""
    await realtime_service.broadcast_notification_read(
        notification_id=123,
        user_id=1
    )

    user_id, message = mock_connection_manager.sent_messages[0]

    assert message["event"] == "notification.read"
    assert message["data"]["notification_id"] == 123
    assert message["data"]["user_id"] == 1
    assert "read_at" in message["data"]


# ==================== Notification Dismissed Tests ====================

@pytest.mark.asyncio
async def test_broadcast_notification_dismissed(realtime_service, mock_connection_manager):
    """Test broadcasting notification dismissed event."""
    await realtime_service.broadcast_notification_dismissed(
        notification_id=123,
        user_id=1
    )

    user_id, message = mock_connection_manager.sent_messages[0]

    assert message["event"] == "notification.dismissed"
    assert message["data"]["notification_id"] == 123
    assert "dismissed_at" in message["data"]


# ==================== Notification Clicked Tests ====================

@pytest.mark.asyncio
async def test_broadcast_notification_clicked(realtime_service, mock_connection_manager):
    """Test broadcasting notification clicked event."""
    await realtime_service.broadcast_notification_clicked(
        notification_id=123,
        user_id=1,
        action_url="/matches/123"
    )

    user_id, message = mock_connection_manager.sent_messages[0]

    assert message["event"] == "notification.clicked"
    assert message["data"]["notification_id"] == 123
    assert message["data"]["action_url"] == "/matches/123"
    assert "clicked_at" in message["data"]


# ==================== Batch Notification Tests ====================

@pytest.mark.asyncio
async def test_broadcast_notification_batch(realtime_service, mock_connection_manager):
    """Test broadcasting multiple notifications at once."""
    # Create sample notifications
    notifications = []
    for i in range(5):
        notification = Mock(spec=Notification)
        notification.id = i + 1
        notification.notification_type = NotificationType.MESSAGE_NEW
        notification.title = f"Message {i+1}"
        notification.message = f"Content {i+1}"
        notification.priority = NotificationPriority.NORMAL
        notification.action_url = f"/messages/{i+1}"
        notification.action_text = "View"
        notification.created_at = datetime.utcnow()
        notification.is_read = Mock(return_value=(i % 2 == 0))  # Alternate read/unread
        notifications.append(notification)

    await realtime_service.broadcast_notification_batch(
        user_id=1,
        notifications=notifications
    )

    user_id, message = mock_connection_manager.sent_messages[0]

    assert message["event"] == "notification.batch"
    assert message["data"]["total_count"] == 5
    assert message["data"]["unread_count"] == 2  # 2 unread (indices 1, 3)
    assert len(message["data"]["notifications"]) == 5


# ==================== Count Update Tests ====================

@pytest.mark.asyncio
async def test_broadcast_count_updated(realtime_service, mock_connection_manager):
    """Test broadcasting unread count update."""
    await realtime_service.broadcast_count_updated(
        user_id=1,
        unread_count=5,
        total_count=20
    )

    user_id, message = mock_connection_manager.sent_messages[0]

    assert message["event"] == "notification.count_updated"
    assert message["data"]["unread_count"] == 5
    assert message["data"]["total_count"] == 20
    assert "updated_at" in message["data"]


# ==================== Notification Deleted Tests ====================

@pytest.mark.asyncio
async def test_broadcast_notification_deleted(realtime_service, mock_connection_manager):
    """Test broadcasting notification deleted event."""
    await realtime_service.broadcast_notification_deleted(
        notification_id=123,
        user_id=1
    )

    user_id, message = mock_connection_manager.sent_messages[0]

    assert message["event"] == "notification.deleted"
    assert message["data"]["notification_id"] == 123
    assert "deleted_at" in message["data"]


# ==================== All Read Tests ====================

@pytest.mark.asyncio
async def test_broadcast_all_read(realtime_service, mock_connection_manager):
    """Test broadcasting all notifications read event."""
    await realtime_service.broadcast_all_read(
        user_id=1,
        count_marked=10
    )

    user_id, message = mock_connection_manager.sent_messages[0]

    assert message["event"] == "notification.all_read"
    assert message["data"]["count_marked"] == 10
    assert "marked_at" in message["data"]


# ==================== Daily Digest Tests ====================

@pytest.mark.asyncio
async def test_send_daily_digest(realtime_service, mock_connection_manager):
    """Test sending daily notification digest."""
    # Create sample notifications
    notifications = [Mock(spec=Notification) for _ in range(3)]
    for i, notification in enumerate(notifications):
        notification.id = i + 1
        notification.notification_type = NotificationType.MESSAGE_NEW
        notification.title = f"Title {i+1}"
        notification.message = f"Message {i+1}"
        notification.priority = NotificationPriority.NORMAL
        notification.action_url = f"/messages/{i+1}"
        notification.action_text = "View"
        notification.created_at = datetime.utcnow()
        notification.is_read = Mock(return_value=False)

    await realtime_service.send_daily_digest(
        user_id=1,
        notifications=notifications
    )

    # Should send as batch
    user_id, message = mock_connection_manager.sent_messages[0]
    assert message["event"] == "notification.batch"
    assert message["data"]["total_count"] == 3


# ==================== User Online Check Tests ====================

def test_is_user_online(realtime_service, mock_connection_manager):
    """Test checking if user is online."""
    mock_connection_manager.add_online_user(1)

    assert realtime_service.is_user_online(1) is True
    assert realtime_service.is_user_online(2) is False


# ==================== Test Notification Tests ====================

@pytest.mark.asyncio
async def test_send_test_notification(realtime_service, mock_connection_manager):
    """Test sending a test notification."""
    await realtime_service.send_test_notification(
        user_id=1,
        title="Test Title",
        message="Test Message"
    )

    user_id, message = mock_connection_manager.sent_messages[0]

    assert message["event"] == "notification.new"
    assert message["data"]["notification_id"] == 0  # Test notifications have ID 0
    assert message["data"]["title"] == "Test Title"
    assert message["data"]["message"] == "Test Message"
    assert message["data"]["type"] == "system_test"


# ==================== Helper Function Tests ====================

@pytest.mark.asyncio
async def test_notify_user_helper(sample_notification):
    """Test notify_user helper function."""
    mock_service = Mock()
    mock_service.broadcast_notification = AsyncMock()

    await notify_user(
        user_id=1,
        notification=sample_notification,
        service=mock_service
    )

    mock_service.broadcast_notification.assert_called_once_with(sample_notification)


@pytest.mark.asyncio
async def test_update_notification_count_helper():
    """Test update_notification_count helper function."""
    mock_service = Mock()
    mock_service.broadcast_count_updated = AsyncMock()

    await update_notification_count(
        user_id=1,
        unread_count=5,
        total_count=20,
        service=mock_service
    )

    mock_service.broadcast_count_updated.assert_called_once_with(
        user_id=1,
        unread_count=5,
        total_count=20
    )


# ==================== Multiple Users Tests ====================

@pytest.mark.asyncio
async def test_broadcast_to_multiple_users(mock_connection_manager):
    """Test broadcasting to multiple users."""
    service = RealtimeNotificationService(connection_manager=mock_connection_manager)

    # Send to user 1
    await service.send_test_notification(user_id=1, title="User 1", message="Message 1")

    # Send to user 2
    await service.send_test_notification(user_id=2, title="User 2", message="Message 2")

    # Check both users received messages
    assert 1 in mock_connection_manager.user_messages
    assert 2 in mock_connection_manager.user_messages
    assert len(mock_connection_manager.user_messages[1]) == 1
    assert len(mock_connection_manager.user_messages[2]) == 1


# ==================== Error Handling Tests ====================

@pytest.mark.asyncio
async def test_broadcast_handles_errors():
    """Test that broadcast handles connection manager errors gracefully."""
    # Create connection manager that raises errors
    error_manager = Mock()
    error_manager.send_to_user = AsyncMock(side_effect=Exception("Connection error"))

    service = RealtimeNotificationService(connection_manager=error_manager)

    # Should not raise exception
    await service.broadcast_count_updated(user_id=1, unread_count=5, total_count=20)


# ==================== Event Format Validation Tests ====================

@pytest.mark.asyncio
async def test_notification_event_format(realtime_service, mock_connection_manager, sample_notification):
    """Test that notification event has correct format."""
    await realtime_service.broadcast_notification(sample_notification)

    user_id, message = mock_connection_manager.sent_messages[0]

    # Validate required fields
    assert "event" in message
    assert "timestamp" in message
    assert "data" in message

    # Validate data fields
    data = message["data"]
    assert "notification_id" in data
    assert "user_id" in data
    assert "title" in data
    assert "message" in data
    assert "type" in data
    assert "priority" in data
