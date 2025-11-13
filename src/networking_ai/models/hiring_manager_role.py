"""
Hiring Manager Role Model.

Links users to companies as hiring managers.
Tracks employment relationship and agent connections.
"""

from datetime import datetime
from sqlalchemy import Column, Integer, DateTime, Boolean, ForeignKey
from sqlalchemy.orm import relationship

from ..database import Base


class HiringManagerRole(Base):
    """
    Hiring Manager Role model.

    Links:
    - User (the person)
    - Company (where they work)
    - Hiring Manager Agent (their personal hiring style)
    - Company Admin Agent (company knowledge keeper)

    When hiring manager leaves:
    - This record is deactivated
    - Their agent goes with them (if subscription active)
    - Company retains knowledge in Admin Agent
    """
    __tablename__ = "hiring_manager_roles"
    __table_args__ = {'extend_existing': True}

    # Primary key
    id = Column(Integer, primary_key=True, index=True)

    # Links
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    company_id = Column(Integer, ForeignKey("companies.id"), nullable=False, index=True)
    hiring_manager_agent_id = Column(Integer, ForeignKey("personal_ai_agents.id"), nullable=False)
    company_admin_agent_id = Column(Integer, ForeignKey("company_admin_agents.id"), nullable=False)

    # Employment status
    is_active = Column(Boolean, default=True, nullable=False)

    # Timestamps
    joined_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    left_at = Column(DateTime)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    user = relationship("User")
    company = relationship("CompanyLegacy", back_populates="hiring_managers")
    hiring_manager_agent = relationship("PersonalAIAgent")
    company_admin_agent = relationship("CompanyAdminAgent", back_populates="hiring_managers")

    def __repr__(self):
        return f"<HiringManagerRole(id={self.id}, user_id={self.user_id}, company_id={self.company_id}, active={self.is_active})>"

    def deactivate(self):
        """
        Deactivate hiring manager role (they left company).

        Agent goes with them, but company retains knowledge.
        """
        self.is_active = False
        self.left_at = datetime.utcnow()

    def reactivate(self):
        """Reactivate role (rehired or returned)."""
        self.is_active = True
        self.left_at = None
