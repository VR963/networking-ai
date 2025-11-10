"""
Match API Endpoints.

Handles viewing and responding to AI-generated matches.
"""

from typing import List
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from ..database import get_db
from ..models.user import User, UserRole
from ..models.match import Match, MatchStatus
from ..models.profile import UserProfile
from ..models.job import Job
from ..api.auth import get_current_user, get_current_active_user


router = APIRouter()


# ============================================================================
# Match Viewing Endpoints
# ============================================================================

@router.get("")
async def get_my_matches(
    status_filter: str = None,
    min_score: float = None,
    limit: int = 20,
    offset: int = 0,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    """
    Get matches for current user.

    For job seekers: Returns job matches
    For companies: Returns candidate matches
    """
    if current_user.role == UserRole.JOB_SEEKER:
        # Get user's profile
        profile = db.query(UserProfile).filter(UserProfile.user_id == current_user.id).first()

        if not profile:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Profile not found. Create a profile first.",
            )

        # Get matches for this profile
        matches_query = db.query(Match).filter(Match.profile_id == profile.id)

    elif current_user.role == UserRole.COMPANY:
        # Get all jobs for this company
        from ..models.company import Company
        company = db.query(Company).filter(Company.user_id == current_user.id).first()

        if not company:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Company not found.",
            )

        # Get matches for company's jobs
        job_ids = [job.id for job in company.jobs]
        matches_query = db.query(Match).filter(Match.job_id.in_(job_ids))

    else:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only job seekers and companies can view matches.",
        )

    # Apply filters
    if status_filter:
        matches_query = matches_query.filter(Match.status == status_filter)

    if min_score is not None:
        matches_query = matches_query.filter(Match.match_score >= min_score)

    # Get total count
    total = matches_query.count()

    # Apply pagination and sorting
    matches = matches_query.order_by(
        Match.match_score.desc(),
        Match.created_at.desc()
    ).offset(offset).limit(limit).all()

    # Format response
    result = []
    for match in matches:
        if current_user.role == UserRole.JOB_SEEKER:
            # Return job info
            result.append({
                "match_id": match.id,
                "match_score": float(match.match_score),
                "confidence_level": match.confidence_level,
                "status": match.status.value,
                "job": {
                    "id": match.job.id,
                    "title": match.job.title,
                    "company_name": match.job.company.company_name,
                    "location": match.job.location,
                    "job_type": match.job.job_type.value,
                    "is_remote": match.job.is_remote,
                    "salary_min": match.job.salary_min,
                    "salary_max": match.job.salary_max,
                },
                "ai_explanation": match.ai_explanation,
                "matching_skills": match.matching_skills,
                "skill_gaps": match.skill_gaps,
                "salary_alignment": match.salary_alignment,
                "location_compatibility": match.location_compatibility,
                "created_at": match.created_at.isoformat(),
                "viewed_at": match.viewed_at.isoformat() if match.viewed_at else None,
            })
        else:
            # Return candidate info
            result.append({
                "match_id": match.id,
                "match_score": float(match.match_score),
                "confidence_level": match.confidence_level,
                "status": match.status.value,
                "candidate": {
                    "id": match.profile.user_id,
                    "name": match.profile.user.full_name,
                    "headline": match.profile.headline,
                    "location": match.profile.location,
                    "current_title": match.profile.current_title,
                    "years_of_experience": match.profile.years_of_experience,
                    "skills": match.profile.skills,
                },
                "job": {
                    "id": match.job.id,
                    "title": match.job.title,
                },
                "ai_explanation": match.ai_explanation,
                "matching_skills": match.matching_skills,
                "skill_gaps": match.skill_gaps,
                "created_at": match.created_at.isoformat(),
                "viewed_at": match.viewed_at.isoformat() if match.viewed_at else None,
            })

    return {
        "total": total,
        "matches": result,
        "limit": limit,
        "offset": offset,
    }


@router.get("/{match_id}")
async def get_match(
    match_id: int,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    """
    Get detailed match information.

    Marks match as viewed if not already viewed.
    """
    match = db.query(Match).filter(Match.id == match_id).first()

    if not match:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Match not found.",
        )

    # Check permission
    if current_user.role == UserRole.JOB_SEEKER:
        # Check if match belongs to user's profile
        profile = db.query(UserProfile).filter(UserProfile.user_id == current_user.id).first()
        if not profile or match.profile_id != profile.id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You don't have permission to view this match.",
            )

    elif current_user.role == UserRole.COMPANY:
        # Check if match belongs to company's job
        from ..models.company import Company
        company = db.query(Company).filter(Company.user_id == current_user.id).first()
        if not company:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Company not found.",
            )

        job = db.query(Job).filter(Job.id == match.job_id).first()
        if not job or job.company_id != company.id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You don't have permission to view this match.",
            )

    # Mark as viewed
    if match.status == MatchStatus.PENDING:
        match.status = MatchStatus.VIEWED
        match.viewed_at = datetime.utcnow()
        db.commit()

    # Return detailed info
    return {
        "match_id": match.id,
        "match_score": float(match.match_score),
        "confidence_level": match.confidence_level,
        "status": match.status.value,
        "ai_explanation": match.ai_explanation,
        "matching_skills": match.matching_skills,
        "skill_gaps": match.skill_gaps,
        "salary_alignment": match.salary_alignment,
        "location_compatibility": match.location_compatibility,
        "created_by_agent": match.created_by_agent,
        "match_strategy": match.match_strategy,
        "created_at": match.created_at.isoformat(),
        "viewed_at": match.viewed_at.isoformat() if match.viewed_at else None,
        "profile": match.profile.to_dict() if current_user.role == UserRole.COMPANY else None,
        "job": match.job.to_dict() if current_user.role == UserRole.JOB_SEEKER else None,
    }


