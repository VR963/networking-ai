"""
Agent Message Model - Phase 2 Week 3.

Enables agent-to-agent conversations for collaborative hiring and networking.

Key Features:
- Talent ↔ HM conversations (via matches/applications)
- HM ↔ Company Admin conversations (internal discussions)
- Talent ↔ Company Admin conversations (company inquiries)
- Thread management with context
- Read/unread status tracking
- Message types (question, response, notification)
"""

from datetime import datetime
from enum import Enum
from typing import Dict, Optional

from sqlalchemy import Column, Integer, String, Text, DateTime, ForeignKey, Boolean, Enum as SQLEnum
from sqlalchemy.orm import relationship

from ..database import Base


class MessageType(str, Enum):
    """Message type classification."""
    QUESTION = "question"  # Asking for information
    RESPONSE = "response"  # Responding to a question
    NOTIFICATION = "notification"  # System/AI notification
    CLARIFICATION = "clarification"  # Asking for clarification
    UPDATE = "update"  # Status update
    INTRODUCTION = "introduction"  # Initial introduction message


class ConversationContext(str, Enum):
    """Context of the conversation."""
    MATCH = "match"  # About a specific match
    APPLICATION = "application"  # About an application
    JOB = "job"  # About a job posting
    INTERVIEW = "interview"  # About an interview
    OFFER = "offer"  # About a job offer
    GENERAL = "general"  # General conversation
    COMPANY_INQUIRY = "company_inquiry"  # General company questions


class AgentMessage(Base):
    """
    Agent-to-Agent message model.

    Enables AI agents to communicate with each other in a structured way.
    Each message belongs to a conversation thread with context.
    """
    __tablename__ = "agent_messages"
    __table_args__ = {'extend_existing': True}

    # Primary Key
    id = Column(Integer, primary_key=True, index=True)

    # Thread management
    thread_id = Column(String(100), nullable=False, index=True)  # Groups related messages
    parent_message_id = Column(Integer, ForeignKey("agent_messages.id"), nullable=True)  # Reply thread

    # Sender and Receiver (AI Agents)
    sender_agent_type = Column(String(50), nullable=False)  # "talent", "hiring_manager", "company_admin"
    sender_agent_id = Column(Integer, nullable=False, index=True)  # Agent ID (polymorphic)
    sender_user_id = Column(Integer, ForeignKey("users.id"), nullable=True)  # User behind the agent

    receiver_agent_type = Column(String(50), nullable=False)  # "talent", "hiring_manager", "company_admin"
    receiver_agent_id = Column(Integer, nullable=False, index=True)  # Agent ID (polymorphic)
    receiver_user_id = Column(Integer, ForeignKey("users.id"), nullable=True)  # User behind the agent

    # Message Content
    message_type = Column(SQLEnum(MessageType), default=MessageType.QUESTION, nullable=False)
    subject = Column(String(200), nullable=True)  # Optional subject line
    content = Column(Text, nullable=False)  # Message body
    ai_generated = Column(Boolean, default=True, nullable=False)  # True if AI composed it

    # Context (what is this message about?)
    context_type = Column(SQLEnum(ConversationContext), default=ConversationContext.GENERAL)
    match_id = Column(Integer, ForeignKey("matches.id"), nullable=True, index=True)
    application_id = Column(Integer, ForeignKey("applications.id"), nullable=True, index=True)
    job_id = Column(Integer, ForeignKey("jobs.id"), nullable=True, index=True)
    interview_id = Column(Integer, ForeignKey("interview_sessions.id"), nullable=True)

    # Status
    is_read = Column(Boolean, default=False, nullable=False)
    read_at = Column(DateTime, nullable=True)
    is_archived = Column(Boolean, default=False, nullable=False)

    # Metadata
    message_metadata = Column(Text, nullable=True)  # JSON string for additional data

    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False, index=True)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    # Relationships
    parent_message = relationship("AgentMessage", remote_side=[id], backref="replies")
    match = relationship("Match", foreign_keys=[match_id])
    application = relationship("Application", foreign_keys=[application_id])
    job = relationship("Job", foreign_keys=[job_id])

    def __repr__(self):
        return f"<AgentMessage {self.id}: {self.sender_agent_type}→{self.receiver_agent_type} ({self.message_type.value})>"

    def mark_read(self):
        """Mark message as read."""
        self.is_read = True
        self.read_at = datetime.utcnow()

    def mark_unread(self):
        """Mark message as unread."""
        self.is_read = False
        self.read_at = None

    def archive(self):
        """Archive this message."""
        self.is_archived = True

    def is_from_talent(self) -> bool:
        """Check if message is from a talent agent."""
        return self.sender_agent_type == "talent"

    def is_from_hm(self) -> bool:
        """Check if message is from a hiring manager agent."""
        return self.sender_agent_type == "hiring_manager"

    def is_from_company(self) -> bool:
        """Check if message is from a company admin agent."""
        return self.sender_agent_type == "company_admin"

    def is_to_talent(self) -> bool:
        """Check if message is to a talent agent."""
        return self.receiver_agent_type == "talent"

    def is_to_hm(self) -> bool:
        """Check if message is to a hiring manager agent."""
        return self.receiver_agent_type == "hiring_manager"

    def is_to_company(self) -> bool:
        """Check if message is to a company admin agent."""
        return self.receiver_agent_type == "company_admin"

    def get_conversation_partners(self) -> tuple:
        """Get the two agent types in this conversation."""
        return (self.sender_agent_type, self.receiver_agent_type)

    def to_dict(self) -> Dict:
        """Convert to dictionary representation."""
        return {
            "id": self.id,
            "thread_id": self.thread_id,
            "parent_message_id": self.parent_message_id,
            "sender": {
                "agent_type": self.sender_agent_type,
                "agent_id": self.sender_agent_id,
                "user_id": self.sender_user_id
            },
            "receiver": {
                "agent_type": self.receiver_agent_type,
                "agent_id": self.receiver_agent_id,
                "user_id": self.receiver_user_id
            },
            "message_type": self.message_type.value,
            "subject": self.subject,
            "content": self.content,
            "ai_generated": self.ai_generated,
            "context": {
                "type": self.context_type.value,
                "match_id": self.match_id,
                "application_id": self.application_id,
                "job_id": self.job_id,
                "interview_id": self.interview_id
            },
            "is_read": self.is_read,
            "read_at": self.read_at.isoformat() if self.read_at else None,
            "is_archived": self.is_archived,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat()
        }


