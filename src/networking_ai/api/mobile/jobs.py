"""
Mobile Jobs Router.

Endpoints:
- GET / - Search jobs with filters and pagination
- GET /{job_id} - Get job details
- POST /{job_id}/save - Save job for later
- DELETE /{job_id}/save - Unsave job
"""

from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from sqlalchemy import desc, or_
from datetime import datetime
from typing import Optional, List

from ...database import get_db
from ...models.user import User
from ...models.job import Job, JobStatus
from ...models.company import CompanyLegacy as Company
from ...models.mobile import SavedJob
from ...models.application import Application
from .schemas import (
    JobSearchRequest,
    JobCompact,
    JobDetail,
    CompanyCompact,
    SalaryRange,
    JobRequirements,
    SavedJobResponse,
    JobListResponse,
    PaginationMeta,
    CursorMeta
)
from .responses import create_success_response, create_error_response, ErrorCode
from .dependencies import mobile_auth_required, validate_pagination_params
from .pagination import paginate_query, create_pagination_cursor

jobs_router = APIRouter()


def build_job_compact_response(job: Job, user_id: int, db: Session) -> JobCompact:
    """Build compact job response with user-specific flags."""
    # Check if saved
    is_saved = db.query(SavedJob).filter(
        SavedJob.user_id == user_id,
        SavedJob.job_id == job.id
    ).first() is not None

    # Check if applied
    is_applied = db.query(Application).filter(
        Application.talent_user_id == user_id,
        Application.job_id == job.id
    ).first() is not None

    # Get company info
    company_compact = None
    if job.company:
        company_compact = CompanyCompact(
            id=job.company.id,
            name=job.company.name,
            logo_url=None  # Add logo URL field to Company model if needed
        )

    # Build salary range
    salary_range = None
    if job.min_salary or job.max_salary:
        salary_range = SalaryRange(
            min=job.min_salary,
            max=job.max_salary,
            currency=job.salary_currency or "USD"
        )

    return JobCompact(
        id=job.id,
        title=job.title,
        company=company_compact,
        location=job.location,
        job_type=job.job_type.value if job.job_type else None,
        experience_level=job.experience_level.value if job.experience_level else None,
        salary_range=salary_range,
        posted_at=job.created_at,
        is_saved=is_saved,
        is_applied=is_applied,
        match_score=None  # TODO: Calculate match score if matching system exists
    )


@jobs_router.get("/", response_model=dict)
async def search_jobs(
    q: Optional[str] = Query(None, description="Search query"),
    location: Optional[str] = Query(None, description="Location filter"),
    job_type: Optional[str] = Query(None, description="Job type filter"),
    experience_level: Optional[str] = Query(None, description="Experience level filter"),
    cursor: Optional[str] = Query(None, description="Pagination cursor"),
    limit: int = Query(20, ge=1, le=50, description="Page size"),
    db: Session = Depends(get_db),
    user: User = Depends(mobile_auth_required)
):
    """
    Search jobs with filters and cursor-based pagination.

    Returns mobile-optimized job listings.
    """
    # Build query
    query = db.query(Job).filter(Job.status == JobStatus.OPEN)

    # Apply filters
    if q:
        # Search in title and description
        search_term = f"%{q}%"
        query = query.filter(
            or_(
                Job.title.ilike(search_term),
                Job.description.ilike(search_term)
            )
        )

    if location:
        query = query.filter(Job.location.ilike(f"%{location}%"))

    if job_type:
        query = query.filter(Job.job_type == job_type)

    if experience_level:
        query = query.filter(Job.experience_level == experience_level)

    # Sort by created_at descending (most recent first)
    query = query.order_by(desc(Job.created_at))

    # Apply pagination
    paginated_query, actual_limit = paginate_query(
        query,
        cursor=cursor,
        limit=limit,
        max_limit=50,
        sort_field="created_at",
        sort_desc=True
    )

    # Execute query
    jobs = paginated_query.all()

    # Check if there are more pages
    has_more = len(jobs) > actual_limit
    if has_more:
        jobs = jobs[:actual_limit]

    # Create next cursor
    next_cursor = create_pagination_cursor(
        items=jobs + ([jobs[-1]] if has_more else []),  # Add extra item for cursor generation
        limit=actual_limit,
        sort_field="created_at"
    )

    # Build response
    job_responses = [
        build_job_compact_response(job, user.id, db)
        for job in jobs
    ]

    pagination_meta = PaginationMeta(
        cursor=CursorMeta(
            next=next_cursor,
            has_more=has_more
        ),
        count=len(job_responses)
    )

    return create_success_response(
        data={
            "data": [job.model_dump() for job in job_responses],
            "meta": pagination_meta.model_dump()
        },
        self_link="/api/v1/mobile/jobs"
    )


