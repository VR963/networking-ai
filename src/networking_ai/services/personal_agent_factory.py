"""
Personal Agent Factory.

Creates and activates personal AI agents from completed interviews.
"""

from typing import Dict, Optional
from datetime import datetime
from sqlalchemy.orm import Session

from ..models.personal_ai_agent import PersonalAIAgent, AgentType, AgentStatus
from ..models.interview_session import InterviewSession, InterviewStatus
from ..models.user import User
from ..services.cv_parser import create_cv_parser
from .personal_rag import create_personal_rag_manager


class PersonalAgentFactory:
    """
    Factory for creating and activating personal AI agents.

    Workflow:
    1. Load completed interview
    2. Extract knowledge
    3. Create ChromaDB collection
    4. Populate personal RAG
    5. Create PersonalAIAgent record
    6. Mark as ACTIVE
    """

    def __init__(self):
        """Initialize factory."""
        self.personal_rag = create_personal_rag_manager()
        self.cv_parser = create_cv_parser()

    def create_from_interview(
        self,
        session_id: int,
        db: Session
    ) -> PersonalAIAgent:
        """
        Create personal agent from completed interview.

        Args:
            session_id: Interview session ID
            db: Database session

        Returns:
            PersonalAIAgent instance

        Raises:
            ValueError: If interview not complete or agent already exists
        """
        # Load interview session
        session = db.query(InterviewSession).filter(
            InterviewSession.id == session_id
        ).first()

        if not session:
            raise ValueError(f"Interview session {session_id} not found")

        if session.status != InterviewStatus.COMPLETED:
            raise ValueError(f"Interview session {session_id} not completed (status: {session.status})")

        # Check if agent already exists
        existing_agent = db.query(PersonalAIAgent).filter(
            PersonalAIAgent.user_id == session.user_id
        ).first()

        if existing_agent:
            raise ValueError(f"Personal agent already exists for user {session.user_id}")

        # Get user
        user = db.query(User).filter(User.id == session.user_id).first()
        if not user:
            raise ValueError(f"User {session.user_id} not found")

        print(f"[AGENT FACTORY] Creating personal agent for user {user.id}...")

        # Step 1: Extract knowledge
        knowledge = session.knowledge_extracted or {}
        cv_data = session.cv_parsed_data or {}

        # Step 2: Generate user segment ID
        user_segment_id = self._generate_user_segment_id(
            session.detected_industry,
            session.detected_role,
            cv_data
        )

        # Step 3: Create ChromaDB collection
        collection_id = self.personal_rag.create_collection(user.id)

        # Step 4: Populate personal RAG
        self.personal_rag.populate_from_interview(
            collection_id=collection_id,
            knowledge=knowledge,
            cv_data=cv_data
        )

        # Step 5: Create PersonalAIAgent record
        agent = PersonalAIAgent(
            user_id=user.id,
            agent_type=AgentType.JOBSEEKER,  # Default for job seekers
            personal_rag_collection_id=collection_id,
            industry=session.detected_industry,
            role=session.detected_role,
            user_segment_id=user_segment_id,
            status=AgentStatus.READY,  # Ready but not yet activated
            created_at=datetime.utcnow()
        )

        db.add(agent)
        db.commit()
        db.refresh(agent)

        print(f"[AGENT FACTORY] Created agent {agent.id} for user {user.id}")
        print(f"[AGENT FACTORY] Collection: {collection_id}")
        print(f"[AGENT FACTORY] Segment: {user_segment_id}")

        return agent

    def activate_agent(
        self,
        agent_id: int,
        db: Session
    ) -> PersonalAIAgent:
        """
        Activate agent for matching.

        Args:
            agent_id: Personal AI agent ID
            db: Database session

        Returns:
            Activated PersonalAIAgent

        Raises:
            ValueError: If agent not found or already active
        """
        agent = db.query(PersonalAIAgent).filter(
            PersonalAIAgent.id == agent_id
        ).first()

        if not agent:
            raise ValueError(f"Agent {agent_id} not found")

        if agent.status == AgentStatus.ACTIVE:
            print(f"[AGENT FACTORY] Agent {agent_id} already active")
            return agent

        # Activate
        agent.status = AgentStatus.ACTIVE
        agent.activated_at = datetime.utcnow()
        agent.last_activity_at = datetime.utcnow()

        db.commit()
        db.refresh(agent)

        print(f"[AGENT FACTORY] Activated agent {agent.id}")

        return agent

    def pause_agent(
        self,
        agent_id: int,
        db: Session
    ) -> PersonalAIAgent:
        """
        Pause agent (user requested).

        Args:
            agent_id: Personal AI agent ID
            db: Database session

        Returns:
            Paused PersonalAIAgent
        """
        agent = db.query(PersonalAIAgent).filter(
            PersonalAIAgent.id == agent_id
        ).first()

        if not agent:
            raise ValueError(f"Agent {agent_id} not found")

        agent.status = AgentStatus.PAUSED
        db.commit()
        db.refresh(agent)

        print(f"[AGENT FACTORY] Paused agent {agent.id}")

        return agent

    def resume_agent(
        self,
        agent_id: int,
        db: Session
    ) -> PersonalAIAgent:
        """
        Resume paused agent.

        Args:
            agent_id: Personal AI agent ID
            db: Database session

        Returns:
            Resumed PersonalAIAgent
        """
        agent = db.query(PersonalAIAgent).filter(
            PersonalAIAgent.id == agent_id
        ).first()

        if not agent:
            raise ValueError(f"Agent {agent_id} not found")

        if agent.status != AgentStatus.PAUSED:
            raise ValueError(f"Agent {agent.id} is not paused (status: {agent.status})")

        agent.status = AgentStatus.ACTIVE
        agent.last_activity_at = datetime.utcnow()

        db.commit()
        db.refresh(agent)

        print(f"[AGENT FACTORY] Resumed agent {agent.id}")

        return agent

    def disable_agent(
        self,
        agent_id: int,
        db: Session
    ) -> PersonalAIAgent:
        """
        Disable agent (soft delete).

        Args:
            agent_id: Personal AI agent ID
            db: Database session

        Returns:
            Disabled PersonalAIAgent
        """
        agent = db.query(PersonalAIAgent).filter(
            PersonalAIAgent.id == agent_id
        ).first()

        if not agent:
            raise ValueError(f"Agent {agent_id} not found")

        agent.status = AgentStatus.DISABLED
        db.commit()
        db.refresh(agent)

        print(f"[AGENT FACTORY] Disabled agent {agent.id}")

        return agent

    def _generate_user_segment_id(
        self,
        industry: str,
        role: str,
        cv_data: Dict
    ) -> str:
        """
        Generate user segment ID for cross-learning.

        Format: "role_industry_experienceyrs_primaryskill"
        Example: "system_engineer_finance_5yrs_python"

        Args:
            industry: Detected industry
            role: Detected role
            cv_data: Parsed CV data

        Returns:
            User segment ID
        """
        # Calculate years of experience
        work_history = cv_data.get("work_history", [])
        total_years = sum(job.get("years", 0) for job in work_history)

        # Bucket years (0-2, 3-5, 6-10, 10+)
        if total_years <= 2:
            years_bucket = "0-2yrs"
        elif total_years <= 5:
            years_bucket = "3-5yrs"
        elif total_years <= 10:
            years_bucket = "6-10yrs"
        else:
            years_bucket = "10+yrs"

        # Get primary skill
        skills = cv_data.get("skills", {})
        primary_skill = "general"

        if isinstance(skills, dict):
            technical_skills = skills.get("technical", [])
            if technical_skills:
                primary_skill = technical_skills[0].lower().replace(" ", "_")
        elif isinstance(skills, list) and skills:
            primary_skill = skills[0].lower().replace(" ", "_")

        # Clean strings
        role_clean = role.lower().replace(" ", "_") if role else "general"
        industry_clean = industry.lower().replace(" ", "_") if industry else "general"

        # Format: role_industry_years_skill
        segment_id = f"{role_clean}_{industry_clean}_{years_bucket}_{primary_skill}"

        return segment_id


def create_personal_agent_factory() -> PersonalAgentFactory:
    """
    Factory function to create PersonalAgentFactory.

    Returns:
        PersonalAgentFactory instance
    """
    return PersonalAgentFactory()
