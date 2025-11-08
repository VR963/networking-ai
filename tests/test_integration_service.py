"""
Tests for Integration Service - Phase 7.

Comprehensive tests for external service integrations.
"""

import pytest
from datetime import datetime, timedelta
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session

from src.networking_ai.database import Base
from src.networking_ai.models import (
    User, UserRole, Company, CompanySize,
    Job, JobStatus, JobType, ExperienceLevel,
    Application, ApplicationStatus
)
from src.networking_ai.models.integrations import (
    Integration,
    CalendarEvent,
    VideoMeeting,
    ATSSync,
    CommunicationLog,
    BackgroundCheck,
    WebhookEndpoint,
    WebhookEvent,
    IntegrationType,
    IntegrationProvider,
    IntegrationStatus
)
from src.networking_ai.services.integration_service import (
    IntegrationService,
    create_integration_service
)


# ==================== Test Database Setup ====================

@pytest.fixture(scope="function")
def db_session():
    """Create a test database session."""
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    TestingSessionLocal = sessionmaker(bind=engine)
    session = TestingSessionLocal()

    yield session

    session.close()


@pytest.fixture
def integration_service():
    """Create integration service instance."""
    return create_integration_service()


# ==================== Test Fixtures ====================

@pytest.fixture
def test_user(db_session: Session):
    """Create a test user."""
    user = User(
        email="user@example.com",
        hashed_password="hashed_password",
        full_name="Test User",
        role=UserRole.TALENT
    )
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)
    return user


@pytest.fixture
def test_company(db_session: Session):
    """Create a test company."""
    user = User(
        email="company@example.com",
        hashed_password="hashed_password",
        full_name="Company Admin",
        role=UserRole.COMPANY
    )
    db_session.add(user)
    db_session.flush()

    company = Company(
        user_id=user.id,
        company_name="Test Company",
        industry="Technology",
        company_size=CompanySize.MEDIUM,
        company_description="Test company"
    )
    db_session.add(company)
    db_session.commit()
    db_session.refresh(company)
    return company


@pytest.fixture
def test_application(db_session: Session, test_user, test_company):
    """Create a test application."""
    hiring_manager = User(
        email="manager@example.com",
        hashed_password="hashed_password",
        full_name="Hiring Manager",
        role=UserRole.HIRING_MANAGER
    )
    db_session.add(hiring_manager)
    db_session.flush()

    job = Job(
        company_id=test_company.id,
        hiring_manager_id=hiring_manager.id,
        title="Software Engineer",
        description="Test job",
        location="Remote",
        job_type=JobType.FULL_TIME,
        experience_level=ExperienceLevel.MID_LEVEL,
        status=JobStatus.ACTIVE
    )
    db_session.add(job)
    db_session.flush()

    application = Application(
        user_id=test_user.id,
        job_id=job.id,
        talent_user_id=test_user.id,
        status=ApplicationStatus.PENDING
    )
    db_session.add(application)
    db_session.commit()
    db_session.refresh(application)
    return application


# ==================== Integration Management Tests ====================

def test_create_integration(
    integration_service: IntegrationService,
    db_session: Session,
    test_user
):
    """Test creating an integration."""
    integration = integration_service.create_integration(
        user_id=test_user.id,
        integration_type=IntegrationType.CALENDAR,
        provider=IntegrationProvider.GOOGLE_CALENDAR,
        integration_name="My Google Calendar",
        access_token="test_access_token",
        db=db_session
    )

    assert integration is not None
    assert integration.user_id == test_user.id
    assert integration.integration_type == IntegrationType.CALENDAR
    assert integration.provider == IntegrationProvider.GOOGLE_CALENDAR
    assert integration.status == IntegrationStatus.ACTIVE
    assert integration.is_active == True


def test_get_integration(
    integration_service: IntegrationService,
    db_session: Session,
    test_user
):
    """Test getting an integration by ID."""
    integration = integration_service.create_integration(
        user_id=test_user.id,
        integration_type=IntegrationType.VIDEO_CONFERENCING,
        provider=IntegrationProvider.ZOOM,
        integration_name="Zoom Integration",
        db=db_session
    )

    retrieved = integration_service.get_integration(
        integration_id=integration.id,
        db=db_session
    )

    assert retrieved is not None
    assert retrieved.id == integration.id
    assert retrieved.provider == IntegrationProvider.ZOOM


