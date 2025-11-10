"""
Tests for Realtime Activity Service - Phase 11

Tests WebSocket broadcasting for activity feed updates.
"""

import pytest
from datetime import datetime
from unittest.mock import AsyncMock, MagicMock, patch
from typing import List, Dict

from src.networking_ai.services.realtime_activity_service import (
    RealtimeActivityService,
    get_realtime_activity_service,
)
from src.networking_ai.websocket.activity_events import (
    ConnectionRequestEvent,
    ConnectionAcceptedEvent,
    ProfileViewedEvent,
    SkillEndorsedEvent,
    MessageReceivedEvent,
    PostLikedEvent,
    PostCommentedEvent,
    PostSharedEvent,
    NetworkActivityEvent,
    AchievementUnlockedEvent,
    ProfileUpdatedEvent,
)


@pytest.fixture
def mock_connection_manager():
    """Create mock connection manager."""
    manager = AsyncMock()
    manager.send_personal_message = AsyncMock()
    return manager


@pytest.fixture
def activity_service(mock_connection_manager):
    """Create activity service with mock connection manager."""
    return RealtimeActivityService(mock_connection_manager)


# Event Model Tests


class TestActivityEventModels:
    """Test activity event Pydantic models."""

    def test_connection_request_event(self):
        """Test ConnectionRequestEvent model."""
        event = ConnectionRequestEvent(
            request_id=1,
            requester_id=100,
            requester_name="Alice Johnson",
            requester_headline="Senior Engineer",
            mutual_connections=5,
            match_score=0.85,
        )

        assert event.event_type == "activity.connection_request"
        assert event.request_id == 1
        assert event.requester_id == 100
        assert event.requester_name == "Alice Johnson"
        assert event.mutual_connections == 5
        assert event.match_score == 0.85
        assert event.notification_priority == "medium"

    def test_connection_accepted_event(self):
        """Test ConnectionAcceptedEvent model."""
        event = ConnectionAcceptedEvent(
            connection_id=1,
            accepter_id=200,
            accepter_name="Bob Smith",
            relationship_strength="new",
            suggested_actions=["Send message", "View profile"],
        )

        assert event.event_type == "activity.connection_accepted"
        assert event.connection_id == 1
        assert event.accepter_id == 200
        assert event.relationship_strength == "new"
        assert len(event.suggested_actions) == 2

    def test_profile_viewed_event(self):
        """Test ProfileViewedEvent model."""
        event = ProfileViewedEvent(
            viewer_id=300,
            viewer_name="Carol Chen",
            viewer_company="TechCorp",
            is_recruiter=True,
            view_duration_seconds=45,
            sections_viewed=["Experience", "Skills", "Education"],
            total_views_today=5,
        )

        assert event.event_type == "activity.profile_viewed"
        assert event.viewer_id == 300
        assert event.is_recruiter is True
        assert event.view_duration_seconds == 45
        assert len(event.sections_viewed) == 3
        assert event.total_views_today == 5

    def test_skill_endorsed_event(self):
        """Test SkillEndorsedEvent model."""
        event = SkillEndorsedEvent(
            endorsement_id=1,
            endorser_id=400,
            endorser_name="David Lee",
            skill_id=10,
            skill_name="Python",
            endorsement_count=15,
            is_connection=True,
            credibility_score=0.9,
        )

        assert event.event_type == "activity.skill_endorsed"
        assert event.skill_name == "Python"
        assert event.endorsement_count == 15
        assert event.credibility_score == 0.9

    def test_message_received_event(self):
        """Test MessageReceivedEvent model."""
        event = MessageReceivedEvent(
            message_id=1,
            conversation_id=5,
            sender_id=500,
            sender_name="Emily White",
            message_preview="Hey, would love to connect about...",
            has_attachments=True,
            unread_count=3,
            is_priority=True,
        )

        assert event.event_type == "activity.message_received"
        assert event.message_id == 1
        assert event.has_attachments is True
        assert event.unread_count == 3
        assert event.is_priority is True

    def test_post_liked_event(self):
        """Test PostLikedEvent model."""
        event = PostLikedEvent(
            post_id=1,
            post_preview="Just published my new article...",
            liker_id=600,
            liker_name="Frank Brown",
            liker_headline="Product Manager",
            total_likes=50,
            is_milestone=True,
            milestone_value=50,
        )

        assert event.event_type == "activity.post_liked"
        assert event.total_likes == 50
        assert event.is_milestone is True
        assert event.milestone_value == 50

    def test_post_commented_event(self):
        """Test PostCommentedEvent model."""
        event = PostCommentedEvent(
            post_id=1,
            post_preview="My thoughts on AI trends...",
            comment_id=10,
            comment_preview="Great insights! I especially agree with...",
            comment_length=45,
            commenter_id=700,
            commenter_name="Grace Kim",
            total_comments=12,
            is_reply=False,
        )

        assert event.event_type == "activity.post_commented"
        assert event.comment_id == 10
        assert event.total_comments == 12
        assert event.is_reply is False

    def test_post_shared_event(self):
        """Test PostSharedEvent model."""
        event = PostSharedEvent(
            post_id=1,
            post_preview="Announcing our new product...",
            sharer_id=800,
            sharer_name="Henry Davis",
            sharer_comment="This is exactly what we need!",
            total_shares=25,
            estimated_reach=5000,
        )

        assert event.event_type == "activity.post_shared"
        assert event.total_shares == 25
        assert event.estimated_reach == 5000

    def test_network_activity_event(self):
        """Test NetworkActivityEvent model."""
        event = NetworkActivityEvent(
            activity_type="new_job",
            actor_id=900,
            actor_name="Ivy Martinez",
            activity_summary="Started new position at Google",
            activity_target="Google",
            activity_data={"position": "Senior Engineer", "location": "SF"},
            relevance_score=0.8,
            connection_degree=1,
        )

        assert event.event_type == "activity.network_activity"
        assert event.activity_type == "new_job"
        assert event.connection_degree == 1
        assert event.activity_data["position"] == "Senior Engineer"

    def test_achievement_unlocked_event(self):
        """Test AchievementUnlockedEvent model."""
        event = AchievementUnlockedEvent(
            achievement_id="network_builder",
            achievement_name="Network Builder",
            achievement_description="Reached 50 connections",
            achievement_tier="silver",
            progress_value=50,
            progress_target=50,
            completion_percentage=100.0,
            points_earned=500,
            badge_earned="Silver Connector",
            unlock_message="Congratulations on building your network!",
        )

        assert event.event_type == "activity.achievement_unlocked"
        assert event.achievement_tier == "silver"
        assert event.completion_percentage == 100.0
        assert event.points_earned == 500

    def test_profile_updated_event(self):
        """Test ProfileUpdatedEvent model."""
        event = ProfileUpdatedEvent(
            user_id=1000,
            user_name="Jack Wilson",
            update_type="new_position",
            update_summary="Started new role at Amazon",
            fields_updated=["current_position", "company"],
            is_significant=True,
            connection_strength="strong",
        )

        assert event.event_type == "activity.profile_updated"
        assert event.update_type == "new_position"
        assert event.is_significant is True
        assert len(event.fields_updated) == 2


