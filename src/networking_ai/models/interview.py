"""
Interview Models - Phase 4.

Complete interview management for hiring pipeline.

Models:
- Interview: Main interview entity
- InterviewStage: Stage in multi-stage interview process
- InterviewAvailability: HM/interviewer availability slots
- InterviewFeedback: Structured feedback per interview
- InterviewParticipant: Track who's involved in each interview
"""

from datetime import datetime, timedelta
from enum import Enum
from typing import Dict, Optional, List

from sqlalchemy import Column, Integer, String, Text, DateTime, ForeignKey, Boolean, Enum as SQLEnum, JSON, Float
from sqlalchemy.orm import relationship

from ..database import Base


class InterviewStage(str, Enum):
    """Interview stage in hiring pipeline."""
    PHONE_SCREEN = "phone_screen"
    TECHNICAL = "technical"
    BEHAVIORAL = "behavioral"
    CULTURE_FIT = "culture_fit"
    TEAM_INTERVIEW = "team_interview"
    FINAL_ROUND = "final_round"
    HIRING_MANAGER = "hiring_manager"
    EXECUTIVE = "executive"


class InterviewStatus(str, Enum):
    """Interview status."""
    SCHEDULED = "scheduled"
    CONFIRMED = "confirmed"
    REMINDED = "reminded"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    CANCELLED = "cancelled"
    RESCHEDULED = "rescheduled"
    NO_SHOW = "no_show"


class InterviewFormat(str, Enum):
    """Interview format/type."""
    VIDEO = "video"
    PHONE = "phone"
    IN_PERSON = "in_person"
    ASYNCHRONOUS = "asynchronous"


class FeedbackRating(str, Enum):
    """Feedback rating scale."""
    STRONG_YES = "strong_yes"
    YES = "yes"
    MAYBE = "maybe"
    NO = "no"
    STRONG_NO = "strong_no"


