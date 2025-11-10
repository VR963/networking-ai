"""
Notification WebSocket Events - Phase 11

Real-time notification events for instant delivery and updates.

Event Types:
- notification.new - New notification created
- notification.read - Notification marked as read
- notification.dismissed - Notification dismissed
- notification.clicked - Notification action clicked
- notification.batch - Multiple notifications
- notification.count_updated - Unread count changed
"""

from datetime import datetime
from typing import Dict, Any, List, Optional
from pydantic import BaseModel, Field


# ==================== Base Notification Event ====================

class NotificationEvent(BaseModel):
    """Base class for all notification events."""
    event: str
    timestamp: str = Field(default_factory=lambda: datetime.utcnow().isoformat())
    data: Dict[str, Any]

    class Config:
        frozen = False


# ==================== Notification Created Event ====================

class NotificationCreatedEvent(BaseModel):
    """
    Event fired when a new notification is created and ready to display.

    This is the primary notification delivery mechanism via WebSocket.
    """
    event: str = "notification.new"
    timestamp: str = Field(default_factory=lambda: datetime.utcnow().isoformat())
    data: Dict[str, Any]

    class Config:
        frozen = False

    @classmethod
    def create(
        cls,
        notification_id: int,
        user_id: int,
        notification_type: str,
        title: str,
        message: str,
        priority: str = "normal",
        action_url: Optional[str] = None,
        action_text: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
        expires_at: Optional[str] = None
    ) -> "NotificationCreatedEvent":
        """
        Create a new notification event.

        Args:
            notification_id: Notification database ID
            user_id: Recipient user ID
            notification_type: Type of notification (match_new, message_new, etc.)
            title: Notification title
            message: Notification message content
            priority: Priority level (low, normal, high, urgent)
            action_url: URL to navigate to on click
            action_text: Text for action button
            metadata: Additional notification metadata
            expires_at: ISO timestamp when notification expires

        Returns:
            NotificationCreatedEvent instance
        """
        return cls(data={
            "notification_id": notification_id,
            "user_id": user_id,
            "type": notification_type,
            "title": title,
            "message": message,
            "priority": priority,
            "action_url": action_url,
            "action_text": action_text,
            "metadata": metadata or {},
            "expires_at": expires_at,
            "created_at": datetime.utcnow().isoformat()
        })


# ==================== Notification Read Event ====================

class NotificationReadEvent(BaseModel):
    """Event fired when a notification is marked as read."""
    event: str = "notification.read"
    timestamp: str = Field(default_factory=lambda: datetime.utcnow().isoformat())
    data: Dict[str, Any]

    class Config:
        frozen = False

    @classmethod
    def create(
        cls,
        notification_id: int,
        user_id: int,
        read_at: Optional[str] = None
    ) -> "NotificationReadEvent":
        """
        Create notification read event.

        Args:
            notification_id: Notification ID that was read
            user_id: User who read the notification
            read_at: ISO timestamp when read (default: now)

        Returns:
            NotificationReadEvent instance
        """
        return cls(data={
            "notification_id": notification_id,
            "user_id": user_id,
            "read_at": read_at or datetime.utcnow().isoformat()
        })


# ==================== Notification Dismissed Event ====================

class NotificationDismissedEvent(BaseModel):
    """Event fired when a notification is dismissed without action."""
    event: str = "notification.dismissed"
    timestamp: str = Field(default_factory=lambda: datetime.utcnow().isoformat())
    data: Dict[str, Any]

    class Config:
        frozen = False

    @classmethod
    def create(
        cls,
        notification_id: int,
        user_id: int
    ) -> "NotificationDismissedEvent":
        """
        Create notification dismissed event.

        Args:
            notification_id: Notification ID that was dismissed
            user_id: User who dismissed the notification

        Returns:
            NotificationDismissedEvent instance
        """
        return cls(data={
            "notification_id": notification_id,
            "user_id": user_id,
            "dismissed_at": datetime.utcnow().isoformat()
        })


# ==================== Notification Clicked Event ====================

class NotificationClickedEvent(BaseModel):
    """Event fired when a notification action is clicked."""
    event: str = "notification.clicked"
    timestamp: str = Field(default_factory=lambda: datetime.utcnow().isoformat())
    data: Dict[str, Any]

    class Config:
        frozen = False

    @classmethod
    def create(
        cls,
        notification_id: int,
        user_id: int,
        action_url: str
    ) -> "NotificationClickedEvent":
        """
        Create notification clicked event.

        Args:
            notification_id: Notification ID that was clicked
            user_id: User who clicked the notification
            action_url: URL that was navigated to

        Returns:
            NotificationClickedEvent instance
        """
        return cls(data={
            "notification_id": notification_id,
            "user_id": user_id,
            "action_url": action_url,
            "clicked_at": datetime.utcnow().isoformat()
        })


# ==================== Notification Batch Event ====================

class NotificationBatchEvent(BaseModel):
    """
    Event for delivering multiple notifications at once.

    Used for:
    - Daily digest delivery
    - Initial load of unread notifications
    - Bulk notification sync
    """
    event: str = "notification.batch"
    timestamp: str = Field(default_factory=lambda: datetime.utcnow().isoformat())
    data: Dict[str, Any]

    class Config:
        frozen = False

    @classmethod
    def create(
        cls,
        user_id: int,
        notifications: List[Dict[str, Any]],
        total_count: int,
        unread_count: int
    ) -> "NotificationBatchEvent":
        """
        Create notification batch event.

        Args:
            user_id: User receiving the batch
            notifications: List of notification dictionaries
            total_count: Total number of notifications in batch
            unread_count: Number of unread notifications

        Returns:
            NotificationBatchEvent instance
        """
        return cls(data={
            "user_id": user_id,
            "notifications": notifications,
            "total_count": total_count,
            "unread_count": unread_count,
            "batch_sent_at": datetime.utcnow().isoformat()
        })


