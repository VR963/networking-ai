"""
Application Model - Phase 2: Job Applications with AI Screening.

Represents applications submitted by job seekers to jobs.
Includes comprehensive AI screening and workflow tracking.
"""

from datetime import datetime
from enum import Enum
from typing import Dict, List

from sqlalchemy import Column, Integer, String, Text, DateTime, ForeignKey, JSON, Float, Enum as SQLEnum
from sqlalchemy.orm import relationship

from ..database import Base


class ApplicationStatus(str, Enum):
    """Application status - Phase 2 enhanced."""
    PENDING = "pending"  # Phase 1 compatibility
    AI_SCREENING = "ai_screening"  # Phase 2: Being screened by AI
    SCREENED_PASS = "screened_pass"  # Phase 2: Passed AI screening
    SCREENED_FAIL = "screened_fail"  # Phase 2: Failed AI screening
    REVIEWING = "reviewing"  # Phase 1 compatibility
    SHORTLISTED = "shortlisted"  # Phase 1 compatibility
    INTERVIEW_SCHEDULED = "interview_scheduled"
    INTERVIEW_COMPLETED = "interview_completed"
    OFFER_EXTENDED = "offer_extended"
    OFFER_ACCEPTED = "offer_accepted"
    OFFER_DECLINED = "offer_declined"
    REJECTED = "rejected"
    WITHDRAWN = "withdrawn"


class ScreeningResult(str, Enum):
    """AI screening result - Phase 2."""
    STRONG_MATCH = "strong_match"  # Highly recommended
    GOOD_MATCH = "good_match"  # Recommended
    MODERATE_MATCH = "moderate_match"  # Consider
    WEAK_MATCH = "weak_match"  # Not recommended
    INSUFFICIENT_INFO = "insufficient_info"  # Cannot determine


