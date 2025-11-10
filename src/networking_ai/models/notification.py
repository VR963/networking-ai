"""
Notification Model - Phase 3 Week 2.

Multi-channel notification system for user engagement.

Notification Types:
- Match notifications (new match found)
- Message notifications (new message received)
- Application notifications (status updates)
- Interview notifications (scheduled, reminder)
- System notifications (account, platform updates)
"""

from datetime import datetime
from enum import Enum
from typing import Dict, Optional

from sqlalchemy import Column, Integer, String, Text, DateTime, ForeignKey, Boolean, Enum as SQLEnum, JSON
from sqlalchemy.orm import relationship

from ..database import Base


class NotificationType(str, Enum):
    """Notification type classification."""
    # Match notifications
    MATCH_NEW = "match_new"
    MATCH_INTERESTED = "match_interested"
    MATCH_EXPIRING = "match_expiring"

    # Message notifications
    MESSAGE_NEW = "message_new"
    MESSAGE_UNREAD = "message_unread"

    # Application notifications
    APPLICATION_RECEIVED = "application_received"
    APPLICATION_REVIEWED = "application_reviewed"
    APPLICATION_SCREENED = "application_screened"
    APPLICATION_ACCEPTED = "application_accepted"
    APPLICATION_REJECTED = "application_rejected"

    # Interview notifications
    INTERVIEW_SCHEDULED = "interview_scheduled"
    INTERVIEW_REMINDER = "interview_reminder"
    INTERVIEW_RESCHEDULED = "interview_rescheduled"
    INTERVIEW_CANCELLED = "interview_cancelled"

    # Job notifications
    JOB_POSTED = "job_posted"
    JOB_EXPIRING = "job_expiring"
    JOB_CLOSED = "job_closed"

    # System notifications
    PROFILE_INCOMPLETE = "profile_incomplete"
    ACCOUNT_UPDATE = "account_update"
    DAILY_DIGEST = "daily_digest"
    WEEKLY_SUMMARY = "weekly_summary"
    PLATFORM_UPDATE = "platform_update"


class NotificationPriority(str, Enum):
    """Notification priority levels."""
    LOW = "low"
    NORMAL = "normal"
    HIGH = "high"
    URGENT = "urgent"


class NotificationChannel(str, Enum):
    """Delivery channels for notifications."""
    IN_APP = "in_app"  # WebSocket + database
    EMAIL = "email"
    SMS = "sms"
    PUSH = "push"  # Mobile push notifications


class NotificationStatus(str, Enum):
    """Notification delivery status."""
    PENDING = "pending"
    SENT = "sent"
    DELIVERED = "delivered"
    READ = "read"
    FAILED = "failed"


class Notification(Base):
    """
    Notification model for multi-channel user notifications.

    Supports in-app, email, SMS, and push notifications.
    """
    __tablename__ = "notifications"
    __table_args__ = {'extend_existing': True}

    # Primary Key
    id = Column(Integer, primary_key=True, index=True)

    # Recipient
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)

    # Notification details
    notification_type = Column(SQLEnum(NotificationType), nullable=False, index=True)
    priority = Column(SQLEnum(NotificationPriority), default=NotificationPriority.NORMAL, nullable=False)

    # Content
    title = Column(String(200), nullable=False)
    message = Column(Text, nullable=False)

    # Actions
    action_url = Column(String(500), nullable=True)  # URL to navigate to
    action_text = Column(String(100), nullable=True)  # Button text (e.g., "View Match")

    # Metadata (JSON)
    extra_data = Column(JSON, nullable=True)  # Additional data (match_id, job_id, etc.)

    # Related entities
    match_id = Column(Integer, ForeignKey("matches.id"), nullable=True)
    message_id = Column(Integer, ForeignKey("agent_messages.id"), nullable=True)
    application_id = Column(Integer, ForeignKey("applications.id"), nullable=True)
    job_id = Column(Integer, ForeignKey("jobs.id"), nullable=True)

    # Delivery channels
    channels = Column(JSON, nullable=False)  # List of channels: ["in_app", "email"]

    # Status tracking
    status = Column(SQLEnum(NotificationStatus), default=NotificationStatus.PENDING, nullable=False, index=True)

    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False, index=True)
    sent_at = Column(DateTime, nullable=True)
    delivered_at = Column(DateTime, nullable=True)
    read_at = Column(DateTime, nullable=True)

    # Expiration
    expires_at = Column(DateTime, nullable=True)  # Auto-delete after this time

    # Delivery tracking
    email_sent = Column(Boolean, default=False, nullable=False)
    email_sent_at = Column(DateTime, nullable=True)
    email_error = Column(Text, nullable=True)

    sms_sent = Column(Boolean, default=False, nullable=False)
    sms_sent_at = Column(DateTime, nullable=True)
    sms_error = Column(Text, nullable=True)

    push_sent = Column(Boolean, default=False, nullable=False)
    push_sent_at = Column(DateTime, nullable=True)
    push_error = Column(Text, nullable=True)

    # Relationships
    user = relationship("User", foreign_keys=[user_id])
    match = relationship("Match", foreign_keys=[match_id])
    application = relationship("Application", foreign_keys=[application_id])
    job = relationship("Job", foreign_keys=[job_id])

    def __repr__(self):
        return f"<Notification {self.id}: {self.notification_type.value} to user {self.user_id}>"

    def mark_sent(self):
        """Mark notification as sent."""
        self.status = NotificationStatus.SENT
        self.sent_at = datetime.utcnow()

    def mark_delivered(self):
        """Mark notification as delivered."""
        self.status = NotificationStatus.DELIVERED
        self.delivered_at = datetime.utcnow()

    def mark_read(self):
        """Mark notification as read."""
        self.status = NotificationStatus.READ
        self.read_at = datetime.utcnow()

    def mark_failed(self):
        """Mark notification as failed."""
        self.status = NotificationStatus.FAILED

    def is_expired(self) -> bool:
        """Check if notification has expired."""
        if not self.expires_at:
            return False
        return datetime.utcnow() > self.expires_at

    def is_read(self) -> bool:
        """Check if notification has been read."""
        return self.status == NotificationStatus.READ

    def mark_email_sent(self, success: bool = True, error: Optional[str] = None):
        """Mark email delivery status."""
        self.email_sent = success
        self.email_sent_at = datetime.utcnow()
        if error:
            self.email_error = error

    def mark_sms_sent(self, success: bool = True, error: Optional[str] = None):
        """Mark SMS delivery status."""
        self.sms_sent = success
        self.sms_sent_at = datetime.utcnow()
        if error:
            self.sms_error = error

    def mark_push_sent(self, success: bool = True, error: Optional[str] = None):
        """Mark push notification delivery status."""
        self.push_sent = success
        self.push_sent_at = datetime.utcnow()
        if error:
            self.push_error = error

    def to_dict(self) -> Dict:
        """Convert to dictionary representation."""
        return {
            "id": self.id,
            "user_id": self.user_id,
            "type": self.notification_type.value,
            "priority": self.priority.value,
            "title": self.title,
            "message": self.message,
            "action_url": self.action_url,
            "action_text": self.action_text,
            "metadata": self.metadata,
            "channels": self.channels,
            "status": self.status.value,
            "created_at": self.created_at.isoformat(),
            "sent_at": self.sent_at.isoformat() if self.sent_at else None,
            "delivered_at": self.delivered_at.isoformat() if self.delivered_at else None,
            "read_at": self.read_at.isoformat() if self.read_at else None,
            "expires_at": self.expires_at.isoformat() if self.expires_at else None,
            "is_read": self.is_read(),
            "is_expired": self.is_expired()
        }


