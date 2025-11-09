"""
Realtime Activity Service - Phase 11

WebSocket broadcasting service for real-time activity feed updates.

Features:
- Broadcast connection requests and acceptances
- Notify profile views and skill endorsements
- Send message notifications
- Share post interactions (likes, comments, shares)
- Deliver network activity updates
- Announce achievements and milestones
- Notify profile updates from connections

Integration:
    from networking_ai.services.realtime_activity_service import RealtimeActivityService

    activity_service = RealtimeActivityService(connection_manager)

    # When someone views your profile
    await activity_service.broadcast_profile_viewed(
        user_id=profile_owner_id,
        viewer_id=viewer.id,
        viewer_name=viewer.name,
        view_duration_seconds=45
    )
"""

from datetime import datetime
from typing import Optional, List, Dict, Any
from functools import lru_cache

from ..websocket.connection_manager import ConnectionManager
from ..websocket.activity_events import (
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


class RealtimeActivityService:
    """
    Real-time activity broadcasting service using WebSockets.

    Handles broadcasting of all activity feed events to connected users.
    """

    def __init__(self, connection_manager: ConnectionManager):
        """
        Initialize the realtime activity service.

        Args:
            connection_manager: WebSocket connection manager
        """
        self.connection_manager = connection_manager

    async def broadcast_connection_request(
        self,
        user_id: int,
        request_id: int,
        requester_id: int,
        requester_name: str,
        requester_headline: Optional[str] = None,
        requester_photo_url: Optional[str] = None,
        mutual_connections: int = 0,
        match_score: Optional[float] = None,
        message: Optional[str] = None,
        notification_priority: str = "medium",
    ) -> None:
        """
        Broadcast new connection request event.

        Args:
            user_id: User receiving the request
            request_id: Connection request ID
            requester_id: User who sent the request
            requester_name: Requester's full name
            requester_headline: Requester's headline
            requester_photo_url: Requester's photo URL
            mutual_connections: Number of mutual connections
            match_score: Compatibility score (0-1)
            message: Personal message with request
            notification_priority: Priority level
        """
        event = ConnectionRequestEvent(
            request_id=request_id,
            requester_id=requester_id,
            requester_name=requester_name,
            requester_headline=requester_headline,
            requester_photo_url=requester_photo_url,
            mutual_connections=mutual_connections,
            match_score=match_score,
            message=message,
            notification_priority=notification_priority,
        )

        await self.connection_manager.send_personal_message(
            message=event.dict(), user_id=user_id
        )

    async def broadcast_connection_accepted(
        self,
        user_id: int,
        connection_id: int,
        accepter_id: int,
        accepter_name: str,
        accepter_headline: Optional[str] = None,
        accepter_photo_url: Optional[str] = None,
        connected_at: Optional[datetime] = None,
        relationship_strength: str = "new",
        suggested_actions: Optional[List[str]] = None,
    ) -> None:
        """
        Broadcast connection accepted event.

        Args:
            user_id: User whose request was accepted
            connection_id: Connection ID
            accepter_id: User who accepted
            accepter_name: Accepter's full name
            accepter_headline: Accepter's headline
            accepter_photo_url: Accepter's photo URL
            connected_at: Connection timestamp
            relationship_strength: Connection strength rating
            suggested_actions: Suggested next steps
        """
        event = ConnectionAcceptedEvent(
            connection_id=connection_id,
            accepter_id=accepter_id,
            accepter_name=accepter_name,
            accepter_headline=accepter_headline,
            accepter_photo_url=accepter_photo_url,
            connected_at=connected_at or datetime.now(),
            relationship_strength=relationship_strength,
            suggested_actions=suggested_actions or [
                "Send a message",
                "Endorse their skills",
                "View their profile",
            ],
        )

        await self.connection_manager.send_personal_message(
            message=event.dict(), user_id=user_id
        )

    async def broadcast_profile_viewed(
        self,
        user_id: int,
        viewer_id: Optional[int] = None,
        viewer_name: Optional[str] = None,
        viewer_headline: Optional[str] = None,
        viewer_company: Optional[str] = None,
        is_anonymous: bool = False,
        view_duration_seconds: Optional[int] = None,
        sections_viewed: Optional[List[str]] = None,
        is_recruiter: bool = False,
        is_connection: bool = False,
        total_views_today: int = 1,
        view_source: Optional[str] = None,
    ) -> None:
        """
        Broadcast profile viewed event.

        Args:
            user_id: Profile owner user ID
            viewer_id: Viewer's user ID (None if anonymous)
            viewer_name: Viewer's name
            viewer_headline: Viewer's headline
            viewer_company: Viewer's company
            is_anonymous: Anonymous view
            view_duration_seconds: Time spent viewing
            sections_viewed: Profile sections viewed
            is_recruiter: Viewer is a recruiter
            is_connection: Viewer is a connection
            total_views_today: Total views today
            view_source: How they found the profile
        """
        event = ProfileViewedEvent(
            viewer_id=viewer_id,
            viewer_name=viewer_name,
            viewer_headline=viewer_headline,
            viewer_company=viewer_company,
            is_anonymous=is_anonymous,
            view_duration_seconds=view_duration_seconds,
            sections_viewed=sections_viewed or [],
            is_recruiter=is_recruiter,
            is_connection=is_connection,
            total_views_today=total_views_today,
            view_source=view_source,
        )

        await self.connection_manager.send_personal_message(
            message=event.dict(), user_id=user_id
        )

    async def broadcast_skill_endorsed(
        self,
        user_id: int,
        endorsement_id: int,
        endorser_id: int,
        endorser_name: str,
        endorser_photo_url: Optional[str],
        skill_id: int,
        skill_name: str,
        endorsement_count: int,
        is_connection: bool = False,
        endorser_expertise: Optional[str] = None,
        credibility_score: Optional[float] = None,
    ) -> None:
        """
        Broadcast skill endorsement event.

        Args:
            user_id: User receiving endorsement
            endorsement_id: Endorsement ID
            endorser_id: Endorser user ID
            endorser_name: Endorser's name
            endorser_photo_url: Endorser's photo URL
            skill_id: Skill ID
            skill_name: Skill name
            endorsement_count: Total endorsements for skill
            is_connection: Endorser is a connection
            endorser_expertise: Endorser's expertise level
            credibility_score: Credibility score (0-1)
        """
        event = SkillEndorsedEvent(
            endorsement_id=endorsement_id,
            endorser_id=endorser_id,
            endorser_name=endorser_name,
            endorser_photo_url=endorser_photo_url,
            skill_id=skill_id,
            skill_name=skill_name,
            endorsement_count=endorsement_count,
            is_connection=is_connection,
            endorser_expertise=endorser_expertise,
            credibility_score=credibility_score,
        )

        await self.connection_manager.send_personal_message(
            message=event.dict(), user_id=user_id
        )

    async def broadcast_message_received(
        self,
        user_id: int,
        message_id: int,
        conversation_id: int,
        sender_id: int,
        sender_name: str,
        message_preview: str,
        sender_photo_url: Optional[str] = None,
        has_attachments: bool = False,
        message_type: str = "text",
        unread_count: int = 1,
        is_priority: bool = False,
    ) -> None:
        """
        Broadcast new message received event.

        Args:
            user_id: Message recipient
            message_id: Message ID
            conversation_id: Conversation ID
            sender_id: Sender user ID
            sender_name: Sender's name
            message_preview: Message preview (first 100 chars)
            sender_photo_url: Sender's photo URL
            has_attachments: Message has attachments
            message_type: Message type (text, image, etc.)
            unread_count: Total unread messages
            is_priority: Priority message
        """
        event = MessageReceivedEvent(
            message_id=message_id,
            conversation_id=conversation_id,
            sender_id=sender_id,
            sender_name=sender_name,
            sender_photo_url=sender_photo_url,
            message_preview=message_preview[:100],  # Limit preview
            has_attachments=has_attachments,
            message_type=message_type,
            unread_count=unread_count,
            is_priority=is_priority,
        )

        await self.connection_manager.send_personal_message(
            message=event.dict(), user_id=user_id
        )

    async def broadcast_post_liked(
        self,
        user_id: int,
        post_id: int,
        post_preview: str,
        liker_id: int,
        liker_name: str,
        total_likes: int,
        post_type: str = "text",
        liker_photo_url: Optional[str] = None,
        liker_headline: Optional[str] = None,
    ) -> None:
        """
        Broadcast post liked event.

        Args:
            user_id: Post author
            post_id: Post ID
            post_preview: Post preview text
            liker_id: User who liked
            liker_name: Liker's name
            total_likes: Total likes on post
            post_type: Post type
            liker_photo_url: Liker's photo URL
            liker_headline: Liker's headline
        """
        # Check for milestone
        is_milestone = total_likes in [10, 25, 50, 100, 250, 500, 1000]
        milestone_value = total_likes if is_milestone else None

        event = PostLikedEvent(
            post_id=post_id,
            post_preview=post_preview[:150],
            post_type=post_type,
            liker_id=liker_id,
            liker_name=liker_name,
            liker_photo_url=liker_photo_url,
            liker_headline=liker_headline,
            total_likes=total_likes,
            is_milestone=is_milestone,
            milestone_value=milestone_value,
        )

        await self.connection_manager.send_personal_message(
            message=event.dict(), user_id=user_id
        )

    async def broadcast_post_commented(
        self,
        user_id: int,
        post_id: int,
        post_preview: str,
        comment_id: int,
        comment_preview: str,
        commenter_id: int,
        commenter_name: str,
        total_comments: int,
        commenter_photo_url: Optional[str] = None,
        is_reply: bool = False,
    ) -> None:
        """
        Broadcast post commented event.

        Args:
            user_id: Post author or parent comment author
            post_id: Post ID
            post_preview: Post preview text
            comment_id: Comment ID
            comment_preview: Comment preview
            commenter_id: Commenter user ID
            commenter_name: Commenter's name
            total_comments: Total comments on post
            commenter_photo_url: Commenter's photo URL
            is_reply: Reply to user's comment
        """
        event = PostCommentedEvent(
            post_id=post_id,
            post_preview=post_preview[:150],
            comment_id=comment_id,
            comment_preview=comment_preview[:200],
            comment_length=len(comment_preview),
            commenter_id=commenter_id,
            commenter_name=commenter_name,
            commenter_photo_url=commenter_photo_url,
            total_comments=total_comments,
            is_reply=is_reply,
        )

        await self.connection_manager.send_personal_message(
            message=event.dict(), user_id=user_id
        )

    async def broadcast_post_shared(
        self,
        user_id: int,
        post_id: int,
        post_preview: str,
        sharer_id: int,
        sharer_name: str,
        total_shares: int,
        sharer_photo_url: Optional[str] = None,
        sharer_comment: Optional[str] = None,
        estimated_reach: Optional[int] = None,
    ) -> None:
        """
        Broadcast post shared event.

        Args:
            user_id: Post author
            post_id: Post ID
            post_preview: Post preview text
            sharer_id: User who shared
            sharer_name: Sharer's name
            total_shares: Total shares
            sharer_photo_url: Sharer's photo URL
            sharer_comment: Comment on share
            estimated_reach: Estimated additional reach
        """
        event = PostSharedEvent(
            post_id=post_id,
            post_preview=post_preview[:150],
            sharer_id=sharer_id,
            sharer_name=sharer_name,
            sharer_photo_url=sharer_photo_url,
            sharer_comment=sharer_comment,
            total_shares=total_shares,
            estimated_reach=estimated_reach,
        )

        await self.connection_manager.send_personal_message(
            message=event.dict(), user_id=user_id
        )

    async def broadcast_network_activity(
        self,
        user_id: int,
        activity_type: str,
        actor_id: int,
        actor_name: str,
        activity_summary: str,
        actor_photo_url: Optional[str] = None,
        activity_target: Optional[str] = None,
        activity_data: Optional[Dict[str, Any]] = None,
        relevance_score: Optional[float] = None,
        connection_degree: int = 1,
    ) -> None:
        """
        Broadcast network activity event.

        Args:
            user_id: User to notify
            activity_type: Type of activity (new_job, work_anniversary, etc.)
            actor_id: User who performed activity
            actor_name: Actor's name
            activity_summary: Activity description
            actor_photo_url: Actor's photo URL
            activity_target: Target of activity
            activity_data: Additional activity data
            relevance_score: Relevance score (0-1)
            connection_degree: Connection degree (1st, 2nd, 3rd)
        """
        event = NetworkActivityEvent(
            activity_type=activity_type,
            actor_id=actor_id,
            actor_name=actor_name,
            actor_photo_url=actor_photo_url,
            activity_summary=activity_summary,
            activity_target=activity_target,
            activity_data=activity_data or {},
            relevance_score=relevance_score,
            connection_degree=connection_degree,
        )

        await self.connection_manager.send_personal_message(
            message=event.dict(), user_id=user_id
        )

    async def broadcast_achievement_unlocked(
        self,
        user_id: int,
        achievement_id: str,
        achievement_name: str,
        achievement_description: str,
        progress_value: int,
        progress_target: int,
        unlock_message: str,
        achievement_icon: Optional[str] = None,
        achievement_tier: str = "bronze",
        points_earned: int = 0,
        badge_earned: Optional[str] = None,
    ) -> None:
        """
        Broadcast achievement unlocked event.

        Args:
            user_id: User who unlocked achievement
            achievement_id: Achievement identifier
            achievement_name: Achievement name
            achievement_description: Achievement description
            progress_value: Current value
            progress_target: Target value
            unlock_message: Congratulations message
            achievement_icon: Icon URL
            achievement_tier: Tier (bronze, silver, gold, platinum)
            points_earned: Platform points earned
            badge_earned: Badge name
        """
        completion_percentage = (progress_value / progress_target * 100) if progress_target > 0 else 100

        event = AchievementUnlockedEvent(
            achievement_id=achievement_id,
            achievement_name=achievement_name,
            achievement_description=achievement_description,
            achievement_icon=achievement_icon,
            achievement_tier=achievement_tier,
            progress_value=progress_value,
            progress_target=progress_target,
            completion_percentage=min(completion_percentage, 100.0),
            points_earned=points_earned,
            badge_earned=badge_earned,
            unlock_message=unlock_message,
        )

        await self.connection_manager.send_personal_message(
            message=event.dict(), user_id=user_id
        )

    async def broadcast_profile_updated(
        self,
        user_id: int,
        updated_user_id: int,
        user_name: str,
        update_type: str,
        update_summary: str,
        user_photo_url: Optional[str] = None,
        fields_updated: Optional[List[str]] = None,
        is_significant: bool = False,
        connection_strength: str = "medium",
    ) -> None:
        """
        Broadcast profile update from connection.

        Args:
            user_id: User to notify
            updated_user_id: User who updated profile
            user_name: Updated user's name
            update_type: Type of update (new_position, new_education, etc.)
            update_summary: Update description
            user_photo_url: Updated user's photo URL
            fields_updated: List of fields that changed
            is_significant: Major update flag
            connection_strength: Connection strength
        """
        event = ProfileUpdatedEvent(
            user_id=updated_user_id,
            user_name=user_name,
            user_photo_url=user_photo_url,
            update_type=update_type,
            update_summary=update_summary,
            fields_updated=fields_updated or [],
            is_significant=is_significant,
            connection_strength=connection_strength,
        )

        await self.connection_manager.send_personal_message(
            message=event.dict(), user_id=user_id
        )


@lru_cache()
def get_realtime_activity_service(
    connection_manager: ConnectionManager,
) -> RealtimeActivityService:
    """
    Get or create singleton instance of RealtimeActivityService.

    Args:
        connection_manager: WebSocket connection manager

    Returns:
        RealtimeActivityService instance
    """
    return RealtimeActivityService(connection_manager)
