"""
Analytics API Endpoints - Phase 5.

REST API for analytics, metrics, and reporting.
"""

from typing import Optional
from datetime import date, datetime, timedelta
from fastapi import APIRouter, Depends, HTTPException, status, Response
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session
from pydantic import BaseModel
import io
import csv

from ..database import get_db
from ..models.analytics import (
    HiringMetrics,
    JobAnalytics,
    CandidateAnalytics,
    AIPerformanceMetrics
)
from ..services.analytics_service import (
    AnalyticsService,
    create_analytics_service
)


# ==================== Request/Response Models ====================

class MetricsPeriodRequest(BaseModel):
    """Request for metrics within a period."""
    start_date: date
    end_date: date
    period_type: str = "monthly"  # daily, weekly, monthly, quarterly, yearly


class HiringMetricsResponse(BaseModel):
    """Hiring metrics response."""
    id: int
    company_id: int
    period_start: date
    period_end: date
    period_type: str
    total_jobs_posted: int
    total_applications: int
    total_interviews: int
    total_offers: int
    total_hires: int
    application_to_interview_rate: float
    interview_to_offer_rate: float
    offer_acceptance_rate: float
    avg_time_to_hire: float
    avg_time_to_interview: float
    avg_time_to_offer: float
    calculated_at: datetime

    class Config:
        from_attributes = True


class JobAnalyticsResponse(BaseModel):
    """Job analytics response."""
    job_id: int
    company_id: int
    is_active: bool
    days_open: int
    total_applications: int
    applications_in_review: int
    applications_interviewing: int
    applications_offered: int
    applications_hired: int
    application_to_interview_rate: float
    interview_to_offer_rate: float
    last_calculated: datetime

    class Config:
        from_attributes = True


class CandidateAnalyticsResponse(BaseModel):
    """Candidate analytics response."""
    user_id: int
    total_applications: int
    applications_this_month: int
    active_applications: int
    total_interviews: int
    total_offers: int
    total_hires: int
    application_to_interview_rate: float
    interview_to_offer_rate: float
    avg_match_score: float
    last_calculated: datetime

    class Config:
        from_attributes = True


# ==================== Router Setup ====================

router = APIRouter(prefix="/api/analytics", tags=["analytics"])


# ==================== Helper Functions ====================

def get_analytics_service() -> AnalyticsService:
    """Get analytics service instance."""
    return create_analytics_service()


# ==================== Company Analytics Endpoints ====================

@router.get("/company/{company_id}/dashboard")
def get_company_dashboard(
    company_id: int,
    db: Session = Depends(get_db),
    service: AnalyticsService = Depends(get_analytics_service)
):
    """
    Get comprehensive company dashboard data.

    Returns current month metrics, active jobs, and recent activity.
    """
    dashboard = service.get_company_dashboard(company_id=company_id, db=db)
    return dashboard


@router.post("/company/{company_id}/metrics", response_model=HiringMetricsResponse)
def calculate_company_metrics(
    company_id: int,
    request: MetricsPeriodRequest,
    db: Session = Depends(get_db),
    service: AnalyticsService = Depends(get_analytics_service)
):
    """
    Calculate hiring metrics for a company within a period.

    Calculates comprehensive hiring metrics including:
    - Volume metrics (applications, interviews, offers, hires)
    - Conversion rates (application→interview→offer→hire)
    - Time metrics (time-to-hire, time-to-interview, time-to-offer)
    - Quality metrics (candidate quality scores, interview ratings)
    - AI performance (match accuracy, screening effectiveness)
    """
    metrics = service.calculate_hiring_metrics(
        company_id=company_id,
        start_date=request.start_date,
        end_date=request.end_date,
        period_type=request.period_type,
        db=db
    )
    return metrics


@router.get("/company/{company_id}/metrics/current-month", response_model=HiringMetricsResponse)
def get_current_month_metrics(
    company_id: int,
    db: Session = Depends(get_db),
    service: AnalyticsService = Depends(get_analytics_service)
):
    """
    Get hiring metrics for the current month.

    Convenience endpoint that calculates metrics from the start of the current month to today.
    """
    today = date.today()
    month_start = today.replace(day=1)

    metrics = service.calculate_hiring_metrics(
        company_id=company_id,
        start_date=month_start,
        end_date=today,
        period_type="monthly",
        db=db
    )
    return metrics


@router.get("/company/{company_id}/metrics/year-to-date", response_model=HiringMetricsResponse)
def get_year_to_date_metrics(
    company_id: int,
    db: Session = Depends(get_db),
    service: AnalyticsService = Depends(get_analytics_service)
):
    """
    Get hiring metrics for year-to-date.

    Calculates metrics from January 1st of current year to today.
    """
    today = date.today()
    year_start = today.replace(month=1, day=1)

    metrics = service.calculate_hiring_metrics(
        company_id=company_id,
        start_date=year_start,
        end_date=today,
        period_type="yearly",
        db=db
    )
    return metrics


