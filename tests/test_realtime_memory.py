"""
Tests for Realtime Memory Service - Phase 11

Tests WebSocket broadcasting for memory events.
"""

import pytest
import asyncio
from datetime import datetime
from unittest.mock import Mock, AsyncMock, MagicMock

from src.networking_ai.services.realtime_memory_service import (
    RealtimeMemoryService,
    notify_memory_event
)
from src.networking_ai.websocket.memory_events import (
    MemoryCreatedEvent,
    MemoryUpdatedEvent,
    MemoryDeletedEvent,
    MemoryTierChangedEvent
)


class MockConnectionManager:
    """Mock connection manager for testing."""

    def __init__(self):
        self.sent_messages = []
        self.user_messages = {}

    async def send_to_user(self, user_id: int, message: dict):
        """Record sent messages."""
        if user_id not in self.user_messages:
            self.user_messages[user_id] = []
        self.user_messages[user_id].append(message)
        self.sent_messages.append((user_id, message))

    async def send_personal_message(self, connection_id: str, message: dict):
        """Record personal messages."""
        self.sent_messages.append((connection_id, message))


@pytest.fixture
def mock_connection_manager():
    """Create mock connection manager."""
    return MockConnectionManager()


@pytest.fixture
def realtime_service(mock_connection_manager):
    """Create realtime memory service with mock connection manager."""
    return RealtimeMemoryService(connection_manager=mock_connection_manager)


# ==================== Memory Created Event Tests ====================

@pytest.mark.asyncio
async def test_broadcast_memory_created(realtime_service, mock_connection_manager):
    """Test broadcasting memory created event."""
    await realtime_service.broadcast_memory_created(
        memory_id=123,
        user_id=1,
        content_preview="Important meeting notes about project X...",
        importance=0.8,
        tier="hot",
        memory_type="conversation"
    )

    # Check message was sent
    assert len(mock_connection_manager.sent_messages) == 1
    user_id, message = mock_connection_manager.sent_messages[0]

    assert user_id == 1
    assert message["event"] == "memory.created"
    assert message["data"]["memory_id"] == 123
    assert message["data"]["importance"] == 0.8
    assert message["data"]["tier"] == "hot"
    assert "Important meeting" in message["data"]["content_preview"]


@pytest.mark.asyncio
async def test_broadcast_memory_created_truncates_preview(realtime_service, mock_connection_manager):
    """Test that content preview is truncated to 100 characters."""
    long_content = "x" * 200

    await realtime_service.broadcast_memory_created(
        memory_id=123,
        user_id=1,
        content_preview=long_content,
        importance=0.5,
        tier="warm",
        memory_type="document"
    )

    user_id, message = mock_connection_manager.sent_messages[0]
    preview = message["data"]["content_preview"]

    assert len(preview) <= 100


# ==================== Memory Updated Event Tests ====================

@pytest.mark.asyncio
async def test_broadcast_memory_updated(realtime_service, mock_connection_manager):
    """Test broadcasting memory updated event."""
    changes = {
        "importance": {"old": 0.5, "new": 0.8},
        "metadata": {"old": {}, "new": {"tag": "important"}}
    }

    await realtime_service.broadcast_memory_updated(
        memory_id=123,
        user_id=1,
        changes=changes
    )

    user_id, message = mock_connection_manager.sent_messages[0]

    assert message["event"] == "memory.updated"
    assert message["data"]["memory_id"] == 123
    assert message["data"]["changes"] == changes


# ==================== Memory Deleted Event Tests ====================

@pytest.mark.asyncio
async def test_broadcast_memory_deleted(realtime_service, mock_connection_manager):
    """Test broadcasting memory deleted event."""
    await realtime_service.broadcast_memory_deleted(
        memory_id=123,
        user_id=1
    )

    user_id, message = mock_connection_manager.sent_messages[0]

    assert message["event"] == "memory.deleted"
    assert message["data"]["memory_id"] == 123
    assert message["data"]["user_id"] == 1
    assert "deleted_at" in message["data"]


# ==================== Tier Changed Event Tests ====================

@pytest.mark.asyncio
async def test_broadcast_tier_changed_promotion(realtime_service, mock_connection_manager):
    """Test broadcasting tier promotion event."""
    await realtime_service.broadcast_tier_changed(
        memory_id=123,
        user_id=1,
        old_tier="warm",
        new_tier="hot",
        decay_score=0.85,
        reason="promotion"
    )

    user_id, message = mock_connection_manager.sent_messages[0]

    assert message["event"] == "memory.tier_changed"
    assert message["data"]["old_tier"] == "warm"
    assert message["data"]["new_tier"] == "hot"
    assert message["data"]["is_promotion"] is True


@pytest.mark.asyncio
async def test_broadcast_tier_changed_demotion(realtime_service, mock_connection_manager):
    """Test broadcasting tier demotion event."""
    await realtime_service.broadcast_tier_changed(
        memory_id=123,
        user_id=1,
        old_tier="hot",
        new_tier="cold",
        decay_score=0.25,
        reason="demotion"
    )

    user_id, message = mock_connection_manager.sent_messages[0]

    assert message["event"] == "memory.tier_changed"
    assert message["data"]["is_promotion"] is False


# ==================== Decay Alert Event Tests ====================

@pytest.mark.asyncio
async def test_broadcast_decay_alert(realtime_service, mock_connection_manager):
    """Test broadcasting decay alert event."""
    await realtime_service.broadcast_decay_alert(
        memory_id=123,
        user_id=1,
        current_tier="warm",
        decay_score=0.35,
        content_preview="Meeting notes from last month",
        days_until_demotion=7
    )

    user_id, message = mock_connection_manager.sent_messages[0]

    assert message["event"] == "memory.decay_alert"
    assert message["data"]["current_tier"] == "warm"
    assert message["data"]["decay_score"] == 0.35
    assert message["data"]["days_until_demotion"] == 7
    assert message["data"]["action"] == "access_to_preserve"


