"""
UserProfile Pydantic Schemas for API request/response validation.
"""

from datetime import datetime
from typing import Optional, List, Dict
from pydantic import BaseModel, Field, validator, ConfigDict

from ..models.profile import ProfileVisibility


# ============================================================================
# Request Schemas
# ============================================================================

class ProfileCreateRequest(BaseModel):
    """Create user profile request."""
    headline: Optional[str] = Field(None, max_length=500)
    bio: Optional[str] = None
    location: Optional[str] = Field(None, max_length=255)
    website: Optional[str] = None
    linkedin_url: Optional[str] = None
    github_url: Optional[str] = None
    current_title: Optional[str] = Field(None, max_length=255)
    current_company: Optional[str] = Field(None, max_length=255)
    years_of_experience: Optional[int] = Field(None, ge=0, le=50)
    skills: Optional[List[str]] = None
    interests: Optional[List[str]] = None
    career_goals: Optional[str] = None
    desired_roles: Optional[List[str]] = None
    desired_locations: Optional[List[str]] = None
    desired_salary_min: Optional[int] = Field(None, ge=0)
    desired_salary_max: Optional[int] = Field(None, ge=0)
    is_looking_for_job: bool = True
    is_open_to_remote: bool = True
    is_open_to_relocation: bool = False
    visibility: ProfileVisibility = ProfileVisibility.PUBLIC


class ProfileUpdateRequest(BaseModel):
    """Update user profile request."""
    headline: Optional[str] = Field(None, max_length=500)
    bio: Optional[str] = None
    location: Optional[str] = Field(None, max_length=255)
    website: Optional[str] = None
    linkedin_url: Optional[str] = None
    github_url: Optional[str] = None
    current_title: Optional[str] = Field(None, max_length=255)
    current_company: Optional[str] = Field(None, max_length=255)
    years_of_experience: Optional[int] = Field(None, ge=0, le=50)
    skills: Optional[List[str]] = None
    interests: Optional[List[str]] = None
    career_goals: Optional[str] = None
    desired_roles: Optional[List[str]] = None
    desired_locations: Optional[List[str]] = None
    desired_salary_min: Optional[int] = Field(None, ge=0)
    desired_salary_max: Optional[int] = Field(None, ge=0)
    is_looking_for_job: Optional[bool] = None
    is_open_to_remote: Optional[bool] = None
    is_open_to_relocation: Optional[bool] = None
    visibility: Optional[ProfileVisibility] = None


class WorkExperienceItem(BaseModel):
    """Work experience entry."""
    title: str
    company: str
    start_date: str  # YYYY-MM format
    end_date: Optional[str] = None  # None = current
    description: Optional[str] = None


class EducationItem(BaseModel):
    """Education entry."""
    degree: str
    school: str
    field: Optional[str] = None
    year: Optional[int] = None


class ProfileWorkExperienceRequest(BaseModel):
    """Add/update work experience."""
    work_experience: List[WorkExperienceItem]


class ProfileEducationRequest(BaseModel):
    """Add/update education."""
    education: List[EducationItem]


# ============================================================================
# Response Schemas
# ============================================================================

class ProfileResponse(BaseModel):
    """User profile response."""
    id: int
    user_id: int
    headline: Optional[str]
    bio: Optional[str]
    location: Optional[str]
    website: Optional[str]
    linkedin_url: Optional[str]
    github_url: Optional[str]
    current_title: Optional[str]
    current_company: Optional[str]
    years_of_experience: Optional[int]
    skills: Optional[List[str]]
    interests: Optional[List[str]]
    career_goals: Optional[str]
    desired_roles: Optional[List[str]]
    desired_locations: Optional[List[str]]
    desired_salary_min: Optional[int]
    desired_salary_max: Optional[int]
    work_experience: Optional[List[Dict]]
    education: Optional[List[Dict]]
    cv_url: Optional[str]
    is_looking_for_job: bool
    visibility: ProfileVisibility
    is_open_to_remote: bool
    is_open_to_relocation: bool
    profile_completion_percentage: int
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class ProfileSummaryResponse(BaseModel):
    """Minimal profile info for listings."""
    id: int
    user_id: int
    headline: Optional[str]
    location: Optional[str]
    current_title: Optional[str]
    skills: Optional[List[str]]
    profile_completion_percentage: int

    model_config = ConfigDict(from_attributes=True)
