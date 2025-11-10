"""
Activity Feed WebSocket Events - Phase 11

Real-time activity feed updates via WebSocket.

Event Types:
- activity.connection_request: New connection request received
- activity.connection_accepted: Connection request accepted
- activity.profile_viewed: Someone viewed your profile
- activity.skill_endorsed: Someone endorsed your skill
- activity.message_received: New direct message
- activity.post_liked: Someone liked your post
- activity.post_commented: Someone commented on your post
- activity.post_shared: Someone shared your post
- activity.network_activity: Activity from your connections
- activity.achievement_unlocked: Achievement or milestone reached
- activity.profile_updated: Connection updated their profile

Usage:
    from networking_ai.services.realtime_activity_service import RealtimeActivityService

    activity_service = RealtimeActivityService(connection_manager)

    # Broadcast connection request
    await activity_service.broadcast_connection_request(
        user_id=user_id,
        requester_id=requester.id,
        requester_name=requester.name
    )
"""

from datetime import datetime
from typing import Optional, List, Dict, Any, Literal
from pydantic import BaseModel, Field


class ConnectionRequestEvent(BaseModel):
    """Event for new connection request received."""

    event_type: Literal["activity.connection_request"] = "activity.connection_request"
    timestamp: datetime = Field(default_factory=datetime.now)

    # Request details
    request_id: int = Field(..., description="Connection request ID")
    requester_id: int = Field(..., description="User who sent request")
    requester_name: str = Field(..., description="Requester's full name")
    requester_headline: Optional[str] = Field(None, description="Requester's headline")
    requester_photo_url: Optional[str] = Field(None, description="Requester's photo")

    # Context
    mutual_connections: int = Field(default=0, description="Number of mutual connections")
    match_score: Optional[float] = Field(None, ge=0, le=1, description="Compatibility score")
    message: Optional[str] = Field(None, description="Personal message with request")

    # Metadata
    notification_priority: str = Field(default="medium", description="Notification priority")


class ConnectionAcceptedEvent(BaseModel):
    """Event for connection request accepted."""

    event_type: Literal["activity.connection_accepted"] = "activity.connection_accepted"
    timestamp: datetime = Field(default_factory=datetime.now)

    # Connection details
    connection_id: int = Field(..., description="Connection ID")
    accepter_id: int = Field(..., description="User who accepted")
    accepter_name: str = Field(..., description="Accepter's full name")
    accepter_headline: Optional[str] = Field(None, description="Accepter's headline")
    accepter_photo_url: Optional[str] = Field(None, description="Accepter's photo")

    # Relationship
    connected_at: datetime = Field(default_factory=datetime.now)
    relationship_strength: str = Field(default="new", description="Connection strength")
    suggested_actions: List[str] = Field(default_factory=list, description="Next step suggestions")

    # Metadata
    notification_message: str = Field(default="Your connection request was accepted!")


class ProfileViewedEvent(BaseModel):
    """Event for profile view notification."""

    event_type: Literal["activity.profile_viewed"] = "activity.profile_viewed"
    timestamp: datetime = Field(default_factory=datetime.now)

    # Viewer details
    viewer_id: Optional[int] = Field(None, description="Viewer ID (if not anonymous)")
    viewer_name: Optional[str] = Field(None, description="Viewer name")
    viewer_headline: Optional[str] = Field(None, description="Viewer headline")
    viewer_company: Optional[str] = Field(None, description="Viewer company")
    is_anonymous: bool = Field(default=False, description="Anonymous view")

    # View context
    view_duration_seconds: Optional[int] = Field(None, description="Time spent viewing")
    sections_viewed: List[str] = Field(default_factory=list, description="Profile sections viewed")
    is_recruiter: bool = Field(default=False, description="Viewer is recruiter")
    is_connection: bool = Field(default=False, description="Viewer is connection")

    # Analytics
    total_views_today: int = Field(default=1, description="Total views today")
    view_source: Optional[str] = Field(None, description="How they found you")


