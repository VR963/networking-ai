"""
Realtime Application Service - Phase 11

WebSocket broadcasting service for real-time application status updates.

Features:
- Broadcast status changes to applicants
- Notify when recruiters view applications
- Send interview scheduling and reminders
- Deliver job offers and updates
- Share recruiter feedback
- Provide timeline updates
- Forward recruiter messages

Integration:
    from networking_ai.services.realtime_application_service import RealtimeApplicationService

    app_service = RealtimeApplicationService(connection_manager)

    # When application status changes
    await app_service.broadcast_status_changed(
        user_id=1,
        application_id=123,
        job_id=456,
        job_title="Senior Python Developer",
        company_name="TechCorp",
        old_status="applied",
        new_status="under_review"
    )
"""

import logging
from datetime import datetime
from typing import List, Optional, Dict, Any

from ..websocket.connection_manager import ConnectionManager
from ..websocket.application_events import (
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

logger = logging.getLogger(__name__)


class RealtimeApplicationService:
    """
    Realtime application broadcasting service.

    Handles WebSocket broadcasting for all application-related events.
    """

    def __init__(self, connection_manager: ConnectionManager):
        """
        Initialize realtime application service.

        Args:
            connection_manager: WebSocket connection manager
        """
        self.connection_manager = connection_manager
        logger.info("RealtimeApplicationService initialized")

    async def broadcast_status_changed(
        self,
        user_id: int,
        application_id: int,
        job_id: int,
        job_title: str,
        company_name: str,
        old_status: str,
        new_status: str,
        status_display: str,
        message: str,
        days_since_applied: int,
        company_logo: Optional[str] = None,
        next_steps: Optional[List[str]] = None,
        estimated_decision_days: Optional[int] = None,
    ) -> bool:
        """
        Broadcast application status change to user.

        Args:
            user_id: User ID (applicant)
            application_id: Application ID
            job_id: Job ID
            job_title: Job title
            company_name: Company name
            old_status: Previous status
            new_status: New status
            status_display: Human-readable new status
            message: Status change message
            days_since_applied: Days since application submitted
            company_logo: Company logo URL
            next_steps: What to do next
            estimated_decision_days: Days until expected decision

        Returns:
            True if sent successfully
        """
        logger.info(
            f"Broadcasting status change for application {application_id}: {old_status} -> {new_status}"
        )

        event = ApplicationStatusChangedEvent(
            application_id=application_id,
            job_id=job_id,
            job_title=job_title,
            company_name=company_name,
            company_logo=company_logo,
            old_status=old_status,
            new_status=new_status,
            status_display=status_display,
            message=message,
            next_steps=next_steps or [],
            days_since_applied=days_since_applied,
            estimated_decision_days=estimated_decision_days,
            action_url=f"/applications/{application_id}",
        )

        await self.connection_manager.send_to_user(
            user_id=user_id, message=event.model_dump()
        )

        logger.info(f"Status change for application {application_id} sent to user {user_id}")
        return True

    async def broadcast_recruiter_viewed(
        self,
        user_id: int,
        application_id: int,
        job_id: int,
        job_title: str,
        company_name: str,
        recruiter_name: Optional[str] = None,
        recruiter_title: Optional[str] = None,
        view_duration_seconds: Optional[int] = None,
        sections_viewed: Optional[List[str]] = None,
    ) -> bool:
        """
        Notify user that recruiter viewed their application.

        Args:
            user_id: User ID (applicant)
            application_id: Application ID
            job_id: Job ID
            job_title: Job title
            company_name: Company name
            recruiter_name: Recruiter name
            recruiter_title: Recruiter title
            view_duration_seconds: How long they viewed
            sections_viewed: Which sections they viewed

        Returns:
            True if sent successfully
        """
        logger.info(
            f"Broadcasting recruiter view for application {application_id} to user {user_id}"
        )

        # Build message
        if recruiter_name and recruiter_title:
            message = f"{recruiter_name} ({recruiter_title}) viewed your application"
        elif recruiter_name:
            message = f"{recruiter_name} viewed your application"
        else:
            message = f"A recruiter at {company_name} viewed your application"

        event = RecruiterViewedEvent(
            application_id=application_id,
            job_id=job_id,
            job_title=job_title,
            company_name=company_name,
            recruiter_name=recruiter_name,
            recruiter_title=recruiter_title,
            view_duration_seconds=view_duration_seconds,
            sections_viewed=sections_viewed,
            message=message,
            action_url=f"/applications/{application_id}",
        )

        await self.connection_manager.send_to_user(
            user_id=user_id, message=event.model_dump()
        )

        logger.info(f"Recruiter view notification sent to user {user_id}")
        return True

    async def broadcast_interview_scheduled(
        self,
        user_id: int,
        application_id: int,
        interview_id: int,
        job_id: int,
        job_title: str,
        company_name: str,
        interview_type: str,
        interview_round: int,
        scheduled_at: datetime,
        duration_minutes: int,
        interviewer_names: Optional[List[str]] = None,
        interviewer_titles: Optional[List[str]] = None,
        location: Optional[str] = None,
        video_link: Optional[str] = None,
        phone_number: Optional[str] = None,
        preparation_notes: Optional[str] = None,
        topics_to_cover: Optional[List[str]] = None,
    ) -> bool:
        """
        Notify user that interview has been scheduled.

        Args:
            user_id: User ID (applicant)
            application_id: Application ID
            interview_id: Interview ID
            job_id: Job ID
            job_title: Job title
            company_name: Company name
            interview_type: Interview type (phone, video, onsite, technical)
            interview_round: Interview round number
            scheduled_at: Interview date/time
            duration_minutes: Interview duration
            interviewer_names: Interviewer names
            interviewer_titles: Interviewer titles
            location: Physical location (for onsite)
            video_link: Video call link
            phone_number: Phone number (for phone interviews)
            preparation_notes: Preparation instructions
            topics_to_cover: Topics that will be covered

        Returns:
            True if sent successfully
        """
        logger.info(
            f"Broadcasting interview scheduled for application {application_id} to user {user_id}"
        )

        # Format message
        interview_date_str = scheduled_at.strftime("%b %d at %I:%M %p")
        message = f"Interview scheduled for {interview_date_str}"

        event = InterviewScheduledEvent(
            application_id=application_id,
            interview_id=interview_id,
            job_id=job_id,
            job_title=job_title,
            company_name=company_name,
            interview_type=interview_type,
            interview_round=interview_round,
            scheduled_at=scheduled_at,
            duration_minutes=duration_minutes,
            location=location,
            video_link=video_link,
            phone_number=phone_number,
            interviewer_names=interviewer_names or [],
            interviewer_titles=interviewer_titles or [],
            preparation_notes=preparation_notes,
            topics_to_cover=topics_to_cover,
            message=message,
            action_url=f"/applications/{application_id}/interviews/{interview_id}",
            calendar_link=f"/applications/{application_id}/interviews/{interview_id}/calendar",
        )

        await self.connection_manager.send_to_user(
            user_id=user_id, message=event.model_dump()
        )

        logger.info(f"Interview scheduled notification sent to user {user_id}")
        return True

    async def broadcast_interview_reminder(
        self,
        user_id: int,
        application_id: int,
        interview_id: int,
        job_title: str,
        company_name: str,
        interview_type: str,
        scheduled_at: datetime,
        hours_until_interview: int,
        video_link: Optional[str] = None,
        location: Optional[str] = None,
    ) -> bool:
        """
        Send interview reminder to user.

        Args:
            user_id: User ID (applicant)
            application_id: Application ID
            interview_id: Interview ID
            job_title: Job title
            company_name: Company name
            interview_type: Interview type
            scheduled_at: Interview date/time
            hours_until_interview: Hours until interview
            video_link: Video call link
            location: Location

        Returns:
            True if sent successfully
        """
        logger.info(
            f"Broadcasting interview reminder ({hours_until_interview}h) for application {application_id}"
        )

        # Format message based on timing
        if hours_until_interview <= 1:
            time_str = scheduled_at.strftime("%I:%M %p")
            message = f"Interview in {hours_until_interview} hour! Join {interview_type} at {time_str}"
        elif hours_until_interview <= 24:
            message = f"Interview in {hours_until_interview} hours with {company_name}"
        else:
            message = f"Upcoming interview with {company_name} in {hours_until_interview // 24} days"

        event = InterviewReminderEvent(
            application_id=application_id,
            interview_id=interview_id,
            job_title=job_title,
            company_name=company_name,
            interview_type=interview_type,
            scheduled_at=scheduled_at,
            hours_until_interview=hours_until_interview,
            video_link=video_link,
            location=location,
            message=message,
            action_url=f"/applications/{application_id}/interviews/{interview_id}",
        )

        await self.connection_manager.send_to_user(
            user_id=user_id, message=event.model_dump()
        )

        logger.info(f"Interview reminder sent to user {user_id}")
        return True

    async def broadcast_offer_extended(
        self,
        user_id: int,
        application_id: int,
        offer_id: int,
        job_id: int,
        job_title: str,
        company_name: str,
        salary: int,
        offer_expires_at: datetime,
        days_to_decide: int,
        company_logo: Optional[str] = None,
        salary_currency: str = "USD",
        signing_bonus: Optional[int] = None,
        equity_value: Optional[int] = None,
        benefits_summary: Optional[List[str]] = None,
        start_date: Optional[datetime] = None,
    ) -> bool:
        """
        Notify user that job offer has been extended.

        Args:
            user_id: User ID (applicant)
            application_id: Application ID
            offer_id: Offer ID
            job_id: Job ID
            job_title: Job title
            company_name: Company name
            salary: Annual salary
            offer_expires_at: Offer expiration date
            days_to_decide: Days remaining to accept
            company_logo: Company logo URL
            salary_currency: Currency
            signing_bonus: Signing bonus
            equity_value: Equity value
            benefits_summary: Key benefits
            start_date: Proposed start date

        Returns:
            True if sent successfully
        """
        logger.info(
            f"Broadcasting offer extended for application {application_id} to user {user_id}"
        )

        # Format salary
        salary_formatted = f"${salary:,}/year" if salary_currency == "USD" else f"{salary:,} {salary_currency}/year"

        event = OfferExtendedEvent(
            application_id=application_id,
            offer_id=offer_id,
            job_id=job_id,
            job_title=job_title,
            company_name=company_name,
            company_logo=company_logo,
            salary=salary,
            salary_currency=salary_currency,
            salary_formatted=salary_formatted,
            signing_bonus=signing_bonus,
            equity_value=equity_value,
            benefits_summary=benefits_summary,
            offer_expires_at=offer_expires_at,
            days_to_decide=days_to_decide,
            start_date=start_date,
            message=f"Congratulations! {company_name} has extended you a job offer!",
            action_url=f"/applications/{application_id}/offer",
            accept_url=f"/applications/{application_id}/offer/accept",
            negotiate_url=f"/applications/{application_id}/offer/negotiate",
        )

        await self.connection_manager.send_to_user(
            user_id=user_id, message=event.model_dump()
        )

        logger.info(f"Offer extended notification sent to user {user_id}")
        return True

    async def broadcast_offer_updated(
        self,
        user_id: int,
        application_id: int,
        offer_id: int,
        job_title: str,
        company_name: str,
        updated_fields: List[str],
        update_summary: str,
        new_salary: Optional[int] = None,
        new_signing_bonus: Optional[int] = None,
        new_equity_value: Optional[int] = None,
        new_start_date: Optional[datetime] = None,
    ) -> bool:
        """
        Notify user that offer terms have been updated.

        Args:
            user_id: User ID (applicant)
            application_id: Application ID
            offer_id: Offer ID
            job_title: Job title
            company_name: Company name
            updated_fields: Fields that were updated
            update_summary: Summary of changes
            new_salary: Updated salary
            new_signing_bonus: Updated signing bonus
            new_equity_value: Updated equity
            new_start_date: Updated start date

        Returns:
            True if sent successfully
        """
        logger.info(
            f"Broadcasting offer update for application {application_id} to user {user_id}"
        )

        event = OfferUpdatedEvent(
            application_id=application_id,
            offer_id=offer_id,
            job_title=job_title,
            company_name=company_name,
            updated_fields=updated_fields,
            update_summary=update_summary,
            new_salary=new_salary,
            new_signing_bonus=new_signing_bonus,
            new_equity_value=new_equity_value,
            new_start_date=new_start_date,
            message="Great news! The offer has been updated with improved terms",
            action_url=f"/applications/{application_id}/offer",
        )

        await self.connection_manager.send_to_user(
            user_id=user_id, message=event.model_dump()
        )

        logger.info(f"Offer update notification sent to user {user_id}")
        return True

    async def broadcast_feedback_received(
        self,
        user_id: int,
        application_id: int,
        job_title: str,
        company_name: str,
        feedback_type: str,
        feedback_stage: str,
        feedback_summary: str,
        overall_sentiment: str,
        strengths: Optional[List[str]] = None,
        areas_to_improve: Optional[List[str]] = None,
    ) -> bool:
        """
        Notify user that feedback has been received.

        Args:
            user_id: User ID (applicant)
            application_id: Application ID
            job_title: Job title
            company_name: Company name
            feedback_type: Type (interview, application, assessment)
            feedback_stage: Which stage
            feedback_summary: Summary of feedback
            overall_sentiment: Sentiment (positive, neutral, negative)
            strengths: Highlighted strengths
            areas_to_improve: Areas for improvement

        Returns:
            True if sent successfully
        """
        logger.info(
            f"Broadcasting feedback for application {application_id} to user {user_id}"
        )

        # Format message based on sentiment
        if overall_sentiment == "positive":
            message = f"You've received positive feedback from your {feedback_stage.replace('_', ' ')}"
        elif overall_sentiment == "negative":
            message = f"You've received feedback from your {feedback_stage.replace('_', ' ')}"
        else:
            message = f"You've received feedback from your {feedback_stage.replace('_', ' ')}"

        event = FeedbackReceivedEvent(
            application_id=application_id,
            job_title=job_title,
            company_name=company_name,
            feedback_type=feedback_type,
            feedback_stage=feedback_stage,
            feedback_summary=feedback_summary,
            strengths=strengths,
            areas_to_improve=areas_to_improve,
            overall_sentiment=overall_sentiment,
            message=message,
            action_url=f"/applications/{application_id}/feedback",
        )

        await self.connection_manager.send_to_user(
            user_id=user_id, message=event.model_dump()
        )

        logger.info(f"Feedback notification sent to user {user_id}")
        return True

    async def broadcast_timeline_updated(
        self,
        user_id: int,
        application_id: int,
        job_title: str,
        company_name: str,
        current_stage: str,
        completed_stages: List[str],
        upcoming_stages: List[str],
        next_step: str,
        expected_next_update: Optional[datetime] = None,
        days_until_next_step: Optional[int] = None,
    ) -> bool:
        """
        Notify user that application timeline has been updated.

        Args:
            user_id: User ID (applicant)
            application_id: Application ID
            job_title: Job title
            company_name: Company name
            current_stage: Current pipeline stage
            completed_stages: Completed stages
            upcoming_stages: Upcoming stages
            next_step: Next expected step
            expected_next_update: When to expect next update
            days_until_next_step: Days until next step

        Returns:
            True if sent successfully
        """
        logger.info(
            f"Broadcasting timeline update for application {application_id} to user {user_id}"
        )

        event = TimelineUpdatedEvent(
            application_id=application_id,
            job_title=job_title,
            company_name=company_name,
            current_stage=current_stage,
            completed_stages=completed_stages,
            upcoming_stages=upcoming_stages,
            next_step=next_step,
            expected_next_update=expected_next_update,
            days_until_next_step=days_until_next_step,
            message="Your application timeline has been updated",
            action_url=f"/applications/{application_id}/timeline",
        )

        await self.connection_manager.send_to_user(
            user_id=user_id, message=event.model_dump()
        )

        logger.info(f"Timeline update sent to user {user_id}")
        return True

    async def broadcast_message_received(
        self,
        user_id: int,
        application_id: int,
        message_id: int,
        job_title: str,
        company_name: str,
        sender_name: str,
        sender_title: str,
        subject: str,
        message_preview: str,
        sender_avatar: Optional[str] = None,
        priority: str = "normal",
    ) -> bool:
        """
        Notify user that message has been received from recruiter.

        Args:
            user_id: User ID (applicant)
            application_id: Application ID
            message_id: Message ID
            job_title: Job title
            company_name: Company name
            sender_name: Recruiter name
            sender_title: Recruiter title
            subject: Message subject
            message_preview: First 100 chars of message
            sender_avatar: Recruiter avatar URL
            priority: Priority (urgent, normal)

        Returns:
            True if sent successfully
        """
        logger.info(
            f"Broadcasting message for application {application_id} to user {user_id}"
        )

        event = MessageReceivedEvent(
            application_id=application_id,
            message_id=message_id,
            job_title=job_title,
            company_name=company_name,
            sender_name=sender_name,
            sender_title=sender_title,
            sender_avatar=sender_avatar,
            subject=subject,
            message_preview=message_preview,
            priority=priority,
            action_url=f"/applications/{application_id}/messages/{message_id}",
            reply_url=f"/applications/{application_id}/messages/{message_id}/reply",
        )

        await self.connection_manager.send_to_user(
            user_id=user_id, message=event.model_dump()
        )

        logger.info(f"Message notification sent to user {user_id}")
        return True


# Helper function for easy import
def get_realtime_application_service(
    connection_manager: ConnectionManager,
) -> RealtimeApplicationService:
    """
    Get or create realtime application service instance.

    Args:
        connection_manager: WebSocket connection manager

    Returns:
        RealtimeApplicationService instance
    """
    return RealtimeApplicationService(connection_manager)
