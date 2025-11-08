"""
Integration API Endpoints - Phase 7.

REST API for external service integrations.
"""

from typing import List, Optional
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from pydantic import BaseModel, Field

from ..database import get_db
from ..models.integrations import (
    Integration,
    CalendarEvent,
    VideoMeeting,
    ATSSync,
    CommunicationLog,
    BackgroundCheck,
    IntegrationType,
    IntegrationProvider,
    IntegrationStatus
)
from ..services.integration_service import (
    IntegrationService,
    create_integration_service
)


# ==================== Request/Response Models ====================

class IntegrationCreate(BaseModel):
    """Create integration request."""
    integration_type: IntegrationType
    provider: IntegrationProvider
    integration_name: str
    company_id: Optional[int] = None
    access_token: Optional[str] = None
    refresh_token: Optional[str] = None
    token_expires_at: Optional[datetime] = None
    config: Optional[dict] = {}


class IntegrationResponse(BaseModel):
    """Integration response."""
    id: int
    integration_type: IntegrationType
    provider: IntegrationProvider
    integration_name: str
    status: IntegrationStatus
    is_active: bool
    last_sync_at: Optional[datetime] = None
    created_at: datetime

    class Config:
        from_attributes = True


class TokenRefresh(BaseModel):
    """Token refresh request."""
    access_token: str
    refresh_token: Optional[str] = None
    expires_at: Optional[datetime] = None


class CalendarEventCreate(BaseModel):
    """Create calendar event request."""
    title: str
    start_time: datetime
    end_time: datetime
    description: Optional[str] = None
    location: Optional[str] = None
    attendees: Optional[List[str]] = []


class CalendarEventResponse(BaseModel):
    """Calendar event response."""
    id: int
    title: str
    description: Optional[str] = None
    location: Optional[str] = None
    start_time: datetime
    end_time: datetime
    attendees: List[str]
    status: str
    created_at: datetime

    class Config:
        from_attributes = True


class VideoMeetingCreate(BaseModel):
    """Create video meeting request."""
    meeting_title: str
    scheduled_start: datetime
    duration_minutes: int
    interview_id: Optional[int] = None
    participants: Optional[List[str]] = []


class VideoMeetingResponse(BaseModel):
    """Video meeting response."""
    id: int
    meeting_title: str
    meeting_url: str
    join_url: str
    scheduled_start: datetime
    scheduled_end: datetime
    duration_minutes: int
    status: str
    host_email: str
    created_at: datetime

    class Config:
        from_attributes = True


class EmailSend(BaseModel):
    """Send email request."""
    recipient_email: str
    subject: str
    body: str
    sender_email: Optional[str] = None
    template_id: Optional[str] = None


class SMSSend(BaseModel):
    """Send SMS request."""
    recipient_phone: str
    body: str


class CommunicationResponse(BaseModel):
    """Communication log response."""
    id: int
    communication_type: str
    provider: IntegrationProvider
    recipient_email: Optional[str] = None
    recipient_phone: Optional[str] = None
    subject: Optional[str] = None
    status: str
    sent_at: Optional[datetime] = None
    created_at: datetime

    class Config:
        from_attributes = True


class BackgroundCheckOrder(BaseModel):
    """Background check order request."""
    application_id: int
    package_name: str
    first_name: str
    last_name: str
    email: str
    phone: Optional[str] = None
    checks_requested: Optional[List[str]] = []


class BackgroundCheckResponse(BaseModel):
    """Background check response."""
    id: int
    external_check_id: str
    package_name: str
    status: str
    result: Optional[str] = None
    ordered_at: datetime
    completed_at: Optional[datetime] = None
    report_url: Optional[str] = None

    class Config:
        from_attributes = True


# ==================== Router Setup ====================

router = APIRouter(prefix="/api/integrations", tags=["integrations"])


# ==================== Helper Functions ====================

def get_integration_service() -> IntegrationService:
    """Get integration service instance."""
    return create_integration_service()


# ==================== Integration Management ====================

@router.post("", response_model=IntegrationResponse, status_code=status.HTTP_201_CREATED)
def create_integration(
    integration: IntegrationCreate,
    user_id: int,  # Should come from auth
    db: Session = Depends(get_db),
    service: IntegrationService = Depends(get_integration_service)
):
    """
    Create a new integration.

    Connects to an external service provider.
    """
    created = service.create_integration(
        user_id=user_id,
        integration_type=integration.integration_type,
        provider=integration.provider,
        integration_name=integration.integration_name,
        company_id=integration.company_id,
        access_token=integration.access_token,
        refresh_token=integration.refresh_token,
        token_expires_at=integration.token_expires_at,
        config=integration.config,
        db=db
    )
    return created


@router.get("", response_model=List[IntegrationResponse])
def list_integrations(
    user_id: int,  # Should come from auth
    integration_type: Optional[IntegrationType] = None,
    active_only: bool = True,
    db: Session = Depends(get_db),
    service: IntegrationService = Depends(get_integration_service)
):
    """
    List user integrations.

    Returns all integrations for the authenticated user.
    """
    integrations = service.get_user_integrations(
        user_id=user_id,
        integration_type=integration_type,
        active_only=active_only,
        db=db
    )
    return integrations


