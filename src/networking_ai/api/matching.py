"""
Matching API - Phase 2.

Endpoints for AI-powered matching between Talent Personal Agents and Job Postings.

Key Features:
- Daily match delivery (top 3 matches per day for talent)
- Match feedback (interested/not interested)
- Match viewing and response tracking
- Dual RAG semantic matching
"""

from typing import List, Optional
from datetime import datetime, timedelta
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from sqlalchemy import and_, or_
from pydantic import BaseModel, Field

from ..database import get_db
from ..models.user import User
from ..models.personal_ai_agent import PersonalAIAgent, AgentType
from ..models.job import Job
from ..models.match import Match, MatchStatus
from ..models.company_v2 import Company
from ..models.subscription import Subscription
from ..models.audit_log import AgentAuditLog as AuditLog
from ..api.auth import get_current_active_user
from ..services.agent_matching_service import create_agent_matching_service


router = APIRouter()


# ============================================================================
# Request/Response Models
# ============================================================================

class MatchResponse(BaseModel):
    """Match response."""
    id: int
    job_id: int
    job_title: str
    company_id: int
    company_name: str
    match_score: float
    skill_match_score: Optional[float]
    preference_match_score: Optional[float]
    culture_match_score: Optional[float]
    ai_explanation: Optional[str]
    matched_skills: List[str] = []
    skill_gaps: List[str] = []
    matched_preferences: List[str] = []
    growth_opportunities: List[str] = []
    status: str
    talent_viewed_at: Optional[str]
    talent_responded_at: Optional[str]
    created_at: str
    expires_at: Optional[str]

    # Job details (denormalized for convenience)
    job_type: Optional[str]
    location: Optional[str]
    is_remote: bool
    salary_min: Optional[int]
    salary_max: Optional[int]


class MatchFeedbackRequest(BaseModel):
    """Request to provide feedback on a match."""
    feedback: str = Field(..., description="'interested' or 'not_interested'")
    reason: Optional[str] = Field(None, description="Optional reason for feedback")


class GenerateMatchesRequest(BaseModel):
    """Request to generate new matches (admin/testing)."""
    limit: int = Field(3, ge=1, le=10, description="Number of matches to generate")


# ============================================================================
# Talent Matching Endpoints
# ============================================================================

@router.get("/my-matches", response_model=List[MatchResponse])
async def get_my_matches(
    status_filter: Optional[str] = Query(None, description="Filter by status: pending, viewed, interested, etc."),
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """
    Get matches for current talent user.

    Returns all matches, optionally filtered by status.
    Talent users only see their own matches.
    """
    # Verify user has talent agent
    talent_agent = db.query(PersonalAIAgent).filter(
        PersonalAIAgent.user_id == current_user.id,
        PersonalAIAgent.agent_type == AgentType.TALENT
    ).first()

    if not talent_agent:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Talent agent not found. Complete your profile interview first."
        )

    # Check subscription
    subscription = db.query(Subscription).filter(
        Subscription.user_id == current_user.id
    ).first()

    if not subscription or not subscription.has_data_access():
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="No active subscription. Please renew to access matches."
        )

    # Build query
    query = db.query(Match).filter(
        Match.talent_user_id == current_user.id
    )

    # Apply status filter
    if status_filter:
        try:
            status_enum = MatchStatus(status_filter)
            query = query.filter(Match.status == status_enum)
        except ValueError:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid status: {status_filter}"
            )

    # Get matches
    matches = query.order_by(Match.created_at.desc()).all()

    # Build responses with job details
    responses = []
    for match in matches:
        job = db.query(Job).filter(Job.id == match.job_id).first()

        responses.append(MatchResponse(
            id=match.id,
            job_id=match.job_id,
            job_title=match.job_title,
            company_id=match.company_id,
            company_name=match.company_name,
            match_score=match.match_score,
            skill_match_score=match.skill_match_score,
            preference_match_score=match.preference_match_score,
            culture_match_score=match.culture_match_score,
            ai_explanation=match.ai_explanation,
            matched_skills=match.matched_skills or [],
            skill_gaps=match.skill_gaps or [],
            matched_preferences=match.matched_preferences or [],
            growth_opportunities=match.growth_opportunities or [],
            status=match.status.value,
            talent_viewed_at=match.talent_viewed_at.isoformat() if match.talent_viewed_at else None,
            talent_responded_at=match.talent_responded_at.isoformat() if match.talent_responded_at else None,
            created_at=match.created_at.isoformat(),
            expires_at=match.expires_at.isoformat() if match.expires_at else None,
            # Job details
            job_type=job.job_type.value if job and job.job_type else None,
            location=job.location if job else None,
            is_remote=job.is_remote if job else False,
            salary_min=job.salary_min if job else None,
            salary_max=job.salary_max if job else None
        ))

    return responses


