"""
Job WebSocket Events - Phase 11

Real-time job feed events for live job updates via WebSocket.

Event Types:
- job.posted: New job posted (sent to matching talent)
- job.updated: Job details updated
- job.closed: Job closed/filled
- job.expiring: Job expiring soon (alert)
- job.matched: User matched with job
- job.subscription.created: User subscribed to job alerts
- job.subscription.deleted: User unsubscribed
- job.feed.update: Batch feed update

Usage:
    from networking_ai.services.realtime_job_service import RealtimeJobService

    job_service = RealtimeJobService(connection_manager)

    # Broadcast new job to matching talent
    await job_service.broadcast_job_posted(
        job_id=123,
        title="Senior Python Developer",
        company_name="TechCorp",
        location="San Francisco, CA",
        salary_range="$120k-$180k",
        skills=["Python", "Django", "PostgreSQL"],
        matched_user_ids=[1, 2, 3]  # Only send to matching users
    )
"""

from datetime import datetime
from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field


class JobPostedEvent(BaseModel):
    """
    Event: New job posted.

    Sent to talent matching job criteria (skills, location, experience).
    """
    event: str = Field(default="job.posted", description="Event type identifier")
    timestamp: datetime = Field(default_factory=datetime.utcnow, description="Event timestamp")

    # Job details
    job_id: int = Field(..., description="Job ID")
    title: str = Field(..., description="Job title")
    company_name: str = Field(..., description="Company name")
    company_logo: Optional[str] = Field(None, description="Company logo URL")

    # Location
    location: str = Field(..., description="Job location")
    remote_type: str = Field(default="on_site", description="Remote type: on_site, hybrid, remote")

    # Compensation
    salary_min: Optional[int] = Field(None, description="Minimum salary")
    salary_max: Optional[int] = Field(None, description="Maximum salary")
    salary_currency: str = Field(default="USD", description="Salary currency")
    salary_range: Optional[str] = Field(None, description="Formatted salary range")

    # Requirements
    skills: List[str] = Field(default_factory=list, description="Required skills")
    experience_min: Optional[int] = Field(None, description="Minimum years of experience")
    experience_max: Optional[int] = Field(None, description="Maximum years of experience")

    # Match score
    match_score: Optional[float] = Field(None, description="Match score (0-1) for this user")
    match_reasons: List[str] = Field(default_factory=list, description="Why this job matches")

    # Preview
    description_preview: str = Field(..., description="First 200 chars of description")
    job_type: str = Field(..., description="Job type: full_time, part_time, contract")
    posted_at: datetime = Field(default_factory=datetime.utcnow, description="When job was posted")

    # Actions
    action_url: str = Field(..., description="URL to view job details")
    quick_apply: bool = Field(default=False, description="Supports quick apply")

    class Config:
        json_schema_extra = {
            "example": {
                "event": "job.posted",
                "timestamp": "2025-11-09T10:00:00Z",
                "job_id": 123,
                "title": "Senior Python Developer",
                "company_name": "TechCorp Inc.",
                "company_logo": "https://cdn.example.com/logos/techcorp.png",
                "location": "San Francisco, CA",
                "remote_type": "hybrid",
                "salary_min": 120000,
                "salary_max": 180000,
                "salary_currency": "USD",
                "salary_range": "$120k-$180k",
                "skills": ["Python", "Django", "PostgreSQL", "AWS"],
                "experience_min": 3,
                "experience_max": 7,
                "match_score": 0.92,
                "match_reasons": [
                    "Your Python skills match 100%",
                    "Location preference match",
                    "Salary meets your expectations"
                ],
                "description_preview": "We're looking for a Senior Python Developer to join our growing team...",
                "job_type": "full_time",
                "posted_at": "2025-11-09T10:00:00Z",
                "action_url": "/jobs/123",
                "quick_apply": True
            }
        }


class JobUpdatedEvent(BaseModel):
    """
    Event: Job details updated.

    Sent to users who have saved/applied to this job.
    """
    event: str = Field(default="job.updated", description="Event type identifier")
    timestamp: datetime = Field(default_factory=datetime.utcnow, description="Event timestamp")

    job_id: int = Field(..., description="Job ID")
    title: str = Field(..., description="Job title")
    company_name: str = Field(..., description="Company name")

    # What changed
    updated_fields: List[str] = Field(..., description="Fields that were updated")
    update_summary: str = Field(..., description="Human-readable summary of changes")

    # Key details (may have changed)
    location: Optional[str] = Field(None, description="Updated location")
    remote_type: Optional[str] = Field(None, description="Updated remote type")
    salary_range: Optional[str] = Field(None, description="Updated salary range")
    skills: Optional[List[str]] = Field(None, description="Updated skills")

    action_url: str = Field(..., description="URL to view updated job")

    class Config:
        json_schema_extra = {
            "example": {
                "event": "job.updated",
                "timestamp": "2025-11-09T11:00:00Z",
                "job_id": 123,
                "title": "Senior Python Developer",
                "company_name": "TechCorp Inc.",
                "updated_fields": ["salary_range", "remote_type"],
                "update_summary": "Salary increased to $130k-$190k and now fully remote",
                "location": "Remote",
                "remote_type": "remote",
                "salary_range": "$130k-$190k",
                "skills": ["Python", "Django", "PostgreSQL", "AWS"],
                "action_url": "/jobs/123"
            }
        }


