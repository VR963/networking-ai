"""
Job API Endpoints.

Handles job posting, searching, and applications.
"""

from datetime import datetime
from typing import List
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from sqlalchemy import or_, and_

from ..database import get_db, SessionLocal
from ..models.user import User, UserRole
from ..models.company import CompanyLegacy as Company
from ..models.job import Job, JobStatus
from ..models.application import Application, ApplicationStatus
from ..models.ai_agent import AIAgent, AgentType
from ..schemas.job import (
    JobCreateRequest,
    JobUpdateRequest,
    JobSearchRequest,
    JobResponse,
    JobSummaryResponse,
    JobListResponse,
)
from ..api.auth import get_current_user, get_current_active_user
from ..services.background_tasks import task_manager, run_matching_for_job


router = APIRouter()


# ============================================================================
# Job CRUD Endpoints
# ============================================================================

@router.post("", response_model=JobResponse, status_code=status.HTTP_201_CREATED)
async def create_job(
    job_data: JobCreateRequest,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    """
    Create a new job posting (companies only).

    Automatically creates an AI agent for this job.
    """
    # Check if user is a company
    if current_user.role != UserRole.COMPANY:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only companies can post jobs.",
        )

    # Get company
    company = db.query(Company).filter(Company.user_id == current_user.id).first()
    if not company:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Company profile not found. Create company profile first.",
        )

    # Create job
    job = Job(
        company_id=company.id,
        status=JobStatus.DRAFT,
        **job_data.model_dump()
    )

    db.add(job)
    db.commit()
    db.refresh(job)

    # Create AI agent for this job
    ai_agent = AIAgent(
        agent_type=AgentType.JOB_AGENT,
        agent_name=f"Job Agent: {job.title}",
        agent_specialization=[job.title] + (job.required_skills or []),
        status="active",
    )
    db.add(ai_agent)
    db.commit()
    db.refresh(ai_agent)

    # Link agent to job
    job.ai_agent_id = ai_agent.id
    company.total_jobs_posted += 1
    db.commit()
    db.refresh(job)

    print(f"[JOB] Created job {job.id} for company {company.id}")

    # Trigger background matching if job is active
    if job.status == JobStatus.ACTIVE:
        task_id = task_manager.submit_task(
            func=run_matching_for_job,
            args=(job.id, SessionLocal)
        )
        print(f"[JOB] Submitted matching task {task_id} for job {job.id}")

    return job


@router.get("", response_model=JobListResponse)
async def list_jobs(
    query: str = None,
    location: str = None,
    job_type: str = None,
    is_remote: bool = None,
    salary_min: int = None,
    limit: int = 20,
    offset: int = 0,
    db: Session = Depends(get_db),
):
    """
    List and search jobs with filters.

    Public endpoint - no authentication required.
    """
    # Start with base query for active jobs
    jobs_query = db.query(Job).filter(Job.status == JobStatus.ACTIVE)

    # Apply filters
    if query:
        # Search in title and description
        search_filter = or_(
            Job.title.ilike(f"%{query}%"),
            Job.description.ilike(f"%{query}%")
        )
        jobs_query = jobs_query.filter(search_filter)

    if location:
        jobs_query = jobs_query.filter(Job.location.ilike(f"%{location}%"))

    if job_type:
        jobs_query = jobs_query.filter(Job.job_type == job_type)

    if is_remote is not None:
        jobs_query = jobs_query.filter(Job.is_remote == is_remote)

    if salary_min is not None:
        jobs_query = jobs_query.filter(
            or_(
                Job.salary_min >= salary_min,
                Job.salary_max >= salary_min
            )
        )

    # Get total count
    total = jobs_query.count()

    # Apply pagination
    jobs = jobs_query.order_by(Job.created_at.desc()).offset(offset).limit(limit).all()

    return JobListResponse(
        jobs=jobs,
        total=total,
        limit=limit,
        offset=offset,
    )


@router.get("/{job_id}", response_model=JobResponse)
async def get_job(
    job_id: int,
    db: Session = Depends(get_db),
):
    """
    Get job details by ID.

    Public endpoint - increments view count.
    """
    job = db.query(Job).filter(Job.id == job_id).first()

    if not job:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Job not found.",
        )

    # Increment view count
    job.total_views += 1
    db.commit()

    return job


