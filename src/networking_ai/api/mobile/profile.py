"""
Mobile Profile Router.

Endpoints:
- GET / - Get user profile
- PATCH / - Update profile
- POST /avatar - Upload profile avatar
- POST /resume - Upload resume
"""

from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File
from sqlalchemy.orm import Session
from datetime import datetime
from typing import Optional
import os

from ...database import get_db
from ...models.user import User
from ...models.profile import UserProfile
from ...models.application import Application
from ...models.interview import Interview
from .schemas import (
    ProfileResponse,
    ProfileUpdateRequest,
    ProfileStats,
    ResumeCompact,
    AvatarUploadResponse,
    ResumeUploadResponse,
    ParsedResumeData
)
from .responses import create_success_response, create_error_response, ErrorCode
from .dependencies import mobile_auth_required

profile_router = APIRouter()


def calculate_profile_completeness(user: User, profile: Optional[UserProfile]) -> float:
    """
    Calculate profile completeness score (0.0 - 1.0).

    Factors:
    - Email (always present)
    - Full name (always present)
    - Avatar (10%)
    - Headline (10%)
    - Location (10%)
    - Skills (20%)
    - Experience years (10%)
    - Resume (20%)
    - Profile info (20%)
    """
    score = 0.0

    # Base score for email and name
    score += 0.2  # 20% for having account

    # Avatar
    if profile and profile.profile_picture:
        score += 0.1

    # Headline
    if profile and profile.headline:
        score += 0.1

    # Location
    if profile and profile.location:
        score += 0.1

    # Skills
    if profile and profile.skills and len(profile.skills) > 0:
        score += 0.2

    # Experience years
    if profile and profile.years_of_experience:
        score += 0.1

    # Resume (check if user has uploaded resume)
    # TODO: Check parsed_resume or resume file
    score += 0.0  # Placeholder

    # Profile summary/bio
    if profile and profile.bio:
        score += 0.2

    return min(score, 1.0)


@profile_router.get("/", response_model=dict)
async def get_profile(
    db: Session = Depends(get_db),
    user: User = Depends(mobile_auth_required)
):
    """
    Get user profile with stats.

    Returns complete profile information and activity statistics.
    """
    # Get profile
    profile = db.query(UserProfile).filter(UserProfile.user_id == user.id).first()

    # Calculate stats
    applications_count = db.query(Application).filter(
        Application.talent_user_id == user.id
    ).count()

    interviews_count = db.query(Interview).join(Application).filter(
        Application.talent_user_id == user.id
    ).count()

    # Profile completeness
    completeness = calculate_profile_completeness(user, profile)

    # Build response
    stats = ProfileStats(
        applications_submitted=applications_count,
        interviews_scheduled=interviews_count,
        profile_views=0  # TODO: Implement profile view tracking
    )

    resume_compact = None
    # TODO: Get resume if exists
    # if profile and profile.resume_id:
    #     resume_compact = ResumeCompact(...)

    profile_response = ProfileResponse(
        id=user.id,
        email=user.email,
        full_name=user.full_name,
        role=user.role.value,
        avatar_url=profile.profile_picture if profile else None,
        headline=profile.headline if profile else None,
        location=profile.location if profile else None,
        resume=resume_compact,
        skills=profile.skills if profile and profile.skills else [],
        experience_years=profile.years_of_experience if profile else None,
        profile_completeness=completeness,
        stats=stats
    )

    return create_success_response(
        data=profile_response.model_dump(),
        self_link="/api/v1/mobile/profile"
    )