@router.get("/{integration_id}", response_model=IntegrationResponse)
def get_integration(
    integration_id: int,
    user_id: int,  # Should come from auth
    db: Session = Depends(get_db),
    service: IntegrationService = Depends(get_integration_service)
):
    """
    Get integration details.

    Returns details for a specific integration.
    """
    integration = service.get_integration(integration_id=integration_id, db=db)

    if not integration or integration.user_id != user_id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Integration not found"
        )

    return integration


@router.delete("/{integration_id}")
def delete_integration(
    integration_id: int,
    user_id: int,  # Should come from auth
    db: Session = Depends(get_db),
    service: IntegrationService = Depends(get_integration_service)
):
    """
    Delete an integration.

    Disconnects the integration and removes access.
    """
    try:
        service.delete_integration(
            integration_id=integration_id,
            user_id=user_id,
            db=db
        )
        return {"message": "Integration deleted successfully"}
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e)
        )


@router.post("/{integration_id}/refresh-token", response_model=IntegrationResponse)
def refresh_token(
    integration_id: int,
    token_data: TokenRefresh,
    user_id: int,  # Should come from auth
    db: Session = Depends(get_db),
    service: IntegrationService = Depends(get_integration_service)
):
    """
    Refresh OAuth token.

    Updates the access token for an integration.
    """
    try:
        integration = service.refresh_token(
            integration_id=integration_id,
            new_access_token=token_data.access_token,
            new_refresh_token=token_data.refresh_token,
            expires_at=token_data.expires_at,
            db=db
        )
        return integration
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e)
        )


# ==================== Calendar ====================

@router.get("/{integration_id}/calendar/events", response_model=List[CalendarEventResponse])
def list_calendar_events(
    integration_id: int,
    user_id: int,  # Should come from auth
    start_date: Optional[datetime] = None,
    end_date: Optional[datetime] = None,
    db: Session = Depends(get_db),
    service: IntegrationService = Depends(get_integration_service)
):
    """
    List calendar events.

    Returns synced calendar events from the integration.
    """
    if not start_date:
        start_date = datetime.utcnow()
    if not end_date:
        end_date = start_date + timedelta(days=30)

    events = service.sync_calendar_events(
        integration_id=integration_id,
        user_id=user_id,
        start_date=start_date,
        end_date=end_date,
        db=db
    )
    return events


@router.post("/{integration_id}/calendar/events", response_model=CalendarEventResponse, status_code=status.HTTP_201_CREATED)
def create_calendar_event(
    integration_id: int,
    event: CalendarEventCreate,
    user_id: int,  # Should come from auth
    db: Session = Depends(get_db),
    service: IntegrationService = Depends(get_integration_service)
):
    """
    Create a calendar event.

    Creates an event in the connected calendar.
    """
    created = service.create_calendar_event(
        integration_id=integration_id,
        user_id=user_id,
        title=event.title,
        start_time=event.start_time,
        end_time=event.end_time,
        description=event.description,
        location=event.location,
        attendees=event.attendees,
        db=db
    )
    return created


# ==================== Video Meetings ====================

@router.post("/{integration_id}/video/meetings", response_model=VideoMeetingResponse, status_code=status.HTTP_201_CREATED)
def create_video_meeting(
    integration_id: int,
    meeting: VideoMeetingCreate,
    user_id: int,  # Should come from auth
    company_id: Optional[int] = None,
    db: Session = Depends(get_db),
    service: IntegrationService = Depends(get_integration_service)
):
    """
    Create a video meeting.

    Creates a meeting in the video conferencing platform.
    """
    created = service.create_video_meeting(
        integration_id=integration_id,
        user_id=user_id,
        meeting_title=meeting.meeting_title,
        scheduled_start=meeting.scheduled_start,
        duration_minutes=meeting.duration_minutes,
        interview_id=meeting.interview_id,
        company_id=company_id,
        participants=meeting.participants,
        db=db
    )
    return created


@router.get("/{integration_id}/video/meetings/{meeting_id}", response_model=VideoMeetingResponse)
def get_video_meeting(
    integration_id: int,
    meeting_id: int,
    user_id: int,  # Should come from auth
    db: Session = Depends(get_db),
    service: IntegrationService = Depends(get_integration_service)
):
    """
    Get video meeting details.

    Returns details and join URL for a video meeting.
    """
    meeting = service.get_video_meeting(meeting_id=meeting_id, db=db)

    if not meeting or meeting.integration_id != integration_id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Meeting not found"
        )

    return meeting


