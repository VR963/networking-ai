"""
Interview Scheduling Service - Phase 4.

Handles interview scheduling, availability management, and interview lifecycle.

Features:
- Find available time slots based on interviewer availability
- Schedule interviews with calendar integration
- Send interview invitations and reminders
- Handle confirmations, cancellations, and rescheduling
- Track interview status and completion
"""

from datetime import datetime, timedelta
from typing import Optional, List, Dict, Tuple
from sqlalchemy.orm import Session
from sqlalchemy import and_, or_

from ..models.interview import (
    Interview,
    InterviewAvailability,
    InterviewStage,
    InterviewStatus,
    InterviewFormat
)
from ..models.application import Application
from ..models.job import Job
from ..models.user import User
from ..models.notification import NotificationType, NotificationPriority


class InterviewSchedulingService:
    """
    Service for scheduling and managing interviews.

    Handles the complete interview lifecycle from scheduling to completion.
    """

    def __init__(
        self,
        notification_service=None,
        calendar_service=None,
        enable_notifications: bool = True
    ):
        """
        Initialize the interview scheduling service.

        Args:
            notification_service: Optional notification service for sending alerts
            calendar_service: Optional calendar service for calendar integration
            enable_notifications: Whether to send notifications (default True)
        """
        self.notification_service = notification_service
        self.calendar_service = calendar_service
        self.enable_notifications = enable_notifications

    # ==================== Availability Management ====================

    def add_availability(
        self,
        user_id: int,
        start_time: datetime,
        end_time: datetime,
        timezone: str = "UTC",
        is_recurring: bool = False,
        recurrence_rule: Optional[str] = None,
        max_interviews_per_day: int = 4,
        db: Session = None
    ) -> InterviewAvailability:
        """
        Add interviewer availability slot.

        Args:
            user_id: Interviewer's user ID
            start_time: Availability window start
            end_time: Availability window end
            timezone: Timezone for the availability
            is_recurring: Whether this is a recurring slot
            recurrence_rule: RRULE format for recurring slots
            max_interviews_per_day: Max interviews per day
            db: Database session

        Returns:
            Created InterviewAvailability object
        """
        availability = InterviewAvailability(
            user_id=user_id,
            start_time=start_time,
            end_time=end_time,
            timezone=timezone,
            is_recurring=is_recurring,
            recurrence_rule=recurrence_rule,
            max_interviews_per_day=max_interviews_per_day,
            is_available=True
        )

        db.add(availability)
        db.commit()
        db.refresh(availability)

        return availability

    def get_interviewer_availability(
        self,
        user_id: int,
        start_date: datetime,
        end_date: datetime,
        db: Session
    ) -> List[InterviewAvailability]:
        """
        Get all availability slots for an interviewer in a date range.

        Args:
            user_id: Interviewer's user ID
            start_date: Start of date range
            end_date: End of date range
            db: Database session

        Returns:
            List of availability slots
        """
        return db.query(InterviewAvailability).filter(
            and_(
                InterviewAvailability.user_id == user_id,
                InterviewAvailability.is_available == True,
                or_(
                    # Overlapping availability
                    and_(
                        InterviewAvailability.start_time <= end_date,
                        InterviewAvailability.end_time >= start_date
                    ),
                    # Recurring availability
                    InterviewAvailability.is_recurring == True
                )
            )
        ).all()

    def find_available_slots(
        self,
        interviewer_user_id: int,
        start_date: datetime,
        end_date: datetime,
        duration_minutes: int = 60,
        db: Session = None
    ) -> List[Dict]:
        """
        Find all available time slots for scheduling an interview.

        Args:
            interviewer_user_id: Interviewer's user ID
            start_date: Start of search window
            end_date: End of search window
            duration_minutes: Interview duration
            db: Database session

        Returns:
            List of available slots with start/end times
        """
        # Get interviewer availability
        availability_slots = self.get_interviewer_availability(
            user_id=interviewer_user_id,
            start_date=start_date,
            end_date=end_date,
            db=db
        )

        # Get existing interviews
        existing_interviews = db.query(Interview).filter(
            and_(
                Interview.interviewer_user_id == interviewer_user_id,
                Interview.scheduled_at >= start_date,
                Interview.scheduled_at <= end_date,
                Interview.status.in_([
                    InterviewStatus.SCHEDULED,
                    InterviewStatus.CONFIRMED,
                    InterviewStatus.REMINDED,
                    InterviewStatus.IN_PROGRESS
                ])
            )
        ).all()

        # Find free slots
        free_slots = []

        for avail in availability_slots:
            current_time = max(avail.start_time, start_date)
            slot_end = min(avail.end_time, end_date)

            while current_time + timedelta(minutes=duration_minutes) <= slot_end:
                proposed_end = current_time + timedelta(minutes=duration_minutes)

                # Check if this slot conflicts with existing interviews
                has_conflict = False
                for interview in existing_interviews:
                    interview_end = interview.scheduled_at + timedelta(
                        minutes=interview.duration_minutes
                    )

                    # Check for overlap
                    if (current_time < interview_end and
                        proposed_end > interview.scheduled_at):
                        has_conflict = True
                        break

                if not has_conflict:
                    free_slots.append({
                        "start_time": current_time,
                        "end_time": proposed_end,
                        "duration_minutes": duration_minutes,
                        "timezone": avail.timezone
                    })

                # Move to next slot (30-minute increments)
                current_time += timedelta(minutes=30)

        return free_slots

    # ==================== Interview Scheduling ====================

    def schedule_interview(
        self,
        application_id: int,
        job_id: int,
        company_id: int,
        candidate_user_id: int,
        interviewer_user_id: int,
        stage: InterviewStage,
        scheduled_at: datetime,
        duration_minutes: int = 60,
        format: InterviewFormat = InterviewFormat.VIDEO,
        timezone: str = "UTC",
        meeting_url: Optional[str] = None,
        meeting_id: Optional[str] = None,
        meeting_password: Optional[str] = None,
        preparation_materials: Optional[Dict] = None,
        interview_questions: Optional[List[str]] = None,
        db: Session = None
    ) -> Interview:
        """
        Schedule a new interview.

        Args:
            application_id: Related application ID
            job_id: Related job ID
            company_id: Company ID
            candidate_user_id: Candidate's user ID
            interviewer_user_id: Interviewer's user ID
            stage: Interview stage
            scheduled_at: When the interview is scheduled
            duration_minutes: Interview duration
            format: Interview format (video, phone, in-person)
            timezone: Timezone for the interview
            meeting_url: Video meeting URL
            meeting_id: Meeting ID
            meeting_password: Meeting password
            preparation_materials: Materials for candidate preparation
            interview_questions: Suggested interview questions
            db: Database session

        Returns:
            Created Interview object
        """
        # Create interview
        interview = Interview(
            application_id=application_id,
            job_id=job_id,
            company_id=company_id,
            candidate_user_id=candidate_user_id,
            interviewer_user_id=interviewer_user_id,
            stage=stage,
            status=InterviewStatus.SCHEDULED,
            format=format,
            scheduled_at=scheduled_at,
            duration_minutes=duration_minutes,
            timezone=timezone,
            meeting_url=meeting_url,
            meeting_id=meeting_id,
            meeting_password=meeting_password,
            preparation_materials=preparation_materials,
            interview_questions=interview_questions
        )

        db.add(interview)
        db.commit()
        db.refresh(interview)

        # Create calendar events if calendar service is available
        if self.calendar_service:
            try:
                # Create event for candidate
                candidate_event_id = self.calendar_service.create_event(
                    user_id=candidate_user_id,
                    title=f"Interview: {stage.value}",
                    start_time=scheduled_at,
                    duration_minutes=duration_minutes,
                    meeting_url=meeting_url,
                    db=db
                )

                # Create event for interviewer
                interviewer_event_id = self.calendar_service.create_event(
                    user_id=interviewer_user_id,
                    title=f"Interview with candidate",
                    start_time=scheduled_at,
                    duration_minutes=duration_minutes,
                    meeting_url=meeting_url,
                    db=db
                )

                # Update interview with calendar event IDs
                interview.calendar_event_id = candidate_event_id
                db.commit()

            except Exception as e:
                # Calendar integration is optional, continue if it fails
                print(f"Calendar event creation failed: {e}")

        # Send notifications
        if self.enable_notifications and self.notification_service:
            self._send_interview_scheduled_notifications(interview, db)

        return interview

    def confirm_interview(
        self,
        interview_id: int,
        user_id: int,
        db: Session
    ) -> bool:
        """
        Confirm interview attendance.

        Args:
            interview_id: Interview ID
            user_id: User confirming (candidate or interviewer)
            db: Database session

        Returns:
            True if confirmed successfully
        """
        interview = db.query(Interview).filter(
            Interview.id == interview_id
        ).first()

        if not interview:
            return False

        # Mark calendar as confirmed
        if user_id == interview.candidate_user_id:
            interview.candidate_calendar_confirmed = True
        elif user_id == interview.interviewer_user_id:
            interview.interviewer_calendar_confirmed = True
        else:
            return False

        # If both confirmed, update status
        if (interview.candidate_calendar_confirmed and
            interview.interviewer_calendar_confirmed):
            interview.status = InterviewStatus.CONFIRMED

        db.commit()

        return True

    def reschedule_interview(
        self,
        interview_id: int,
        new_scheduled_at: datetime,
        reschedule_reason: Optional[str] = None,
        db: Session = None
    ) -> Optional[Interview]:
        """
        Reschedule an existing interview.

        Args:
            interview_id: Original interview ID
            new_scheduled_at: New date/time
            reschedule_reason: Reason for rescheduling
            db: Database session

        Returns:
            New Interview object, or None if failed
        """
        # Get original interview
        original_interview = db.query(Interview).filter(
            Interview.id == interview_id
        ).first()

        if not original_interview:
            return None

        # Mark original as rescheduled
        original_interview.status = InterviewStatus.RESCHEDULED
        original_interview.cancellation_reason = reschedule_reason
        db.commit()

        # Create new interview with same details but new time
        new_interview = Interview(
            application_id=original_interview.application_id,
            job_id=original_interview.job_id,
            company_id=original_interview.company_id,
            candidate_user_id=original_interview.candidate_user_id,
            interviewer_user_id=original_interview.interviewer_user_id,
            stage=original_interview.stage,
            status=InterviewStatus.SCHEDULED,
            format=original_interview.format,
            scheduled_at=new_scheduled_at,
            duration_minutes=original_interview.duration_minutes,
            timezone=original_interview.timezone,
            meeting_url=original_interview.meeting_url,
            meeting_id=original_interview.meeting_id,
            meeting_password=original_interview.meeting_password,
            preparation_materials=original_interview.preparation_materials,
            interview_questions=original_interview.interview_questions,
            rescheduled_from_interview_id=interview_id
        )

        db.add(new_interview)
        db.commit()
        db.refresh(new_interview)

        # Send notifications
        if self.enable_notifications and self.notification_service:
            self._send_interview_rescheduled_notifications(
                new_interview,
                original_interview.scheduled_at,
                db
            )

        return new_interview

    def cancel_interview(
        self,
        interview_id: int,
        cancelled_by_user_id: int,
        reason: str,
        db: Session
    ) -> bool:
        """
        Cancel an interview.

        Args:
            interview_id: Interview ID
            cancelled_by_user_id: User who cancelled
            reason: Cancellation reason
            db: Database session

        Returns:
            True if cancelled successfully
        """
        interview = db.query(Interview).filter(
            Interview.id == interview_id
        ).first()

        if not interview:
            return False

        interview.mark_cancelled(cancelled_by_user_id, reason)
        db.commit()

        # Cancel calendar events
        if self.calendar_service and interview.calendar_event_id:
            try:
                self.calendar_service.cancel_event(
                    event_id=interview.calendar_event_id,
                    db=db
                )
            except Exception as e:
                print(f"Calendar event cancellation failed: {e}")

        # Send notifications
        if self.enable_notifications and self.notification_service:
            self._send_interview_cancelled_notifications(interview, reason, db)

        return True

    # ==================== Interview Lifecycle ====================

    def start_interview(
        self,
        interview_id: int,
        db: Session
    ) -> bool:
        """
        Mark interview as started.

        Args:
            interview_id: Interview ID
            db: Database session

        Returns:
            True if started successfully
        """
        interview = db.query(Interview).filter(
            Interview.id == interview_id
        ).first()

        if not interview:
            return False

        interview.mark_started()
        db.commit()

        return True

    def complete_interview(
        self,
        interview_id: int,
        db: Session
    ) -> bool:
        """
        Mark interview as completed.

        Args:
            interview_id: Interview ID
            db: Database session

        Returns:
            True if completed successfully
        """
        interview = db.query(Interview).filter(
            Interview.id == interview_id
        ).first()

        if not interview:
            return False

        interview.mark_completed()
        db.commit()

        return True

    def mark_no_show(
        self,
        interview_id: int,
        db: Session
    ) -> bool:
        """
        Mark interview as no-show.

        Args:
            interview_id: Interview ID
            db: Database session

        Returns:
            True if marked successfully
        """
        interview = db.query(Interview).filter(
            Interview.id == interview_id
        ).first()

        if not interview:
            return False

        interview.mark_no_show()
        db.commit()

        return True

    # ==================== Reminders ====================

    def send_interview_reminders(
        self,
        db: Session
    ) -> Dict[str, int]:
        """
        Send interview reminders for upcoming interviews.

        Checks all upcoming interviews and sends 24h and 1h reminders.

        Args:
            db: Database session

        Returns:
            Dict with counts of reminders sent
        """
        results = {
            "24h_reminders": 0,
            "1h_reminders": 0
        }

        # Get all upcoming interviews
        upcoming_interviews = db.query(Interview).filter(
            Interview.status.in_([
                InterviewStatus.SCHEDULED,
                InterviewStatus.CONFIRMED
            ]),
            Interview.scheduled_at > datetime.utcnow()
        ).all()

        for interview in upcoming_interviews:
            # Check 24h reminder
            if interview.needs_24h_reminder():
                self._send_24h_reminder(interview, db)
                interview.reminder_24h_sent = True
                interview.reminder_24h_sent_at = datetime.utcnow()
                interview.status = InterviewStatus.REMINDED
                results["24h_reminders"] += 1

            # Check 1h reminder
            if interview.needs_1h_reminder():
                self._send_1h_reminder(interview, db)
                interview.reminder_1h_sent = True
                interview.reminder_1h_sent_at = datetime.utcnow()
                interview.status = InterviewStatus.REMINDED
                results["1h_reminders"] += 1

        db.commit()

        return results

    # ==================== Query Methods ====================

    def get_interview(
        self,
        interview_id: int,
        db: Session
    ) -> Optional[Interview]:
        """Get interview by ID."""
        return db.query(Interview).filter(
            Interview.id == interview_id
        ).first()

    def get_interviews_for_candidate(
        self,
        candidate_user_id: int,
        db: Session,
        upcoming_only: bool = False
    ) -> List[Interview]:
        """Get all interviews for a candidate."""
        query = db.query(Interview).filter(
            Interview.candidate_user_id == candidate_user_id
        )

        if upcoming_only:
            query = query.filter(
                Interview.scheduled_at > datetime.utcnow(),
                Interview.status.in_([
                    InterviewStatus.SCHEDULED,
                    InterviewStatus.CONFIRMED,
                    InterviewStatus.REMINDED
                ])
            )

        return query.order_by(Interview.scheduled_at.desc()).all()

    def get_interviews_for_interviewer(
        self,
        interviewer_user_id: int,
        db: Session,
        upcoming_only: bool = False
    ) -> List[Interview]:
        """Get all interviews for an interviewer."""
        query = db.query(Interview).filter(
            Interview.interviewer_user_id == interviewer_user_id
        )

        if upcoming_only:
            query = query.filter(
                Interview.scheduled_at > datetime.utcnow(),
                Interview.status.in_([
                    InterviewStatus.SCHEDULED,
                    InterviewStatus.CONFIRMED,
                    InterviewStatus.REMINDED
                ])
            )

        return query.order_by(Interview.scheduled_at).all()

    def get_interviews_for_application(
        self,
        application_id: int,
        db: Session
    ) -> List[Interview]:
        """Get all interviews for an application."""
        return db.query(Interview).filter(
            Interview.application_id == application_id
        ).order_by(Interview.scheduled_at).all()

    # ==================== Private Helper Methods ====================

    def _send_interview_scheduled_notifications(
        self,
        interview: Interview,
        db: Session
    ):
        """Send notifications when interview is scheduled."""
        if not self.notification_service:
            return

        # Get job details
        job = db.query(Job).filter(Job.id == interview.job_id).first()

        # Notify candidate
        self.notification_service.create_notification(
            user_id=interview.candidate_user_id,
            notification_type=NotificationType.INTERVIEW_SCHEDULED,
            title=f"Interview Scheduled: {interview.stage.value}",
            message=f"Your {interview.stage.value} interview for {job.title if job else 'position'} is scheduled for {interview.scheduled_at.strftime('%B %d, %Y at %I:%M %p')}",
            channels=["in_app", "email"],
            priority=NotificationPriority.HIGH,
            action_url=f"/interviews/{interview.id}",
            action_text="View Interview Details",
            metadata={
                "interview_id": interview.id,
                "job_id": interview.job_id,
                "scheduled_at": interview.scheduled_at.isoformat()
            },
            db=db
        )

        # Notify interviewer
        self.notification_service.create_notification(
            user_id=interview.interviewer_user_id,
            notification_type=NotificationType.INTERVIEW_SCHEDULED,
            title="New Interview Scheduled",
            message=f"You have a {interview.stage.value} interview scheduled for {interview.scheduled_at.strftime('%B %d, %Y at %I:%M %p')}",
            channels=["in_app", "email"],
            priority=NotificationPriority.HIGH,
            action_url=f"/interviews/{interview.id}",
            action_text="View Interview Details",
            metadata={
                "interview_id": interview.id,
                "job_id": interview.job_id,
                "scheduled_at": interview.scheduled_at.isoformat()
            },
            db=db
        )

    def _send_interview_rescheduled_notifications(
        self,
        new_interview: Interview,
        original_time: datetime,
        db: Session
    ):
        """Send notifications when interview is rescheduled."""
        if not self.notification_service:
            return

        # Notify candidate
        self.notification_service.create_notification(
            user_id=new_interview.candidate_user_id,
            notification_type=NotificationType.INTERVIEW_RESCHEDULED,
            title="Interview Rescheduled",
            message=f"Your interview has been rescheduled from {original_time.strftime('%B %d at %I:%M %p')} to {new_interview.scheduled_at.strftime('%B %d at %I:%M %p')}",
            channels=["in_app", "email"],
            priority=NotificationPriority.HIGH,
            action_url=f"/interviews/{new_interview.id}",
            action_text="View New Details",
            db=db
        )

        # Notify interviewer
        self.notification_service.create_notification(
            user_id=new_interview.interviewer_user_id,
            notification_type=NotificationType.INTERVIEW_RESCHEDULED,
            title="Interview Rescheduled",
            message=f"Interview has been rescheduled from {original_time.strftime('%B %d at %I:%M %p')} to {new_interview.scheduled_at.strftime('%B %d at %I:%M %p')}",
            channels=["in_app", "email"],
            priority=NotificationPriority.HIGH,
            action_url=f"/interviews/{new_interview.id}",
            action_text="View New Details",
            db=db
        )

    def _send_interview_cancelled_notifications(
        self,
        interview: Interview,
        reason: str,
        db: Session
    ):
        """Send notifications when interview is cancelled."""
        if not self.notification_service:
            return

        # Notify candidate
        self.notification_service.create_notification(
            user_id=interview.candidate_user_id,
            notification_type=NotificationType.INTERVIEW_CANCELLED,
            title="Interview Cancelled",
            message=f"Your interview scheduled for {interview.scheduled_at.strftime('%B %d at %I:%M %p')} has been cancelled. Reason: {reason}",
            channels=["in_app", "email"],
            priority=NotificationPriority.HIGH,
            action_url=f"/applications/{interview.application_id}",
            action_text="View Application",
            db=db
        )

        # Notify interviewer
        self.notification_service.create_notification(
            user_id=interview.interviewer_user_id,
            notification_type=NotificationType.INTERVIEW_CANCELLED,
            title="Interview Cancelled",
            message=f"Interview scheduled for {interview.scheduled_at.strftime('%B %d at %I:%M %p')} has been cancelled",
            channels=["in_app", "email"],
            priority=NotificationPriority.NORMAL,
            action_url=f"/interviews",
            action_text="View Interviews",
            db=db
        )

    def _send_24h_reminder(self, interview: Interview, db: Session):
        """Send 24-hour reminder."""
        if not self.notification_service:
            return

        job = db.query(Job).filter(Job.id == interview.job_id).first()

        self.notification_service.create_notification(
            user_id=interview.candidate_user_id,
            notification_type=NotificationType.INTERVIEW_REMINDER,
            title="Interview Tomorrow",
            message=f"Reminder: Your {interview.stage.value} interview for {job.title if job else 'position'} is tomorrow at {interview.scheduled_at.strftime('%I:%M %p')}",
            channels=["in_app", "email"],
            priority=NotificationPriority.HIGH,
            action_url=f"/interviews/{interview.id}",
            action_text="View Details",
            db=db
        )

    def _send_1h_reminder(self, interview: Interview, db: Session):
        """Send 1-hour reminder."""
        if not self.notification_service:
            return

        self.notification_service.create_notification(
            user_id=interview.candidate_user_id,
            notification_type=NotificationType.INTERVIEW_REMINDER,
            title="Interview in 1 Hour",
            message=f"Your interview starts in 1 hour! Meeting link: {interview.meeting_url or 'Check interview details'}",
            channels=["in_app", "email", "push"],
            priority=NotificationPriority.URGENT,
            action_url=interview.meeting_url or f"/interviews/{interview.id}",
            action_text="Join Meeting" if interview.meeting_url else "View Details",
            db=db
        )


# ==================== Factory Function ====================

def create_interview_scheduling_service(
    notification_service=None,
    calendar_service=None,
    enable_notifications: bool = True
) -> InterviewSchedulingService:
    """
    Factory function to create InterviewSchedulingService.

    Args:
        notification_service: Optional notification service
        calendar_service: Optional calendar service
        enable_notifications: Whether to send notifications

    Returns:
        InterviewSchedulingService instance
    """
    return InterviewSchedulingService(
        notification_service=notification_service,
        calendar_service=calendar_service,
        enable_notifications=enable_notifications
    )
