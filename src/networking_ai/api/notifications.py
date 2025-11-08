"""
Notifications API - Phase 3 Week 2.

REST API endpoints for notification management.

Endpoints:
- GET /notifications - Get user's notifications
- GET /notifications/unread-count - Get unread count
- POST /notifications/{id}/read - Mark as read
- POST /notifications/read-all - Mark all as read
- GET /notifications/preferences - Get user preferences
- PUT /notifications/preferences - Update preferences
- POST /notifications/test - Send test notification
"""

from typing import Optional, List
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session
from pydantic import BaseModel, Field

from ..database import get_db
from ..models.user import User
from ..models.notification import (
    Notification,
    NotificationPreferences,
    NotificationType,
    NotificationPriority,
    NotificationStatus
)
from ..services.notification_service import create_notification_service
from ..services.email_service import create_email_service
from ..api.auth import get_current_active_user


router = APIRouter(prefix="/notifications", tags=["Notifications"])


# ==================== Request/Response Models ====================

class NotificationResponse(BaseModel):
    """Notification response model."""
    id: int
    type: str
    priority: str
    title: str
    message: str
    action_url: Optional[str]
    action_text: Optional[str]
    status: str
    created_at: str
    read_at: Optional[str]
    is_read: bool

    class Config:
        from_attributes = True


class PreferencesResponse(BaseModel):
    """Notification preferences response."""
    user_id: int
    enabled: bool
    email_enabled: bool
    sms_enabled: bool
    push_enabled: bool
    daily_digest_enabled: bool
    daily_digest_time: str
    weekly_summary_enabled: bool
    weekly_summary_day: str
    dnd_enabled: bool
    dnd_start_time: Optional[str]
    dnd_end_time: Optional[str]

    class Config:
        from_attributes = True


class UpdatePreferencesRequest(BaseModel):
    """Update preferences request."""
    enabled: Optional[bool] = None
    email_enabled: Optional[bool] = None
    sms_enabled: Optional[bool] = None
    push_enabled: Optional[bool] = None
    daily_digest_enabled: Optional[bool] = None
    daily_digest_time: Optional[str] = None
    weekly_summary_enabled: Optional[bool] = None
    weekly_summary_day: Optional[str] = None
    dnd_enabled: Optional[bool] = None
    dnd_start_time: Optional[str] = None
    dnd_end_time: Optional[str] = None

    class Config:
        json_schema_extra = {
            "example": {
                "enabled": True,
                "email_enabled": True,
                "daily_digest_enabled": True,
                "daily_digest_time": "09:00",
                "dnd_enabled": True,
                "dnd_start_time": "22:00",
                "dnd_end_time": "08:00"
            }
        }


class TestNotificationRequest(BaseModel):
    """Test notification request."""
    notification_type: str = Field(default="match_new", description="Type of notification to send")
    title: str = Field(default="Test Notification", description="Notification title")
    message: str = Field(default="This is a test notification", description="Notification message")
    channels: List[str] = Field(default=["in_app", "email"], description="Channels to test")


# ==================== API Endpoints ====================