@router.get("/my-matches/today")
async def get_todays_matches(
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """
    Get today's matches (top 3 daily matches).

    Matches are delivered daily to keep talent engaged without overwhelming them.
    """
    # Verify talent agent
    talent_agent = db.query(PersonalAIAgent).filter(
        PersonalAIAgent.user_id == current_user.id,
        PersonalAIAgent.agent_type == AgentType.TALENT
    ).first()

    if not talent_agent:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Talent agent not found"
        )

    # Check subscription
    subscription = db.query(Subscription).filter(
        Subscription.user_id == current_user.id
    ).first()

    if not subscription or not subscription.has_data_access():
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="No active subscription"
        )

    # Get matches from last 24 hours
    yesterday = datetime.utcnow() - timedelta(days=1)

    matches = db.query(Match).filter(
        Match.talent_user_id == current_user.id,
        Match.created_at >= yesterday
    ).order_by(Match.match_score.desc()).limit(3).all()

    # If no matches today, generate new ones
    if not matches:
        matching_service = create_agent_matching_service()
        matches = matching_service.find_matches_for_talent(
            talent_user=current_user,
            talent_agent=talent_agent,
            db=db,
            limit=3
        )

    # Build responses
    responses = []
    for match in matches:
        job = db.query(Job).filter(Job.id == match.job_id).first()

        responses.append(MatchResponse(
            id=match.id,
            job_id=match.job_id,
            job_title=match.job_title,
            company_id=match.company_id,
            company_name=match.company_name,
            match_score=match.match_score,
            skill_match_score=match.skill_match_score,
            preference_match_score=match.preference_match_score,
            culture_match_score=match.culture_match_score,
            ai_explanation=match.ai_explanation,
            matched_skills=match.matched_skills or [],
            skill_gaps=match.skill_gaps or [],
            matched_preferences=match.matched_preferences or [],
            growth_opportunities=match.growth_opportunities or [],
            status=match.status.value,
            talent_viewed_at=match.talent_viewed_at.isoformat() if match.talent_viewed_at else None,
            talent_responded_at=match.talent_responded_at.isoformat() if match.talent_responded_at else None,
            created_at=match.created_at.isoformat(),
            expires_at=match.expires_at.isoformat() if match.expires_at else None,
            # Job details
            job_type=job.job_type.value if job and job.job_type else None,
            location=job.location if job else None,
            is_remote=job.is_remote if job else False,
            salary_min=job.salary_min if job else None,
            salary_max=job.salary_max if job else None
        ))

    return {
        "total": len(responses),
        "matches": responses,
        "generated_at": datetime.utcnow().isoformat()
    }


