"""
Authentication API Endpoints.

Handles user registration, login, password reset, email verification.
"""

from datetime import datetime, timedelta
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from sqlalchemy.orm import Session

from ..database import get_db
from ..models.user import User, UserRole, AccountStatus
from ..models.profile import UserProfile
from ..models.company import Company
from ..models.ai_agent import AIAgent, AgentType
from ..schemas.user import (
    UserRegisterRequest,
    UserLoginRequest,
    TokenResponse,
    UserResponse,
    MessageResponse,
    PasswordResetRequest,
    PasswordResetConfirm,
)
from ..security import (
    hash_password,
    verify_password,
    create_access_token,
    create_refresh_token,
    decode_token,
    generate_verification_token,
    generate_password_reset_token,
)


router = APIRouter()


# OAuth2 scheme for JWT tokens
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/auth/login")


# ============================================================================
# Dependencies
# ============================================================================

async def get_current_user(
    token: str = Depends(oauth2_scheme),
    db: Session = Depends(get_db),
) -> User:
    """
    Get current authenticated user from JWT token.

    Args:
        token: JWT token from Authorization header
        db: Database session

    Returns:
        Current user

    Raises:
        HTTPException: If token is invalid or user not found
    """
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )

    # Decode token
    payload = decode_token(token)
    if payload is None:
        raise credentials_exception

    user_id: int = payload.get("sub")
    if user_id is None:
        raise credentials_exception

    # Get user from database
    user = db.query(User).filter(User.id == user_id).first()
    if user is None:
        raise credentials_exception

    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="User account is inactive",
        )

    return user


async def get_current_active_user(
    current_user: User = Depends(get_current_user),
) -> User:
    """Get current active user (requires email verification)."""
    if current_user.status == AccountStatus.PENDING_VERIFICATION:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Email not verified. Please verify your email to access this resource.",
        )

    return current_user


# ============================================================================
# Endpoints
# ============================================================================

@router.post("/register", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
async def register(
    user_data: UserRegisterRequest,
    db: Session = Depends(get_db),
):
    """
    Register a new user.

    Creates user account, profile (for job seekers) or company (for companies),
    and AI agent.
    """
    # Check if email already exists
    existing_user = db.query(User).filter(User.email == user_data.email).first()
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email already registered",
        )

    # Create user
    user = User(
        email=user_data.email,
        hashed_password=hash_password(user_data.password),
        full_name=user_data.full_name,
        role=user_data.role,
        status=AccountStatus.PENDING_VERIFICATION,
        email_verification_token=generate_verification_token(),
    )

    db.add(user)
    db.commit()
    db.refresh(user)

    # Create profile or company based on role
    if user_data.role in (UserRole.JOB_SEEKER, UserRole.TALENT):
        # Create user profile for talent/job seekers
        profile = UserProfile(user_id=user.id)
        db.add(profile)
    # Note: Company accounts should use the dedicated company registration endpoint
    # elif user_data.role == UserRole.COMPANY:
    #     # Create company
    #     company = Company(
    #         user_id=user.id,
    #         company_name=user_data.full_name,  # Will be updated later
    #     )
    #     db.add(company)

    # Create AI agent for this user (only for talent users)
    if user_data.role in (UserRole.JOB_SEEKER, UserRole.TALENT):
        ai_agent = AIAgent(
            user_id=user.id,
            agent_type=AgentType.USER_AGENT,
            agent_name=f"Agent for {user_data.full_name}",
            status="active",
        )
        db.add(ai_agent)

    db.commit()

    # TODO: Send verification email
    # send_verification_email(user.email, user.email_verification_token)

    print(f"[AUTH] New user registered: {user.email} ({user.role.value})")

    return user


