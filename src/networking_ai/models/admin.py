"""
Admin and Platform Management Models - Phase 6.

Models for platform administration, audit logging, and compliance.
"""

from datetime import datetime
from enum import Enum
from typing import Optional, Dict, Any
from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, Boolean, Text, JSON, Enum as SQLEnum, Float
from sqlalchemy.orm import relationship

from ..database import Base


class AdminRole(str, Enum):
    """Admin role types."""
    SUPER_ADMIN = "super_admin"
    PLATFORM_ADMIN = "platform_admin"
    SUPPORT_ADMIN = "support_admin"
    CONTENT_MODERATOR = "content_moderator"
    BILLING_ADMIN = "billing_admin"


class AuditAction(str, Enum):
    """Audit action types."""
    CREATE = "create"
    READ = "read"
    UPDATE = "update"
    DELETE = "delete"
    LOGIN = "login"
    LOGOUT = "logout"
    EXPORT = "export"
    IMPORT = "import"
    APPROVE = "approve"
    REJECT = "reject"
    SUSPEND = "suspend"
    ACTIVATE = "activate"


class AuditResourceType(str, Enum):
    """Resource types for audit logging."""
    USER = "user"
    COMPANY = "company"
    JOB = "job"
    APPLICATION = "application"
    INTERVIEW = "interview"
    OFFER = "offer"
    SUBSCRIPTION = "subscription"
    PAYMENT = "payment"
    INVOICE = "invoice"
    AI_AGENT = "ai_agent"
    CONFIGURATION = "configuration"


class ConfigurationType(str, Enum):
    """Platform configuration types."""
    GENERAL = "general"
    SECURITY = "security"
    EMAIL = "email"
    AI = "ai"
    BILLING = "billing"
    FEATURES = "features"
    LIMITS = "limits"


class AdminUser(Base):
    """
    Platform administrator.

    Tracks admin users with elevated permissions.
    """
    __tablename__ = "admin_users"

    # Primary Key
    id = Column(Integer, primary_key=True, index=True)

    # Foreign Key
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, unique=True, index=True)

    # Admin Details
    admin_role = Column(SQLEnum(AdminRole), nullable=False, index=True)
    permissions = Column(JSON, default=dict)  # Granular permissions

    # Status
    is_active = Column(Boolean, default=True)

    # Two-Factor Authentication
    two_factor_enabled = Column(Boolean, default=False)
    two_factor_secret = Column(String(255), nullable=True)

    # Access Control
    ip_whitelist = Column(JSON, default=list)  # List of allowed IPs
    last_login_at = Column(DateTime, nullable=True)
    last_login_ip = Column(String(45), nullable=True)

    # Metadata
    notes = Column(Text, nullable=True)
    granted_by_user_id = Column(Integer, ForeignKey("users.id"), nullable=True)

    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow, index=True)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    revoked_at = Column(DateTime, nullable=True)

    # Relationships
    user = relationship("User", foreign_keys=[user_id], back_populates="admin_user")
    granted_by = relationship("User", foreign_keys=[granted_by_user_id])
    audit_logs = relationship("AuditLog", back_populates="admin_user")

    def has_permission(self, permission: str) -> bool:
        """Check if admin has specific permission."""
        if self.admin_role == AdminRole.SUPER_ADMIN:
            return True
        return self.permissions.get(permission, False)


class AuditLog(Base):
    """
    Audit log for tracking all system activities.

    Comprehensive logging for compliance and security.
    """
    __tablename__ = "audit_logs"

    # Primary Key
    id = Column(Integer, primary_key=True, index=True)

    # Actor (who performed the action)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=True, index=True)
    admin_user_id = Column(Integer, ForeignKey("admin_users.id"), nullable=True, index=True)
    actor_email = Column(String(255), nullable=True, index=True)
    actor_role = Column(String(50), nullable=True)

    # Action Details
    action = Column(SQLEnum(AuditAction), nullable=False, index=True)
    resource_type = Column(SQLEnum(AuditResourceType), nullable=True, index=True)
    resource_id = Column(Integer, nullable=True, index=True)

    # Description
    description = Column(Text, nullable=False)

    # Before/After State (for updates)
    old_values = Column(JSON, nullable=True)
    new_values = Column(JSON, nullable=True)

    # Request Context
    ip_address = Column(String(45), nullable=True, index=True)
    user_agent = Column(Text, nullable=True)
    request_method = Column(String(10), nullable=True)
    request_path = Column(String(500), nullable=True)

    # Status
    success = Column(Boolean, default=True)
    error_message = Column(Text, nullable=True)

    # Metadata
    metadata = Column(JSON, default=dict)

    # Timestamps
    timestamp = Column(DateTime, default=datetime.utcnow, index=True)

    # Relationships
    user = relationship("User", foreign_keys=[user_id])
    admin_user = relationship("AdminUser", foreign_keys=[admin_user_id], back_populates="audit_logs")

    def to_dict(self) -> Dict[str, Any]:
        """Convert audit log to dictionary."""
        return {
            "id": self.id,
            "user_id": self.user_id,
            "actor_email": self.actor_email,
            "action": self.action.value if self.action else None,
            "resource_type": self.resource_type.value if self.resource_type else None,
            "resource_id": self.resource_id,
            "description": self.description,
            "ip_address": self.ip_address,
            "success": self.success,
            "timestamp": self.timestamp.isoformat() if self.timestamp else None,
        }


