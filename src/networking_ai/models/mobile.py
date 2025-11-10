"""
Mobile-specific database models - Phase 10.

Includes:
- MobileDevice: Device registration for push notifications
- RefreshToken: JWT refresh token management
- SavedJob: User's saved jobs
- PushNotification: Push notification tracking
"""

from datetime import datetime
from enum import Enum
from sqlalchemy import Column, Integer, String, Boolean, DateTime, ForeignKey, Text, JSON
from sqlalchemy.orm import relationship

from ..database import Base


class DevicePlatform(str, Enum):
    """Mobile device platform."""
    IOS = "ios"
    ANDROID = "android"


class PushNotificationStatus(str, Enum):
    """Push notification delivery status."""
    PENDING = "pending"
    SENT = "sent"
    DELIVERED = "delivered"
    FAILED = "failed"
    OPENED = "opened"


class MobileDevice(Base):
    """
    Mobile device registration.

    Tracks user devices for push notifications and analytics.
    """
    __tablename__ = "mobile_devices"
    __table_args__ = {'extend_existing': True}

    # Primary Key
    id = Column(Integer, primary_key=True, index=True)

    # Foreign Keys
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)

    # Device Information
    device_id = Column(String(255), nullable=False, unique=True, index=True)  # Unique device identifier
    platform = Column(String(20), nullable=False)  # 'ios' or 'android'
    push_token = Column(String(500), nullable=True)  # FCM/APNS token for push notifications

    # App Information
    app_version = Column(String(50), nullable=True)  # e.g., "1.0.0"
    os_version = Column(String(50), nullable=True)  # e.g., "iOS 17.0", "Android 14"

    # Status
    is_active = Column(Boolean, default=True, nullable=False)
    last_active = Column(DateTime, nullable=True)

    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    user = relationship("User", back_populates="mobile_devices")
    refresh_tokens = relationship("RefreshToken", back_populates="device", cascade="all, delete-orphan")
    push_notifications = relationship("PushNotification", back_populates="device", cascade="all, delete-orphan")

    def __repr__(self):
        return f"<MobileDevice {self.device_id} ({self.platform})>"

    def to_dict(self):
        """Convert to dictionary."""
        return {
            "id": self.id,
            "device_id": self.device_id,
            "platform": self.platform,
            "app_version": self.app_version,
            "os_version": self.os_version,
            "is_active": self.is_active,
            "last_active": self.last_active.isoformat() if self.last_active else None,
            "created_at": self.created_at.isoformat()
        }


class RefreshToken(Base):
    """
    JWT refresh token.

    Enables token refresh without re-authentication.
    Tokens are device-bound for security.
    """
    __tablename__ = "refresh_tokens"
    __table_args__ = {'extend_existing': True}

    # Primary Key
    id = Column(Integer, primary_key=True, index=True)

    # Foreign Keys
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    device_id = Column(String(255), ForeignKey("mobile_devices.device_id", ondelete="CASCADE"), nullable=True)

    # Token Data
    token_hash = Column(String(255), nullable=False, unique=True, index=True)  # Hashed token
    expires_at = Column(DateTime, nullable=False, index=True)

    # Status
    is_revoked = Column(Boolean, default=False, nullable=False)
    revoked_at = Column(DateTime, nullable=True)

    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    # Relationships
    user = relationship("User", back_populates="refresh_tokens")
    device = relationship("MobileDevice", back_populates="refresh_tokens")

    def __repr__(self):
        return f"<RefreshToken user={self.user_id} device={self.device_id}>"

    def is_expired(self) -> bool:
        """Check if token is expired."""
        return datetime.utcnow() > self.expires_at

    def is_valid(self) -> bool:
        """Check if token is valid (not expired and not revoked)."""
        return not self.is_revoked and not self.is_expired()


class SavedJob(Base):
    """
    User's saved jobs.

    Allows users to bookmark jobs for later review.
    """
    __tablename__ = "saved_jobs"
    __table_args__ = {'extend_existing': True}

    # Primary Key
    id = Column(Integer, primary_key=True, index=True)

    # Foreign Keys
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    job_id = Column(Integer, ForeignKey("jobs.id", ondelete="CASCADE"), nullable=False, index=True)

    # Metadata
    notes = Column(Text, nullable=True)  # User's private notes about the job

    # Timestamps
    saved_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    user = relationship("User", back_populates="saved_jobs")
    job = relationship("Job")

    def __repr__(self):
        return f"<SavedJob user={self.user_id} job={self.job_id}>"

    def to_dict(self):
        """Convert to dictionary."""
        return {
            "id": self.id,
            "job_id": self.job_id,
            "notes": self.notes,
            "saved_at": self.saved_at.isoformat(),
            "updated_at": self.updated_at.isoformat() if self.updated_at else None
        }


class PushNotification(Base):
    """
    Push notification tracking.

    Tracks sent push notifications for analytics and debugging.
    """
    __tablename__ = "push_notifications"
    __table_args__ = {'extend_existing': True}

    # Primary Key
    id = Column(Integer, primary_key=True, index=True)

    # Foreign Keys
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    device_id = Column(String(255), ForeignKey("mobile_devices.device_id", ondelete="SET NULL"), nullable=True)

    # Notification Content
    type = Column(String(50), nullable=False, index=True)  # e.g., "application_update", "new_message"
    title = Column(String(255), nullable=False)
    message = Column(Text, nullable=False)
    data = Column(JSON, nullable=True)  # Additional data payload

    # Delivery Status
    status = Column(String(20), default=PushNotificationStatus.PENDING.value, nullable=False, index=True)
    sent_at = Column(DateTime, nullable=True)
    delivered_at = Column(DateTime, nullable=True)
    opened_at = Column(DateTime, nullable=True)
    error_message = Column(Text, nullable=True)

    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False, index=True)

    # Relationships
    user = relationship("User", back_populates="push_notifications")
    device = relationship("MobileDevice", back_populates="push_notifications")

    def __repr__(self):
        return f"<PushNotification {self.type} to user={self.user_id}>"

    def to_dict(self):
        """Convert to dictionary."""
        return {
            "id": self.id,
            "type": self.type,
            "title": self.title,
            "message": self.message,
            "data": self.data,
            "status": self.status,
            "sent_at": self.sent_at.isoformat() if self.sent_at else None,
            "delivered_at": self.delivered_at.isoformat() if self.delivered_at else None,
            "opened_at": self.opened_at.isoformat() if self.opened_at else None,
            "created_at": self.created_at.isoformat()
        }


# Add unique constraint for saved_jobs (user_id, job_id)
from sqlalchemy import UniqueConstraint
SavedJob.__table_args__ = (
    UniqueConstraint('user_id', 'job_id', name='uq_user_saved_job'),
    {'extend_existing': True}
)
