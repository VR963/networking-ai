"""
WebSocket Package - Phase 3 Week 1.

Real-time WebSocket infrastructure for live updates.
"""

from .connection_manager import ConnectionManager, ConnectionInfo, PresenceStatus, get_connection_manager
from .event_types import (
    EventType,
    WebSocketMessage,
    HeartbeatResponse,
    ConnectedEvent,
    ErrorEvent,
    NewMessageEvent,
    TypingEvent,
    NewMatchEvent,
    PresenceEvent,
    NotificationEvent
)

__all__ = [
    "ConnectionManager",
    "ConnectionInfo",
    "PresenceStatus",
    "get_connection_manager",
    "EventType",
    "WebSocketMessage",
    "HeartbeatResponse",
    "ConnectedEvent",
    "ErrorEvent",
    "NewMessageEvent",
    "TypingEvent",
    "NewMatchEvent",
    "PresenceEvent",
    "NotificationEvent"
]
