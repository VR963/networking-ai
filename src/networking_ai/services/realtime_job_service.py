"""
Realtime Job Service - Phase 11

WebSocket broadcasting service for live job feed updates.

Features:
- Broadcast new jobs to matching talent
- Send job updates to interested users
- Alert about expiring jobs
- Notify about high-quality matches
- Manage job alert subscriptions
- Batch feed updates

Integration:
    from networking_ai.services.realtime_job_service import RealtimeJobService

    job_service = RealtimeJobService(connection_manager)

    # When new job is posted
    await job_service.broadcast_job_posted(
        job_id=job.id,
        title=job.title,
        company_name=job.company.name,
        location=job.location,
        salary_range=job.salary_range,
        skills=job.required_skills,
        matched_user_ids=[1, 2, 3]  # Only send to matching users
    )
"""

import logging
from datetime import datetime
from typing import List, Optional, Dict, Any

from ..websocket.connection_manager import ConnectionManager
from ..websocket.job_events import (
    JobPostedEvent,
    JobUpdatedEvent,
    JobClosedEvent,
    JobExpiringEvent,
    JobMatchedEvent,
    JobSubscriptionCreatedEvent,
    JobSubscriptionDeletedEvent,
    JobFeedUpdateEvent,
)

logger = logging.getLogger(__name__)


