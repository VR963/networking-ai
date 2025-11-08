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

# Agent Marketplace Models (Phase 1 & 2)
from .personal_ai_agent import PersonalAIAgent, AgentType as PersonalAgentType, AgentStatus
from .agent_conversation import AgentConversation, ConversationType, ConversationStatus
from .interview_session import InterviewSession, InterviewStatus
from .sub_agent_activation import SubAgentActivation, SubAgentType
from .user_knowledge import UserKnowledge, KnowledgeCategory
from .network_knowledge import NetworkKnowledge
from .audit_log import AuditLog

# Phase 2: Company & Subscription Models
from .company_admin_agent import CompanyAdminAgent, AdminAgentStatus
from .hiring_manager_role import HiringManagerRole
from .company_admin_user import CompanyAdminUser
from .subscription import Subscription, SubscriptionType, SubscriptionStatus

# Phase 2 Week 3: Agent Messaging
from .agent_message import AgentMessage, MessageType, ConversationContext

# Phase 3: Notifications & Real-time
from .notification import (
    Notification,
    NotificationPreferences,
    NotificationType,
    NotificationPriority,
    NotificationStatus,
    NotificationChannel
)

# Phase 4: Interviews & Hiring
from .interview import (
    Interview,
    InterviewAvailability,
    InterviewFeedback,
    InterviewPipeline,
    InterviewStage,
    InterviewStatus,
    InterviewFormat,
    FeedbackRating
)
from .job_offer import (
    JobOffer,
    OfferNegotiation,
    OfferStatus,
    NegotiationType,
    NegotiationStatus
)

# Phase 5: Analytics & Reporting
from .analytics import (
    HiringMetrics,
    JobAnalytics,
    CandidateAnalytics,
    AIPerformanceMetrics,
    MetricType,
    ReportType
)

# Phase 6: Billing & Admin
from .billing import (
    PaymentMethod,
    SubscriptionPlan,
    BillingSubscription,
    Invoice,
    Payment,
    UsageRecord,
    BillingEvent,
    BillingCycle,
    PaymentStatus,
    InvoiceStatus,
    SubscriptionPlanType
)
from .admin import (
    AdminUser,
    AuditLog as AdminAuditLog,
    PlatformConfiguration,
    SystemMetrics,
    UserActionLog,
    FeatureFlag,
    DataExport,
    ComplianceRecord,
    AdminRole,
    AuditAction,
    AuditResourceType,
    ConfigurationType
)

# Phase 7: Integrations
from .integrations import (
    Integration,
    CalendarEvent,
    VideoMeeting,
    ATSSync,
    CommunicationLog,
    BackgroundCheck,
    LinkedInProfile,
    WebhookEndpoint,
    WebhookEvent,
    IntegrationType,
    IntegrationProvider,
    IntegrationStatus
)

# Phase 8: Advanced AI Features
from .ai_features import (
    ParsedResume,
    AIScreening,
    AIPrediction,
    SkillTaxonomy,
    AIModelMetrics,
    CandidateInsight,
    JobInsight,
    ResumeParseStatus,
    ScreeningDecision,
    PredictionType,
    ModelType
)

# Phase 9: Employee Onboarding
from .onboarding import (
    Employee,
    OnboardingChecklist,
    OnboardingTask,
    TrainingProgram,
    EmployeeTraining,
    Equipment,
    EmployeeDocument,
    TimeOffRequest,
    EmployeeReview,
    EmploymentType,
    EmploymentStatus,
    OnboardingStatus,
    TaskStatus,
    TaskCategory,
    TrainingStatus,
    TrainingType,
    EquipmentType,
    EquipmentStatus,
    DocumentType,
    DocumentStatus,
    TimeOffType,
    TimeOffStatus,
    ReviewType,
    ReviewStatus
)

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
    # Personal AI Agent (Phase 1)
    'PersonalAIAgent',
    'PersonalAgentType',
    'AgentStatus',
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
    # Phase 2: Company & Subscription
    'CompanyAdminAgent',
    'AdminAgentStatus',
    'HiringManagerRole',
    'CompanyAdminUser',
    'Subscription',
    'SubscriptionType',
    'SubscriptionStatus',
    # Phase 2 Week 3: Agent Messaging
    'AgentMessage',
    'MessageType',
    'ConversationContext',
    # Phase 3: Notifications
    'Notification',
    'NotificationPreferences',
    'NotificationType',
    'NotificationPriority',
    'NotificationStatus',
    'NotificationChannel',
    # Phase 4: Interviews
    'Interview',
    'InterviewAvailability',
    'InterviewFeedback',
    'InterviewPipeline',
    'InterviewStage',
    'InterviewStatus',
    'InterviewFormat',
    'FeedbackRating',
    # Phase 4: Job Offers
    'JobOffer',
    'OfferNegotiation',
    'OfferStatus',
    'NegotiationType',
    'NegotiationStatus',
    # Phase 5: Analytics
    'HiringMetrics',
    'JobAnalytics',
    'CandidateAnalytics',
    'AIPerformanceMetrics',
    'MetricType',
    'ReportType',
    # Phase 6: Billing
    'PaymentMethod',
    'SubscriptionPlan',
    'BillingSubscription',
    'Invoice',
    'Payment',
    'UsageRecord',
    'BillingEvent',
    'BillingCycle',
    'PaymentStatus',
    'InvoiceStatus',
    'SubscriptionPlanType',
    # Phase 6: Admin
    'AdminUser',
    'AdminAuditLog',
    'PlatformConfiguration',
    'SystemMetrics',
    'UserActionLog',
    'FeatureFlag',
    'DataExport',
    'ComplianceRecord',
    'AdminRole',
    'AuditAction',
    'AuditResourceType',
    'ConfigurationType',
    # Phase 7: Integrations
    'Integration',
    'CalendarEvent',
    'VideoMeeting',
    'ATSSync',
    'CommunicationLog',
    'BackgroundCheck',
    'LinkedInProfile',
    'WebhookEndpoint',
    'WebhookEvent',
    'IntegrationType',
    'IntegrationProvider',
    'IntegrationStatus',
    # Phase 8: AI Features
    'ParsedResume',
    'AIScreening',
    'AIPrediction',
    'SkillTaxonomy',
    'AIModelMetrics',
    'CandidateInsight',
    'JobInsight',
    'ResumeParseStatus',
    'ScreeningDecision',
    'PredictionType',
    'ModelType',
    # Phase 9: Employee Onboarding
    'Employee',
    'OnboardingChecklist',
    'OnboardingTask',
    'TrainingProgram',
    'EmployeeTraining',
    'Equipment',
    'EmployeeDocument',
    'TimeOffRequest',
    'EmployeeReview',
    'EmploymentType',
    'EmploymentStatus',
    'OnboardingStatus',
    'TaskStatus',
    'TaskCategory',
    'TrainingStatus',
    'TrainingType',
    'EquipmentType',
    'EquipmentStatus',
    'DocumentType',
    'DocumentStatus',
    'TimeOffType',
    'TimeOffStatus',
    'ReviewType',
    'ReviewStatus',
]
