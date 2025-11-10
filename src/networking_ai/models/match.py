"""
Match Model - Phase 2: Matches between Talent Personal Agents and Job Postings (Company AI Agents).

Represents semantic matches created by the AI matching system between:
- Talent Personal Agent RAG (skills, preferences, career goals)
- Job Posting RAG (requirements + HM preferences + company culture)
"""

from datetime import datetime
from enum import Enum
from typing import Dict

from sqlalchemy import Column, Integer, String, Text, Float, DateTime, ForeignKey, JSON, Enum as SQLEnum
from sqlalchemy.orm import relationship

from ..database import Base


class MatchStatus(str, Enum):
    """Match status."""
    PENDING = "pending"  # Match created, awaiting talent response
    VIEWED = "viewed"  # Talent viewed the match
    INTERESTED = "interested"  # Talent marked as interested
    NOT_INTERESTED = "not_interested"  # Talent not interested
    APPLIED = "applied"  # Talent applied to job
    EXPIRED = "expired"  # Match expired (job closed or talent moved on)


class Match(Base):
    """
    Match between Talent Personal Agent and Job Posting (Company AI Agent).

    Phase 2: Uses dual RAG systems for intelligent matching:
    - Talent Personal Agent RAG (portable knowledge about candidate)
    - Job RAG with dual access (HM Personal RAG + Company Admin RAG)
    """
    __tablename__ = "matches"
    __table_args__ = {'extend_existing': True}

    # Primary Key
    id = Column(Integer, primary_key=True, index=True)

    # Phase 2: Talent info (with agent)
    talent_user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    talent_agent_id = Column(Integer, ForeignKey("personal_ai_agents.id"), nullable=False)

    # Phase 1 compatibility (nullable for migration)
    profile_id = Column(Integer, ForeignKey("user_profiles.id"), nullable=True, index=True)

    # Job info
    job_id = Column(Integer, ForeignKey("jobs.id"), nullable=False, index=True)
    job_title = Column(String(255), nullable=False)  # Denormalized for quick access

    # Phase 2: Company info
    company_id = Column(Integer, ForeignKey("companies.id"), nullable=True)
    company_name = Column(String(255), nullable=True)  # Denormalized

    # Match Score
    match_score = Column(Float, nullable=False, index=True)  # 0.0 to 1.0
    confidence_level = Column(String(50), nullable=True)  # high, medium, low

    # Phase 2: Enhanced match breakdown
    skill_match_score = Column(Float)  # How well skills align (0.0-1.0)
    preference_match_score = Column(Float)  # How well preferences align (0.0-1.0)
    culture_match_score = Column(Float)  # How well culture aligns (0.0-1.0)

    # AI Analysis
    ai_explanation = Column(Text, nullable=True)  # Why this is a good match

    # Phase 2: Structured match metadata (JSON)
    matched_skills = Column(JSON)  # List of matched skills
    skill_gaps = Column(JSON)  # Skills candidate needs
    matched_preferences = Column(JSON)  # Matched preferences
    growth_opportunities = Column(JSON)  # Career growth opportunities identified

    # Phase 1 compatibility
    matching_skills = Column(Text, nullable=True)  # JSON string (legacy)
    salary_alignment = Column(String(50), nullable=True)  # good, acceptable, poor
    location_compatibility = Column(String(50), nullable=True)  # perfect, good, requires_relocation

    # Match Source
    created_by_agent = Column(String(100), nullable=True)  # Which AI agent created this
    match_strategy = Column(String(100), nullable=True)  # semantic, keyword, hybrid

    # Status
    status = Column(SQLEnum(MatchStatus), default=MatchStatus.PENDING, index=True)

    # Phase 2: Enhanced feedback tracking
    talent_feedback = Column(String(50))  # "interested", "not_interested", "maybe_later"
    talent_feedback_reason = Column(Text)  # Why they're (not) interested
    talent_viewed_at = Column(DateTime)  # When talent viewed the match
    talent_responded_at = Column(DateTime)  # When talent gave feedback

    # Phase 1 compatibility
    viewed_at = Column(DateTime, nullable=True)
    responded_at = Column(DateTime, nullable=True)
    user_feedback = Column(String(500), nullable=True)  # User's opinion on match quality

    # Phase 2: Application tracking
    applied_at = Column(DateTime)  # When talent applied
    application_id = Column(Integer, ForeignKey("applications.id"), nullable=True)

    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False, index=True)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    expires_at = Column(DateTime, nullable=True)  # Matches can expire

    # Relationships
    # Phase 2 relationships
    talent_user = relationship("User", foreign_keys=[talent_user_id])
    talent_agent = relationship("PersonalAIAgent", foreign_keys=[talent_agent_id])
    job = relationship("Job")
    company = relationship("Company")
    agent_conversation = relationship("AgentConversation", back_populates="match", uselist=False)

    # Phase 1 compatibility
    profile = relationship("UserProfile", foreign_keys=[profile_id], back_populates="matches")

    def __repr__(self):
        return f"<Match {self.id}: Talent {self.talent_user_id} → Job {self.job_id} ({self.match_score:.2f})>"

    # Phase 2 methods
    def mark_viewed(self):
        """Mark match as viewed by talent."""
        if not self.talent_viewed_at:
            self.talent_viewed_at = datetime.utcnow()
            self.status = MatchStatus.VIEWED

    def mark_interested(self, reason: str = None):
        """Talent marked as interested in this match."""
        self.status = MatchStatus.INTERESTED
        self.talent_feedback = "interested"
        self.talent_feedback_reason = reason
        self.talent_responded_at = datetime.utcnow()

    def mark_not_interested(self, reason: str = None):
        """Talent marked as not interested in this match."""
        self.status = MatchStatus.NOT_INTERESTED
        self.talent_feedback = "not_interested"
        self.talent_feedback_reason = reason
        self.talent_responded_at = datetime.utcnow()

    def mark_applied(self, application_id: int):
        """Talent applied to this job."""
        self.status = MatchStatus.APPLIED
        self.application_id = application_id
        self.applied_at = datetime.utcnow()

    def is_pending(self) -> bool:
        """Check if match is pending talent response."""
        return self.status == MatchStatus.PENDING

    def is_active(self) -> bool:
        """Check if match is still active (not expired or rejected)."""
        if self.status in [MatchStatus.EXPIRED, MatchStatus.NOT_INTERESTED]:
            return False
        if self.expires_at and datetime.utcnow() > self.expires_at:
            return False
        return True

    def to_dict(self) -> Dict:
        """Convert to dictionary."""
        return {
            'id': self.id,
            # Phase 2 fields
            'talent_user_id': self.talent_user_id,
            'talent_agent_id': self.talent_agent_id,
            'job_id': self.job_id,
            'job_title': self.job_title,
            'company_id': self.company_id,
            'company_name': self.company_name,
            'match_score': float(self.match_score),
            'skill_match_score': float(self.skill_match_score) if self.skill_match_score else None,
            'preference_match_score': float(self.preference_match_score) if self.preference_match_score else None,
            'culture_match_score': float(self.culture_match_score) if self.culture_match_score else None,
            'confidence_level': self.confidence_level,
            'ai_explanation': self.ai_explanation,
            'matched_skills': self.matched_skills,
            'skill_gaps': self.skill_gaps,
            'matched_preferences': self.matched_preferences,
            'growth_opportunities': self.growth_opportunities,
            'status': self.status.value,
            'talent_feedback': self.talent_feedback,
            'talent_feedback_reason': self.talent_feedback_reason,
            'talent_viewed_at': self.talent_viewed_at.isoformat() if self.talent_viewed_at else None,
            'talent_responded_at': self.talent_responded_at.isoformat() if self.talent_responded_at else None,
            'applied_at': self.applied_at.isoformat() if self.applied_at else None,
            'created_at': self.created_at.isoformat(),
            'expires_at': self.expires_at.isoformat() if self.expires_at else None,
            # Phase 1 compatibility
            'profile_id': self.profile_id,
            'matching_skills': self.matching_skills,
            'salary_alignment': self.salary_alignment,
            'location_compatibility': self.location_compatibility,
            'created_by_agent': self.created_by_agent,
            'match_strategy': self.match_strategy,
        }
