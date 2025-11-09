"""
Realtime Notification Service - Phase 11

Enhanced WebSocket notification broadcasting with real-time delivery.

Wraps and extends the existing NotificationService from Phase 3 with
improved WebSocket event delivery using typed Pydantic models.

Features:
- Instant notification delivery via WebSocket
- Batch notification delivery
- Unread count updates
- Priority notification handling
- Notification interaction tracking (read, clicked, dismissed)
"""

import logging
from typing import List, Dict, Any, Optional
from datetime import datetime

from ..websocket.connection_manager import ConnectionManager, get_connection_manager
from ..websocket.notification_events import (
    NotificationCreatedEvent,
    NotificationReadEvent,
    NotificationDismissedEvent,
    NotificationClickedEvent,
    NotificationBatchEvent,
    NotificationCountUpdatedEvent,
    PriorityNotificationEvent,
    NotificationDeletedEvent,
    AllNotificationsReadEvent,
    create_notification_event_from_model
)
from ..models.notification import Notification, NotificationPriority

logger = logging.getLogger(__name__)


class RealtimeNotificationService:
    """
    Enhanced notification broadcasting service via WebSocket.

    Integrates with Phase 3 NotificationService to provide real-time delivery.
    """

    def __init__(self, connection_manager: Optional[ConnectionManager] = None):
        """
        Initialize Realtime Notification Service.

        Args:
            connection_manager: WebSocket connection manager (default: global instance)
        """
        self.connection_manager = connection_manager or get_connection_manager()

    async def broadcast_notification(
        self,
        notification: Notification,
        priority_override: Optional[str] = None
    ):
        """
        Broadcast a notification to user via WebSocket.

        Args:
            notification: Notification model instance
            priority_override: Override notification priority (for urgent alerts)
        """
        try:
            # Determine if this is a priority notification
            is_priority = (
                priority_override == "urgent" or
                notification.priority == NotificationPriority.URGENT or
                notification.priority == NotificationPriority.HIGH
            )

            if is_priority:
                # Use priority event for urgent notifications
                event = PriorityNotificationEvent.create(
                    notification_id=notification.id,
                    user_id=notification.user_id,
                    notification_type=notification.notification_type.value,
                    title=notification.title,
                    message=notification.message,
                    action_url=notification.action_url,
                    action_text=notification.action_text,
                    sound="alert" if priority_override == "urgent" else "default",
                    vibrate=True
                )
            else:
                # Use standard notification event
                event = create_notification_event_from_model(notification)

            # Send to user's WebSocket connections
            await self.connection_manager.send_to_user(
                user_id=notification.user_id,
                message=event.model_dump() if hasattr(event, 'model_dump') else event.dict()
            )

            logger.debug(
                f"Broadcasted notification {notification.id} to user {notification.user_id} "
                f"(priority={is_priority})"
            )

        except Exception as e:
            logger.error(f"Failed to broadcast notification: {str(e)}")

    async def broadcast_notification_read(
        self,
        notification_id: int,
        user_id: int
    ):
        """
        Broadcast notification read event.

        Used for cross-device synchronization - when user reads a notification
        on one device, mark it read on all other devices.

        Args:
            notification_id: Notification ID that was read
            user_id: User who read the notification
        """
        try:
            event = NotificationReadEvent.create(
                notification_id=notification_id,
                user_id=user_id
            )

            await self.connection_manager.send_to_user(
                user_id=user_id,
                message=event.model_dump() if hasattr(event, 'model_dump') else event.dict()
            )

            logger.debug(f"Broadcasted notification.read for notification {notification_id}")

        except Exception as e:
            logger.error(f"Failed to broadcast notification read: {str(e)}")

    async def broadcast_notification_dismissed(
        self,
        notification_id: int,
        user_id: int
    ):
        """
        Broadcast notification dismissed event.

        Args:
            notification_id: Notification ID that was dismissed
            user_id: User who dismissed the notification
        """
        try:
            event = NotificationDismissedEvent.create(
                notification_id=notification_id,
                user_id=user_id
            )

            await self.connection_manager.send_to_user(
                user_id=user_id,
                message=event.model_dump() if hasattr(event, 'model_dump') else event.dict()
            )

            logger.debug(f"Broadcasted notification.dismissed for notification {notification_id}")

        except Exception as e:
            logger.error(f"Failed to broadcast notification dismissed: {str(e)}")

    async def broadcast_notification_clicked(
        self,
        notification_id: int,
        user_id: int,
        action_url: str
    ):
        """
        Broadcast notification clicked event.

        Tracks user engagement with notifications.

        Args:
            notification_id: Notification ID that was clicked
            user_id: User who clicked the notification
            action_url: URL that was navigated to
        """
        try:
            event = NotificationClickedEvent.create(
                notification_id=notification_id,
                user_id=user_id,
                action_url=action_url
            )

            await self.connection_manager.send_to_user(
                user_id=user_id,
                message=event.model_dump() if hasattr(event, 'model_dump') else event.dict()
            )

            logger.debug(f"Broadcasted notification.clicked for notification {notification_id}")

        except Exception as e:
            logger.error(f"Failed to broadcast notification clicked: {str(e)}")

    async def broadcast_notification_batch(
        self,
        user_id: int,
        notifications: List[Notification]
    ):
        """
        Broadcast multiple notifications at once.

        Used for:
        - Initial load when user connects
        - Daily digest delivery
        - Bulk notification sync

        Args:
            user_id: User receiving the batch
            notifications: List of Notification model instances
        """
        try:
            # Convert notifications to dict format
            notification_dicts = [
                {
                    "id": n.id,
                    "type": n.notification_type.value,
                    "title": n.title,
                    "message": n.message,
                    "priority": n.priority.value,
                    "action_url": n.action_url,
                    "action_text": n.action_text,
                    "created_at": n.created_at.isoformat(),
                    "is_read": n.is_read()
                }
                for n in notifications
            ]

            unread_count = sum(1 for n in notifications if not n.is_read())

            event = NotificationBatchEvent.create(
                user_id=user_id,
                notifications=notification_dicts,
                total_count=len(notifications),
                unread_count=unread_count
            )

            await self.connection_manager.send_to_user(
                user_id=user_id,
                message=event.model_dump() if hasattr(event, 'model_dump') else event.dict()
            )

            logger.info(
                f"Broadcasted notification batch to user {user_id} "
                f"(total={len(notifications)}, unread={unread_count})"
            )

        except Exception as e:
            logger.error(f"Failed to broadcast notification batch: {str(e)}")

    async def broadcast_count_updated(
        self,
        user_id: int,
        unread_count: int,
        total_count: int
    ):
        """
        Broadcast unread count update.

        Used to update badge counts in UI across all devices.

        Args:
            user_id: User whose count changed
            unread_count: New unread count
            total_count: Total notification count
        """
        try:
            event = NotificationCountUpdatedEvent.create(
                user_id=user_id,
                unread_count=unread_count,
                total_count=total_count
            )

            await self.connection_manager.send_to_user(
                user_id=user_id,
                message=event.model_dump() if hasattr(event, 'model_dump') else event.dict()
            )

            logger.debug(
                f"Broadcasted notification.count_updated to user {user_id} "
                f"(unread={unread_count})"
            )

        except Exception as e:
            logger.error(f"Failed to broadcast count update: {str(e)}")

    async def broadcast_notification_deleted(
        self,
        notification_id: int,
        user_id: int
    ):
        """
        Broadcast notification deleted event.

        Args:
            notification_id: Notification ID that was deleted
            user_id: User whose notification was deleted
        """
        try:
            event = NotificationDeletedEvent.create(
                notification_id=notification_id,
                user_id=user_id
            )

            await self.connection_manager.send_to_user(
                user_id=user_id,
                message=event.model_dump() if hasattr(event, 'model_dump') else event.dict()
            )

            logger.debug(f"Broadcasted notification.deleted for notification {notification_id}")

        except Exception as e:
            logger.error(f"Failed to broadcast notification deleted: {str(e)}")

    async def broadcast_all_read(
        self,
        user_id: int,
        count_marked: int
    ):
        """
        Broadcast all notifications read event.

        Args:
            user_id: User who marked all as read
            count_marked: Number of notifications marked as read
        """
        try:
            event = AllNotificationsReadEvent.create(
                user_id=user_id,
                count_marked=count_marked
            )

            await self.connection_manager.send_to_user(
                user_id=user_id,
                message=event.model_dump() if hasattr(event, 'model_dump') else event.dict()
            )

            logger.info(
                f"Broadcasted notification.all_read to user {user_id} "
                f"(count={count_marked})"
            )

        except Exception as e:
            logger.error(f"Failed to broadcast all read: {str(e)}")

    async def send_daily_digest(
        self,
        user_id: int,
        notifications: List[Notification]
    ):
        """
        Send daily notification digest via WebSocket.

        Args:
            user_id: User receiving the digest
            notifications: List of notifications from the past day
        """
        try:
            # Send as batch with special metadata
            await self.broadcast_notification_batch(
                user_id=user_id,
                notifications=notifications
            )

            logger.info(f"Sent daily digest to user {user_id} ({len(notifications)} notifications)")

        except Exception as e:
            logger.error(f"Failed to send daily digest: {str(e)}")

    def is_user_online(self, user_id: int) -> bool:
        """
        Check if user is currently online (has active WebSocket connection).

        Args:
            user_id: User ID to check

        Returns:
            True if user is online
        """
        return self.connection_manager.is_user_online(user_id)

    async def send_test_notification(
        self,
        user_id: int,
        title: str = "Test Notification",
        message: str = "This is a test notification from the system."
    ):
        """
        Send a test notification (for debugging).

        Args:
            user_id: User to send test notification to
            title: Notification title
            message: Notification message
        """
        try:
            event = NotificationCreatedEvent.create(
                notification_id=0,  # Test notification has no ID
                user_id=user_id,
                notification_type="system_test",
                title=title,
                message=message,
                priority="normal"
            )

            await self.connection_manager.send_to_user(
                user_id=user_id,
                message=event.model_dump() if hasattr(event, 'model_dump') else event.dict()
            )

            logger.info(f"Sent test notification to user {user_id}")

        except Exception as e:
            logger.error(f"Failed to send test notification: {str(e)}")