@router.post("/login", response_model=TokenResponse)
async def login(
    credentials: UserLoginRequest,
    db: Session = Depends(get_db),
):
    """
    Login with email and password.

    Returns JWT access token and refresh token.
    """
    # Find user by email
    user = db.query(User).filter(User.email == credentials.email).first()

    if not user or not verify_password(credentials.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )

    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Account is inactive",
        )

    # Update last login
    user.last_login = datetime.utcnow()
    db.commit()

    # Create tokens
    access_token = create_access_token(data={"sub": user.id})
    refresh_token = create_refresh_token(data={"sub": user.id})

    print(f"[AUTH] User logged in: {user.email}")

    return TokenResponse(
        access_token=access_token,
        refresh_token=refresh_token,
        user=user,
    )


@router.post("/login/form", response_model=TokenResponse)
async def login_form(
    form_data: OAuth2PasswordRequestForm = Depends(),
    db: Session = Depends(get_db),
):
    """
    Login using OAuth2 password flow (for Swagger UI).

    Args:
        form_data: username=email, password=password

    Returns:
        Token response
    """
    # Use email as username
    credentials = UserLoginRequest(email=form_data.username, password=form_data.password)
    return await login(credentials, db)


@router.get("/me", response_model=UserResponse)
async def get_current_user_info(
    current_user: User = Depends(get_current_user),
):
    """Get current user information."""
    return current_user


@router.post("/verify-email/{token}", response_model=MessageResponse)
async def verify_email(
    token: str,
    db: Session = Depends(get_db),
):
    """
    Verify user email with token.

    Args:
        token: Email verification token sent via email

    Returns:
        Success message
    """
    user = db.query(User).filter(User.email_verification_token == token).first()

    if not user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid verification token",
        )

    # Mark email as verified
    user.is_email_verified = True
    user.email_verification_token = None
    user.status = AccountStatus.ACTIVE
    db.commit()

    print(f"[AUTH] Email verified: {user.email}")

    return MessageResponse(message="Email verified successfully")


@router.post("/forgot-password", response_model=MessageResponse)
async def forgot_password(
    request: PasswordResetRequest,
    db: Session = Depends(get_db),
):
    """
    Request password reset.

    Sends password reset email with token.
    """
    user = db.query(User).filter(User.email == request.email).first()

    if user:
        # Generate reset token
        user.password_reset_token = generate_password_reset_token()
        user.password_reset_expires = datetime.utcnow() + timedelta(hours=24)
        db.commit()

        # TODO: Send password reset email
        # send_password_reset_email(user.email, user.password_reset_token)

        print(f"[AUTH] Password reset requested: {user.email}")

    # Always return success to prevent email enumeration
    return MessageResponse(message="If email exists, password reset link has been sent")


@router.post("/reset-password", response_model=MessageResponse)
async def reset_password(
    request: PasswordResetConfirm,
    db: Session = Depends(get_db),
):
    """
    Reset password with token.

    Args:
        request: Token and new password

    Returns:
        Success message
    """
    user = db.query(User).filter(User.password_reset_token == request.token).first()

    if not user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid reset token",
        )

    # Check if token expired
    if user.password_reset_expires < datetime.utcnow():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Reset token has expired",
        )

    # Update password
    user.hashed_password = hash_password(request.new_password)
    user.password_reset_token = None
    user.password_reset_expires = None
    db.commit()

    print(f"[AUTH] Password reset: {user.email}")

    return MessageResponse(message="Password reset successfully")


@router.post("/refresh", response_model=TokenResponse)
async def refresh_token(
    refresh_token: str,
    db: Session = Depends(get_db),
):
    """
    Refresh access token using refresh token.

    Args:
        refresh_token: Refresh token

    Returns:
        New token pair
    """
    payload = decode_token(refresh_token)
    if payload is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid refresh token",
        )

    user_id = payload.get("sub")
    user = db.query(User).filter(User.id == user_id).first()

    if not user or not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found or inactive",
        )

    # Create new tokens
    new_access_token = create_access_token(data={"sub": user.id})
    new_refresh_token = create_refresh_token(data={"sub": user.id})

    return TokenResponse(
        access_token=new_access_token,
        refresh_token=new_refresh_token,
        user=user,
    )
