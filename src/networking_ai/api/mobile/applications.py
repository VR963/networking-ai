"""
Mobile Applications Router.

Endpoints:
- POST / - Submit job application
- GET / - List user's applications
- GET /{application_id} - Get application details with timeline
"""

from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from sqlalchemy import desc
from datetime import datetime
from typing import Optional, List

from ...database import get_db
from ...models.user import User
from ...models.application import Application, ApplicationStatus as AppStatus
from ...models.job import Job
from ...models.interview import Interview
from .schemas import (
    ApplicationCreateRequest,
    ApplicationCompact,
    ApplicationDetail,
    ApplicationListResponse,
    JobCompact,
    JobDetail,
    CompanyCompact,
    SalaryRange,
    JobRequirements,
    TimelineEvent,
    InterviewCompact,
    MessageCompact,
    NextStep,
    PaginationMeta,
    CursorMeta
)
from .responses import create_success_response, create_error_response, ErrorCode
from .dependencies import mobile_auth_required
from .pagination import paginate_query, create_pagination_cursor

applications_router = APIRouter()


def build_application_compact(app: Application, db: Session) -> ApplicationCompact:
    """Build compact application response."""
    # Get job info
    job = app.job
    company_compact = None
    if job and job.company:
        company_compact = CompanyCompact(
            id=job.company.id,
            name=job.company.name,
            logo_url=None
        )

    salary_range = None
    if job and (job.min_salary or job.max_salary):
        salary_range = SalaryRange(
            min=job.min_salary,
            max=job.max_salary,
            currency=job.salary_currency or "USD"
        )

    job_compact = JobCompact(
        id=job.id,
        title=job.title,
        company=company_compact,
        location=job.location,
        job_type=job.job_type.value if job.job_type else None,
        experience_level=job.experience_level.value if job.experience_level else None,
        salary_range=salary_range,
        posted_at=job.created_at,
        is_saved=False,  # Not checking saved status in compact view
        is_applied=True,
        match_score=app.match_score
    )

    return ApplicationCompact(
        id=app.id,
        job=job_compact,
        status=app.status.value if app.status else "submitted",
        submitted_at=app.applied_at or app.created_at,
        last_updated=app.updated_at or app.created_at
    )


@applications_router.post("/", response_model=dict, status_code=status.HTTP_201_CREATED)
async def submit_application(
    request: ApplicationCreateRequest,
    db: Session = Depends(get_db),
    user: User = Depends(mobile_auth_required)
):
    """
    Submit job application.

    Creates a new application for the specified job.
    """
    # Check if job exists
    job = db.query(Job).filter(Job.id == request.job_id).first()
    if not job:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=create_error_response(
                code=ErrorCode.NOT_FOUND,
                message="Job not found"
            )
        )

    # Check if already applied
    existing_app = db.query(Application).filter(
        Application.talent_user_id == user.id,
        Application.job_id == request.job_id
    ).first()

    if existing_app:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=create_error_response(
                code=ErrorCode.ALREADY_EXISTS,
                message="You have already applied to this job"
            )
        )

    # Create application
    application = Application(
        talent_user_id=user.id,
        job_id=request.job_id,
        company_id=job.company_id,
        cover_letter=request.cover_letter,
        status=AppStatus.APPLIED,
        applied_at=datetime.utcnow(),
        created_at=datetime.utcnow()
    )
    db.add(application)
    db.commit()
    db.refresh(application)

    # Build response
    app_compact = build_application_compact(application, db)

    return create_success_response(
        data=app_compact.model_dump(),
        self_link=f"/api/v1/mobile/applications/{application.id}"
    )