class PlatformConfiguration(Base):
    """
    Platform-wide configuration settings.

    Stores configurable platform settings.
    """
    __tablename__ = "platform_configurations"

    # Primary Key
    id = Column(Integer, primary_key=True, index=True)

    # Configuration Details
    config_type = Column(SQLEnum(ConfigurationType), nullable=False, index=True)
    config_key = Column(String(100), nullable=False, unique=True, index=True)
    config_value = Column(JSON, nullable=False)

    # Metadata
    description = Column(Text, nullable=True)
    is_public = Column(Boolean, default=False)  # Whether users can see this config
    is_editable = Column(Boolean, default=True)  # Whether admins can edit

    # Validation
    validation_rules = Column(JSON, nullable=True)  # JSON schema for validation

    # Change Tracking
    updated_by_user_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    previous_value = Column(JSON, nullable=True)

    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    updated_by = relationship("User", foreign_keys=[updated_by_user_id])


class SystemMetrics(Base):
    """
    System-wide metrics and statistics.

    Tracks platform health and usage metrics.
    """
    __tablename__ = "system_metrics"

    # Primary Key
    id = Column(Integer, primary_key=True, index=True)

    # Metric Details
    metric_name = Column(String(100), nullable=False, index=True)
    metric_value = Column(Float, nullable=False)
    metric_unit = Column(String(50), nullable=True)

    # Dimensions
    dimensions = Column(JSON, default=dict)  # Additional metric dimensions

    # Aggregation
    aggregation_period = Column(String(20), nullable=True)  # hourly, daily, monthly
    period_start = Column(DateTime, nullable=True, index=True)
    period_end = Column(DateTime, nullable=True)

    # Timestamps
    recorded_at = Column(DateTime, default=datetime.utcnow, index=True)

    # Indexes for time-series queries
    __table_args__ = (
        {'mysql_engine': 'InnoDB'},
    )


class UserActionLog(Base):
    """
    User action tracking for analytics.

    Tracks user behavior for product analytics.
    """
    __tablename__ = "user_action_logs"

    # Primary Key
    id = Column(Integer, primary_key=True, index=True)

    # User Details
    user_id = Column(Integer, ForeignKey("users.id"), nullable=True, index=True)
    session_id = Column(String(255), nullable=True, index=True)

    # Action Details
    action_type = Column(String(100), nullable=False, index=True)
    action_category = Column(String(50), nullable=True, index=True)

    # Page/Screen Info
    page_url = Column(String(500), nullable=True)
    page_title = Column(String(255), nullable=True)
    referrer_url = Column(String(500), nullable=True)

    # Device Info
    device_type = Column(String(50), nullable=True)  # desktop, mobile, tablet
    browser = Column(String(100), nullable=True)
    os = Column(String(100), nullable=True)
    screen_resolution = Column(String(20), nullable=True)

    # Location
    ip_address = Column(String(45), nullable=True)
    country = Column(String(2), nullable=True)
    region = Column(String(100), nullable=True)
    city = Column(String(100), nullable=True)

    # Performance
    page_load_time = Column(Integer, nullable=True)  # milliseconds

    # Metadata
    metadata = Column(JSON, default=dict)

    # Timestamps
    timestamp = Column(DateTime, default=datetime.utcnow, index=True)

    # Relationships
    user = relationship("User", foreign_keys=[user_id])