# ============================================================================
# Match Action Endpoints
# ============================================================================

@router.post("/{match_id}/accept")
async def accept_match(
    match_id: int,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    """
    Accept a match (show interest).

    For job seekers: Indicates interest in the job
    For companies: Indicates interest in the candidate
    """
    match = db.query(Match).filter(Match.id == match_id).first()

    if not match:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Match not found.",
        )

    # Check permission (same as get_match)
    if current_user.role == UserRole.JOB_SEEKER:
        profile = db.query(UserProfile).filter(UserProfile.user_id == current_user.id).first()
        if not profile or match.profile_id != profile.id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You don't have permission to modify this match.",
            )

    elif current_user.role == UserRole.COMPANY:
        from ..models.company import Company
        company = db.query(Company).filter(Company.user_id == current_user.id).first()
        job = db.query(Job).filter(Job.id == match.job_id).first()
        if not company or not job or job.company_id != company.id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You don't have permission to modify this match.",
            )

    # Update match status
    match.status = MatchStatus.ACCEPTED
    match.responded_at = datetime.utcnow()

    db.commit()

    print(f"[MATCH] Match {match_id} accepted by user {current_user.id}")

    return {
        "message": "Match accepted successfully",
        "match_id": match_id,
        "status": match.status.value,
    }


@router.post("/{match_id}/reject")
async def reject_match(
    match_id: int,
    feedback: str = None,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    """
    Reject a match (not interested).

    Optional feedback helps improve AI matching.
    """
    match = db.query(Match).filter(Match.id == match_id).first()

    if not match:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Match not found.",
        )

    # Check permission
    if current_user.role == UserRole.JOB_SEEKER:
        profile = db.query(UserProfile).filter(UserProfile.user_id == current_user.id).first()
        if not profile or match.profile_id != profile.id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You don't have permission to modify this match.",
            )

    elif current_user.role == UserRole.COMPANY:
        from ..models.company import Company
        company = db.query(Company).filter(Company.user_id == current_user.id).first()
        job = db.query(Job).filter(Job.id == match.job_id).first()
        if not company or not job or job.company_id != company.id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You don't have permission to modify this match.",
            )

    # Update match status
    match.status = MatchStatus.REJECTED
    match.responded_at = datetime.utcnow()

    if feedback:
        match.user_feedback = feedback

    db.commit()

    print(f"[MATCH] Match {match_id} rejected by user {current_user.id}")

    return {
        "message": "Match rejected. Thanks for your feedback!",
        "match_id": match_id,
        "status": match.status.value,
    }


# ============================================================================
# Match Statistics
# ============================================================================

@router.get("/stats/summary")
async def get_match_stats(
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    """Get match statistics summary for current user."""
    if current_user.role == UserRole.JOB_SEEKER:
        profile = db.query(UserProfile).filter(UserProfile.user_id == current_user.id).first()

        if not profile:
            return {
                "total_matches": 0,
                "pending": 0,
                "viewed": 0,
                "accepted": 0,
                "rejected": 0,
            }

        matches = db.query(Match).filter(Match.profile_id == profile.id).all()

    elif current_user.role == UserRole.COMPANY:
        from ..models.company import Company
        company = db.query(Company).filter(Company.user_id == current_user.id).first()

        if not company:
            return {
                "total_matches": 0,
                "pending": 0,
                "viewed": 0,
                "accepted": 0,
                "rejected": 0,
            }

        job_ids = [job.id for job in company.jobs]
        matches = db.query(Match).filter(Match.job_id.in_(job_ids)).all()

    else:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only job seekers and companies can view match stats.",
        )

    # Calculate stats
    stats = {
        "total_matches": len(matches),
        "pending": len([m for m in matches if m.status == MatchStatus.PENDING]),
        "viewed": len([m for m in matches if m.status == MatchStatus.VIEWED]),
        "accepted": len([m for m in matches if m.status == MatchStatus.ACCEPTED]),
        "rejected": len([m for m in matches if m.status == MatchStatus.REJECTED]),
        "applied": len([m for m in matches if m.status == MatchStatus.APPLIED]),
    }

    if matches:
        stats["average_match_score"] = sum(m.match_score for m in matches) / len(matches)
        stats["highest_match_score"] = max(m.match_score for m in matches)

    return stats
