"""
Tests for Realtime Job Service - Phase 11

Tests WebSocket broadcasting for job feed events.
"""

import pytest
from datetime import datetime, timedelta
from unittest.mock import AsyncMock, MagicMock, patch
from typing import List, Dict

from src.networking_ai.services.realtime_job_service import (
    RealtimeJobService,
    get_realtime_job_service,
)
from src.networking_ai.websocket.job_events import (
    JobPostedEvent,
    JobUpdatedEvent,
    JobClosedEvent,
    JobExpiringEvent,
    JobMatchedEvent,
    JobSubscriptionCreatedEvent,
    JobSubscriptionDeletedEvent,
    JobFeedUpdateEvent,
)


@pytest.fixture
def mock_connection_manager():
    """Mock connection manager for testing."""
    manager = MagicMock()
    manager.send_to_user = AsyncMock()
    manager.broadcast_to_users = AsyncMock()
    return manager


@pytest.fixture
def job_service(mock_connection_manager):
    """Create RealtimeJobService instance for testing."""
    return RealtimeJobService(mock_connection_manager)


class TestJobEvents:
    """Test job event models."""

    def test_job_posted_event_creation(self):
        """Test JobPostedEvent model creation."""
        event = JobPostedEvent(
            job_id=123,
            title="Senior Python Developer",
            company_name="TechCorp",
            company_logo="https://example.com/logo.png",
            location="San Francisco, CA",
            remote_type="hybrid",
            salary_min=120000,
            salary_max=180000,
            salary_currency="USD",
            salary_range="$120k-$180k",
            skills=["Python", "Django", "PostgreSQL"],
            experience_min=3,
            experience_max=7,
            match_score=0.92,
            match_reasons=["Skills match", "Location match"],
            description_preview="We're looking for...",
            job_type="full_time",
            action_url="/jobs/123",
            quick_apply=True,
        )

        assert event.event == "job.posted"
        assert event.job_id == 123
        assert event.title == "Senior Python Developer"
        assert event.match_score == 0.92
        assert len(event.skills) == 3
        assert event.quick_apply is True

    def test_job_updated_event_creation(self):
        """Test JobUpdatedEvent model creation."""
        event = JobUpdatedEvent(
            job_id=123,
            title="Senior Python Developer",
            company_name="TechCorp",
            updated_fields=["salary_range", "remote_type"],
            update_summary="Salary increased, now fully remote",
            location="Remote",
            remote_type="remote",
            salary_range="$130k-$190k",
            action_url="/jobs/123",
        )

        assert event.event == "job.updated"
        assert event.job_id == 123
        assert "salary_range" in event.updated_fields
        assert event.remote_type == "remote"

    def test_job_closed_event_creation(self):
        """Test JobClosedEvent model creation."""
        event = JobClosedEvent(
            job_id=123,
            title="Senior Python Developer",
            company_name="TechCorp",
            reason="filled",
            message="Position has been filled",
            similar_jobs=[124, 125, 126],
            action_url="/jobs/search?similar_to=123",
        )

        assert event.event == "job.closed"
        assert event.reason == "filled"
        assert len(event.similar_jobs) == 3

    def test_job_expiring_event_creation(self):
        """Test JobExpiringEvent model creation."""
        expires_at = datetime.utcnow() + timedelta(hours=24)

        event = JobExpiringEvent(
            job_id=123,
            title="Senior Python Developer",
            company_name="TechCorp",
            expires_in_hours=24,
            expires_at=expires_at,
            message="Job expires in 24 hours!",
            action_url="/jobs/123/apply",
            quick_apply=True,
        )

        assert event.event == "job.expiring"
        assert event.expires_in_hours == 24
        assert event.quick_apply is True

    def test_job_matched_event_creation(self):
        """Test JobMatchedEvent model creation."""
        event = JobMatchedEvent(
            job_id=125,
            title="Lead Backend Engineer",
            company_name="StartupXYZ",
            company_logo="https://example.com/logo.png",
            match_score=0.95,
            match_quality="excellent",
            match_reasons=["Backend expertise", "Leadership experience"],
            location="Remote",
            remote_type="remote",
            salary_range="$150k-$200k",
            skills=["Python", "Microservices", "Kubernetes"],
            description_preview="Lead our backend team...",
            action_url="/jobs/125",
            quick_apply=True,
        )

        assert event.event == "job.matched"
        assert event.match_score == 0.95
        assert event.match_quality == "excellent"
        assert len(event.match_reasons) == 2

    def test_job_subscription_created_event(self):
        """Test JobSubscriptionCreatedEvent model creation."""
        event = JobSubscriptionCreatedEvent(
            subscription_id=42,
            keywords=["Python", "Backend"],
            locations=["San Francisco", "Remote"],
            remote_types=["remote", "hybrid"],
            skills=["Python", "Django"],
            salary_min=120000,
            frequency="instant",
            message="You'll receive instant notifications!",
        )

        assert event.event == "job.subscription.created"
        assert event.subscription_id == 42
        assert event.frequency == "instant"
        assert len(event.keywords) == 2

    def test_job_subscription_deleted_event(self):
        """Test JobSubscriptionDeletedEvent model creation."""
        event = JobSubscriptionDeletedEvent(
            subscription_id=42,
            message="Subscription deleted",
        )

        assert event.event == "job.subscription.deleted"
        assert event.subscription_id == 42

    def test_job_feed_update_event(self):
        """Test JobFeedUpdateEvent model creation."""
        event = JobFeedUpdateEvent(
            new_jobs_count=12,
            new_matches_count=3,
            expiring_jobs_count=2,
            top_matches=[
                {"job_id": 130, "title": "Python Dev", "company": "TechCorp", "match_score": 0.95},
                {"job_id": 131, "title": "Backend Lead", "company": "StartupXYZ", "match_score": 0.92},
            ],
            total_active_jobs=47,
            action_url="/jobs",
            message="12 new jobs posted!",
        )

        assert event.event == "job.feed.update"
        assert event.new_jobs_count == 12
        assert len(event.top_matches) == 2
        assert event.total_active_jobs == 47