class FeatureFlag(Base):
    """
    Feature flag for gradual rollouts.

    Enables/disables features for specific users or groups.
    """
    __tablename__ = "feature_flags"

    # Primary Key
    id = Column(Integer, primary_key=True, index=True)

    # Feature Details
    feature_key = Column(String(100), nullable=False, unique=True, index=True)
    feature_name = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)

    # Status
    is_enabled = Column(Boolean, default=False, index=True)

    # Rollout Strategy
    rollout_percentage = Column(Float, default=0.0)  # 0-100
    rollout_type = Column(String(50), default="all")  # all, whitelist, percentage, gradual

    # Targeting
    enabled_for_users = Column(JSON, default=list)  # List of user IDs
    enabled_for_companies = Column(JSON, default=list)  # List of company IDs
    enabled_for_roles = Column(JSON, default=list)  # List of roles

    # Environment
    environments = Column(JSON, default=list)  # ["production", "staging", "development"]

    # Metadata
    owner = Column(String(255), nullable=True)
    tags = Column(JSON, default=list)

    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    expires_at = Column(DateTime, nullable=True)

    def is_enabled_for_user(self, user_id: int, company_id: Optional[int] = None, role: Optional[str] = None) -> bool:
        """Check if feature is enabled for a specific user."""
        if not self.is_enabled:
            return False

        # Check whitelist
        if self.rollout_type == "whitelist":
            if user_id in self.enabled_for_users:
                return True
            if company_id and company_id in self.enabled_for_companies:
                return True
            if role and role in self.enabled_for_roles:
                return True
            return False

        # Check percentage rollout
        if self.rollout_type == "percentage":
            # Use deterministic hash to ensure consistent experience
            import hashlib
            hash_val = int(hashlib.md5(f"{self.feature_key}:{user_id}".encode()).hexdigest(), 16)
            return (hash_val % 100) < self.rollout_percentage

        # Default: enabled for all
        return True


class DataExport(Base):
    """
    Data export requests and tracking.

    Tracks user data export requests for GDPR compliance.
    """
    __tablename__ = "data_exports"

    # Primary Key
    id = Column(Integer, primary_key=True, index=True)

    # User Details
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    company_id = Column(Integer, ForeignKey("companies.id"), nullable=True, index=True)

    # Export Details
    export_type = Column(String(50), nullable=False)  # full, partial, specific
    data_types = Column(JSON, default=list)  # List of data types to export

    # Status
    status = Column(String(50), default="pending", index=True)  # pending, processing, completed, failed

    # File Info
    file_format = Column(String(20), default="json")  # json, csv, xml
    file_size_bytes = Column(Integer, nullable=True)
    file_url = Column(String(500), nullable=True)
    file_expires_at = Column(DateTime, nullable=True)

    # Processing
    started_at = Column(DateTime, nullable=True)
    completed_at = Column(DateTime, nullable=True)
    error_message = Column(Text, nullable=True)

    # Metadata
    requested_by_ip = Column(String(45), nullable=True)
    metadata = Column(JSON, default=dict)

    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow, index=True)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    user = relationship("User", foreign_keys=[user_id])
    company = relationship("Company", foreign_keys=[company_id])


class ComplianceRecord(Base):
    """
    Compliance and regulatory records.

    Tracks compliance-related actions and records.
    """
    __tablename__ = "compliance_records"

    # Primary Key
    id = Column(Integer, primary_key=True, index=True)

    # Subject
    user_id = Column(Integer, ForeignKey("users.id"), nullable=True, index=True)
    company_id = Column(Integer, ForeignKey("companies.id"), nullable=True, index=True)

    # Compliance Type
    compliance_type = Column(String(100), nullable=False, index=True)  # gdpr_consent, data_deletion, etc.
    regulation = Column(String(50), nullable=True)  # GDPR, CCPA, HIPAA, etc.

    # Action Details
    action = Column(String(100), nullable=False)
    description = Column(Text, nullable=False)

    # Status
    status = Column(String(50), default="pending", index=True)

    # Evidence
    evidence = Column(JSON, default=dict)  # Supporting documentation/data

    # Processing
    processed_by_user_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    processed_at = Column(DateTime, nullable=True)

    # Deadlines
    due_date = Column(DateTime, nullable=True)
    completed_at = Column(DateTime, nullable=True)

    # Metadata
    metadata = Column(JSON, default=dict)

    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow, index=True)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    user = relationship("User", foreign_keys=[user_id])
    company = relationship("Company", foreign_keys=[company_id])
    processed_by = relationship("User", foreign_keys=[processed_by_user_id])