# ==================== Stats Update Event Tests ====================

@pytest.mark.asyncio
async def test_broadcast_stats_update(realtime_service, mock_connection_manager):
    """Test broadcasting statistics update."""
    tier_distribution = {"hot": 10, "warm": 50, "cold": 100}

    await realtime_service.broadcast_stats_update(
        user_id=1,
        total_memories=160,
        tier_distribution=tier_distribution,
        cache_hit_rate=0.75,
        avg_importance=0.6
    )

    user_id, message = mock_connection_manager.sent_messages[0]

    assert message["event"] == "memory.stats_updated"
    assert message["data"]["total_memories"] == 160
    assert message["data"]["cache_hit_rate"] == 0.75


# ==================== Batch Changes Tests ====================

@pytest.mark.asyncio
async def test_broadcast_batch_changes(realtime_service, mock_connection_manager):
    """Test broadcasting batch changes."""
    await realtime_service.broadcast_batch_changes(
        user_id=1,
        created=[1, 2, 3],
        updated=[4, 5],
        deleted=[6],
        tier_changed=[7, 8, 9, 10]
    )

    user_id, message = mock_connection_manager.sent_messages[0]

    assert message["event"] == "memory.batch_update"
    assert message["data"]["created_count"] == 3
    assert message["data"]["updated_count"] == 2
    assert message["data"]["deleted_count"] == 1
    assert message["data"]["tier_changed_count"] == 4


# ==================== Helper Function Tests ====================

@pytest.mark.asyncio
async def test_notify_memory_event_created():
    """Test notify_memory_event helper for created event."""
    mock_service = Mock()
    mock_service.broadcast_memory_created = AsyncMock()

    memory_data = {
        "memory_id": 123,
        "content": "Test content",
        "importance": 0.8,
        "tier": "hot",
        "memory_type": "conversation"
    }

    await notify_memory_event(
        event_type="created",
        user_id=1,
        memory_data=memory_data,
        service=mock_service
    )

    # Check the method was called
    mock_service.broadcast_memory_created.assert_called_once()


@pytest.mark.asyncio
async def test_notify_memory_event_deleted():
    """Test notify_memory_event helper for deleted event."""
    mock_service = Mock()
    mock_service.broadcast_memory_deleted = AsyncMock()

    memory_data = {"memory_id": 123}

    await notify_memory_event(
        event_type="deleted",
        user_id=1,
        memory_data=memory_data,
        service=mock_service
    )

    mock_service.broadcast_memory_deleted.assert_called_once()


# ==================== Sync Request Tests ====================

@pytest.mark.asyncio
async def test_handle_sync_request(realtime_service, mock_connection_manager):
    """Test handling memory sync request."""
    result = await realtime_service.handle_sync_request(
        user_id=1,
        last_sync_timestamp="2025-11-09T00:00:00",
        device_id="device_123"
    )

    # Check response
    assert "sync_timestamp" in result
    assert result["memories_updated"] >= 0

    # Check sync response event was sent
    user_id, message = mock_connection_manager.sent_messages[0]
    assert message["event"] == "memory.sync_response"


# ==================== Multiple Users Tests ====================

@pytest.mark.asyncio
async def test_broadcast_to_multiple_users(mock_connection_manager):
    """Test broadcasting to multiple users."""
    service = RealtimeMemoryService(connection_manager=mock_connection_manager)

    # Broadcast to user 1
    await service.broadcast_memory_created(
        memory_id=1, user_id=1, content_preview="User 1 memory",
        importance=0.5, tier="warm", memory_type="general"
    )

    # Broadcast to user 2
    await service.broadcast_memory_created(
        memory_id=2, user_id=2, content_preview="User 2 memory",
        importance=0.5, tier="warm", memory_type="general"
    )

    # Check both users received messages
    assert 1 in mock_connection_manager.user_messages
    assert 2 in mock_connection_manager.user_messages
    assert len(mock_connection_manager.user_messages[1]) == 1
    assert len(mock_connection_manager.user_messages[2]) == 1


# ==================== Error Handling Tests ====================

@pytest.mark.asyncio
async def test_broadcast_handles_connection_manager_errors():
    """Test that broadcast handles connection manager errors gracefully."""
    # Create connection manager that raises errors
    error_manager = Mock()
    error_manager.send_to_user = AsyncMock(side_effect=Exception("Connection error"))

    service = RealtimeMemoryService(connection_manager=error_manager)

    # Should not raise exception
    await service.broadcast_memory_created(
        memory_id=123,
        user_id=1,
        content_preview="Test",
        importance=0.5,
        tier="warm",
        memory_type="general"
    )


# ==================== Event Format Validation Tests ====================

@pytest.mark.asyncio
async def test_memory_created_event_format(realtime_service, mock_connection_manager):
    """Test that memory created event has correct format."""
    await realtime_service.broadcast_memory_created(
        memory_id=123,
        user_id=1,
        content_preview="Test content",
        importance=0.8,
        tier="hot",
        memory_type="conversation"
    )

    user_id, message = mock_connection_manager.sent_messages[0]

    # Validate required fields
    assert "event" in message
    assert "timestamp" in message
    assert "data" in message

    # Validate event type
    assert message["event"] == "memory.created"

    # Validate data fields
    data = message["data"]
    assert "memory_id" in data
    assert "user_id" in data
    assert "content_preview" in data
    assert "importance" in data
    assert "tier" in data
    assert "memory_type" in data