# Broadcasting Tests


@pytest.mark.asyncio
class TestActivityBroadcasting:
    """Test activity broadcasting functionality."""

    async def test_broadcast_connection_request(
        self, activity_service, mock_connection_manager
    ):
        """Test broadcasting connection request."""
        await activity_service.broadcast_connection_request(
            user_id=1,
            request_id=100,
            requester_id=200,
            requester_name="Alice Johnson",
            requester_headline="Senior Engineer",
            mutual_connections=5,
            match_score=0.85,
            message="Would love to connect!",
        )

        mock_connection_manager.send_personal_message.assert_called_once()
        call_args = mock_connection_manager.send_personal_message.call_args
        message = call_args.kwargs["message"]

        assert message["event_type"] == "activity.connection_request"
        assert message["requester_name"] == "Alice Johnson"
        assert message["mutual_connections"] == 5
        assert message["match_score"] == 0.85

    async def test_broadcast_connection_accepted(
        self, activity_service, mock_connection_manager
    ):
        """Test broadcasting connection accepted."""
        await activity_service.broadcast_connection_accepted(
            user_id=1,
            connection_id=100,
            accepter_id=200,
            accepter_name="Bob Smith",
            relationship_strength="new",
            suggested_actions=["Send a message", "View profile"],
        )

        mock_connection_manager.send_personal_message.assert_called_once()
        call_args = mock_connection_manager.send_personal_message.call_args
        message = call_args.kwargs["message"]

        assert message["event_type"] == "activity.connection_accepted"
        assert message["accepter_name"] == "Bob Smith"
        assert len(message["suggested_actions"]) == 2

    async def test_broadcast_profile_viewed(
        self, activity_service, mock_connection_manager
    ):
        """Test broadcasting profile viewed."""
        await activity_service.broadcast_profile_viewed(
            user_id=1,
            viewer_id=300,
            viewer_name="Carol Chen",
            viewer_company="TechCorp",
            is_recruiter=True,
            view_duration_seconds=45,
            sections_viewed=["Experience", "Skills"],
            total_views_today=5,
        )

        mock_connection_manager.send_personal_message.assert_called_once()
        call_args = mock_connection_manager.send_personal_message.call_args
        message = call_args.kwargs["message"]

        assert message["event_type"] == "activity.profile_viewed"
        assert message["is_recruiter"] is True
        assert message["view_duration_seconds"] == 45

    async def test_broadcast_skill_endorsed(
        self, activity_service, mock_connection_manager
    ):
        """Test broadcasting skill endorsement."""
        await activity_service.broadcast_skill_endorsed(
            user_id=1,
            endorsement_id=100,
            endorser_id=400,
            endorser_name="David Lee",
            endorser_photo_url="https://example.com/photo.jpg",
            skill_id=10,
            skill_name="Python",
            endorsement_count=15,
            is_connection=True,
            credibility_score=0.9,
        )

        mock_connection_manager.send_personal_message.assert_called_once()
        call_args = mock_connection_manager.send_personal_message.call_args
        message = call_args.kwargs["message"]

        assert message["event_type"] == "activity.skill_endorsed"
        assert message["skill_name"] == "Python"
        assert message["endorsement_count"] == 15

    async def test_broadcast_message_received(
        self, activity_service, mock_connection_manager
    ):
        """Test broadcasting message received."""
        await activity_service.broadcast_message_received(
            user_id=1,
            message_id=100,
            conversation_id=5,
            sender_id=500,
            sender_name="Emily White",
            message_preview="Hey, would love to connect about machine learning...",
            has_attachments=True,
            unread_count=3,
            is_priority=True,
        )

        mock_connection_manager.send_personal_message.assert_called_once()
        call_args = mock_connection_manager.send_personal_message.call_args
        message = call_args.kwargs["message"]

        assert message["event_type"] == "activity.message_received"
        assert message["unread_count"] == 3
        assert message["is_priority"] is True

    async def test_broadcast_post_liked(
        self, activity_service, mock_connection_manager
    ):
        """Test broadcasting post liked."""
        await activity_service.broadcast_post_liked(
            user_id=1,
            post_id=100,
            post_preview="Just published my new article on AI...",
            liker_id=600,
            liker_name="Frank Brown",
            liker_headline="Product Manager",
            total_likes=50,
        )

        mock_connection_manager.send_personal_message.assert_called_once()
        call_args = mock_connection_manager.send_personal_message.call_args
        message = call_args.kwargs["message"]

        assert message["event_type"] == "activity.post_liked"
        assert message["total_likes"] == 50
        assert message["is_milestone"] is True  # 50 is a milestone

    async def test_broadcast_post_commented(
        self, activity_service, mock_connection_manager
    ):
        """Test broadcasting post commented."""
        await activity_service.broadcast_post_commented(
            user_id=1,
            post_id=100,
            post_preview="My thoughts on AI trends...",
            comment_id=10,
            comment_preview="Great insights! I especially agree with your point about...",
            commenter_id=700,
            commenter_name="Grace Kim",
            total_comments=12,
            is_reply=False,
        )

        mock_connection_manager.send_personal_message.assert_called_once()
        call_args = mock_connection_manager.send_personal_message.call_args
        message = call_args.kwargs["message"]

        assert message["event_type"] == "activity.post_commented"
        assert message["total_comments"] == 12

    async def test_broadcast_post_shared(
        self, activity_service, mock_connection_manager
    ):
        """Test broadcasting post shared."""
        await activity_service.broadcast_post_shared(
            user_id=1,
            post_id=100,
            post_preview="Announcing our new product...",
            sharer_id=800,
            sharer_name="Henry Davis",
            sharer_comment="This is exactly what we need!",
            total_shares=25,
            estimated_reach=5000,
        )

        mock_connection_manager.send_personal_message.assert_called_once()
        call_args = mock_connection_manager.send_personal_message.call_args
        message = call_args.kwargs["message"]

        assert message["event_type"] == "activity.post_shared"
        assert message["total_shares"] == 25
        assert message["estimated_reach"] == 5000

    async def test_broadcast_network_activity(
        self, activity_service, mock_connection_manager
    ):
        """Test broadcasting network activity."""
        await activity_service.broadcast_network_activity(
            user_id=1,
            activity_type="new_job",
            actor_id=900,
            actor_name="Ivy Martinez",
            activity_summary="Started new position at Google as Senior Engineer",
            activity_target="Google",
            activity_data={"position": "Senior Engineer", "location": "SF"},
            relevance_score=0.8,
            connection_degree=1,
        )

        mock_connection_manager.send_personal_message.assert_called_once()
        call_args = mock_connection_manager.send_personal_message.call_args
        message = call_args.kwargs["message"]

        assert message["event_type"] == "activity.network_activity"
        assert message["activity_type"] == "new_job"
        assert message["connection_degree"] == 1

    async def test_broadcast_achievement_unlocked(
        self, activity_service, mock_connection_manager
    ):
        """Test broadcasting achievement unlocked."""
        await activity_service.broadcast_achievement_unlocked(
            user_id=1,
            achievement_id="network_builder",
            achievement_name="Network Builder",
            achievement_description="Reached 50 connections",
            progress_value=50,
            progress_target=50,
            unlock_message="Congratulations on building your network!",
            achievement_tier="silver",
            points_earned=500,
            badge_earned="Silver Connector",
        )

        mock_connection_manager.send_personal_message.assert_called_once()
        call_args = mock_connection_manager.send_personal_message.call_args
        message = call_args.kwargs["message"]

        assert message["event_type"] == "activity.achievement_unlocked"
        assert message["achievement_tier"] == "silver"
        assert message["points_earned"] == 500
        assert message["completion_percentage"] == 100.0

    async def test_broadcast_profile_updated(
        self, activity_service, mock_connection_manager
    ):
        """Test broadcasting profile updated."""
        await activity_service.broadcast_profile_updated(
            user_id=1,
            updated_user_id=1000,
            user_name="Jack Wilson",
            update_type="new_position",
            update_summary="Started new role at Amazon as Principal Engineer",
            fields_updated=["current_position", "company"],
            is_significant=True,
            connection_strength="strong",
        )

        mock_connection_manager.send_personal_message.assert_called_once()
        call_args = mock_connection_manager.send_personal_message.call_args
        message = call_args.kwargs["message"]

        assert message["event_type"] == "activity.profile_updated"
        assert message["update_type"] == "new_position"
        assert message["is_significant"] is True


