"""
Analytics Models - Phase 5.

Tracks metrics, KPIs, and performance data for hiring pipeline analytics.
"""

from datetime import datetime
from enum import Enum
from typing import Dict, Optional
from sqlalchemy import Column, Integer, String, Float, DateTime, ForeignKey, JSON, Enum as SQLEnum, Date
from sqlalchemy.orm import relationship

from ..database import Base


class MetricType(str, Enum):
    """Type of metric being tracked."""
    TIME_TO_HIRE = "time_to_hire"
    COST_PER_HIRE = "cost_per_hire"
    APPLICATION_RATE = "application_rate"
    INTERVIEW_RATE = "interview_rate"
    OFFER_RATE = "offer_rate"
    ACCEPTANCE_RATE = "acceptance_rate"
    QUALITY_OF_HIRE = "quality_of_hire"
    SOURCE_EFFECTIVENESS = "source_effectiveness"
    DIVERSITY_METRICS = "diversity_metrics"


class ReportType(str, Enum):
    """Type of report."""
    HIRING_FUNNEL = "hiring_funnel"
    TIME_TO_HIRE = "time_to_hire"
    COST_ANALYSIS = "cost_analysis"
    SOURCE_ANALYSIS = "source_analysis"
    INTERVIEWER_PERFORMANCE = "interviewer_performance"
    AI_PERFORMANCE = "ai_performance"
    CANDIDATE_EXPERIENCE = "candidate_experience"
    DIVERSITY_REPORT = "diversity_report"


class HiringMetrics(Base):
    """
    Hiring metrics for company analytics.

    Stores aggregated metrics for a specific time period.
    """
    __tablename__ = "hiring_metrics"
    __table_args__ = {'extend_existing': True}

    # Primary Key
    id = Column(Integer, primary_key=True, index=True)

    # Related Entity
    company_id = Column(Integer, ForeignKey("companies.id"), nullable=False, index=True)

    # Time Period
    period_start = Column(Date, nullable=False, index=True)
    period_end = Column(Date, nullable=False, index=True)
    period_type = Column(String(20), nullable=False)  # daily, weekly, monthly, quarterly, yearly

    # Volume Metrics
    total_jobs_posted = Column(Integer, default=0)
    total_applications = Column(Integer, default=0)
    total_interviews = Column(Integer, default=0)
    total_offers = Column(Integer, default=0)
    total_hires = Column(Integer, default=0)

    # Conversion Rates (as percentages)
    application_to_interview_rate = Column(Float, default=0.0)  # % of apps that get interviews
    interview_to_offer_rate = Column(Float, default=0.0)  # % of interviews that get offers
    offer_acceptance_rate = Column(Float, default=0.0)  # % of offers accepted

    # Time Metrics (in days)
    avg_time_to_hire = Column(Float, default=0.0)  # Average days from application to hire
    avg_time_to_interview = Column(Float, default=0.0)  # Average days from application to first interview
    avg_time_to_offer = Column(Float, default=0.0)  # Average days from application to offer

    # Cost Metrics
    total_hiring_cost = Column(Float, default=0.0)  # Total cost for period
    avg_cost_per_hire = Column(Float, default=0.0)  # Average cost per successful hire
    avg_cost_per_application = Column(Float, default=0.0)  # Cost per application processed

    # Quality Metrics
    avg_candidate_quality_score = Column(Float, default=0.0)  # Average quality score (0-100)
    avg_interview_rating = Column(Float, default=0.0)  # Average interview feedback rating

    # Source Effectiveness (JSON: {source_name: {applications, hires, conversion_rate}})
    source_metrics = Column(JSON, nullable=True)

    # AI Performance Metrics
    ai_match_accuracy = Column(Float, default=0.0)  # % of AI matches that led to interviews
    ai_screening_accuracy = Column(Float, default=0.0)  # % of AI screens that passed human review

    # Timestamps
    calculated_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    company = relationship("Company", foreign_keys=[company_id])

    def __repr__(self):
        return f"<HiringMetrics {self.company_id}: {self.period_start} - {self.period_end}>"

    def to_dict(self) -> Dict:
        """Convert to dictionary."""
        return {
            "id": self.id,
            "company_id": self.company_id,
            "period_start": self.period_start.isoformat(),
            "period_end": self.period_end.isoformat(),
            "period_type": self.period_type,
            "volume_metrics": {
                "total_jobs_posted": self.total_jobs_posted,
                "total_applications": self.total_applications,
                "total_interviews": self.total_interviews,
                "total_offers": self.total_offers,
                "total_hires": self.total_hires,
            },
            "conversion_rates": {
                "application_to_interview_rate": self.application_to_interview_rate,
                "interview_to_offer_rate": self.interview_to_offer_rate,
                "offer_acceptance_rate": self.offer_acceptance_rate,
            },
            "time_metrics": {
                "avg_time_to_hire": self.avg_time_to_hire,
                "avg_time_to_interview": self.avg_time_to_interview,
                "avg_time_to_offer": self.avg_time_to_offer,
            },
            "cost_metrics": {
                "total_hiring_cost": self.total_hiring_cost,
                "avg_cost_per_hire": self.avg_cost_per_hire,
                "avg_cost_per_application": self.avg_cost_per_application,
            },
            "quality_metrics": {
                "avg_candidate_quality_score": self.avg_candidate_quality_score,
                "avg_interview_rating": self.avg_interview_rating,
            },
            "ai_performance": {
                "ai_match_accuracy": self.ai_match_accuracy,
                "ai_screening_accuracy": self.ai_screening_accuracy,
            },
            "source_metrics": self.source_metrics,
            "calculated_at": self.calculated_at.isoformat(),
        }


