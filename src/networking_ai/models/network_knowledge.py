"""
Network Knowledge Model.

Stores aggregated patterns from Master AI for cross-learning between agents.
"""

from datetime import datetime
from sqlalchemy import Column, Integer, String, Float, DateTime, Text, JSON
from enum import Enum

from ..database import Base


class NetworkKnowledge(Base):
    """
    Network Knowledge model.

    Stores aggregated behavioral patterns learned across multiple users.
    Enables cross-learning: agents benefit from collective intelligence.
    """
    __tablename__ = "network_knowledge"

    # Primary key
    id = Column(Integer, primary_key=True, index=True)

    # Segmentation (who does this apply to?)
    user_segment = Column(String(500), nullable=False, index=True)
    """
    Format: "role_industry_experience_primaryskill"
    Example: "system_engineer_finance_5yrs_python"
    """

    # Pattern details
    pattern_type = Column(String(255), nullable=False, index=True)
    """
    Examples:
    - "company_stage_preference"
    - "work_life_balance_priority"
    - "typical_salary_range"
    - "preferred_company_size"
    """

    pattern_data = Column(JSON, nullable=False)
    """
    Format varies by pattern_type.

    Example for "company_stage_preference":
    {
        "preferred_stages": ["series_b", "series_c"],
        "avoid_stages": ["seed", "series_a"],
        "reasoning": "Users in this segment prefer stability"
    }

    Example for "typical_salary_range":
    {
        "min": 130000,
        "max": 160000,
        "median": 145000,
        "currency": "USD"
    }
    """

    # Statistics
    contributing_users = Column(Integer, default=1)  # How many users contributed
    total_observations = Column(Integer, default=1)  # Total data points
    confidence = Column(Float, default=0.5)  # 0.0 - 1.0

    # Versioning
    version = Column(Integer, default=1)  # Increments when pattern is updated

    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False, index=True)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    def __repr__(self):
        return f"<NetworkKnowledge(id={self.id}, segment={self.user_segment}, type={self.pattern_type}, confidence={self.confidence})>"

    @classmethod
    def get_segment_knowledge(cls, db_session, user_segment: str) -> list:
        """
        Get all network knowledge for a user segment.

        Args:
            db_session: Database session
            user_segment: Segment ID (e.g., "system_engineer_finance_5yrs_python")

        Returns:
            List of NetworkKnowledge objects
        """
        return db_session.query(cls).filter(
            cls.user_segment == user_segment
        ).order_by(cls.confidence.desc()).all()

    @classmethod
    def get_pattern(cls, db_session, user_segment: str, pattern_type: str):
        """
        Get specific pattern for a segment.

        Args:
            db_session: Database session
            user_segment: Segment ID
            pattern_type: Type of pattern

        Returns:
            NetworkKnowledge object or None
        """
        return db_session.query(cls).filter(
            cls.user_segment == user_segment,
            cls.pattern_type == pattern_type
        ).order_by(cls.version.desc()).first()

    @classmethod
    def create_or_update_pattern(
        cls,
        db_session,
        user_segment: str,
        pattern_type: str,
        pattern_data: dict,
        contributing_users: int = 1,
        total_observations: int = 1
    ):
        """
        Create a new pattern or update existing one.

        Args:
            db_session: Database session
            user_segment: Segment ID
            pattern_type: Type of pattern
            pattern_data: Pattern data
            contributing_users: Number of users who contributed
            total_observations: Total data points

        Returns:
            NetworkKnowledge object
        """
        # Check if pattern exists
        existing = cls.get_pattern(db_session, user_segment, pattern_type)

        if existing:
            # Update existing
            existing.pattern_data = pattern_data
            existing.contributing_users = contributing_users
            existing.total_observations = total_observations
            existing.confidence = min(1.0, contributing_users / 10.0)  # Cap at 1.0, reaches 1.0 at 10+ users
            existing.version += 1
            existing.updated_at = datetime.utcnow()

            db_session.commit()
            db_session.refresh(existing)

            return existing
        else:
            # Create new
            knowledge = cls(
                user_segment=user_segment,
                pattern_type=pattern_type,
                pattern_data=pattern_data,
                contributing_users=contributing_users,
                total_observations=total_observations,
                confidence=min(1.0, contributing_users / 10.0)
            )

            db_session.add(knowledge)
            db_session.commit()
            db_session.refresh(knowledge)

            return knowledge

    def increment_observations(self, new_observation: dict):
        """
        Increment observation count and update confidence.

        Args:
            new_observation: New data point to incorporate
        """
        self.total_observations += 1
        self.updated_at = datetime.utcnow()

        # Recalculate confidence
        self.confidence = min(1.0, self.contributing_users / 10.0)
