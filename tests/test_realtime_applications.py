"""
Tests for Realtime Application Service - Phase 11

Tests WebSocket broadcasting for application status updates.
"""

import pytest
from datetime import datetime, timedelta
from unittest.mock import AsyncMock, MagicMock, patch
from typing import List, Dict

from src.networking_ai.services.realtime_application_service import (
    RealtimeApplicationService,
    get_realtime_application_service,
)
from src.networking_ai.websocket.application_events import (
    ApplicationStatusChangedEvent,
    RecruiterViewedEvent,
    InterviewScheduledEvent,
    InterviewReminderEvent,
    OfferExtendedEvent,
    OfferUpdatedEvent,
    FeedbackReceivedEvent,
    TimelineUpdatedEvent,
    MessageReceivedEvent,
)


@pytest.fixture
def mock_connection_manager():
    """Mock connection manager for testing."""
    manager = MagicMock()
    manager.send_to_user = AsyncMock()
    return manager


@pytest.fixture
def app_service(mock_connection_manager):
    """Create RealtimeApplicationService instance for testing."""
    return RealtimeApplicationService(mock_connection_manager)


class TestApplicationEvents:
    """Test application event models."""

    def test_status_changed_event_creation(self):
        """Test ApplicationStatusChangedEvent model creation."""
        event = ApplicationStatusChangedEvent(
            application_id=123,
            job_id=456,
            job_title="Senior Python Developer",
            company_name="TechCorp",
            company_logo="https://example.com/logo.png",
            old_status="applied",
            new_status="under_review",
            status_display="Under Review",
            message="Great news! Your application is now under review",
            next_steps=["Review by hiring team", "Possible phone screen"],
            days_since_applied=2,
            estimated_decision_days=7,
            action_url="/applications/123",
        )

        assert event.event == "application.status_changed"
        assert event.application_id == 123
        assert event.new_status == "under_review"
        assert len(event.next_steps) == 2

    def test_recruiter_viewed_event_creation(self):
        """Test RecruiterViewedEvent model creation."""
        event = RecruiterViewedEvent(
            application_id=123,
            job_id=456,
            job_title="Senior Python Developer",
            company_name="TechCorp",
            recruiter_name="Sarah Johnson",
            recruiter_title="Senior Technical Recruiter",
            view_duration_seconds=180,
            sections_viewed=["Resume", "Portfolio", "Skills"],
            message="Sarah Johnson viewed your application",
            action_url="/applications/123",
        )

        assert event.event == "application.recruiter_viewed"
        assert event.recruiter_name == "Sarah Johnson"
        assert event.view_duration_seconds == 180
        assert len(event.sections_viewed) == 3

    def test_interview_scheduled_event_creation(self):
        """Test InterviewScheduledEvent model creation."""
        scheduled_at = datetime.utcnow() + timedelta(days=7)

        event = InterviewScheduledEvent(
            application_id=123,
            interview_id=1,
            job_id=456,
            job_title="Senior Python Developer",
            company_name="TechCorp",
            interview_type="video",
            interview_round=1,
            scheduled_at=scheduled_at,
            duration_minutes=60,
            video_link="https://zoom.us/j/123456789",
            interviewer_names=["John Smith", "Jane Doe"],
            interviewer_titles=["Engineering Manager", "Senior Engineer"],
            preparation_notes="Review our tech stack",
            topics_to_cover=["System design", "Python coding"],
            message="Interview scheduled",
            action_url="/applications/123/interviews/1",
            calendar_link="/applications/123/interviews/1/calendar",
        )

        assert event.event == "application.interview_scheduled"
        assert event.interview_type == "video"
        assert event.duration_minutes == 60
        assert len(event.interviewer_names) == 2

    def test_interview_reminder_event_creation(self):
        """Test InterviewReminderEvent model creation."""
        scheduled_at = datetime.utcnow() + timedelta(hours=1)

        event = InterviewReminderEvent(
            application_id=123,
            interview_id=1,
            job_title="Senior Python Developer",
            company_name="TechCorp",
            interview_type="video",
            scheduled_at=scheduled_at,
            hours_until_interview=1,
            video_link="https://zoom.us/j/123456789",
            message="Interview in 1 hour!",
            action_url="/applications/123/interviews/1",
        )

        assert event.event == "application.interview_reminder"
        assert event.hours_until_interview == 1
        assert event.video_link is not None

    def test_offer_extended_event_creation(self):
        """Test OfferExtendedEvent model creation."""
        expires_at = datetime.utcnow() + timedelta(days=7)
        start_date = datetime.utcnow() + timedelta(days=30)

        event = OfferExtendedEvent(
            application_id=123,
            offer_id=1,
            job_id=456,
            job_title="Senior Python Developer",
            company_name="TechCorp",
            company_logo="https://example.com/logo.png",
            salary=150000,
            salary_currency="USD",
            salary_formatted="$150,000/year",
            signing_bonus=10000,
            equity_value=50000,
            benefits_summary=["Health insurance", "401k match", "Unlimited PTO"],
            offer_expires_at=expires_at,
            days_to_decide=7,
            start_date=start_date,
            message="Congratulations! Job offer extended",
            action_url="/applications/123/offer",
            accept_url="/applications/123/offer/accept",
            negotiate_url="/applications/123/offer/negotiate",
        )

        assert event.event == "application.offer_extended"
        assert event.salary == 150000
        assert event.days_to_decide == 7
        assert len(event.benefits_summary) == 3

    def test_offer_updated_event_creation(self):
        """Test OfferUpdatedEvent model creation."""
        event = OfferUpdatedEvent(
            application_id=123,
            offer_id=1,
            job_title="Senior Python Developer",
            company_name="TechCorp",
            updated_fields=["salary", "signing_bonus"],
            update_summary="Salary increased to $160k",
            new_salary=160000,
            new_signing_bonus=15000,
            message="Offer has been updated",
            action_url="/applications/123/offer",
        )

        assert event.event == "application.offer_updated"
        assert "salary" in event.updated_fields
        assert event.new_salary == 160000

    def test_feedback_received_event_creation(self):
        """Test FeedbackReceivedEvent model creation."""
        event = FeedbackReceivedEvent(
            application_id=123,
            job_title="Senior Python Developer",
            company_name="TechCorp",
            feedback_type="interview",
            feedback_stage="technical",
            feedback_summary="Strong technical skills",
            strengths=["Excellent Python knowledge", "Clear communication"],
            areas_to_improve=["Scalability considerations"],
            overall_sentiment="positive",
            message="You've received feedback",
            action_url="/applications/123/feedback",
        )

        assert event.event == "application.feedback_received"
        assert event.overall_sentiment == "positive"
        assert len(event.strengths) == 2

    def test_timeline_updated_event_creation(self):
        """Test TimelineUpdatedEvent model creation."""
        expected_update = datetime.utcnow() + timedelta(days=3)

        event = TimelineUpdatedEvent(
            application_id=123,
            job_title="Senior Python Developer",
            company_name="TechCorp",
            current_stage="technical_interview",
            completed_stages=["applied", "phone_screen"],
            upcoming_stages=["final_interview", "offer"],
            next_step="Final round interview",
            expected_next_update=expected_update,
            days_until_next_step=3,
            message="Timeline updated",
            action_url="/applications/123/timeline",
        )

        assert event.event == "application.timeline_updated"
        assert event.current_stage == "technical_interview"
        assert len(event.completed_stages) == 2

    def test_message_received_event_creation(self):
        """Test MessageReceivedEvent model creation."""
        event = MessageReceivedEvent(
            application_id=123,
            message_id=1,
            job_title="Senior Python Developer",
            company_name="TechCorp",
            sender_name="Sarah Johnson",
            sender_title="Senior Technical Recruiter",
            sender_avatar="https://example.com/avatar.jpg",
            subject="Question about availability",
            message_preview="Hi! I wanted to check if you'd be available...",
            priority="normal",
            action_url="/applications/123/messages/1",
            reply_url="/applications/123/messages/1/reply",
        )

        assert event.event == "application.message_received"
        assert event.sender_name == "Sarah Johnson"
        assert event.priority == "normal"


