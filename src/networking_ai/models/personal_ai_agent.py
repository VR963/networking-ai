"""
Personal AI Agent Model.

Each user has a personal AI agent that represents them in the marketplace.
The agent learns from conversations and evolves over time.
"""

from datetime import datetime
from sqlalchemy import Column, Integer, String, Float, DateTime, ForeignKey, Enum as SQLEnum, Text
from sqlalchemy.orm import relationship
from enum import Enum

from ..database import Base


class AgentType(str, Enum):
    """Type of AI agent."""
    JOBSEEKER = "jobseeker"
    HIRING_MANAGER = "hiring_manager"  # Phase 2: HM agent (portable)
    RECRUITER = "recruiter"  # Phase 2: External recruiter
    COMPANY = "company"  # Legacy


class AgentStatus(str, Enum):
    """Status of AI agent lifecycle."""
    PENDING = "pending"          # Interview in progress
    READY = "ready"              # Interview complete, not yet activated
    ACTIVE = "active"            # Searching for matches
    PAUSED = "paused"            # User paused agent
    DISABLED = "disabled"        # User disabled agent


class PersonalAIAgent(Base):
    """
    Personal AI Agent model.

    One agent per user. Represents the user in the marketplace,
    conducts conversations, and learns from interactions.
    """
    __tablename__ = "personal_ai_agents"

    # Primary key
    id = Column(Integer, primary_key=True, index=True)

    # Ownership
    user_id = Column(Integer, ForeignKey("users.id"), unique=True, nullable=False)
    agent_type = Column(SQLEnum(AgentType), nullable=False)

    # Knowledge base
    personal_rag_collection_id = Column(String(255), nullable=False)  # ChromaDB collection name

    # Profile (extracted during onboarding)
    industry = Column(String(255))  # e.g., "finance", "tech", "healthcare"
    role = Column(String(255))  # e.g., "system_engineer", "backend_engineer"
    user_segment_id = Column(String(500))  # For cross-learning: "system_engineer_finance_5yrs_python"

    # Phase 2: Recruiter-specific fields
    recruitment_company_name = Column(String(255))  # For RECRUITER agent type
    recruitment_company_description = Column(Text)  # For RECRUITER agent type

    # Performance metrics
    activation_date = Column(DateTime, default=datetime.utcnow, nullable=False)
    total_conversations = Column(Integer, default=0)
    successful_matches = Column(Integer, default=0)
    learning_score = Column(Float, default=0.5)  # 0.0 - 1.0, improves over time
    knowledge_version = Column(Integer, default=1)  # Tracks evolution

    # Active conversation management
    active_conversations_count = Column(Integer, default=0)  # Current active (max 3)
    max_concurrent_conversations = Column(Integer, default=3)

    # Status (Phase 2: Proper enum)
    status = Column(SQLEnum(AgentStatus), default=AgentStatus.PENDING, nullable=False)

    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    last_activity_at = Column(DateTime)
    activated_at = Column(DateTime)  # Phase 2: When agent became ACTIVE
    last_search_at = Column(DateTime)  # Phase 2: Last search for matches

    # Relationships
    user = relationship("User", back_populates="personal_agent")
    conversations = relationship("AgentConversation", foreign_keys="[AgentConversation.agent1_id]", back_populates="agent1")
    sub_agent_activations = relationship("SubAgentActivation", back_populates="personal_agent")
    knowledge_entries = relationship("UserKnowledge", back_populates="agent")

    def __repr__(self):
        return f"<PersonalAIAgent(id={self.id}, user_id={self.user_id}, type={self.agent_type}, learning_score={self.learning_score})>"

    def can_start_new_conversation(self) -> bool:
        """Check if agent can start a new conversation (respects concurrent limit)."""
        return self.active_conversations_count < self.max_concurrent_conversations

    def increment_conversation_count(self):
        """Increment active conversation count."""
        self.active_conversations_count += 1
        self.last_activity_at = datetime.utcnow()

    def decrement_conversation_count(self):
        """Decrement active conversation count."""
        if self.active_conversations_count > 0:
            self.active_conversations_count -= 1

    def record_successful_match(self):
        """Record a successful match."""
        self.successful_matches += 1
        self.total_conversations += 1
        self.last_activity_at = datetime.utcnow()

        # Improve learning score (simple linear improvement, cap at 0.95)
        if self.learning_score < 0.95:
            self.learning_score = min(0.95, self.learning_score + 0.02)

    def record_failed_conversation(self):
        """Record a conversation that didn't result in a match."""
        self.total_conversations += 1
        self.last_activity_at = datetime.utcnow()

    def get_success_rate(self) -> float:
        """Calculate match success rate."""
        if self.total_conversations == 0:
            return 0.0
        return self.successful_matches / self.total_conversations
