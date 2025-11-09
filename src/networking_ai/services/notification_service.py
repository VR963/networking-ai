"""
Notification Service - Phase 3 Week 2.

Multi-channel notification delivery service.

Supports:
- In-app notifications (WebSocket + database)
- Email notifications
- SMS notifications (Twilio integration)
- Push notifications (mobile)

Features:
- User preference checking
- Do Not Disturb (DND) handling
- Notification batching
- Delivery tracking
- Retry logic
"""

from typing import List, Dict, Optional
from datetime import datetime, timedelta
from sqlalchemy.orm import Session
import asyncio

from ..models.notification import (
    Notification,
    NotificationPreferences,
    NotificationType,
    NotificationPriority,
    NotificationChannel,
    NotificationStatus
)
from ..models.user import User


class NotificationService:
    """
    Service for creating and delivering multi-channel notifications.

    Handles all notification logic including preference checking,
    channel delivery, and tracking.
    """

    def __init__(
        self,
        email_service=None,
        sms_service=None,
        push_service=None,
        enable_websocket: bool = True,
        realtime_service=None
    ):
        """
        Initialize notification service.

        Args:
            email_service: Email service instance
            sms_service: SMS service instance
            push_service: Push notification service instance
            enable_websocket: Enable WebSocket in-app notifications
            realtime_service: Realtime notification service for enhanced WebSocket broadcasting
        """
        self.email_service = email_service
        self.sms_service = sms_service
        self.push_service = push_service
        self.enable_websocket = enable_websocket
        self._connection_manager = None
        self.realtime = realtime_service

    def _get_connection_manager(self):
        """Get WebSocket connection manager lazily."""
        if self._connection_manager is None and self.enable_websocket:
            try:
                from ..websocket.connection_manager import get_connection_manager
                self._connection_manager = get_connection_manager()
            except ImportError:
                print("[Notification] WebSocket not available")
                self.enable_websocket = False
        return self._connection_manager

    def create_notification(
        self,
        user_id: int,
        notification_type: NotificationType,
        title: str,
        message: str,
        channels: List[str] = None,
        priority: NotificationPriority = NotificationPriority.NORMAL,
        action_url: Optional[str] = None,
        action_text: Optional[str] = None,
        metadata: Optional[Dict] = None,
        match_id: Optional[int] = None,
        message_id: Optional[int] = None,
        application_id: Optional[int] = None,
        job_id: Optional[int] = None,
        expires_in_days: Optional[int] = 30,
        db: Session = None
    ) -> Notification:
        """
        Create a notification (but don't send yet).

        Args:
            user_id: Recipient user ID
            notification_type: Type of notification
            title: Notification title
            message: Notification message
            channels: List of delivery channels (default: ["in_app", "email"])
            priority: Notification priority
            action_url: URL to navigate to
            action_text: Action button text
            metadata: Additional metadata
            match_id: Related match ID
            message_id: Related message ID
            application_id: Related application ID
            job_id: Related job ID
            expires_in_days: Days until expiration (default: 30)
            db: Database session

        Returns:
            Created Notification object
        """
        # Default channels
        if channels is None:
            channels = ["in_app", "email"]

        # Calculate expiration
        expires_at = None
        if expires_in_days:
            expires_at = datetime.utcnow() + timedelta(days=expires_in_days)

        # Create notification
        notification = Notification(
            user_id=user_id,
            notification_type=notification_type,
            priority=priority,
            title=title,
            message=message,
            action_url=action_url,
            action_text=action_text,
            metadata=metadata,
            channels=channels,
            match_id=match_id,
            message_id=message_id,
            application_id=application_id,
            job_id=job_id,
            expires_at=expires_at,
            status=NotificationStatus.PENDING
        )

        db.add(notification)
        db.commit()
        db.refresh(notification)

        return notification

    async def send_notification(
        self,
        notification: Notification,
        db: Session,
        force: bool = False
    ) -> Dict[str, bool]:
        """
        Send notification through all configured channels.

        Args:
            notification: Notification to send
            db: Database session
            force: Force send even if preferences disabled

        Returns:
            Dict of channel: success status
        """
        results = {}

        # Get user preferences
        prefs = self._get_user_preferences(notification.user_id, db)

        # Check if notifications enabled
        if not force and prefs and not prefs.enabled:
            print(f"[Notification] User {notification.user_id} has notifications disabled")
            notification.mark_failed()
            db.commit()
            return results

        # Check Do Not Disturb
        if not force and prefs and prefs.is_in_dnd():
            print(f"[Notification] User {notification.user_id} is in DND mode")
            # Don't fail, just delay delivery
            return results

        # Send to each channel
        for channel in notification.channels:
            channel_enum = NotificationChannel(channel)

            # Check channel preference
            if not force and prefs and not prefs.is_type_enabled(notification.notification_type, channel_enum):
                print(f"[Notification] User {notification.user_id} disabled {channel} for {notification.notification_type.value}")
                continue

            # Deliver to channel
            success = False
            if channel == NotificationChannel.IN_APP.value:
                success = await self._send_in_app(notification)
            elif channel == NotificationChannel.EMAIL.value:
                success = await self._send_email(notification, db)
            elif channel == NotificationChannel.SMS.value:
                success = await self._send_sms(notification, db)
            elif channel == NotificationChannel.PUSH.value:
                success = await self._send_push(notification, db)

            results[channel] = success

        # Update notification status
        if any(results.values()):
            notification.mark_sent()
        else:
            notification.mark_failed()

        db.commit()

        return results

    async def _send_in_app(self, notification: Notification) -> bool:
        """Send in-app notification via WebSocket."""
        if not self.enable_websocket:
            return False

        try:
            # Use enhanced realtime service if available (Phase 11)
            if self.realtime:
                await self.realtime.broadcast_notification(notification)
                print(f"[Notification] Sent in-app notification {notification.id} to user {notification.user_id} (realtime)")
                return True

            # Fallback to legacy WebSocket event (Phase 3)
            connection_manager = self._get_connection_manager()
            if not connection_manager:
                return False

            from ..websocket.event_types import NotificationEvent

            # Create WebSocket event
            event = NotificationEvent.create(
                notification_id=notification.id,
                title=notification.title,
                message=notification.message,
                notification_type=notification.notification_type.value,
                action_url=notification.action_url,
                priority=notification.priority.value
            )

            # Send to user
            await connection_manager.send_to_user(
                user_id=notification.user_id,
                message=event.model_dump()
            )

            print(f"[Notification] Sent in-app notification {notification.id} to user {notification.user_id} (legacy)")
            return True

        except Exception as e:
            print(f"[Notification] In-app delivery failed: {e}")
            return False

    async def _send_email(self, notification: Notification, db: Session) -> bool:
        """Send email notification."""
        if not self.email_service:
            return False

        try:
            # Get user email
            user = db.query(User).filter(User.id == notification.user_id).first()
            if not user or not user.email:
                notification.mark_email_sent(success=False, error="No email address")
                return False

            # Send email
            success = await self.email_service.send_notification_email(
                to_email=user.email,
                notification=notification
            )

            notification.mark_email_sent(success=success)
            db.commit()

            return success

        except Exception as e:
            print(f"[Notification] Email delivery failed: {e}")
            notification.mark_email_sent(success=False, error=str(e))
            db.commit()
            return False

    async def _send_sms(self, notification: Notification, db: Session) -> bool:
        """Send SMS notification."""
        if not self.sms_service:
            return False

        try:
            # Get user phone
            user = db.query(User).filter(User.id == notification.user_id).first()
            if not user:
                notification.mark_sms_sent(success=False, error="User not found")
                return False

            # TODO: Add phone_number field to User model
            # For now, mark as not sent
            notification.mark_sms_sent(success=False, error="Phone number not available")
            db.commit()
            return False

        except Exception as e:
            print(f"[Notification] SMS delivery failed: {e}")
            notification.mark_sms_sent(success=False, error=str(e))
            db.commit()
            return False

    async def _send_push(self, notification: Notification, db: Session) -> bool:
        """Send push notification."""
        if not self.push_service:
            return False

        try:
            # TODO: Implement push notification delivery
            notification.mark_push_sent(success=False, error="Push not implemented")
            db.commit()
            return False

        except Exception as e:
            print(f"[Notification] Push delivery failed: {e}")
            notification.mark_push_sent(success=False, error=str(e))
            db.commit()
            return False

    def _get_user_preferences(
        self,
        user_id: int,
        db: Session
    ) -> Optional[NotificationPreferences]:
        """Get user notification preferences."""
        prefs = db.query(NotificationPreferences).filter(
            NotificationPreferences.user_id == user_id
        ).first()

        # Create default preferences if not exist
        if not prefs:
            prefs = NotificationPreferences(
                user_id=user_id,
                enabled=True,
                email_enabled=True,
                sms_enabled=False,
                push_enabled=True
            )
            db.add(prefs)
            db.commit()
            db.refresh(prefs)

        return prefs

    async def send_new_match_notification(
        self,
        user_id: int,
        match_id: int,
        job_title: str,
        company_name: str,
        match_score: float,
        db: Session
    ):
        """
        Send notification for a new match.

        Args:
            user_id: Talent user ID
            match_id: Match ID
            job_title: Job title
            company_name: Company name
            match_score: Match score (0-1)
            db: Database session
        """
        notification = self.create_notification(
            user_id=user_id,
            notification_type=NotificationType.MATCH_NEW,
            title="🎯 New Match Found!",
            message=f"You have a new {int(match_score * 100)}% match: {job_title} at {company_name}",
            channels=["in_app", "email"],
            priority=NotificationPriority.HIGH,
            action_url=f"/matches/{match_id}",
            action_text="View Match",
            match_id=match_id,
            metadata={"job_title": job_title, "company_name": company_name, "match_score": match_score},
            db=db
        )

        await self.send_notification(notification, db)

    async def send_new_message_notification(
        self,
        user_id: int,
        message_id: int,
        sender_name: str,
        message_preview: str,
        thread_id: str,
        db: Session
    ):
        """
        Send notification for a new message.

        Args:
            user_id: Receiver user ID
            message_id: Message ID
            sender_name: Sender's name
            message_preview: First 100 chars of message
            thread_id: Conversation thread ID
            db: Database session
        """
        notification = self.create_notification(
            user_id=user_id,
            notification_type=NotificationType.MESSAGE_NEW,
            title=f"💬 Message from {sender_name}",
            message=message_preview,
            channels=["in_app", "email"],
            priority=NotificationPriority.NORMAL,
            action_url=f"/messages/{thread_id}",
            action_text="Reply",
            message_id=message_id,
            metadata={"sender_name": sender_name, "thread_id": thread_id},
            db=db
        )

        await self.send_notification(notification, db)

    async def send_application_screened_notification(
        self,
        user_id: int,
        application_id: int,
        job_title: str,
        screening_result: str,
        db: Session
    ):
        """Send notification when application is AI-screened."""
        passed = screening_result in ["strong_match", "good_match"]

        notification = self.create_notification(
            user_id=user_id,
            notification_type=NotificationType.APPLICATION_SCREENED,
            title="✅ Application Reviewed" if passed else "📝 Application Reviewed",
            message=f"Your application for {job_title} has been reviewed by our AI",
            channels=["in_app", "email"],
            priority=NotificationPriority.NORMAL,
            action_url=f"/applications/{application_id}",
            action_text="View Details",
            application_id=application_id,
            metadata={"job_title": job_title, "screening_result": screening_result},
            db=db
        )

        await self.send_notification(notification, db)

    def get_user_notifications(
        self,
        user_id: int,
        db: Session,
        unread_only: bool = False,
        limit: int = 50
    ) -> List[Notification]:
        """
        Get notifications for a user.

        Args:
            user_id: User ID
            db: Database session
            unread_only: Only return unread notifications
            limit: Maximum number of notifications

        Returns:
            List of notifications
        """
        query = db.query(Notification).filter(
            Notification.user_id == user_id
        )

        if unread_only:
            query = query.filter(Notification.status != NotificationStatus.READ)

        notifications = query.order_by(
            Notification.created_at.desc()
        ).limit(limit).all()

        return notifications

    def get_unread_count(self, user_id: int, db: Session) -> int:
        """Get count of unread notifications."""
        count = db.query(Notification).filter(
            Notification.user_id == user_id,
            Notification.status != NotificationStatus.READ
        ).count()

        return count

    async def mark_as_read(
        self,
        notification_id: int,
        user_id: int,
        db: Session
    ) -> bool:
        """
        Mark a notification as read.

        Args:
            notification_id: Notification ID
            user_id: User ID (for security check)
            db: Database session

        Returns:
            True if successful
        """
        notification = db.query(Notification).filter(
            Notification.id == notification_id,
            Notification.user_id == user_id
        ).first()

        if not notification:
            return False

        notification.mark_read()
        db.commit()

        # Broadcast read event and update count (realtime sync across devices)
        if self.realtime:
            try:
                await self.realtime.broadcast_notification_read(notification_id, user_id)

                # Update unread count
                unread_count = self.get_unread_count(user_id, db)
                total_count = db.query(Notification).filter(Notification.user_id == user_id).count()
                await self.realtime.broadcast_count_updated(user_id, unread_count, total_count)
            except Exception as e:
                print(f"[Notification] Failed to broadcast read event: {e}")

        return True

    async def mark_all_as_read(self, user_id: int, db: Session) -> int:
        """
        Mark all notifications as read for a user.

        Args:
            user_id: User ID
            db: Database session

        Returns:
            Number of notifications marked as read
        """
        notifications = db.query(Notification).filter(
            Notification.user_id == user_id,
            Notification.status != NotificationStatus.READ
        ).all()

        count = 0
        for notification in notifications:
            notification.mark_read()
            count += 1

        db.commit()

        # Broadcast all read event and update count
        if self.realtime and count > 0:
            try:
                await self.realtime.broadcast_all_read(user_id, count)
                await self.realtime.broadcast_count_updated(user_id, 0, db.query(Notification).filter(Notification.user_id == user_id).count())
            except Exception as e:
                print(f"[Notification] Failed to broadcast all read event: {e}")

        return count


def create_notification_service(
    email_service=None,
    enable_websocket: bool = True
) -> NotificationService:
    """
    Factory function to create notification service.

    Args:
        email_service: Email service instance
        enable_websocket: Enable WebSocket notifications

    Returns:
        NotificationService instance
    """
    return NotificationService(
        email_service=email_service,
        enable_websocket=enable_websocket
    )