class Interview(Base):
    """
    Interview entity for hiring pipeline.

    Tracks scheduled interviews between candidates and hiring teams.
    """
    __tablename__ = "interviews"
    __table_args__ = {'extend_existing': True}

    # Primary Key
    id = Column(Integer, primary_key=True, index=True)

    # Application & Job
    application_id = Column(Integer, ForeignKey("applications.id"), nullable=False, index=True)
    job_id = Column(Integer, ForeignKey("jobs.id"), nullable=False, index=True)
    company_id = Column(Integer, ForeignKey("companies.id"), nullable=False)

    # Candidate
    candidate_user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    candidate_agent_id = Column(Integer, ForeignKey("personal_ai_agents.id"), nullable=True)

    # Interviewer
    interviewer_user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    interviewer_agent_id = Column(Integer, ForeignKey("personal_ai_agents.id"), nullable=True)

    # Interview Details
    stage = Column(SQLEnum(InterviewStage), nullable=False, index=True)
    status = Column(SQLEnum(InterviewStatus), default=InterviewStatus.SCHEDULED, nullable=False, index=True)
    format = Column(SQLEnum(InterviewFormat), default=InterviewFormat.VIDEO, nullable=False)

    # Scheduling
    scheduled_at = Column(DateTime, nullable=False, index=True)
    duration_minutes = Column(Integer, default=60, nullable=False)
    timezone = Column(String(50), default="UTC", nullable=False)

    # Meeting Details
    meeting_url = Column(String(500), nullable=True)  # Zoom/Meet link
    meeting_id = Column(String(100), nullable=True)
    meeting_password = Column(String(100), nullable=True)
    phone_number = Column(String(50), nullable=True)
    location = Column(String(200), nullable=True)  # For in-person

    # Calendar Integration
    calendar_event_id = Column(String(200), nullable=True)  # Google/Outlook event ID
    candidate_calendar_confirmed = Column(Boolean, default=False)
    interviewer_calendar_confirmed = Column(Boolean, default=False)

    # Preparation
    preparation_materials = Column(JSON, nullable=True)  # Links, documents, etc.
    interview_questions = Column(JSON, nullable=True)  # Suggested questions
    candidate_resume_url = Column(String(500), nullable=True)

    # Reminders
    reminder_24h_sent = Column(Boolean, default=False)
    reminder_1h_sent = Column(Boolean, default=False)
    reminder_24h_sent_at = Column(DateTime, nullable=True)
    reminder_1h_sent_at = Column(DateTime, nullable=True)

    # Completion
    started_at = Column(DateTime, nullable=True)
    completed_at = Column(DateTime, nullable=True)
    actual_duration_minutes = Column(Integer, nullable=True)

    # Cancellation/Rescheduling
    cancelled_at = Column(DateTime, nullable=True)
    cancelled_by_user_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    cancellation_reason = Column(Text, nullable=True)
    rescheduled_from_interview_id = Column(Integer, ForeignKey("interviews.id"), nullable=True)

    # Notes
    interviewer_notes = Column(Text, nullable=True)
    internal_notes = Column(Text, nullable=True)

    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    # Relationships
    application = relationship("Application", foreign_keys=[application_id])
    job = relationship("Job", foreign_keys=[job_id])
    candidate = relationship("User", foreign_keys=[candidate_user_id])
    interviewer = relationship("User", foreign_keys=[interviewer_user_id])
    feedbacks = relationship("InterviewFeedback", back_populates="interview")

    def __repr__(self):
        return f"<Interview {self.id}: {self.stage.value} at {self.scheduled_at}>"

    def mark_confirmed(self):
        """Mark interview as confirmed by both parties."""
        self.status = InterviewStatus.CONFIRMED

    def mark_started(self):
        """Mark interview as started."""
        self.status = InterviewStatus.IN_PROGRESS
        self.started_at = datetime.utcnow()

    def mark_completed(self):
        """Mark interview as completed."""
        self.status = InterviewStatus.COMPLETED
        self.completed_at = datetime.utcnow()
        if self.started_at:
            self.actual_duration_minutes = int((self.completed_at - self.started_at).total_seconds() / 60)

    def mark_cancelled(self, cancelled_by_user_id: int, reason: str):
        """Cancel interview."""
        self.status = InterviewStatus.CANCELLED
        self.cancelled_at = datetime.utcnow()
        self.cancelled_by_user_id = cancelled_by_user_id
        self.cancellation_reason = reason

    def mark_no_show(self):
        """Mark as no-show."""
        self.status = InterviewStatus.NO_SHOW
        self.completed_at = datetime.utcnow()

    def is_upcoming(self) -> bool:
        """Check if interview is upcoming (scheduled in future)."""
        return self.scheduled_at > datetime.utcnow() and self.status in [
            InterviewStatus.SCHEDULED, InterviewStatus.CONFIRMED, InterviewStatus.REMINDED
        ]

    def is_past(self) -> bool:
        """Check if interview is in the past."""
        return self.scheduled_at < datetime.utcnow()

    def needs_24h_reminder(self) -> bool:
        """Check if 24h reminder should be sent."""
        if self.reminder_24h_sent:
            return False
        reminder_time = self.scheduled_at - timedelta(hours=24)
        return datetime.utcnow() >= reminder_time and self.is_upcoming()

    def needs_1h_reminder(self) -> bool:
        """Check if 1h reminder should be sent."""
        if self.reminder_1h_sent:
            return False
        reminder_time = self.scheduled_at - timedelta(hours=1)
        return datetime.utcnow() >= reminder_time and self.is_upcoming()

    def to_dict(self) -> Dict:
        """Convert to dictionary."""
        return {
            "id": self.id,
            "application_id": self.application_id,
            "job_id": self.job_id,
            "stage": self.stage.value,
            "status": self.status.value,
            "format": self.format.value,
            "scheduled_at": self.scheduled_at.isoformat(),
            "duration_minutes": self.duration_minutes,
            "timezone": self.timezone,
            "meeting_url": self.meeting_url,
            "is_upcoming": self.is_upcoming(),
            "created_at": self.created_at.isoformat()
        }


