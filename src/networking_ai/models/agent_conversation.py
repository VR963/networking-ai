"""
Agent Conversation Model.

Stores conversations between AI agents and interview sessions with users.
"""

from datetime import datetime
from sqlalchemy import Column, Integer, String, Boolean, DateTime, ForeignKey, Enum as SQLEnum, Text, JSON, Float
from sqlalchemy.orm import relationship
from enum import Enum

from ..database import Base


class ConversationType(str, Enum):
    """Type of conversation."""
    INTERVIEW = "interview"  # User being interviewed by recruiter agent
    AGENT_TO_AGENT = "agent_to_agent"  # Two agents negotiating
    CLARIFICATION = "clarification"  # Agent asking for more info


class ConversationStatus(str, Enum):
    """Status of conversation."""
    ACTIVE = "active"  # Ongoing
    WAITING_FEEDBACK = "waiting_feedback"  # Waiting for user response
    COMPLETED = "completed"  # Successfully finished
    ONGOING = "ongoing"  # User requested more info, agent continuing
    ABANDONED = "abandoned"  # User or agent stopped responding
    TERMINATED = "terminated"  # Master AI terminated (waste detected)


class AgentConversation(Base):
    """
    Agent Conversation model.

    Stores all types of conversations: interviews, agent-to-agent negotiations, clarifications.
    """
    __tablename__ = "agent_conversations"

    # Primary key
    id = Column(Integer, primary_key=True, index=True)

    # Participants
    agent1_id = Column(Integer, ForeignKey("personal_ai_agents.id"), nullable=False)
    agent2_id = Column(Integer, ForeignKey("personal_ai_agents.id"), nullable=True)  # Null for interviews

    # Type
    conversation_type = Column(SQLEnum(ConversationType), nullable=False)

    # Messages (stored as JSON array)
    # Format: [{"role": "agent1", "content": "...", "timestamp": "...", "sub_agent": "psychometric"}]
    messages = Column(JSON, default=list, nullable=False)
    turn_count = Column(Integer, default=0)

    # Status
    status = Column(SQLEnum(ConversationStatus), default=ConversationStatus.ACTIVE, nullable=False)

    # Outcomes
    mutual_agreement = Column(Boolean, default=False)  # Both agents agreed (for agent-to-agent)
    match_created = Column(Boolean, default=False)  # Was a match created?
    match_id = Column(Integer, ForeignKey("matches.id"), nullable=True)

    # Summary
    synopsis = Column(Text)  # User-friendly summary of conversation
    key_points = Column(JSON)  # Bullet points of important details
    learning_signals = Column(JSON)  # Patterns extracted for learning

    # Master AI monitoring
    resource_usage_score = Column(Float)  # How efficient was this conversation (0-1)
    terminated_by_master = Column(Boolean, default=False)
    termination_reason = Column(String(500))

    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    ended_at = Column(DateTime)

    # Relationships
    agent1 = relationship("PersonalAIAgent", foreign_keys=[agent1_id], back_populates="conversations")
    agent2 = relationship("PersonalAIAgent", foreign_keys=[agent2_id])
    match = relationship("Match", back_populates="agent_conversation", uselist=False)
    sub_agent_activations = relationship("SubAgentActivation", back_populates="conversation")
    interview_session = relationship("InterviewSession", back_populates="conversation", uselist=False)

    def __repr__(self):
        return f"<AgentConversation(id={self.id}, type={self.conversation_type}, status={self.status}, turns={self.turn_count})>"

    def add_message(self, role: str, content: str, sub_agent: str = None):
        """Add a message to the conversation."""
        message = {
            "role": role,
            "content": content,
            "timestamp": datetime.utcnow().isoformat(),
            "sub_agent": sub_agent
        }

        if self.messages is None:
            self.messages = []

        self.messages.append(message)
        self.turn_count += 1
        self.updated_at = datetime.utcnow()

    def get_recent_messages(self, n: int = 10) -> list:
        """Get the last N messages."""
        if not self.messages:
            return []
        return self.messages[-n:]

    def calculate_efficiency(self) -> float:
        """
        Calculate conversation efficiency.

        Efficient conversations:
        - Reach mutual agreement quickly
        - Don't repeat questions
        - Stay on topic

        Returns: 0.0 - 1.0 (higher is better)
        """
        if self.turn_count == 0:
            return 0.0

        # Base score: fewer turns is better (for agent-to-agent)
        if self.conversation_type == ConversationType.AGENT_TO_AGENT:
            if self.turn_count <= 6:
                efficiency = 1.0
            elif self.turn_count <= 10:
                efficiency = 0.8
            else:
                efficiency = 0.6

            # Bonus for mutual agreement
            if self.mutual_agreement:
                efficiency = min(1.0, efficiency + 0.1)

        # Interviews have different criteria (completeness matters more)
        elif self.conversation_type == ConversationType.INTERVIEW:
            if self.turn_count >= 10 and self.turn_count <= 15:
                efficiency = 1.0  # Ideal length
            elif self.turn_count < 10:
                efficiency = 0.7  # Too short, missed info
            else:
                efficiency = 0.8  # A bit long

        else:
            efficiency = 0.7

        return efficiency

    def mark_completed(self, mutual_agreement: bool = False):
        """Mark conversation as completed."""
        self.status = ConversationStatus.COMPLETED
        self.ended_at = datetime.utcnow()
        self.mutual_agreement = mutual_agreement
        self.resource_usage_score = self.calculate_efficiency()

    def mark_waiting_feedback(self):
        """Mark conversation as waiting for user feedback."""
        self.status = ConversationStatus.WAITING_FEEDBACK
        self.updated_at = datetime.utcnow()

    def mark_ongoing(self):
        """Mark conversation as ongoing (user requested more info)."""
        self.status = ConversationStatus.ONGOING
        self.updated_at = datetime.utcnow()
