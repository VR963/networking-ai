"""
Application WebSocket Events - Phase 11

Real-time application status updates via WebSocket.

Event Types:
- application.status_changed: Application status changed
- application.recruiter_viewed: Recruiter viewed your application
- application.interview_scheduled: Interview scheduled
- application.interview_reminder: Interview reminder
- application.offer_extended: Job offer extended
- application.offer_updated: Offer terms updated
- application.feedback_received: Feedback from recruiter
- application.timeline_updated: Application timeline updated
- application.message_received: Message from recruiter

Usage:
    from networking_ai.services.realtime_application_service import RealtimeApplicationService

    app_service = RealtimeApplicationService(connection_manager)

    # When application status changes
    await app_service.broadcast_status_changed(
        user_id=1,
        application_id=123,
        job_title="Senior Python Developer",
        company_name="TechCorp",
        old_status="applied",
        new_status="under_review"
    )
"""

from datetime import datetime
from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field


class ApplicationStatusChangedEvent(BaseModel):
    """
    Event: Application status changed.

    Sent when application moves through pipeline stages.
    """
    event: str = Field(default="application.status_changed", description="Event type identifier")
    timestamp: datetime = Field(default_factory=datetime.utcnow, description="Event timestamp")

    # Application details
    application_id: int = Field(..., description="Application ID")
    job_id: int = Field(..., description="Job ID")
    job_title: str = Field(..., description="Job title")
    company_name: str = Field(..., description="Company name")
    company_logo: Optional[str] = Field(None, description="Company logo URL")

    # Status change
    old_status: str = Field(..., description="Previous status")
    new_status: str = Field(..., description="New status")
    status_display: str = Field(..., description="Human-readable new status")

    # Context
    message: str = Field(..., description="Status change message")
    next_steps: Optional[List[str]] = Field(None, description="What to do next")

    # Timeline
    days_since_applied: int = Field(..., description="Days since application submitted")
    estimated_decision_days: Optional[int] = Field(None, description="Days until expected decision")

    # Actions
    action_url: str = Field(..., description="URL to view application details")

    class Config:
        json_schema_extra = {
            "example": {
                "event": "application.status_changed",
                "timestamp": "2025-11-09T10:00:00Z",
                "application_id": 123,
                "job_id": 456,
                "job_title": "Senior Python Developer",
                "company_name": "TechCorp Inc.",
                "company_logo": "https://cdn.example.com/logos/techcorp.png",
                "old_status": "applied",
                "new_status": "under_review",
                "status_display": "Under Review",
                "message": "Great news! Your application is now under review by the hiring team.",
                "next_steps": [
                    "The hiring team will review your profile",
                    "You may be contacted for a phone screen within 5-7 days"
                ],
                "days_since_applied": 2,
                "estimated_decision_days": 7,
                "action_url": "/applications/123"
            }
        }


class RecruiterViewedEvent(BaseModel):
    """
    Event: Recruiter viewed your application.

    Sent when a recruiter/hiring manager views the application.
    """
    event: str = Field(default="application.recruiter_viewed", description="Event type identifier")
    timestamp: datetime = Field(default_factory=datetime.utcnow, description="Event timestamp")

    application_id: int = Field(..., description="Application ID")
    job_id: int = Field(..., description="Job ID")
    job_title: str = Field(..., description="Job title")
    company_name: str = Field(..., description="Company name")

    # Recruiter info
    recruiter_name: Optional[str] = Field(None, description="Recruiter name (if available)")
    recruiter_title: Optional[str] = Field(None, description="Recruiter title")

    # Viewing details
    viewed_at: datetime = Field(default_factory=datetime.utcnow, description="When viewed")
    view_duration_seconds: Optional[int] = Field(None, description="How long they viewed")
    sections_viewed: Optional[List[str]] = Field(None, description="Which sections they viewed")

    message: str = Field(..., description="Notification message")
    action_url: str = Field(..., description="URL to view application")

    class Config:
        json_schema_extra = {
            "example": {
                "event": "application.recruiter_viewed",
                "timestamp": "2025-11-09T11:00:00Z",
                "application_id": 123,
                "job_id": 456,
                "job_title": "Senior Python Developer",
                "company_name": "TechCorp Inc.",
                "recruiter_name": "Sarah Johnson",
                "recruiter_title": "Senior Technical Recruiter",
                "viewed_at": "2025-11-09T11:00:00Z",
                "view_duration_seconds": 180,
                "sections_viewed": ["Resume", "Portfolio", "Skills"],
                "message": "Sarah Johnson (Senior Technical Recruiter) viewed your application",
                "action_url": "/applications/123"
            }
        }