@profile_router.patch("/", response_model=dict)
async def update_profile(
    request: ProfileUpdateRequest,
    db: Session = Depends(get_db),
    user: User = Depends(mobile_auth_required)
):
    """
    Update user profile.

    Updates profile fields provided in the request.
    """
    # Get or create profile
    profile = db.query(UserProfile).filter(UserProfile.user_id == user.id).first()
    if not profile:
        profile = UserProfile(
            user_id=user.id,
            created_at=datetime.utcnow()
        )
        db.add(profile)

    # Update user fields
    if request.full_name:
        user.full_name = request.full_name

    # Update profile fields
    if request.headline is not None:
        profile.headline = request.headline

    if request.location is not None:
        profile.location = request.location

    if request.skills is not None:
        profile.skills = request.skills

    if request.experience_years is not None:
        profile.years_of_experience = request.experience_years

    profile.updated_at = datetime.utcnow()

    db.commit()
    db.refresh(user)
    db.refresh(profile)

    # Return updated profile
    completeness = calculate_profile_completeness(user, profile)

    applications_count = db.query(Application).filter(
        Application.talent_user_id == user.id
    ).count()

    interviews_count = db.query(Interview).join(Application).filter(
        Application.talent_user_id == user.id
    ).count()

    stats = ProfileStats(
        applications_submitted=applications_count,
        interviews_scheduled=interviews_count,
        profile_views=0
    )

    profile_response = ProfileResponse(
        id=user.id,
        email=user.email,
        full_name=user.full_name,
        role=user.role.value,
        avatar_url=profile.profile_picture,
        headline=profile.headline,
        location=profile.location,
        resume=None,
        skills=profile.skills or [],
        experience_years=profile.years_of_experience,
        profile_completeness=completeness,
        stats=stats
    )

    return create_success_response(
        data=profile_response.model_dump(),
        self_link="/api/v1/mobile/profile"
    )


@profile_router.post("/avatar", response_model=dict, status_code=status.HTTP_200_OK)
async def upload_avatar(
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    user: User = Depends(mobile_auth_required)
):
    """
    Upload profile avatar.

    Accepts image files (JPG, PNG, etc.).
    Returns URL to uploaded avatar.
    """
    # Validate file type
    allowed_types = ["image/jpeg", "image/png", "image/jpg", "image/webp"]
    if file.content_type not in allowed_types:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=create_error_response(
                code=ErrorCode.VALIDATION_ERROR,
                message=f"Invalid file type. Allowed: {', '.join(allowed_types)}"
            )
        )

    # Validate file size (max 5MB)
    max_size = 5 * 1024 * 1024  # 5MB
    content = await file.read()
    if len(content) > max_size:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=create_error_response(
                code=ErrorCode.VALIDATION_ERROR,
                message="File too large. Maximum size: 5MB"
            )
        )

    # TODO: Implement actual file upload to cloud storage (S3, etc.)
    # For now, just return a placeholder URL
    avatar_url = f"https://storage.example.com/avatars/user_{user.id}_{datetime.utcnow().timestamp()}.jpg"

    # Update profile
    profile = db.query(UserProfile).filter(UserProfile.user_id == user.id).first()
    if not profile:
        profile = UserProfile(
            user_id=user.id,
            created_at=datetime.utcnow()
        )
        db.add(profile)

    profile.profile_picture = avatar_url
    profile.updated_at = datetime.utcnow()

    db.commit()

    response = AvatarUploadResponse(avatar_url=avatar_url)

    return create_success_response(
        data=response.model_dump(),
        self_link="/api/v1/mobile/profile/avatar"
    )


@profile_router.post("/resume", response_model=dict, status_code=status.HTTP_201_CREATED)
async def upload_resume(
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    user: User = Depends(mobile_auth_required)
):
    """
    Upload resume/CV.

    Accepts PDF, DOC, DOCX files.
    Triggers resume parsing to extract skills and experience.
    """
    # Validate file type
    allowed_types = [
        "application/pdf",
        "application/msword",
        "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
    ]
    if file.content_type not in allowed_types:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=create_error_response(
                code=ErrorCode.VALIDATION_ERROR,
                message="Invalid file type. Allowed: PDF, DOC, DOCX"
            )
        )

    # Validate file size (max 10MB)
    max_size = 10 * 1024 * 1024  # 10MB
    content = await file.read()
    if len(content) > max_size:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=create_error_response(
                code=ErrorCode.VALIDATION_ERROR,
                message="File too large. Maximum size: 10MB"
            )
        )

    # TODO: Implement actual file upload to cloud storage
    # TODO: Trigger resume parsing service
    # For now, return placeholder data

    resume_id = 1  # Placeholder
    uploaded_at = datetime.utcnow()

    # Simulated parsed data
    parsed_data = ParsedResumeData(
        skills=["Python", "FastAPI", "PostgreSQL"],
        experience_years=5
    )

    response = ResumeUploadResponse(
        id=resume_id,
        filename=file.filename,
        uploaded_at=uploaded_at,
        parsed_data=parsed_data
    )

    return create_success_response(
        data=response.model_dump(),
        self_link="/api/v1/mobile/profile/resume"
    )
