"""
Integration Models - Phase 7.

Models for external service integrations (Calendar, Video, ATS, Communication).
"""

from datetime import datetime, timedelta
from enum import Enum
from typing import Optional, Dict, Any
from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, Boolean, Text, JSON, Enum as SQLEnum
from sqlalchemy.orm import relationship

from ..database import Base


class IntegrationType(str, Enum):
    """Types of integrations."""
    CALENDAR = "calendar"
    VIDEO_CONFERENCING = "video_conferencing"
    ATS = "ats"
    EMAIL = "email"
    MESSAGING = "messaging"
    BACKGROUND_CHECK = "background_check"
    LINKEDIN = "linkedin"
    PAYMENT = "payment"


class IntegrationProvider(str, Enum):
    """Integration providers."""
    # Calendar
    GOOGLE_CALENDAR = "google_calendar"
    OUTLOOK_CALENDAR = "outlook_calendar"
    APPLE_CALENDAR = "apple_calendar"

    # Video Conferencing
    ZOOM = "zoom"
    MICROSOFT_TEAMS = "microsoft_teams"
    GOOGLE_MEET = "google_meet"
    WEBEX = "webex"

    # ATS
    GREENHOUSE = "greenhouse"
    LEVER = "lever"
    WORKDAY = "workday"
    JOBVITE = "jobvite"

    # Communication
    SLACK = "slack"
    SENDGRID = "sendgrid"
    MAILGUN = "mailgun"
    TWILIO = "twilio"

    # Background Check
    CHECKR = "checkr"
    STERLING = "sterling"

    # Social
    LINKEDIN = "linkedin"

    # Payment
    STRIPE = "stripe"


class IntegrationStatus(str, Enum):
    """Integration connection status."""
    ACTIVE = "active"
    INACTIVE = "inactive"
    ERROR = "error"
    EXPIRED = "expired"
    PENDING = "pending"


class Integration(Base):
    """
    External service integration.

    Stores OAuth tokens and configuration for external services.
    """
    __tablename__ = "integrations"
    __table_args__ = {'extend_existing': True}

    # Primary Key
    id = Column(Integer, primary_key=True, index=True)

    # Owner
    user_id = Column(Integer, ForeignKey("users.id"), nullable=True, index=True)
    company_id = Column(Integer, ForeignKey("companies.id"), nullable=True, index=True)

    # Integration Details
    integration_type = Column(SQLEnum(IntegrationType), nullable=False, index=True)
    provider = Column(SQLEnum(IntegrationProvider), nullable=False, index=True)
    integration_name = Column(String(255), nullable=False)

    # OAuth/API Credentials
    access_token = Column(Text, nullable=True)  # Encrypted
    refresh_token = Column(Text, nullable=True)  # Encrypted
    token_expires_at = Column(DateTime, nullable=True)
    api_key = Column(String(500), nullable=True)  # Encrypted
    api_secret = Column(String(500), nullable=True)  # Encrypted

    # Provider-Specific IDs
    provider_user_id = Column(String(255), nullable=True)
    provider_account_id = Column(String(255), nullable=True)
    provider_workspace_id = Column(String(255), nullable=True)

    # Configuration
    config = Column(JSON, default=dict)  # Provider-specific configuration
    scopes = Column(JSON, default=list)  # OAuth scopes granted

    # Status
    status = Column(SQLEnum(IntegrationStatus), default=IntegrationStatus.PENDING, index=True)
    is_active = Column(Boolean, default=True)

    # Metadata
    last_sync_at = Column(DateTime, nullable=True)
    last_error = Column(Text, nullable=True)
    sync_frequency = Column(String(50), nullable=True)  # hourly, daily, manual

    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow, index=True)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    expires_at = Column(DateTime, nullable=True)

    # Relationships
    user = relationship("User", foreign_keys=[user_id])
    company = relationship("CompanyLegacy", foreign_keys=[company_id])
    calendar_events = relationship("CalendarEvent", back_populates="integration")
    video_meetings = relationship("VideoMeeting", back_populates="integration")

    def is_token_expired(self) -> bool:
        """Check if access token is expired."""
        if not self.token_expires_at:
            return False
        return datetime.utcnow() >= self.token_expires_at

    def needs_refresh(self) -> bool:
        """Check if token needs refresh (within 5 minutes of expiry)."""
        if not self.token_expires_at:
            return False
        return datetime.utcnow() >= (self.token_expires_at - timedelta(minutes=5))