@router.get("/company/{company_id}/trends")
def get_hiring_trends(
    company_id: int,
    months: int = 12,
    db: Session = Depends(get_db),
    service: AnalyticsService = Depends(get_analytics_service)
):
    """
    Get hiring trends over time.

    Returns monthly metrics for the specified number of months to show trends.
    """
    trends = []
    today = date.today()

    for i in range(months):
        # Calculate month start and end
        if i == 0:
            # Current month
            month_start = today.replace(day=1)
            month_end = today
        else:
            # Previous months
            month_date = today.replace(day=1) - timedelta(days=i * 30)
            month_start = month_date.replace(day=1)
            # Last day of that month
            if month_start.month == 12:
                month_end = month_start.replace(year=month_start.year + 1, month=1, day=1) - timedelta(days=1)
            else:
                month_end = month_start.replace(month=month_start.month + 1, day=1) - timedelta(days=1)

        metrics = service.calculate_hiring_metrics(
            company_id=company_id,
            start_date=month_start,
            end_date=month_end,
            period_type="monthly",
            db=db
        )

        trends.append({
            "month": month_start.strftime("%Y-%m"),
            "metrics": metrics.to_dict()
        })

    return {
        "company_id": company_id,
        "period_months": months,
        "trends": list(reversed(trends))  # Oldest to newest
    }


# ==================== Job Analytics Endpoints ====================

@router.get("/jobs/{job_id}", response_model=JobAnalyticsResponse)
def get_job_analytics(
    job_id: int,
    db: Session = Depends(get_db),
    service: AnalyticsService = Depends(get_analytics_service)
):
    """
    Get analytics for a specific job.

    Returns comprehensive metrics for a job posting including:
    - Application counts and pipeline status
    - Conversion rates throughout the funnel
    - Time metrics
    - Quality scores
    """
    try:
        analytics = service.calculate_job_analytics(job_id=job_id, db=db)
        return analytics
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e)
        )


@router.get("/company/{company_id}/jobs")
def get_all_jobs_analytics(
    company_id: int,
    active_only: bool = False,
    db: Session = Depends(get_db),
    service: AnalyticsService = Depends(get_analytics_service)
):
    """
    Get analytics for all jobs of a company.

    Returns analytics for each job, optionally filtered to active jobs only.
    """
    from ..models.job import Job, JobStatus

    query = db.query(Job).filter(Job.company_id == company_id)

    if active_only:
        query = query.filter(Job.status == JobStatus.ACTIVE)

    jobs = query.all()

    job_analytics_list = []
    for job in jobs:
        try:
            analytics = service.calculate_job_analytics(job.id, db)
            job_analytics_list.append({
                "job_id": job.id,
                "job_title": job.title,
                "status": job.status.value,
                "analytics": analytics.to_dict()
            })
        except Exception as e:
            # Skip jobs that error
            continue

    return {
        "company_id": company_id,
        "total_jobs": len(job_analytics_list),
        "jobs": job_analytics_list
    }


# ==================== Candidate Analytics Endpoints ====================

@router.get("/candidate/{user_id}", response_model=CandidateAnalyticsResponse)
def get_candidate_analytics(
    user_id: int,
    db: Session = Depends(get_db),
    service: AnalyticsService = Depends(get_analytics_service)
):
    """
    Get analytics for a candidate.

    Returns comprehensive metrics for a candidate's job search including:
    - Application counts and success rates
    - Conversion rates
    - Interview and offer statistics
    - Quality scores
    """
    analytics = service.calculate_candidate_analytics(user_id=user_id, db=db)
    return analytics


@router.get("/candidate/{user_id}/dashboard")
def get_candidate_dashboard(
    user_id: int,
    db: Session = Depends(get_db),
    service: AnalyticsService = Depends(get_analytics_service)
):
    """
    Get comprehensive candidate dashboard data.

    Returns analytics, active applications, and upcoming interviews.
    """
    dashboard = service.get_candidate_dashboard(user_id=user_id, db=db)
    return dashboard


# ==================== Funnel Analytics ====================