class NotificationPreferences(Base):
    """
    User notification preferences.

    Controls what notifications user receives and through which channels.
    """
    __tablename__ = "notification_preferences"
    __table_args__ = {'extend_existing': True}

    # Primary Key
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, unique=True, index=True)

    # Global settings
    enabled = Column(Boolean, default=True, nullable=False)  # Master switch

    # Channel preferences
    email_enabled = Column(Boolean, default=True, nullable=False)
    sms_enabled = Column(Boolean, default=False, nullable=False)
    push_enabled = Column(Boolean, default=True, nullable=False)

    # Notification type preferences (JSON)
    # Format: {"match_new": {"email": true, "in_app": true, "sms": false}, ...}
    type_preferences = Column(JSON, nullable=True)

    # Frequency settings
    daily_digest_enabled = Column(Boolean, default=True, nullable=False)
    daily_digest_time = Column(String(5), default="09:00", nullable=False)  # HH:MM format

    weekly_summary_enabled = Column(Boolean, default=True, nullable=False)
    weekly_summary_day = Column(String(10), default="monday", nullable=False)  # Day of week

    # Do Not Disturb
    dnd_enabled = Column(Boolean, default=False, nullable=False)
    dnd_start_time = Column(String(5), default="22:00", nullable=True)  # HH:MM
    dnd_end_time = Column(String(5), default="08:00", nullable=True)  # HH:MM

    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    # Relationships
    user = relationship("User", foreign_keys=[user_id])

    def __repr__(self):
        return f"<NotificationPreferences user={self.user_id} email={self.email_enabled}>"

    def is_channel_enabled(self, channel: NotificationChannel) -> bool:
        """Check if a channel is enabled."""
        if not self.enabled:
            return False

        if channel == NotificationChannel.EMAIL:
            return self.email_enabled
        elif channel == NotificationChannel.SMS:
            return self.sms_enabled
        elif channel == NotificationChannel.PUSH:
            return self.push_enabled
        elif channel == NotificationChannel.IN_APP:
            return True  # In-app always enabled

        return False

    def is_type_enabled(self, notification_type: NotificationType, channel: NotificationChannel) -> bool:
        """Check if a specific notification type is enabled for a channel."""
        if not self.is_channel_enabled(channel):
            return False

        if not self.type_preferences:
            return True  # Default: all enabled

        type_prefs = self.type_preferences.get(notification_type.value, {})
        return type_prefs.get(channel.value, True)

    def is_in_dnd(self) -> bool:
        """Check if currently in Do Not Disturb hours."""
        if not self.dnd_enabled:
            return False

        if not self.dnd_start_time or not self.dnd_end_time:
            return False

        from datetime import datetime
        now = datetime.utcnow()
        current_time = now.strftime("%H:%M")

        # Simple comparison (doesn't handle timezone or cross-midnight properly)
        # In production, you'd want proper timezone handling
        return self.dnd_start_time <= current_time or current_time <= self.dnd_end_time

    def to_dict(self) -> Dict:
        """Convert to dictionary representation."""
        return {
            "user_id": self.user_id,
            "enabled": self.enabled,
            "email_enabled": self.email_enabled,
            "sms_enabled": self.sms_enabled,
            "push_enabled": self.push_enabled,
            "type_preferences": self.type_preferences,
            "daily_digest_enabled": self.daily_digest_enabled,
            "daily_digest_time": self.daily_digest_time,
            "weekly_summary_enabled": self.weekly_summary_enabled,
            "weekly_summary_day": self.weekly_summary_day,
            "dnd_enabled": self.dnd_enabled,
            "dnd_start_time": self.dnd_start_time,
            "dnd_end_time": self.dnd_end_time
        }