def test_get_user_integrations(
    integration_service: IntegrationService,
    db_session: Session,
    test_user
):
    """Test getting all integrations for a user."""
    # Create multiple integrations
    integration_service.create_integration(
        user_id=test_user.id,
        integration_type=IntegrationType.CALENDAR,
        provider=IntegrationProvider.GOOGLE_CALENDAR,
        integration_name="Google Calendar",
        db=db_session
    )

    integration_service.create_integration(
        user_id=test_user.id,
        integration_type=IntegrationType.VIDEO_CONFERENCING,
        provider=IntegrationProvider.ZOOM,
        integration_name="Zoom",
        db=db_session
    )

    integrations = integration_service.get_user_integrations(
        user_id=test_user.id,
        db=db_session
    )

    assert len(integrations) == 2


def test_get_user_integrations_filtered(
    integration_service: IntegrationService,
    db_session: Session,
    test_user
):
    """Test getting filtered integrations."""
    integration_service.create_integration(
        user_id=test_user.id,
        integration_type=IntegrationType.CALENDAR,
        provider=IntegrationProvider.GOOGLE_CALENDAR,
        integration_name="Google Calendar",
        db=db_session
    )

    integration_service.create_integration(
        user_id=test_user.id,
        integration_type=IntegrationType.VIDEO_CONFERENCING,
        provider=IntegrationProvider.ZOOM,
        integration_name="Zoom",
        db=db_session
    )

    calendar_integrations = integration_service.get_user_integrations(
        user_id=test_user.id,
        integration_type=IntegrationType.CALENDAR,
        db=db_session
    )

    assert len(calendar_integrations) == 1
    assert calendar_integrations[0].integration_type == IntegrationType.CALENDAR


def test_delete_integration(
    integration_service: IntegrationService,
    db_session: Session,
    test_user
):
    """Test deleting an integration."""
    integration = integration_service.create_integration(
        user_id=test_user.id,
        integration_type=IntegrationType.CALENDAR,
        provider=IntegrationProvider.GOOGLE_CALENDAR,
        integration_name="Google Calendar",
        db=db_session
    )

    result = integration_service.delete_integration(
        integration_id=integration.id,
        user_id=test_user.id,
        db=db_session
    )

    assert result == True

    # Verify it's marked inactive
    deleted = db_session.query(Integration).get(integration.id)
    assert deleted.is_active == False
    assert deleted.status == IntegrationStatus.INACTIVE


def test_refresh_token(
    integration_service: IntegrationService,
    db_session: Session,
    test_user
):
    """Test refreshing OAuth token."""
    integration = integration_service.create_integration(
        user_id=test_user.id,
        integration_type=IntegrationType.CALENDAR,
        provider=IntegrationProvider.GOOGLE_CALENDAR,
        integration_name="Google Calendar",
        access_token="old_token",
        refresh_token="old_refresh",
        db=db_session
    )

    new_expires = datetime.utcnow() + timedelta(hours=1)
    updated = integration_service.refresh_token(
        integration_id=integration.id,
        new_access_token="new_token",
        new_refresh_token="new_refresh",
        expires_at=new_expires,
        db=db_session
    )

    assert updated.access_token == "new_token"
    assert updated.refresh_token == "new_refresh"
    assert updated.token_expires_at == new_expires
    assert updated.status == IntegrationStatus.ACTIVE


# ==================== Calendar Event Tests ====================

