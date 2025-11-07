"""
Match Model - AI-Generated Matches.

Represents matches created by AI agents between job seekers and jobs.
This is the core output of the AI matching system.
"""

from datetime import datetime
from enum import Enum
from typing import Dict

from sqlalchemy import Column, Integer, String, Text, Float, DateTime, ForeignKey, Enum as SQLEnum
from sqlalchemy.orm import relationship

from ..database import Base


class MatchStatus(str, Enum):
    """Match status."""
    PENDING = "pending"  # Match created, user hasn't seen it
    VIEWED = "viewed"  # User viewed the match
    ACCEPTED = "accepted"  # User interested
    REJECTED = "rejected"  # User not interested
    APPLIED = "applied"  # User applied to job
    EXPIRED = "expired"  # Match expired


class Match(Base):
    """
    AI-generated match model.

    Created automatically by AI agents when they find good fits.
    Matches can be profile-to-job or job-to-profile.
    """
    __tablename__ = "matches"

    # Primary Key
    id = Column(Integer, primary_key=True, index=True)
    profile_id = Column(Integer, ForeignKey("user_profiles.id"), nullable=False, index=True)
    job_id = Column(Integer, ForeignKey("jobs.id"), nullable=False, index=True)

    # Match Score
    match_score = Column(Float, nullable=False, index=True)  # 0.0 to 1.0
    confidence_level = Column(String(50), nullable=True)  # high, medium, low

    # AI Analysis
    ai_explanation = Column(Text, nullable=True)  # Why this is a good match
    matching_skills = Column(Text, nullable=True)  # JSON string of matching skills
    skill_gaps = Column(Text, nullable=True)  # Skills candidate needs
    salary_alignment = Column(String(50), nullable=True)  # good, acceptable, poor
    location_compatibility = Column(String(50), nullable=True)  # perfect, good, requires_relocation

    # Match Source
    created_by_agent = Column(String(100), nullable=True)  # Which AI agent created this
    match_strategy = Column(String(100), nullable=True)  # semantic, keyword, hybrid

    # Status
    status = Column(SQLEnum(MatchStatus), default=MatchStatus.PENDING, index=True)

    # User Actions
    viewed_at = Column(DateTime(timezone=True), nullable=True)
    responded_at = Column(DateTime(timezone=True), nullable=True)
    user_feedback = Column(String(500), nullable=True)  # User's opinion on match quality

    # Timestamps
    created_at = Column(DateTime(timezone=True), default=datetime.utcnow, nullable=False, index=True)
    expires_at = Column(DateTime(timezone=True), nullable=True)  # Matches can expire

    # Relationships
    profile = relationship("UserProfile", foreign_keys=[profile_id], back_populates="matches")
    job = relationship("Job", foreign_keys=[job_id], back_populates="matches")
    agent_conversation = relationship("AgentConversation", back_populates="match", uselist=False)

    def __repr__(self):
        return f"<Match profile_id={self.profile_id} job_id={self.job_id} score={self.match_score:.2f}>"

    def to_dict(self) -> Dict:
        """Convert to dictionary."""
        return {
            'id': self.id,
            'profile_id': self.profile_id,
            'job_id': self.job_id,
            'match_score': float(self.match_score),
            'confidence_level': self.confidence_level,
            'ai_explanation': self.ai_explanation,
            'matching_skills': self.matching_skills,
            'skill_gaps': self.skill_gaps,
            'salary_alignment': self.salary_alignment,
            'location_compatibility': self.location_compatibility,
            'created_by_agent': self.created_by_agent,
            'match_strategy': self.match_strategy,
            'status': self.status.value,
            'viewed_at': self.viewed_at.isoformat() if self.viewed_at else None,
            'responded_at': self.responded_at.isoformat() if self.responded_at else None,
            'user_feedback': self.user_feedback,
            'created_at': self.created_at.isoformat(),
            'expires_at': self.expires_at.isoformat() if self.expires_at else None,
        }
