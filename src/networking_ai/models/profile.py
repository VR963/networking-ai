"""
UserProfile Model - Job Seeker Profile Data.

Represents the CV/resume and professional profile of job seekers.
"""

from datetime import datetime
from enum import Enum
from typing import List, Dict

from sqlalchemy import Column, Integer, String, Text, Boolean, DateTime, ForeignKey, JSON, Enum as SQLEnum
from sqlalchemy.orm import relationship

from ..database import Base


class ProfileVisibility(str, Enum):
    """Profile visibility settings."""
    PUBLIC = "public"
    PRIVATE = "private"
    CONNECTIONS_ONLY = "connections_only"


class UserProfile(Base):
    """
    Job seeker profile model.

    This contains all the career-related information for job seekers.
    Used by AI agents to match with job opportunities.
    """
    __tablename__ = "user_profiles"
    __table_args__ = {'extend_existing': True}

    # Primary Key
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, unique=True, index=True)

    # Basic Info
    headline = Column(String(500), nullable=True)  # Professional headline
    bio = Column(Text, nullable=True)  # About me / summary
    location = Column(String(255), nullable=True)
    website = Column(String(500), nullable=True)
    linkedin_url = Column(String(500), nullable=True)
    github_url = Column(String(500), nullable=True)

    # Career Info
    current_title = Column(String(255), nullable=True)
    current_company = Column(String(255), nullable=True)
    years_of_experience = Column(Integer, nullable=True)

    # Skills & Interests
    skills = Column(JSON, nullable=True)  # List of skills
    interests = Column(JSON, nullable=True)  # Professional interests

    # Career Goals
    career_goals = Column(Text, nullable=True)
    desired_roles = Column(JSON, nullable=True)  # List of desired job titles
    desired_locations = Column(JSON, nullable=True)  # List of desired locations
    desired_salary_min = Column(Integer, nullable=True)  # Annual salary in USD
    desired_salary_max = Column(Integer, nullable=True)

    # Work Experience
    work_experience = Column(JSON, nullable=True)  # List of {title, company, start, end, description}

    # Education
    education = Column(JSON, nullable=True)  # List of {degree, school, year, field}

    # CV/Resume
    cv_url = Column(String(500), nullable=True)  # S3 URL to uploaded CV
    cv_text = Column(Text, nullable=True)  # Extracted text from CV
    cv_uploaded_at = Column(DateTime(timezone=True), nullable=True)

    # AI Profile
    ai_generated_summary = Column(Text, nullable=True)  # AI-generated profile summary
    profile_embedding = Column(Text, nullable=True)  # Semantic embedding (JSON string)

    # Settings
    is_looking_for_job = Column(Boolean, default=True)
    visibility = Column(SQLEnum(ProfileVisibility), default=ProfileVisibility.PUBLIC)
    is_open_to_remote = Column(Boolean, default=True)
    is_open_to_relocation = Column(Boolean, default=False)

    # Profile Completion
    profile_completion_percentage = Column(Integer, default=0)  # 0-100

    # Timestamps
    created_at = Column(DateTime(timezone=True), default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime(timezone=True), default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    # Relationships
    user = relationship("User", back_populates="profile")
    matches = relationship("Match", foreign_keys="Match.profile_id", back_populates="profile")

    def __repr__(self):
        return f"<UserProfile user_id={self.user_id} headline={self.headline}>"

    def calculate_completion_percentage(self) -> int:
        """Calculate profile completion percentage."""
        fields = [
            self.headline,
            self.bio,
            self.location,
            self.current_title,
            self.skills,
            self.work_experience,
            self.education,
            self.desired_roles,
            self.cv_url,
        ]

        completed = sum(1 for field in fields if field)
        percentage = int((completed / len(fields)) * 100)

        self.profile_completion_percentage = percentage
        return percentage

    def to_dict(self) -> Dict:
        """Convert to dictionary."""
        return {
            'id': self.id,
            'user_id': self.user_id,
            'headline': self.headline,
            'bio': self.bio,
            'location': self.location,
            'website': self.website,
            'linkedin_url': self.linkedin_url,
            'github_url': self.github_url,
            'current_title': self.current_title,
            'current_company': self.current_company,
            'years_of_experience': self.years_of_experience,
            'skills': self.skills,
            'interests': self.interests,
            'career_goals': self.career_goals,
            'desired_roles': self.desired_roles,
            'desired_locations': self.desired_locations,
            'desired_salary_min': self.desired_salary_min,
            'desired_salary_max': self.desired_salary_max,
            'work_experience': self.work_experience,
            'education': self.education,
            'cv_url': self.cv_url,
            'is_looking_for_job': self.is_looking_for_job,
            'visibility': self.visibility.value,
            'is_open_to_remote': self.is_open_to_remote,
            'is_open_to_relocation': self.is_open_to_relocation,
            'profile_completion_percentage': self.profile_completion_percentage,
            'created_at': self.created_at.isoformat(),
            'updated_at': self.updated_at.isoformat(),
        }