class TestRealtimeJobService:
    """Test RealtimeJobService broadcasting."""

    @pytest.mark.asyncio
    async def test_broadcast_job_posted(self, job_service, mock_connection_manager):
        """Test broadcasting job posted event to matching users."""
        matched_users = [1, 2, 3]
        match_scores = {1: 0.95, 2: 0.88, 3: 0.92}
        match_reasons = {
            1: ["Perfect skill match", "Location match"],
            2: ["Good experience match"],
            3: ["Salary aligned", "Remote preference"],
        }

        count = await job_service.broadcast_job_posted(
            job_id=123,
            title="Senior Python Developer",
            company_name="TechCorp",
            location="San Francisco, CA",
            description_preview="We're looking for...",
            job_type="full_time",
            matched_user_ids=matched_users,
            remote_type="hybrid",
            salary_min=120000,
            salary_max=180000,
            salary_range="$120k-$180k",
            skills=["Python", "Django", "PostgreSQL"],
            match_scores=match_scores,
            match_reasons=match_reasons,
            quick_apply=True,
        )

        # Should notify all matched users
        assert count == 3
        assert mock_connection_manager.send_to_user.call_count == 3

        # Verify first user received correct event
        first_call = mock_connection_manager.send_to_user.call_args_list[0]
        assert first_call[1]["user_id"] == 1
        message = first_call[1]["message"]
        assert message["event"] == "job.posted"
        assert message["job_id"] == 123
        assert message["match_score"] == 0.95
        assert message["match_reasons"] == ["Perfect skill match", "Location match"]

    @pytest.mark.asyncio
    async def test_broadcast_job_posted_no_matches(self, job_service, mock_connection_manager):
        """Test broadcasting job with no matching users."""
        count = await job_service.broadcast_job_posted(
            job_id=123,
            title="Senior Python Developer",
            company_name="TechCorp",
            location="San Francisco, CA",
            description_preview="We're looking for...",
            job_type="full_time",
            matched_user_ids=[],  # No matches
        )

        assert count == 0
        mock_connection_manager.send_to_user.assert_not_called()

    @pytest.mark.asyncio
    async def test_broadcast_job_updated(self, job_service, mock_connection_manager):
        """Test broadcasting job update to interested users."""
        interested_users = [1, 2, 3]

        count = await job_service.broadcast_job_updated(
            job_id=123,
            title="Senior Python Developer",
            company_name="TechCorp",
            updated_fields=["salary_range", "remote_type"],
            update_summary="Salary increased, now fully remote",
            interested_user_ids=interested_users,
            location="Remote",
            remote_type="remote",
            salary_range="$130k-$190k",
        )

        assert count == 3
        assert mock_connection_manager.send_to_user.call_count == 3

        # Verify event content
        first_call = mock_connection_manager.send_to_user.call_args_list[0]
        message = first_call[1]["message"]
        assert message["event"] == "job.updated"
        assert "salary_range" in message["updated_fields"]
        assert message["remote_type"] == "remote"

    @pytest.mark.asyncio
    async def test_broadcast_job_closed(self, job_service, mock_connection_manager):
        """Test broadcasting job closed notification."""
        interested_users = [1, 2]
        similar_jobs = [124, 125, 126]

        count = await job_service.broadcast_job_closed(
            job_id=123,
            title="Senior Python Developer",
            company_name="TechCorp",
            reason="filled",
            message="Position has been filled",
            interested_user_ids=interested_users,
            similar_jobs=similar_jobs,
        )

        assert count == 2
        assert mock_connection_manager.send_to_user.call_count == 2

        # Verify event content
        first_call = mock_connection_manager.send_to_user.call_args_list[0]
        message = first_call[1]["message"]
        assert message["event"] == "job.closed"
        assert message["reason"] == "filled"
        assert len(message["similar_jobs"]) == 3

    @pytest.mark.asyncio
    async def test_broadcast_job_expiring(self, job_service, mock_connection_manager):
        """Test broadcasting job expiring alert."""
        saved_users = [1, 2]
        expires_at = datetime.utcnow() + timedelta(hours=24)

        count = await job_service.broadcast_job_expiring(
            job_id=123,
            title="Senior Python Developer",
            company_name="TechCorp",
            expires_in_hours=24,
            expires_at=expires_at,
            message="Job expires in 24 hours!",
            saved_by_user_ids=saved_users,
            quick_apply=True,
        )

        assert count == 2
        assert mock_connection_manager.send_to_user.call_count == 2

        # Verify event content
        first_call = mock_connection_manager.send_to_user.call_args_list[0]
        message = first_call[1]["message"]
        assert message["event"] == "job.expiring"
        assert message["expires_in_hours"] == 24
        assert message["quick_apply"] is True

    @pytest.mark.asyncio
    async def test_broadcast_job_matched(self, job_service, mock_connection_manager):
        """Test broadcasting high-quality job match to user."""
        result = await job_service.broadcast_job_matched(
            user_id=1,
            job_id=125,
            title="Lead Backend Engineer",
            company_name="StartupXYZ",
            match_score=0.95,
            match_quality="excellent",
            match_reasons=["Backend expertise", "Leadership experience", "Salary aligned"],
            location="Remote",
            remote_type="remote",
            skills=["Python", "Microservices", "Kubernetes"],
            description_preview="Lead our backend team...",
            salary_range="$150k-$200k",
            quick_apply=True,
        )

        assert result is True
        mock_connection_manager.send_to_user.assert_called_once()

        # Verify event content
        call = mock_connection_manager.send_to_user.call_args
        assert call[1]["user_id"] == 1
        message = call[1]["message"]
        assert message["event"] == "job.matched"
        assert message["match_score"] == 0.95
        assert message["match_quality"] == "excellent"
        assert len(message["match_reasons"]) == 3

    @pytest.mark.asyncio
    async def test_broadcast_subscription_created(self, job_service, mock_connection_manager):
        """Test broadcasting subscription created confirmation."""
        result = await job_service.broadcast_subscription_created(
            user_id=1,
            subscription_id=42,
            keywords=["Python", "Backend"],
            locations=["San Francisco", "Remote"],
            remote_types=["remote", "hybrid"],
            skills=["Python", "Django"],
            salary_min=120000,
            frequency="instant",
        )

        assert result is True
        mock_connection_manager.send_to_user.assert_called_once()

        # Verify event content
        call = mock_connection_manager.send_to_user.call_args
        message = call[1]["message"]
        assert message["event"] == "job.subscription.created"
        assert message["subscription_id"] == 42
        assert message["frequency"] == "instant"

    @pytest.mark.asyncio
    async def test_broadcast_subscription_created_daily(self, job_service, mock_connection_manager):
        """Test subscription created with daily frequency."""
        result = await job_service.broadcast_subscription_created(
            user_id=1,
            subscription_id=43,
            frequency="daily",
        )

        assert result is True

        # Verify daily digest message
        call = mock_connection_manager.send_to_user.call_args
        message = call[1]["message"]
        assert "daily digest" in message["message"].lower()

    @pytest.mark.asyncio
    async def test_broadcast_subscription_deleted(self, job_service, mock_connection_manager):
        """Test broadcasting subscription deleted confirmation."""
        result = await job_service.broadcast_subscription_deleted(
            user_id=1,
            subscription_id=42,
        )

        assert result is True
        mock_connection_manager.send_to_user.assert_called_once()

        # Verify event content
        call = mock_connection_manager.send_to_user.call_args
        message = call[1]["message"]
        assert message["event"] == "job.subscription.deleted"
        assert message["subscription_id"] == 42

    @pytest.mark.asyncio
    async def test_broadcast_feed_update(self, job_service, mock_connection_manager):
        """Test broadcasting batch feed update."""
        top_matches = [
            {"job_id": 130, "title": "Python Dev", "company": "TechCorp", "match_score": 0.95},
            {"job_id": 131, "title": "Backend Lead", "company": "StartupXYZ", "match_score": 0.92},
            {"job_id": 132, "title": "Full Stack", "company": "BigCo", "match_score": 0.88},
        ]

        result = await job_service.broadcast_feed_update(
            user_id=1,
            new_jobs_count=12,
            new_matches_count=3,
            expiring_jobs_count=2,
            top_matches=top_matches,
            total_active_jobs=47,
            message="12 new jobs posted, including 3 excellent matches!",
        )

        assert result is True
        mock_connection_manager.send_to_user.assert_called_once()

        # Verify event content
        call = mock_connection_manager.send_to_user.call_args
        message = call[1]["message"]
        assert message["event"] == "job.feed.update"
        assert message["new_jobs_count"] == 12
        assert message["new_matches_count"] == 3
        assert len(message["top_matches"]) == 3


