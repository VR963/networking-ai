"""
Job Posting API - Phase 2.

Job postings are Company AI Agents with access to:
- Hiring Manager Personal Agent RAG (hiring preferences)
- Company Admin Agent RAG (company knowledge)
- Job-specific RAG (job requirements and description)
"""

from typing import Optional, List
from datetime import datetime, timedelta
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from pydantic import BaseModel, Field

from ..database import get_db
from ..models.user import User
from ..models.job import Job, JobStatus, JobType, ExperienceLevel
from ..models.company_v2 import Company
from ..models.hiring_manager_role import HiringManagerRole
from ..models.personal_ai_agent import PersonalAIAgent, AgentType
from ..models.company_admin_agent import CompanyAdminAgent
from ..models.audit_log import AuditLog
from ..api.auth import get_current_active_user
from ..services.company_agent_factory import CompanyAgentFactory


router = APIRouter()
company_agent_factory = CompanyAgentFactory()


# ============================================================================
# Request/Response Models
# ============================================================================

class JobCreateRequest(BaseModel):
    """Request to create a job posting."""
    title: str = Field(..., min_length=5, max_length=255)
    description: str = Field(..., min_length=50)
    short_description: Optional[str] = Field(None, max_length=500)
    job_type: str  # "full_time", "part_time", etc.
    experience_level: str  # "entry_level", "mid_level", etc.
    department: Optional[str]
    location: str
    is_remote: bool = False
    is_hybrid: bool = False
    salary_min: Optional[int]
    salary_max: Optional[int]
    salary_visible: bool = True
    required_skills: List[str] = []
    preferred_skills: List[str] = []
    required_experience_years: Optional[int]
    education_requirements: Optional[str]
    benefits: List[str] = []
    application_deadline: Optional[str]  # ISO format
    positions_available: int = 1


class JobResponse(BaseModel):
    """Job posting response."""
    id: int
    company_id: int
    company_name: str
    hiring_manager_id: int
    hiring_manager_name: str
    title: str
    description: str
    short_description: Optional[str]
    job_type: str
    experience_level: str
    department: Optional[str]
    location: str
    is_remote: bool
    is_hybrid: bool
    salary_min: Optional[int]
    salary_max: Optional[int]
    salary_visible: bool
    required_skills: List[str]
    preferred_skills: List[str]
    status: str
    total_applications: int
    total_matches: int
    created_at: str
    published_at: Optional[str]


class JobPublishResponse(BaseModel):
    """Response after publishing a job."""
    job_id: int
    status: str
    message: str
    job_rag_collection_id: str


# ============================================================================
# Job Posting Endpoints
# ============================================================================