class InterviewAvailability(Base):
    """
    Interviewer availability slots.

    Used for automated scheduling.
    """
    __tablename__ = "interview_availability"
    __table_args__ = {'extend_existing': True}

    # Primary Key
    id = Column(Integer, primary_key=True, index=True)

    # Interviewer
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)

    # Availability Window
    start_time = Column(DateTime, nullable=False, index=True)
    end_time = Column(DateTime, nullable=False)
    timezone = Column(String(50), default="UTC", nullable=False)

    # Constraints
    is_available = Column(Boolean, default=True, nullable=False)
    max_interviews_per_day = Column(Integer, default=4, nullable=False)

    # Recurring availability (optional)
    is_recurring = Column(Boolean, default=False)
    recurrence_rule = Column(String(200), nullable=True)  # RRULE format

    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    # Relationships
    user = relationship("User", foreign_keys=[user_id])

    def __repr__(self):
        return f"<InterviewAvailability {self.id}: {self.start_time} - {self.end_time}>"

    def is_slot_available(self, proposed_start: datetime, duration_minutes: int) -> bool:
        """Check if a proposed time slot fits in this availability."""
        proposed_end = proposed_start + timedelta(minutes=duration_minutes)
        return (
            self.is_available and
            proposed_start >= self.start_time and
            proposed_end <= self.end_time
        )


class InterviewFeedback(Base):
    """
    Structured feedback for interviews.

    Collected after each interview stage.
    """
    __tablename__ = "interview_feedbacks"
    __table_args__ = {'extend_existing': True}

    # Primary Key
    id = Column(Integer, primary_key=True, index=True)

    # Interview
    interview_id = Column(Integer, ForeignKey("interviews.id"), nullable=False, index=True)

    # Feedback Provider
    provided_by_user_id = Column(Integer, ForeignKey("users.id"), nullable=False)

    # Overall Rating
    overall_rating = Column(SQLEnum(FeedbackRating), nullable=False)
    recommendation = Column(String(50), nullable=False)  # "hire", "no_hire", "maybe"

    # Detailed Ratings (0-5 scale)
    technical_skills_rating = Column(Float, nullable=True)
    communication_rating = Column(Float, nullable=True)
    problem_solving_rating = Column(Float, nullable=True)
    culture_fit_rating = Column(Float, nullable=True)
    leadership_rating = Column(Float, nullable=True)
    experience_rating = Column(Float, nullable=True)

    # Structured Feedback
    strengths = Column(JSON, nullable=True)  # List of strengths
    weaknesses = Column(JSON, nullable=True)  # List of areas for improvement
    concerns = Column(JSON, nullable=True)  # List of concerns

    # Written Feedback
    summary = Column(Text, nullable=True)
    detailed_notes = Column(Text, nullable=True)

    # Follow-up
    requires_follow_up = Column(Boolean, default=False)
    follow_up_notes = Column(Text, nullable=True)

    # Sharing
    shared_with_candidate = Column(Boolean, default=False)
    shared_at = Column(DateTime, nullable=True)

    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    # Relationships
    interview = relationship("Interview", back_populates="feedbacks")
    provider = relationship("User", foreign_keys=[provided_by_user_id])

    def __repr__(self):
        return f"<InterviewFeedback {self.id}: {self.overall_rating.value} for interview {self.interview_id}>"

    def get_average_rating(self) -> Optional[float]:
        """Calculate average of all detailed ratings."""
        ratings = [
            self.technical_skills_rating,
            self.communication_rating,
            self.problem_solving_rating,
            self.culture_fit_rating,
            self.leadership_rating,
            self.experience_rating
        ]

        valid_ratings = [r for r in ratings if r is not None]
        if not valid_ratings:
            return None

        return sum(valid_ratings) / len(valid_ratings)

    def is_positive(self) -> bool:
        """Check if feedback is positive."""
        return self.overall_rating in [FeedbackRating.YES, FeedbackRating.STRONG_YES]

    def to_dict(self) -> Dict:
        """Convert to dictionary."""
        return {
            "id": self.id,
            "interview_id": self.interview_id,
            "overall_rating": self.overall_rating.value,
            "recommendation": self.recommendation,
            "average_rating": self.get_average_rating(),
            "strengths": self.strengths,
            "weaknesses": self.weaknesses,
            "summary": self.summary,
            "is_positive": self.is_positive(),
            "created_at": self.created_at.isoformat()
        }