class JobClosedEvent(BaseModel):
    """
    Event: Job closed/filled.

    Sent to users who saved this job or have pending applications.
    """
    event: str = Field(default="job.closed", description="Event type identifier")
    timestamp: datetime = Field(default_factory=datetime.utcnow, description="Event timestamp")

    job_id: int = Field(..., description="Job ID")
    title: str = Field(..., description="Job title")
    company_name: str = Field(..., description="Company name")

    reason: str = Field(..., description="Why job was closed: filled, expired, cancelled")
    message: str = Field(..., description="Message to user")

    # Recommendations
    similar_jobs: List[int] = Field(default_factory=list, description="IDs of similar open jobs")

    action_url: Optional[str] = Field(None, description="URL to view similar jobs")

    class Config:
        json_schema_extra = {
            "example": {
                "event": "job.closed",
                "timestamp": "2025-11-09T12:00:00Z",
                "job_id": 123,
                "title": "Senior Python Developer",
                "company_name": "TechCorp Inc.",
                "reason": "filled",
                "message": "This position has been filled. Check out similar opportunities!",
                "similar_jobs": [124, 125, 126],
                "action_url": "/jobs/search?similar_to=123"
            }
        }


class JobExpiringEvent(BaseModel):
    """
    Event: Job expiring soon.

    Sent to users who saved this job but haven't applied yet.
    """
    event: str = Field(default="job.expiring", description="Event type identifier")
    timestamp: datetime = Field(default_factory=datetime.utcnow, description="Event timestamp")

    job_id: int = Field(..., description="Job ID")
    title: str = Field(..., description="Job title")
    company_name: str = Field(..., description="Company name")

    expires_in_hours: int = Field(..., description="Hours until expiration")
    expires_at: datetime = Field(..., description="Exact expiration time")

    message: str = Field(..., description="Urgency message")
    action_url: str = Field(..., description="URL to apply now")
    quick_apply: bool = Field(default=False, description="Supports quick apply")

    class Config:
        json_schema_extra = {
            "example": {
                "event": "job.expiring",
                "timestamp": "2025-11-09T13:00:00Z",
                "job_id": 123,
                "title": "Senior Python Developer",
                "company_name": "TechCorp Inc.",
                "expires_in_hours": 24,
                "expires_at": "2025-11-10T13:00:00Z",
                "message": "This job expires in 24 hours! Apply now to not miss out.",
                "action_url": "/jobs/123/apply",
                "quick_apply": True
            }
        }


class JobMatchedEvent(BaseModel):
    """
    Event: User matched with job.

    Sent when matching algorithm finds a high-quality match.
    """
    event: str = Field(default="job.matched", description="Event type identifier")
    timestamp: datetime = Field(default_factory=datetime.utcnow, description="Event timestamp")

    job_id: int = Field(..., description="Job ID")
    title: str = Field(..., description="Job title")
    company_name: str = Field(..., description="Company name")
    company_logo: Optional[str] = Field(None, description="Company logo URL")

    # Match details
    match_score: float = Field(..., description="Match score (0-1)")
    match_quality: str = Field(..., description="Match quality: excellent, good, fair")
    match_reasons: List[str] = Field(..., description="Why this is a good match")

    # Job preview
    location: str = Field(..., description="Job location")
    remote_type: str = Field(..., description="Remote type")
    salary_range: Optional[str] = Field(None, description="Salary range")
    skills: List[str] = Field(default_factory=list, description="Required skills")
    description_preview: str = Field(..., description="Job description preview")

    action_url: str = Field(..., description="URL to view job")
    quick_apply: bool = Field(default=False, description="Supports quick apply")

    class Config:
        json_schema_extra = {
            "example": {
                "event": "job.matched",
                "timestamp": "2025-11-09T14:00:00Z",
                "job_id": 125,
                "title": "Lead Backend Engineer",
                "company_name": "StartupXYZ",
                "company_logo": "https://cdn.example.com/logos/startupxyz.png",
                "match_score": 0.95,
                "match_quality": "excellent",
                "match_reasons": [
                    "Your backend expertise is a perfect fit",
                    "Leadership experience matches requirements",
                    "Salary expectation aligned ($150k-$200k)"
                ],
                "location": "Remote",
                "remote_type": "remote",
                "salary_range": "$150k-$200k",
                "skills": ["Python", "Microservices", "Kubernetes", "Team Leadership"],
                "description_preview": "Lead our backend team building scalable microservices...",
                "action_url": "/jobs/125",
                "quick_apply": True
            }
        }