def test_create_calendar_event(
    integration_service: IntegrationService,
    db_session: Session,
    test_user
):
    """Test creating a calendar event."""
    integration = integration_service.create_integration(
        user_id=test_user.id,
        integration_type=IntegrationType.CALENDAR,
        provider=IntegrationProvider.GOOGLE_CALENDAR,
        integration_name="Google Calendar",
        db=db_session
    )

    start_time = datetime.utcnow() + timedelta(days=1)
    end_time = start_time + timedelta(hours=1)

    event = integration_service.create_calendar_event(
        integration_id=integration.id,
        user_id=test_user.id,
        title="Team Meeting",
        start_time=start_time,
        end_time=end_time,
        description="Weekly team sync",
        location="Conference Room A",
        attendees=["alice@example.com", "bob@example.com"],
        db=db_session
    )

    assert event is not None
    assert event.title == "Team Meeting"
    assert event.start_time == start_time
    assert event.end_time == end_time
    assert len(event.attendees) == 2


def test_sync_calendar_events(
    integration_service: IntegrationService,
    db_session: Session,
    test_user
):
    """Test syncing calendar events."""
    integration = integration_service.create_integration(
        user_id=test_user.id,
        integration_type=IntegrationType.CALENDAR,
        provider=IntegrationProvider.GOOGLE_CALENDAR,
        integration_name="Google Calendar",
        db=db_session
    )

    # Create some events first
    start_time = datetime.utcnow()
    integration_service.create_calendar_event(
        integration_id=integration.id,
        user_id=test_user.id,
        title="Event 1",
        start_time=start_time,
        end_time=start_time + timedelta(hours=1),
        db=db_session
    )

    # Sync events
    start_date = datetime.utcnow() - timedelta(days=7)
    end_date = datetime.utcnow() + timedelta(days=7)

    events = integration_service.sync_calendar_events(
        integration_id=integration.id,
        user_id=test_user.id,
        start_date=start_date,
        end_date=end_date,
        db=db_session
    )

    assert len(events) >= 1
    assert events[0].title == "Event 1"


# ==================== Video Meeting Tests ====================

def test_create_video_meeting(
    integration_service: IntegrationService,
    db_session: Session,
    test_user,
    test_company
):
    """Test creating a video meeting."""
    integration = integration_service.create_integration(
        user_id=test_user.id,
        integration_type=IntegrationType.VIDEO_CONFERENCING,
        provider=IntegrationProvider.ZOOM,
        integration_name="Zoom",
        db=db_session
    )

    scheduled_start = datetime.utcnow() + timedelta(days=1)

    meeting = integration_service.create_video_meeting(
        integration_id=integration.id,
        user_id=test_user.id,
        meeting_title="Technical Interview",
        scheduled_start=scheduled_start,
        duration_minutes=60,
        company_id=test_company.id,
        participants=["candidate@example.com", "interviewer@example.com"],
        db=db_session
    )

    assert meeting is not None
    assert meeting.meeting_title == "Technical Interview"
    assert meeting.duration_minutes == 60
    assert meeting.status == "scheduled"
    assert len(meeting.participants) == 2
    assert meeting.meeting_url is not None


def test_get_video_meeting(
    integration_service: IntegrationService,
    db_session: Session,
    test_user
):
    """Test getting a video meeting."""
    integration = integration_service.create_integration(
        user_id=test_user.id,
        integration_type=IntegrationType.VIDEO_CONFERENCING,
        provider=IntegrationProvider.ZOOM,
        integration_name="Zoom",
        db=db_session
    )

    meeting = integration_service.create_video_meeting(
        integration_id=integration.id,
        user_id=test_user.id,
        meeting_title="Interview",
        scheduled_start=datetime.utcnow() + timedelta(days=1),
        duration_minutes=30,
        db=db_session
    )

    retrieved = integration_service.get_video_meeting(
        meeting_id=meeting.id,
        db=db_session
    )

    assert retrieved is not None
    assert retrieved.id == meeting.id
    assert retrieved.meeting_title == "Interview"


def test_update_meeting_status(
    integration_service: IntegrationService,
    db_session: Session,
    test_user
):
    """Test updating video meeting status."""
    integration = integration_service.create_integration(
        user_id=test_user.id,
        integration_type=IntegrationType.VIDEO_CONFERENCING,
        provider=IntegrationProvider.ZOOM,
        integration_name="Zoom",
        db=db_session
    )

    meeting = integration_service.create_video_meeting(
        integration_id=integration.id,
        user_id=test_user.id,
        meeting_title="Interview",
        scheduled_start=datetime.utcnow(),
        duration_minutes=30,
        db=db_session
    )

    # Start the meeting
    updated = integration_service.update_meeting_status(
        meeting_id=meeting.id,
        status="started",
        actual_start_time=datetime.utcnow(),
        db=db_session
    )

    assert updated.status == "started"
    assert updated.actual_start_time is not None