@router.patch("/{integration_id}/video/meetings/{meeting_id}/status")
def update_meeting_status(
    integration_id: int,
    meeting_id: int,
    status: str,
    user_id: int,  # Should come from auth
    db: Session = Depends(get_db),
    service: IntegrationService = Depends(get_integration_service)
):
    """
    Update meeting status.

    Updates the status of a video meeting (started, ended, etc.).
    """
    try:
        meeting = service.update_meeting_status(
            meeting_id=meeting_id,
            status=status,
            actual_start_time=datetime.utcnow() if status == "started" else None,
            actual_end_time=datetime.utcnow() if status == "ended" else None,
            db=db
        )
        return {"message": "Meeting status updated", "status": meeting.status}
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e)
        )


# ==================== Communication ====================

@router.post("/{integration_id}/email", response_model=CommunicationResponse, status_code=status.HTTP_201_CREATED)
def send_email(
    integration_id: int,
    email: EmailSend,
    user_id: int,  # Should come from auth
    db: Session = Depends(get_db),
    service: IntegrationService = Depends(get_integration_service)
):
    """
    Send an email.

    Sends an email through the connected email provider.
    """
    log = service.send_email(
        integration_id=integration_id,
        recipient_email=email.recipient_email,
        subject=email.subject,
        body=email.body,
        sender_email=email.sender_email,
        sender_user_id=user_id,
        template_id=email.template_id,
        db=db
    )
    return log


@router.post("/{integration_id}/sms", response_model=CommunicationResponse, status_code=status.HTTP_201_CREATED)
def send_sms(
    integration_id: int,
    sms: SMSSend,
    user_id: int,  # Should come from auth
    db: Session = Depends(get_db),
    service: IntegrationService = Depends(get_integration_service)
):
    """
    Send an SMS.

    Sends an SMS through the connected SMS provider (e.g., Twilio).
    """
    log = service.send_sms(
        integration_id=integration_id,
        recipient_phone=sms.recipient_phone,
        body=sms.body,
        db=db
    )
    return log


@router.get("/{integration_id}/communications", response_model=List[CommunicationResponse])
def list_communications(
    integration_id: int,
    user_id: int,  # Should come from auth
    communication_type: Optional[str] = None,
    limit: int = Query(100, le=1000),
    db: Session = Depends(get_db)
):
    """
    List communication logs.

    Returns communication history for an integration.
    """
    query = db.query(CommunicationLog).filter(
        CommunicationLog.integration_id == integration_id
    )

    if communication_type:
        query = query.filter(CommunicationLog.communication_type == communication_type)

    logs = query.order_by(CommunicationLog.created_at.desc()).limit(limit).all()
    return logs


# ==================== Background Checks ====================

@router.post("/{integration_id}/background-checks", response_model=BackgroundCheckResponse, status_code=status.HTTP_201_CREATED)
def order_background_check(
    integration_id: int,
    check_order: BackgroundCheckOrder,
    user_id: int,  # Should come from auth
    company_id: int = Query(...),
    db: Session = Depends(get_db),
    service: IntegrationService = Depends(get_integration_service)
):
    """
    Order a background check.

    Orders a background check through the connected provider.
    """
    check = service.order_background_check(
        integration_id=integration_id,
        application_id=check_order.application_id,
        candidate_user_id=user_id,
        company_id=company_id,
        package_name=check_order.package_name,
        first_name=check_order.first_name,
        last_name=check_order.last_name,
        email=check_order.email,
        checks_requested=check_order.checks_requested,
        db=db
    )
    return check


@router.get("/{integration_id}/background-checks/{check_id}", response_model=BackgroundCheckResponse)
def get_background_check(
    integration_id: int,
    check_id: int,
    user_id: int,  # Should come from auth
    db: Session = Depends(get_db)
):
    """
    Get background check status.

    Returns the status and results of a background check.
    """
    check = db.query(BackgroundCheck).filter(
        BackgroundCheck.id == check_id,
        BackgroundCheck.integration_id == integration_id
    ).first()

    if not check:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Background check not found"
        )

    return check


# ==================== ATS Sync ====================

@router.post("/{integration_id}/ats/sync")
def start_ats_sync(
    integration_id: int,
    company_id: int,
    sync_type: str = "incremental",
    sync_direction: str = "import",
    user_id: int = Query(...),  # Should come from auth
    db: Session = Depends(get_db),
    service: IntegrationService = Depends(get_integration_service)
):
    """
    Start ATS synchronization.

    Syncs data with an external ATS system.
    """
    sync = service.start_ats_sync(
        integration_id=integration_id,
        company_id=company_id,
        sync_type=sync_type,
        sync_direction=sync_direction,
        db=db
    )
    return {
        "sync_id": sync.id,
        "status": sync.status,
        "message": "ATS sync started"
    }


@router.get("/{integration_id}/ats/syncs")
def list_ats_syncs(
    integration_id: int,
    company_id: int,
    limit: int = Query(50, le=500),
    user_id: int = Query(...),  # Should come from auth
    db: Session = Depends(get_db)
):
    """
    List ATS sync history.

    Returns history of ATS synchronization operations.
    """
    syncs = db.query(ATSSync).filter(
        ATSSync.integration_id == integration_id,
        ATSSync.company_id == company_id
    ).order_by(ATSSync.created_at.desc()).limit(limit).all()

    return syncs
