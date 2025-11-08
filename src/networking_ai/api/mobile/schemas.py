"""
Mobile API Pydantic Schemas.

Compact, mobile-optimized request/response schemas for all endpoints.
"""

from datetime import datetime
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, EmailStr, Field, ConfigDict
from enum import Enum


# ==================== Common Enums ====================

class Platform(str, Enum):
    """Mobile platform."""
    IOS = "ios"
    ANDROID = "android"


class JobType(str, Enum):
    """Job type."""
    FULL_TIME = "full_time"
    PART_TIME = "part_time"
    CONTRACT = "contract"
    INTERNSHIP = "internship"


class ExperienceLevel(str, Enum):
    """Experience level."""
    ENTRY = "entry"
    MID = "mid"
    SENIOR = "senior"
    LEAD = "lead"
    EXECUTIVE = "executive"


class ApplicationStatus(str, Enum):
    """Application status."""
    SUBMITTED = "submitted"
    SCREENING = "screening"
    INTERVIEWING = "interviewing"
    OFFERED = "offered"
    ACCEPTED = "accepted"
    REJECTED = "rejected"
    WITHDRAWN = "withdrawn"


# ==================== Device Schemas ====================

class DeviceInfo(BaseModel):
    """Device information."""
    model_config = ConfigDict(from_attributes=True)

    platform: Platform
    device_id: str = Field(..., min_length=1, max_length=255)
    push_token: Optional[str] = Field(None, max_length=500)
    app_version: Optional[str] = Field(None, max_length=50)
    os_version: Optional[str] = Field(None, max_length=50)


class DeviceResponse(BaseModel):
    """Device registration response."""
    model_config = ConfigDict(from_attributes=True)

    id: int
    device_id: str
    platform: str
    app_version: Optional[str]
    is_active: bool
    last_active: Optional[datetime]
    created_at: datetime


# ==================== Authentication Schemas ====================

class RegisterRequest(BaseModel):
    """User registration request."""
    model_config = ConfigDict(from_attributes=True)

    email: EmailStr
    password: str = Field(..., min_length=8, max_length=100)
    full_name: str = Field(..., min_length=1, max_length=255)
    role: str = Field(..., pattern="^(jobseeker|hiring_manager|recruiter)$")
    device: DeviceInfo


class LoginRequest(BaseModel):
    """User login request."""
    model_config = ConfigDict(from_attributes=True)

    email: EmailStr
    password: str
    device: DeviceInfo


class RefreshTokenRequest(BaseModel):
    """Token refresh request."""
    model_config = ConfigDict(from_attributes=True)

    refresh_token: str


class LogoutRequest(BaseModel):
    """Logout request."""
    model_config = ConfigDict(from_attributes=True)

    device_id: Optional[str] = None  # If not provided, logout all devices


class TokenResponse(BaseModel):
    """JWT token response."""
    model_config = ConfigDict(from_attributes=True)

    access_token: str
    refresh_token: Optional[str] = None  # Only on login/register
    token_type: str = "bearer"
    expires_in: int  # Seconds until expiration


class UserMobileResponse(BaseModel):
    """User profile response (mobile-optimized)."""
    model_config = ConfigDict(from_attributes=True)

    id: int
    email: str
    full_name: str
    role: str
    avatar_url: Optional[str] = None
    created_at: datetime


class AuthResponse(BaseModel):
    """Authentication response (register/login)."""
    model_config = ConfigDict(from_attributes=True)

    user: UserMobileResponse
    tokens: TokenResponse


# ==================== Job Schemas ====================

class CompanyCompact(BaseModel):
    """Compact company information for job listings."""
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    logo_url: Optional[str] = None


class SalaryRange(BaseModel):
    """Salary range."""
    model_config = ConfigDict(from_attributes=True)

    min: Optional[float]
    max: Optional[float]
    currency: str = "USD"


class JobCompact(BaseModel):
    """Compact job response for list views."""
    model_config = ConfigDict(from_attributes=True)

    id: int
    title: str
    company: CompanyCompact
    location: Optional[str]
    job_type: str
    experience_level: Optional[str]
    salary_range: Optional[SalaryRange] = None
    posted_at: datetime
    is_saved: bool = False
    is_applied: bool = False
    match_score: Optional[float] = None  # 0.0 - 1.0


class JobRequirements(BaseModel):
    """Job requirements."""
    model_config = ConfigDict(from_attributes=True)

    required_skills: List[str] = []
    preferred_skills: List[str] = []
    min_experience_years: Optional[int] = None