@jobs_router.get("/{job_id}", response_model=dict)
async def get_job_detail(
    job_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(mobile_auth_required)
):
    """
    Get detailed job information.

    Includes full description, requirements, benefits, and user-specific flags.
    """
    # Find job
    job = db.query(Job).filter(Job.id == job_id).first()
    if not job:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=create_error_response(
                code=ErrorCode.NOT_FOUND,
                message="Job not found"
            )
        )

    # Check if saved
    is_saved = db.query(SavedJob).filter(
        SavedJob.user_id == user.id,
        SavedJob.job_id == job.id
    ).first() is not None

    # Check if applied
    is_applied = db.query(Application).filter(
        Application.talent_user_id == user.id,
        Application.job_id == job.id
    ).first() is not None

    # Get company info
    company_compact = None
    if job.company:
        company_compact = CompanyCompact(
            id=job.company.id,
            name=job.company.name,
            logo_url=None
        )

    # Build salary range
    salary_range = None
    if job.min_salary or job.max_salary:
        salary_range = SalaryRange(
            min=job.min_salary,
            max=job.max_salary,
            currency=job.salary_currency or "USD"
        )

    # Parse requirements (if stored as JSON or text)
    requirements = JobRequirements(
        required_skills=[],  # TODO: Parse from job.required_skills if exists
        preferred_skills=[],
        min_experience_years=None
    )

    # Count applications
    application_count = db.query(Application).filter(
        Application.job_id == job.id
    ).count()

    # Build detail response
    job_detail = JobDetail(
        id=job.id,
        title=job.title,
        description=job.description,
        company=company_compact,
        location=job.location,
        job_type=job.job_type.value if job.job_type else None,
        experience_level=job.experience_level.value if job.experience_level else None,
        salary_range=salary_range,
        requirements=requirements,
        benefits=[],  # TODO: Parse from job.benefits if exists
        application_count=application_count,
        posted_at=job.created_at,
        is_saved=is_saved,
        is_applied=is_applied,
        match_score=None,  # TODO: Calculate match score
        match_reasons=[]  # TODO: Generate match reasons
    )

    return create_success_response(
        data=job_detail.model_dump(),
        self_link=f"/api/v1/mobile/jobs/{job_id}"
    )


@jobs_router.post("/{job_id}/save", response_model=dict, status_code=status.HTTP_201_CREATED)
async def save_job(
    job_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(mobile_auth_required)
):
    """
    Save job for later.

    Bookmarks the job for the user.
    """
    # Check if job exists
    job = db.query(Job).filter(Job.id == job_id).first()
    if not job:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=create_error_response(
                code=ErrorCode.NOT_FOUND,
                message="Job not found"
            )
        )

    # Check if already saved
    existing_save = db.query(SavedJob).filter(
        SavedJob.user_id == user.id,
        SavedJob.job_id == job_id
    ).first()

    if existing_save:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=create_error_response(
                code=ErrorCode.ALREADY_EXISTS,
                message="Job already saved"
            )
        )

    # Create saved job
    saved_job = SavedJob(
        user_id=user.id,
        job_id=job_id,
        saved_at=datetime.utcnow()
    )
    db.add(saved_job)
    db.commit()
    db.refresh(saved_job)

    response = SavedJobResponse(
        job_id=saved_job.job_id,
        notes=saved_job.notes,
        saved_at=saved_job.saved_at
    )

    return create_success_response(
        data=response.model_dump(),
        self_link=f"/api/v1/mobile/jobs/{job_id}/save"
    )


@jobs_router.delete("/{job_id}/save", status_code=status.HTTP_204_NO_CONTENT)
async def unsave_job(
    job_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(mobile_auth_required)
):
    """
    Unsave job.

    Removes job from user's saved jobs.
    """
    # Find saved job
    saved_job = db.query(SavedJob).filter(
        SavedJob.user_id == user.id,
        SavedJob.job_id == job_id
    ).first()

    if not saved_job:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=create_error_response(
                code=ErrorCode.NOT_FOUND,
                message="Saved job not found"
            )
        )

    # Delete saved job
    db.delete(saved_job)
    db.commit()

    return None  # 204 No Content
