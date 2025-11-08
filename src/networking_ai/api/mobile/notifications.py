"""
Mobile Notifications Router.

Endpoints:
- GET / - List notifications
- POST /{notification_id}/read - Mark notification as read
- POST /read-all - Mark all notifications as read
- GET /settings - Get notification preferences
- PATCH /settings - Update notification preferences
"""

from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from sqlalchemy import desc
from datetime import datetime
from typing import Optional, List

from ...database import get_db
from ...models.user import User
from ...models.notification import Notification, NotificationStatus, NotificationPreferences
from .schemas import (
    NotificationResponse,
    NotificationData,
    NotificationListResponse,
    NotificationSettingsResponse,
    NotificationSettingsUpdateRequest,
    NotificationChannelSettings
)
from .responses import create_success_response, create_error_response, ErrorCode
from .dependencies import mobile_auth_required

notifications_router = APIRouter()


@notifications_router.get("/", response_model=dict)
async def list_notifications(
    unread_only: bool = Query(False, description="Show only unread notifications"),
    limit: int = Query(50, ge=1, le=100, description="Number of notifications to return"),
    db: Session = Depends(get_db),
    user: User = Depends(mobile_auth_required)
):
    """
    List user's notifications.

    Can filter to show only unread notifications.
    """
    # Build query
    query = db.query(Notification).filter(Notification.user_id == user.id)

    # Filter by read status
    if unread_only:
        query = query.filter(Notification.status == NotificationStatus.UNREAD)

    # Sort by most recent first
    query = query.order_by(desc(Notification.created_at))

    # Limit results
    query = query.limit(limit)

    # Execute query
    notifications = query.all()

    # Count unread
    unread_count = db.query(Notification).filter(
        Notification.user_id == user.id,
        Notification.status == NotificationStatus.UNREAD
    ).count()

    # Build response
    notification_responses = []
    for notif in notifications:
        # Parse notification data
        data = None
        if notif.metadata:
            data = NotificationData(
                application_id=notif.metadata.get("application_id"),
                job_id=notif.metadata.get("job_id"),
                new_status=notif.metadata.get("new_status")
            )

        notification_responses.append(
            NotificationResponse(
                id=notif.id,
                type=notif.type.value if notif.type else "info",
                title=notif.title,
                message=notif.message,
                data=data,
                is_read=(notif.status == NotificationStatus.READ),
                created_at=notif.created_at
            )
        )

    return create_success_response(
        data={
            "data": [n.model_dump() for n in notification_responses],
            "meta": {
                "unread_count": unread_count
            }
        },
        self_link="/api/v1/mobile/notifications"
    )


@notifications_router.post("/{notification_id}/read", status_code=status.HTTP_204_NO_CONTENT)
async def mark_notification_read(
    notification_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(mobile_auth_required)
):
    """
    Mark notification as read.
    """
    # Find notification
    notification = db.query(Notification).filter(
        Notification.id == notification_id,
        Notification.user_id == user.id
    ).first()

    if not notification:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=create_error_response(
                code=ErrorCode.NOT_FOUND,
                message="Notification not found"
            )
        )

    # Mark as read
    notification.status = NotificationStatus.READ
    notification.read_at = datetime.utcnow()

    db.commit()

    return None  # 204 No Content


@notifications_router.post("/read-all", status_code=status.HTTP_204_NO_CONTENT)
async def mark_all_notifications_read(
    db: Session = Depends(get_db),
    user: User = Depends(mobile_auth_required)
):
    """
    Mark all notifications as read.
    """
    # Update all unread notifications
    unread_notifications = db.query(Notification).filter(
        Notification.user_id == user.id,
        Notification.status == NotificationStatus.UNREAD
    ).all()

    for notification in unread_notifications:
        notification.status = NotificationStatus.READ
        notification.read_at = datetime.utcnow()

    db.commit()

    return None  # 204 No Content


@notifications_router.get("/settings", response_model=dict)
async def get_notification_settings(
    db: Session = Depends(get_db),
    user: User = Depends(mobile_auth_required)
):
    """
    Get notification preferences.

    Returns settings for email and push notifications.
    """
    # Get preferences
    prefs = db.query(NotificationPreferences).filter(
        NotificationPreferences.user_id == user.id
    ).first()

    # Default settings if not exists
    if not prefs:
        email_settings = NotificationChannelSettings(
            application_updates=True,
            interview_reminders=True,
            new_matches=True,
            messages=True
        )
        push_settings = NotificationChannelSettings(
            application_updates=True,
            interview_reminders=True,
            new_matches=True,
            messages=True
        )
    else:
        # Parse from stored preferences
        email_settings = NotificationChannelSettings(
            application_updates=prefs.email_enabled,
            interview_reminders=prefs.email_enabled,
            new_matches=prefs.email_enabled,
            messages=prefs.email_enabled
        )
        push_settings = NotificationChannelSettings(
            application_updates=prefs.push_enabled,
            interview_reminders=prefs.push_enabled,
            new_matches=prefs.push_enabled,
            messages=prefs.push_enabled
        )

    response = NotificationSettingsResponse(
        email=email_settings,
        push=push_settings
    )

    return create_success_response(
        data=response.model_dump(),
        self_link="/api/v1/mobile/notifications/settings"
    )


@notifications_router.patch("/settings", response_model=dict)
async def update_notification_settings(
    request: NotificationSettingsUpdateRequest,
    db: Session = Depends(get_db),
    user: User = Depends(mobile_auth_required)
):
    """
    Update notification preferences.

    Updates email and/or push notification settings.
    """
    # Get or create preferences
    prefs = db.query(NotificationPreferences).filter(
        NotificationPreferences.user_id == user.id
    ).first()

    if not prefs:
        prefs = NotificationPreferences(
            user_id=user.id,
            email_enabled=True,
            push_enabled=True,
            sms_enabled=False,
            created_at=datetime.utcnow()
        )
        db.add(prefs)

    # Update email settings
    if request.email:
        # For now, use a single toggle for all email notifications
        # In production, store individual preferences in JSON field
        prefs.email_enabled = any([
            request.email.application_updates,
            request.email.interview_reminders,
            request.email.new_matches,
            request.email.messages
        ])

    # Update push settings
    if request.push:
        prefs.push_enabled = any([
            request.push.application_updates,
            request.push.interview_reminders,
            request.push.new_matches,
            request.push.messages
        ])

    prefs.updated_at = datetime.utcnow()

    db.commit()
    db.refresh(prefs)

    # Return updated settings
    email_settings = NotificationChannelSettings(
        application_updates=prefs.email_enabled,
        interview_reminders=prefs.email_enabled,
        new_matches=prefs.email_enabled,
        messages=prefs.email_enabled
    )
    push_settings = NotificationChannelSettings(
        application_updates=prefs.push_enabled,
        interview_reminders=prefs.push_enabled,
        new_matches=prefs.push_enabled,
        messages=prefs.push_enabled
    )

    response = NotificationSettingsResponse(
        email=email_settings,
        push=push_settings
    )

    return create_success_response(
        data=response.model_dump(),
        self_link="/api/v1/mobile/notifications/settings"
    )
