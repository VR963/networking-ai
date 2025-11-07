"""
Job Model - Job Postings.

Represents job opportunities posted by companies.
Each job gets its own AI agent to find matching candidates.
"""

from datetime import datetime
from enum import Enum
from typing import Dict

from sqlalchemy import Column, Integer, String, Text, Boolean, DateTime, ForeignKey, JSON, Enum as SQLEnum
from sqlalchemy.orm import relationship

from ..database import Base


class JobStatus(str, Enum):
    """Job posting status."""
    DRAFT = "draft"
    ACTIVE = "active"
    PAUSED = "paused"
    CLOSED = "closed"
    FILLED = "filled"


class JobType(str, Enum):
    """Job type."""
    FULL_TIME = "full_time"
    PART_TIME = "part_time"
    CONTRACT = "contract"
    TEMPORARY = "temporary"
    INTERNSHIP = "internship"


class ExperienceLevel(str, Enum):
    """Experience level required."""
    ENTRY_LEVEL = "entry_level"
    MID_LEVEL = "mid_level"
    SENIOR_LEVEL = "senior_level"
    LEAD = "lead"
    EXECUTIVE = "executive"


class Job(Base):
    """
    Job posting model.

    Each job has an AI agent created automatically to find matching candidates.
    """
    __tablename__ = "jobs"

    # Primary Key
    id = Column(Integer, primary_key=True, index=True)
    company_id = Column(Integer, ForeignKey("companies.id"), nullable=False, index=True)

    # Basic Info
    title = Column(String(255), nullable=False, index=True)
    description = Column(Text, nullable=False)
    short_description = Column(String(500), nullable=True)  # For listings

    # Job Details
    job_type = Column(SQLEnum(JobType), nullable=False, index=True)
    experience_level = Column(SQLEnum(ExperienceLevel), nullable=False, index=True)
    department = Column(String(255), nullable=True)

    # Location
    location = Column(String(255), nullable=False, index=True)
    is_remote = Column(Boolean, default=False, index=True)
    is_hybrid = Column(Boolean, default=False)

    # Compensation
    salary_min = Column(Integer, nullable=True)  # Annual in USD
    salary_max = Column(Integer, nullable=True)
    salary_currency = Column(String(10), default="USD")
    salary_visible = Column(Boolean, default=True)

    # Requirements
    required_skills = Column(JSON, nullable=True)  # List of skills
    preferred_skills = Column(JSON, nullable=True)
    required_experience_years = Column(Integer, nullable=True)
    education_requirements = Column(String(500), nullable=True)

    # Benefits
    benefits = Column(JSON, nullable=True)  # List of benefits

    # Application Details
    application_deadline = Column(DateTime(timezone=True), nullable=True)
    positions_available = Column(Integer, default=1)
    application_url = Column(String(500), nullable=True)  # External application URL (optional)

    # AI Matching
    ai_agent_id = Column(Integer, ForeignKey("ai_agents.id"), nullable=True)  # Job's AI agent
    job_embedding = Column(Text, nullable=True)  # Semantic embedding
    ai_generated_description = Column(Text, nullable=True)  # AI enhancement of description

    # Status
    status = Column(SQLEnum(JobStatus), default=JobStatus.DRAFT, index=True)
    is_featured = Column(Boolean, default=False)
    priority = Column(Integer, default=0)  # For sorting

    # Stats
    total_applications = Column(Integer, default=0)
    total_views = Column(Integer, default=0)
    total_matches = Column(Integer, default=0)

    # Timestamps
    created_at = Column(DateTime(timezone=True), default=datetime.utcnow, nullable=False, index=True)
    updated_at = Column(DateTime(timezone=True), default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    published_at = Column(DateTime(timezone=True), nullable=True)
    closed_at = Column(DateTime(timezone=True), nullable=True)

    # Relationships
    company = relationship("Company", back_populates="jobs")
    applications = relationship("Application", back_populates="job", cascade="all, delete-orphan")
    matches = relationship("Match", foreign_keys="Match.job_id", back_populates="job")
    ai_agent = relationship("AIAgent", foreign_keys=[ai_agent_id], post_update=True)

    def __repr__(self):
        return f"<Job {self.title} at {self.company.company_name if self.company else 'Unknown'}>"

    def to_dict(self) -> Dict:
        """Convert to dictionary."""
        return {
            'id': self.id,
            'company_id': self.company_id,
            'title': self.title,
            'description': self.description,
            'short_description': self.short_description,
            'job_type': self.job_type.value,
            'experience_level': self.experience_level.value,
            'department': self.department,
            'location': self.location,
            'is_remote': self.is_remote,
            'is_hybrid': self.is_hybrid,
            'salary_min': self.salary_min,
            'salary_max': self.salary_max,
            'salary_currency': self.salary_currency,
            'salary_visible': self.salary_visible,
            'required_skills': self.required_skills,
            'preferred_skills': self.preferred_skills,
            'required_experience_years': self.required_experience_years,
            'education_requirements': self.education_requirements,
            'benefits': self.benefits,
            'application_deadline': self.application_deadline.isoformat() if self.application_deadline else None,
            'positions_available': self.positions_available,
            'application_url': self.application_url,
            'status': self.status.value,
            'is_featured': self.is_featured,
            'total_applications': self.total_applications,
            'total_views': self.total_views,
            'total_matches': self.total_matches,
            'created_at': self.created_at.isoformat(),
            'updated_at': self.updated_at.isoformat(),
            'published_at': self.published_at.isoformat() if self.published_at else None,
        }
