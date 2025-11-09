"""
Marketplace Models - AI Agent Template Marketplace (Phase 12).

Models for agent template publishing, purchasing, reviews, and installations.
"""

from datetime import datetime
from enum import Enum
from typing import Optional, List
from decimal import Decimal

from sqlalchemy import Column, Integer, String, Boolean, DateTime, Enum as SQLEnum, Text, DECIMAL, JSON, ForeignKey
from sqlalchemy.dialects.postgresql import UUID, ARRAY
from sqlalchemy.orm import relationship
import uuid

from ..database import Base


class TemplateCategory(str, Enum):
    """Agent template categories."""
    CAREER_COACH = "career_coach"  # Career coaching and guidance
    INTERVIEW_PREP = "interview_prep"  # Interview preparation
    RESUME_BUILDER = "resume_builder"  # Resume optimization
    JOB_SEARCH = "job_search"  # Job search assistance
    NETWORKING = "networking"  # Professional networking
    SKILL_DEVELOPMENT = "skill_development"  # Skill learning and development
    SALARY_NEGOTIATION = "salary_negotiation"  # Salary and offer negotiation
    RECRUITER_ASSISTANT = "recruiter_assistant"  # Recruiting and hiring
    COMPANY_ADMIN = "company_admin"  # Company administration
    GENERAL_PURPOSE = "general_purpose"  # General purpose agents
    CUSTOM = "custom"  # Custom/other


class TemplateStatus(str, Enum):
    """Template publication status."""
    DRAFT = "draft"  # Being created
    PENDING_REVIEW = "pending_review"  # Submitted for approval
    PUBLISHED = "published"  # Live in marketplace
    REJECTED = "rejected"  # Rejected by admin
    ARCHIVED = "archived"  # Removed from marketplace


class AgentTemplate(Base):
    """
    Agent Template model for marketplace.

    Represents a reusable AI agent configuration that users can purchase and install.
    """
    __tablename__ = "agent_templates"
    __table_args__ = {'extend_existing': True}

    # Primary Key
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, index=True)

    # Creator
    creator_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)

    # Basic Info
    name = Column(String(255), nullable=False, index=True)
    description = Column(Text, nullable=False)
    category = Column(SQLEnum(TemplateCategory), nullable=False, index=True)
    tags = Column(ARRAY(String), default=list)  # Searchable tags

    # Status & Publishing
    status = Column(SQLEnum(TemplateStatus), default=TemplateStatus.DRAFT, nullable=False, index=True)
    is_featured = Column(Boolean, default=False, index=True)  # Featured in marketplace
    is_verified = Column(Boolean, default=False)  # Verified by platform

    # Pricing
    price = Column(DECIMAL(10, 2), default=Decimal('0.00'), nullable=False)  # USD, 0.00 = free

    # Versioning
    version = Column(String(50), default="1.0.0", nullable=False)
    changelog = Column(Text, nullable=True)  # Version changelog

    # Configuration (JSON)
    configuration = Column(JSON, nullable=False)  # Agent configuration
    prompt_template = Column(Text, nullable=False)  # Agent system prompt
    knowledge_sources = Column(JSON, default=dict)  # Knowledge base configuration
    sub_agents = Column(JSON, default=list)  # Sub-agent configurations

    # Metadata
    icon_url = Column(String(500), nullable=True)  # Template icon/avatar
    screenshots = Column(ARRAY(String), default=list)  # Screenshot URLs
    demo_url = Column(String(500), nullable=True)  # Demo video/page

    # Statistics
    downloads_count = Column(Integer, default=0, nullable=False, index=True)
    installations_count = Column(Integer, default=0, nullable=False)
    revenue_total = Column(DECIMAL(10, 2), default=Decimal('0.00'), nullable=False)
    average_rating = Column(DECIMAL(3, 2), default=Decimal('0.00'))  # 0.00 - 5.00
    review_count = Column(Integer, default=0, nullable=False)

    # Admin fields
    admin_notes = Column(Text, nullable=True)  # Admin review notes
    reviewed_by = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    reviewed_at = Column(DateTime(timezone=True), nullable=True)
    rejection_reason = Column(Text, nullable=True)

    # Timestamps
    created_at = Column(DateTime(timezone=True), default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime(timezone=True), default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    published_at = Column(DateTime(timezone=True), nullable=True)
    archived_at = Column(DateTime(timezone=True), nullable=True)

    # Relationships
    creator = relationship("User", foreign_keys=[creator_id], backref="created_templates")
    reviewer = relationship("User", foreign_keys=[reviewed_by])
    purchases = relationship("TemplatePurchase", back_populates="template", cascade="all, delete-orphan")
    reviews = relationship("TemplateReview", back_populates="template", cascade="all, delete-orphan")
    installations = relationship("TemplateInstallation", back_populates="template", cascade="all, delete-orphan")


class TemplatePurchase(Base):
    """
    Template Purchase model.

    Records when a user purchases a paid template.
    """
    __tablename__ = "template_purchases"
    __table_args__ = {'extend_existing': True}

    # Primary Key
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, index=True)

    # References
    template_id = Column(UUID(as_uuid=True), ForeignKey("agent_templates.id", ondelete="CASCADE"), nullable=False, index=True)
    buyer_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)

    # Payment Details
    price_paid = Column(DECIMAL(10, 2), nullable=False)  # Price at time of purchase
    stripe_payment_id = Column(String(255), unique=True, index=True)  # Stripe Payment Intent ID
    stripe_charge_id = Column(String(255), nullable=True)  # Stripe Charge ID

    # Status
    refunded = Column(Boolean, default=False, nullable=False)
    refund_amount = Column(DECIMAL(10, 2), nullable=True)
    refund_reason = Column(Text, nullable=True)
    refunded_at = Column(DateTime(timezone=True), nullable=True)

    # Timestamps
    purchased_at = Column(DateTime(timezone=True), default=datetime.utcnow, nullable=False, index=True)

    # Relationships
    template = relationship("AgentTemplate", back_populates="purchases")
    buyer = relationship("User", backref="template_purchases")