@applications_router.get("/", response_model=dict)
async def list_applications(
    status_filter: Optional[str] = Query(None, alias="status", description="Filter by status"),
    cursor: Optional[str] = Query(None, description="Pagination cursor"),
    limit: int = Query(20, ge=1, le=50, description="Page size"),
    db: Session = Depends(get_db),
    user: User = Depends(mobile_auth_required)
):
    """
    List user's applications with pagination.

    Can filter by status.
    """
    # Build query
    query = db.query(Application).filter(Application.talent_user_id == user.id)

    # Apply status filter
    if status_filter:
        try:
            status_enum = AppStatus(status_filter)
            query = query.filter(Application.status == status_enum)
        except ValueError:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=create_error_response(
                    code=ErrorCode.VALIDATION_ERROR,
                    message=f"Invalid status: {status_filter}"
                )
            )

    # Sort by most recent first
    query = query.order_by(desc(Application.applied_at))

    # Apply pagination
    paginated_query, actual_limit = paginate_query(
        query,
        cursor=cursor,
        limit=limit,
        max_limit=50,
        sort_field="applied_at",
        sort_desc=True
    )

    # Execute query
    applications = paginated_query.all()

    # Check if there are more pages
    has_more = len(applications) > actual_limit
    if has_more:
        applications = applications[:actual_limit]

    # Create next cursor
    next_cursor = create_pagination_cursor(
        items=applications + ([applications[-1]] if has_more else []),
        limit=actual_limit,
        sort_field="applied_at"
    )

    # Build response
    app_responses = [
        build_application_compact(app, db)
        for app in applications
    ]

    pagination_meta = PaginationMeta(
        cursor=CursorMeta(
            next=next_cursor,
            has_more=has_more
        ),
        count=len(app_responses)
    )

    return create_success_response(
        data={
            "data": [app.model_dump() for app in app_responses],
            "meta": pagination_meta.model_dump()
        },
        self_link="/api/v1/mobile/applications"
    )


@applications_router.get("/{application_id}", response_model=dict)
async def get_application_detail(
    application_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(mobile_auth_required)
):
    """
    Get detailed application information.

    Includes timeline, interviews, messages, and next steps.
    """
    # Find application
    application = db.query(Application).filter(
        Application.id == application_id,
        Application.talent_user_id == user.id
    ).first()

    if not application:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=create_error_response(
                code=ErrorCode.NOT_FOUND,
                message="Application not found"
            )
        )

    # Build job detail
    job = application.job
    company_compact = None
    if job.company:
        company_compact = CompanyCompact(
            id=job.company.id,
            name=job.company.name,
            logo_url=None
        )

    salary_range = None
    if job.min_salary or job.max_salary:
        salary_range = SalaryRange(
            min=job.min_salary,
            max=job.max_salary,
            currency=job.salary_currency or "USD"
        )

    job_detail = JobDetail(
        id=job.id,
        title=job.title,
        description=job.description,
        company=company_compact,
        location=job.location,
        job_type=job.job_type.value if job.job_type else None,
        experience_level=job.experience_level.value if job.experience_level else None,
        salary_range=salary_range,
        requirements=JobRequirements(required_skills=[], preferred_skills=[]),
        benefits=[],
        application_count=None,
        posted_at=job.created_at,
        is_saved=False,
        is_applied=True,
        match_score=application.match_score,
        match_reasons=[]
    )

    # Build timeline
    timeline = [
        TimelineEvent(
            stage="submitted",
            timestamp=application.applied_at or application.created_at,
            note="Application submitted"
        )
    ]

    # Add status changes to timeline
    if application.status == AppStatus.SCREENING:
        timeline.append(TimelineEvent(
            stage="screening",
            timestamp=application.updated_at,
            note="Application under review"
        ))
    elif application.status == AppStatus.INTERVIEWING:
        timeline.append(TimelineEvent(
            stage="interviewing",
            timestamp=application.updated_at,
            note="Interview scheduled"
        ))

    # Get interviews
    interviews = db.query(Interview).filter(
        Interview.application_id == application.id
    ).order_by(Interview.scheduled_at).all()

    interview_responses = [
        InterviewCompact(
            id=interview.id,
            stage=interview.stage.value if interview.stage else "unknown",
            scheduled_at=interview.scheduled_at,
            interviewer=None,  # TODO: Get interviewer name
            location=interview.location,
            status=interview.status.value if interview.status else "scheduled"
        )
        for interview in interviews
    ]

    # Determine next step
    next_step = None
    if interviews:
        upcoming = [i for i in interviews if i.scheduled_at and i.scheduled_at > datetime.utcnow()]
        if upcoming:
            next_interview = upcoming[0]
            next_step = NextStep(
                type="interview",
                scheduled_at=next_interview.scheduled_at,
                description=f"{next_interview.stage.value if next_interview.stage else 'Interview'} scheduled"
            )

    # Build detail response
    app_detail = ApplicationDetail(
        id=application.id,
        job=job_detail,
        status=application.status.value if application.status else "submitted",
        submitted_at=application.applied_at or application.created_at,
        last_updated=application.updated_at or application.created_at,
        timeline=timeline,
        interviews=interview_responses,
        messages=[],  # TODO: Get messages
        next_step=next_step
    )

    return create_success_response(
        data=app_detail.model_dump(),
        self_link=f"/api/v1/mobile/applications/{application_id}"
    )
