"""
Company Admin Agent Model.

Master AI agent for companies - retains all hiring knowledge.
NOT a personal agent - owned by the company, not an individual.
"""

from datetime import datetime
from sqlalchemy import Column, Integer, String, Float, DateTime, ForeignKey, Enum as SQLEnum
from sqlalchemy.orm import relationship
from enum import Enum

from ..database import Base


class AdminAgentStatus(str, Enum):
    """Status of Company Admin Agent."""
    ACTIVE = "active"
    PAUSED = "paused"
    SUSPENDED = "suspended"  # Subscription expired


class CompanyAdminAgent(Base):
    """
    Company Admin Agent model.

    Master knowledge keeper for company.
    - Stores ALL hiring conversations
    - Retains knowledge when hiring managers leave
    - Monitors all hiring manager agents
    - Provides company-wide insights
    """
    __tablename__ = "company_admin_agents"
    __table_args__ = {'extend_existing': True}

    # Primary key
    id = Column(Integer, primary_key=True, index=True)

    # Ownership
    company_id = Column(Integer, ForeignKey("companies.id"), unique=True, nullable=False)

    # Knowledge base
    company_rag_collection_id = Column(String(255), nullable=False)  # ChromaDB collection

    # Metrics
    total_hiring_managers = Column(Integer, default=0)
    active_hiring_managers = Column(Integer, default=0)
    total_conversations = Column(Integer, default=0)
    total_candidates_contacted = Column(Integer, default=0)
    total_hires = Column(Integer, default=0)
    total_rejections = Column(Integer, default=0)

    # Performance
    average_time_to_hire = Column(Float)  # Days
    success_rate = Column(Float)  # Percentage
    knowledge_version = Column(Integer, default=1)

    # Status
    status = Column(SQLEnum(AdminAgentStatus), default=AdminAgentStatus.ACTIVE, nullable=False)

    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    last_activity_at = Column(DateTime)
    subscription_expires_at = Column(DateTime)  # Mirrors company subscription

    # Relationships
    company = relationship("CompanyV2", back_populates="admin_agent", foreign_keys=[company_id])
    hiring_managers = relationship("HiringManagerRole", back_populates="company_admin_agent")

    def __repr__(self):
        return f"<CompanyAdminAgent(id={self.id}, company_id={self.company_id}, status={self.status})>"

    def record_new_hiring_manager(self):
        """Record that a new hiring manager joined."""
        self.total_hiring_managers += 1
        self.active_hiring_managers += 1
        self.last_activity_at = datetime.utcnow()

    def record_hiring_manager_departure(self):
        """Record that a hiring manager left."""
        if self.active_hiring_managers > 0:
            self.active_hiring_managers -= 1

    def record_conversation(self):
        """Record a new candidate conversation."""
        self.total_conversations += 1
        self.last_activity_at = datetime.utcnow()

    def record_hire(self):
        """Record a successful hire."""
        self.total_hires += 1
        self.update_success_rate()

    def record_rejection(self):
        """Record a rejected candidate."""
        self.total_rejections += 1
        self.update_success_rate()

    def update_success_rate(self):
        """Calculate and update success rate."""
        total_outcomes = self.total_hires + self.total_rejections
        if total_outcomes > 0:
            self.success_rate = (self.total_hires / total_outcomes) * 100

    def is_subscription_active(self) -> bool:
        """Check if subscription is active."""
        if self.status == AdminAgentStatus.SUSPENDED:
            return False
        if not self.subscription_expires_at:
            return False
        return datetime.utcnow() < self.subscription_expires_at

    def get_metrics_summary(self) -> dict:
        """Get comprehensive metrics summary."""
        return {
            "hiring_managers": {
                "total": self.total_hiring_managers,
                "active": self.active_hiring_managers
            },
            "conversations": {
                "total": self.total_conversations,
                "candidates_contacted": self.total_candidates_contacted
            },
            "outcomes": {
                "hires": self.total_hires,
                "rejections": self.total_rejections,
                "success_rate": round(self.success_rate, 2) if self.success_rate else 0
            },
            "performance": {
                "average_time_to_hire_days": round(self.average_time_to_hire, 1) if self.average_time_to_hire else None
            }
        }