@router.post("/", response_model=JobResponse, status_code=status.HTTP_201_CREATED)
async def create_job_posting(
    request: JobCreateRequest,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """
    Create a job posting.

    Prerequisites:
    - User must be an active Hiring Manager
    - HM agent must be activated
    - Company must exist

    Job posting is created as a Company AI Agent with access to:
    - HM Personal Agent RAG (hiring preferences)
    - Company Admin Agent RAG (company knowledge)
    """
    # Verify user is an active HM
    hm_role = db.query(HiringManagerRole).filter(
        HiringManagerRole.user_id == current_user.id,
        HiringManagerRole.is_active == True
    ).first()

    if not hm_role:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="User must be an active Hiring Manager to create job postings"
        )

    # Get HM agent
    hm_agent = db.query(PersonalAIAgent).filter(
        PersonalAIAgent.id == hm_role.hiring_manager_agent_id
    ).first()

    if not hm_agent or hm_agent.status != "active":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Hiring Manager agent must be activated first"
        )

    # Get company
    company = db.query(Company).filter(Company.id == hm_role.company_id).first()
    if not company:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Company {hm_role.company_id} not found"
        )

    # Get company admin agent
    admin_agent = db.query(CompanyAdminAgent).filter(
        CompanyAdminAgent.id == hm_role.company_admin_agent_id
    ).first()

    if not admin_agent:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Company Admin Agent not found"
        )

    # Parse deadline
    application_deadline = None
    if request.application_deadline:
        application_deadline = datetime.fromisoformat(request.application_deadline.replace('Z', '+00:00'))

    # Create job posting
    job = Job(
        company_id=company.id,
        hiring_manager_id=current_user.id,
        hiring_manager_agent_id=hm_agent.id,
        company_admin_agent_id=admin_agent.id,
        title=request.title,
        description=request.description,
        short_description=request.short_description,
        job_type=JobType(request.job_type),
        experience_level=ExperienceLevel(request.experience_level),
        department=request.department,
        location=request.location,
        is_remote=request.is_remote,
        is_hybrid=request.is_hybrid,
        salary_min=request.salary_min,
        salary_max=request.salary_max,
        salary_visible=request.salary_visible,
        required_skills=request.required_skills,
        preferred_skills=request.preferred_skills,
        required_experience_years=request.required_experience_years,
        education_requirements=request.education_requirements,
        benefits=request.benefits,
        application_deadline=application_deadline,
        positions_available=request.positions_available,
        status=JobStatus.DRAFT,
        created_at=datetime.utcnow(),
        updated_at=datetime.utcnow()
    )

    db.add(job)
    db.commit()
    db.refresh(job)

    # Audit log
    audit = AuditLog(
        user_id=current_user.id,
        action="job_created",
        details={
            "job_id": job.id,
            "title": job.title,
            "company_id": company.id
        }
    )
    db.add(audit)
    db.commit()

    return JobResponse(
        id=job.id,
        company_id=job.company_id,
        company_name=company.name,
        hiring_manager_id=current_user.id,
        hiring_manager_name=f"{current_user.first_name} {current_user.last_name}",
        title=job.title,
        description=job.description,
        short_description=job.short_description,
        job_type=job.job_type.value,
        experience_level=job.experience_level.value,
        department=job.department,
        location=job.location,
        is_remote=job.is_remote,
        is_hybrid=job.is_hybrid,
        salary_min=job.salary_min,
        salary_max=job.salary_max,
        salary_visible=job.salary_visible,
        required_skills=job.required_skills or [],
        preferred_skills=job.preferred_skills or [],
        status=job.status.value,
        total_applications=job.total_applications,
        total_matches=job.total_matches,
        created_at=job.created_at.isoformat(),
        published_at=job.published_at.isoformat() if job.published_at else None
    )


@router.post("/{job_id}/publish", response_model=JobPublishResponse)
async def publish_job_posting(
    job_id: int,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """
    Publish a job posting.

    This activates the job as a Company AI Agent:
    1. Creates job-specific RAG collection
    2. Populates with job requirements
    3. Adds HM hiring preferences from Personal RAG
    4. Adds company culture from Company Admin RAG
    5. Makes job searchable for Talent agents
    """
    # Get job
    job = db.query(Job).filter(Job.id == job_id).first()
    if not job:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Job {job_id} not found"
        )

    # Verify ownership
    if job.hiring_manager_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only the hiring manager who created the job can publish it"
        )

    # Check if already published
    if job.status == JobStatus.ACTIVE:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Job is already published"
        )

    # Create job RAG collection ID
    job_rag_collection_id = f"job_{job.id}_rag"
    job.job_rag_collection_id = job_rag_collection_id

    # Prepare job data for Company RAG
    job_data = {
        "title": job.title,
        "description": job.description,
        "department": job.department,
        "level": job.experience_level.value,
        "required_skills": job.required_skills or [],
        "preferred_skills": job.preferred_skills or [],
        "responsibilities": [],  # TODO: Extract from description
        "qualifications": []  # TODO: Extract from description
    }

    # Add job to Company Admin Agent RAG
    company_agent_factory.add_job_posting(
        company_admin_agent_id=job.company_admin_agent_id,
        job_id=job.id,
        job_title=job.title,
        job_data=job_data,
        db=db
    )

    # TODO: Create and populate job-specific RAG collection
    # This would include:
    # - Job requirements and description
    # - HM's hiring preferences (from Personal HM Agent RAG)
    # - Company culture and values (from Company Admin Agent RAG)

    # Publish job
    job.status = JobStatus.ACTIVE
    job.published_at = datetime.utcnow()
    job.updated_at = datetime.utcnow()

    db.commit()

    # Audit log
    audit = AuditLog(
        user_id=current_user.id,
        action="job_published",
        details={
            "job_id": job.id,
            "title": job.title,
            "job_rag_collection_id": job_rag_collection_id
        }
    )
    db.add(audit)
    db.commit()

    return JobPublishResponse(
        job_id=job.id,
        status=job.status.value,
        message="Job published successfully! Now searchable by Talent agents.",
        job_rag_collection_id=job_rag_collection_id
    )