class InterviewScheduledEvent(BaseModel):
    """
    Event: Interview scheduled.

    Sent when an interview is scheduled for the application.
    """
    event: str = Field(default="application.interview_scheduled", description="Event type identifier")
    timestamp: datetime = Field(default_factory=datetime.utcnow, description="Event timestamp")

    application_id: int = Field(..., description="Application ID")
    interview_id: int = Field(..., description="Interview ID")
    job_id: int = Field(..., description="Job ID")
    job_title: str = Field(..., description="Job title")
    company_name: str = Field(..., description="Company name")

    # Interview details
    interview_type: str = Field(..., description="Interview type: phone, video, onsite, technical")
    interview_round: int = Field(..., description="Interview round number")
    scheduled_at: datetime = Field(..., description="Interview date/time")
    duration_minutes: int = Field(..., description="Interview duration in minutes")

    # Location/link
    location: Optional[str] = Field(None, description="Physical location (for onsite)")
    video_link: Optional[str] = Field(None, description="Video call link")
    phone_number: Optional[str] = Field(None, description="Phone number (for phone interviews)")

    # Interviewer(s)
    interviewer_names: List[str] = Field(default_factory=list, description="Interviewer names")
    interviewer_titles: List[str] = Field(default_factory=list, description="Interviewer titles")

    # Preparation
    preparation_notes: Optional[str] = Field(None, description="Preparation instructions")
    topics_to_cover: Optional[List[str]] = Field(None, description="Topics that will be covered")

    # Actions
    message: str = Field(..., description="Notification message")
    action_url: str = Field(..., description="URL to view interview details")
    calendar_link: Optional[str] = Field(None, description="Add to calendar link")

    class Config:
        json_schema_extra = {
            "example": {
                "event": "application.interview_scheduled",
                "timestamp": "2025-11-09T12:00:00Z",
                "application_id": 123,
                "interview_id": 1,
                "job_id": 456,
                "job_title": "Senior Python Developer",
                "company_name": "TechCorp Inc.",
                "interview_type": "video",
                "interview_round": 1,
                "scheduled_at": "2025-11-15T14:00:00Z",
                "duration_minutes": 60,
                "video_link": "https://zoom.us/j/123456789",
                "interviewer_names": ["John Smith", "Jane Doe"],
                "interviewer_titles": ["Engineering Manager", "Senior Engineer"],
                "preparation_notes": "Please review our tech stack documentation",
                "topics_to_cover": ["System design", "Python coding", "Past projects"],
                "message": "Interview scheduled for Nov 15 at 2:00 PM",
                "action_url": "/applications/123/interviews/1",
                "calendar_link": "/applications/123/interviews/1/calendar"
            }
        }


class InterviewReminderEvent(BaseModel):
    """
    Event: Interview reminder.

    Sent before an upcoming interview (typically 24h and 1h before).
    """
    event: str = Field(default="application.interview_reminder", description="Event type identifier")
    timestamp: datetime = Field(default_factory=datetime.utcnow, description="Event timestamp")

    application_id: int = Field(..., description="Application ID")
    interview_id: int = Field(..., description="Interview ID")
    job_title: str = Field(..., description="Job title")
    company_name: str = Field(..., description="Company name")

    # Interview details
    interview_type: str = Field(..., description="Interview type")
    scheduled_at: datetime = Field(..., description="Interview date/time")
    hours_until_interview: int = Field(..., description="Hours until interview starts")

    # Quick access
    video_link: Optional[str] = Field(None, description="Video call link")
    location: Optional[str] = Field(None, description="Location")

    message: str = Field(..., description="Reminder message")
    action_url: str = Field(..., description="URL to view interview details")

    class Config:
        json_schema_extra = {
            "example": {
                "event": "application.interview_reminder",
                "timestamp": "2025-11-15T13:00:00Z",
                "application_id": 123,
                "interview_id": 1,
                "job_title": "Senior Python Developer",
                "company_name": "TechCorp Inc.",
                "interview_type": "video",
                "scheduled_at": "2025-11-15T14:00:00Z",
                "hours_until_interview": 1,
                "video_link": "https://zoom.us/j/123456789",
                "message": "Interview in 1 hour! Join video call at 2:00 PM",
                "action_url": "/applications/123/interviews/1"
            }
        }