class CalendarEvent(Base):
    """
    Synced calendar event.

    Stores events from external calendar providers.
    """
    __tablename__ = "calendar_events"
    __table_args__ = {'extend_existing': True}

    # Primary Key
    id = Column(Integer, primary_key=True, index=True)

    # Integration
    integration_id = Column(Integer, ForeignKey("integrations.id"), nullable=False, index=True)

    # Owner
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)

    # External IDs
    external_id = Column(String(255), nullable=False, index=True)
    external_calendar_id = Column(String(255), nullable=True)

    # Event Details
    title = Column(String(500), nullable=False)
    description = Column(Text, nullable=True)
    location = Column(String(500), nullable=True)

    # Timing
    start_time = Column(DateTime, nullable=False, index=True)
    end_time = Column(DateTime, nullable=False, index=True)
    timezone = Column(String(100), nullable=True)
    is_all_day = Column(Boolean, default=False)

    # Recurrence
    is_recurring = Column(Boolean, default=False)
    recurrence_rule = Column(Text, nullable=True)  # iCal RRULE format

    # Attendees
    attendees = Column(JSON, default=list)  # List of attendee emails
    organizer_email = Column(String(255), nullable=True)

    # Status
    status = Column(String(50), default="confirmed")  # confirmed, tentative, cancelled
    visibility = Column(String(50), default="default")  # public, private, default

    # Links
    meeting_url = Column(String(500), nullable=True)
    html_link = Column(String(500), nullable=True)

    # Sync
    last_synced_at = Column(DateTime, default=datetime.utcnow)

    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    integration = relationship("Integration", back_populates="calendar_events")
    user = relationship("User", foreign_keys=[user_id])


class VideoMeeting(Base):
    """
    Video conference meeting.

    Stores video meeting links and details.
    """
    __tablename__ = "video_meetings"
    __table_args__ = {'extend_existing': True}

    # Primary Key
    id = Column(Integer, primary_key=True, index=True)

    # Integration
    integration_id = Column(Integer, ForeignKey("integrations.id"), nullable=False, index=True)

    # Related Resources
    interview_id = Column(Integer, ForeignKey("interviews.id"), nullable=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    company_id = Column(Integer, ForeignKey("companies.id"), nullable=True, index=True)

    # External IDs
    external_meeting_id = Column(String(255), nullable=False, unique=True, index=True)

    # Meeting Details
    meeting_title = Column(String(500), nullable=False)
    meeting_url = Column(String(1000), nullable=False)
    join_url = Column(String(1000), nullable=False)
    start_url = Column(String(1000), nullable=True)  # Host start URL

    # Timing
    scheduled_start = Column(DateTime, nullable=False, index=True)
    scheduled_end = Column(DateTime, nullable=False)
    duration_minutes = Column(Integer, nullable=False)

    # Access
    meeting_password = Column(String(255), nullable=True)
    waiting_room_enabled = Column(Boolean, default=False)

    # Participants
    host_email = Column(String(255), nullable=False)
    participants = Column(JSON, default=list)  # List of participant emails

    # Settings
    provider = Column(SQLEnum(IntegrationProvider), nullable=False)
    settings = Column(JSON, default=dict)  # Provider-specific settings

    # Status
    status = Column(String(50), default="scheduled", index=True)  # scheduled, started, ended, cancelled
    actual_start_time = Column(DateTime, nullable=True)
    actual_end_time = Column(DateTime, nullable=True)

    # Recording
    recording_enabled = Column(Boolean, default=False)
    recording_urls = Column(JSON, default=list)  # List of recording URLs

    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    integration = relationship("Integration", back_populates="video_meetings")
    interview = relationship("Interview")
    user = relationship("User", foreign_keys=[user_id])
    company = relationship("CompanyLegacy", foreign_keys=[company_id])


class ATSSync(Base):
    """
    ATS (Applicant Tracking System) synchronization log.

    Tracks sync operations with external ATS systems.
    """
    __tablename__ = "ats_syncs"
    __table_args__ = {'extend_existing': True}

    # Primary Key
    id = Column(Integer, primary_key=True, index=True)

    # Integration
    integration_id = Column(Integer, ForeignKey("integrations.id"), nullable=False, index=True)
    company_id = Column(Integer, ForeignKey("companies.id"), nullable=False, index=True)

    # Sync Details
    sync_type = Column(String(50), nullable=False, index=True)  # full, incremental
    sync_direction = Column(String(50), nullable=False)  # import, export, bidirectional

    # Resources Synced
    jobs_synced = Column(Integer, default=0)
    applications_synced = Column(Integer, default=0)
    candidates_synced = Column(Integer, default=0)

    # Status
    status = Column(String(50), default="pending", index=True)  # pending, running, completed, failed
    started_at = Column(DateTime, nullable=True)
    completed_at = Column(DateTime, nullable=True)

    # Results
    success_count = Column(Integer, default=0)
    error_count = Column(Integer, default=0)
    errors = Column(JSON, default=list)  # List of error messages

    # Metadata
    extra_data = Column(JSON, default=dict)

    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow, index=True)

    # Relationships
    integration = relationship("Integration")
    company = relationship("CompanyLegacy", foreign_keys=[company_id])


