"""
Audit Log Model.

Provides complete transparency - users can see how their agent represents them.
"""

from datetime import datetime
from sqlalchemy import Column, Integer, String, Boolean, DateTime, ForeignKey, Text, JSON
from sqlalchemy.orm import relationship

from ..database import Base


class AuditLog(Base):
    """
    Audit Log model.

    Records all actions taken by AI agents for transparency and compliance.
    Users can view their audit trail to see how they're being represented.
    """
    __tablename__ = "audit_logs"

    # Primary key
    id = Column(Integer, primary_key=True, index=True)

    # Ownership
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    agent_id = Column(Integer, ForeignKey("personal_ai_agents.id"), nullable=True)

    # Action details
    action_type = Column(String(255), nullable=False, index=True)
    """
    Examples:
    - "asked_question"
    - "activated_sub_agent"
    - "initiated_conversation"
    - "made_recommendation"
    - "extracted_knowledge"
    - "shared_with_master"
    - "learned_from_network"
    """

    action_details = Column(JSON)
    """
    Format varies by action_type.

    Example for "asked_question":
    {
        "question": "What are your salary expectations?",
        "reason": "need_compensation_data",
        "sub_agent": "compensation_analyzer"
    }

    Example for "initiated_conversation":
    {
        "target_agent_id": 456,
        "target_user_type": "company",
        "reason": "potential_match",
        "match_score": 0.85
    }

    Example for "shared_with_master":
    {
        "pattern_type": "company_stage_preference",
        "pattern_data": {...},
        "anonymized": true
    }
    """

    # Visibility
    user_can_view = Column(Boolean, default=True)  # Can user see this in their audit trail?
    """
    Most actions are visible to users for transparency.
    Some internal optimizations might be hidden.
    """

    # Privacy
    contains_personal_data = Column(Boolean, default=False)
    anonymized_for_network = Column(Boolean, default=False)

    # Context
    conversation_id = Column(Integer, ForeignKey("agent_conversations.id"), nullable=True)
    interview_session_id = Column(Integer, ForeignKey("interview_sessions.id"), nullable=True)

    # Timestamp
    timestamp = Column(DateTime, default=datetime.utcnow, nullable=False, index=True)

    # Relationships
    user = relationship("User")
    agent = relationship("PersonalAIAgent")

    def __repr__(self):
        return f"<AuditLog(id={self.id}, user_id={self.user_id}, action={self.action_type})>"

    @classmethod
    def log_action(
        cls,
        db_session,
        user_id: int,
        action_type: str,
        action_details: dict,
        agent_id: int = None,
        user_can_view: bool = True,
        contains_personal_data: bool = False,
        conversation_id: int = None,
        interview_session_id: int = None
    ):
        """
        Create an audit log entry.

        Args:
            db_session: Database session
            user_id: User ID
            action_type: Type of action
            action_details: Details (JSON)
            agent_id: Personal AI agent ID
            user_can_view: Whether user can see this
            contains_personal_data: Whether this contains PII
            conversation_id: Related conversation
            interview_session_id: Related interview

        Returns:
            AuditLog object
        """
        log = cls(
            user_id=user_id,
            agent_id=agent_id,
            action_type=action_type,
            action_details=action_details,
            user_can_view=user_can_view,
            contains_personal_data=contains_personal_data,
            conversation_id=conversation_id,
            interview_session_id=interview_session_id
        )

        db_session.add(log)
        db_session.commit()
        db_session.refresh(log)

        return log

    @classmethod
    def get_user_audit_trail(
        cls,
        db_session,
        user_id: int,
        limit: int = 100,
        action_type: str = None
    ) -> list:
        """
        Get audit trail for a user.

        Args:
            db_session: Database session
            user_id: User ID
            limit: Max entries to return
            action_type: Optional filter by action type

        Returns:
            List of AuditLog objects
        """
        query = db_session.query(cls).filter(
            cls.user_id == user_id,
            cls.user_can_view == True  # Only show visible entries
        )

        if action_type:
            query = query.filter(cls.action_type == action_type)

        return query.order_by(cls.timestamp.desc()).limit(limit).all()

    @classmethod
    def export_user_data(cls, db_session, user_id: int) -> dict:
        """
        Export all user data for GDPR compliance.

        Args:
            db_session: Database session
            user_id: User ID

        Returns:
            Dictionary with all user data
        """
        logs = db_session.query(cls).filter(cls.user_id == user_id).all()

        return {
            "total_actions": len(logs),
            "actions": [
                {
                    "timestamp": log.timestamp.isoformat(),
                    "action_type": log.action_type,
                    "details": log.action_details,
                    "visible_to_you": log.user_can_view
                }
                for log in logs
            ]
        }
