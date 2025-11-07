"""
Database Models.

SQLAlchemy ORM models for all database tables.
"""

from .user import User, UserRole, AccountStatus
from .profile import UserProfile, ProfileVisibility
from .company import Company, CompanyStatus, CompanySize
from .job import Job, JobStatus, JobType, ExperienceLevel
from .application import Application, ApplicationStatus
from .match import Match, MatchStatus
from .message import Conversation, Message, MessageStatus
from .ai_agent import AIAgent, AgentType, AgentStatus as AIAgentStatus

# New: Agent Marketplace Models
from .personal_ai_agent import PersonalAIAgent, AgentType as PersonalAgentType
from .agent_conversation import AgentConversation, ConversationType, ConversationStatus
from .interview_session import InterviewSession, InterviewStatus
from .sub_agent_activation import SubAgentActivation, SubAgentType
from .user_knowledge import UserKnowledge, KnowledgeCategory
from .network_knowledge import NetworkKnowledge
from .audit_log import AuditLog

__all__ = [
    # User
    'User',
    'UserRole',
    'AccountStatus',
    # Profile
    'UserProfile',
    'ProfileVisibility',
    # Company
    'Company',
    'CompanyStatus',
    'CompanySize',
    # Job
    'Job',
    'JobStatus',
    'JobType',
    'ExperienceLevel',
    # Application
    'Application',
    'ApplicationStatus',
    # Match
    'Match',
    'MatchStatus',
    # Message
    'Conversation',
    'Message',
    'MessageStatus',
    # AI Agent (legacy)
    'AIAgent',
    'AgentType',
    'AIAgentStatus',
    # Personal AI Agent (new)
    'PersonalAIAgent',
    'PersonalAgentType',
    'AgentConversation',
    'ConversationType',
    'ConversationStatus',
    'InterviewSession',
    'InterviewStatus',
    'SubAgentActivation',
    'SubAgentType',
    'UserKnowledge',
    'KnowledgeCategory',
    'NetworkKnowledge',
    'AuditLog',
]