class TemplateReview(Base):
    """
    Template Review model.

    User reviews and ratings for templates.
    """
    __tablename__ = "template_reviews"
    __table_args__ = {'extend_existing': True}

    # Primary Key
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, index=True)

    # References
    template_id = Column(UUID(as_uuid=True), ForeignKey("agent_templates.id", ondelete="CASCADE"), nullable=False, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)

    # Review Content
    rating = Column(Integer, nullable=False)  # 1-5 stars
    title = Column(String(255), nullable=True)  # Review title
    review_text = Column(Text, nullable=True)  # Review body

    # Engagement
    helpful_count = Column(Integer, default=0, nullable=False)  # How many found it helpful

    # Moderation
    is_verified_purchase = Column(Boolean, default=False)  # Did user actually purchase?
    is_flagged = Column(Boolean, default=False)  # Flagged for review
    is_hidden = Column(Boolean, default=False)  # Hidden by admin

    # Creator Response
    creator_response = Column(Text, nullable=True)  # Template creator's response
    creator_responded_at = Column(DateTime(timezone=True), nullable=True)

    # Timestamps
    created_at = Column(DateTime(timezone=True), default=datetime.utcnow, nullable=False, index=True)
    updated_at = Column(DateTime(timezone=True), default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    # Relationships
    template = relationship("AgentTemplate", back_populates="reviews")
    user = relationship("User", backref="template_reviews")


class TemplateInstallation(Base):
    """
    Template Installation model.

    Tracks when users install templates and create agents from them.
    """
    __tablename__ = "template_installations"
    __table_args__ = {'extend_existing': True}

    # Primary Key
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, index=True)

    # References
    template_id = Column(UUID(as_uuid=True), ForeignKey("agent_templates.id", ondelete="CASCADE"), nullable=False, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    agent_id = Column(Integer, ForeignKey("personal_ai_agents.id", ondelete="SET NULL"), nullable=True)  # Created agent

    # Installation Details
    customized = Column(Boolean, default=False)  # Did user customize during install?
    custom_configuration = Column(JSON, nullable=True)  # Custom config overrides

    # Status
    installation_successful = Column(Boolean, default=True, nullable=False)
    error_message = Column(Text, nullable=True)  # If installation failed

    # Usage tracking
    is_active = Column(Boolean, default=True)  # Is the installed agent still active?
    deleted_at = Column(DateTime(timezone=True), nullable=True)

    # Timestamps
    installed_at = Column(DateTime(timezone=True), default=datetime.utcnow, nullable=False, index=True)

    # Relationships
    template = relationship("AgentTemplate", back_populates="installations")
    user = relationship("User", backref="template_installations")
    agent = relationship("PersonalAIAgent", backref="installed_from_template")


class CreatorFollow(Base):
    """
    Creator Follow model.

    Allows users to follow template creators.
    """
    __tablename__ = "creator_follows"
    __table_args__ = {'extend_existing': True}

    # Primary Key
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, index=True)

    # References
    follower_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    creator_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)

    # Timestamps
    followed_at = Column(DateTime(timezone=True), default=datetime.utcnow, nullable=False)

    # Relationships
    follower = relationship("User", foreign_keys=[follower_id], backref="following_creators")
    creator = relationship("User", foreign_keys=[creator_id], backref="followers")


class TemplateComment(Base):
    """
    Template Comment model.

    User comments and questions on templates.
    """
    __tablename__ = "template_comments"
    __table_args__ = {'extend_existing': True}

    # Primary Key
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, index=True)

    # References
    template_id = Column(UUID(as_uuid=True), ForeignKey("agent_templates.id", ondelete="CASCADE"), nullable=False, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    parent_comment_id = Column(UUID(as_uuid=True), ForeignKey("template_comments.id", ondelete="CASCADE"), nullable=True)  # For replies

    # Content
    comment_text = Column(Text, nullable=False)

    # Moderation
    is_flagged = Column(Boolean, default=False)
    is_hidden = Column(Boolean, default=False)

    # Timestamps
    created_at = Column(DateTime(timezone=True), default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime(timezone=True), default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    deleted_at = Column(DateTime(timezone=True), nullable=True)

    # Relationships
    template = relationship("AgentTemplate", backref="comments")
    user = relationship("User", backref="template_comments")
    parent_comment = relationship("TemplateComment", remote_side=[id], backref="replies")
