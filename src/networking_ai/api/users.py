"""
User and Profile API Endpoints.

Handles user profile creation, updates, and CV upload.
"""

from typing import List
from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File
from sqlalchemy.orm import Session

from ..database import get_db, SessionLocal
from ..models.user import User, UserRole
from ..models.profile import UserProfile
from ..models.company import Company
from ..schemas.profile import (
    ProfileCreateRequest,
    ProfileUpdateRequest,
    ProfileResponse,
    ProfileSummaryResponse,
    ProfileWorkExperienceRequest,
    ProfileEducationRequest,
)
from ..schemas.user import UserResponse
from ..api.auth import get_current_user, get_current_active_user
from ..services.background_tasks import task_manager, run_matching_for_profile


router = APIRouter()


# ============================================================================
# Profile Endpoints
# ============================================================================

@router.post("/me/profile", response_model=ProfileResponse, status_code=status.HTTP_201_CREATED)
async def create_my_profile(
    profile_data: ProfileCreateRequest,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    """
    Create profile for current user (job seekers only).

    Requires user to be a job seeker role.
    """
    # Check if user is job seeker
    if current_user.role != UserRole.JOB_SEEKER:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only job seekers can create profiles. Companies should use company endpoints.",
        )

    # Check if profile already exists
    existing_profile = db.query(UserProfile).filter(UserProfile.user_id == current_user.id).first()
    if existing_profile:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Profile already exists. Use PUT to update.",
        )

    # Create profile
    profile = UserProfile(
        user_id=current_user.id,
        **profile_data.model_dump()
    )

    # Calculate completion percentage
    profile.calculate_completion_percentage()

    db.add(profile)
    db.commit()
    db.refresh(profile)

    print(f"[PROFILE] Created profile for user {current_user.id}")

    # Trigger background matching for this profile
    task_id = task_manager.submit_task(
        func=run_matching_for_profile,
        args=(profile.id, SessionLocal)
    )
    print(f"[PROFILE] Submitted matching task {task_id} for profile {profile.id}")

    return profile


@router.get("/me/profile", response_model=ProfileResponse)
async def get_my_profile(
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    """Get current user's profile."""
    profile = db.query(UserProfile).filter(UserProfile.user_id == current_user.id).first()

    if not profile:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Profile not found. Create a profile first.",
        )

    return profile


@router.put("/me/profile", response_model=ProfileResponse)
async def update_my_profile(
    profile_data: ProfileUpdateRequest,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    """Update current user's profile."""
    profile = db.query(UserProfile).filter(UserProfile.user_id == current_user.id).first()

    if not profile:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Profile not found. Create a profile first.",
        )

    # Update fields
    update_data = profile_data.dict(exclude_unset=True)
    for field, value in update_data.items():
        setattr(profile, field, value)

    # Recalculate completion percentage
    profile.calculate_completion_percentage()

    db.commit()
    db.refresh(profile)

    print(f"[PROFILE] Updated profile for user {current_user.id}")

    # Trigger background matching to refresh matches with updated profile
    task_id = task_manager.submit_task(
        func=run_matching_for_profile,
        args=(profile.id, SessionLocal)
    )
    print(f"[PROFILE] Submitted matching task {task_id} for updated profile {profile.id}")

    return profile


@router.put("/me/profile/work-experience", response_model=ProfileResponse)
async def update_work_experience(
    work_exp_data: ProfileWorkExperienceRequest,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    """Update work experience."""
    profile = db.query(UserProfile).filter(UserProfile.user_id == current_user.id).first()

    if not profile:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Profile not found.",
        )

    # Convert to dict
    profile.work_experience = [exp.model_dump() for exp in work_exp_data.work_experience]
    profile.calculate_completion_percentage()

    db.commit()
    db.refresh(profile)

    # Trigger background matching for updated profile
    task_id = task_manager.submit_task(
        func=run_matching_for_profile,
        args=(profile.id, SessionLocal)
    )
    print(f"[PROFILE] Submitted matching task {task_id} for profile {profile.id} (work experience updated)")

    return profile


@router.put("/me/profile/education", response_model=ProfileResponse)
async def update_education(
    education_data: ProfileEducationRequest,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    """Update education."""
    profile = db.query(UserProfile).filter(UserProfile.user_id == current_user.id).first()

    if not profile:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Profile not found.",
        )

    # Convert to dict
    profile.education = [edu.model_dump() for edu in education_data.education]
    profile.calculate_completion_percentage()

    db.commit()
    db.refresh(profile)

    return profile


@router.post("/me/cv-upload")
async def upload_cv(
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    """
    Upload CV/Resume file.

    Accepts PDF, DOC, DOCX files.
    TODO: Implement actual file upload to S3 and CV parsing.
    """
    # Validate file type
    allowed_types = ["application/pdf", "application/msword", "application/vnd.openxmlformats-officedocument.wordprocessingml.document"]

    if file.content_type not in allowed_types:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid file type. Only PDF, DOC, DOCX allowed.",
        )

    # Get profile
    profile = db.query(UserProfile).filter(UserProfile.user_id == current_user.id).first()

    if not profile:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Profile not found. Create a profile first.",
        )

    # TODO: Upload to S3
    # For now, just save filename
    # file_content = await file.read()
    # s3_url = upload_to_s3(file_content, file.filename)

    # Placeholder
    from datetime import datetime
    profile.cv_url = f"uploads/cvs/{current_user.id}/{file.filename}"
    profile.cv_uploaded_at = datetime.utcnow()

    # TODO: Parse CV content
    # cv_text = parse_cv(file_content)
    # profile.cv_text = cv_text

    # TODO: Extract skills from CV using AI
    # skills = extract_skills_from_cv(cv_text)
    # profile.skills = skills

    profile.calculate_completion_percentage()

    db.commit()
    db.refresh(profile)

    print(f"[PROFILE] CV uploaded for user {current_user.id}")

    return {
        "message": "CV uploaded successfully",
        "cv_url": profile.cv_url,
        "profile_completion": profile.profile_completion_percentage,
    }


@router.get("/{user_id}/profile", response_model=ProfileResponse)
async def get_user_profile(
    user_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Get another user's profile (public info only).

    Respects visibility settings.
    """
    profile = db.query(UserProfile).filter(UserProfile.user_id == user_id).first()

    if not profile:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Profile not found.",
        )

    # Check visibility
    from ..models.profile import ProfileVisibility

    if profile.visibility == ProfileVisibility.PRIVATE:
        # Only owner can see private profiles
        if current_user.id != user_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Profile is private.",
            )

    # TODO: Implement CONNECTIONS_ONLY logic
    # if profile.visibility == ProfileVisibility.CONNECTIONS_ONLY:
    #     if not are_connected(current_user.id, user_id):
    #         raise HTTPException(403, "Profile is only visible to connections")

    return profile


# ============================================================================
# User Info Endpoints
# ============================================================================

@router.get("/me", response_model=UserResponse)
async def get_current_user_info(
    current_user: User = Depends(get_current_user),
):
    """Get current user information (same as /api/auth/me)."""
    return current_user
