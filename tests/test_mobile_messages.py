"""
Comprehensive tests for Mobile Messaging API.

Tests cover:
- Conversation listing
- Message retrieval
- Sending messages
- Auto-read marking
- Message validation
"""

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session
from datetime import datetime

from src.networking_ai.api.main import app
from src.networking_ai.models.user import User
from src.networking_ai.models.message import Conversation, Message, MessageStatus

client = TestClient(app)


@pytest.fixture
def auth_users_with_conversation(db_session):
    """Create two authenticated users with a conversation."""
    # Register user 1
    user1_data = {
        "email": "user1@test.com",
        "password": "SecurePass123!",
        "full_name": "User One",
        "role": "jobseeker",
        "device": {
            "platform": "ios",
            "device_id": "user1_device",
            "push_token": "fcm_token_1"
        }
    }

    response1 = client.post("/api/v1/mobile/auth/register", json=user1_data)
    user1_token = response1.json()["data"]["tokens"]["access_token"]
    user1_id = response1.json()["data"]["user"]["id"]

    # Register user 2
    user2_data = {
        "email": "user2@test.com",
        "password": "SecurePass123!",
        "full_name": "User Two",
        "role": "hiring_manager",
        "device": {
            "platform": "android",
            "device_id": "user2_device",
            "push_token": "fcm_token_2"
        }
    }

    response2 = client.post("/api/v1/mobile/auth/register", json=user2_data)
    user2_token = response2.json()["data"]["tokens"]["access_token"]
    user2_id = response2.json()["data"]["user"]["id"]

    # Create conversation
    conversation = Conversation(
        user1_id=user1_id,
        user2_id=user2_id,
        created_at=datetime.utcnow(),
        updated_at=datetime.utcnow()
    )
    db_session.add(conversation)
    db_session.commit()
    db_session.refresh(conversation)

    # Create messages
    messages = [
        Message(
            conversation_id=conversation.id,
            sender_id=user1_id,
            content="Hello, I'm interested in the position",
            status=MessageStatus.READ,
            created_at=datetime.utcnow()
        ),
        Message(
            conversation_id=conversation.id,
            sender_id=user2_id,
            content="Great! Let's discuss the details",
            status=MessageStatus.SENT,
            created_at=datetime.utcnow()
        )
    ]

    for msg in messages:
        db_session.add(msg)

    db_session.commit()

    return {
        "user1": {
            "auth_header": {"Authorization": f"Bearer {user1_token}"},
            "user_id": user1_id
        },
        "user2": {
            "auth_header": {"Authorization": f"Bearer {user2_token}"},
            "user_id": user2_id
        },
        "conversation": conversation,
        "messages": messages
    }


# ==================== Conversation Listing Tests ====================

def test_list_conversations_success(auth_users_with_conversation):
    """Test successful conversation listing."""
    auth = auth_users_with_conversation["user1"]["auth_header"]

    response = client.get(
        "/api/v1/mobile/messages/conversations",
        headers=auth
    )

    assert response.status_code == 200
    data = response.json()["data"]

    assert "data" in data
    conversations = data["data"]
    assert len(conversations) >= 1

    # Check conversation structure
    conv = conversations[0]
    assert "id" in conv
    assert "participant" in conv
    assert "last_message" in conv
    assert "unread_count" in conv


def test_list_conversations_shows_participant_info(auth_users_with_conversation):
    """Test conversations include participant information."""
    auth = auth_users_with_conversation["user1"]["auth_header"]

    response = client.get(
        "/api/v1/mobile/messages/conversations",
        headers=auth
    )

    assert response.status_code == 200
    conversations = response.json()["data"]["data"]

    conv = conversations[0]
    participant = conv["participant"]

    assert "id" in participant
    assert "name" in participant
    assert "role" in participant
    assert participant["name"] == "User Two"


def test_list_conversations_shows_last_message(auth_users_with_conversation):
    """Test conversations include last message preview."""
    auth = auth_users_with_conversation["user1"]["auth_header"]

    response = client.get(
        "/api/v1/mobile/messages/conversations",
        headers=auth
    )

    assert response.status_code == 200
    conversations = response.json()["data"]["data"]

    conv = conversations[0]
    assert conv["last_message"] is not None

    last_msg = conv["last_message"]
    assert "text" in last_msg
    assert "timestamp" in last_msg
    assert "is_from_me" in last_msg


def test_list_conversations_shows_unread_count(auth_users_with_conversation):
    """Test conversations show correct unread count."""
    auth = auth_users_with_conversation["user1"]["auth_header"]

    response = client.get(
        "/api/v1/mobile/messages/conversations",
        headers=auth
    )

    assert response.status_code == 200
    conversations = response.json()["data"]["data"]

    conv = conversations[0]
    # User 1 should see 1 unread message from User 2
    assert conv["unread_count"] == 1