class OfferExtendedEvent(BaseModel):
    """
    Event: Job offer extended.

    Sent when company extends a job offer.
    """
    event: str = Field(default="application.offer_extended", description="Event type identifier")
    timestamp: datetime = Field(default_factory=datetime.utcnow, description="Event timestamp")

    application_id: int = Field(..., description="Application ID")
    offer_id: int = Field(..., description="Offer ID")
    job_id: int = Field(..., description="Job ID")
    job_title: str = Field(..., description="Job title")
    company_name: str = Field(..., description="Company name")
    company_logo: Optional[str] = Field(None, description="Company logo URL")

    # Offer details
    salary: int = Field(..., description="Annual salary")
    salary_currency: str = Field(default="USD", description="Currency")
    salary_formatted: str = Field(..., description="Formatted salary")

    # Additional compensation
    signing_bonus: Optional[int] = Field(None, description="Signing bonus")
    equity_value: Optional[int] = Field(None, description="Equity value")
    benefits_summary: Optional[List[str]] = Field(None, description="Key benefits")

    # Timing
    offer_expires_at: datetime = Field(..., description="Offer expiration date")
    days_to_decide: int = Field(..., description="Days remaining to accept")
    start_date: Optional[datetime] = Field(None, description="Proposed start date")

    # Actions
    message: str = Field(..., description="Congratulations message")
    action_url: str = Field(..., description="URL to view offer details")
    accept_url: str = Field(..., description="URL to accept offer")
    negotiate_url: Optional[str] = Field(None, description="URL to negotiate terms")

    class Config:
        json_schema_extra = {
            "example": {
                "event": "application.offer_extended",
                "timestamp": "2025-11-20T10:00:00Z",
                "application_id": 123,
                "offer_id": 1,
                "job_id": 456,
                "job_title": "Senior Python Developer",
                "company_name": "TechCorp Inc.",
                "company_logo": "https://cdn.example.com/logos/techcorp.png",
                "salary": 150000,
                "salary_currency": "USD",
                "salary_formatted": "$150,000/year",
                "signing_bonus": 10000,
                "equity_value": 50000,
                "benefits_summary": [
                    "Full health, dental, vision",
                    "401k with 6% match",
                    "Unlimited PTO",
                    "Remote-friendly"
                ],
                "offer_expires_at": "2025-11-27T23:59:59Z",
                "days_to_decide": 7,
                "start_date": "2025-12-15T00:00:00Z",
                "message": "Congratulations! TechCorp has extended you a job offer!",
                "action_url": "/applications/123/offer",
                "accept_url": "/applications/123/offer/accept",
                "negotiate_url": "/applications/123/offer/negotiate"
            }
        }


class OfferUpdatedEvent(BaseModel):
    """
    Event: Offer terms updated.

    Sent when offer terms are modified (e.g., after negotiation).
    """
    event: str = Field(default="application.offer_updated", description="Event type identifier")
    timestamp: datetime = Field(default_factory=datetime.utcnow, description="Event timestamp")

    application_id: int = Field(..., description="Application ID")
    offer_id: int = Field(..., description="Offer ID")
    job_title: str = Field(..., description="Job title")
    company_name: str = Field(..., description="Company name")

    # What changed
    updated_fields: List[str] = Field(..., description="Fields that were updated")
    update_summary: str = Field(..., description="Summary of changes")

    # New values (optional, only if changed)
    new_salary: Optional[int] = Field(None, description="Updated salary")
    new_signing_bonus: Optional[int] = Field(None, description="Updated signing bonus")
    new_equity_value: Optional[int] = Field(None, description="Updated equity")
    new_start_date: Optional[datetime] = Field(None, description="Updated start date")

    message: str = Field(..., description="Update message")
    action_url: str = Field(..., description="URL to view updated offer")

    class Config:
        json_schema_extra = {
            "example": {
                "event": "application.offer_updated",
                "timestamp": "2025-11-22T15:00:00Z",
                "application_id": 123,
                "offer_id": 1,
                "job_title": "Senior Python Developer",
                "company_name": "TechCorp Inc.",
                "updated_fields": ["salary", "signing_bonus"],
                "update_summary": "Salary increased to $160k and signing bonus increased to $15k",
                "new_salary": 160000,
                "new_signing_bonus": 15000,
                "message": "Great news! The offer has been updated with improved terms",
                "action_url": "/applications/123/offer"
            }
        }


class FeedbackReceivedEvent(BaseModel):
    """
    Event: Feedback received from recruiter.

    Sent when recruiter provides feedback on interview or application.
    """
    event: str = Field(default="application.feedback_received", description="Event type identifier")
    timestamp: datetime = Field(default_factory=datetime.utcnow, description="Event timestamp")

    application_id: int = Field(..., description="Application ID")
    job_title: str = Field(..., description="Job title")
    company_name: str = Field(..., description="Company name")

    # Feedback details
    feedback_type: str = Field(..., description="Type: interview, application, assessment")
    feedback_stage: str = Field(..., description="Which stage: phone_screen, technical, etc.")

    # Content
    feedback_summary: str = Field(..., description="Summary of feedback")
    strengths: Optional[List[str]] = Field(None, description="Highlighted strengths")
    areas_to_improve: Optional[List[str]] = Field(None, description="Areas for improvement")

    # Sentiment
    overall_sentiment: str = Field(..., description="Sentiment: positive, neutral, negative")

    message: str = Field(..., description="Notification message")
    action_url: str = Field(..., description="URL to view full feedback")

    class Config:
        json_schema_extra = {
            "example": {
                "event": "application.feedback_received",
                "timestamp": "2025-11-16T16:00:00Z",
                "application_id": 123,
                "job_title": "Senior Python Developer",
                "company_name": "TechCorp Inc.",
                "feedback_type": "interview",
                "feedback_stage": "technical",
                "feedback_summary": "Strong technical skills and problem-solving approach",
                "strengths": [
                    "Excellent Python knowledge",
                    "Clear communication",
                    "Good system design thinking"
                ],
                "areas_to_improve": [
                    "Could dive deeper into scalability considerations"
                ],
                "overall_sentiment": "positive",
                "message": "You've received feedback from your technical interview",
                "action_url": "/applications/123/feedback"
            }
        }


