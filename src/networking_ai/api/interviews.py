"""
Interview API Endpoints - Phase 4.

REST API for managing interviews, scheduling, and feedback.
"""

from typing import List, Optional
from datetime import datetime, timedelta
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from pydantic import BaseModel, Field

from ..database import get_db
from ..models.interview import (
    Interview,
    InterviewAvailability,
    InterviewFeedback,
    InterviewPipeline,
    InterviewStage,
    InterviewStatus,
    InterviewFormat,
    FeedbackRating
)
from ..models.user import User
from ..services.interview_scheduling_service import (
    InterviewSchedulingService,
    create_interview_scheduling_service
)


# ==================== Request/Response Models ====================

class AvailabilityCreate(BaseModel):
    """Create availability slot."""
    start_time: datetime
    end_time: datetime
    timezone: str = "UTC"
    is_recurring: bool = False
    recurrence_rule: Optional[str] = None
    max_interviews_per_day: int = 4


class AvailabilityResponse(BaseModel):
    """Availability response."""
    id: int
    user_id: int
    start_time: datetime
    end_time: datetime
    timezone: str
    is_recurring: bool
    is_available: bool
    max_interviews_per_day: int

    class Config:
        from_attributes = True


class AvailableSlot(BaseModel):
    """Available time slot."""
    start_time: datetime
    end_time: datetime
    duration_minutes: int
    timezone: str


class InterviewCreate(BaseModel):
    """Create interview request."""
    application_id: int
    job_id: int
    company_id: int
    candidate_user_id: int
    interviewer_user_id: int
    stage: InterviewStage
    scheduled_at: datetime
    duration_minutes: int = 60
    format: InterviewFormat = InterviewFormat.VIDEO
    timezone: str = "UTC"
    meeting_url: Optional[str] = None
    meeting_id: Optional[str] = None
    meeting_password: Optional[str] = None
    preparation_materials: Optional[dict] = None
    interview_questions: Optional[List[str]] = None


class InterviewReschedule(BaseModel):
    """Reschedule interview request."""
    new_scheduled_at: datetime
    reschedule_reason: Optional[str] = None


class InterviewCancel(BaseModel):
    """Cancel interview request."""
    reason: str


class InterviewResponse(BaseModel):
    """Interview response."""
    id: int
    application_id: int
    job_id: int
    company_id: int
    candidate_user_id: int
    interviewer_user_id: int
    stage: InterviewStage
    status: InterviewStatus
    format: InterviewFormat
    scheduled_at: datetime
    duration_minutes: int
    timezone: str
    meeting_url: Optional[str] = None
    meeting_id: Optional[str] = None
    created_at: datetime
    candidate_calendar_confirmed: bool
    interviewer_calendar_confirmed: bool
    reminder_24h_sent: bool
    reminder_1h_sent: bool

    class Config:
        from_attributes = True


class FeedbackCreate(BaseModel):
    """Create interview feedback."""
    interview_id: int
    interviewer_user_id: int
    overall_rating: FeedbackRating
    technical_skills_rating: Optional[FeedbackRating] = None
    communication_rating: Optional[FeedbackRating] = None
    problem_solving_rating: Optional[FeedbackRating] = None
    cultural_fit_rating: Optional[FeedbackRating] = None
    detailed_feedback: Optional[str] = None
    strengths: Optional[List[str]] = None
    weaknesses: Optional[List[str]] = None
    recommendation: str  # "hire", "no_hire", "maybe"
    notes: Optional[str] = None


class FeedbackResponse(BaseModel):
    """Feedback response."""
    id: int
    interview_id: int
    interviewer_user_id: int
    overall_rating: FeedbackRating
    recommendation: str
    detailed_feedback: Optional[str] = None
    created_at: datetime

    class Config:
        from_attributes = True


# ==================== Router Setup ====================

router = APIRouter(prefix="/api/interviews", tags=["interviews"])


# ==================== Helper Functions ====================

def get_scheduling_service() -> InterviewSchedulingService:
    """Get interview scheduling service instance."""
    # In production, inject notification_service and calendar_service
    return create_interview_scheduling_service()


# ==================== Availability Endpoints ====================

@router.post("/availability", response_model=AvailabilityResponse, status_code=status.HTTP_201_CREATED)
def create_availability(
    availability: AvailabilityCreate,
    user_id: int,  # Should come from auth
    db: Session = Depends(get_db),
    service: InterviewSchedulingService = Depends(get_scheduling_service)
):
    """
    Create interviewer availability slot.

    Allows interviewers to set their available times for interviews.
    Supports recurring availability using RRULE format.
    """
    created = service.add_availability(
        user_id=user_id,
        start_time=availability.start_time,
        end_time=availability.end_time,
        timezone=availability.timezone,
        is_recurring=availability.is_recurring,
        recurrence_rule=availability.recurrence_rule,
        max_interviews_per_day=availability.max_interviews_per_day,
        db=db
    )
    return created


