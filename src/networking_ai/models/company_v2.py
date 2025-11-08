"""
Company Model.

Represents organizations that hire talent.
Each company has an Admin Agent and seat licensing.
"""

from datetime import datetime
from sqlalchemy import Column, Integer, String, DateTime, Boolean, ForeignKey, JSON, Enum as SQLEnum
from sqlalchemy.orm import relationship
from enum import Enum

from ..database import Base


class CompanySize(str, Enum):
    """Company size categories."""
    STARTUP = "startup"          # 1-10 employees
    SMALL = "small"              # 11-50
    MEDIUM = "medium"            # 51-200
    LARGE = "large"              # 201-1000
    ENTERPRISE = "enterprise"    # 1000+


class CompanyStatus(str, Enum):
    """Company account status."""
    ACTIVE = "active"
    SUSPENDED = "suspended"
    INACTIVE = "inactive"


class Company(Base):
    """
    Company model.

    Organizations that hire talent through the platform.
    Has Admin Agent for knowledge retention and seat licensing.
    """
    __tablename__ = "companies"

    # Primary key
    id = Column(Integer, primary_key=True, index=True)

    # Company details
    name = Column(String(255), nullable=False, index=True)
    industry = Column(String(100))
    size = Column(SQLEnum(CompanySize))
    description = Column(String(1000))
    website = Column(String(255))

    # Location
    headquarters_location = Column(String(255))
    locations = Column(JSON)  # Multiple office locations

    # Subscription & Licensing
    subscription_tier = Column(String(50))  # solo, team, enterprise
    total_seats_purchased = Column(Integer, default=0)
    hiring_manager_seats_allocated = Column(Integer, default=0)
    hiring_manager_seats_used = Column(Integer, default=0)
    talent_seats_allocated = Column(Integer, default=0)
    talent_seats_used = Column(Integer, default=0)

    # Status
    status = Column(SQLEnum(CompanyStatus), default=CompanyStatus.ACTIVE, nullable=False)

    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    subscription_started_at = Column(DateTime)
    subscription_expires_at = Column(DateTime)

    # Relationships
    admin_agent = relationship("CompanyAdminAgent", back_populates="company", uselist=False)
    hiring_managers = relationship("HiringManagerRole", back_populates="company")
    admin_users = relationship("CompanyAdminUser", back_populates="company")

    def __repr__(self):
        return f"<Company(id={self.id}, name='{self.name}', status={self.status})>"

    def has_available_hiring_manager_seats(self) -> bool:
        """Check if company has available Hiring Manager seats."""
        return self.hiring_manager_seats_used < self.hiring_manager_seats_allocated

    def has_available_talent_seats(self) -> bool:
        """Check if company has available Talent seats."""
        return self.talent_seats_used < self.talent_seats_allocated

    def allocate_hiring_manager_seat(self) -> bool:
        """
        Allocate a Hiring Manager seat.

        Returns:
            True if seat allocated, False if no seats available
        """
        if self.has_available_hiring_manager_seats():
            self.hiring_manager_seats_used += 1
            return True
        return False

    def release_hiring_manager_seat(self):
        """Release a Hiring Manager seat (when HM leaves)."""
        if self.hiring_manager_seats_used > 0:
            self.hiring_manager_seats_used -= 1

    def allocate_talent_seat(self) -> bool:
        """
        Allocate a Talent seat (for employee or sponsorship).

        Returns:
            True if seat allocated, False if no seats available
        """
        if self.has_available_talent_seats():
            self.talent_seats_used += 1
            return True
        return False

    def release_talent_seat(self):
        """Release a Talent seat."""
        if self.talent_seats_used > 0:
            self.talent_seats_used -= 1

    def is_subscription_active(self) -> bool:
        """Check if company subscription is active and not expired."""
        if self.status != CompanyStatus.ACTIVE:
            return False
        if not self.subscription_expires_at:
            return False
        return datetime.utcnow() < self.subscription_expires_at

    def get_available_seats_summary(self) -> dict:
        """Get seat availability summary."""
        return {
            "total_purchased": self.total_seats_purchased,
            "hiring_manager": {
                "allocated": self.hiring_manager_seats_allocated,
                "used": self.hiring_manager_seats_used,
                "available": self.hiring_manager_seats_allocated - self.hiring_manager_seats_used
            },
            "talent": {
                "allocated": self.talent_seats_allocated,
                "used": self.talent_seats_used,
                "available": self.talent_seats_allocated - self.talent_seats_used
            }
        }