# Integration Tests


@pytest.mark.asyncio
class TestActivityIntegration:
    """Test activity service integration scenarios."""

    async def test_complete_connection_flow(
        self, activity_service, mock_connection_manager
    ):
        """Test complete connection request -> acceptance flow."""
        # User 1 sends connection request to User 2
        await activity_service.broadcast_connection_request(
            user_id=2,
            request_id=1,
            requester_id=1,
            requester_name="Alice Johnson",
            mutual_connections=5,
            match_score=0.85,
        )

        # User 2 accepts
        await activity_service.broadcast_connection_accepted(
            user_id=1,
            connection_id=1,
            accepter_id=2,
            accepter_name="Bob Smith",
        )

        # Both users get achievement for first connection
        await activity_service.broadcast_achievement_unlocked(
            user_id=1,
            achievement_id="first_connection",
            achievement_name="First Connection",
            achievement_description="Made your first connection!",
            progress_value=1,
            progress_target=1,
            unlock_message="Welcome to the network!",
        )

        assert mock_connection_manager.send_personal_message.call_count == 3

    async def test_post_engagement_flow(
        self, activity_service, mock_connection_manager
    ):
        """Test post engagement notifications."""
        # Post gets liked
        await activity_service.broadcast_post_liked(
            user_id=1,
            post_id=100,
            post_preview="My thoughts on AI...",
            liker_id=2,
            liker_name="Bob Smith",
            total_likes=10,
        )

        # Post gets commented
        await activity_service.broadcast_post_commented(
            user_id=1,
            post_id=100,
            post_preview="My thoughts on AI...",
            comment_id=1,
            comment_preview="Great post!",
            commenter_id=3,
            commenter_name="Carol Chen",
            total_comments=5,
        )

        # Post gets shared
        await activity_service.broadcast_post_shared(
            user_id=1,
            post_id=100,
            post_preview="My thoughts on AI...",
            sharer_id=4,
            sharer_name="David Lee",
            total_shares=3,
            estimated_reach=1000,
        )

        # Achievement for engagement
        await activity_service.broadcast_achievement_unlocked(
            user_id=1,
            achievement_id="thought_leader",
            achievement_name="Thought Leader",
            achievement_description="Received 100 likes on your posts",
            progress_value=100,
            progress_target=100,
            unlock_message="You're becoming an influencer!",
        )

        assert mock_connection_manager.send_personal_message.call_count == 4

    async def test_profile_activity_flow(
        self, activity_service, mock_connection_manager
    ):
        """Test profile-related activity notifications."""
        # Profile viewed by recruiter
        await activity_service.broadcast_profile_viewed(
            user_id=1,
            viewer_id=2,
            viewer_name="Jane Recruiter",
            viewer_company="TechCorp",
            is_recruiter=True,
            view_duration_seconds=120,
        )

        # Skill endorsed
        await activity_service.broadcast_skill_endorsed(
            user_id=1,
            endorsement_id=1,
            endorser_id=3,
            endorser_name="Expert Dev",
            endorser_photo_url="photo.jpg",
            skill_id=10,
            skill_name="Python",
            endorsement_count=10,
            credibility_score=0.95,
        )

        # Achievement for views
        await activity_service.broadcast_achievement_unlocked(
            user_id=1,
            achievement_id="popular_profile",
            achievement_name="Popular Profile",
            achievement_description="Your profile reached 1000 views",
            progress_value=1000,
            progress_target=1000,
            unlock_message="You're standing out!",
        )

        assert mock_connection_manager.send_personal_message.call_count == 3


# Helper Functions Test


def test_get_realtime_activity_service():
    """Test singleton service getter."""
    mock_manager = MagicMock()
    service1 = get_realtime_activity_service(mock_manager)
    service2 = get_realtime_activity_service(mock_manager)

    assert service1 is service2  # Should be same instance