class TestRealtimeApplicationService:
    """Test RealtimeApplicationService broadcasting."""

    @pytest.mark.asyncio
    async def test_broadcast_status_changed(self, app_service, mock_connection_manager):
        """Test broadcasting status change to user."""
        result = await app_service.broadcast_status_changed(
            user_id=1,
            application_id=123,
            job_id=456,
            job_title="Senior Python Developer",
            company_name="TechCorp",
            old_status="applied",
            new_status="under_review",
            status_display="Under Review",
            message="Great news! Your application is now under review",
            days_since_applied=2,
            next_steps=["Review by hiring team", "Possible phone screen"],
            estimated_decision_days=7,
        )

        assert result is True
        mock_connection_manager.send_to_user.assert_called_once()

        # Verify event content
        call = mock_connection_manager.send_to_user.call_args
        assert call[1]["user_id"] == 1
        message = call[1]["message"]
        assert message["event"] == "application.status_changed"
        assert message["new_status"] == "under_review"
        assert message["days_since_applied"] == 2

    @pytest.mark.asyncio
    async def test_broadcast_recruiter_viewed(self, app_service, mock_connection_manager):
        """Test broadcasting recruiter viewed notification."""
        result = await app_service.broadcast_recruiter_viewed(
            user_id=1,
            application_id=123,
            job_id=456,
            job_title="Senior Python Developer",
            company_name="TechCorp",
            recruiter_name="Sarah Johnson",
            recruiter_title="Senior Technical Recruiter",
            view_duration_seconds=180,
            sections_viewed=["Resume", "Portfolio"],
        )

        assert result is True
        mock_connection_manager.send_to_user.assert_called_once()

        # Verify event content
        call = mock_connection_manager.send_to_user.call_args
        message = call[1]["message"]
        assert message["event"] == "application.recruiter_viewed"
        assert message["recruiter_name"] == "Sarah Johnson"
        assert message["view_duration_seconds"] == 180

    @pytest.mark.asyncio
    async def test_broadcast_interview_scheduled(self, app_service, mock_connection_manager):
        """Test broadcasting interview scheduled notification."""
        scheduled_at = datetime.utcnow() + timedelta(days=7)

        result = await app_service.broadcast_interview_scheduled(
            user_id=1,
            application_id=123,
            interview_id=1,
            job_id=456,
            job_title="Senior Python Developer",
            company_name="TechCorp",
            interview_type="video",
            interview_round=1,
            scheduled_at=scheduled_at,
            duration_minutes=60,
            video_link="https://zoom.us/j/123456789",
            interviewer_names=["John Smith"],
            interviewer_titles=["Engineering Manager"],
        )

        assert result is True
        mock_connection_manager.send_to_user.assert_called_once()

        # Verify event content
        call = mock_connection_manager.send_to_user.call_args
        message = call[1]["message"]
        assert message["event"] == "application.interview_scheduled"
        assert message["interview_type"] == "video"
        assert message["duration_minutes"] == 60

    @pytest.mark.asyncio
    async def test_broadcast_interview_reminder(self, app_service, mock_connection_manager):
        """Test broadcasting interview reminder."""
        scheduled_at = datetime.utcnow() + timedelta(hours=1)

        result = await app_service.broadcast_interview_reminder(
            user_id=1,
            application_id=123,
            interview_id=1,
            job_title="Senior Python Developer",
            company_name="TechCorp",
            interview_type="video",
            scheduled_at=scheduled_at,
            hours_until_interview=1,
            video_link="https://zoom.us/j/123456789",
        )

        assert result is True
        mock_connection_manager.send_to_user.assert_called_once()

        # Verify event content
        call = mock_connection_manager.send_to_user.call_args
        message = call[1]["message"]
        assert message["event"] == "application.interview_reminder"
        assert message["hours_until_interview"] == 1

    @pytest.mark.asyncio
    async def test_broadcast_offer_extended(self, app_service, mock_connection_manager):
        """Test broadcasting job offer extended."""
        expires_at = datetime.utcnow() + timedelta(days=7)
        start_date = datetime.utcnow() + timedelta(days=30)

        result = await app_service.broadcast_offer_extended(
            user_id=1,
            application_id=123,
            offer_id=1,
            job_id=456,
            job_title="Senior Python Developer",
            company_name="TechCorp",
            salary=150000,
            offer_expires_at=expires_at,
            days_to_decide=7,
            signing_bonus=10000,
            equity_value=50000,
            benefits_summary=["Health insurance", "401k"],
            start_date=start_date,
        )

        assert result is True
        mock_connection_manager.send_to_user.assert_called_once()

        # Verify event content
        call = mock_connection_manager.send_to_user.call_args
        message = call[1]["message"]
        assert message["event"] == "application.offer_extended"
        assert message["salary"] == 150000
        assert message["days_to_decide"] == 7

    @pytest.mark.asyncio
    async def test_broadcast_offer_updated(self, app_service, mock_connection_manager):
        """Test broadcasting offer update."""
        result = await app_service.broadcast_offer_updated(
            user_id=1,
            application_id=123,
            offer_id=1,
            job_title="Senior Python Developer",
            company_name="TechCorp",
            updated_fields=["salary", "signing_bonus"],
            update_summary="Salary increased to $160k",
            new_salary=160000,
            new_signing_bonus=15000,
        )

        assert result is True
        mock_connection_manager.send_to_user.assert_called_once()

        # Verify event content
        call = mock_connection_manager.send_to_user.call_args
        message = call[1]["message"]
        assert message["event"] == "application.offer_updated"
        assert message["new_salary"] == 160000

    @pytest.mark.asyncio
    async def test_broadcast_feedback_received(self, app_service, mock_connection_manager):
        """Test broadcasting feedback received."""
        result = await app_service.broadcast_feedback_received(
            user_id=1,
            application_id=123,
            job_title="Senior Python Developer",
            company_name="TechCorp",
            feedback_type="interview",
            feedback_stage="technical",
            feedback_summary="Strong technical skills",
            overall_sentiment="positive",
            strengths=["Excellent Python knowledge"],
            areas_to_improve=["Scalability"],
        )

        assert result is True
        mock_connection_manager.send_to_user.assert_called_once()

        # Verify event content
        call = mock_connection_manager.send_to_user.call_args
        message = call[1]["message"]
        assert message["event"] == "application.feedback_received"
        assert message["overall_sentiment"] == "positive"

    @pytest.mark.asyncio
    async def test_broadcast_timeline_updated(self, app_service, mock_connection_manager):
        """Test broadcasting timeline update."""
        expected_update = datetime.utcnow() + timedelta(days=3)

        result = await app_service.broadcast_timeline_updated(
            user_id=1,
            application_id=123,
            job_title="Senior Python Developer",
            company_name="TechCorp",
            current_stage="technical_interview",
            completed_stages=["applied", "phone_screen"],
            upcoming_stages=["final_interview", "offer"],
            next_step="Final round interview",
            expected_next_update=expected_update,
            days_until_next_step=3,
        )

        assert result is True
        mock_connection_manager.send_to_user.assert_called_once()

        # Verify event content
        call = mock_connection_manager.send_to_user.call_args
        message = call[1]["message"]
        assert message["event"] == "application.timeline_updated"
        assert message["current_stage"] == "technical_interview"

    @pytest.mark.asyncio
    async def test_broadcast_message_received(self, app_service, mock_connection_manager):
        """Test broadcasting message received."""
        result = await app_service.broadcast_message_received(
            user_id=1,
            application_id=123,
            message_id=1,
            job_title="Senior Python Developer",
            company_name="TechCorp",
            sender_name="Sarah Johnson",
            sender_title="Senior Technical Recruiter",
            subject="Question about availability",
            message_preview="Hi! I wanted to check if you'd be available...",
            priority="normal",
        )

        assert result is True
        mock_connection_manager.send_to_user.assert_called_once()

        # Verify event content
        call = mock_connection_manager.send_to_user.call_args
        message = call[1]["message"]
        assert message["event"] == "application.message_received"
        assert message["sender_name"] == "Sarah Johnson"