class RealtimeJobService:
    """
    Realtime job broadcasting service.

    Handles WebSocket broadcasting for all job-related events.
    """

    def __init__(self, connection_manager: ConnectionManager):
        """
        Initialize realtime job service.

        Args:
            connection_manager: WebSocket connection manager
        """
        self.connection_manager = connection_manager
        logger.info("RealtimeJobService initialized")

    async def broadcast_job_posted(
        self,
        job_id: int,
        title: str,
        company_name: str,
        location: str,
        description_preview: str,
        job_type: str,
        matched_user_ids: List[int],
        company_logo: Optional[str] = None,
        remote_type: str = "on_site",
        salary_min: Optional[int] = None,
        salary_max: Optional[int] = None,
        salary_currency: str = "USD",
        salary_range: Optional[str] = None,
        skills: Optional[List[str]] = None,
        experience_min: Optional[int] = None,
        experience_max: Optional[int] = None,
        match_scores: Optional[Dict[int, float]] = None,
        match_reasons: Optional[Dict[int, List[str]]] = None,
        posted_at: Optional[datetime] = None,
        quick_apply: bool = False,
    ) -> int:
        """
        Broadcast new job posted to matching talent.

        Args:
            job_id: Job ID
            title: Job title
            company_name: Company name
            location: Job location
            description_preview: Job description preview (first 200 chars)
            job_type: Job type (full_time, part_time, contract)
            matched_user_ids: List of user IDs who match this job
            company_logo: Company logo URL
            remote_type: Remote type (on_site, hybrid, remote)
            salary_min: Minimum salary
            salary_max: Maximum salary
            salary_currency: Salary currency
            salary_range: Formatted salary range
            skills: Required skills
            experience_min: Minimum years of experience
            experience_max: Maximum years of experience
            match_scores: Dict mapping user_id -> match_score
            match_reasons: Dict mapping user_id -> list of match reasons
            posted_at: When job was posted
            quick_apply: Whether quick apply is supported

        Returns:
            Number of users notified
        """
        if not matched_user_ids:
            logger.debug(f"No matched users for job {job_id}, skipping broadcast")
            return 0

        skills = skills or []
        match_scores = match_scores or {}
        match_reasons = match_reasons or {}
        posted_at = posted_at or datetime.utcnow()

        logger.info(
            f"Broadcasting job.posted event for job {job_id} to {len(matched_user_ids)} users"
        )

        notified_count = 0

        for user_id in matched_user_ids:
            # Get user-specific match data
            user_match_score = match_scores.get(user_id)
            user_match_reasons = match_reasons.get(user_id, [])

            # Create user-specific event
            event = JobPostedEvent(
                job_id=job_id,
                title=title,
                company_name=company_name,
                company_logo=company_logo,
                location=location,
                remote_type=remote_type,
                salary_min=salary_min,
                salary_max=salary_max,
                salary_currency=salary_currency,
                salary_range=salary_range,
                skills=skills,
                experience_min=experience_min,
                experience_max=experience_max,
                match_score=user_match_score,
                match_reasons=user_match_reasons,
                description_preview=description_preview,
                job_type=job_type,
                posted_at=posted_at,
                action_url=f"/jobs/{job_id}",
                quick_apply=quick_apply,
            )

            # Send to this user
            await self.connection_manager.send_to_user(
                user_id=user_id, message=event.model_dump()
            )

            notified_count += 1

        logger.info(f"Job {job_id} broadcast sent to {notified_count} users")
        return notified_count

    async def broadcast_job_updated(
        self,
        job_id: int,
        title: str,
        company_name: str,
        updated_fields: List[str],
        update_summary: str,
        interested_user_ids: List[int],
        location: Optional[str] = None,
        remote_type: Optional[str] = None,
        salary_range: Optional[str] = None,
        skills: Optional[List[str]] = None,
    ) -> int:
        """
        Broadcast job update to interested users.

        Sent to users who have saved or applied to this job.

        Args:
            job_id: Job ID
            title: Job title
            company_name: Company name
            updated_fields: List of fields that were updated
            update_summary: Human-readable summary of changes
            interested_user_ids: Users who saved/applied to this job
            location: Updated location (if changed)
            remote_type: Updated remote type (if changed)
            salary_range: Updated salary range (if changed)
            skills: Updated skills (if changed)

        Returns:
            Number of users notified
        """
        if not interested_user_ids:
            logger.debug(f"No interested users for job {job_id}, skipping update broadcast")
            return 0

        logger.info(
            f"Broadcasting job.updated event for job {job_id} to {len(interested_user_ids)} users"
        )

        event = JobUpdatedEvent(
            job_id=job_id,
            title=title,
            company_name=company_name,
            updated_fields=updated_fields,
            update_summary=update_summary,
            location=location,
            remote_type=remote_type,
            salary_range=salary_range,
            skills=skills,
            action_url=f"/jobs/{job_id}",
        )

        notified_count = 0

        for user_id in interested_user_ids:
            await self.connection_manager.send_to_user(
                user_id=user_id, message=event.model_dump()
            )
            notified_count += 1

        logger.info(f"Job {job_id} update broadcast sent to {notified_count} users")
        return notified_count

    async def broadcast_job_closed(
        self,
        job_id: int,
        title: str,
        company_name: str,
        reason: str,
        message: str,
        interested_user_ids: List[int],
        similar_jobs: Optional[List[int]] = None,
    ) -> int:
        """
        Broadcast job closed notification.

        Sent to users who saved this job or have pending applications.

        Args:
            job_id: Job ID
            title: Job title
            company_name: Company name
            reason: Why job was closed (filled, expired, cancelled)
            message: Message to display to users
            interested_user_ids: Users who saved/applied to this job
            similar_jobs: IDs of similar open jobs

        Returns:
            Number of users notified
        """
        if not interested_user_ids:
            logger.debug(f"No interested users for job {job_id}, skipping closed broadcast")
            return 0

        similar_jobs = similar_jobs or []

        logger.info(
            f"Broadcasting job.closed event for job {job_id} to {len(interested_user_ids)} users"
        )

        event = JobClosedEvent(
            job_id=job_id,
            title=title,
            company_name=company_name,
            reason=reason,
            message=message,
            similar_jobs=similar_jobs,
            action_url=f"/jobs/search?similar_to={job_id}" if similar_jobs else None,
        )

        notified_count = 0

        for user_id in interested_user_ids:
            await self.connection_manager.send_to_user(
                user_id=user_id, message=event.model_dump()
            )
            notified_count += 1

        logger.info(f"Job {job_id} closed broadcast sent to {notified_count} users")
        return notified_count

    async def broadcast_job_expiring(
        self,
        job_id: int,
        title: str,
        company_name: str,
        expires_in_hours: int,
        expires_at: datetime,
        message: str,
        saved_by_user_ids: List[int],
        quick_apply: bool = False,
    ) -> int:
        """
        Broadcast job expiring alert.

        Sent to users who saved this job but haven't applied yet.

        Args:
            job_id: Job ID
            title: Job title
            company_name: Company name
            expires_in_hours: Hours until expiration
            expires_at: Exact expiration datetime
            message: Urgency message
            saved_by_user_ids: Users who saved but haven't applied
            quick_apply: Whether quick apply is supported

        Returns:
            Number of users notified
        """
        if not saved_by_user_ids:
            logger.debug(f"No saved users for job {job_id}, skipping expiring broadcast")
            return 0

        logger.info(
            f"Broadcasting job.expiring event for job {job_id} to {len(saved_by_user_ids)} users"
        )

        event = JobExpiringEvent(
            job_id=job_id,
            title=title,
            company_name=company_name,
            expires_in_hours=expires_in_hours,
            expires_at=expires_at,
            message=message,
            action_url=f"/jobs/{job_id}/apply",
            quick_apply=quick_apply,
        )

        notified_count = 0

        for user_id in saved_by_user_ids:
            await self.connection_manager.send_to_user(
                user_id=user_id, message=event.model_dump()
            )
            notified_count += 1

        logger.info(f"Job {job_id} expiring broadcast sent to {notified_count} users")
        return notified_count

    async def broadcast_job_matched(
        self,
        user_id: int,
        job_id: int,
        title: str,
        company_name: str,
        match_score: float,
        match_quality: str,
        match_reasons: List[str],
        location: str,
        remote_type: str,
        skills: List[str],
        description_preview: str,
        company_logo: Optional[str] = None,
        salary_range: Optional[str] = None,
        quick_apply: bool = False,
    ) -> bool:
        """
        Broadcast high-quality job match to a specific user.

        Sent when matching algorithm finds an excellent match.

        Args:
            user_id: User ID to notify
            job_id: Job ID
            title: Job title
            company_name: Company name
            match_score: Match score (0-1)
            match_quality: Match quality (excellent, good, fair)
            match_reasons: Reasons why this is a good match
            location: Job location
            remote_type: Remote type
            skills: Required skills
            description_preview: Job description preview
            company_logo: Company logo URL
            salary_range: Salary range
            quick_apply: Whether quick apply is supported

        Returns:
            True if sent successfully
        """
        logger.info(
            f"Broadcasting job.matched event for job {job_id} to user {user_id} (score: {match_score})"
        )

        event = JobMatchedEvent(
            job_id=job_id,
            title=title,
            company_name=company_name,
            company_logo=company_logo,
            match_score=match_score,
            match_quality=match_quality,
            match_reasons=match_reasons,
            location=location,
            remote_type=remote_type,
            salary_range=salary_range,
            skills=skills,
            description_preview=description_preview,
            action_url=f"/jobs/{job_id}",
            quick_apply=quick_apply,
        )

        await self.connection_manager.send_to_user(
            user_id=user_id, message=event.model_dump()
        )

        logger.info(f"Job match for job {job_id} sent to user {user_id}")
        return True

    async def broadcast_subscription_created(
        self,
        user_id: int,
        subscription_id: int,
        keywords: Optional[List[str]] = None,
        locations: Optional[List[str]] = None,
        remote_types: Optional[List[str]] = None,
        skills: Optional[List[str]] = None,
        salary_min: Optional[int] = None,
        frequency: str = "instant",
    ) -> bool:
        """
        Confirm job alert subscription created.

        Args:
            user_id: User ID
            subscription_id: Subscription ID
            keywords: Keyword filters
            locations: Location filters
            remote_types: Remote type filters
            skills: Skill filters
            salary_min: Minimum salary filter
            frequency: Notification frequency

        Returns:
            True if sent successfully
        """
        logger.info(
            f"Broadcasting job.subscription.created event for subscription {subscription_id} to user {user_id}"
        )

        message = "You'll receive instant notifications when jobs matching your criteria are posted!"
        if frequency == "daily":
            message = "You'll receive a daily digest of jobs matching your criteria!"
        elif frequency == "weekly":
            message = "You'll receive a weekly summary of jobs matching your criteria!"

        event = JobSubscriptionCreatedEvent(
            subscription_id=subscription_id,
            keywords=keywords,
            locations=locations,
            remote_types=remote_types,
            skills=skills,
            salary_min=salary_min,
            frequency=frequency,
            message=message,
        )

        await self.connection_manager.send_to_user(
            user_id=user_id, message=event.model_dump()
        )

        logger.info(f"Subscription {subscription_id} confirmation sent to user {user_id}")
        return True

    async def broadcast_subscription_deleted(
        self,
        user_id: int,
        subscription_id: int,
    ) -> bool:
        """
        Confirm job alert subscription deleted.

        Args:
            user_id: User ID
            subscription_id: Subscription ID that was deleted

        Returns:
            True if sent successfully
        """
        logger.info(
            f"Broadcasting job.subscription.deleted event for subscription {subscription_id} to user {user_id}"
        )

        event = JobSubscriptionDeletedEvent(
            subscription_id=subscription_id,
            message="Job alert subscription deleted successfully",
        )

        await self.connection_manager.send_to_user(
            user_id=user_id, message=event.model_dump()
        )

        logger.info(f"Subscription {subscription_id} deletion confirmed to user {user_id}")
        return True

    async def broadcast_feed_update(
        self,
        user_id: int,
        new_jobs_count: int,
        new_matches_count: int,
        expiring_jobs_count: int,
        top_matches: List[Dict[str, Any]],
        total_active_jobs: int,
        message: str,
    ) -> bool:
        """
        Broadcast batch feed update.

        Sent when user's job feed has been updated with multiple new jobs.
        Used for daily digest or when user opens app after being offline.

        Args:
            user_id: User ID
            new_jobs_count: Number of new jobs
            new_matches_count: Number of new matches
            expiring_jobs_count: Number of jobs expiring soon
            top_matches: Top 3 job matches (summary data)
            total_active_jobs: Total active jobs matching user
            message: Summary message

        Returns:
            True if sent successfully
        """
        logger.info(
            f"Broadcasting job.feed.update event to user {user_id} ({new_jobs_count} new jobs)"
        )

        event = JobFeedUpdateEvent(
            new_jobs_count=new_jobs_count,
            new_matches_count=new_matches_count,
            expiring_jobs_count=expiring_jobs_count,
            top_matches=top_matches,
            total_active_jobs=total_active_jobs,
            action_url="/jobs",
            message=message,
        )

        await self.connection_manager.send_to_user(
            user_id=user_id, message=event.model_dump()
        )

        logger.info(f"Feed update sent to user {user_id}")
        return True


# Helper function for easy import
def get_realtime_job_service(connection_manager: ConnectionManager) -> RealtimeJobService:
    """
    Get or create realtime job service instance.

    Args:
        connection_manager: WebSocket connection manager

    Returns:
        RealtimeJobService instance
    """
    return RealtimeJobService(connection_manager)