class JobDetail(BaseModel):
    """Detailed job information."""
    model_config = ConfigDict(from_attributes=True)

    id: int
    title: str
    description: str
    company: CompanyCompact
    location: Optional[str]
    job_type: str
    experience_level: Optional[str]
    salary_range: Optional[SalaryRange] = None
    requirements: Optional[JobRequirements] = None
    benefits: List[str] = []
    application_count: Optional[int] = None
    posted_at: datetime
    is_saved: bool = False
    is_applied: bool = False
    match_score: Optional[float] = None
    match_reasons: List[str] = []


class JobSearchRequest(BaseModel):
    """Job search request."""
    model_config = ConfigDict(from_attributes=True)

    q: Optional[str] = Field(None, description="Search query")
    location: Optional[str] = None
    job_type: Optional[JobType] = None
    experience_level: Optional[ExperienceLevel] = None
    cursor: Optional[str] = None
    limit: int = Field(20, ge=1, le=50)


class SavedJobResponse(BaseModel):
    """Saved job response."""
    model_config = ConfigDict(from_attributes=True)

    job_id: int
    notes: Optional[str] = None
    saved_at: datetime


# ==================== Application Schemas ====================

class QuestionAnswer(BaseModel):
    """Application question answer."""
    model_config = ConfigDict(from_attributes=True)

    question_id: int
    answer: str


class ApplicationCreateRequest(BaseModel):
    """Application submission request."""
    model_config = ConfigDict(from_attributes=True)

    job_id: int
    cover_letter: Optional[str] = Field(None, max_length=5000)
    resume_id: Optional[int] = None
    answers: List[QuestionAnswer] = []


class ApplicationCompact(BaseModel):
    """Compact application for list views."""
    model_config = ConfigDict(from_attributes=True)

    id: int
    job: JobCompact
    status: str
    submitted_at: datetime
    last_updated: datetime


class NextStep(BaseModel):
    """Next step in application process."""
    model_config = ConfigDict(from_attributes=True)

    type: str  # interview, assessment, etc.
    scheduled_at: Optional[datetime] = None
    description: Optional[str] = None


class TimelineEvent(BaseModel):
    """Application timeline event."""
    model_config = ConfigDict(from_attributes=True)

    stage: str
    timestamp: datetime
    note: Optional[str] = None


class InterviewCompact(BaseModel):
    """Compact interview information."""
    model_config = ConfigDict(from_attributes=True)

    id: int
    stage: str
    scheduled_at: Optional[datetime] = None
    interviewer: Optional[str] = None
    location: Optional[str] = None
    status: str


class MessageCompact(BaseModel):
    """Compact message."""
    model_config = ConfigDict(from_attributes=True)

    id: int
    from_type: str  # recruiter, system, etc.
    message: str
    timestamp: datetime


class ApplicationDetail(BaseModel):
    """Detailed application information."""
    model_config = ConfigDict(from_attributes=True)

    id: int
    job: JobDetail
    status: str
    submitted_at: datetime
    last_updated: datetime
    timeline: List[TimelineEvent] = []
    interviews: List[InterviewCompact] = []
    messages: List[MessageCompact] = []
    next_step: Optional[NextStep] = None


# ==================== Profile Schemas ====================

class ProfileStats(BaseModel):
    """User profile statistics."""
    model_config = ConfigDict(from_attributes=True)

    applications_submitted: int = 0
    interviews_scheduled: int = 0
    profile_views: int = 0


class ResumeCompact(BaseModel):
    """Compact resume information."""
    model_config = ConfigDict(from_attributes=True)

    id: int
    filename: str
    uploaded_at: datetime


class ProfileResponse(BaseModel):
    """User profile response."""
    model_config = ConfigDict(from_attributes=True)

    id: int
    email: str
    full_name: str
    role: str
    avatar_url: Optional[str] = None
    headline: Optional[str] = None
    location: Optional[str] = None
    resume: Optional[ResumeCompact] = None
    skills: List[str] = []
    experience_years: Optional[int] = None
    profile_completeness: float = 0.0  # 0.0 - 1.0
    stats: ProfileStats


class ProfileUpdateRequest(BaseModel):
    """Profile update request."""
    model_config = ConfigDict(from_attributes=True)

    full_name: Optional[str] = Field(None, min_length=1, max_length=255)
    headline: Optional[str] = Field(None, max_length=500)
    location: Optional[str] = Field(None, max_length=255)
    skills: Optional[List[str]] = None
    experience_years: Optional[int] = Field(None, ge=0, le=70)


class AvatarUploadResponse(BaseModel):
    """Avatar upload response."""
    model_config = ConfigDict(from_attributes=True)

    avatar_url: str