@router.put("/{job_id}", response_model=JobResponse)
async def update_job(
    job_id: int,
    job_data: JobUpdateRequest,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    """Update job posting (only by job owner)."""
    # Get job
    job = db.query(Job).filter(Job.id == job_id).first()

    if not job:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Job not found.",
        )

    # Check ownership
    company = db.query(Company).filter(Company.user_id == current_user.id).first()
    if not company or job.company_id != company.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You don't have permission to update this job.",
        )

    # Track if status is changing to active
    is_newly_published = (
        job_data.status == JobStatus.ACTIVE and
        job.status != JobStatus.ACTIVE and
        not job.published_at
    )

    # Update fields
    update_data = job_data.dict(exclude_unset=True)
    for field, value in update_data.items():
        setattr(job, field, value)

    # If publishing, set published_at
    if job_data.status == JobStatus.ACTIVE and not job.published_at:
        job.published_at = datetime.utcnow()
        company.active_jobs += 1

    db.commit()
    db.refresh(job)

    print(f"[JOB] Updated job {job_id}")

    # Trigger background matching if job is newly published
    if is_newly_published:
        task_id = task_manager.submit_task(
            func=run_matching_for_job,
            args=(job.id, SessionLocal)
        )
        print(f"[JOB] Submitted matching task {task_id} for newly published job {job.id}")

    return job


@router.delete("/{job_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_job(
    job_id: int,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    """Delete job posting (only by job owner)."""
    # Get job
    job = db.query(Job).filter(Job.id == job_id).first()

    if not job:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Job not found.",
        )

    # Check ownership
    company = db.query(Company).filter(Company.user_id == current_user.id).first()
    if not company or job.company_id != company.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You don't have permission to delete this job.",
        )

    # Update active jobs count
    if job.status == JobStatus.ACTIVE:
        company.active_jobs = max(0, company.active_jobs - 1)

    # Delete job (cascades to applications, matches, etc)
    db.delete(job)
    db.commit()

    print(f"[JOB] Deleted job {job_id}")

    return None


# ============================================================================
# Application Endpoints
# ============================================================================

@router.post("/{job_id}/apply", status_code=status.HTTP_201_CREATED)
async def apply_to_job(
    job_id: int,
    cover_letter: str = None,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    """
    Apply to a job.

    Job seekers only. Creates application record.
    """
    # Check if user is job seeker
    if current_user.role != UserRole.JOB_SEEKER:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only job seekers can apply to jobs.",
        )

    # Get job
    job = db.query(Job).filter(Job.id == job_id).first()

    if not job:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Job not found.",
        )

    if job.status != JobStatus.ACTIVE:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="This job is not accepting applications.",
        )

    # Check if already applied
    existing_application = db.query(Application).filter(
        and_(
            Application.user_id == current_user.id,
            Application.job_id == job_id
        )
    ).first()

    if existing_application:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="You have already applied to this job.",
        )

    # Get user's profile for resume URL
    from ..models.profile import UserProfile
    profile = db.query(UserProfile).filter(UserProfile.user_id == current_user.id).first()

    # Create application
    application = Application(
        user_id=current_user.id,
        job_id=job_id,
        cover_letter=cover_letter,
        resume_url=profile.cv_url if profile else None,
        status=ApplicationStatus.PENDING,
    )

    db.add(application)

    # Update job stats
    job.total_applications += 1

    db.commit()
    db.refresh(application)

    print(f"[APPLICATION] User {current_user.id} applied to job {job_id}")

    return {
        "message": "Application submitted successfully",
        "application_id": application.id,
        "status": application.status.value,
    }


@router.get("/{job_id}/applications")
async def get_job_applications(
    job_id: int,
    status_filter: str = None,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    """
    Get applications for a job (company only).

    Returns list of applications with applicant info.
    """
    # Get job
    job = db.query(Job).filter(Job.id == job_id).first()

    if not job:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Job not found.",
        )

    # Check ownership
    company = db.query(Company).filter(Company.user_id == current_user.id).first()
    if not company or job.company_id != company.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You don't have permission to view these applications.",
        )

    # Get applications
    applications_query = db.query(Application).filter(Application.job_id == job_id)

    if status_filter:
        applications_query = applications_query.filter(Application.status == status_filter)

    applications = applications_query.order_by(Application.created_at.desc()).all()

    # Return applications with applicant info
    result = []
    for app in applications:
        result.append({
            "id": app.id,
            "applicant_id": app.user_id,
            "applicant_name": app.user.full_name,
            "cover_letter": app.cover_letter,
            "resume_url": app.resume_url,
            "status": app.status.value,
            "ai_match_score": app.ai_match_score,
            "created_at": app.created_at.isoformat(),
        })

    return {
        "job_id": job_id,
        "total_applications": len(applications),
        "applications": result,
    }


@router.get("/my/applications")
async def get_my_applications(
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    """Get current user's job applications."""
    applications = db.query(Application).filter(
        Application.user_id == current_user.id
    ).order_by(Application.created_at.desc()).all()

    result = []
    for app in applications:
        result.append({
            "id": app.id,
            "job_id": app.job_id,
            "job_title": app.job.title,
            "company_name": app.job.company.company_name,
            "status": app.status.value,
            "ai_match_score": app.ai_match_score,
            "created_at": app.created_at.isoformat(),
            "updated_at": app.updated_at.isoformat(),
        })

    return {
        "total_applications": len(applications),
        "applications": result,
    }