class ConversationThread:
    """
    Helper class to manage conversation threads.

    Not a database model - used for organizing messages into threads.
    """

    @staticmethod
    def generate_thread_id(
        agent1_type: str,
        agent1_id: int,
        agent2_type: str,
        agent2_id: int,
        context_type: str,
        context_id: Optional[int] = None
    ) -> str:
        """
        Generate a unique thread ID for a conversation.

        Format: {agent1_type}_{agent1_id}_{agent2_type}_{agent2_id}_{context}_{context_id}

        Args:
            agent1_type: Type of first agent (talent/hiring_manager/company_admin)
            agent1_id: ID of first agent
            agent2_type: Type of second agent
            agent2_id: ID of second agent
            context_type: Type of context (match/application/job/etc)
            context_id: ID of the context object (optional)

        Returns:
            Thread ID string
        """
        # Sort agents to ensure consistent thread ID regardless of who initiates
        agents = sorted([
            (agent1_type, agent1_id),
            (agent2_type, agent2_id)
        ], key=lambda x: (x[0], x[1]))

        thread_id = f"{agents[0][0]}_{agents[0][1]}_{agents[1][0]}_{agents[1][1]}_{context_type}"

        if context_id:
            thread_id += f"_{context_id}"

        return thread_id

    @staticmethod
    def parse_thread_id(thread_id: str) -> Dict:
        """
        Parse a thread ID back into components.

        Args:
            thread_id: Thread ID string

        Returns:
            Dict with thread components
        """
        parts = thread_id.split("_")

        if len(parts) >= 5:
            return {
                "agent1_type": parts[0],
                "agent1_id": int(parts[1]),
                "agent2_type": parts[2],
                "agent2_id": int(parts[3]),
                "context_type": parts[4],
                "context_id": int(parts[5]) if len(parts) > 5 else None
            }

        return {}