@router.get("", response_model=List[NotificationResponse])
async def get_notifications(
    unread_only: bool = Query(False, description="Only return unread notifications"),
    limit: int = Query(50, ge=1, le=100, description="Maximum number of notifications"),
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """
    Get notifications for current user.

    Args:
        unread_only: Only return unread notifications
        limit: Maximum number of notifications

    Returns:
        List of notifications
    """
    notification_service = create_notification_service()

    notifications = notification_service.get_user_notifications(
        user_id=current_user.id,
        db=db,
        unread_only=unread_only,
        limit=limit
    )

    return [
        NotificationResponse(
            id=n.id,
            type=n.notification_type.value,
            priority=n.priority.value,
            title=n.title,
            message=n.message,
            action_url=n.action_url,
            action_text=n.action_text,
            status=n.status.value,
            created_at=n.created_at.isoformat(),
            read_at=n.read_at.isoformat() if n.read_at else None,
            is_read=n.is_read()
        )
        for n in notifications
    ]


@router.get("/unread-count")
async def get_unread_count(
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """
    Get count of unread notifications.

    Returns:
        {"unread_count": int}
    """
    notification_service = create_notification_service()

    count = notification_service.get_unread_count(
        user_id=current_user.id,
        db=db
    )

    return {"unread_count": count}


@router.post("/{notification_id}/read")
async def mark_notification_as_read(
    notification_id: int,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """
    Mark a specific notification as read.

    Args:
        notification_id: Notification ID

    Returns:
        Success status
    """
    notification_service = create_notification_service()

    success = notification_service.mark_as_read(
        notification_id=notification_id,
        user_id=current_user.id,
        db=db
    )

    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Notification not found"
        )

    return {"status": "success", "notification_id": notification_id}


@router.post("/read-all")
async def mark_all_as_read(
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """
    Mark all notifications as read for current user.

    Returns:
        Number of notifications marked as read
    """
    notification_service = create_notification_service()

    count = notification_service.mark_all_as_read(
        user_id=current_user.id,
        db=db
    )

    return {
        "status": "success",
        "marked_read": count
    }


@router.get("/preferences", response_model=PreferencesResponse)
async def get_notification_preferences(
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """
    Get notification preferences for current user.

    Returns:
        User's notification preferences
    """
    prefs = db.query(NotificationPreferences).filter(
        NotificationPreferences.user_id == current_user.id
    ).first()

    # Create default if not exist
    if not prefs:
        prefs = NotificationPreferences(
            user_id=current_user.id,
            enabled=True,
            email_enabled=True,
            sms_enabled=False,
            push_enabled=True
        )
        db.add(prefs)
        db.commit()
        db.refresh(prefs)

    return PreferencesResponse(
        user_id=prefs.user_id,
        enabled=prefs.enabled,
        email_enabled=prefs.email_enabled,
        sms_enabled=prefs.sms_enabled,
        push_enabled=prefs.push_enabled,
        daily_digest_enabled=prefs.daily_digest_enabled,
        daily_digest_time=prefs.daily_digest_time,
        weekly_summary_enabled=prefs.weekly_summary_enabled,
        weekly_summary_day=prefs.weekly_summary_day,
        dnd_enabled=prefs.dnd_enabled,
        dnd_start_time=prefs.dnd_start_time,
        dnd_end_time=prefs.dnd_end_time
    )


@router.put("/preferences", response_model=PreferencesResponse)
async def update_notification_preferences(
    request: UpdatePreferencesRequest,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """
    Update notification preferences for current user.

    Args:
        request: Preferences to update

    Returns:
        Updated preferences
    """
    prefs = db.query(NotificationPreferences).filter(
        NotificationPreferences.user_id == current_user.id
    ).first()

    # Create if not exist
    if not prefs:
        prefs = NotificationPreferences(user_id=current_user.id)
        db.add(prefs)

    # Update fields
    update_data = request.dict(exclude_unset=True)
    for field, value in update_data.items():
        setattr(prefs, field, value)

    db.commit()
    db.refresh(prefs)

    return PreferencesResponse(
        user_id=prefs.user_id,
        enabled=prefs.enabled,
        email_enabled=prefs.email_enabled,
        sms_enabled=prefs.sms_enabled,
        push_enabled=prefs.push_enabled,
        daily_digest_enabled=prefs.daily_digest_enabled,
        daily_digest_time=prefs.daily_digest_time,
        weekly_summary_enabled=prefs.weekly_summary_enabled,
        weekly_summary_day=prefs.weekly_summary_day,
        dnd_enabled=prefs.dnd_enabled,
        dnd_start_time=prefs.dnd_start_time,
        dnd_end_time=prefs.dnd_end_time
    )


@router.post("/test")
async def send_test_notification(
    request: TestNotificationRequest,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """
    Send a test notification (for testing/debugging).

    Args:
        request: Test notification parameters

    Returns:
        Delivery status
    """
    # Create notification service with email service
    email_service = create_email_service()
    notification_service = create_notification_service(
        email_service=email_service,
        enable_websocket=True
    )

    # Create notification
    notification = notification_service.create_notification(
        user_id=current_user.id,
        notification_type=NotificationType(request.notification_type),
        title=request.title,
        message=request.message,
        channels=request.channels,
        priority=NotificationPriority.NORMAL,
        action_url="/dashboard",
        action_text="View Dashboard",
        db=db
    )

    # Send notification
    import asyncio
    results = await notification_service.send_notification(
        notification=notification,
        db=db,
        force=True  # Force send even if disabled
    )

    return {
        "status": "sent",
        "notification_id": notification.id,
        "delivery_results": results
    }