class InterviewPipeline(Base):
    """
    Track candidate progress through interview stages.

    One pipeline per application.
    """
    __tablename__ = "interview_pipelines"
    __table_args__ = {'extend_existing': True}

    # Primary Key
    id = Column(Integer, primary_key=True, index=True)

    # Application
    application_id = Column(Integer, ForeignKey("applications.id"), nullable=False, unique=True, index=True)
    job_id = Column(Integer, ForeignKey("jobs.id"), nullable=False)

    # Current State
    current_stage = Column(SQLEnum(InterviewStage), nullable=True, index=True)
    status = Column(String(50), default="in_progress", nullable=False)  # in_progress, completed, rejected

    # Stage Configuration (ordered list)
    stages_config = Column(JSON, nullable=False)  # ["phone_screen", "technical", "final_round"]
    current_stage_index = Column(Integer, default=0, nullable=False)

    # Progress
    stages_completed = Column(JSON, default=list, nullable=False)  # List of completed stages
    stages_scheduled = Column(JSON, default=list, nullable=False)  # List of scheduled stages

    # Decision
    final_decision = Column(String(50), nullable=True)  # "hire", "reject", "pending"
    decision_made_at = Column(DateTime, nullable=True)
    decision_made_by_user_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    decision_notes = Column(Text, nullable=True)

    # Timestamps
    started_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    completed_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    # Relationships
    application = relationship("Application", foreign_keys=[application_id])
    job = relationship("Job", foreign_keys=[job_id])

    def __repr__(self):
        return f"<InterviewPipeline {self.id}: stage {self.current_stage_index + 1}/{len(self.stages_config)}>"

    def advance_to_next_stage(self) -> bool:
        """Advance to next stage in pipeline."""
        if self.current_stage_index < len(self.stages_config) - 1:
            # Mark current stage as completed
            if self.current_stage:
                self.stages_completed.append(self.current_stage.value)

            # Move to next stage
            self.current_stage_index += 1
            self.current_stage = InterviewStage(self.stages_config[self.current_stage_index])
            return True

        return False

    def is_complete(self) -> bool:
        """Check if all stages are complete."""
        return self.current_stage_index >= len(self.stages_config) - 1 and \
               len(self.stages_completed) == len(self.stages_config)

    def get_progress_percentage(self) -> float:
        """Get progress as percentage."""
        if not self.stages_config:
            return 0.0
        return (len(self.stages_completed) / len(self.stages_config)) * 100

    def mark_completed(self, decision: str, decided_by_user_id: int, notes: str = None):
        """Mark pipeline as completed with final decision."""
        self.status = "completed"
        self.final_decision = decision
        self.decision_made_at = datetime.utcnow()
        self.decision_made_by_user_id = decided_by_user_id
        self.decision_notes = notes
        self.completed_at = datetime.utcnow()

    def mark_rejected(self, decided_by_user_id: int, notes: str = None):
        """Mark candidate as rejected."""
        self.mark_completed("reject", decided_by_user_id, notes)

    def mark_hired(self, decided_by_user_id: int, notes: str = None):
        """Mark candidate as hired."""
        self.mark_completed("hire", decided_by_user_id, notes)
