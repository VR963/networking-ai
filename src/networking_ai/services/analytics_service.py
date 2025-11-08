"""
Analytics Service - Phase 5.

Calculates hiring metrics, KPIs, and performance data for companies and candidates.
"""

from datetime import datetime, timedelta, date
from typing import List, Dict, Optional, Tuple
from sqlalchemy.orm import Session
from sqlalchemy import and_, or_, func, case

from ..models.analytics import (
    HiringMetrics,
    JobAnalytics,
    CandidateAnalytics,
    AIPerformanceMetrics
)
from ..models.application import Application, ApplicationStatus
from ..models.job import Job, JobStatus
from ..models.interview import Interview, InterviewStatus
from ..models.job_offer import JobOffer, OfferStatus
from ..models.match import Match, MatchStatus
from ..models.user import User


class AnalyticsService:
    """
    Service for calculating and retrieving analytics data.

    Provides methods to calculate metrics across different dimensions.
    """

    def __init__(self):
        """Initialize analytics service."""
        pass

    # ==================== Hiring Metrics Calculation ====================

    def calculate_hiring_metrics(
        self,
        company_id: int,
        start_date: date,
        end_date: date,
        period_type: str = "monthly",
        db: Session = None
    ) -> HiringMetrics:
        """
        Calculate comprehensive hiring metrics for a company.

        Args:
            company_id: Company ID
            start_date: Start of period
            end_date: End of period
            period_type: Type of period (daily, weekly, monthly, quarterly, yearly)
            db: Database session

        Returns:
            HiringMetrics object
        """
        # Check if metrics already exist
        existing = db.query(HiringMetrics).filter(
            and_(
                HiringMetrics.company_id == company_id,
                HiringMetrics.period_start == start_date,
                HiringMetrics.period_end == end_date
            )
        ).first()

        if existing:
            # Update existing metrics
            metrics = existing
        else:
            # Create new metrics
            metrics = HiringMetrics(
                company_id=company_id,
                period_start=start_date,
                period_end=end_date,
                period_type=period_type
            )

        # Calculate volume metrics
        volume = self._calculate_volume_metrics(company_id, start_date, end_date, db)
        metrics.total_jobs_posted = volume["jobs_posted"]
        metrics.total_applications = volume["applications"]
        metrics.total_interviews = volume["interviews"]
        metrics.total_offers = volume["offers"]
        metrics.total_hires = volume["hires"]

        # Calculate conversion rates
        if metrics.total_applications > 0:
            metrics.application_to_interview_rate = (metrics.total_interviews / metrics.total_applications) * 100

        if metrics.total_interviews > 0:
            metrics.interview_to_offer_rate = (metrics.total_offers / metrics.total_interviews) * 100

        if metrics.total_offers > 0:
            metrics.offer_acceptance_rate = (metrics.total_hires / metrics.total_offers) * 100

        # Calculate time metrics
        time_metrics = self._calculate_time_metrics(company_id, start_date, end_date, db)
        metrics.avg_time_to_hire = time_metrics["time_to_hire"]
        metrics.avg_time_to_interview = time_metrics["time_to_interview"]
        metrics.avg_time_to_offer = time_metrics["time_to_offer"]

        # Calculate quality metrics
        quality = self._calculate_quality_metrics(company_id, start_date, end_date, db)
        metrics.avg_candidate_quality_score = quality["candidate_quality"]
        metrics.avg_interview_rating = quality["interview_rating"]

        # Calculate source effectiveness
        metrics.source_metrics = self._calculate_source_metrics(company_id, start_date, end_date, db)

        # Calculate AI performance
        ai_perf = self._calculate_ai_performance(company_id, start_date, end_date, db)
        metrics.ai_match_accuracy = ai_perf["match_accuracy"]
        metrics.ai_screening_accuracy = ai_perf["screening_accuracy"]

        metrics.calculated_at = datetime.utcnow()

        if not existing:
            db.add(metrics)
        db.commit()
        db.refresh(metrics)

        return metrics

    def _calculate_volume_metrics(
        self,
        company_id: int,
        start_date: date,
        end_date: date,
        db: Session
    ) -> Dict:
        """Calculate volume metrics (counts)."""
        # Jobs posted in period
        jobs_posted = db.query(func.count(Job.id)).filter(
            and_(
                Job.company_id == company_id,
                func.date(Job.created_at) >= start_date,
                func.date(Job.created_at) <= end_date
            )
        ).scalar() or 0

        # Applications received
        applications = db.query(func.count(Application.id)).join(
            Job, Application.job_id == Job.id
        ).filter(
            and_(
                Job.company_id == company_id,
                func.date(Application.created_at) >= start_date,
                func.date(Application.created_at) <= end_date
            )
        ).scalar() or 0

        # Interviews conducted
        interviews = db.query(func.count(Interview.id)).filter(
            and_(
                Interview.company_id == company_id,
                func.date(Interview.scheduled_at) >= start_date,
                func.date(Interview.scheduled_at) <= end_date,
                Interview.status.in_([InterviewStatus.COMPLETED, InterviewStatus.IN_PROGRESS])
            )
        ).scalar() or 0

        # Offers extended
        offers = db.query(func.count(JobOffer.id)).filter(
            and_(
                JobOffer.company_id == company_id,
                func.date(JobOffer.sent_at) >= start_date,
                func.date(JobOffer.sent_at) <= end_date,
                JobOffer.status != OfferStatus.DRAFT
            )
        ).scalar() or 0

        # Hires (accepted offers)
        hires = db.query(func.count(JobOffer.id)).filter(
            and_(
                JobOffer.company_id == company_id,
                func.date(JobOffer.accepted_at) >= start_date,
                func.date(JobOffer.accepted_at) <= end_date,
                JobOffer.status == OfferStatus.ACCEPTED
            )
        ).scalar() or 0

        return {
            "jobs_posted": jobs_posted,
            "applications": applications,
            "interviews": interviews,
            "offers": offers,
            "hires": hires
        }

    def _calculate_time_metrics(
        self,
        company_id: int,
        start_date: date,
        end_date: date,
        db: Session
    ) -> Dict:
        """Calculate time-based metrics."""
        # Time to hire (application to accepted offer)
        hires = db.query(
            JobOffer.accepted_at,
            Application.created_at
        ).join(
            Application, JobOffer.application_id == Application.id
        ).filter(
            and_(
                JobOffer.company_id == company_id,
                func.date(JobOffer.accepted_at) >= start_date,
                func.date(JobOffer.accepted_at) <= end_date,
                JobOffer.status == OfferStatus.ACCEPTED
            )
        ).all()

        time_to_hire_days = []
        for accepted_at, created_at in hires:
            if accepted_at and created_at:
                days = (accepted_at - created_at).days
                time_to_hire_days.append(days)

        avg_time_to_hire = sum(time_to_hire_days) / len(time_to_hire_days) if time_to_hire_days else 0.0

        # Time to interview (application to first interview)
        interviews = db.query(
            Interview.scheduled_at,
            Application.created_at
        ).join(
            Application, Interview.application_id == Application.id
        ).filter(
            and_(
                Interview.company_id == company_id,
                func.date(Interview.scheduled_at) >= start_date,
                func.date(Interview.scheduled_at) <= end_date
            )
        ).all()

        time_to_interview_days = []
        for scheduled_at, created_at in interviews:
            if scheduled_at and created_at:
                days = (scheduled_at - created_at).days
                time_to_interview_days.append(days)

        avg_time_to_interview = sum(time_to_interview_days) / len(time_to_interview_days) if time_to_interview_days else 0.0

        # Time to offer (application to offer sent)
        offers = db.query(
            JobOffer.sent_at,
            Application.created_at
        ).join(
            Application, JobOffer.application_id == Application.id
        ).filter(
            and_(
                JobOffer.company_id == company_id,
                func.date(JobOffer.sent_at) >= start_date,
                func.date(JobOffer.sent_at) <= end_date,
                JobOffer.status != OfferStatus.DRAFT
            )
        ).all()

        time_to_offer_days = []
        for sent_at, created_at in offers:
            if sent_at and created_at:
                days = (sent_at - created_at).days
                time_to_offer_days.append(days)

        avg_time_to_offer = sum(time_to_offer_days) / len(time_to_offer_days) if time_to_offer_days else 0.0

        return {
            "time_to_hire": round(avg_time_to_hire, 1),
            "time_to_interview": round(avg_time_to_interview, 1),
            "time_to_offer": round(avg_time_to_offer, 1)
        }

    def _calculate_quality_metrics(
        self,
        company_id: int,
        start_date: date,
        end_date: date,
        db: Session
    ) -> Dict:
        """Calculate quality metrics."""
        # Average match score
        avg_match_score = db.query(
            func.avg(Match.match_score)
        ).join(
            Job, Match.job_id == Job.id
        ).filter(
            and_(
                Job.company_id == company_id,
                func.date(Match.created_at) >= start_date,
                func.date(Match.created_at) <= end_date
            )
        ).scalar() or 0.0

        # Convert to 0-100 scale
        candidate_quality = avg_match_score * 100

        # Average interview rating (from InterviewFeedback)
        from ..models.interview import InterviewFeedback, FeedbackRating

        # Map ratings to numeric values
        rating_map = {
            FeedbackRating.STRONG_YES: 5,
            FeedbackRating.YES: 4,
            FeedbackRating.MAYBE: 3,
            FeedbackRating.NO: 2,
            FeedbackRating.STRONG_NO: 1
        }

        feedbacks = db.query(InterviewFeedback.overall_rating).join(
            Interview, InterviewFeedback.interview_id == Interview.id
        ).filter(
            and_(
                Interview.company_id == company_id,
                func.date(InterviewFeedback.created_at) >= start_date,
                func.date(InterviewFeedback.created_at) <= end_date
            )
        ).all()

        if feedbacks:
            rating_values = [rating_map.get(f[0], 3) for f in feedbacks]
            avg_interview_rating = sum(rating_values) / len(rating_values)
        else:
            avg_interview_rating = 0.0

        return {
            "candidate_quality": round(candidate_quality, 2),
            "interview_rating": round(avg_interview_rating, 2)
        }

    def _calculate_source_metrics(
        self,
        company_id: int,
        start_date: date,
        end_date: date,
        db: Session
    ) -> Dict:
        """Calculate source effectiveness metrics."""
        # This would track where applications came from
        # For now, return placeholder
        return {
            "direct": {"applications": 0, "hires": 0, "conversion_rate": 0.0},
            "referral": {"applications": 0, "hires": 0, "conversion_rate": 0.0},
            "job_board": {"applications": 0, "hires": 0, "conversion_rate": 0.0},
        }

    def _calculate_ai_performance(
        self,
        company_id: int,
        start_date: date,
        end_date: date,
        db: Session
    ) -> Dict:
        """Calculate AI performance metrics."""
        # Matches that led to applications (match accuracy)
        total_matches = db.query(func.count(Match.id)).join(
            Job, Match.job_id == Job.id
        ).filter(
            and_(
                Job.company_id == company_id,
                func.date(Match.created_at) >= start_date,
                func.date(Match.created_at) <= end_date
            )
        ).scalar() or 0

        matches_with_applications = db.query(func.count(Match.id)).join(
            Job, Match.job_id == Job.id
        ).filter(
            and_(
                Job.company_id == company_id,
                func.date(Match.created_at) >= start_date,
                func.date(Match.created_at) <= end_date,
                Match.status == MatchStatus.APPLIED
            )
        ).scalar() or 0

        match_accuracy = (matches_with_applications / total_matches * 100) if total_matches > 0 else 0.0

        # AI screening accuracy (applications that passed screening)
        total_ai_screens = db.query(func.count(Application.id)).join(
            Job, Application.job_id == Job.id
        ).filter(
            and_(
                Job.company_id == company_id,
                func.date(Application.created_at) >= start_date,
                func.date(Application.created_at) <= end_date,
                Application.status.in_([ApplicationStatus.AI_SCREENING, ApplicationStatus.SCREENED_PASS, ApplicationStatus.SCREENED_FAIL])
            )
        ).scalar() or 0

        screens_passed = db.query(func.count(Application.id)).join(
            Job, Application.job_id == Job.id
        ).filter(
            and_(
                Job.company_id == company_id,
                func.date(Application.created_at) >= start_date,
                func.date(Application.created_at) <= end_date,
                Application.status == ApplicationStatus.SCREENED_PASS
            )
        ).scalar() or 0

        screening_accuracy = (screens_passed / total_ai_screens * 100) if total_ai_screens > 0 else 0.0

        return {
            "match_accuracy": round(match_accuracy, 2),
            "screening_accuracy": round(screening_accuracy, 2)
        }

    # ==================== Job Analytics ====================

    def calculate_job_analytics(
        self,
        job_id: int,
        db: Session
    ) -> JobAnalytics:
        """
        Calculate analytics for a specific job.

        Args:
            job_id: Job ID
            db: Database session

        Returns:
            JobAnalytics object
        """
        # Get or create analytics
        analytics = db.query(JobAnalytics).filter(
            JobAnalytics.job_id == job_id
        ).first()

        if not analytics:
            job = db.query(Job).filter(Job.id == job_id).first()
            if not job:
                raise ValueError("Job not found")

            analytics = JobAnalytics(
                job_id=job_id,
                company_id=job.company_id
            )

        # Update status
        job = db.query(Job).filter(Job.id == job_id).first()
        analytics.is_active = 1 if job.status == JobStatus.ACTIVE else 0
        if job.created_at:
            analytics.days_open = (datetime.utcnow() - job.created_at).days

        # Count applications by status
        application_counts = db.query(
            Application.status,
            func.count(Application.id)
        ).filter(
            Application.job_id == job_id
        ).group_by(Application.status).all()

        status_map = {status: count for status, count in application_counts}

        analytics.total_applications = sum(status_map.values())
        analytics.applications_in_review = status_map.get(ApplicationStatus.REVIEWING, 0) + status_map.get(ApplicationStatus.PENDING, 0)
        analytics.applications_screening = status_map.get(ApplicationStatus.AI_SCREENING, 0)
        analytics.applications_interviewing = status_map.get(ApplicationStatus.INTERVIEW_SCHEDULED, 0) + status_map.get(ApplicationStatus.INTERVIEW_COMPLETED, 0)
        analytics.applications_offered = status_map.get(ApplicationStatus.OFFER_EXTENDED, 0)
        analytics.applications_hired = status_map.get(ApplicationStatus.OFFER_ACCEPTED, 0)
        analytics.applications_rejected = status_map.get(ApplicationStatus.REJECTED, 0)

        # Calculate conversion rates
        analytics.calculate_conversion_rates()

        # Update view count from job model
        analytics.total_views = job.total_views

        # Calculate average match score
        avg_match = db.query(func.avg(Match.match_score)).filter(
            Match.job_id == job_id
        ).scalar() or 0.0
        analytics.avg_candidate_match_score = avg_match

        analytics.last_calculated = datetime.utcnow()

        if not db.query(JobAnalytics).filter(JobAnalytics.job_id == job_id).first():
            db.add(analytics)
        db.commit()
        db.refresh(analytics)

        return analytics

    # ==================== Candidate Analytics ====================

    def calculate_candidate_analytics(
        self,
        user_id: int,
        db: Session
    ) -> CandidateAnalytics:
        """
        Calculate analytics for a candidate.

        Args:
            user_id: User ID (candidate)
            db: Database session

        Returns:
            CandidateAnalytics object
        """
        # Get or create analytics
        analytics = db.query(CandidateAnalytics).filter(
            CandidateAnalytics.user_id == user_id
        ).first()

        if not analytics:
            analytics = CandidateAnalytics(user_id=user_id)

        # Count applications
        analytics.total_applications = db.query(func.count(Application.id)).filter(
            Application.talent_user_id == user_id
        ).scalar() or 0

        # Applications this month
        month_start = datetime.utcnow().replace(day=1)
        analytics.applications_this_month = db.query(func.count(Application.id)).filter(
            and_(
                Application.talent_user_id == user_id,
                Application.created_at >= month_start
            )
        ).scalar() or 0

        # Active applications
        analytics.active_applications = db.query(func.count(Application.id)).filter(
            and_(
                Application.talent_user_id == user_id,
                Application.status.in_([
                    ApplicationStatus.PENDING,
                    ApplicationStatus.REVIEWING,
                    ApplicationStatus.AI_SCREENING,
                    ApplicationStatus.SCREENED_PASS,
                    ApplicationStatus.INTERVIEW_SCHEDULED,
                    ApplicationStatus.INTERVIEW_COMPLETED,
                    ApplicationStatus.OFFER_EXTENDED
                ])
            )
        ).scalar() or 0

        # Success metrics
        analytics.total_interviews = db.query(func.count(Interview.id)).filter(
            Interview.candidate_user_id == user_id
        ).scalar() or 0

        analytics.total_offers = db.query(func.count(JobOffer.id)).filter(
            JobOffer.candidate_user_id == user_id
        ).scalar() or 0

        analytics.total_hires = db.query(func.count(JobOffer.id)).filter(
            and_(
                JobOffer.candidate_user_id == user_id,
                JobOffer.status == OfferStatus.ACCEPTED
            )
        ).scalar() or 0

        analytics.total_rejections = db.query(func.count(Application.id)).filter(
            and_(
                Application.talent_user_id == user_id,
                Application.status == ApplicationStatus.REJECTED
            )
        ).scalar() or 0

        # Calculate rates
        analytics.calculate_rates()

        # Average match score
        avg_match = db.query(func.avg(Match.match_score)).filter(
            Match.talent_user_id == user_id
        ).scalar() or 0.0
        analytics.avg_match_score = avg_match

        # Last application date
        last_app = db.query(Application.created_at).filter(
            Application.talent_user_id == user_id
        ).order_by(Application.created_at.desc()).first()
        analytics.last_application_date = last_app[0] if last_app else None

        analytics.last_calculated = datetime.utcnow()

        if not db.query(CandidateAnalytics).filter(CandidateAnalytics.user_id == user_id).first():
            db.add(analytics)
        db.commit()
        db.refresh(analytics)

        return analytics

    # ==================== Dashboard Data ====================

    def get_company_dashboard(
        self,
        company_id: int,
        db: Session
    ) -> Dict:
        """
        Get comprehensive dashboard data for a company.

        Args:
            company_id: Company ID
            db: Database session

        Returns:
            Dictionary with dashboard data
        """
        # Get current month metrics
        today = date.today()
        month_start = today.replace(day=1)
        month_end = today

        current_metrics = self.calculate_hiring_metrics(
            company_id=company_id,
            start_date=month_start,
            end_date=month_end,
            period_type="monthly",
            db=db
        )

        # Get active jobs with analytics
        active_jobs = db.query(Job).filter(
            and_(
                Job.company_id == company_id,
                Job.status == JobStatus.ACTIVE
            )
        ).all()

        job_analytics_list = []
        for job in active_jobs:
            analytics = self.calculate_job_analytics(job.id, db)
            job_analytics_list.append({
                "job_id": job.id,
                "job_title": job.title,
                "analytics": analytics.to_dict()
            })

        # Recent activity (last 30 days)
        thirty_days_ago = datetime.utcnow() - timedelta(days=30)

        recent_applications = db.query(func.count(Application.id)).join(
            Job, Application.job_id == Job.id
        ).filter(
            and_(
                Job.company_id == company_id,
                Application.created_at >= thirty_days_ago
            )
        ).scalar() or 0

        recent_interviews = db.query(func.count(Interview.id)).filter(
            and_(
                Interview.company_id == company_id,
                Interview.scheduled_at >= thirty_days_ago
            )
        ).scalar() or 0

        recent_offers = db.query(func.count(JobOffer.id)).filter(
            and_(
                JobOffer.company_id == company_id,
                JobOffer.sent_at >= thirty_days_ago
            )
        ).scalar() or 0

        return {
            "current_month_metrics": current_metrics.to_dict(),
            "active_jobs": {
                "count": len(active_jobs),
                "details": job_analytics_list
            },
            "recent_activity": {
                "applications_30d": recent_applications,
                "interviews_30d": recent_interviews,
                "offers_30d": recent_offers
            },
            "generated_at": datetime.utcnow().isoformat()
        }

    def get_candidate_dashboard(
        self,
        user_id: int,
        db: Session
    ) -> Dict:
        """
        Get dashboard data for a candidate.

        Args:
            user_id: User ID (candidate)
            db: Database session

        Returns:
            Dictionary with dashboard data
        """
        analytics = self.calculate_candidate_analytics(user_id, db)

        # Get active applications with details
        active_apps = db.query(Application).filter(
            and_(
                Application.talent_user_id == user_id,
                Application.status.in_([
                    ApplicationStatus.PENDING,
                    ApplicationStatus.REVIEWING,
                    ApplicationStatus.INTERVIEW_SCHEDULED,
                    ApplicationStatus.OFFER_EXTENDED
                ])
            )
        ).all()

        active_app_details = []
        for app in active_apps:
            job = db.query(Job).filter(Job.id == app.job_id).first()
            active_app_details.append({
                "application_id": app.id,
                "job_title": job.title if job else "Unknown",
                "company": job.company.company_name if job and job.company else "Unknown",
                "status": app.status.value,
                "applied_at": app.created_at.isoformat()
            })

        # Upcoming interviews
        upcoming_interviews = db.query(Interview).filter(
            and_(
                Interview.candidate_user_id == user_id,
                Interview.scheduled_at >= datetime.utcnow(),
                Interview.status.in_([InterviewStatus.SCHEDULED, InterviewStatus.CONFIRMED])
            )
        ).order_by(Interview.scheduled_at).limit(5).all()

        interview_details = []
        for interview in upcoming_interviews:
            job = db.query(Job).filter(Job.id == interview.job_id).first()
            interview_details.append({
                "interview_id": interview.id,
                "job_title": job.title if job else "Unknown",
                "scheduled_at": interview.scheduled_at.isoformat(),
                "stage": interview.stage.value,
                "format": interview.format.value
            })

        return {
            "analytics": analytics.to_dict(),
            "active_applications": {
                "count": len(active_apps),
                "details": active_app_details
            },
            "upcoming_interviews": {
                "count": len(upcoming_interviews),
                "details": interview_details
            },
            "generated_at": datetime.utcnow().isoformat()
        }


# ==================== Factory Function ====================

def create_analytics_service() -> AnalyticsService:
    """
    Factory function to create AnalyticsService.

    Returns:
        AnalyticsService instance
    """
    return AnalyticsService()
