"""
Company Model - Company/Employer Accounts.

Represents companies that post jobs and hire talent.
"""

from datetime import datetime
from enum import Enum
from typing import Dict

from sqlalchemy import Column, Integer, String, Text, DateTime, ForeignKey, JSON, Enum as SQLEnum
from sqlalchemy.orm import relationship

from ..database import Base


class CompanyStatus(str, Enum):
    """Company account status."""
    ACTIVE = "active"
    PENDING_VERIFICATION = "pending_verification"
    VERIFIED = "verified"
    SUSPENDED = "suspended"


class CompanySize(str, Enum):
    """Company size ranges."""
    STARTUP = "1-10"
    SMALL = "11-50"
    MEDIUM = "51-200"
    LARGE = "201-1000"
    ENTERPRISE = "1000+"


class CompanyLegacy(Base):
    """
    Company model for employers (LEGACY - use CompanyV2 for new code).

    Companies post jobs and use AI agents to find matching candidates.
    """
    __tablename__ = "companies"
    __table_args__ = {'extend_existing': True}

    # Primary Key
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, unique=True, index=True)

    # Basic Info
    company_name = Column(String(255), nullable=False, index=True)
    company_description = Column(Text, nullable=True)
    industry = Column(String(255), nullable=True, index=True)
    company_size = Column(SQLEnum(CompanySize), nullable=True)
    founded_year = Column(Integer, nullable=True)

    # Contact Info
    website = Column(String(500), nullable=True)
    linkedin_url = Column(String(500), nullable=True)
    headquarters_location = Column(String(255), nullable=True)
    locations = Column(JSON, nullable=True)  # List of office locations

    # Company Details
    logo_url = Column(String(500), nullable=True)
    cover_image_url = Column(String(500), nullable=True)
    benefits = Column(JSON, nullable=True)  # List of benefits
    culture_highlights = Column(JSON, nullable=True)  # Company culture points

    # AI Profile
    company_embedding = Column(Text, nullable=True)  # Semantic embedding

    # Status
    status = Column(SQLEnum(CompanyStatus), default=CompanyStatus.PENDING_VERIFICATION, index=True)
    verification_document_url = Column(String(500), nullable=True)

    # Stats
    total_jobs_posted = Column(Integer, default=0)
    total_hires = Column(Integer, default=0)
    active_jobs = Column(Integer, default=0)

    # Timestamps
    created_at = Column(DateTime(timezone=True), default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime(timezone=True), default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    # Relationships
    user = relationship("User")  # back_populates removed due to Company model conflict
    jobs = relationship("Job", back_populates="company", cascade="all, delete-orphan")
    admin_agent = relationship("CompanyAdminAgent", back_populates="company", uselist=False, cascade="all, delete-orphan")
    hiring_managers = relationship("HiringManagerRole", back_populates="company", cascade="all, delete-orphan")
    admin_users = relationship("CompanyAdminUser", back_populates="company", cascade="all, delete-orphan")

    def __repr__(self):
        return f"<Company {self.company_name}>"

    def to_dict(self) -> Dict:
        """Convert to dictionary."""
        return {
            'id': self.id,
            'user_id': self.user_id,
            'company_name': self.company_name,
            'company_description': self.company_description,
            'industry': self.industry,
            'company_size': self.company_size.value if self.company_size else None,
            'founded_year': self.founded_year,
            'website': self.website,
            'linkedin_url': self.linkedin_url,
            'headquarters_location': self.headquarters_location,
            'locations': self.locations,
            'logo_url': self.logo_url,
            'cover_image_url': self.cover_image_url,
            'benefits': self.benefits,
            'culture_highlights': self.culture_highlights,
            'status': self.status.value,
            'total_jobs_posted': self.total_jobs_posted,
            'total_hires': self.total_hires,
            'active_jobs': self.active_jobs,
            'created_at': self.created_at.isoformat(),
            'updated_at': self.updated_at.isoformat(),
        }
