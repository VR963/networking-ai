import uuid
from typing import Optional

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from app.database import get_db

router = APIRouter()


def _get_supabase():
    client = get_db()
    if not client:
        raise HTTPException(status_code=503, detail="Database not configured.")
    return client


class JobCreateRequest(BaseModel):
    title: str
    company: str
    industry: str = "technology"
    description: str = ""
    requirements: list[str] = []
    values: list[str] = []
    culture: list[str] = []
    salary_range: Optional[str] = None
    location: Optional[str] = None
    user_id: Optional[str] = None
    hiring_manager_id: Optional[str] = None


class JobUpdateRequest(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None
    requirements: Optional[list[str]] = None
    values: Optional[list[str]] = None
    culture: Optional[list[str]] = None
    salary_range: Optional[str] = None
    active: Optional[bool] = None


@router.post("/create")
async def create_job(request: JobCreateRequest):
    """Create a new job listing for A2A matching.

    The job profile is what the Job Agent uses to negotiate with Candidate Agents.
    Include values and culture signals for deep matching beyond keywords.
    """
    client = _get_supabase()

    job_id = str(uuid.uuid4())

    job_profile = {
        "title": request.title,
        "company": request.company,
        "industry": request.industry,
        "description": request.description,
        "requirements": request.requirements,
        "values": request.values,
        "culture": request.culture,
        "salary_range": request.salary_range,
    }

    record = {
        "id": job_id,
        "job_id": job_id,
        "industry": request.industry,
        "profile": job_profile,
        "hiring_manager_id": request.hiring_manager_id or request.user_id,
        "active": True,
    }
    client.table("cv2_a2a_jobs").insert(record).execute()

    # Also store flat record for auto-activation service
    user_id = request.user_id or request.hiring_manager_id or ""
    flat_record = {
        "id": job_id,
        "user_id": user_id,
        "title": request.title,
        "company": request.company,
        "industry": request.industry,
        "description": request.description,
        "requirements": request.requirements,
        "values": request.values,
        "culture": request.culture,
        "salary_range": request.salary_range,
        "location": request.location,
        "status": "draft",
    }
    try:
        client.table("cv2_jobs").insert(flat_record).execute()
    except Exception:
        pass  # Table may not exist yet

    return {"status": "created", "job_id": job_id, "profile": job_profile}


@router.get("/list")
async def list_jobs():
    """List all active jobs."""
    client = _get_supabase()
    result = (
        client.table("cv2_a2a_jobs")
        .select("*")
        .eq("active", True)
        .execute()
    )
    return {"jobs": result.data or []}


@router.get("/{job_id}")
async def get_job(job_id: str):
    """Get a specific job by ID."""
    client = _get_supabase()
    result = (
        client.table("cv2_a2a_jobs")
        .select("*")
        .eq("id", job_id)
        .execute()
    )
    if not result.data:
        raise HTTPException(status_code=404, detail="Job not found.")
    return result.data[0]


@router.patch("/{job_id}")
async def update_job(job_id: str, request: JobUpdateRequest):
    """Update a job listing."""
    client = _get_supabase()

    existing = (
        client.table("cv2_a2a_jobs")
        .select("*")
        .eq("id", job_id)
        .execute()
    )
    if not existing.data:
        raise HTTPException(status_code=404, detail="Job not found.")

    job = existing.data[0]
    profile = job.get("profile", {})

    update_data = {}
    if request.title is not None:
        profile["title"] = request.title
    if request.description is not None:
        profile["description"] = request.description
    if request.requirements is not None:
        profile["requirements"] = request.requirements
    if request.values is not None:
        profile["values"] = request.values
    if request.culture is not None:
        profile["culture"] = request.culture
    if request.salary_range is not None:
        profile["salary_range"] = request.salary_range

    update_data["profile"] = profile
    if request.active is not None:
        update_data["active"] = request.active

    client.table("cv2_a2a_jobs").update(update_data).eq("id", job_id).execute()
    return {"status": "updated", "job_id": job_id}


@router.delete("/{job_id}")
async def deactivate_job(job_id: str):
    """Deactivate a job (soft delete)."""
    client = _get_supabase()
    client.table("cv2_a2a_jobs").update({"active": False}).eq("id", job_id).execute()
    return {"status": "deactivated", "job_id": job_id}