class JobSubscriptionCreatedEvent(BaseModel):
    """
    Event: User subscribed to job alerts.

    Confirmation that subscription was created successfully.
    """
    event: str = Field(default="job.subscription.created", description="Event type identifier")
    timestamp: datetime = Field(default_factory=datetime.utcnow, description="Event timestamp")

    subscription_id: int = Field(..., description="Subscription ID")

    # Filters
    keywords: Optional[List[str]] = Field(None, description="Keyword filters")
    locations: Optional[List[str]] = Field(None, description="Location filters")
    remote_types: Optional[List[str]] = Field(None, description="Remote type filters")
    skills: Optional[List[str]] = Field(None, description="Skill filters")
    salary_min: Optional[int] = Field(None, description="Minimum salary filter")

    frequency: str = Field(default="instant", description="Notification frequency: instant, daily, weekly")
    message: str = Field(..., description="Confirmation message")

    class Config:
        json_schema_extra = {
            "example": {
                "event": "job.subscription.created",
                "timestamp": "2025-11-09T15:00:00Z",
                "subscription_id": 42,
                "keywords": ["Python", "Backend"],
                "locations": ["San Francisco", "Remote"],
                "remote_types": ["remote", "hybrid"],
                "skills": ["Python", "Django", "PostgreSQL"],
                "salary_min": 120000,
                "frequency": "instant",
                "message": "You'll receive instant notifications when jobs matching your criteria are posted!"
            }
        }


class JobSubscriptionDeletedEvent(BaseModel):
    """
    Event: User unsubscribed from job alerts.

    Confirmation that subscription was deleted.
    """
    event: str = Field(default="job.subscription.deleted", description="Event type identifier")
    timestamp: datetime = Field(default_factory=datetime.utcnow, description="Event timestamp")

    subscription_id: int = Field(..., description="Subscription ID that was deleted")
    message: str = Field(..., description="Confirmation message")

    class Config:
        json_schema_extra = {
            "example": {
                "event": "job.subscription.deleted",
                "timestamp": "2025-11-09T16:00:00Z",
                "subscription_id": 42,
                "message": "Job alert subscription deleted successfully"
            }
        }


class JobFeedUpdateEvent(BaseModel):
    """
    Event: Batch feed update.

    Sent when user's job feed has been updated with multiple new jobs.
    Used for daily digest or when user opens app after being offline.
    """
    event: str = Field(default="job.feed.update", description="Event type identifier")
    timestamp: datetime = Field(default_factory=datetime.utcnow, description="Event timestamp")

    # Summary
    new_jobs_count: int = Field(..., description="Number of new jobs")
    new_matches_count: int = Field(..., description="Number of new matches")
    expiring_jobs_count: int = Field(..., description="Number of jobs expiring soon")

    # Top matches (summary only, not full jobs)
    top_matches: List[Dict[str, Any]] = Field(default_factory=list, description="Top 3 job matches")

    # Stats
    total_active_jobs: int = Field(..., description="Total active jobs matching user")

    action_url: str = Field(default="/jobs", description="URL to view full feed")
    message: str = Field(..., description="Summary message")

    class Config:
        json_schema_extra = {
            "example": {
                "event": "job.feed.update",
                "timestamp": "2025-11-09T17:00:00Z",
                "new_jobs_count": 12,
                "new_matches_count": 3,
                "expiring_jobs_count": 2,
                "top_matches": [
                    {
                        "job_id": 130,
                        "title": "Senior Python Developer",
                        "company": "TechCorp",
                        "match_score": 0.95
                    },
                    {
                        "job_id": 131,
                        "title": "Backend Lead",
                        "company": "StartupXYZ",
                        "match_score": 0.92
                    },
                    {
                        "job_id": 132,
                        "title": "Full Stack Engineer",
                        "company": "BigCo",
                        "match_score": 0.88
                    }
                ],
                "total_active_jobs": 47,
                "action_url": "/jobs",
                "message": "12 new jobs posted, including 3 excellent matches!"
            }
        }


# Export all event types
__all__ = [
    "JobPostedEvent",
    "JobUpdatedEvent",
    "JobClosedEvent",
    "JobExpiringEvent",
    "JobMatchedEvent",
    "JobSubscriptionCreatedEvent",
    "JobSubscriptionDeletedEvent",
    "JobFeedUpdateEvent",
]
