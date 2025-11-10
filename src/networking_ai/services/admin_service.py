"""
Admin Service - Phase 6.

Service for platform administration, audit logging, and compliance.
"""

from datetime import datetime, timedelta
from typing import Optional, List, Dict, Any
from sqlalchemy.orm import Session
from sqlalchemy import func, desc
import logging

from ..models.admin import (
    AdminUser,
    AuditLog,
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
from ..models.user import User
from ..models.company import Company

logger = logging.getLogger(__name__)


class AdminService:
    """
    Service for platform administration and management.
    """

    def __init__(self, notification_service=None):
        """Initialize admin service."""
        self.notification_service = notification_service

    # ==================== Admin Users ====================

    def create_admin_user(
        self,
        user_id: int,
        admin_role: AdminRole,
        permissions: Dict[str, bool] = None,
        granted_by_user_id: Optional[int] = None,
        notes: Optional[str] = None,
        db: Session = None
    ) -> AdminUser:
        """
        Grant admin privileges to a user.

        Args:
            user_id: User ID to grant admin access
            admin_role: Admin role
            permissions: Granular permissions dictionary
            granted_by_user_id: User who granted the admin access
            notes: Notes about admin grant
            db: Database session

        Returns:
            Created AdminUser
        """
        # Check if user exists
        user = db.query(User).get(user_id)
        if not user:
            raise ValueError("User not found")

        # Check if already admin
        existing = db.query(AdminUser).filter(AdminUser.user_id == user_id).first()
        if existing:
            raise ValueError("User is already an admin")

        admin_user = AdminUser(
            user_id=user_id,
            admin_role=admin_role,
            permissions=permissions or {},
            granted_by_user_id=granted_by_user_id,
            notes=notes
        )

        db.add(admin_user)
        db.commit()
        db.refresh(admin_user)

        # Log audit event
        self.log_audit(
            action=AuditAction.CREATE,
            resource_type=AuditResourceType.USER,
            resource_id=user_id,
            description=f"Granted {admin_role.value} admin access to user {user_id}",
            user_id=granted_by_user_id,
            db=db
        )

        logger.info(f"Created admin user {admin_user.id} for user {user_id}")
        return admin_user

    def revoke_admin_access(
        self,
        user_id: int,
        revoked_by_user_id: int,
        db: Session = None
    ) -> bool:
        """
        Revoke admin access from a user.

        Args:
            user_id: User ID to revoke admin access
            revoked_by_user_id: User who revoked the access
            db: Database session

        Returns:
            True if revoked successfully
        """
        admin_user = db.query(AdminUser).filter(AdminUser.user_id == user_id).first()
        if not admin_user:
            raise ValueError("User is not an admin")

        admin_user.is_active = False
        admin_user.revoked_at = datetime.utcnow()
        db.commit()

        # Log audit event
        self.log_audit(
            action=AuditAction.UPDATE,
            resource_type=AuditResourceType.USER,
            resource_id=user_id,
            description=f"Revoked admin access from user {user_id}",
            user_id=revoked_by_user_id,
            db=db
        )

        logger.info(f"Revoked admin access for user {user_id}")
        return True

    def get_admin_users(
        self,
        active_only: bool = True,
        admin_role: Optional[AdminRole] = None,
        db: Session = None
    ) -> List[AdminUser]:
        """
        Get list of admin users.

        Args:
            active_only: Only return active admins
            admin_role: Filter by admin role
            db: Database session

        Returns:
            List of AdminUser objects
        """
        query = db.query(AdminUser)

        if active_only:
            query = query.filter(AdminUser.is_active == True)

        if admin_role:
            query = query.filter(AdminUser.admin_role == admin_role)

        return query.order_by(AdminUser.created_at.desc()).all()

    # ==================== Audit Logging ====================

    def log_audit(
        self,
        action: AuditAction,
        description: str,
        resource_type: Optional[AuditResourceType] = None,
        resource_id: Optional[int] = None,
        user_id: Optional[int] = None,
        admin_user_id: Optional[int] = None,
        old_values: Optional[Dict[str, Any]] = None,
        new_values: Optional[Dict[str, Any]] = None,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None,
        success: bool = True,
        error_message: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
        db: Session = None
    ) -> AuditLog:
        """
        Create an audit log entry.

        Args:
            action: Action performed
            description: Description of action
            resource_type: Type of resource affected
            resource_id: ID of resource affected
            user_id: User who performed action
            admin_user_id: Admin user who performed action
            old_values: Values before change
            new_values: Values after change
            ip_address: IP address of request
            user_agent: User agent string
            success: Whether action was successful
            error_message: Error message if failed
            metadata: Additional metadata
            db: Database session

        Returns:
            Created AuditLog
        """
        # Get user email if user_id provided
        actor_email = None
        if user_id:
            user = db.query(User).get(user_id)
            if user:
                actor_email = user.email

        audit_log = AuditLog(
            user_id=user_id,
            admin_user_id=admin_user_id,
            actor_email=actor_email,
            action=action,
            resource_type=resource_type,
            resource_id=resource_id,
            description=description,
            old_values=old_values,
            new_values=new_values,
            ip_address=ip_address,
            user_agent=user_agent,
            success=success,
            error_message=error_message,
            metadata=metadata or {}
        )

        db.add(audit_log)
        db.commit()

        return audit_log

    def get_audit_logs(
        self,
        user_id: Optional[int] = None,
        resource_type: Optional[AuditResourceType] = None,
        resource_id: Optional[int] = None,
        action: Optional[AuditAction] = None,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        limit: int = 100,
        db: Session = None
    ) -> List[AuditLog]:
        """
        Query audit logs with filters.

        Args:
            user_id: Filter by user
            resource_type: Filter by resource type
            resource_id: Filter by specific resource
            action: Filter by action
            start_date: Filter by start date
            end_date: Filter by end date
            limit: Maximum number of results
            db: Database session

        Returns:
            List of AuditLog objects
        """
        query = db.query(AuditLog)

        if user_id:
            query = query.filter(AuditLog.user_id == user_id)

        if resource_type:
            query = query.filter(AuditLog.resource_type == resource_type)

        if resource_id:
            query = query.filter(AuditLog.resource_id == resource_id)

        if action:
            query = query.filter(AuditLog.action == action)

        if start_date:
            query = query.filter(AuditLog.timestamp >= start_date)

        if end_date:
            query = query.filter(AuditLog.timestamp <= end_date)

        return query.order_by(desc(AuditLog.timestamp)).limit(limit).all()

    # ==================== Platform Configuration ====================

    def get_configuration(
        self,
        config_key: str,
        db: Session = None
    ) -> Optional[PlatformConfiguration]:
        """
        Get a configuration value.

        Args:
            config_key: Configuration key
            db: Database session

        Returns:
            PlatformConfiguration or None
        """
        return db.query(PlatformConfiguration).filter(
            PlatformConfiguration.config_key == config_key
        ).first()

    def set_configuration(
        self,
        config_key: str,
        config_value: Any,
        config_type: ConfigurationType,
        description: Optional[str] = None,
        updated_by_user_id: Optional[int] = None,
        db: Session = None
    ) -> PlatformConfiguration:
        """
        Set a configuration value.

        Args:
            config_key: Configuration key
            config_value: Configuration value
            config_type: Configuration type
            description: Description
            updated_by_user_id: User who updated the config
            db: Database session

        Returns:
            PlatformConfiguration
        """
        config = db.query(PlatformConfiguration).filter(
            PlatformConfiguration.config_key == config_key
        ).first()

        if config:
            # Update existing
            config.previous_value = config.config_value
            config.config_value = config_value
            config.updated_by_user_id = updated_by_user_id
            config.updated_at = datetime.utcnow()
        else:
            # Create new
            config = PlatformConfiguration(
                config_key=config_key,
                config_value=config_value,
                config_type=config_type,
                description=description,
                updated_by_user_id=updated_by_user_id
            )
            db.add(config)

        db.commit()
        db.refresh(config)

        # Log audit event
        self.log_audit(
            action=AuditAction.UPDATE,
            resource_type=AuditResourceType.CONFIGURATION,
            resource_id=config.id,
            description=f"Updated configuration {config_key}",
            user_id=updated_by_user_id,
            new_values={"config_value": config_value},
            db=db
        )

        return config

    def get_all_configurations(
        self,
        config_type: Optional[ConfigurationType] = None,
        public_only: bool = False,
        db: Session = None
    ) -> List[PlatformConfiguration]:
        """
        Get all platform configurations.

        Args:
            config_type: Filter by configuration type
            public_only: Only return public configurations
            db: Database session

        Returns:
            List of PlatformConfiguration objects
        """
        query = db.query(PlatformConfiguration)

        if config_type:
            query = query.filter(PlatformConfiguration.config_type == config_type)

        if public_only:
            query = query.filter(PlatformConfiguration.is_public == True)

        return query.all()

    # ==================== System Metrics ====================

    def record_metric(
        self,
        metric_name: str,
        metric_value: float,
        metric_unit: Optional[str] = None,
        dimensions: Optional[Dict[str, Any]] = None,
        aggregation_period: Optional[str] = None,
        db: Session = None
    ):
        """
        Record a system metric.

        Args:
            metric_name: Name of the metric
            metric_value: Metric value
            metric_unit: Unit of measurement
            dimensions: Additional dimensions
            aggregation_period: Aggregation period
            db: Database session
        """
        metric = SystemMetrics(
            metric_name=metric_name,
            metric_value=metric_value,
            metric_unit=metric_unit,
            dimensions=dimensions or {},
            aggregation_period=aggregation_period
        )

        db.add(metric)
        db.commit()

    def get_metrics(
        self,
        metric_name: str,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        aggregation_period: Optional[str] = None,
        db: Session = None
    ) -> List[SystemMetrics]:
        """
        Query system metrics.

        Args:
            metric_name: Metric name
            start_date: Start date
            end_date: End date
            aggregation_period: Aggregation period
            db: Database session

        Returns:
            List of SystemMetrics
        """
        query = db.query(SystemMetrics).filter(SystemMetrics.metric_name == metric_name)

        if start_date:
            query = query.filter(SystemMetrics.recorded_at >= start_date)

        if end_date:
            query = query.filter(SystemMetrics.recorded_at <= end_date)

        if aggregation_period:
            query = query.filter(SystemMetrics.aggregation_period == aggregation_period)

        return query.order_by(SystemMetrics.recorded_at.desc()).all()

    # ==================== Feature Flags ====================

    def create_feature_flag(
        self,
        feature_key: str,
        feature_name: str,
        description: Optional[str] = None,
        is_enabled: bool = False,
        rollout_type: str = "all",
        db: Session = None
    ) -> FeatureFlag:
        """
        Create a feature flag.

        Args:
            feature_key: Unique feature key
            feature_name: Display name
            description: Description
            is_enabled: Whether feature is enabled
            rollout_type: Rollout strategy
            db: Database session

        Returns:
            Created FeatureFlag
        """
        flag = FeatureFlag(
            feature_key=feature_key,
            feature_name=feature_name,
            description=description,
            is_enabled=is_enabled,
            rollout_type=rollout_type
        )

        db.add(flag)
        db.commit()
        db.refresh(flag)

        logger.info(f"Created feature flag {flag.id}: {feature_key}")
        return flag

    def toggle_feature_flag(
        self,
        feature_key: str,
        is_enabled: bool,
        db: Session = None
    ) -> FeatureFlag:
        """
        Toggle a feature flag.

        Args:
            feature_key: Feature key
            is_enabled: Enable/disable
            db: Database session

        Returns:
            Updated FeatureFlag
        """
        flag = db.query(FeatureFlag).filter(FeatureFlag.feature_key == feature_key).first()
        if not flag:
            raise ValueError("Feature flag not found")

        flag.is_enabled = is_enabled
        flag.updated_at = datetime.utcnow()
        db.commit()

        logger.info(f"Toggled feature flag {feature_key} to {is_enabled}")
        return flag

    def is_feature_enabled(
        self,
        feature_key: str,
        user_id: Optional[int] = None,
        company_id: Optional[int] = None,
        role: Optional[str] = None,
        db: Session = None
    ) -> bool:
        """
        Check if a feature is enabled for a user.

        Args:
            feature_key: Feature key
            user_id: User ID
            company_id: Company ID
            role: User role
            db: Database session

        Returns:
            True if feature is enabled
        """
        flag = db.query(FeatureFlag).filter(FeatureFlag.feature_key == feature_key).first()
        if not flag:
            return False

        return flag.is_enabled_for_user(user_id, company_id, role)

    # ==================== Data Export ====================

    def request_data_export(
        self,
        user_id: int,
        export_type: str = "full",
        data_types: List[str] = None,
        file_format: str = "json",
        company_id: Optional[int] = None,
        db: Session = None
    ) -> DataExport:
        """
        Request a data export for a user.

        Args:
            user_id: User ID
            export_type: Export type
            data_types: Data types to export
            file_format: File format
            company_id: Optional company ID
            db: Database session

        Returns:
            Created DataExport
        """
        export = DataExport(
            user_id=user_id,
            company_id=company_id,
            export_type=export_type,
            data_types=data_types or [],
            file_format=file_format,
            status="pending"
        )

        db.add(export)
        db.commit()
        db.refresh(export)

        # Log audit event
        self.log_audit(
            action=AuditAction.EXPORT,
            resource_type=AuditResourceType.USER,
            resource_id=user_id,
            description=f"Requested data export for user {user_id}",
            user_id=user_id,
            db=db
        )

        logger.info(f"Created data export request {export.id} for user {user_id}")
        return export

    # ==================== Compliance ====================

    def create_compliance_record(
        self,
        compliance_type: str,
        action: str,
        description: str,
        user_id: Optional[int] = None,
        company_id: Optional[int] = None,
        regulation: Optional[str] = None,
        due_date: Optional[datetime] = None,
        db: Session = None
    ) -> ComplianceRecord:
        """
        Create a compliance record.

        Args:
            compliance_type: Type of compliance
            action: Action taken
            description: Description
            user_id: User ID
            company_id: Company ID
            regulation: Regulation (GDPR, CCPA, etc.)
            due_date: Due date
            db: Database session

        Returns:
            Created ComplianceRecord
        """
        record = ComplianceRecord(
            user_id=user_id,
            company_id=company_id,
            compliance_type=compliance_type,
            regulation=regulation,
            action=action,
            description=description,
            status="pending",
            due_date=due_date
        )

        db.add(record)
        db.commit()
        db.refresh(record)

        logger.info(f"Created compliance record {record.id}")
        return record

    def get_compliance_records(
        self,
        user_id: Optional[int] = None,
        company_id: Optional[int] = None,
        compliance_type: Optional[str] = None,
        status: Optional[str] = None,
        db: Session = None
    ) -> List[ComplianceRecord]:
        """
        Query compliance records.

        Args:
            user_id: Filter by user
            company_id: Filter by company
            compliance_type: Filter by type
            status: Filter by status
            db: Database session

        Returns:
            List of ComplianceRecord objects
        """
        query = db.query(ComplianceRecord)

        if user_id:
            query = query.filter(ComplianceRecord.user_id == user_id)

        if company_id:
            query = query.filter(ComplianceRecord.company_id == company_id)

        if compliance_type:
            query = query.filter(ComplianceRecord.compliance_type == compliance_type)

        if status:
            query = query.filter(ComplianceRecord.status == status)

        return query.order_by(desc(ComplianceRecord.created_at)).all()

    # ==================== User Actions ====================

    def log_user_action(
        self,
        user_id: Optional[int],
        action_type: str,
        action_category: Optional[str] = None,
        page_url: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
        session_id: Optional[str] = None,
        ip_address: Optional[str] = None,
        db: Session = None
    ):
        """
        Log a user action for analytics.

        Args:
            user_id: User ID
            action_type: Action type
            action_category: Action category
            page_url: Page URL
            metadata: Additional metadata
            session_id: Session ID
            ip_address: IP address
            db: Database session
        """
        action_log = UserActionLog(
            user_id=user_id,
            session_id=session_id,
            action_type=action_type,
            action_category=action_category,
            page_url=page_url,
            ip_address=ip_address,
            metadata=metadata or {}
        )

        db.add(action_log)
        db.commit()


def create_admin_service(notification_service=None) -> AdminService:
    """
    Factory function to create AdminService.

    Args:
        notification_service: Optional notification service

    Returns:
        AdminService instance
    """
    return AdminService(notification_service=notification_service)