# ==================== Communication Tests ====================

def test_send_email(
    integration_service: IntegrationService,
    db_session: Session,
    test_user
):
    """Test sending an email."""
    integration = integration_service.create_integration(
        user_id=test_user.id,
        integration_type=IntegrationType.EMAIL,
        provider=IntegrationProvider.SENDGRID,
        integration_name="SendGrid",
        db=db_session
    )

    log = integration_service.send_email(
        integration_id=integration.id,
        recipient_email="recipient@example.com",
        subject="Test Email",
        body="This is a test email",
        sender_email="sender@example.com",
        db=db_session
    )

    assert log is not None
    assert log.communication_type == "email"
    assert log.recipient_email == "recipient@example.com"
    assert log.subject == "Test Email"
    assert log.status == "sent"


def test_send_sms(
    integration_service: IntegrationService,
    db_session: Session,
    test_user
):
    """Test sending an SMS."""
    integration = integration_service.create_integration(
        user_id=test_user.id,
        integration_type=IntegrationType.MESSAGING,
        provider=IntegrationProvider.TWILIO,
        integration_name="Twilio",
        db=db_session
    )

    log = integration_service.send_sms(
        integration_id=integration.id,
        recipient_phone="+1234567890",
        body="Test SMS message",
        db=db_session
    )

    assert log is not None
    assert log.communication_type == "sms"
    assert log.recipient_phone == "+1234567890"
    assert log.body == "Test SMS message"
    assert log.status == "sent"


# ==================== ATS Sync Tests ====================

def test_start_ats_sync(
    integration_service: IntegrationService,
    db_session: Session,
    test_company
):
    """Test starting an ATS sync."""
    integration = integration_service.create_integration(
        user_id=1,  # Dummy user
        integration_type=IntegrationType.ATS,
        provider=IntegrationProvider.GREENHOUSE,
        integration_name="Greenhouse",
        company_id=test_company.id,
        db=db_session
    )

    sync = integration_service.start_ats_sync(
        integration_id=integration.id,
        company_id=test_company.id,
        sync_type="incremental",
        sync_direction="import",
        db=db_session
    )

    assert sync is not None
    assert sync.sync_type == "incremental"
    assert sync.sync_direction == "import"
    assert sync.status == "pending"


def test_complete_ats_sync(
    integration_service: IntegrationService,
    db_session: Session,
    test_company
):
    """Test completing an ATS sync."""
    integration = integration_service.create_integration(
        user_id=1,
        integration_type=IntegrationType.ATS,
        provider=IntegrationProvider.GREENHOUSE,
        integration_name="Greenhouse",
        company_id=test_company.id,
        db=db_session
    )

    sync = integration_service.start_ats_sync(
        integration_id=integration.id,
        company_id=test_company.id,
        db=db_session
    )

    completed = integration_service.complete_ats_sync(
        sync_id=sync.id,
        jobs_synced=10,
        applications_synced=50,
        candidates_synced=30,
        success_count=90,
        error_count=0,
        db=db_session
    )

    assert completed.status == "completed"
    assert completed.jobs_synced == 10
    assert completed.applications_synced == 50
    assert completed.success_count == 90
    assert completed.completed_at is not None


# ==================== Background Check Tests ====================