@router.get("/availability/slots", response_model=List[AvailableSlot])
def get_available_slots(
    interviewer_user_id: int,
    start_date: datetime,
    end_date: datetime,
    duration_minutes: int = 60,
    db: Session = Depends(get_db),
    service: InterviewSchedulingService = Depends(get_scheduling_service)
):
    """
    Get available time slots for an interviewer.

    Returns all available slots within the date range, excluding conflicts.
    Useful for scheduling UI to show available times.
    """
    slots = service.find_available_slots(
        interviewer_user_id=interviewer_user_id,
        start_date=start_date,
        end_date=end_date,
        duration_minutes=duration_minutes,
        db=db
    )
    return slots


# ==================== Interview CRUD ====================

@router.post("", response_model=InterviewResponse, status_code=status.HTTP_201_CREATED)
def schedule_interview(
    interview: InterviewCreate,
    db: Session = Depends(get_db),
    service: InterviewSchedulingService = Depends(get_scheduling_service)
):
    """
    Schedule a new interview.

    Creates an interview and sends notifications to both candidate and interviewer.
    Optionally creates calendar events if calendar service is configured.
    """
    created = service.schedule_interview(
        application_id=interview.application_id,
        job_id=interview.job_id,
        company_id=interview.company_id,
        candidate_user_id=interview.candidate_user_id,
        interviewer_user_id=interview.interviewer_user_id,
        stage=interview.stage,
        scheduled_at=interview.scheduled_at,
        duration_minutes=interview.duration_minutes,
        format=interview.format,
        timezone=interview.timezone,
        meeting_url=interview.meeting_url,
        meeting_id=interview.meeting_id,
        meeting_password=interview.meeting_password,
        preparation_materials=interview.preparation_materials,
        interview_questions=interview.interview_questions,
        db=db
    )
    return created


@router.get("/{interview_id}", response_model=InterviewResponse)
def get_interview(
    interview_id: int,
    db: Session = Depends(get_db),
    service: InterviewSchedulingService = Depends(get_scheduling_service)
):
    """Get interview by ID."""
    interview = service.get_interview(interview_id=interview_id, db=db)
    if not interview:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Interview not found"
        )
    return interview


@router.get("", response_model=List[InterviewResponse])
def list_interviews(
    candidate_user_id: Optional[int] = None,
    interviewer_user_id: Optional[int] = None,
    application_id: Optional[int] = None,
    upcoming_only: bool = False,
    db: Session = Depends(get_db),
    service: InterviewSchedulingService = Depends(get_scheduling_service)
):
    """
    List interviews with filters.

    Can filter by candidate, interviewer, application, or show only upcoming.
    """
    if candidate_user_id:
        interviews = service.get_interviews_for_candidate(
            candidate_user_id=candidate_user_id,
            db=db,
            upcoming_only=upcoming_only
        )
    elif interviewer_user_id:
        interviews = service.get_interviews_for_interviewer(
            interviewer_user_id=interviewer_user_id,
            db=db,
            upcoming_only=upcoming_only
        )
    elif application_id:
        interviews = service.get_interviews_for_application(
            application_id=application_id,
            db=db
        )
    else:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Must provide candidate_user_id, interviewer_user_id, or application_id"
        )

    return interviews


# ==================== Interview Actions ====================

@router.post("/{interview_id}/confirm")
def confirm_interview(
    interview_id: int,
    user_id: int,  # Should come from auth
    db: Session = Depends(get_db),
    service: InterviewSchedulingService = Depends(get_scheduling_service)
):
    """
    Confirm interview attendance.

    Can be called by candidate or interviewer to confirm they will attend.
    When both confirm, status changes to CONFIRMED.
    """
    success = service.confirm_interview(
        interview_id=interview_id,
        user_id=user_id,
        db=db
    )

    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Interview not found or user not authorized"
        )

    return {"message": "Interview confirmed successfully"}


@router.post("/{interview_id}/reschedule", response_model=InterviewResponse)
def reschedule_interview(
    interview_id: int,
    reschedule: InterviewReschedule,
    db: Session = Depends(get_db),
    service: InterviewSchedulingService = Depends(get_scheduling_service)
):
    """
    Reschedule an interview.

    Creates a new interview at the new time and marks the old one as RESCHEDULED.
    Sends notifications to both parties.
    """
    new_interview = service.reschedule_interview(
        interview_id=interview_id,
        new_scheduled_at=reschedule.new_scheduled_at,
        reschedule_reason=reschedule.reschedule_reason,
        db=db
    )

    if not new_interview:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Interview not found"
        )

    return new_interview