class TestRealtimeApplicationServiceIntegration:
    """Test RealtimeApplicationService integration scenarios."""

    @pytest.mark.asyncio
    async def test_complete_application_lifecycle(self, app_service, mock_connection_manager):
        """Test complete application lifecycle from applied to offer."""
        user_id = 1
        application_id = 123
        job_id = 456
        job_title = "Senior Python Developer"
        company_name = "TechCorp"

        # 1. Status changed: applied -> under_review
        await app_service.broadcast_status_changed(
            user_id=user_id,
            application_id=application_id,
            job_id=job_id,
            job_title=job_title,
            company_name=company_name,
            old_status="applied",
            new_status="under_review",
            status_display="Under Review",
            message="Application under review",
            days_since_applied=2,
        )

        # 2. Recruiter viewed
        await app_service.broadcast_recruiter_viewed(
            user_id=user_id,
            application_id=application_id,
            job_id=job_id,
            job_title=job_title,
            company_name=company_name,
            recruiter_name="Sarah Johnson",
        )

        # 3. Interview scheduled
        scheduled_at = datetime.utcnow() + timedelta(days=7)
        await app_service.broadcast_interview_scheduled(
            user_id=user_id,
            application_id=application_id,
            interview_id=1,
            job_id=job_id,
            job_title=job_title,
            company_name=company_name,
            interview_type="video",
            interview_round=1,
            scheduled_at=scheduled_at,
            duration_minutes=60,
        )

        # 4. Interview reminder
        await app_service.broadcast_interview_reminder(
            user_id=user_id,
            application_id=application_id,
            interview_id=1,
            job_title=job_title,
            company_name=company_name,
            interview_type="video",
            scheduled_at=scheduled_at,
            hours_until_interview=1,
        )

        # 5. Feedback received
        await app_service.broadcast_feedback_received(
            user_id=user_id,
            application_id=application_id,
            job_title=job_title,
            company_name=company_name,
            feedback_type="interview",
            feedback_stage="technical",
            feedback_summary="Strong performance",
            overall_sentiment="positive",
        )

        # 6. Offer extended
        expires_at = datetime.utcnow() + timedelta(days=7)
        await app_service.broadcast_offer_extended(
            user_id=user_id,
            application_id=application_id,
            offer_id=1,
            job_id=job_id,
            job_title=job_title,
            company_name=company_name,
            salary=150000,
            offer_expires_at=expires_at,
            days_to_decide=7,
        )

        # All 6 events should be sent
        assert mock_connection_manager.send_to_user.call_count == 6

    @pytest.mark.asyncio
    async def test_interview_scheduling_workflow(self, app_service, mock_connection_manager):
        """Test interview scheduling and reminder workflow."""
        user_id = 1
        application_id = 123
        interview_id = 1
        scheduled_at = datetime.utcnow() + timedelta(days=7)

        # Schedule interview
        await app_service.broadcast_interview_scheduled(
            user_id=user_id,
            application_id=application_id,
            interview_id=interview_id,
            job_id=456,
            job_title="Senior Python Developer",
            company_name="TechCorp",
            interview_type="video",
            interview_round=1,
            scheduled_at=scheduled_at,
            duration_minutes=60,
            video_link="https://zoom.us/j/123456789",
        )

        # 24-hour reminder
        await app_service.broadcast_interview_reminder(
            user_id=user_id,
            application_id=application_id,
            interview_id=interview_id,
            job_title="Senior Python Developer",
            company_name="TechCorp",
            interview_type="video",
            scheduled_at=scheduled_at,
            hours_until_interview=24,
        )

        # 1-hour reminder
        await app_service.broadcast_interview_reminder(
            user_id=user_id,
            application_id=application_id,
            interview_id=interview_id,
            job_title="Senior Python Developer",
            company_name="TechCorp",
            interview_type="video",
            scheduled_at=scheduled_at,
            hours_until_interview=1,
        )

        assert mock_connection_manager.send_to_user.call_count == 3

    @pytest.mark.asyncio
    async def test_offer_negotiation_workflow(self, app_service, mock_connection_manager):
        """Test offer extended and negotiation workflow."""
        user_id = 1
        application_id = 123
        offer_id = 1
        expires_at = datetime.utcnow() + timedelta(days=7)

        # Initial offer
        await app_service.broadcast_offer_extended(
            user_id=user_id,
            application_id=application_id,
            offer_id=offer_id,
            job_id=456,
            job_title="Senior Python Developer",
            company_name="TechCorp",
            salary=150000,
            offer_expires_at=expires_at,
            days_to_decide=7,
            signing_bonus=10000,
        )

        # Offer updated after negotiation
        await app_service.broadcast_offer_updated(
            user_id=user_id,
            application_id=application_id,
            offer_id=offer_id,
            job_title="Senior Python Developer",
            company_name="TechCorp",
            updated_fields=["salary", "signing_bonus"],
            update_summary="Improved terms after negotiation",
            new_salary=160000,
            new_signing_bonus=15000,
        )

        assert mock_connection_manager.send_to_user.call_count == 2


class TestHelperFunctions:
    """Test helper functions."""

    def test_get_realtime_application_service(self, mock_connection_manager):
        """Test get_realtime_application_service helper function."""
        service = get_realtime_application_service(mock_connection_manager)

        assert isinstance(service, RealtimeApplicationService)
        assert service.connection_manager == mock_connection_manager