class SkillEndorsedEvent(BaseModel):
    """Event for skill endorsement received."""

    event_type: Literal["activity.skill_endorsed"] = "activity.skill_endorsed"
    timestamp: datetime = Field(default_factory=datetime.now)

    # Endorsement details
    endorsement_id: int = Field(..., description="Endorsement ID")
    endorser_id: int = Field(..., description="Endorser user ID")
    endorser_name: str = Field(..., description="Endorser name")
    endorser_photo_url: Optional[str] = Field(None, description="Endorser photo")

    # Skill details
    skill_id: int = Field(..., description="Skill ID")
    skill_name: str = Field(..., description="Skill name")
    endorsement_count: int = Field(..., description="Total endorsements for this skill")

    # Context
    is_connection: bool = Field(default=False, description="Endorser is connection")
    endorser_expertise: Optional[str] = Field(None, description="Endorser's expertise level")
    credibility_score: Optional[float] = Field(None, ge=0, le=1)


class MessageReceivedEvent(BaseModel):
    """Event for new direct message received."""

    event_type: Literal["activity.message_received"] = "activity.message_received"
    timestamp: datetime = Field(default_factory=datetime.now)

    # Message details
    message_id: int = Field(..., description="Message ID")
    conversation_id: int = Field(..., description="Conversation ID")
    sender_id: int = Field(..., description="Sender user ID")
    sender_name: str = Field(..., description="Sender name")
    sender_photo_url: Optional[str] = Field(None, description="Sender photo")

    # Content preview
    message_preview: str = Field(..., description="First 100 chars of message")
    has_attachments: bool = Field(default=False)
    message_type: str = Field(default="text", description="Message type")

    # Context
    unread_count: int = Field(default=1, description="Total unread messages")
    is_priority: bool = Field(default=False, description="Priority message")


class PostLikedEvent(BaseModel):
    """Event for post liked notification."""

    event_type: Literal["activity.post_liked"] = "activity.post_liked"
    timestamp: datetime = Field(default_factory=datetime.now)

    # Post details
    post_id: int = Field(..., description="Post ID")
    post_preview: str = Field(..., description="Post preview text")
    post_type: str = Field(default="text", description="Post type")

    # Liker details
    liker_id: int = Field(..., description="User who liked")
    liker_name: str = Field(..., description="Liker name")
    liker_photo_url: Optional[str] = Field(None, description="Liker photo")
    liker_headline: Optional[str] = Field(None, description="Liker headline")

    # Engagement
    total_likes: int = Field(..., description="Total likes on post")
    is_milestone: bool = Field(default=False, description="Hit milestone (10, 50, 100, etc)")
    milestone_value: Optional[int] = Field(None, description="Milestone number")


class PostCommentedEvent(BaseModel):
    """Event for comment on post notification."""

    event_type: Literal["activity.post_commented"] = "activity.post_commented"
    timestamp: datetime = Field(default_factory=datetime.now)

    # Post details
    post_id: int = Field(..., description="Post ID")
    post_preview: str = Field(..., description="Post preview text")

    # Comment details
    comment_id: int = Field(..., description="Comment ID")
    comment_preview: str = Field(..., description="Comment preview")
    comment_length: int = Field(..., description="Comment length")

    # Commenter details
    commenter_id: int = Field(..., description="Commenter user ID")
    commenter_name: str = Field(..., description="Commenter name")
    commenter_photo_url: Optional[str] = Field(None, description="Commenter photo")

    # Engagement
    total_comments: int = Field(..., description="Total comments on post")
    is_reply: bool = Field(default=False, description="Reply to your comment")


class PostSharedEvent(BaseModel):
    """Event for post shared notification."""

    event_type: Literal["activity.post_shared"] = "activity.post_shared"
    timestamp: datetime = Field(default_factory=datetime.now)

    # Post details
    post_id: int = Field(..., description="Post ID")
    post_preview: str = Field(..., description="Post preview text")

    # Sharer details
    sharer_id: int = Field(..., description="User who shared")
    sharer_name: str = Field(..., description="Sharer name")
    sharer_photo_url: Optional[str] = Field(None, description="Sharer photo")
    sharer_comment: Optional[str] = Field(None, description="Comment on share")

    # Reach
    total_shares: int = Field(..., description="Total shares")
    estimated_reach: Optional[int] = Field(None, description="Estimated additional reach")