class Application(Base):
    """
    Job application model - Phase 2 with AI screening.

    Tracks applications from job seekers to jobs with AI-powered screening.
    """
    __tablename__ = "applications"

    # Primary Key
    id = Column(Integer, primary_key=True, index=True)

    # Phase 1 compatibility
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    job_id = Column(Integer, ForeignKey("jobs.id"), nullable=False, index=True)

    # Phase 2: Enhanced applicant info
    talent_user_id = Column(Integer, ForeignKey("users.id"), index=True)  # Same as user_id
    talent_agent_id = Column(Integer, ForeignKey("personal_ai_agents.id"))
    company_id = Column(Integer, ForeignKey("companies.id"))
    hiring_manager_id = Column(Integer, ForeignKey("users.id"))

    # Application Details
    cover_letter = Column(Text, nullable=True)
    resume_url = Column(String(500), nullable=True)  # Phase 1 compatibility
    resume_file_path = Column(String(500), nullable=True)  # Phase 2: Local file path
    additional_info = Column(Text, nullable=True)  # Phase 1: Text
    additional_info_json = Column(JSON, nullable=True)  # Phase 2: Structured data

    # Match reference (if from matching system)
    match_id = Column(Integer, ForeignKey("matches.id"), nullable=True)

    # Status
    status = Column(SQLEnum(ApplicationStatus), default=ApplicationStatus.PENDING, index=True)
    current_stage = Column(String(100), nullable=True)  # Phase 2: Current workflow stage

    # Phase 2: Enhanced AI Screening
    ai_screening_score = Column(Float, nullable=True)  # 0.0 to 1.0
    ai_screening_result = Column(SQLEnum(ScreeningResult), nullable=True)
    ai_screening_reasoning = Column(Text, nullable=True)
    ai_screening_completed_at = Column(DateTime, nullable=True)

    # Screening breakdown (Phase 2)
    skill_alignment_score = Column(Float, nullable=True)
    experience_match_score = Column(Float, nullable=True)
    cultural_fit_score = Column(Float, nullable=True)

    # Screening details (Phase 2)
    strengths = Column(JSON, nullable=True)  # List of strengths
    concerns = Column(JSON, nullable=True)  # List of concerns
    recommendations = Column(Text, nullable=True)  # AI recommendations

    # Phase 1 compatibility
    ai_match_score = Column(Integer, nullable=True)  # 0-100 (legacy)
    ai_analysis = Column(Text, nullable=True)  # AI's assessment
    ai_suggested_questions = Column(Text, nullable=True)  # Interview questions

    # Feedback
    company_feedback = Column(Text, nullable=True)
    rejection_reason = Column(Text, nullable=True)

    # HM review (Phase 2)
    hm_reviewed_at = Column(DateTime, nullable=True)
    hm_notes = Column(Text, nullable=True)
    hm_rating = Column(Integer, nullable=True)  # 1-5 rating

    # Interview Details
    interview_scheduled_at = Column(DateTime, nullable=True)
    interview_location = Column(String(500), nullable=True)
    interview_notes = Column(Text, nullable=True)
    interview_completed_at = Column(DateTime, nullable=True)  # Phase 2
    interview_score = Column(Integer, nullable=True)  # Phase 2: 1-10 score

    # Decision (Phase 2)
    decision = Column(String(50), nullable=True)  # "proceed", "reject", "hold"
    decision_made_at = Column(DateTime, nullable=True)
    decision_reason = Column(Text, nullable=True)

    # Offer (Phase 2)
    offer_extended_at = Column(DateTime, nullable=True)
    offer_amount = Column(Integer, nullable=True)
    offer_accepted_at = Column(DateTime, nullable=True)
    offer_rejected_at = Column(DateTime, nullable=True)

    # Timestamps
    submitted_at = Column(DateTime, default=datetime.utcnow, nullable=False)  # Phase 2
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False, index=True)  # Phase 1
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    reviewed_at = Column(DateTime, nullable=True)
    rejected_at = Column(DateTime, nullable=True)

    # Relationships
    user = relationship("User", foreign_keys=[user_id], back_populates="applications")
    job = relationship("Job", back_populates="applications")
    talent_agent = relationship("PersonalAIAgent", foreign_keys=[talent_agent_id])
    match = relationship("Match", foreign_keys=[match_id])

    def __repr__(self):
        return f"<Application {self.id}: User {self.user_id} → Job {self.job_id} ({self.status.value})>"

    # Phase 2 Methods

    def mark_ai_screening_complete(
        self,
        score: float,
        result: ScreeningResult,
        reasoning: str,
        strengths: List[str] = None,
        concerns: List[str] = None,
        recommendations: str = None
    ):
        """Mark AI screening as complete."""
        self.ai_screening_score = score
        self.ai_screening_result = result
        self.ai_screening_reasoning = reasoning
        self.strengths = strengths or []
        self.concerns = concerns or []
        self.recommendations = recommendations
        self.ai_screening_completed_at = datetime.utcnow()

        # Update status based on result
        if result in [ScreeningResult.STRONG_MATCH, ScreeningResult.GOOD_MATCH]:
            self.status = ApplicationStatus.SCREENED_PASS
            self.current_stage = "ready_for_hm_review"
        elif result == ScreeningResult.MODERATE_MATCH:
            self.status = ApplicationStatus.SCREENED_PASS
            self.current_stage = "needs_hm_review"
        else:
            self.status = ApplicationStatus.SCREENED_FAIL
            self.current_stage = "screening_failed"

    def mark_under_review(self):
        """Mark application as under HM review."""
        self.status = ApplicationStatus.REVIEWING
        self.current_stage = "hm_review"
        self.hm_reviewed_at = datetime.utcnow()

    def schedule_interview(self, scheduled_at: datetime, location: str = None):
        """Schedule interview."""
        self.status = ApplicationStatus.INTERVIEW_SCHEDULED
        self.current_stage = "interview_scheduled"
        self.interview_scheduled_at = scheduled_at
        self.interview_location = location

    def mark_interviewed(self, notes: str = None, score: int = None):
        """Mark interview as completed."""
        self.status = ApplicationStatus.INTERVIEW_COMPLETED
        self.current_stage = "interview_completed"
        self.interview_completed_at = datetime.utcnow()
        self.interview_notes = notes
        self.interview_score = score

    def extend_offer(self, amount: int):
        """Extend job offer."""
        self.status = ApplicationStatus.OFFER_EXTENDED
        self.current_stage = "offer_extended"
        self.offer_extended_at = datetime.utcnow()
        self.offer_amount = amount

    def accept_offer(self):
        """Accept job offer."""
        self.status = ApplicationStatus.OFFER_ACCEPTED
        self.current_stage = "completed"
        self.offer_accepted_at = datetime.utcnow()

    def reject(self, reason: str = None):
        """Reject application."""
        self.status = ApplicationStatus.REJECTED
        self.current_stage = "rejected"
        self.decision = "reject"
        self.decision_made_at = datetime.utcnow()
        self.decision_reason = reason
        self.rejection_reason = reason
        self.rejected_at = datetime.utcnow()

    def withdraw(self):
        """Withdraw application."""
        self.status = ApplicationStatus.WITHDRAWN
        self.current_stage = "withdrawn"
        self.decision_made_at = datetime.utcnow()

    def is_active(self) -> bool:
        """Check if application is still active."""
        final_statuses = [
            ApplicationStatus.OFFER_ACCEPTED,
            ApplicationStatus.REJECTED,
            ApplicationStatus.WITHDRAWN,
            ApplicationStatus.SCREENED_FAIL
        ]
        return self.status not in final_statuses

    def passed_screening(self) -> bool:
        """Check if application passed AI screening."""
        return self.status == ApplicationStatus.SCREENED_PASS or \
               self.ai_screening_result in [ScreeningResult.STRONG_MATCH, ScreeningResult.GOOD_MATCH]

    def to_dict(self) -> Dict:
        """Convert to dictionary - Phase 2 enhanced."""
        return {
            'id': self.id,
            'user_id': self.user_id,
            'job_id': self.job_id,
            'talent_agent_id': self.talent_agent_id,
            'company_id': self.company_id,
            'match_id': self.match_id,
            'cover_letter': self.cover_letter,
            'resume_url': self.resume_url,
            'additional_info': self.additional_info,
            'status': self.status.value,
            'current_stage': self.current_stage,
            # AI Screening
            'ai_screening_score': float(self.ai_screening_score) if self.ai_screening_score else None,
            'ai_screening_result': self.ai_screening_result.value if self.ai_screening_result else None,
            'ai_screening_reasoning': self.ai_screening_reasoning,
            'skill_alignment_score': self.skill_alignment_score,
            'experience_match_score': self.experience_match_score,
            'cultural_fit_score': self.cultural_fit_score,
            'strengths': self.strengths,
            'concerns': self.concerns,
            'recommendations': self.recommendations,
            # Legacy
            'ai_match_score': self.ai_match_score,
            'ai_analysis': self.ai_analysis,
            'company_feedback': self.company_feedback,
            'rejection_reason': self.rejection_reason,
            # Interview
            'interview_scheduled_at': self.interview_scheduled_at.isoformat() if self.interview_scheduled_at else None,
            'interview_location': self.interview_location,
            'interview_completed_at': self.interview_completed_at.isoformat() if self.interview_completed_at else None,
            'interview_score': self.interview_score,
            # Timestamps
            'submitted_at': self.submitted_at.isoformat() if self.submitted_at else self.created_at.isoformat(),
            'created_at': self.created_at.isoformat(),
            'updated_at': self.updated_at.isoformat(),
            'reviewed_at': self.reviewed_at.isoformat() if self.reviewed_at else None,
        }