class CommunicationLog(Base):
    """
    External communication log.

    Tracks emails, messages, and SMS sent through integrations.
    """
    __tablename__ = "communication_logs"
    __table_args__ = {'extend_existing': True}

    # Primary Key
    id = Column(Integer, primary_key=True, index=True)

    # Integration
    integration_id = Column(Integer, ForeignKey("integrations.id"), nullable=False, index=True)

    # Communication Details
    communication_type = Column(String(50), nullable=False, index=True)  # email, sms, slack
    provider = Column(SQLEnum(IntegrationProvider), nullable=False)

    # Recipients
    recipient_email = Column(String(255), nullable=True, index=True)
    recipient_phone = Column(String(50), nullable=True)
    recipient_user_id = Column(Integer, ForeignKey("users.id"), nullable=True, index=True)

    # Sender
    sender_email = Column(String(255), nullable=True)
    sender_user_id = Column(Integer, ForeignKey("users.id"), nullable=True, index=True)

    # Content
    subject = Column(String(500), nullable=True)
    body = Column(Text, nullable=True)
    template_id = Column(String(255), nullable=True)

    # External IDs
    external_id = Column(String(255), nullable=True, unique=True, index=True)
    external_thread_id = Column(String(255), nullable=True)

    # Status
    status = Column(String(50), default="pending", index=True)  # pending, sent, delivered, failed, bounced
    sent_at = Column(DateTime, nullable=True)
    delivered_at = Column(DateTime, nullable=True)
    opened_at = Column(DateTime, nullable=True)
    clicked_at = Column(DateTime, nullable=True)
    failed_at = Column(DateTime, nullable=True)

    # Error Info
    error_message = Column(Text, nullable=True)

    # Metadata
    extra_data = Column(JSON, default=dict)

    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow, index=True)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    integration = relationship("Integration")
    recipient_user = relationship("User", foreign_keys=[recipient_user_id])
    sender_user = relationship("User", foreign_keys=[sender_user_id])


class BackgroundCheck(Base):
    """
    Background check request and results.

    Tracks background check orders through integration providers.
    """
    __tablename__ = "background_checks"
    __table_args__ = {'extend_existing': True}

    # Primary Key
    id = Column(Integer, primary_key=True, index=True)

    # Integration
    integration_id = Column(Integer, ForeignKey("integrations.id"), nullable=False, index=True)

    # Subject
    application_id = Column(Integer, ForeignKey("applications.id"), nullable=False, index=True)
    candidate_user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    company_id = Column(Integer, ForeignKey("companies.id"), nullable=False, index=True)

    # External IDs
    external_check_id = Column(String(255), nullable=False, unique=True, index=True)

    # Check Details
    provider = Column(SQLEnum(IntegrationProvider), nullable=False)
    package_name = Column(String(255), nullable=False)  # Type of background check
    checks_requested = Column(JSON, default=list)  # List of check types

    # Candidate Info (as submitted)
    first_name = Column(String(255), nullable=False)
    last_name = Column(String(255), nullable=False)
    email = Column(String(255), nullable=False)
    phone = Column(String(50), nullable=True)
    date_of_birth = Column(String(10), nullable=True)  # YYYY-MM-DD
    ssn_last4 = Column(String(4), nullable=True)

    # Status
    status = Column(String(50), default="pending", index=True)  # pending, processing, completed, disputed, cancelled
    result = Column(String(50), nullable=True, index=True)  # clear, consider, suspended

    # Timing
    ordered_at = Column(DateTime, default=datetime.utcnow)
    completed_at = Column(DateTime, nullable=True)
    expires_at = Column(DateTime, nullable=True)

    # Results
    report_url = Column(String(1000), nullable=True)
    results = Column(JSON, default=dict)  # Detailed results by check type

    # Adjudication
    reviewed_by_user_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    reviewed_at = Column(DateTime, nullable=True)
    adjudication_notes = Column(Text, nullable=True)

    # Metadata
    extra_data = Column(JSON, default=dict)

    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow, index=True)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    integration = relationship("Integration")
    application = relationship("Application")
    candidate_user = relationship("User", foreign_keys=[candidate_user_id])
    company = relationship("CompanyLegacy", foreign_keys=[company_id])
    reviewed_by = relationship("User", foreign_keys=[reviewed_by_user_id])


