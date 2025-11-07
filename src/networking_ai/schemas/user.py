"""
User Pydantic Schemas for API request/response validation.
"""

from datetime import datetime
from typing import Optional
from pydantic import BaseModel, EmailStr, Field, validator

from ..models.user import UserRole, AccountStatus


# ============================================================================
# Request Schemas
# ============================================================================

class UserRegisterRequest(BaseModel):
    """User registration request."""
    email: EmailStr
    password: str = Field(..., min_length=8, max_length=100)
    full_name: str = Field(..., min_length=1, max_length=255)
    role: UserRole

    @validator('password')
    def password_strength(cls, v):
        """Validate password strength."""
        if not any(c.isupper() for c in v):
            raise ValueError('Password must contain at least one uppercase letter')
        if not any(c.islower() for c in v):
            raise ValueError('Password must contain at least one lowercase letter')
        if not any(c.isdigit() for c in v):
            raise ValueError('Password must contain at least one digit')
        return v


class UserLoginRequest(BaseModel):
    """User login request."""
    email: EmailStr
    password: str


class PasswordResetRequest(BaseModel):
    """Password reset request (forgot password)."""
    email: EmailStr


class PasswordResetConfirm(BaseModel):
    """Confirm password reset with token."""
    token: str
    new_password: str = Field(..., min_length=8, max_length=100)


class UserUpdateRequest(BaseModel):
    """Update user information."""
    full_name: Optional[str] = Field(None, min_length=1, max_length=255)
    # Add more updatable fields as needed


# ============================================================================
# Response Schemas
# ============================================================================

class UserResponse(BaseModel):
    """User response (public info only)."""
    id: int
    email: EmailStr
    full_name: str
    role: UserRole
    status: AccountStatus
    is_email_verified: bool
    is_active: bool
    last_login: Optional[datetime]
    created_at: datetime

    class Config:
        orm_mode = True


class TokenResponse(BaseModel):
    """JWT token response."""
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    user: UserResponse


class MessageResponse(BaseModel):
    """Generic message response."""
    message: str
    success: bool = True