class ParsedResumeData(BaseModel):
    """Parsed resume data."""
    model_config = ConfigDict(from_attributes=True)

    skills: List[str] = []
    experience_years: Optional[int] = None


class ResumeUploadResponse(BaseModel):
    """Resume upload response."""
    model_config = ConfigDict(from_attributes=True)

    id: int
    filename: str
    uploaded_at: datetime
    parsed_data: Optional[ParsedResumeData] = None


# ==================== Notification Schemas ====================

class NotificationData(BaseModel):
    """Notification data payload."""
    model_config = ConfigDict(from_attributes=True)

    application_id: Optional[int] = None
    job_id: Optional[int] = None
    new_status: Optional[str] = None


class NotificationResponse(BaseModel):
    """Notification response."""
    model_config = ConfigDict(from_attributes=True)

    id: int
    type: str
    title: str
    message: str
    data: Optional[NotificationData] = None
    is_read: bool
    created_at: datetime


class NotificationChannelSettings(BaseModel):
    """Notification settings for a channel."""
    model_config = ConfigDict(from_attributes=True)

    application_updates: bool = True
    interview_reminders: bool = True
    new_matches: bool = True
    messages: bool = True


class NotificationSettingsResponse(BaseModel):
    """Notification preferences response."""
    model_config = ConfigDict(from_attributes=True)

    email: NotificationChannelSettings
    push: NotificationChannelSettings


class NotificationSettingsUpdateRequest(BaseModel):
    """Update notification settings request."""
    model_config = ConfigDict(from_attributes=True)

    email: Optional[NotificationChannelSettings] = None
    push: Optional[NotificationChannelSettings] = None


# ==================== Messaging Schemas ====================

class ParticipantCompact(BaseModel):
    """Compact participant information."""
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    role: str
    avatar_url: Optional[str] = None
    company: Optional[str] = None


class LastMessage(BaseModel):
    """Last message in conversation."""
    model_config = ConfigDict(from_attributes=True)

    text: str
    timestamp: datetime
    is_from_me: bool


class RelatedTo(BaseModel):
    """Related entity (application, job, etc.)."""
    model_config = ConfigDict(from_attributes=True)

    type: str  # application, job, etc.
    id: int
    job_title: Optional[str] = None


class ConversationCompact(BaseModel):
    """Compact conversation for list views."""
    model_config = ConfigDict(from_attributes=True)

    id: int
    participant: ParticipantCompact
    last_message: Optional[LastMessage] = None
    unread_count: int = 0
    related_to: Optional[RelatedTo] = None


class MessageDetail(BaseModel):
    """Detailed message."""
    model_config = ConfigDict(from_attributes=True)

    id: int
    from_user_id: int
    text: str
    timestamp: datetime
    is_read: bool


class ConversationDetail(BaseModel):
    """Detailed conversation."""
    model_config = ConfigDict(from_attributes=True)

    id: int
    participant: ParticipantCompact
    messages: List[MessageDetail] = []
    related_to: Optional[RelatedTo] = None


class SendMessageRequest(BaseModel):
    """Send message request."""
    model_config = ConfigDict(from_attributes=True)

    text: str = Field(..., min_length=1, max_length=5000)


class MessageResponse(BaseModel):
    """Message send response."""
    model_config = ConfigDict(from_attributes=True)

    id: int
    text: str
    timestamp: datetime


# ==================== Pagination Schemas ====================

class CursorMeta(BaseModel):
    """Cursor pagination metadata."""
    model_config = ConfigDict(from_attributes=True)

    next: Optional[str] = None
    has_more: bool = False


class PaginationMeta(BaseModel):
    """Pagination metadata."""
    model_config = ConfigDict(from_attributes=True)

    cursor: Optional[CursorMeta] = None
    count: int


# ==================== Generic Response Wrappers ====================

class JobListResponse(BaseModel):
    """Job list response."""
    model_config = ConfigDict(from_attributes=True)

    data: List[JobCompact]
    meta: PaginationMeta


class ApplicationListResponse(BaseModel):
    """Application list response."""
    model_config = ConfigDict(from_attributes=True)

    data: List[ApplicationCompact]
    meta: PaginationMeta


class NotificationListResponse(BaseModel):
    """Notification list response."""
    model_config = ConfigDict(from_attributes=True)

    data: List[NotificationResponse]
    meta: Dict[str, Any]  # Includes unread_count


class ConversationListResponse(BaseModel):
    """Conversation list response."""
    model_config = ConfigDict(from_attributes=True)

    data: List[ConversationCompact]


class DeviceListResponse(BaseModel):
    """Device list response."""
    model_config = ConfigDict(from_attributes=True)

    data: List[DeviceResponse]