class LinkedInProfile(Base):
    """
    LinkedIn profile data.

    Stores LinkedIn profile information from integration.
    """
    __tablename__ = "linkedin_profiles"
    __table_args__ = {'extend_existing': True}

    # Primary Key
    id = Column(Integer, primary_key=True, index=True)

    # Integration
    integration_id = Column(Integer, ForeignKey("integrations.id"), nullable=False, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, unique=True, index=True)

    # LinkedIn IDs
    linkedin_id = Column(String(255), nullable=False, unique=True, index=True)
    public_profile_url = Column(String(500), nullable=True)

    # Profile Data
    profile_data = Column(JSON, default=dict)  # Full profile data from LinkedIn

    # Basic Info
    first_name = Column(String(255), nullable=True)
    last_name = Column(String(255), nullable=True)
    headline = Column(String(500), nullable=True)
    summary = Column(Text, nullable=True)
    location = Column(String(255), nullable=True)

    # Profile Picture
    profile_picture_url = Column(String(1000), nullable=True)

    # Sync
    last_synced_at = Column(DateTime, default=datetime.utcnow)

    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    integration = relationship("Integration")
    user = relationship("User", foreign_keys=[user_id])


class WebhookEndpoint(Base):
    """
    Webhook endpoint for receiving events from integrations.

    Tracks registered webhooks and their events.
    """
    __tablename__ = "webhook_endpoints"
    __table_args__ = {'extend_existing': True}

    # Primary Key
    id = Column(Integer, primary_key=True, index=True)

    # Integration
    integration_id = Column(Integer, ForeignKey("integrations.id"), nullable=False, index=True)

    # Endpoint Details
    url = Column(String(1000), nullable=False)
    secret = Column(String(255), nullable=False)  # For signature verification

    # Events
    enabled_events = Column(JSON, default=list)  # List of event types to receive

    # External IDs
    external_webhook_id = Column(String(255), nullable=True)

    # Status
    is_active = Column(Boolean, default=True)
    last_success_at = Column(DateTime, nullable=True)
    last_failure_at = Column(DateTime, nullable=True)
    consecutive_failures = Column(Integer, default=0)

    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    integration = relationship("Integration")
    events = relationship("WebhookEvent", back_populates="endpoint")


class WebhookEvent(Base):
    """
    Webhook event log.

    Tracks all webhook events received from integrations.
    """
    __tablename__ = "webhook_events"
    __table_args__ = {'extend_existing': True}

    # Primary Key
    id = Column(Integer, primary_key=True, index=True)

    # Endpoint
    endpoint_id = Column(Integer, ForeignKey("webhook_endpoints.id"), nullable=False, index=True)
    integration_id = Column(Integer, ForeignKey("integrations.id"), nullable=False, index=True)

    # Event Details
    event_type = Column(String(100), nullable=False, index=True)
    event_id = Column(String(255), nullable=True, unique=True, index=True)

    # Payload
    payload = Column(JSON, nullable=False)

    # Processing
    processed = Column(Boolean, default=False, index=True)
    processed_at = Column(DateTime, nullable=True)
    processing_error = Column(Text, nullable=True)

    # Request Details
    request_headers = Column(JSON, default=dict)
    signature_verified = Column(Boolean, default=False)

    # Timestamps
    received_at = Column(DateTime, default=datetime.utcnow, index=True)

    # Relationships
    endpoint = relationship("WebhookEndpoint", back_populates="events")
    integration = relationship("Integration")