class TestRealtimeJobServiceIntegration:
    """Test RealtimeJobService integration scenarios."""

    @pytest.mark.asyncio
    async def test_complete_job_lifecycle(self, job_service, mock_connection_manager):
        """Test complete job lifecycle: posted -> updated -> expiring -> closed."""
        user_id = 1

        # 1. Job posted
        await job_service.broadcast_job_posted(
            job_id=123,
            title="Senior Python Developer",
            company_name="TechCorp",
            location="San Francisco, CA",
            description_preview="We're looking for...",
            job_type="full_time",
            matched_user_ids=[user_id],
            match_scores={user_id: 0.92},
        )

        # 2. Job updated
        await job_service.broadcast_job_updated(
            job_id=123,
            title="Senior Python Developer",
            company_name="TechCorp",
            updated_fields=["salary_range"],
            update_summary="Salary increased",
            interested_user_ids=[user_id],
            salary_range="$130k-$190k",
        )

        # 3. Job expiring
        expires_at = datetime.utcnow() + timedelta(hours=24)
        await job_service.broadcast_job_expiring(
            job_id=123,
            title="Senior Python Developer",
            company_name="TechCorp",
            expires_in_hours=24,
            expires_at=expires_at,
            message="Apply now!",
            saved_by_user_ids=[user_id],
        )

        # 4. Job closed
        await job_service.broadcast_job_closed(
            job_id=123,
            title="Senior Python Developer",
            company_name="TechCorp",
            reason="filled",
            message="Position filled",
            interested_user_ids=[user_id],
        )

        # All 4 events should be sent
        assert mock_connection_manager.send_to_user.call_count == 4

    @pytest.mark.asyncio
    async def test_subscription_workflow(self, job_service, mock_connection_manager):
        """Test subscription create -> receive jobs -> delete workflow."""
        user_id = 1

        # 1. Create subscription
        await job_service.broadcast_subscription_created(
            user_id=user_id,
            subscription_id=42,
            keywords=["Python"],
            frequency="instant",
        )

        # 2. Receive matching job
        await job_service.broadcast_job_matched(
            user_id=user_id,
            job_id=125,
            title="Python Developer",
            company_name="TechCorp",
            match_score=0.95,
            match_quality="excellent",
            match_reasons=["Python skills"],
            location="Remote",
            remote_type="remote",
            skills=["Python"],
            description_preview="Join our team...",
        )

        # 3. Delete subscription
        await job_service.broadcast_subscription_deleted(
            user_id=user_id,
            subscription_id=42,
        )

        assert mock_connection_manager.send_to_user.call_count == 3

    @pytest.mark.asyncio
    async def test_multiple_users_different_scores(self, job_service, mock_connection_manager):
        """Test job broadcast to multiple users with different match scores."""
        users = [1, 2, 3, 4, 5]
        match_scores = {1: 0.95, 2: 0.88, 3: 0.92, 4: 0.85, 5: 0.90}
        match_reasons = {
            1: ["Perfect match"],
            2: ["Good match"],
            3: ["Excellent match"],
            4: ["Fair match"],
            5: ["Great match"],
        }

        count = await job_service.broadcast_job_posted(
            job_id=123,
            title="Python Developer",
            company_name="TechCorp",
            location="Remote",
            description_preview="We're hiring...",
            job_type="full_time",
            matched_user_ids=users,
            match_scores=match_scores,
            match_reasons=match_reasons,
        )

        assert count == 5

        # Verify each user got their personalized match score
        calls = mock_connection_manager.send_to_user.call_args_list
        for i, user_id in enumerate(users):
            message = calls[i][1]["message"]
            assert message["match_score"] == match_scores[user_id]
            assert message["match_reasons"] == match_reasons[user_id]


class TestHelperFunctions:
    """Test helper functions."""

    def test_get_realtime_job_service(self, mock_connection_manager):
        """Test get_realtime_job_service helper function."""
        service = get_realtime_job_service(mock_connection_manager)

        assert isinstance(service, RealtimeJobService)
        assert service.connection_manager == mock_connection_manager
