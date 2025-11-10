"""
WebSocket Event Types and Schemas - Phase 3 Week 1.

Defines all WebSocket event types and message schemas for real-time features.

Event Categories:
- System events (heartbeat, connect, disconnect)
- Message events (new message, typing, read)
- Match events (new match, match update)
- Presence events (online, offline, away)
- Notification events (generic notifications)
"""

from enum import Enum
from typing import Optional, Dict, Any, List
from datetime import datetime
from pydantic import BaseModel, Field


class EventType(str, Enum):
    """WebSocket event types."""

    # System events
    HEARTBEAT = "heartbeat"
    CONNECTED = "connected"
    DISCONNECTED = "disconnected"
    ERROR = "error"

    # Message events
    MESSAGE_NEW = "message.new"
    MESSAGE_SENT = "message.sent"
    MESSAGE_DELIVERED = "message.delivered"
    MESSAGE_READ = "message.read"
    TYPING_START = "typing.start"
    TYPING_STOP = "typing.stop"

    # Match events
    MATCH_NEW = "match.new"
    MATCH_UPDATED = "match.updated"
    MATCH_VIEWED = "match.viewed"
    MATCH_INTERESTED = "match.interested"
    MATCH_EXPIRED = "match.expired"

    # Application events
    APPLICATION_NEW = "application.new"
    APPLICATION_UPDATED = "application.updated"
    APPLICATION_SCREENED = "application.screened"

    # Presence events
    PRESENCE_ONLINE = "presence.online"
    PRESENCE_OFFLINE = "presence.offline"
    PRESENCE_AWAY = "presence.away"
    USER_JOINED = "user.joined"
    USER_LEFT = "user.left"

    # Notification events
    NOTIFICATION_NEW = "notification.new"
    NOTIFICATION_READ = "notification.read"


class WebSocketMessage(BaseModel):
    """Base WebSocket message schema."""

    event: EventType = Field(..., description="Event type")
    timestamp: str = Field(default_factory=lambda: datetime.utcnow().isoformat(), description="Event timestamp")
    data: Dict[str, Any] = Field(default_factory=dict, description="Event data")

    class Config:
        use_enum_values = True


# ==================== System Event Schemas ====================

class HeartbeatRequest(BaseModel):
    """Heartbeat request from client."""
    event: str = "heartbeat"
    timestamp: Optional[str] = None


class HeartbeatResponse(WebSocketMessage):
    """Heartbeat response to client."""
    event: EventType = EventType.HEARTBEAT

    @staticmethod
    def create() -> "HeartbeatResponse":
        return HeartbeatResponse(
            event=EventType.HEARTBEAT,
            data={"status": "alive"}
        )


class ConnectedEvent(WebSocketMessage):
    """Connection established event."""
    event: EventType = EventType.CONNECTED

    @staticmethod
    def create(connection_id: str, user_id: int) -> "ConnectedEvent":
        return ConnectedEvent(
            event=EventType.CONNECTED,
            data={
                "connection_id": connection_id,
                "user_id": user_id,
                "message": "WebSocket connected successfully"
            }
        )


class ErrorEvent(WebSocketMessage):
    """Error event."""
    event: EventType = EventType.ERROR

    @staticmethod
    def create(error_message: str, error_code: Optional[str] = None) -> "ErrorEvent":
        return ErrorEvent(
            event=EventType.ERROR,
            data={
                "error": error_message,
                "code": error_code
            }
        )


# ==================== Message Event Schemas ====================

class NewMessageEvent(WebSocketMessage):
    """New message received event."""
    event: EventType = EventType.MESSAGE_NEW

    @staticmethod
    def create(
        message_id: int,
        thread_id: str,
        sender_agent_type: str,
        sender_agent_id: int,
        content: str,
        subject: Optional[str] = None,
        message_type: str = "question",
        context_type: str = "general"
    ) -> "NewMessageEvent":
        return NewMessageEvent(
            event=EventType.MESSAGE_NEW,
            data={
                "message_id": message_id,
                "thread_id": thread_id,
                "sender": {
                    "agent_type": sender_agent_type,
                    "agent_id": sender_agent_id
                },
                "content": content,
                "subject": subject,
                "message_type": message_type,
                "context_type": context_type
            }
        )


