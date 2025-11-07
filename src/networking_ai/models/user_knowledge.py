"""
User Knowledge Model.

Implements "never ask twice" - stores all learned information about user.
"""

from datetime import datetime
from sqlalchemy import Column, Integer, String, Float, Boolean, DateTime, ForeignKey, Enum as SQLEnum, Text, JSON
from sqlalchemy.orm import relationship
from enum import Enum

from ..database import Base


class KnowledgeCategory(str, Enum):
    """Category of knowledge."""
    TECHNICAL_SKILL = "technical_skill"
    MOTIVATION = "motivation"
    PREFERENCE = "preference"
    SOFT_SKILL = "soft_skill"
    EXPERIENCE = "experience"
    PERSONAL = "personal"
    COMPENSATION = "compensation"
    LOCATION = "location"


class UserKnowledge(Base):
    """
    User Knowledge model.

    Stores individual pieces of knowledge learned about a user.
    Enables "never ask twice" functionality.
    """
    __tablename__ = "user_knowledge"

    # Primary key
    id = Column(Integer, primary_key=True, index=True)

    # Ownership
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    personal_agent_id = Column(Integer, ForeignKey("personal_ai_agents.id"), nullable=False)

    # Knowledge
    question = Column(Text)  # Original question asked (if applicable)
    answer = Column(Text)  # User's answer or extracted information
    knowledge_key = Column(String(500), index=True)  # e.g., "skill.python.proficiency"

    # Structured data
    structured_data = Column(JSON)  # Parsed, structured version
    """
    Format:
    {
        "type": "technical_skill",
        "skill": "python",
        "proficiency": "expert",
        "years": 5,
        "context": "real_time_trading_systems"
    }
    """

    # Context
    context = Column(JSON)  # When/why this was learned
    """
    Format:
    {
        "conversation_id": 123,
        "turn": 5,
        "trigger": "user_mentioned_skill"
    }
    """

    # Categorization
    knowledge_category = Column(SQLEnum(KnowledgeCategory), nullable=False, index=True)
    confidence = Column(Float, default=1.0)  # 0.0 - 1.0
    verified = Column(Boolean, default=False)  # User confirmed this information?

    # Source tracking
    source = Column(String(500))  # e.g., "interview_turn_5", "match_feedback_123"
    extracted_by_sub_agent = Column(String(100))  # Which sub-agent extracted this

    # Timestamps
    learned_at = Column(DateTime, default=datetime.utcnow, nullable=False, index=True)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    verified_at = Column(DateTime)

    # Relationships
    user = relationship("User")
    agent = relationship("PersonalAIAgent", back_populates="knowledge_entries")

    def __repr__(self):
        return f"<UserKnowledge(id={self.id}, user_id={self.user_id}, category={self.knowledge_category}, key={self.knowledge_key})>"

    @classmethod
    def check_if_asked(cls, db_session, user_id: int, question: str) -> bool:
        """
        Check if a question has already been asked to this user.

        Args:
            db_session: Database session
            user_id: User ID
            question: Question text

        Returns:
            True if question was already asked, False otherwise
        """
        # Normalize question (lowercase, remove punctuation)
        normalized_question = question.lower().strip().rstrip('?')

        # Check for similar question
        existing = db_session.query(cls).filter(
            cls.user_id == user_id,
            cls.question.ilike(f"%{normalized_question}%")
        ).first()

        return existing is not None

    @classmethod
    def get_knowledge(cls, db_session, user_id: int, knowledge_key: str):
        """
        Retrieve specific knowledge about user.

        Args:
            db_session: Database session
            user_id: User ID
            knowledge_key: Key like "skill.python.proficiency"

        Returns:
            UserKnowledge object or None
        """
        return db_session.query(cls).filter(
            cls.user_id == user_id,
            cls.knowledge_key == knowledge_key
        ).order_by(cls.learned_at.desc()).first()

    @classmethod
    def get_all_knowledge(cls, db_session, user_id: int, category: KnowledgeCategory = None) -> list:
        """
        Get all knowledge about a user, optionally filtered by category.

        Args:
            db_session: Database session
            user_id: User ID
            category: Optional category filter

        Returns:
            List of UserKnowledge objects
        """
        query = db_session.query(cls).filter(cls.user_id == user_id)

        if category:
            query = query.filter(cls.knowledge_category == category)

        return query.order_by(cls.learned_at.desc()).all()

    def mark_verified(self):
        """Mark this knowledge as verified by user."""
        self.verified = True
        self.verified_at = datetime.utcnow()
        self.confidence = 1.0
