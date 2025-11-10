"""
Tests for WebSocket Infrastructure - Phase 3 Week 1.

Comprehensive tests for real-time WebSocket features:
- Connection manager
- Connection lifecycle
- Presence tracking
- Event types and schemas
- Broadcasting
- Statistics
"""

import sys
import os
import asyncio
from datetime import datetime, timedelta

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

# Import directly from files to avoid cryptography issues
import importlib.util

def load_module_from_file(file_path, module_name):
    """Load a module directly from a file path."""
    spec = importlib.util.spec_from_file_location(module_name, file_path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[module_name] = module
    spec.loader.exec_module(module)
    return module

# Load connection_manager module
conn_mgr_path = os.path.join(os.path.dirname(__file__), '..', 'src', 'networking_ai', 'websocket', 'connection_manager.py')
conn_mgr_module = load_module_from_file(conn_mgr_path, 'connection_manager')

ConnectionManager = conn_mgr_module.ConnectionManager
ConnectionInfo = conn_mgr_module.ConnectionInfo
PresenceStatus = conn_mgr_module.PresenceStatus

# Load event_types module
event_types_path = os.path.join(os.path.dirname(__file__), '..', 'src', 'networking_ai', 'websocket', 'event_types.py')
event_types_module = load_module_from_file(event_types_path, 'event_types')

EventType = event_types_module.EventType
ConnectedEvent = event_types_module.ConnectedEvent
HeartbeatResponse = event_types_module.HeartbeatResponse
NewMessageEvent = event_types_module.NewMessageEvent
TypingEvent = event_types_module.TypingEvent
NewMatchEvent = event_types_module.NewMatchEvent
PresenceEvent = event_types_module.PresenceEvent
NotificationEvent = event_types_module.NotificationEvent


# ==================== Mock WebSocket ====================

class MockWebSocket:
    """Mock WebSocket for testing."""

    def __init__(self):
        self.messages = []
        self.accepted = False
        self.closed = False

    async def accept(self):
        self.accepted = True

    async def send_json(self, data):
        self.messages.append(data)

    async def send_text(self, text):
        self.messages.append({"text": text})

    async def close(self):
        self.closed = True

    def get_last_message(self):
        return self.messages[-1] if self.messages else None

    def clear_messages(self):
        self.messages = []


# ==================== Test ConnectionInfo ====================

def test_connection_info_creation():
    """Test creating connection info."""
    websocket = MockWebSocket()

    conn_info = ConnectionInfo(
        websocket=websocket,
        user_id=1,
        agent_type="talent",
        agent_id=10
    )

    assert conn_info.user_id == 1
    assert conn_info.agent_type == "talent"
    assert conn_info.agent_id == 10
    assert conn_info.presence == PresenceStatus.ONLINE
    assert not conn_info.is_stale()

    print("✓ ConnectionInfo created successfully")


def test_connection_info_heartbeat():
    """Test connection info heartbeat updates."""
    websocket = MockWebSocket()
    conn_info = ConnectionInfo(websocket=websocket, user_id=1)

    initial_time = conn_info.last_heartbeat

    # Wait a tiny bit
    import time
    time.sleep(0.01)

    conn_info.update_heartbeat()

    assert conn_info.last_heartbeat > initial_time
    assert conn_info.presence == PresenceStatus.ONLINE

    print("✓ ConnectionInfo heartbeat updates work")


def test_connection_info_presence():
    """Test connection info presence states."""
    websocket = MockWebSocket()
    conn_info = ConnectionInfo(websocket=websocket, user_id=1)

    # Initially online
    assert conn_info.presence == PresenceStatus.ONLINE

    # Mark away
    conn_info.mark_away()
    assert conn_info.presence == PresenceStatus.AWAY

    # Update activity brings back online
    conn_info.update_activity()
    assert conn_info.presence == PresenceStatus.ONLINE

    # Mark offline
    conn_info.mark_offline()
    assert conn_info.presence == PresenceStatus.OFFLINE

    print("✓ ConnectionInfo presence states work")


def test_connection_info_to_dict():
    """Test connection info serialization."""
    websocket = MockWebSocket()
    conn_info = ConnectionInfo(
        websocket=websocket,
        user_id=1,
        agent_type="talent",
        agent_id=10
    )

    data = conn_info.to_dict()

    assert data["user_id"] == 1
    assert data["agent_type"] == "talent"
    assert data["agent_id"] == 10
    assert data["presence"] == "online"
    assert "connection_id" in data
    assert "connected_at" in data

    print("✓ ConnectionInfo to_dict works")


# ==================== Test ConnectionManager ====================

def test_connection_manager_creation():
    """Test creating connection manager."""
    manager = ConnectionManager(
        max_connections_per_user=5,
        heartbeat_timeout=300
    )

    assert manager.max_connections_per_user == 5
    assert manager.heartbeat_timeout == 300

    stats = manager.get_stats()
    assert stats["active_connections"] == 0
    assert stats["active_users"] == 0

    print("✓ ConnectionManager created successfully")


async def test_connection_manager_connect():
    """Test connecting to connection manager."""
    manager = ConnectionManager()
    websocket = MockWebSocket()

    connection_id = await manager.connect(
        websocket=websocket,
        user_id=1,
        agent_type="talent",
        agent_id=10
    )

    assert websocket.accepted
    assert connection_id is not None
    assert manager.is_user_online(1)

    stats = manager.get_stats()
    assert stats["active_connections"] == 1
    assert stats["active_users"] == 1

    print("✓ ConnectionManager connect works")


async def test_connection_manager_disconnect():
    """Test disconnecting from connection manager."""
    manager = ConnectionManager()
    websocket = MockWebSocket()

    connection_id = await manager.connect(websocket=websocket, user_id=1)

    assert manager.is_user_online(1)

    await manager.disconnect(connection_id)

    assert not manager.is_user_online(1)

    stats = manager.get_stats()
    assert stats["active_connections"] == 0
    assert stats["total_disconnections"] == 1

    print("✓ ConnectionManager disconnect works")


async def test_connection_manager_multiple_connections():
    """Test multiple connections for same user."""
    manager = ConnectionManager(max_connections_per_user=3)

    ws1 = MockWebSocket()
    ws2 = MockWebSocket()
    ws3 = MockWebSocket()

    # Connect 3 times for same user
    conn1 = await manager.connect(ws1, user_id=1)
    conn2 = await manager.connect(ws2, user_id=1)
    conn3 = await manager.connect(ws3, user_id=1)

    assert manager.is_user_online(1)

    stats = manager.get_stats()
    assert stats["active_connections"] == 3
    assert stats["active_users"] == 1  # Still just 1 user

    # Try to exceed limit
    ws4 = MockWebSocket()
    try:
        conn4 = await manager.connect(ws4, user_id=1)
        assert False, "Should have raised exception"
    except Exception as e:
        assert "Max connections" in str(e)

    print("✓ ConnectionManager multiple connections work")


async def test_connection_manager_send_to_user():
    """Test sending message to user."""
    manager = ConnectionManager()

    ws1 = MockWebSocket()
    ws2 = MockWebSocket()

    await manager.connect(ws1, user_id=1)
    await manager.connect(ws2, user_id=1)

    # Send to user
    message = {"event": "test", "data": "hello"}
    await manager.send_to_user(1, message)

    # Both connections should receive the message
    assert ws1.get_last_message() == message
    assert ws2.get_last_message() == message

    print("✓ ConnectionManager send_to_user works")


async def test_connection_manager_send_to_agent():
    """Test sending message to agent."""
    manager = ConnectionManager()

    ws1 = MockWebSocket()
    ws2 = MockWebSocket()
    ws3 = MockWebSocket()

    await manager.connect(ws1, user_id=1, agent_type="talent", agent_id=10)
    await manager.connect(ws2, user_id=2, agent_type="talent", agent_id=10)
    await manager.connect(ws3, user_id=3, agent_type="hiring_manager", agent_id=20)

    # Send to talent agent 10
    message = {"event": "test", "data": "hello"}
    await manager.send_to_agent("talent", 10, message)

    # Only talent agent connections should receive
    assert ws1.get_last_message() == message
    assert ws2.get_last_message() == message
    assert ws3.get_last_message() != message  # Different agent

    print("✓ ConnectionManager send_to_agent works")


async def test_connection_manager_broadcast():
    """Test broadcasting to all connections."""
    manager = ConnectionManager()

    ws1 = MockWebSocket()
    ws2 = MockWebSocket()
    ws3 = MockWebSocket()

    await manager.connect(ws1, user_id=1)
    await manager.connect(ws2, user_id=2)
    await manager.connect(ws3, user_id=3)

    # Broadcast
    message = {"event": "broadcast", "data": "everyone"}
    await manager.broadcast_to_all(message)

    # All should receive
    assert ws1.get_last_message() == message
    assert ws2.get_last_message() == message
    assert ws3.get_last_message() == message

    stats = manager.get_stats()
    assert stats["broadcasts"] == 1

    print("✓ ConnectionManager broadcast works")


async def test_connection_manager_presence():
    """Test presence tracking."""
    manager = ConnectionManager()
    websocket = MockWebSocket()

    # User not connected = offline
    assert manager.get_user_presence(999) == PresenceStatus.OFFLINE

    # Connect user
    connection_id = await manager.connect(websocket, user_id=999)

    # Now online
    assert manager.get_user_presence(999) == PresenceStatus.ONLINE
    assert manager.is_user_online(999)

    # Disconnect
    await manager.disconnect(connection_id)

    # Back to offline
    assert manager.get_user_presence(999) == PresenceStatus.OFFLINE
    assert not manager.is_user_online(999)

    print("✓ ConnectionManager presence tracking works")


def test_connection_manager_online_users():
    """Test getting online users list."""
    manager = ConnectionManager()

    # No users online
    assert manager.get_online_users() == []

    print("✓ ConnectionManager online users list works")


# ==================== Test Event Types ====================

def test_connected_event():
    """Test ConnectedEvent creation."""
    event = ConnectedEvent.create(connection_id="conn_123", user_id=1)

    assert event.event == EventType.CONNECTED
    assert event.data["connection_id"] == "conn_123"
    assert event.data["user_id"] == 1

    # Should be serializable
    event_dict = event.dict()
    assert event_dict["event"] == "connected"

    print("✓ ConnectedEvent works")


def test_heartbeat_response():
    """Test HeartbeatResponse creation."""
    response = HeartbeatResponse.create()

    assert response.event == EventType.HEARTBEAT
    assert response.data["status"] == "alive"

    print("✓ HeartbeatResponse works")


def test_new_message_event():
    """Test NewMessageEvent creation."""
    event = NewMessageEvent.create(
        message_id=42,
        thread_id="thread_123",
        sender_agent_type="talent",
        sender_agent_id=10,
        content="Hello!",
        subject="Test",
        message_type="question"
    )

    assert event.event == EventType.MESSAGE_NEW
    assert event.data["message_id"] == 42
    assert event.data["thread_id"] == "thread_123"
    assert event.data["content"] == "Hello!"
    assert event.data["sender"]["agent_type"] == "talent"

    print("✓ NewMessageEvent works")


def test_typing_event():
    """Test TypingEvent creation."""
    # Start typing
    start_event = TypingEvent.create_start(
        thread_id="thread_123",
        user_id=1,
        agent_type="talent",
        agent_id=10
    )

    assert start_event.event == EventType.TYPING_START
    assert start_event.data["thread_id"] == "thread_123"

    # Stop typing
    stop_event = TypingEvent.create_stop(
        thread_id="thread_123",
        user_id=1,
        agent_type="talent",
        agent_id=10
    )

    assert stop_event.event == EventType.TYPING_STOP

    print("✓ TypingEvent works")


def test_new_match_event():
    """Test NewMatchEvent creation."""
    event = NewMatchEvent.create(
        match_id=100,
        job_id=50,
        job_title="Senior Engineer",
        company_name="Tech Corp",
        match_score=0.85,
        matched_skills=["Python", "FastAPI", "SQL"],
        ai_explanation="Great match based on skills"
    )

    assert event.event == EventType.MATCH_NEW
    assert event.data["match_id"] == 100
    assert event.data["match_score"] == 0.85
    assert len(event.data["matched_skills"]) == 3
    assert "action_url" in event.data

    print("✓ NewMatchEvent works")


def test_presence_event():
    """Test PresenceEvent creation."""
    # Online
    online_event = PresenceEvent.create(
        user_id=1,
        presence_status="online",
        agent_type="talent",
        agent_id=10
    )

    assert online_event.event == EventType.PRESENCE_ONLINE
    assert online_event.data["user_id"] == 1
    assert online_event.data["presence"] == "online"

    # Away
    away_event = PresenceEvent.create(
        user_id=1,
        presence_status="away"
    )

    assert away_event.event == EventType.PRESENCE_AWAY

    # Offline
    offline_event = PresenceEvent.create(
        user_id=1,
        presence_status="offline"
    )

    assert offline_event.event == EventType.PRESENCE_OFFLINE

    print("✓ PresenceEvent works")


def test_notification_event():
    """Test NotificationEvent creation."""
    event = NotificationEvent.create(
        notification_id=123,
        title="New Match",
        message="You have a new match!",
        notification_type="match",
        action_url="/matches/100",
        priority="high"
    )

    assert event.event == EventType.NOTIFICATION_NEW
    assert event.data["notification_id"] == 123
    assert event.data["title"] == "New Match"
    assert event.data["priority"] == "high"
    assert event.data["action_url"] == "/matches/100"

    print("✓ NotificationEvent works")


# ==================== Run All Tests ====================

async def run_async_tests():
    """Run all async tests."""
    print("\n3. Testing ConnectionManager (async)...")
    await test_connection_manager_connect()
    await test_connection_manager_disconnect()
    await test_connection_manager_multiple_connections()
    await test_connection_manager_send_to_user()
    await test_connection_manager_send_to_agent()
    await test_connection_manager_broadcast()
    await test_connection_manager_presence()


if __name__ == "__main__":
    print("\n" + "="*70)
    print("WebSocket Infrastructure Tests")
    print("="*70 + "\n")

    # ConnectionInfo tests
    print("1. Testing ConnectionInfo...")
    test_connection_info_creation()
    test_connection_info_heartbeat()
    test_connection_info_presence()
    test_connection_info_to_dict()

    # ConnectionManager sync tests
    print("\n2. Testing ConnectionManager (sync)...")
    test_connection_manager_creation()
    test_connection_manager_online_users()

    # ConnectionManager async tests
    asyncio.run(run_async_tests())

    # Event type tests
    print("\n4. Testing Event Types...")
    test_connected_event()
    test_heartbeat_response()
    test_new_message_event()
    test_typing_event()
    test_new_match_event()
    test_presence_event()
    test_notification_event()

    print("\n" + "="*70)
    print("✅ All WebSocket Tests Passed! (21 tests)")
    print("="*70 + "\n")