class MessageDeliveredEvent(WebSocketMessage):
    """Message delivered confirmation."""
    event: EventType = EventType.MESSAGE_DELIVERED

    @staticmethod
    def create(message_id: int, delivered_at: str) -> "MessageDeliveredEvent":
        return MessageDeliveredEvent(
            event=EventType.MESSAGE_DELIVERED,
            data={
                "message_id": message_id,
                "delivered_at": delivered_at
            }
        )


class MessageReadEvent(WebSocketMessage):
    """Message read event."""
    event: EventType = EventType.MESSAGE_READ

    @staticmethod
    def create(
        message_id: int,
        thread_id: str,
        read_by_user_id: int,
        read_at: str
    ) -> "MessageReadEvent":
        return MessageReadEvent(
            event=EventType.MESSAGE_READ,
            data={
                "message_id": message_id,
                "thread_id": thread_id,
                "read_by_user_id": read_by_user_id,
                "read_at": read_at
            }
        )


class TypingEvent(WebSocketMessage):
    """Typing indicator event."""

    @staticmethod
    def create_start(
        thread_id: str,
        user_id: int,
        agent_type: str,
        agent_id: int
    ) -> "TypingEvent":
        return TypingEvent(
            event=EventType.TYPING_START,
            data={
                "thread_id": thread_id,
                "user_id": user_id,
                "agent_type": agent_type,
                "agent_id": agent_id
            }
        )

    @staticmethod
    def create_stop(
        thread_id: str,
        user_id: int,
        agent_type: str,
        agent_id: int
    ) -> "TypingEvent":
        return TypingEvent(
            event=EventType.TYPING_STOP,
            data={
                "thread_id": thread_id,
                "user_id": user_id,
                "agent_type": agent_type,
                "agent_id": agent_id
            }
        )


# ==================== Match Event Schemas ====================

class NewMatchEvent(WebSocketMessage):
    """New match found event."""
    event: EventType = EventType.MATCH_NEW

    @staticmethod
    def create(
        match_id: int,
        job_id: int,
        job_title: str,
        company_name: str,
        match_score: float,
        matched_skills: List[str],
        ai_explanation: str
    ) -> "NewMatchEvent":
        return NewMatchEvent(
            event=EventType.MATCH_NEW,
            data={
                "match_id": match_id,
                "job_id": job_id,
                "job_title": job_title,
                "company_name": company_name,
                "match_score": match_score,
                "matched_skills": matched_skills,
                "ai_explanation": ai_explanation,
                "action_url": f"/matches/{match_id}"
            }
        )


class MatchUpdatedEvent(WebSocketMessage):
    """Match status updated event."""
    event: EventType = EventType.MATCH_UPDATED

    @staticmethod
    def create(
        match_id: int,
        status: str,
        updated_by: str,
        reason: Optional[str] = None
    ) -> "MatchUpdatedEvent":
        return MatchUpdatedEvent(
            event=EventType.MATCH_UPDATED,
            data={
                "match_id": match_id,
                "status": status,
                "updated_by": updated_by,
                "reason": reason
            }
        )


# ==================== Application Event Schemas ====================

class NewApplicationEvent(WebSocketMessage):
    """New application received event."""
    event: EventType = EventType.APPLICATION_NEW

    @staticmethod
    def create(
        application_id: int,
        job_id: int,
        job_title: str,
        applicant_name: str,
        match_score: Optional[float] = None
    ) -> "NewApplicationEvent":
        return NewApplicationEvent(
            event=EventType.APPLICATION_NEW,
            data={
                "application_id": application_id,
                "job_id": job_id,
                "job_title": job_title,
                "applicant_name": applicant_name,
                "match_score": match_score,
                "action_url": f"/applications/{application_id}"
            }
        )


