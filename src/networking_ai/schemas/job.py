"""
Job Pydantic Schemas for API request/response validation.
"""

from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel, Field, ConfigDict

from ..models.job import JobStatus, JobType, ExperienceLevel


# ============================================================================
# Request Schemas
# ============================================================================

class JobCreateRequest(BaseModel):
    """Create job posting request."""
    title: str = Field(..., min_length=1, max_length=255)
    description: str = Field(..., min_length=10)
    short_description: Optional[str] = Field(None, max_length=500)
    job_type: JobType
    experience_level: ExperienceLevel
    department: Optional[str] = Field(None, max_length=255)
    location: str = Field(..., max_length=255)
    is_remote: bool = False
    is_hybrid: bool = False
    salary_min: Optional[int] = Field(None, ge=0)
    salary_max: Optional[int] = Field(None, ge=0)
    salary_currency: str = Field("USD", max_length=10)
    salary_visible: bool = True
    required_skills: Optional[List[str]] = None
    preferred_skills: Optional[List[str]] = None
    required_experience_years: Optional[int] = Field(None, ge=0, le=50)
    education_requirements: Optional[str] = Field(None, max_length=500)
    benefits: Optional[List[str]] = None
    application_deadline: Optional[datetime] = None
    positions_available: int = Field(1, ge=1)
    application_url: Optional[str] = None


class JobUpdateRequest(BaseModel):
    """Update job posting request."""
    title: Optional[str] = Field(None, min_length=1, max_length=255)
    description: Optional[str] = Field(None, min_length=10)
    short_description: Optional[str] = Field(None, max_length=500)
    job_type: Optional[JobType] = None
    experience_level: Optional[ExperienceLevel] = None
    department: Optional[str] = Field(None, max_length=255)
    location: Optional[str] = Field(None, max_length=255)
    is_remote: Optional[bool] = None
    is_hybrid: Optional[bool] = None
    salary_min: Optional[int] = Field(None, ge=0)
    salary_max: Optional[int] = Field(None, ge=0)
    salary_visible: Optional[bool] = None
    required_skills: Optional[List[str]] = None
    preferred_skills: Optional[List[str]] = None
    required_experience_years: Optional[int] = Field(None, ge=0, le=50)
    education_requirements: Optional[str] = Field(None, max_length=500)
    benefits: Optional[List[str]] = None
    application_deadline: Optional[datetime] = None
    positions_available: Optional[int] = Field(None, ge=1)
    status: Optional[JobStatus] = None


class JobSearchRequest(BaseModel):
    """Job search/filter request."""
    query: Optional[str] = None  # Search in title/description
    location: Optional[str] = None
    job_type: Optional[JobType] = None
    experience_level: Optional[ExperienceLevel] = None
    is_remote: Optional[bool] = None
    salary_min: Optional[int] = None
    skills: Optional[List[str]] = None
    limit: int = Field(20, ge=1, le=100)
    offset: int = Field(0, ge=0)


# ============================================================================
# Response Schemas
# ============================================================================

class JobResponse(BaseModel):
    """Full job details response."""
    id: int
    company_id: int
    title: str
    description: str
    short_description: Optional[str]
    job_type: JobType
    experience_level: ExperienceLevel
    department: Optional[str]
    location: str
    is_remote: bool
    is_hybrid: bool
    salary_min: Optional[int]
    salary_max: Optional[int]
    salary_currency: str
    salary_visible: bool
    required_skills: Optional[List[str]]
    preferred_skills: Optional[List[str]]
    required_experience_years: Optional[int]
    education_requirements: Optional[str]
    benefits: Optional[List[str]]
    application_deadline: Optional[datetime]
    positions_available: int
    application_url: Optional[str]
    status: JobStatus
    is_featured: bool
    total_applications: int
    total_views: int
    total_matches: int
    created_at: datetime
    updated_at: datetime
    published_at: Optional[datetime]

    model_config = ConfigDict(from_attributes=True)


class JobSummaryResponse(BaseModel):
    """Minimal job info for listings."""
    id: int
    company_id: int
    title: str
    short_description: Optional[str]
    job_type: JobType
    experience_level: ExperienceLevel
    location: str
    is_remote: bool
    salary_min: Optional[int]
    salary_max: Optional[int]
    salary_visible: bool
    required_skills: Optional[List[str]]
    status: JobStatus
    total_applications: int
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class JobListResponse(BaseModel):
    """Paginated job list response."""
    jobs: List[JobSummaryResponse]
    total: int
    limit: int
    offset: int
