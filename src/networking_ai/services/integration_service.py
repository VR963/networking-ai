"""
Integration Service - Phase 7.

Service for managing external service integrations (Calendar, Video, ATS, Communication).
"""

from datetime import datetime, timedelta
from typing import Optional, List, Dict, Any
from sqlalchemy.orm import Session
import logging

from ..models.integrations import (
    Integration,
    CalendarEvent,
    VideoMeeting,
    ATSSync,
    CommunicationLog,
    BackgroundCheck,
    LinkedInProfile,
    WebhookEndpoint,
    WebhookEvent,
    IntegrationType,
    IntegrationProvider,
    IntegrationStatus
)
from ..models.user import User
from ..models.company import CompanyLegacy as Company

logger = logging.getLogger(__name__)


class IntegrationService:
    """
    Service for managing external integrations.
    """

    def __init__(self, notification_service=None):
        """Initialize integration service."""
        self.notification_service = notification_service

    # ==================== Integration Management ====================

    def create_integration(
        self,
        user_id: int,
        integration_type: IntegrationType,
        provider: IntegrationProvider,
        integration_name: str,
        company_id: Optional[int] = None,
        access_token: Optional[str] = None,
        refresh_token: Optional[str] = None,
        token_expires_at: Optional[datetime] = None,
        config: Optional[Dict[str, Any]] = None,
        db: Session = None
    ) -> Integration:
        """
        Create a new integration.

        Args:
            user_id: User ID
            integration_type: Type of integration
            provider: Provider name
            integration_name: Display name
            company_id: Optional company ID
            access_token: OAuth access token
            refresh_token: OAuth refresh token
            token_expires_at: Token expiration
            config: Provider-specific configuration
            db: Database session

        Returns:
            Created Integration
        """
        integration = Integration(
            user_id=user_id,
            company_id=company_id,
            integration_type=integration_type,
            provider=provider,
            integration_name=integration_name,
            access_token=access_token,
            refresh_token=refresh_token,
            token_expires_at=token_expires_at,
            config=config or {},
            status=IntegrationStatus.ACTIVE if access_token else IntegrationStatus.PENDING
        )

        db.add(integration)
        db.commit()
        db.refresh(integration)

        logger.info(f"Created integration {integration.id}: {provider.value} for user {user_id}")
        return integration

    def get_integration(
        self,
        integration_id: int,
        db: Session = None
    ) -> Optional[Integration]:
        """
        Get integration by ID.

        Args:
            integration_id: Integration ID
            db: Database session

        Returns:
            Integration or None
        """
        return db.query(Integration).filter(Integration.id == integration_id).first()

    def get_user_integrations(
        self,
        user_id: int,
        integration_type: Optional[IntegrationType] = None,
        active_only: bool = True,
        db: Session = None
    ) -> List[Integration]:
        """
        Get integrations for a user.

        Args:
            user_id: User ID
            integration_type: Filter by type
            active_only: Only return active integrations
            db: Database session

        Returns:
            List of Integration objects
        """
        query = db.query(Integration).filter(Integration.user_id == user_id)

        if integration_type:
            query = query.filter(Integration.integration_type == integration_type)

        if active_only:
            query = query.filter(Integration.is_active == True)

        return query.order_by(Integration.created_at.desc()).all()

    def delete_integration(
        self,
        integration_id: int,
        user_id: int,
        db: Session = None
    ) -> bool:
        """
        Delete an integration.

        Args:
            integration_id: Integration ID
            user_id: User ID (for authorization)
            db: Database session

        Returns:
            True if deleted successfully
        """
        integration = db.query(Integration).filter(
            Integration.id == integration_id,
            Integration.user_id == user_id
        ).first()

        if not integration:
            raise ValueError("Integration not found")

        integration.is_active = False
        integration.status = IntegrationStatus.INACTIVE
        db.commit()

        logger.info(f"Deleted integration {integration_id}")
        return True

    def refresh_token(
        self,
        integration_id: int,
        new_access_token: str,
        new_refresh_token: Optional[str] = None,
        expires_at: Optional[datetime] = None,
        db: Session = None
    ) -> Integration:
        """
        Refresh OAuth token for integration.

        Args:
            integration_id: Integration ID
            new_access_token: New access token
            new_refresh_token: New refresh token
            expires_at: Token expiration
            db: Database session

        Returns:
            Updated Integration
        """
        integration = db.query(Integration).get(integration_id)
        if not integration:
            raise ValueError("Integration not found")

        integration.access_token = new_access_token
        if new_refresh_token:
            integration.refresh_token = new_refresh_token
        integration.token_expires_at = expires_at
        integration.status = IntegrationStatus.ACTIVE
        integration.updated_at = datetime.utcnow()

        db.commit()
        db.refresh(integration)

        logger.info(f"Refreshed token for integration {integration_id}")
        return integration

    # ==================== Calendar Events ====================

    def sync_calendar_events(
        self,
        integration_id: int,
        user_id: int,
        start_date: datetime,
        end_date: datetime,
        db: Session = None
    ) -> List[CalendarEvent]:
        """
        Sync calendar events from external provider.

        Args:
            integration_id: Integration ID
            user_id: User ID
            start_date: Start date for sync
            end_date: End date for sync
            db: Database session

        Returns:
            List of synced CalendarEvent objects
        """
        integration = db.query(Integration).get(integration_id)
        if not integration or integration.user_id != user_id:
            raise ValueError("Integration not found")

        # In production, this would call the actual provider API
        # For now, we'll just update the last sync time
        integration.last_sync_at = datetime.utcnow()
        db.commit()

        # Get existing events
        events = db.query(CalendarEvent).filter(
            CalendarEvent.integration_id == integration_id,
            CalendarEvent.start_time >= start_date,
            CalendarEvent.end_time <= end_date
        ).all()

        logger.info(f"Synced {len(events)} calendar events for integration {integration_id}")
        return events

    def create_calendar_event(
        self,
        integration_id: int,
        user_id: int,
        title: str,
        start_time: datetime,
        end_time: datetime,
        description: Optional[str] = None,
        location: Optional[str] = None,
        attendees: Optional[List[str]] = None,
        db: Session = None
    ) -> CalendarEvent:
        """
        Create a calendar event.

        Args:
            integration_id: Integration ID
            user_id: User ID
            title: Event title
            start_time: Start time
            end_time: End time
            description: Event description
            location: Event location
            attendees: List of attendee emails
            db: Database session

        Returns:
            Created CalendarEvent
        """
        # In production, this would create the event via the provider API
        # and get back an external_id
        external_id = f"cal_event_{datetime.utcnow().timestamp()}"

        event = CalendarEvent(
            integration_id=integration_id,
            user_id=user_id,
            external_id=external_id,
            title=title,
            description=description,
            location=location,
            start_time=start_time,
            end_time=end_time,
            attendees=attendees or []
        )

        db.add(event)
        db.commit()
        db.refresh(event)

        logger.info(f"Created calendar event {event.id}")
        return event

    # ==================== Video Meetings ====================

    def create_video_meeting(
        self,
        integration_id: int,
        user_id: int,
        meeting_title: str,
        scheduled_start: datetime,
        duration_minutes: int,
        interview_id: Optional[int] = None,
        company_id: Optional[int] = None,
        participants: Optional[List[str]] = None,
        db: Session = None
    ) -> VideoMeeting:
        """
        Create a video meeting.

        Args:
            integration_id: Integration ID
            user_id: User ID
            meeting_title: Meeting title
            scheduled_start: Scheduled start time
            duration_minutes: Duration in minutes
            interview_id: Optional interview ID
            company_id: Optional company ID
            participants: List of participant emails
            db: Database session

        Returns:
            Created VideoMeeting
        """
        integration = db.query(Integration).get(integration_id)
        if not integration:
            raise ValueError("Integration not found")

        # In production, this would create the meeting via the provider API
        external_meeting_id = f"meeting_{datetime.utcnow().timestamp()}"
        meeting_url = f"https://{integration.provider.value}.example.com/j/{external_meeting_id}"
        join_url = meeting_url

        # Get user email for host
        user = db.query(User).get(user_id)
        host_email = user.email if user else "unknown@example.com"

        scheduled_end = scheduled_start + timedelta(minutes=duration_minutes)

        meeting = VideoMeeting(
            integration_id=integration_id,
            interview_id=interview_id,
            user_id=user_id,
            company_id=company_id,
            external_meeting_id=external_meeting_id,
            meeting_title=meeting_title,
            meeting_url=meeting_url,
            join_url=join_url,
            scheduled_start=scheduled_start,
            scheduled_end=scheduled_end,
            duration_minutes=duration_minutes,
            host_email=host_email,
            participants=participants or [],
            provider=integration.provider,
            status="scheduled"
        )

        db.add(meeting)
        db.commit()
        db.refresh(meeting)

        logger.info(f"Created video meeting {meeting.id}")
        return meeting

    def get_video_meeting(
        self,
        meeting_id: int,
        db: Session = None
    ) -> Optional[VideoMeeting]:
        """
        Get video meeting by ID.

        Args:
            meeting_id: Meeting ID
            db: Database session

        Returns:
            VideoMeeting or None
        """
        return db.query(VideoMeeting).filter(VideoMeeting.id == meeting_id).first()

    def update_meeting_status(
        self,
        meeting_id: int,
        status: str,
        actual_start_time: Optional[datetime] = None,
        actual_end_time: Optional[datetime] = None,
        db: Session = None
    ) -> VideoMeeting:
        """
        Update video meeting status.

        Args:
            meeting_id: Meeting ID
            status: New status
            actual_start_time: Actual start time
            actual_end_time: Actual end time
            db: Database session

        Returns:
            Updated VideoMeeting
        """
        meeting = db.query(VideoMeeting).get(meeting_id)
        if not meeting:
            raise ValueError("Meeting not found")

        meeting.status = status
        if actual_start_time:
            meeting.actual_start_time = actual_start_time
        if actual_end_time:
            meeting.actual_end_time = actual_end_time
        meeting.updated_at = datetime.utcnow()

        db.commit()
        db.refresh(meeting)

        logger.info(f"Updated meeting {meeting_id} status to {status}")
        return meeting

    # ==================== ATS Sync ====================

    def start_ats_sync(
        self,
        integration_id: int,
        company_id: int,
        sync_type: str = "incremental",
        sync_direction: str = "import",
        db: Session = None
    ) -> ATSSync:
        """
        Start an ATS synchronization.

        Args:
            integration_id: Integration ID
            company_id: Company ID
            sync_type: Sync type (full, incremental)
            sync_direction: Direction (import, export, bidirectional)
            db: Database session

        Returns:
            Created ATSSync
        """
        sync = ATSSync(
            integration_id=integration_id,
            company_id=company_id,
            sync_type=sync_type,
            sync_direction=sync_direction,
            status="pending"
        )

        db.add(sync)
        db.commit()
        db.refresh(sync)

        logger.info(f"Started ATS sync {sync.id}")
        return sync

    def complete_ats_sync(
        self,
        sync_id: int,
        jobs_synced: int = 0,
        applications_synced: int = 0,
        candidates_synced: int = 0,
        success_count: int = 0,
        error_count: int = 0,
        errors: Optional[List[str]] = None,
        db: Session = None
    ) -> ATSSync:
        """
        Complete an ATS sync.

        Args:
            sync_id: Sync ID
            jobs_synced: Number of jobs synced
            applications_synced: Number of applications synced
            candidates_synced: Number of candidates synced
            success_count: Successful operations
            error_count: Failed operations
            errors: List of error messages
            db: Database session

        Returns:
            Updated ATSSync
        """
        sync = db.query(ATSSync).get(sync_id)
        if not sync:
            raise ValueError("Sync not found")

        sync.status = "completed" if error_count == 0 else "failed"
        sync.completed_at = datetime.utcnow()
        sync.jobs_synced = jobs_synced
        sync.applications_synced = applications_synced
        sync.candidates_synced = candidates_synced
        sync.success_count = success_count
        sync.error_count = error_count
        sync.errors = errors or []

        db.commit()
        db.refresh(sync)

        logger.info(f"Completed ATS sync {sync_id}: {success_count} success, {error_count} errors")
        return sync

    # ==================== Communication ====================

    def send_email(
        self,
        integration_id: int,
        recipient_email: str,
        subject: str,
        body: str,
        sender_email: Optional[str] = None,
        recipient_user_id: Optional[int] = None,
        sender_user_id: Optional[int] = None,
        template_id: Optional[str] = None,
        db: Session = None
    ) -> CommunicationLog:
        """
        Send an email through integration.

        Args:
            integration_id: Integration ID
            recipient_email: Recipient email
            subject: Email subject
            body: Email body
            sender_email: Sender email
            recipient_user_id: Optional recipient user ID
            sender_user_id: Optional sender user ID
            template_id: Optional template ID
            db: Database session

        Returns:
            Created CommunicationLog
        """
        integration = db.query(Integration).get(integration_id)
        if not integration:
            raise ValueError("Integration not found")

        # In production, this would send via the provider API
        external_id = f"email_{datetime.utcnow().timestamp()}"

        log = CommunicationLog(
            integration_id=integration_id,
            communication_type="email",
            provider=integration.provider,
            recipient_email=recipient_email,
            recipient_user_id=recipient_user_id,
            sender_email=sender_email,
            sender_user_id=sender_user_id,
            subject=subject,
            body=body,
            template_id=template_id,
            external_id=external_id,
            status="sent",
            sent_at=datetime.utcnow()
        )

        db.add(log)
        db.commit()
        db.refresh(log)

        logger.info(f"Sent email {log.id} to {recipient_email}")
        return log

    def send_sms(
        self,
        integration_id: int,
        recipient_phone: str,
        body: str,
        recipient_user_id: Optional[int] = None,
        db: Session = None
    ) -> CommunicationLog:
        """
        Send an SMS through integration.

        Args:
            integration_id: Integration ID
            recipient_phone: Recipient phone number
            body: SMS body
            recipient_user_id: Optional recipient user ID
            db: Database session

        Returns:
            Created CommunicationLog
        """
        integration = db.query(Integration).get(integration_id)
        if not integration:
            raise ValueError("Integration not found")

        # In production, this would send via the provider API (e.g., Twilio)
        external_id = f"sms_{datetime.utcnow().timestamp()}"

        log = CommunicationLog(
            integration_id=integration_id,
            communication_type="sms",
            provider=integration.provider,
            recipient_phone=recipient_phone,
            recipient_user_id=recipient_user_id,
            body=body,
            external_id=external_id,
            status="sent",
            sent_at=datetime.utcnow()
        )

        db.add(log)
        db.commit()
        db.refresh(log)

        logger.info(f"Sent SMS {log.id} to {recipient_phone}")
        return log

    # ==================== Background Checks ====================

    def order_background_check(
        self,
        integration_id: int,
        application_id: int,
        candidate_user_id: int,
        company_id: int,
        package_name: str,
        first_name: str,
        last_name: str,
        email: str,
        checks_requested: Optional[List[str]] = None,
        db: Session = None
    ) -> BackgroundCheck:
        """
        Order a background check.

        Args:
            integration_id: Integration ID
            application_id: Application ID
            candidate_user_id: Candidate user ID
            company_id: Company ID
            package_name: Check package name
            first_name: Candidate first name
            last_name: Candidate last name
            email: Candidate email
            checks_requested: List of check types
            db: Database session

        Returns:
            Created BackgroundCheck
        """
        integration = db.query(Integration).get(integration_id)
        if not integration:
            raise ValueError("Integration not found")

        # In production, this would order via the provider API
        external_check_id = f"bgcheck_{datetime.utcnow().timestamp()}"

        check = BackgroundCheck(
            integration_id=integration_id,
            application_id=application_id,
            candidate_user_id=candidate_user_id,
            company_id=company_id,
            external_check_id=external_check_id,
            provider=integration.provider,
            package_name=package_name,
            checks_requested=checks_requested or [],
            first_name=first_name,
            last_name=last_name,
            email=email,
            status="pending"
        )

        db.add(check)
        db.commit()
        db.refresh(check)

        logger.info(f"Ordered background check {check.id} for application {application_id}")
        return check

    # ==================== Webhooks ====================

    def register_webhook(
        self,
        integration_id: int,
        url: str,
        secret: str,
        enabled_events: List[str],
        db: Session = None
    ) -> WebhookEndpoint:
        """
        Register a webhook endpoint.

        Args:
            integration_id: Integration ID
            url: Webhook URL
            secret: Secret for signature verification
            enabled_events: List of event types
            db: Database session

        Returns:
            Created WebhookEndpoint
        """
        endpoint = WebhookEndpoint(
            integration_id=integration_id,
            url=url,
            secret=secret,
            enabled_events=enabled_events
        )

        db.add(endpoint)
        db.commit()
        db.refresh(endpoint)

        logger.info(f"Registered webhook endpoint {endpoint.id}")
        return endpoint

    def process_webhook_event(
        self,
        endpoint_id: int,
        integration_id: int,
        event_type: str,
        payload: Dict[str, Any],
        event_id: Optional[str] = None,
        request_headers: Optional[Dict[str, str]] = None,
        signature_verified: bool = False,
        db: Session = None
    ) -> WebhookEvent:
        """
        Process a webhook event.

        Args:
            endpoint_id: Endpoint ID
            integration_id: Integration ID
            event_type: Event type
            payload: Event payload
            event_id: External event ID
            request_headers: Request headers
            signature_verified: Whether signature was verified
            db: Database session

        Returns:
            Created WebhookEvent
        """
        event = WebhookEvent(
            endpoint_id=endpoint_id,
            integration_id=integration_id,
            event_type=event_type,
            event_id=event_id,
            payload=payload,
            request_headers=request_headers or {},
            signature_verified=signature_verified
        )

        db.add(event)
        db.commit()
        db.refresh(event)

        logger.info(f"Processed webhook event {event.id}: {event_type}")
        return event


def create_integration_service(notification_service=None) -> IntegrationService:
    """
    Factory function to create IntegrationService.

    Args:
        notification_service: Optional notification service

    Returns:
        IntegrationService instance
    """
    return IntegrationService(notification_service=notification_service)