@router.post("/{interview_id}/cancel")
def cancel_interview(
    interview_id: int,
    cancellation: InterviewCancel,
    user_id: int,  # Should come from auth
    db: Session = Depends(get_db),
    service: InterviewSchedulingService = Depends(get_scheduling_service)
):
    """
    Cancel an interview.

    Marks interview as CANCELLED and sends notifications.
    Cancels calendar events if calendar service is configured.
    """
    success = service.cancel_interview(
        interview_id=interview_id,
        cancelled_by_user_id=user_id,
        reason=cancellation.reason,
        db=db
    )

    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Interview not found"
        )

    return {"message": "Interview cancelled successfully"}


@router.post("/{interview_id}/start")
def start_interview(
    interview_id: int,
    db: Session = Depends(get_db),
    service: InterviewSchedulingService = Depends(get_scheduling_service)
):
    """
    Mark interview as started.

    Updates status to IN_PROGRESS and records start time.
    """
    success = service.start_interview(interview_id=interview_id, db=db)

    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Interview not found"
        )

    return {"message": "Interview started successfully"}


@router.post("/{interview_id}/complete")
def complete_interview(
    interview_id: int,
    db: Session = Depends(get_db),
    service: InterviewSchedulingService = Depends(get_scheduling_service)
):
    """
    Mark interview as completed.

    Updates status to COMPLETED and records completion time and duration.
    """
    success = service.complete_interview(interview_id=interview_id, db=db)

    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Interview not found"
        )

    return {"message": "Interview completed successfully"}


@router.post("/{interview_id}/no-show")
def mark_no_show(
    interview_id: int,
    db: Session = Depends(get_db),
    service: InterviewSchedulingService = Depends(get_scheduling_service)
):
    """
    Mark interview as no-show.

    Updates status to NO_SHOW when candidate doesn't attend.
    """
    success = service.mark_no_show(interview_id=interview_id, db=db)

    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Interview not found"
        )

    return {"message": "Interview marked as no-show"}


# ==================== Feedback Endpoints ====================

@router.post("/feedback", response_model=FeedbackResponse, status_code=status.HTTP_201_CREATED)
def create_feedback(
    feedback: FeedbackCreate,
    db: Session = Depends(get_db)
):
    """
    Submit interview feedback.

    Allows interviewers to provide structured feedback after completing an interview.
    """
    # Verify interview exists and is completed
    interview = db.query(Interview).filter(Interview.id == feedback.interview_id).first()
    if not interview:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Interview not found"
        )

    if interview.status != InterviewStatus.COMPLETED:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Can only provide feedback for completed interviews"
        )

    # Create feedback
    interview_feedback = InterviewFeedback(
        interview_id=feedback.interview_id,
        interviewer_user_id=feedback.interviewer_user_id,
        overall_rating=feedback.overall_rating,
        technical_skills_rating=feedback.technical_skills_rating,
        communication_rating=feedback.communication_rating,
        problem_solving_rating=feedback.problem_solving_rating,
        cultural_fit_rating=feedback.cultural_fit_rating,
        detailed_feedback=feedback.detailed_feedback,
        strengths=feedback.strengths,
        weaknesses=feedback.weaknesses,
        recommendation=feedback.recommendation,
        notes=feedback.notes
    )

    db.add(interview_feedback)
    db.commit()
    db.refresh(interview_feedback)

    return interview_feedback


@router.get("/{interview_id}/feedback", response_model=List[FeedbackResponse])
def get_interview_feedback(
    interview_id: int,
    db: Session = Depends(get_db)
):
    """
    Get all feedback for an interview.

    Returns feedback from all interviewers who participated.
    """
    feedback = db.query(InterviewFeedback).filter(
        InterviewFeedback.interview_id == interview_id
    ).all()

    return feedback


# ==================== Reminder Endpoint ====================

@router.post("/reminders/send")
def send_reminders(
    db: Session = Depends(get_db),
    service: InterviewSchedulingService = Depends(get_scheduling_service)
):
    """
    Send interview reminders (cron job endpoint).

    Checks all upcoming interviews and sends 24h and 1h reminders.
    Should be called by a scheduled task.
    """
    results = service.send_interview_reminders(db=db)

    return {
        "message": "Reminders sent successfully",
        "24h_reminders_sent": results["24h_reminders"],
        "1h_reminders_sent": results["1h_reminders"]
    }
