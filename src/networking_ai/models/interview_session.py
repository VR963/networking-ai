"""
Interview Session Model.

Tracks user onboarding interviews where AI learns about the user.
"""

from datetime import datetime
from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, Enum as SQLEnum, Text, JSON
from sqlalchemy.orm import relationship
from enum import Enum

from ..database import Base


class InterviewStatus(str, Enum):
    """Status of interview session."""
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    ABANDONED = "abandoned"


class InterviewSession(Base):
    """
    Interview Session model.

    Tracks the onboarding interview where recruiter agent learns about user.
    """
    __tablename__ = "interview_sessions"

    # Primary key
    id = Column(Integer, primary_key=True, index=True)

    # Ownership
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    recruiter_agent_id = Column(Integer, ForeignKey("personal_ai_agents.id"), nullable=True)  # Recruiter is ephemeral

    # Session type - Phase 2
    session_type = Column(String(50), default="talent")  # "talent" or "hiring_manager"

    # Uploaded document
    cv_file_path = Column(String(500))  # Path to uploaded CV
    cv_file_name = Column(String(255))
    cv_mime_type = Column(String(100))

    # Parsed data (extracted by AI)
    cv_parsed_data = Column(JSON)  # Structured data from CV
    """
    Format:
    {
        "name": "John Doe",
        "email": "john@example.com",
        "phone": "+1234567890",
        "education": [
            {"degree": "BS Computer Science", "school": "MIT", "year": 2015}
        ],
        "work_history": [
            {
                "company": "Goldman Sachs",
                "title": "System Engineer",
                "start_date": "2015-06",
                "end_date": "2020-12",
                "description": "..."
            }
        ],
        "skills": ["Python", "Java", "Avlog"],
        "gaps": [
            {"type": "employment", "reason": "6 month gap between jobs"}
        ]
    }
    """

    # Detected profile
    detected_industry = Column(String(255))  # e.g., "finance"
    detected_role = Column(String(255))  # e.g., "system_engineer"
    detected_skills = Column(JSON)  # Primary skills detected

    # Conversation
    conversation_id = Column(Integer, ForeignKey("agent_conversations.id"), nullable=True)  # Set after conversation created

    # Interview data
    questions_asked = Column(JSON, default=list)  # Array of questions
    answers_received = Column(JSON, default=list)  # Array of answers
    knowledge_extracted = Column(JSON, default=dict)  # Structured knowledge learned
    """
    Format:
    {
        "technical_skills": {
            "avlog": {"proficiency": "expert", "years": 5, "context": "..."}
        },
        "motivations": {
            "primary": "work_life_balance",
            "secondary": "compensation"
        },
        "preferences": {
            "company_stage": ["series_b", "public"],
            "avoid": ["long_hours", "on_call"]
        },
        "soft_skills": {
            "collaboration": "strong",
            "leadership": "developing"
        }
    }
    """

    # Progress tracking
    completion_percentage = Column(Integer, default=0)  # 0-100
    topics_covered = Column(JSON, default=list)  # ["technical", "motivations", "preferences"]
    topics_remaining = Column(JSON, default=list)  # Topics still to explore

    # Status
    status = Column(SQLEnum(InterviewStatus), default=InterviewStatus.IN_PROGRESS, nullable=False)

    # Timestamps
    started_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    completed_at = Column(DateTime)

    # Relationships
    user = relationship("User")
    recruiter_agent = relationship("PersonalAIAgent")
    conversation = relationship("AgentConversation", back_populates="interview_session")

    def __repr__(self):
        return f"<InterviewSession(id={self.id}, user_id={self.user_id}, status={self.status}, completion={self.completion_percentage}%)>"

    def update_completion(self):
        """Calculate and update completion percentage."""
        required_topics = ["technical_skills", "motivations", "preferences", "soft_skills", "work_history"]

        if not self.topics_covered:
            self.completion_percentage = 0
            return

        covered_count = len(self.topics_covered)
        self.completion_percentage = min(100, int((covered_count / len(required_topics)) * 100))

    def mark_completed(self):
        """Mark interview as completed."""
        self.status = InterviewStatus.COMPLETED
        self.completed_at = datetime.utcnow()
        self.completion_percentage = 100

    def add_knowledge(self, category: str, data: dict):
        """Add extracted knowledge to the session."""
        if not self.knowledge_extracted:
            self.knowledge_extracted = {}

        if category not in self.knowledge_extracted:
            self.knowledge_extracted[category] = {}

        self.knowledge_extracted[category].update(data)

        # Update topics covered
        if category not in self.topics_covered:
            if not self.topics_covered:
                self.topics_covered = []
            self.topics_covered.append(category)

        self.update_completion()