@router.post("/matches/{match_id}/view")
async def mark_match_viewed(
    match_id: int,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Mark a match as viewed."""
    match = db.query(Match).filter(Match.id == match_id).first()

    if not match:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Match {match_id} not found"
        )

    # Verify ownership
    if match.talent_user_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You can only view your own matches"
        )

    # Mark as viewed
    match.mark_viewed()
    db.commit()

    # Audit log
    audit = AuditLog(
        user_id=current_user.id,
        action="match_viewed",
        details={
            "match_id": match_id,
            "job_id": match.job_id,
            "job_title": match.job_title
        }
    )
    db.add(audit)
    db.commit()

    return {
        "match_id": match_id,
        "status": match.status.value,
        "viewed_at": match.talent_viewed_at.isoformat()
    }


@router.post("/matches/{match_id}/feedback")
async def provide_match_feedback(
    match_id: int,
    request: MatchFeedbackRequest,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """
    Provide feedback on a match.

    Feedback options:
    - interested: Talent is interested in this opportunity
    - not_interested: Talent is not interested
    """
    match = db.query(Match).filter(Match.id == match_id).first()

    if not match:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Match {match_id} not found"
        )

    # Verify ownership
    if match.talent_user_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You can only provide feedback on your own matches"
        )

    # Apply feedback
    if request.feedback == "interested":
        match.mark_interested(reason=request.reason)
    elif request.feedback == "not_interested":
        match.mark_not_interested(reason=request.reason)
    else:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Feedback must be 'interested' or 'not_interested'"
        )

    db.commit()

    # Audit log
    audit = AuditLog(
        user_id=current_user.id,
        action="match_feedback",
        details={
            "match_id": match_id,
            "feedback": request.feedback,
            "job_id": match.job_id,
            "job_title": match.job_title
        }
    )
    db.add(audit)
    db.commit()

    feedback_message = "We'll help you connect with this opportunity." if request.feedback == 'interested' else "We'll refine future matches based on your preferences."
    return {
        "match_id": match_id,
        "status": match.status.value,
        "feedback": request.feedback,
        "message": f"Thank you for your feedback! {feedback_message}"
    }


@router.post("/generate-matches")
async def generate_new_matches(
    request: GenerateMatchesRequest,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """
    Generate new matches for current user.

    This endpoint manually triggers match generation (useful for testing or on-demand matching).
    In production, matches are generated automatically daily.
    """
    # Verify talent agent
    talent_agent = db.query(PersonalAIAgent).filter(
        PersonalAIAgent.user_id == current_user.id,
        PersonalAIAgent.agent_type == AgentType.TALENT,
        PersonalAIAgent.status == "active"
    ).first()

    if not talent_agent:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Active talent agent required. Complete your profile interview first."
        )

    # Check subscription
    subscription = db.query(Subscription).filter(
        Subscription.user_id == current_user.id
    ).first()

    if not subscription or not subscription.has_data_access():
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Active subscription required"
        )

    # Generate matches
    matching_service = create_agent_matching_service()

    matches = matching_service.find_matches_for_talent(
        talent_user=current_user,
        talent_agent=talent_agent,
        db=db,
        limit=request.limit
    )

    # Audit log
    audit = AuditLog(
        user_id=current_user.id,
        action="matches_generated",
        details={
            "count": len(matches),
            "limit": request.limit
        }
    )
    db.add(audit)
    db.commit()

    return {
        "total_matches": len(matches),
        "match_ids": [m.id for m in matches],
        "message": f"Generated {len(matches)} new matches!"
    }


# ============================================================================
# Job Matching Endpoints (for Hiring Managers)
# ============================================================================

@router.get("/jobs/{job_id}/matches")
async def get_job_matches(
    job_id: int,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """
    Get talent matches for a job posting.

    Only the hiring manager who created the job can view matches.
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
            detail="Only the hiring manager who created this job can view matches"
        )

    # Get matches
    matches = db.query(Match).filter(
        Match.job_id == job_id
    ).order_by(Match.match_score.desc()).all()

    # Build responses
    responses = []
    for match in matches:
        talent = db.query(User).filter(User.id == match.talent_user_id).first()

        responses.append({
            "match_id": match.id,
            "talent_name": f"{talent.first_name} {talent.last_name}" if talent else "Unknown",
            "match_score": match.match_score,
            "skill_match_score": match.skill_match_score,
            "matched_skills": match.matched_skills or [],
            "skill_gaps": match.skill_gaps or [],
            "status": match.status.value,
            "talent_feedback": match.talent_feedback,
            "created_at": match.created_at.isoformat()
        })

    return {
        "job_id": job_id,
        "job_title": job.title,
        "total_matches": len(responses),
        "matches": responses
    }


@router.post("/jobs/{job_id}/find-candidates")
async def find_candidates_for_job(
    job_id: int,
    limit: int = Query(10, ge=1, le=50),
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """
    Generate candidate matches for a job posting.

    Finds top talent matches for the job using semantic matching.
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
            detail="Only the hiring manager who created this job can find candidates"
        )

    # Generate matches
    matching_service = create_agent_matching_service()

    matches = matching_service.find_matches_for_job(
        job=job,
        db=db,
        limit=limit
    )

    # Update job match count
    job.total_matches = len(matches)
    db.commit()

    # Audit log
    audit = AuditLog(
        user_id=current_user.id,
        action="job_candidates_matched",
        details={
            "job_id": job_id,
            "count": len(matches)
        }
    )
    db.add(audit)
    db.commit()

    return {
        "job_id": job_id,
        "total_matches": len(matches),
        "match_ids": [m.id for m in matches],
        "message": f"Found {len(matches)} candidate matches!"
    }
