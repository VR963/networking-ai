"""
Sub-Agent Activation Model.

Tracks when specialized sub-agents are activated during conversations.
Part of the audit trail system.
"""

from datetime import datetime
from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, Enum as SQLEnum, Text, JSON
from sqlalchemy.orm import relationship
from enum import Enum

from ..database import Base


class SubAgentType(str, Enum):
    """Type of sub-agent specialist."""
    PSYCHOMETRIC = "psychometric"  # Personality analysis
    SOFT_SKILLS = "soft_skills"  # Collaboration, leadership detection
    INDUSTRY_EXPERT = "industry_expert"  # Domain knowledge assessment
    SKILLS_RECOGNIZER = "skills_recognizer"  # Technical skill identification
    CAREER_COACH = "career_coach"  # Motivations, goals, trajectory
    TECHNICAL_INTERVIEWER = "technical_interviewer"  # Deep technical assessment
    COMPENSATION_ANALYZER = "compensation_analyzer"  # Salary, benefits analysis


class SubAgentActivation(Base):
    """
    Sub-Agent Activation model.

    Records when a specialized sub-agent is activated during a conversation.
    Provides audit trail of agent reasoning.
    """
    __tablename__ = "sub_agent_activations"
    __table_args__ = {'extend_existing': True}

    # Primary key
    id = Column(Integer, primary_key=True, index=True)

    # Context
    personal_agent_id = Column(Integer, ForeignKey("personal_ai_agents.id"), nullable=False)
    conversation_id = Column(Integer, ForeignKey("agent_conversations.id"), nullable=False)

    # Sub-agent details
    sub_agent_type = Column(SQLEnum(SubAgentType), nullable=False)
    activation_trigger = Column(Text)  # What caused activation (keyword, context)
    conversation_turn = Column(Integer)  # Which turn of conversation

    # Context snapshot
    context = Column(JSON)  # Conversation context at time of activation
    """
    Format:
    {
        "user_message": "I want better work-life balance",
        "trigger_keywords": ["work-life balance"],
        "prior_knowledge": {...}
    }
    """

    # Outputs
    insights_generated = Column(JSON)  # What the sub-agent learned
    """
    Format:
    {
        "category": "motivation",
        "findings": {
            "primary_motivation": "work_life_balance",
            "life_stage": "family_oriented",
            "confidence": 0.85
        },
        "confidence": 0.85
    }
    """

    # Success metrics
    useful = Column(Integer, default=None)  # Was this activation useful? (1=yes, 0=no, null=unknown)
    contributed_to_match = Column(Integer, default=None)  # Did this help create a match?

    # Timestamp
    activated_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    # Relationships
    personal_agent = relationship("PersonalAIAgent", back_populates="sub_agent_activations")
    conversation = relationship("AgentConversation", back_populates="sub_agent_activations")

    def __repr__(self):
        return f"<SubAgentActivation(id={self.id}, type={self.sub_agent_type}, agent_id={self.personal_agent_id})>"

    @classmethod
    def get_activation_stats(cls, db_session, personal_agent_id: int) -> dict:
        """
        Get statistics on sub-agent activations for an agent.

        Returns:
            {
                "psychometric": {"count": 15, "avg_usefulness": 0.8},
                "career_coach": {"count": 20, "avg_usefulness": 0.9},
                ...
            }
        """
        from sqlalchemy import func

        stats = {}

        for sub_agent_type in SubAgentType:
            results = db_session.query(
                func.count(cls.id).label("count"),
                func.avg(cls.useful).label("avg_usefulness")
            ).filter(
                cls.personal_agent_id == personal_agent_id,
                cls.sub_agent_type == sub_agent_type
            ).first()

            stats[sub_agent_type.value] = {
                "count": results.count or 0,
                "avg_usefulness": float(results.avg_usefulness or 0.0)
            }

        return stats