# ==================== Message Retrieval Tests ====================

def test_get_conversation_messages(auth_users_with_conversation):
    """Test retrieving conversation messages."""
    auth = auth_users_with_conversation["user1"]["auth_header"]
    conversation_id = auth_users_with_conversation["conversation"].id

    response = client.get(
        f"/api/v1/mobile/messages/conversations/{conversation_id}",
        headers=auth
    )

    assert response.status_code == 200
    data = response.json()["data"]

    assert "id" in data
    assert "participant" in data
    assert "messages" in data

    messages = data["messages"]
    assert len(messages) == 2

    # Check message structure
    msg = messages[0]
    assert "id" in msg
    assert "from_user_id" in msg
    assert "text" in msg
    assert "timestamp" in msg
    assert "is_read" in msg


def test_get_conversation_marks_messages_as_read(auth_users_with_conversation, db_session):
    """Test that viewing conversation marks messages as read."""
    auth = auth_users_with_conversation["user1"]["auth_header"]
    conversation_id = auth_users_with_conversation["conversation"].id

    # User 1 views conversation (should mark User 2's message as read)
    response = client.get(
        f"/api/v1/mobile/messages/conversations/{conversation_id}",
        headers=auth
    )

    assert response.status_code == 200

    # Check that unread message was marked as read
    user2_id = auth_users_with_conversation["user2"]["user_id"]
    unread_count = db_session.query(Message).filter(
        Message.conversation_id == conversation_id,
        Message.sender_id == user2_id,
        Message.status != MessageStatus.READ
    ).count()

    assert unread_count == 0


def test_cannot_access_other_users_conversation(auth_users_with_conversation, db_session):
    """Test user cannot access conversation they're not part of."""
    # Create third user
    user3_data = {
        "email": "user3@test.com",
        "password": "SecurePass123!",
        "full_name": "User Three",
        "role": "jobseeker",
        "device": {
            "platform": "ios",
            "device_id": "user3_device",
            "push_token": "fcm_token_3"
        }
    }

    response = client.post("/api/v1/mobile/auth/register", json=user3_data)
    user3_token = response.json()["data"]["tokens"]["access_token"]
    user3_auth = {"Authorization": f"Bearer {user3_token}"}

    # Try to access conversation between user1 and user2
    conversation_id = auth_users_with_conversation["conversation"].id

    response = client.get(
        f"/api/v1/mobile/messages/conversations/{conversation_id}",
        headers=user3_auth
    )

    assert response.status_code == 403


# ==================== Message Sending Tests ====================

def test_send_message_success(auth_users_with_conversation, db_session):
    """Test successfully sending a message."""
    auth = auth_users_with_conversation["user1"]["auth_header"]
    conversation_id = auth_users_with_conversation["conversation"].id

    message_data = {
        "text": "When can we schedule an interview?"
    }

    response = client.post(
        f"/api/v1/mobile/messages/conversations/{conversation_id}/messages",
        headers=auth,
        json=message_data
    )

    assert response.status_code == 201
    data = response.json()["data"]

    assert "id" in data
    assert data["text"] == message_data["text"]
    assert "timestamp" in data

    # Verify message created in database
    message = db_session.query(Message).filter(
        Message.conversation_id == conversation_id,
        Message.content == message_data["text"]
    ).first()

    assert message is not None
    assert message.sender_id == auth_users_with_conversation["user1"]["user_id"]


def test_send_message_to_nonexistent_conversation(auth_users_with_conversation):
    """Test sending message to non-existent conversation fails."""
    auth = auth_users_with_conversation["user1"]["auth_header"]

    message_data = {
        "text": "Hello"
    }

    response = client.post(
        "/api/v1/mobile/messages/conversations/99999/messages",
        headers=auth,
        json=message_data
    )

    assert response.status_code == 404


def test_cannot_send_message_to_other_users_conversation(auth_users_with_conversation):
    """Test cannot send message in conversation user is not part of."""
    # Create third user
    user3_data = {
        "email": "user3msg@test.com",
        "password": "SecurePass123!",
        "full_name": "User Three Msg",
        "role": "jobseeker",
        "device": {
            "platform": "ios",
            "device_id": "user3_device_msg",
            "push_token": "fcm_token_3"
        }
    }

    response = client.post("/api/v1/mobile/auth/register", json=user3_data)
    user3_token = response.json()["data"]["tokens"]["access_token"]
    user3_auth = {"Authorization": f"Bearer {user3_token}"}

    # Try to send message in conversation between user1 and user2
    conversation_id = auth_users_with_conversation["conversation"].id

    message_data = {
        "text": "Trying to intrude"
    }

    response = client.post(
        f"/api/v1/mobile/messages/conversations/{conversation_id}/messages",
        headers=user3_auth,
        json=message_data
    )

    assert response.status_code == 403