class JobAnalytics(Base):
    """
    Analytics for individual job postings.

    Tracks detailed metrics per job.
    """
    __tablename__ = "job_analytics"
    __table_args__ = {'extend_existing': True}

    # Primary Key
    id = Column(Integer, primary_key=True, index=True)

    # Related Entity
    job_id = Column(Integer, ForeignKey("jobs.id"), nullable=False, index=True, unique=True)
    company_id = Column(Integer, ForeignKey("companies.id"), nullable=False, index=True)

    # Job Status
    is_active = Column(Integer, default=1)  # Whether job is currently open
    days_open = Column(Integer, default=0)  # How many days job has been open

    # Application Metrics
    total_views = Column(Integer, default=0)  # How many people viewed the job
    total_applications = Column(Integer, default=0)
    applications_this_week = Column(Integer, default=0)
    applications_this_month = Column(Integer, default=0)

    # Pipeline Metrics
    applications_in_review = Column(Integer, default=0)
    applications_screening = Column(Integer, default=0)
    applications_interviewing = Column(Integer, default=0)
    applications_offered = Column(Integer, default=0)
    applications_hired = Column(Integer, default=0)
    applications_rejected = Column(Integer, default=0)

    # Conversion Metrics
    view_to_application_rate = Column(Float, default=0.0)  # % of views that apply
    application_to_interview_rate = Column(Float, default=0.0)
    interview_to_offer_rate = Column(Float, default=0.0)
    offer_to_hire_rate = Column(Float, default=0.0)

    # Time Metrics
    avg_time_to_first_interview = Column(Float, default=0.0)  # Days
    avg_time_to_offer = Column(Float, default=0.0)
    avg_time_to_hire = Column(Float, default=0.0)

    # Quality Metrics
    avg_candidate_match_score = Column(Float, default=0.0)  # Average match score (0-1)
    avg_interview_rating = Column(Float, default=0.0)  # Average interview feedback

    # Cost Metrics
    total_cost = Column(Float, default=0.0)  # Total cost for this job
    cost_per_hire = Column(Float, default=0.0)  # If position filled

    # Source Breakdown (JSON: {source: count})
    application_sources = Column(JSON, nullable=True)

    # Demographics (for diversity tracking, aggregated/anonymized)
    diversity_metrics = Column(JSON, nullable=True)

    # Timestamps
    last_calculated = Column(DateTime, default=datetime.utcnow)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    job = relationship("Job", foreign_keys=[job_id])
    company = relationship("Company", foreign_keys=[company_id])

    def __repr__(self):
        return f"<JobAnalytics job_id={self.job_id}>"

    def calculate_conversion_rates(self):
        """Calculate conversion rates based on current counts."""
        if self.total_views > 0:
            self.view_to_application_rate = (self.total_applications / self.total_views) * 100

        if self.total_applications > 0:
            total_interviewed = self.applications_interviewing + self.applications_offered + self.applications_hired
            self.application_to_interview_rate = (total_interviewed / self.total_applications) * 100

        interviewed_count = self.applications_interviewing + self.applications_offered + self.applications_hired
        if interviewed_count > 0:
            self.interview_to_offer_rate = ((self.applications_offered + self.applications_hired) / interviewed_count) * 100

        if self.applications_offered > 0:
            self.offer_to_hire_rate = (self.applications_hired / self.applications_offered) * 100

    def to_dict(self) -> Dict:
        """Convert to dictionary."""
        return {
            "job_id": self.job_id,
            "company_id": self.company_id,
            "status": {
                "is_active": bool(self.is_active),
                "days_open": self.days_open,
            },
            "applications": {
                "total": self.total_applications,
                "this_week": self.applications_this_week,
                "this_month": self.applications_this_month,
                "total_views": self.total_views,
            },
            "pipeline": {
                "in_review": self.applications_in_review,
                "screening": self.applications_screening,
                "interviewing": self.applications_interviewing,
                "offered": self.applications_offered,
                "hired": self.applications_hired,
                "rejected": self.applications_rejected,
            },
            "conversion_rates": {
                "view_to_application": round(self.view_to_application_rate, 2),
                "application_to_interview": round(self.application_to_interview_rate, 2),
                "interview_to_offer": round(self.interview_to_offer_rate, 2),
                "offer_to_hire": round(self.offer_to_hire_rate, 2),
            },
            "time_metrics": {
                "avg_time_to_first_interview": round(self.avg_time_to_first_interview, 1),
                "avg_time_to_offer": round(self.avg_time_to_offer, 1),
                "avg_time_to_hire": round(self.avg_time_to_hire, 1),
            },
            "quality": {
                "avg_match_score": round(self.avg_candidate_match_score, 2),
                "avg_interview_rating": round(self.avg_interview_rating, 2),
            },
            "cost": {
                "total_cost": self.total_cost,
                "cost_per_hire": self.cost_per_hire,
            },
            "sources": self.application_sources,
            "diversity": self.diversity_metrics,
            "last_calculated": self.last_calculated.isoformat(),
        }