class NetworkActivityEvent(BaseModel):
    """Event for activity from your network."""

    event_type: Literal["activity.network_activity"] = "activity.network_activity"
    timestamp: datetime = Field(default_factory=datetime.now)

    # Activity details
    activity_type: str = Field(..., description="Type of activity")
    actor_id: int = Field(..., description="User who performed activity")
    actor_name: str = Field(..., description="Actor name")
    actor_photo_url: Optional[str] = Field(None, description="Actor photo")

    # Activity content
    activity_summary: str = Field(..., description="Activity description")
    activity_target: Optional[str] = Field(None, description="Target of activity")
    activity_data: Dict[str, Any] = Field(default_factory=dict)

    # Context
    relevance_score: Optional[float] = Field(None, ge=0, le=1)
    connection_degree: int = Field(default=1, description="1st, 2nd, 3rd degree")

    # Examples of activity_type:
    # - "new_job": Connection started new job
    # - "work_anniversary": Work anniversary
    # - "new_skill": Added new skill
    # - "new_certification": Earned certification
    # - "profile_update": Updated profile


class AchievementUnlockedEvent(BaseModel):
    """Event for achievement or milestone reached."""

    event_type: Literal["activity.achievement_unlocked"] = "activity.achievement_unlocked"
    timestamp: datetime = Field(default_factory=datetime.now)

    # Achievement details
    achievement_id: str = Field(..., description="Achievement identifier")
    achievement_name: str = Field(..., description="Achievement name")
    achievement_description: str = Field(..., description="Achievement description")
    achievement_icon: Optional[str] = Field(None, description="Icon URL")
    achievement_tier: str = Field(default="bronze", description="bronze/silver/gold/platinum")

    # Progress
    progress_value: int = Field(..., description="Current value")
    progress_target: int = Field(..., description="Target value")
    completion_percentage: float = Field(..., ge=0, le=100)

    # Rewards
    points_earned: int = Field(default=0, description="Platform points earned")
    badge_earned: Optional[str] = Field(None, description="Badge name")
    unlock_message: str = Field(..., description="Congratulations message")

    # Examples:
    # - "first_connection": Made first connection
    # - "network_builder": 50 connections
    # - "super_connector": 500 connections
    # - "skill_master": 10 skill endorsements
    # - "thought_leader": 100 post likes
    # - "influencer": 1000 profile views


class ProfileUpdatedEvent(BaseModel):
    """Event for connection's profile update."""

    event_type: Literal["activity.profile_updated"] = "activity.profile_updated"
    timestamp: datetime = Field(default_factory=datetime.now)

    # Connection details
    user_id: int = Field(..., description="User who updated profile")
    user_name: str = Field(..., description="User name")
    user_photo_url: Optional[str] = Field(None, description="User photo")

    # Update details
    update_type: str = Field(..., description="Type of update")
    update_summary: str = Field(..., description="Update description")
    fields_updated: List[str] = Field(default_factory=list, description="Fields that changed")

    # Context
    is_significant: bool = Field(default=False, description="Major update")
    connection_strength: str = Field(default="medium", description="Connection strength")

    # Examples of update_type:
    # - "new_position": Started new job
    # - "new_education": Added education
    # - "new_certification": Added certification
    # - "headline_changed": Updated headline
    # - "location_changed": Changed location
    # - "photo_changed": Updated photo


# Export all event types
__all__ = [
    "ConnectionRequestEvent",
    "ConnectionAcceptedEvent",
    "ProfileViewedEvent",
    "SkillEndorsedEvent",
    "MessageReceivedEvent",
    "PostLikedEvent",
    "PostCommentedEvent",
    "PostSharedEvent",
    "NetworkActivityEvent",
    "AchievementUnlockedEvent",
    "ProfileUpdatedEvent",
]