@router.get("/company/{company_id}/funnel")
def get_hiring_funnel(
    company_id: int,
    start_date: Optional[date] = None,
    end_date: Optional[date] = None,
    db: Session = Depends(get_db)
):
    """
    Get hiring funnel visualization data.

    Returns counts at each stage of the hiring funnel:
    Applications → Screening → Interviews → Offers → Hires

    Useful for visualizing conversion drop-off.
    """
    from ..models.job import Job
    from ..models.application import Application, ApplicationStatus
    from ..models.interview import Interview, InterviewStatus
    from ..models.job_offer import JobOffer, OfferStatus

    # Default to last 90 days if not specified
    if not end_date:
        end_date = date.today()
    if not start_date:
        start_date = end_date - timedelta(days=90)

    # Count at each stage
    total_applications = db.query(func.count(Application.id)).join(
        Job, Application.job_id == Job.id
    ).filter(
        and_(
            Job.company_id == company_id,
            func.date(Application.created_at) >= start_date,
            func.date(Application.created_at) <= end_date
        )
    ).scalar() or 0

    screening_passed = db.query(func.count(Application.id)).join(
        Job, Application.job_id == Job.id
    ).filter(
        and_(
            Job.company_id == company_id,
            func.date(Application.created_at) >= start_date,
            func.date(Application.created_at) <= end_date,
            Application.status.in_([
                ApplicationStatus.SCREENED_PASS,
                ApplicationStatus.REVIEWING,
                ApplicationStatus.INTERVIEW_SCHEDULED,
                ApplicationStatus.INTERVIEW_COMPLETED,
                ApplicationStatus.OFFER_EXTENDED,
                ApplicationStatus.OFFER_ACCEPTED
            ])
        )
    ).scalar() or 0

    interviewed = db.query(func.count(func.distinct(Interview.application_id))).filter(
        and_(
            Interview.company_id == company_id,
            func.date(Interview.scheduled_at) >= start_date,
            func.date(Interview.scheduled_at) <= end_date
        )
    ).scalar() or 0

    offered = db.query(func.count(JobOffer.id)).filter(
        and_(
            JobOffer.company_id == company_id,
            func.date(JobOffer.sent_at) >= start_date,
            func.date(JobOffer.sent_at) <= end_date,
            JobOffer.status != OfferStatus.DRAFT
        )
    ).scalar() or 0

    hired = db.query(func.count(JobOffer.id)).filter(
        and_(
            JobOffer.company_id == company_id,
            func.date(JobOffer.accepted_at) >= start_date,
            func.date(JobOffer.accepted_at) <= end_date,
            JobOffer.status == OfferStatus.ACCEPTED
        )
    ).scalar() or 0

    # Calculate conversion rates
    funnel_data = {
        "period": {
            "start": start_date.isoformat(),
            "end": end_date.isoformat()
        },
        "stages": [
            {
                "name": "Applications",
                "count": total_applications,
                "percentage": 100.0
            },
            {
                "name": "Screening Passed",
                "count": screening_passed,
                "percentage": (screening_passed / total_applications * 100) if total_applications > 0 else 0.0
            },
            {
                "name": "Interviewed",
                "count": interviewed,
                "percentage": (interviewed / total_applications * 100) if total_applications > 0 else 0.0
            },
            {
                "name": "Offered",
                "count": offered,
                "percentage": (offered / total_applications * 100) if total_applications > 0 else 0.0
            },
            {
                "name": "Hired",
                "count": hired,
                "percentage": (hired / total_applications * 100) if total_applications > 0 else 0.0
            }
        ],
        "conversion_rates": {
            "application_to_screening": (screening_passed / total_applications * 100) if total_applications > 0 else 0.0,
            "screening_to_interview": (interviewed / screening_passed * 100) if screening_passed > 0 else 0.0,
            "interview_to_offer": (offered / interviewed * 100) if interviewed > 0 else 0.0,
            "offer_to_hire": (hired / offered * 100) if offered > 0 else 0.0,
            "overall": (hired / total_applications * 100) if total_applications > 0 else 0.0
        }
    }

    return funnel_data


# ==================== Export Endpoints ====================