# ==================== Factory Function ====================

def create_realtime_notification_service() -> RealtimeNotificationService:
    """
    Create a realtime notification service instance.

    Returns:
        RealtimeNotificationService instance
    """
    return RealtimeNotificationService()


# ==================== Integration Helpers ====================

async def notify_user(
    user_id: int,
    notification: Notification,
    service: Optional[RealtimeNotificationService] = None
):
    """
    Helper function to notify a user via WebSocket.

    Can be called from anywhere in the codebase.

    Args:
        user_id: User ID to notify
        notification: Notification model instance
        service: Optional service instance (creates new if None)

    Example:
        notification = notification_service.create_notification(...)
        await notify_user(user_id=1, notification=notification)
    """
    if service is None:
        service = create_realtime_notification_service()

    await service.broadcast_notification(notification)


async def update_notification_count(
    user_id: int,
    unread_count: int,
    total_count: int,
    service: Optional[RealtimeNotificationService] = None
):
    """
    Update notification badge count for a user.

    Args:
        user_id: User ID
        unread_count: New unread count
        total_count: Total notification count
        service: Optional service instance
    """
    if service is None:
        service = create_realtime_notification_service()

    await service.broadcast_count_updated(
        user_id=user_id,
        unread_count=unread_count,
        total_count=total_count
    )