class CandidateAnalytics(Base):
    """
    Analytics for candidate performance and activity.

    Tracks individual candidate metrics for their dashboard.
    """
    __tablename__ = "candidate_analytics"
    __table_args__ = {'extend_existing': True}

    # Primary Key
    id = Column(Integer, primary_key=True, index=True)

    # Related Entity
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True, unique=True)

    # Application Activity
    total_applications = Column(Integer, default=0)
    applications_this_month = Column(Integer, default=0)
    active_applications = Column(Integer, default=0)  # Currently in progress

    # Success Metrics
    total_interviews = Column(Integer, default=0)
    total_offers = Column(Integer, default=0)
    total_hires = Column(Integer, default=0)
    total_rejections = Column(Integer, default=0)

    # Conversion Rates
    application_to_interview_rate = Column(Float, default=0.0)
    interview_to_offer_rate = Column(Float, default=0.0)
    offer_acceptance_rate = Column(Float, default=0.0)

    # Quality Metrics
    avg_match_score = Column(Float, default=0.0)  # Average match score received
    avg_interview_rating = Column(Float, default=0.0)  # Average interview feedback
    profile_completeness = Column(Float, default=0.0)  # % of profile filled out

    # Activity Metrics
    last_application_date = Column(DateTime, nullable=True)
    last_login_date = Column(DateTime, nullable=True)
    profile_views = Column(Integer, default=0)  # How many companies viewed profile

    # AI Interaction Metrics
    total_ai_conversations = Column(Integer, default=0)
    avg_ai_conversation_quality = Column(Float, default=0.0)

    # Job Search Metrics (JSON: preferred industries, roles, locations)
    search_patterns = Column(JSON, nullable=True)

    # Skills Gap Analysis (JSON: {skill: {has: bool, needed_for: [job_ids]}})
    skills_analysis = Column(JSON, nullable=True)

    # Timestamps
    last_calculated = Column(DateTime, default=datetime.utcnow)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    user = relationship("User", foreign_keys=[user_id])

    def __repr__(self):
        return f"<CandidateAnalytics user_id={self.user_id}>"

    def calculate_rates(self):
        """Calculate conversion rates."""
        if self.total_applications > 0:
            self.application_to_interview_rate = (self.total_interviews / self.total_applications) * 100

        if self.total_interviews > 0:
            self.interview_to_offer_rate = (self.total_offers / self.total_interviews) * 100

        if self.total_offers > 0:
            accepted_offers = self.total_hires
            self.offer_acceptance_rate = (accepted_offers / self.total_offers) * 100

    def to_dict(self) -> Dict:
        """Convert to dictionary."""
        return {
            "user_id": self.user_id,
            "applications": {
                "total": self.total_applications,
                "this_month": self.applications_this_month,
                "active": self.active_applications,
            },
            "success_metrics": {
                "interviews": self.total_interviews,
                "offers": self.total_offers,
                "hires": self.total_hires,
                "rejections": self.total_rejections,
            },
            "conversion_rates": {
                "application_to_interview": round(self.application_to_interview_rate, 2),
                "interview_to_offer": round(self.interview_to_offer_rate, 2),
                "offer_acceptance": round(self.offer_acceptance_rate, 2),
            },
            "quality": {
                "avg_match_score": round(self.avg_match_score, 2),
                "avg_interview_rating": round(self.avg_interview_rating, 2),
                "profile_completeness": round(self.profile_completeness, 2),
            },
            "activity": {
                "profile_views": self.profile_views,
                "last_application": self.last_application_date.isoformat() if self.last_application_date else None,
                "last_login": self.last_login_date.isoformat() if self.last_login_date else None,
            },
            "ai_metrics": {
                "total_conversations": self.total_ai_conversations,
                "avg_conversation_quality": round(self.avg_ai_conversation_quality, 2),
            },
            "search_patterns": self.search_patterns,
            "skills_analysis": self.skills_analysis,
            "last_calculated": self.last_calculated.isoformat(),
        }