@router.get("/company/{company_id}/export/csv")
def export_metrics_csv(
    company_id: int,
    start_date: date,
    end_date: date,
    db: Session = Depends(get_db),
    service: AnalyticsService = Depends(get_analytics_service)
):
    """
    Export hiring metrics to CSV.

    Downloads a CSV file with hiring metrics for the specified period.
    """
    metrics = service.calculate_hiring_metrics(
        company_id=company_id,
        start_date=start_date,
        end_date=end_date,
        period_type="custom",
        db=db
    )

    # Create CSV in memory
    output = io.StringIO()
    writer = csv.writer(output)

    # Write headers
    writer.writerow([
        "Metric", "Value"
    ])

    # Write data
    writer.writerow(["Period Start", metrics.period_start.isoformat()])
    writer.writerow(["Period End", metrics.period_end.isoformat()])
    writer.writerow([""])
    writer.writerow(["VOLUME METRICS", ""])
    writer.writerow(["Total Jobs Posted", metrics.total_jobs_posted])
    writer.writerow(["Total Applications", metrics.total_applications])
    writer.writerow(["Total Interviews", metrics.total_interviews])
    writer.writerow(["Total Offers", metrics.total_offers])
    writer.writerow(["Total Hires", metrics.total_hires])
    writer.writerow([""])
    writer.writerow(["CONVERSION RATES", ""])
    writer.writerow(["Application to Interview Rate (%)", round(metrics.application_to_interview_rate, 2)])
    writer.writerow(["Interview to Offer Rate (%)", round(metrics.interview_to_offer_rate, 2)])
    writer.writerow(["Offer Acceptance Rate (%)", round(metrics.offer_acceptance_rate, 2)])
    writer.writerow([""])
    writer.writerow(["TIME METRICS (Days)", ""])
    writer.writerow(["Avg Time to Hire", round(metrics.avg_time_to_hire, 1)])
    writer.writerow(["Avg Time to Interview", round(metrics.avg_time_to_interview, 1)])
    writer.writerow(["Avg Time to Offer", round(metrics.avg_time_to_offer, 1)])
    writer.writerow([""])
    writer.writerow(["QUALITY METRICS", ""])
    writer.writerow(["Avg Candidate Quality Score", round(metrics.avg_candidate_quality_score, 2)])
    writer.writerow(["Avg Interview Rating", round(metrics.avg_interview_rating, 2)])
    writer.writerow([""])
    writer.writerow(["AI PERFORMANCE", ""])
    writer.writerow(["AI Match Accuracy (%)", round(metrics.ai_match_accuracy, 2)])
    writer.writerow(["AI Screening Accuracy (%)", round(metrics.ai_screening_accuracy, 2)])

    # Prepare response
    output.seek(0)
    filename = f"hiring_metrics_{company_id}_{start_date}_{end_date}.csv"

    return StreamingResponse(
        iter([output.getvalue()]),
        media_type="text/csv",
        headers={
            "Content-Disposition": f"attachment; filename={filename}"
        }
    )


# ==================== Comparison Endpoints ====================

@router.get("/company/{company_id}/compare")
def compare_periods(
    company_id: int,
    period1_start: date,
    period1_end: date,
    period2_start: date,
    period2_end: date,
    db: Session = Depends(get_db),
    service: AnalyticsService = Depends(get_analytics_service)
):
    """
    Compare metrics between two time periods.

    Useful for month-over-month or year-over-year comparisons.
    Shows changes and percentage differences.
    """
    period1_metrics = service.calculate_hiring_metrics(
        company_id=company_id,
        start_date=period1_start,
        end_date=period1_end,
        period_type="custom",
        db=db
    )

    period2_metrics = service.calculate_hiring_metrics(
        company_id=company_id,
        start_date=period2_start,
        end_date=period2_end,
        period_type="custom",
        db=db
    )

    def calc_change(old_val, new_val):
        """Calculate percentage change."""
        if old_val == 0:
            return 0.0 if new_val == 0 else 100.0
        return ((new_val - old_val) / old_val) * 100

    return {
        "period1": {
            "start": period1_start.isoformat(),
            "end": period1_end.isoformat(),
            "metrics": period1_metrics.to_dict()
        },
        "period2": {
            "start": period2_start.isoformat(),
            "end": period2_end.isoformat(),
            "metrics": period2_metrics.to_dict()
        },
        "changes": {
            "applications": {
                "absolute": period2_metrics.total_applications - period1_metrics.total_applications,
                "percentage": calc_change(period1_metrics.total_applications, period2_metrics.total_applications)
            },
            "interviews": {
                "absolute": period2_metrics.total_interviews - period1_metrics.total_interviews,
                "percentage": calc_change(period1_metrics.total_interviews, period2_metrics.total_interviews)
            },
            "offers": {
                "absolute": period2_metrics.total_offers - period1_metrics.total_offers,
                "percentage": calc_change(period1_metrics.total_offers, period2_metrics.total_offers)
            },
            "hires": {
                "absolute": period2_metrics.total_hires - period1_metrics.total_hires,
                "percentage": calc_change(period1_metrics.total_hires, period2_metrics.total_hires)
            },
            "time_to_hire": {
                "absolute": period2_metrics.avg_time_to_hire - period1_metrics.avg_time_to_hire,
                "percentage": calc_change(period1_metrics.avg_time_to_hire, period2_metrics.avg_time_to_hire)
            }
        }
    }


# Import func for funnel endpoint
from sqlalchemy import func, and_