class ApplicationScreenedEvent(WebSocketMessage):
    """Application AI screening complete event."""
    event: EventType = EventType.APPLICATION_SCREENED

    @staticmethod
    def create(
        application_id: int,
        screening_result: str,
        screening_score: float,
        strengths: List[str],
        concerns: List[str]
    ) -> "ApplicationScreenedEvent":
        return ApplicationScreenedEvent(
            event=EventType.APPLICATION_SCREENED,
            data={
                "application_id": application_id,
                "screening_result": screening_result,
                "screening_score": screening_score,
                "strengths": strengths,
                "concerns": concerns
            }
        )


# ==================== Presence Event Schemas ====================

class PresenceEvent(WebSocketMessage):
    """User presence update event."""

    @staticmethod
    def create(
        user_id: int,
        presence_status: str,
        agent_type: Optional[str] = None,
        agent_id: Optional[int] = None
    ) -> "PresenceEvent":
        event_type = {
            "online": EventType.PRESENCE_ONLINE,
            "offline": EventType.PRESENCE_OFFLINE,
            "away": EventType.PRESENCE_AWAY
        }.get(presence_status, EventType.PRESENCE_ONLINE)

        return PresenceEvent(
            event=event_type,
            data={
                "user_id": user_id,
                "presence": presence_status,
                "agent_type": agent_type,
                "agent_id": agent_id
            }
        )


class UserJoinedEvent(WebSocketMessage):
    """User joined event."""
    event: EventType = EventType.USER_JOINED

    @staticmethod
    def create(user_id: int, agent_type: str, agent_id: int) -> "UserJoinedEvent":
        return UserJoinedEvent(
            event=EventType.USER_JOINED,
            data={
                "user_id": user_id,
                "agent_type": agent_type,
                "agent_id": agent_id
            }
        )


class UserLeftEvent(WebSocketMessage):
    """User left event."""
    event: EventType = EventType.USER_LEFT

    @staticmethod
    def create(user_id: int, agent_type: str, agent_id: int) -> "UserLeftEvent":
        return UserLeftEvent(
            event=EventType.USER_LEFT,
            data={
                "user_id": user_id,
                "agent_type": agent_type,
                "agent_id": agent_id
            }
        )


# ==================== Notification Event Schemas ====================

class NotificationEvent(WebSocketMessage):
    """Generic notification event."""
    event: EventType = EventType.NOTIFICATION_NEW

    @staticmethod
    def create(
        notification_id: int,
        title: str,
        message: str,
        notification_type: str,
        action_url: Optional[str] = None,
        priority: str = "normal"
    ) -> "NotificationEvent":
        return NotificationEvent(
            event=EventType.NOTIFICATION_NEW,
            data={
                "notification_id": notification_id,
                "title": title,
                "message": message,
                "type": notification_type,
                "action_url": action_url,
                "priority": priority
            }
        )


# ==================== Client Request Schemas ====================

class ClientMessage(BaseModel):
    """Message from client to server."""
    action: str = Field(..., description="Action type")
    data: Dict[str, Any] = Field(default_factory=dict, description="Action data")


class SendTypingIndicator(ClientMessage):
    """Client request to send typing indicator."""
    action: str = "typing"
    data: Dict[str, Any] = Field(
        ...,
        description="Typing data with thread_id and status (start/stop)"
    )


class MarkMessageRead(ClientMessage):
    """Client request to mark message as read."""
    action: str = "mark_read"
    data: Dict[str, Any] = Field(
        ...,
        description="Read data with message_id or thread_id"
    )


class UpdatePresence(ClientMessage):
    """Client request to update presence."""
    action: str = "update_presence"
    data: Dict[str, Any] = Field(
        ...,
        description="Presence data with status (online/away/offline)"
    )