@router.get("/{job_id}", response_model=JobResponse)
async def get_job_posting(
    job_id: int,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Get job posting details."""
    job = db.query(Job).filter(Job.id == job_id).first()
    if not job:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Job {job_id} not found"
        )

    # Get company and HM names
    company = db.query(Company).filter(Company.id == job.company_id).first()
    hm = db.query(User).filter(User.id == job.hiring_manager_id).first()

    return JobResponse(
        id=job.id,
        company_id=job.company_id,
        company_name=company.name if company else "Unknown",
        hiring_manager_id=job.hiring_manager_id,
        hiring_manager_name=f"{hm.first_name} {hm.last_name}" if hm else "Unknown",
        title=job.title,
        description=job.description,
        short_description=job.short_description,
        job_type=job.job_type.value,
        experience_level=job.experience_level.value,
        department=job.department,
        location=job.location,
        is_remote=job.is_remote,
        is_hybrid=job.is_hybrid,
        salary_min=job.salary_min,
        salary_max=job.salary_max,
        salary_visible=job.salary_visible,
        required_skills=job.required_skills or [],
        preferred_skills=job.preferred_skills or [],
        status=job.status.value,
        total_applications=job.total_applications,
        total_matches=job.total_matches,
        created_at=job.created_at.isoformat(),
        published_at=job.published_at.isoformat() if job.published_at else None
    )


@router.get("/my/postings")
async def get_my_job_postings(
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Get all job postings created by current hiring manager."""
    jobs = db.query(Job).filter(
        Job.hiring_manager_id == current_user.id
    ).order_by(Job.created_at.desc()).all()

    # Get company name for each job
    job_responses = []
    for job in jobs:
        company = db.query(Company).filter(Company.id == job.company_id).first()

        job_responses.append({
            "id": job.id,
            "company_name": company.name if company else "Unknown",
            "title": job.title,
            "short_description": job.short_description,
            "status": job.status.value,
            "total_applications": job.total_applications,
            "total_matches": job.total_matches,
            "created_at": job.created_at.isoformat(),
            "published_at": job.published_at.isoformat() if job.published_at else None
        })

    return {
        "total": len(job_responses),
        "jobs": job_responses
    }


@router.patch("/{job_id}/status")
async def update_job_status(
    job_id: int,
    new_status: str,  # "active", "paused", "closed", "filled"
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Update job posting status."""
    job = db.query(Job).filter(Job.id == job_id).first()
    if not job:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Job {job_id} not found"
        )

    # Verify ownership
    if job.hiring_manager_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only the hiring manager who created the job can update it"
        )

    # Update status
    try:
        job.status = JobStatus(new_status)
        if new_status == "closed" or new_status == "filled":
            job.closed_at = datetime.utcnow()

        job.updated_at = datetime.utcnow()
        db.commit()

        # Audit log
        audit = AuditLog(
            user_id=current_user.id,
            action="job_status_updated",
            details={
                "job_id": job.id,
                "new_status": new_status
            }
        )
        db.add(audit)
        db.commit()

        return {
            "job_id": job.id,
            "status": job.status.value,
            "message": f"Job status updated to {new_status}"
        }
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid status: {new_status}"
        )