class TimelineUpdatedEvent(BaseModel):
    """
    Event: Application timeline updated.

    Sent when application timeline or expected next steps change.
    """
    event: str = Field(default="application.timeline_updated", description="Event type identifier")
    timestamp: datetime = Field(default_factory=datetime.utcnow, description="Event timestamp")

    application_id: int = Field(..., description="Application ID")
    job_title: str = Field(..., description="Job title")
    company_name: str = Field(..., description="Company name")

    # Timeline
    current_stage: str = Field(..., description="Current pipeline stage")
    completed_stages: List[str] = Field(default_factory=list, description="Completed stages")
    upcoming_stages: List[str] = Field(default_factory=list, description="Upcoming stages")

    # Next steps
    next_step: str = Field(..., description="Next expected step")
    expected_next_update: Optional[datetime] = Field(None, description="When to expect next update")
    days_until_next_step: Optional[int] = Field(None, description="Days until next step")

    message: str = Field(..., description="Timeline update message")
    action_url: str = Field(..., description="URL to view full timeline")

    class Config:
        json_schema_extra = {
            "example": {
                "event": "application.timeline_updated",
                "timestamp": "2025-11-17T10:00:00Z",
                "application_id": 123,
                "job_title": "Senior Python Developer",
                "company_name": "TechCorp Inc.",
                "current_stage": "technical_interview",
                "completed_stages": ["applied", "phone_screen"],
                "upcoming_stages": ["final_interview", "offer"],
                "next_step": "Final round interview with engineering leadership",
                "expected_next_update": "2025-11-20T00:00:00Z",
                "days_until_next_step": 3,
                "message": "Your application timeline has been updated",
                "action_url": "/applications/123/timeline"
            }
        }


class MessageReceivedEvent(BaseModel):
    """
    Event: Message received from recruiter.

    Sent when recruiter sends a message about the application.
    """
    event: str = Field(default="application.message_received", description="Event type identifier")
    timestamp: datetime = Field(default_factory=datetime.utcnow, description="Event timestamp")

    application_id: int = Field(..., description="Application ID")
    message_id: int = Field(..., description="Message ID")
    job_title: str = Field(..., description="Job title")
    company_name: str = Field(..., description="Company name")

    # Sender
    sender_name: str = Field(..., description="Recruiter name")
    sender_title: str = Field(..., description="Recruiter title")
    sender_avatar: Optional[str] = Field(None, description="Recruiter avatar URL")

    # Message
    subject: str = Field(..., description="Message subject")
    message_preview: str = Field(..., description="First 100 chars of message")
    priority: str = Field(default="normal", description="Priority: urgent, normal")

    # Actions
    action_url: str = Field(..., description="URL to read full message")
    reply_url: str = Field(..., description="URL to reply")

    class Config:
        json_schema_extra = {
            "example": {
                "event": "application.message_received",
                "timestamp": "2025-11-18T09:00:00Z",
                "application_id": 123,
                "message_id": 1,
                "job_title": "Senior Python Developer",
                "company_name": "TechCorp Inc.",
                "sender_name": "Sarah Johnson",
                "sender_title": "Senior Technical Recruiter",
                "sender_avatar": "https://cdn.example.com/avatars/sarah.jpg",
                "subject": "Question about your availability",
                "message_preview": "Hi! I wanted to check if you'd be available for a quick call this week to discuss...",
                "priority": "normal",
                "action_url": "/applications/123/messages/1",
                "reply_url": "/applications/123/messages/1/reply"
            }
        }


# Export all event types
__all__ = [
    "ApplicationStatusChangedEvent",
    "RecruiterViewedEvent",
    "InterviewScheduledEvent",
    "InterviewReminderEvent",
    "OfferExtendedEvent",
    "OfferUpdatedEvent",
    "FeedbackReceivedEvent",
    "TimelineUpdatedEvent",
    "MessageReceivedEvent",
]