def test_order_background_check(
    integration_service: IntegrationService,
    db_session: Session,
    test_user,
    test_company,
    test_application
):
    """Test ordering a background check."""
    integration = integration_service.create_integration(
        user_id=test_user.id,
        integration_type=IntegrationType.BACKGROUND_CHECK,
        provider=IntegrationProvider.CHECKR,
        integration_name="Checkr",
        company_id=test_company.id,
        db=db_session
    )

    check = integration_service.order_background_check(
        integration_id=integration.id,
        application_id=test_application.id,
        candidate_user_id=test_user.id,
        company_id=test_company.id,
        package_name="Standard",
        first_name="John",
        last_name="Doe",
        email="john@example.com",
        checks_requested=["criminal", "employment"],
        db=db_session
    )

    assert check is not None
    assert check.package_name == "Standard"
    assert check.first_name == "John"
    assert check.last_name == "Doe"
    assert check.status == "pending"
    assert len(check.checks_requested) == 2


# ==================== Webhook Tests ====================

def test_register_webhook(
    integration_service: IntegrationService,
    db_session: Session,
    test_user
):
    """Test registering a webhook endpoint."""
    integration = integration_service.create_integration(
        user_id=test_user.id,
        integration_type=IntegrationType.ATS,
        provider=IntegrationProvider.GREENHOUSE,
        integration_name="Greenhouse",
        db=db_session
    )

    endpoint = integration_service.register_webhook(
        integration_id=integration.id,
        url="https://example.com/webhooks/greenhouse",
        secret="webhook_secret_123",
        enabled_events=["candidate.created", "application.submitted"],
        db=db_session
    )

    assert endpoint is not None
    assert endpoint.url == "https://example.com/webhooks/greenhouse"
    assert len(endpoint.enabled_events) == 2
    assert endpoint.is_active == True


def test_process_webhook_event(
    integration_service: IntegrationService,
    db_session: Session,
    test_user
):
    """Test processing a webhook event."""
    integration = integration_service.create_integration(
        user_id=test_user.id,
        integration_type=IntegrationType.ATS,
        provider=IntegrationProvider.GREENHOUSE,
        integration_name="Greenhouse",
        db=db_session
    )

    endpoint = integration_service.register_webhook(
        integration_id=integration.id,
        url="https://example.com/webhooks",
        secret="secret",
        enabled_events=["candidate.created"],
        db=db_session
    )

    event = integration_service.process_webhook_event(
        endpoint_id=endpoint.id,
        integration_id=integration.id,
        event_type="candidate.created",
        payload={"candidate_id": 123, "name": "John Doe"},
        event_id="evt_123",
        signature_verified=True,
        db=db_session
    )

    assert event is not None
    assert event.event_type == "candidate.created"
    assert event.payload["candidate_id"] == 123
    assert event.signature_verified == True


# ==================== Integration Model Tests ====================

def test_integration_is_token_expired(db_session: Session, test_user):
    """Test token expiration check."""
    # Expired token
    expired_integration = Integration(
        user_id=test_user.id,
        integration_type=IntegrationType.CALENDAR,
        provider=IntegrationProvider.GOOGLE_CALENDAR,
        integration_name="Test",
        token_expires_at=datetime.utcnow() - timedelta(hours=1)
    )
    assert expired_integration.is_token_expired() == True

    # Valid token
    valid_integration = Integration(
        user_id=test_user.id,
        integration_type=IntegrationType.CALENDAR,
        provider=IntegrationProvider.GOOGLE_CALENDAR,
        integration_name="Test",
        token_expires_at=datetime.utcnow() + timedelta(hours=1)
    )
    assert valid_integration.is_token_expired() == False


def test_integration_needs_refresh(db_session: Session, test_user):
    """Test token refresh check."""
    # Needs refresh (within 5 minutes)
    needs_refresh = Integration(
        user_id=test_user.id,
        integration_type=IntegrationType.CALENDAR,
        provider=IntegrationProvider.GOOGLE_CALENDAR,
        integration_name="Test",
        token_expires_at=datetime.utcnow() + timedelta(minutes=3)
    )
    assert needs_refresh.needs_refresh() == True

    # Doesn't need refresh
    valid = Integration(
        user_id=test_user.id,
        integration_type=IntegrationType.CALENDAR,
        provider=IntegrationProvider.GOOGLE_CALENDAR,
        integration_name="Test",
        token_expires_at=datetime.utcnow() + timedelta(hours=1)
    )
    assert valid.needs_refresh() == False
