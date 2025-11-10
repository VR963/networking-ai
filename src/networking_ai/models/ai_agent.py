"""
AIAgent Model - AI Agent Tracking.

Represents AI agents created for users and jobs.
Tracks agent performance and links to the AI agent system.
"""

from datetime import datetime
from enum import Enum
from typing import Dict

from sqlalchemy import Column, Integer, String, Text, Float, Boolean, DateTime, ForeignKey, JSON, Enum as SQLEnum
from sqlalchemy.orm import relationship

from ..database import Base


class AgentType(str, Enum):
    """Type of AI agent."""
    USER_AGENT = "user_agent"  # Represents a job seeker
    JOB_AGENT = "job_agent"  # Represents a job/company
    MASTER_AGENT = "master_agent"  # Master orchestrator
    SUB_AGENT = "sub_agent"  # Specialized sub-agents


class AgentStatus(str, Enum):
    """Agent operational status."""
    ACTIVE = "active"
    INACTIVE = "inactive"
    TRAINING = "training"
    SUSPENDED = "suspended"


class AIAgent(Base):
    """
    AI Agent model.

    Each user and each job gets an AI agent that represents them.
    The Master Agent manages all these agents.
    """
    __tablename__ = "ai_agents"
    __table_args__ = {'extend_existing': True}

    # Primary Key
    id = Column(Integer, primary_key=True, index=True)

    # Owner (either user or job)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=True, index=True)
    # Note: job_id relationship handled via Job.ai_agent_id

    # Agent Info
    agent_type = Column(SQLEnum(AgentType), nullable=False, index=True)
    agent_name = Column(String(255), nullable=True)
    agent_specialization = Column(JSON, nullable=True)  # List of specializations

    # Agent Configuration
    model_version = Column(String(100), default="claude-3-5-sonnet-20241022")
    system_prompt = Column(Text, nullable=True)  # Custom instructions for this agent
    temperature = Column(Float, default=0.7)  # AI creativity level

    # Status
    status = Column(SQLEnum(AgentStatus), default=AgentStatus.ACTIVE, index=True)
    is_learning_enabled = Column(Boolean, default=True)  # Can agent learn from interactions?

    # Performance Metrics
    total_interactions = Column(Integer, default=0)
    successful_matches = Column(Integer, default=0)
    total_applications_generated = Column(Integer, default=0)
    accuracy_score = Column(Float, default=0.0)  # 0.0 to 1.0
    hallucination_count = Column(Integer, default=0)
    reward_points = Column(Integer, default=0)

    # Agent Behavior
    response_quality_score = Column(Float, default=0.0)  # 0.0 to 1.0
    avg_response_time_ms = Column(Float, nullable=True)
    last_training_at = Column(DateTime(timezone=True), nullable=True)

    # Master Agent Supervision
    warnings_issued = Column(Integer, default=0)
    needs_assistance = Column(Boolean, default=False)
    assistance_reason = Column(String(500), nullable=True)

    # Embedding
    agent_profile_embedding = Column(Text, nullable=True)  # Vector representation

    # Timestamps
    created_at = Column(DateTime(timezone=True), default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime(timezone=True), default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    last_active_at = Column(DateTime(timezone=True), nullable=True)

    # Relationships
    user = relationship("User", back_populates="ai_agent")
    # jobs relationship handled via Job.ai_agent_id

    def __repr__(self):
        return f"<AIAgent {self.id} type={self.agent_type.value} user_id={self.user_id}>"

    def calculate_performance_score(self) -> float:
        """Calculate overall performance score (0-100)."""
        if self.total_interactions == 0:
            return 0.0

        # Success rate (40% weight)
        success_rate = (self.successful_matches / self.total_interactions) * 40 if self.total_interactions > 0 else 0

        # Accuracy (30% weight)
        accuracy_component = self.accuracy_score * 30

        # Response quality (20% weight)
        quality_component = self.response_quality_score * 20

        # Hallucination penalty (10% weight)
        hallucination_penalty = min(self.hallucination_count * 2, 10)

        score = success_rate + accuracy_component + quality_component - hallucination_penalty
        return max(0.0, min(100.0, score))

    def to_dict(self) -> Dict:
        """Convert to dictionary."""
        return {
            'id': self.id,
            'user_id': self.user_id,
            'agent_type': self.agent_type.value,
            'agent_name': self.agent_name,
            'agent_specialization': self.agent_specialization,
            'model_version': self.model_version,
            'status': self.status.value,
            'is_learning_enabled': self.is_learning_enabled,
            'total_interactions': self.total_interactions,
            'successful_matches': self.successful_matches,
            'total_applications_generated': self.total_applications_generated,
            'accuracy_score': float(self.accuracy_score),
            'hallucination_count': self.hallucination_count,
            'reward_points': self.reward_points,
            'response_quality_score': float(self.response_quality_score),
            'warnings_issued': self.warnings_issued,
            'needs_assistance': self.needs_assistance,
            'performance_score': self.calculate_performance_score(),
            'created_at': self.created_at.isoformat(),
            'updated_at': self.updated_at.isoformat(),
            'last_active_at': self.last_active_at.isoformat() if self.last_active_at else None,
        }