# ==================== Notification Count Updated Event ====================

class NotificationCountUpdatedEvent(BaseModel):
    """
    Event fired when unread notification count changes.

    Used to update badge counts in UI.
    """
    event: str = "notification.count_updated"
    timestamp: str = Field(default_factory=lambda: datetime.utcnow().isoformat())
    data: Dict[str, Any]

    class Config:
        frozen = False

    @classmethod
    def create(
        cls,
        user_id: int,
        unread_count: int,
        total_count: int
    ) -> "NotificationCountUpdatedEvent":
        """
        Create count updated event.

        Args:
            user_id: User whose count changed
            unread_count: New unread count
            total_count: Total notifications

        Returns:
            NotificationCountUpdatedEvent instance
        """
        return cls(data={
            "user_id": user_id,
            "unread_count": unread_count,
            "total_count": total_count,
            "updated_at": datetime.utcnow().isoformat()
        })


# ==================== Priority Notification Event ====================

class PriorityNotificationEvent(BaseModel):
    """
    High-priority notification event for urgent alerts.

    Examples:
    - Interview scheduled/cancelled
    - Job offer received
    - Application deadline approaching
    """
    event: str = "notification.priority"
    timestamp: str = Field(default_factory=lambda: datetime.utcnow().isoformat())
    data: Dict[str, Any]

    class Config:
        frozen = False

    @classmethod
    def create(
        cls,
        notification_id: int,
        user_id: int,
        notification_type: str,
        title: str,
        message: str,
        action_url: Optional[str] = None,
        action_text: Optional[str] = None,
        sound: str = "default",
        vibrate: bool = True
    ) -> "PriorityNotificationEvent":
        """
        Create priority notification event.

        Args:
            notification_id: Notification ID
            user_id: Recipient user ID
            notification_type: Type of notification
            title: Notification title
            message: Notification message
            action_url: URL to navigate to
            action_text: Action button text
            sound: Sound to play (default, alert, none)
            vibrate: Whether to vibrate on mobile

        Returns:
            PriorityNotificationEvent instance
        """
        return cls(data={
            "notification_id": notification_id,
            "user_id": user_id,
            "type": notification_type,
            "title": title,
            "message": message,
            "action_url": action_url,
            "action_text": action_text,
            "priority": "urgent",
            "sound": sound,
            "vibrate": vibrate,
            "requires_action": True,
            "created_at": datetime.utcnow().isoformat()
        })


# ==================== Notification Deleted Event ====================

class NotificationDeletedEvent(BaseModel):
    """Event fired when a notification is deleted."""
    event: str = "notification.deleted"
    timestamp: str = Field(default_factory=lambda: datetime.utcnow().isoformat())
    data: Dict[str, Any]

    class Config:
        frozen = False

    @classmethod
    def create(
        cls,
        notification_id: int,
        user_id: int
    ) -> "NotificationDeletedEvent":
        """
        Create notification deleted event.

        Args:
            notification_id: Notification ID that was deleted
            user_id: User whose notification was deleted

        Returns:
            NotificationDeletedEvent instance
        """
        return cls(data={
            "notification_id": notification_id,
            "user_id": user_id,
            "deleted_at": datetime.utcnow().isoformat()
        })


# ==================== All Read Event ====================

class AllNotificationsReadEvent(BaseModel):
    """Event fired when all notifications are marked as read."""
    event: str = "notification.all_read"
    timestamp: str = Field(default_factory=lambda: datetime.utcnow().isoformat())
    data: Dict[str, Any]

    class Config:
        frozen = False

    @classmethod
    def create(
        cls,
        user_id: int,
        count_marked: int
    ) -> "AllNotificationsReadEvent":
        """
        Create all read event.

        Args:
            user_id: User who marked all as read
            count_marked: Number of notifications marked as read

        Returns:
            AllNotificationsReadEvent instance
        """
        return cls(data={
            "user_id": user_id,
            "count_marked": count_marked,
            "marked_at": datetime.utcnow().isoformat()
        })


# ==================== Event Registry ====================

NOTIFICATION_EVENT_TYPES = {
    "notification.new": NotificationCreatedEvent,
    "notification.read": NotificationReadEvent,
    "notification.dismissed": NotificationDismissedEvent,
    "notification.clicked": NotificationClickedEvent,
    "notification.batch": NotificationBatchEvent,
    "notification.count_updated": NotificationCountUpdatedEvent,
    "notification.priority": PriorityNotificationEvent,
    "notification.deleted": NotificationDeletedEvent,
    "notification.all_read": AllNotificationsReadEvent
}


def get_event_class(event_type: str):
    """
    Get event class by event type string.

    Args:
        event_type: Event type (e.g., "notification.new")

    Returns:
        Event class or None if not found
    """
    return NOTIFICATION_EVENT_TYPES.get(event_type)


# ==================== Helper Functions ====================

def create_notification_event_from_model(notification) -> NotificationCreatedEvent:
    """
    Create WebSocket event from Notification database model.

    Args:
        notification: Notification model instance

    Returns:
        NotificationCreatedEvent instance
    """
    return NotificationCreatedEvent.create(
        notification_id=notification.id,
        user_id=notification.user_id,
        notification_type=notification.notification_type.value,
        title=notification.title,
        message=notification.message,
        priority=notification.priority.value,
        action_url=notification.action_url,
        action_text=notification.action_text,
        metadata=notification.extra_data,
        expires_at=notification.expires_at.isoformat() if notification.expires_at else None
    )