class AIPerformanceMetrics(Base):
    """
    AI system performance metrics.

    Tracks effectiveness of AI matching, screening, and recommendations.
    """
    __tablename__ = "ai_performance_metrics"
    __table_args__ = {'extend_existing': True}

    # Primary Key
    id = Column(Integer, primary_key=True, index=True)

    # Time Period
    period_start = Column(Date, nullable=False, index=True)
    period_end = Column(Date, nullable=False, index=True)
    period_type = Column(String(20), nullable=False)  # daily, weekly, monthly

    # Matching Performance
    total_matches_created = Column(Integer, default=0)
    matches_viewed = Column(Integer, default=0)
    matches_applied = Column(Integer, default=0)
    matches_interviewed = Column(Integer, default=0)
    matches_hired = Column(Integer, default=0)

    # Matching Accuracy Rates
    match_to_view_rate = Column(Float, default=0.0)  # % of matches that were viewed
    match_to_application_rate = Column(Float, default=0.0)  # % that led to applications
    match_to_interview_rate = Column(Float, default=0.0)  # % that led to interviews
    match_to_hire_rate = Column(Float, default=0.0)  # % that led to hires

    # Screening Performance
    total_ai_screens = Column(Integer, default=0)
    ai_screens_passed = Column(Integer, default=0)
    ai_screens_failed = Column(Integer, default=0)
    ai_screen_accuracy = Column(Float, default=0.0)  # % that matched human decision

    # RAG System Performance
    total_rag_queries = Column(Integer, default=0)
    avg_rag_response_time = Column(Float, default=0.0)  # milliseconds
    rag_quality_score = Column(Float, default=0.0)  # User satisfaction (0-10)

    # Agent Conversation Performance
    total_agent_conversations = Column(Integer, default=0)
    avg_conversation_length = Column(Float, default=0.0)  # Number of messages
    avg_conversation_rating = Column(Float, default=0.0)  # User rating (0-5)
    conversation_completion_rate = Column(Float, default=0.0)  # % completed vs abandoned

    # Model Performance
    avg_match_score_accuracy = Column(Float, default=0.0)  # How accurate are match scores
    false_positive_rate = Column(Float, default=0.0)  # High scores that led nowhere
    false_negative_rate = Column(Float, default=0.0)  # Low scores that should have been high

    # Timestamps
    calculated_at = Column(DateTime, default=datetime.utcnow)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    def __repr__(self):
        return f"<AIPerformanceMetrics {self.period_start} - {self.period_end}>"

    def calculate_rates(self):
        """Calculate performance rates."""
        if self.total_matches_created > 0:
            self.match_to_view_rate = (self.matches_viewed / self.total_matches_created) * 100
            self.match_to_application_rate = (self.matches_applied / self.total_matches_created) * 100
            self.match_to_interview_rate = (self.matches_interviewed / self.total_matches_created) * 100
            self.match_to_hire_rate = (self.matches_hired / self.total_matches_created) * 100

        if self.total_ai_screens > 0:
            self.ai_screen_accuracy = (self.ai_screens_passed / self.total_ai_screens) * 100

    def to_dict(self) -> Dict:
        """Convert to dictionary."""
        return {
            "period": {
                "start": self.period_start.isoformat(),
                "end": self.period_end.isoformat(),
                "type": self.period_type,
            },
            "matching": {
                "total_matches_created": self.total_matches_created,
                "matches_viewed": self.matches_viewed,
                "matches_applied": self.matches_applied,
                "matches_interviewed": self.matches_interviewed,
                "matches_hired": self.matches_hired,
                "match_to_view_rate": round(self.match_to_view_rate, 2),
                "match_to_application_rate": round(self.match_to_application_rate, 2),
                "match_to_interview_rate": round(self.match_to_interview_rate, 2),
                "match_to_hire_rate": round(self.match_to_hire_rate, 2),
            },
            "screening": {
                "total_screens": self.total_ai_screens,
                "passed": self.ai_screens_passed,
                "failed": self.ai_screens_failed,
                "accuracy": round(self.ai_screen_accuracy, 2),
            },
            "rag": {
                "total_queries": self.total_rag_queries,
                "avg_response_time_ms": round(self.avg_rag_response_time, 2),
                "quality_score": round(self.rag_quality_score, 2),
            },
            "conversations": {
                "total": self.total_agent_conversations,
                "avg_length": round(self.avg_conversation_length, 1),
                "avg_rating": round(self.avg_conversation_rating, 2),
                "completion_rate": round(self.conversation_completion_rate, 2),
            },
            "model_performance": {
                "match_score_accuracy": round(self.avg_match_score_accuracy, 2),
                "false_positive_rate": round(self.false_positive_rate, 2),
                "false_negative_rate": round(self.false_negative_rate, 2),
            },
            "calculated_at": self.calculated_at.isoformat(),
        }
