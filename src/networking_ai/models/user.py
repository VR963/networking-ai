"""
User Model - Authentication and basic user data.

Represents both job seekers and company users.
"""

from datetime import datetime
from enum import Enum
from typing import Optional, List

from sqlalchemy import Column, Integer, String, Boolean, DateTime, Enum as SQLEnum
from sqlalchemy.orm import relationship

from ..database import Base


class UserRole(str, Enum):
    """User role types."""
    JOB_SEEKER = "job_seeker"  # Legacy - same as TALENT
    TALENT = "talent"  # Job seeker / candidate
    COMPANY = "company"  # Legacy - company user
    HIRING_MANAGER = "hiring_manager"  # Hiring manager at a company
    COMPANY_ADMIN = "company_admin"  # Company administrator
    ADMIN = "admin"  # Platform administrator


class AccountStatus(str, Enum):
    """Account status."""
    ACTIVE = "active"
    INACTIVE = "inactive"
    SUSPENDED = "suspended"
    DELETED = "deleted"
    PENDING_VERIFICATION = "pending_verification"


class User(Base):
    """
    User model for authentication and basic account data.

    This is the core user table that handles authentication.
    Job seekers will have a UserProfile, companies will have a Company record.
    """
    __tablename__ = "users"

    # Primary Key
    id = Column(Integer, primary_key=True, index=True)

    # Authentication
    email = Column(String(255), unique=True, index=True, nullable=False)
    hashed_password = Column(String(255), nullable=False)
    is_email_verified = Column(Boolean, default=False)
    email_verification_token = Column(String(255), nullable=True)

    # Basic Info
    first_name = Column(String(100))  # Phase 2
    last_name = Column(String(100))  # Phase 2
    full_name = Column(String(255), nullable=False)
    role = Column(SQLEnum(UserRole), nullable=False, index=True)
    status = Column(SQLEnum(AccountStatus), default=AccountStatus.PENDING_VERIFICATION, index=True)

    # Security
    is_active = Column(Boolean, default=True)
    is_superuser = Column(Boolean, default=False)
    last_login = Column(DateTime(timezone=True), nullable=True)
    password_reset_token = Column(String(255), nullable=True)
    password_reset_expires = Column(DateTime(timezone=True), nullable=True)

    # Timestamps
    created_at = Column(DateTime(timezone=True), default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime(timezone=True), default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    deleted_at = Column(DateTime(timezone=True), nullable=True)

    # Relationships
    profile = relationship("UserProfile", back_populates="user", uselist=False, cascade="all, delete-orphan")
    company = relationship("Company", back_populates="user", uselist=False, cascade="all, delete-orphan")
    applications = relationship("Application", foreign_keys="Application.talent_user_id", back_populates="user", cascade="all, delete-orphan")
    sent_messages = relationship("Message", foreign_keys="Message.sender_id", back_populates="sender", cascade="all, delete-orphan")
    conversations_initiated = relationship("Conversation", foreign_keys="Conversation.user1_id", back_populates="user1")
    conversations_received = relationship("Conversation", foreign_keys="Conversation.user2_id", back_populates="user2")
    ai_agent = relationship("AIAgent", back_populates="user", uselist=False, cascade="all, delete-orphan")

    # New: Personal AI Agent for agent marketplace
    personal_agent = relationship("PersonalAIAgent", back_populates="user", uselist=False, cascade="all, delete-orphan")

    def __repr__(self):
        return f"<User {self.email} ({self.role.value})>"

    def to_dict(self):
        """Convert to dictionary."""
        return {
            'id': self.id,
            'email': self.email,
            'full_name': self.full_name,
            'role': self.role.value,
            'status': self.status.value,
            'is_email_verified': self.is_email_verified,
            'is_active': self.is_active,
            'last_login': self.last_login.isoformat() if self.last_login else None,
            'created_at': self.created_at.isoformat(),
        }
