"""
Application Model - Job Applications.

Represents applications submitted by job seekers to jobs.
"""

from datetime import datetime
from enum import Enum
from typing import Dict

from sqlalchemy import Column, Integer, String, Text, DateTime, ForeignKey, Enum as SQLEnum
from sqlalchemy.orm import relationship

from ..database import Base


class ApplicationStatus(str, Enum):
    """Application status."""
    PENDING = "pending"
    REVIEWING = "reviewing"
    SHORTLISTED = "shortlisted"
    INTERVIEW_SCHEDULED = "interview_scheduled"
    INTERVIEW_COMPLETED = "interview_completed"
    OFFER_EXTENDED = "offer_extended"
    OFFER_ACCEPTED = "offer_accepted"
    OFFER_DECLINED = "offer_declined"
    REJECTED = "rejected"
    WITHDRAWN = "withdrawn"


class Application(Base):
    """
    Job application model.

    Tracks applications from job seekers to specific jobs.
    """
    __tablename__ = "applications"

    # Primary Key
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    job_id = Column(Integer, ForeignKey("jobs.id"), nullable=False, index=True)

    # Application Details
    cover_letter = Column(Text, nullable=True)
    resume_url = Column(String(500), nullable=True)  # Specific resume for this application
    additional_info = Column(Text, nullable=True)

    # Status
    status = Column(SQLEnum(ApplicationStatus), default=ApplicationStatus.PENDING, index=True)

    # AI Analysis
    ai_match_score = Column(Integer, nullable=True)  # 0-100
    ai_analysis = Column(Text, nullable=True)  # AI's assessment of fit
    ai_suggested_questions = Column(Text, nullable=True)  # AI-generated interview questions

    # Feedback
    company_feedback = Column(Text, nullable=True)
    rejection_reason = Column(Text, nullable=True)

    # Interview Details
    interview_scheduled_at = Column(DateTime(timezone=True), nullable=True)
    interview_location = Column(String(500), nullable=True)
    interview_notes = Column(Text, nullable=True)

    # Timestamps
    created_at = Column(DateTime(timezone=True), default=datetime.utcnow, nullable=False, index=True)
    updated_at = Column(DateTime(timezone=True), default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    reviewed_at = Column(DateTime(timezone=True), nullable=True)
    rejected_at = Column(DateTime(timezone=True), nullable=True)

    # Relationships
    user = relationship("User", back_populates="applications")
    job = relationship("Job", back_populates="applications")

    def __repr__(self):
        return f"<Application user_id={self.user_id} job_id={self.job_id} status={self.status.value}>"

    def to_dict(self) -> Dict:
        """Convert to dictionary."""
        return {
            'id': self.id,
            'user_id': self.user_id,
            'job_id': self.job_id,
            'cover_letter': self.cover_letter,
            'resume_url': self.resume_url,
            'additional_info': self.additional_info,
            'status': self.status.value,
            'ai_match_score': self.ai_match_score,
            'ai_analysis': self.ai_analysis,
            'company_feedback': self.company_feedback,
            'rejection_reason': self.rejection_reason,
            'interview_scheduled_at': self.interview_scheduled_at.isoformat() if self.interview_scheduled_at else None,
            'interview_location': self.interview_location,
            'created_at': self.created_at.isoformat(),
            'updated_at': self.updated_at.isoformat(),
            'reviewed_at': self.reviewed_at.isoformat() if self.reviewed_at else None,
        }
