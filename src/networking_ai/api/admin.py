"""
Admin API Endpoints - Phase 6.

REST API for platform administration, audit logging, and compliance.
"""

from typing import List, Optional
from datetime import datetime, timedelta
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from pydantic import BaseModel, Field

from ..database import get_db
from ..models.admin import (
    AdminUser,
    AuditLog,
    PlatformConfiguration,
    SystemMetrics,
    FeatureFlag,
    DataExport,
    ComplianceRecord,
    AdminRole,
    AuditAction,
    AuditResourceType,
    ConfigurationType
)
from ..services.admin_service import (
    AdminService,
    create_admin_service
)


# ==================== Request/Response Models ====================

class AdminUserCreate(BaseModel):
    """Create admin user request."""
    user_id: int
    admin_role: AdminRole
    permissions: Optional[dict] = {}
    notes: Optional[str] = None


class AdminUserResponse(BaseModel):
    """Admin user response."""
    id: int
    user_id: int
    admin_role: AdminRole
    is_active: bool
    two_factor_enabled: bool
    last_login_at: Optional[datetime] = None
    created_at: datetime

    class Config:
        from_attributes = True


class AuditLogCreate(BaseModel):
    """Create audit log request."""
    action: AuditAction
    description: str
    resource_type: Optional[AuditResourceType] = None
    resource_id: Optional[int] = None
    old_values: Optional[dict] = None
    new_values: Optional[dict] = None
    metadata: Optional[dict] = {}


class AuditLogResponse(BaseModel):
    """Audit log response."""
    id: int
    user_id: Optional[int] = None
    actor_email: Optional[str] = None
    action: AuditAction
    resource_type: Optional[AuditResourceType] = None
    resource_id: Optional[int] = None
    description: str
    ip_address: Optional[str] = None
    success: bool
    timestamp: datetime

    class Config:
        from_attributes = True


class ConfigurationSet(BaseModel):
    """Set configuration request."""
    config_key: str
    config_value: Any
    config_type: ConfigurationType
    description: Optional[str] = None


class ConfigurationResponse(BaseModel):
    """Configuration response."""
    id: int
    config_type: ConfigurationType
    config_key: str
    config_value: Any
    description: Optional[str] = None
    is_public: bool
    updated_at: datetime

    class Config:
        from_attributes = True


class FeatureFlagCreate(BaseModel):
    """Create feature flag request."""
    feature_key: str
    feature_name: str
    description: Optional[str] = None
    is_enabled: bool = False
    rollout_type: str = "all"
    rollout_percentage: float = 0.0


class FeatureFlagResponse(BaseModel):
    """Feature flag response."""
    id: int
    feature_key: str
    feature_name: str
    description: Optional[str] = None
    is_enabled: bool
    rollout_type: str
    rollout_percentage: float
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class DataExportRequest(BaseModel):
    """Data export request."""
    export_type: str = "full"
    data_types: Optional[List[str]] = []
    file_format: str = "json"


class DataExportResponse(BaseModel):
    """Data export response."""
    id: int
    export_type: str
    status: str
    file_format: str
    file_url: Optional[str] = None
    file_expires_at: Optional[datetime] = None
    created_at: datetime
    completed_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class ComplianceRecordCreate(BaseModel):
    """Create compliance record request."""
    compliance_type: str
    action: str
    description: str
    regulation: Optional[str] = None
    due_date: Optional[datetime] = None


class ComplianceRecordResponse(BaseModel):
    """Compliance record response."""
    id: int
    compliance_type: str
    regulation: Optional[str] = None
    action: str
    description: str
    status: str
    due_date: Optional[datetime] = None
    created_at: datetime
    completed_at: Optional[datetime] = None

    class Config:
        from_attributes = True


# ==================== Router Setup ====================

router = APIRouter(prefix="/api/admin", tags=["admin"])


# ==================== Helper Functions ====================

def get_admin_service() -> AdminService:
    """Get admin service instance."""
    return create_admin_service()


def verify_admin_access(admin_user_id: int, required_role: AdminRole = None, db: Session = None) -> bool:
    """Verify user has admin access."""
    admin_user = db.query(AdminUser).filter(
        AdminUser.id == admin_user_id,
        AdminUser.is_active == True
    ).first()

    if not admin_user:
        return False

    if required_role and admin_user.admin_role != AdminRole.SUPER_ADMIN:
        if admin_user.admin_role != required_role:
            return False

    return True


# ==================== Admin Users ====================

@router.post("/users", response_model=AdminUserResponse, status_code=status.HTTP_201_CREATED)
def create_admin_user(
    admin_user: AdminUserCreate,
    current_admin_id: int,  # Should come from auth
    db: Session = Depends(get_db),
    service: AdminService = Depends(get_admin_service)
):
    """
    Grant admin access to a user (Super Admin only).

    Creates admin privileges for the specified user.
    """
    # Verify requester is super admin
    if not verify_admin_access(current_admin_id, AdminRole.SUPER_ADMIN, db):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Requires super admin access"
        )

    try:
        created = service.create_admin_user(
            user_id=admin_user.user_id,
            admin_role=admin_user.admin_role,
            permissions=admin_user.permissions,
            granted_by_user_id=current_admin_id,
            notes=admin_user.notes,
            db=db
        )
        return created
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )


@router.get("/users", response_model=List[AdminUserResponse])
def list_admin_users(
    active_only: bool = True,
    admin_role: Optional[AdminRole] = None,
    current_admin_id: int = Query(...),  # Should come from auth
    db: Session = Depends(get_db),
    service: AdminService = Depends(get_admin_service)
):
    """
    List all admin users.

    Returns list of users with admin privileges.
    """
    # Verify requester is admin
    if not verify_admin_access(current_admin_id, db=db):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Requires admin access"
        )

    admins = service.get_admin_users(
        active_only=active_only,
        admin_role=admin_role,
        db=db
    )
    return admins


@router.delete("/users/{user_id}")
def revoke_admin_access(
    user_id: int,
    current_admin_id: int,  # Should come from auth
    db: Session = Depends(get_db),
    service: AdminService = Depends(get_admin_service)
):
    """
    Revoke admin access from a user (Super Admin only).

    Removes admin privileges from the specified user.
    """
    # Verify requester is super admin
    if not verify_admin_access(current_admin_id, AdminRole.SUPER_ADMIN, db):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Requires super admin access"
        )

    try:
        service.revoke_admin_access(
            user_id=user_id,
            revoked_by_user_id=current_admin_id,
            db=db
        )
        return {"message": "Admin access revoked successfully"}
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e)
        )


# ==================== Audit Logs ====================

@router.post("/audit-logs", response_model=AuditLogResponse, status_code=status.HTTP_201_CREATED)
def create_audit_log(
    audit_log: AuditLogCreate,
    user_id: int,  # Should come from auth
    ip_address: Optional[str] = None,
    db: Session = Depends(get_db),
    service: AdminService = Depends(get_admin_service)
):
    """
    Create an audit log entry (Internal/Admin use).

    Logs an action for audit trail.
    """
    created = service.log_audit(
        action=audit_log.action,
        description=audit_log.description,
        resource_type=audit_log.resource_type,
        resource_id=audit_log.resource_id,
        user_id=user_id,
        old_values=audit_log.old_values,
        new_values=audit_log.new_values,
        ip_address=ip_address,
        metadata=audit_log.metadata,
        db=db
    )
    return created


@router.get("/audit-logs", response_model=List[AuditLogResponse])
def get_audit_logs(
    user_id: Optional[int] = None,
    resource_type: Optional[AuditResourceType] = None,
    resource_id: Optional[int] = None,
    action: Optional[AuditAction] = None,
    start_date: Optional[datetime] = None,
    end_date: Optional[datetime] = None,
    limit: int = Query(100, le=1000),
    current_admin_id: int = Query(...),  # Should come from auth
    db: Session = Depends(get_db),
    service: AdminService = Depends(get_admin_service)
):
    """
    Query audit logs (Admin only).

    Returns audit logs matching the specified filters.
    """
    # Verify requester is admin
    if not verify_admin_access(current_admin_id, db=db):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Requires admin access"
        )

    logs = service.get_audit_logs(
        user_id=user_id,
        resource_type=resource_type,
        resource_id=resource_id,
        action=action,
        start_date=start_date,
        end_date=end_date,
        limit=limit,
        db=db
    )
    return logs


# ==================== Platform Configuration ====================

@router.get("/config/{config_key}", response_model=ConfigurationResponse)
def get_configuration(
    config_key: str,
    current_admin_id: int = Query(...),  # Should come from auth
    db: Session = Depends(get_db),
    service: AdminService = Depends(get_admin_service)
):
    """
    Get a configuration value (Admin only).

    Returns the current value of a platform configuration.
    """
    # Verify requester is admin
    if not verify_admin_access(current_admin_id, db=db):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Requires admin access"
        )

    config = service.get_configuration(config_key=config_key, db=db)
    if not config:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Configuration not found"
        )

    return config


@router.post("/config", response_model=ConfigurationResponse)
def set_configuration(
    config: ConfigurationSet,
    current_admin_id: int,  # Should come from auth
    db: Session = Depends(get_db),
    service: AdminService = Depends(get_admin_service)
):
    """
    Set a configuration value (Admin only).

    Updates or creates a platform configuration.
    """
    # Verify requester is admin
    if not verify_admin_access(current_admin_id, db=db):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Requires admin access"
        )

    updated = service.set_configuration(
        config_key=config.config_key,
        config_value=config.config_value,
        config_type=config.config_type,
        description=config.description,
        updated_by_user_id=current_admin_id,
        db=db
    )
    return updated


@router.get("/config", response_model=List[ConfigurationResponse])
def list_configurations(
    config_type: Optional[ConfigurationType] = None,
    current_admin_id: int = Query(...),  # Should come from auth
    db: Session = Depends(get_db),
    service: AdminService = Depends(get_admin_service)
):
    """
    List all configurations (Admin only).

    Returns all platform configurations.
    """
    # Verify requester is admin
    if not verify_admin_access(current_admin_id, db=db):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Requires admin access"
        )

    configs = service.get_all_configurations(
        config_type=config_type,
        db=db
    )
    return configs


# ==================== Feature Flags ====================

@router.post("/feature-flags", response_model=FeatureFlagResponse, status_code=status.HTTP_201_CREATED)
def create_feature_flag(
    flag: FeatureFlagCreate,
    current_admin_id: int,  # Should come from auth
    db: Session = Depends(get_db),
    service: AdminService = Depends(get_admin_service)
):
    """
    Create a feature flag (Admin only).

    Creates a new feature flag for gradual rollout.
    """
    # Verify requester is admin
    if not verify_admin_access(current_admin_id, db=db):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Requires admin access"
        )

    created = service.create_feature_flag(
        feature_key=flag.feature_key,
        feature_name=flag.feature_name,
        description=flag.description,
        is_enabled=flag.is_enabled,
        rollout_type=flag.rollout_type,
        db=db
    )
    return created


@router.post("/feature-flags/{feature_key}/toggle", response_model=FeatureFlagResponse)
def toggle_feature_flag(
    feature_key: str,
    is_enabled: bool,
    current_admin_id: int,  # Should come from auth
    db: Session = Depends(get_db),
    service: AdminService = Depends(get_admin_service)
):
    """
    Toggle a feature flag (Admin only).

    Enables or disables a feature flag.
    """
    # Verify requester is admin
    if not verify_admin_access(current_admin_id, db=db):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Requires admin access"
        )

    try:
        flag = service.toggle_feature_flag(
            feature_key=feature_key,
            is_enabled=is_enabled,
            db=db
        )
        return flag
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e)
        )


@router.get("/feature-flags/{feature_key}/check")
def check_feature_flag(
    feature_key: str,
    user_id: int,  # Should come from auth
    company_id: Optional[int] = None,
    db: Session = Depends(get_db),
    service: AdminService = Depends(get_admin_service)
):
    """
    Check if a feature is enabled for a user.

    Returns whether the feature flag is enabled for the user.
    """
    is_enabled = service.is_feature_enabled(
        feature_key=feature_key,
        user_id=user_id,
        company_id=company_id,
        db=db
    )

    return {
        "feature_key": feature_key,
        "is_enabled": is_enabled
    }


# ==================== Data Export ====================

@router.post("/data-export", response_model=DataExportResponse, status_code=status.HTTP_201_CREATED)
def request_data_export(
    export_request: DataExportRequest,
    user_id: int,  # Should come from auth
    company_id: Optional[int] = None,
    db: Session = Depends(get_db),
    service: AdminService = Depends(get_admin_service)
):
    """
    Request a data export (GDPR compliance).

    Creates a data export request for the user.
    """
    export = service.request_data_export(
        user_id=user_id,
        export_type=export_request.export_type,
        data_types=export_request.data_types,
        file_format=export_request.file_format,
        company_id=company_id,
        db=db
    )
    return export


@router.get("/data-export/{export_id}", response_model=DataExportResponse)
def get_data_export(
    export_id: int,
    user_id: int,  # Should come from auth
    db: Session = Depends(get_db)
):
    """
    Get data export status.

    Returns the status and download URL for a data export.
    """
    export = db.query(DataExport).filter(
        DataExport.id == export_id,
        DataExport.user_id == user_id
    ).first()

    if not export:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Data export not found"
        )

    return export


# ==================== Compliance ====================

@router.post("/compliance", response_model=ComplianceRecordResponse, status_code=status.HTTP_201_CREATED)
def create_compliance_record(
    record: ComplianceRecordCreate,
    user_id: Optional[int] = None,
    company_id: Optional[int] = None,
    current_admin_id: int = Query(...),  # Should come from auth
    db: Session = Depends(get_db),
    service: AdminService = Depends(get_admin_service)
):
    """
    Create a compliance record (Admin only).

    Tracks compliance-related actions.
    """
    # Verify requester is admin
    if not verify_admin_access(current_admin_id, db=db):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Requires admin access"
        )

    created = service.create_compliance_record(
        compliance_type=record.compliance_type,
        action=record.action,
        description=record.description,
        user_id=user_id,
        company_id=company_id,
        regulation=record.regulation,
        due_date=record.due_date,
        db=db
    )
    return created


@router.get("/compliance", response_model=List[ComplianceRecordResponse])
def get_compliance_records(
    user_id: Optional[int] = None,
    company_id: Optional[int] = None,
    compliance_type: Optional[str] = None,
    status: Optional[str] = None,
    current_admin_id: int = Query(...),  # Should come from auth
    db: Session = Depends(get_db),
    service: AdminService = Depends(get_admin_service)
):
    """
    Query compliance records (Admin only).

    Returns compliance records matching the specified filters.
    """
    # Verify requester is admin
    if not verify_admin_access(current_admin_id, db=db):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Requires admin access"
        )

    records = service.get_compliance_records(
        user_id=user_id,
        company_id=company_id,
        compliance_type=compliance_type,
        status=status,
        db=db
    )
    return records


# ==================== Dashboard ====================

@router.get("/dashboard/metrics")
def get_admin_dashboard_metrics(
    current_admin_id: int = Query(...),  # Should come from auth
    db: Session = Depends(get_db)
):
    """
    Get admin dashboard metrics (Admin only).

    Returns key platform metrics for the admin dashboard.
    """
    from ..models.user import User
    from ..models.company import Company
    from ..models.job import Job
    from ..models.application import Application
    from sqlalchemy import func

    # Verify requester is admin
    if not verify_admin_access(current_admin_id, db=db):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Requires admin access"
        )

    # Get counts
    total_users = db.query(func.count(User.id)).scalar()
    total_companies = db.query(func.count(Company.id)).scalar()
    total_jobs = db.query(func.count(Job.id)).scalar()
    total_applications = db.query(func.count(Application.id)).scalar()

    # Get new users today
    today_start = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)
    new_users_today = db.query(func.count(User.id)).filter(User.created_at >= today_start).scalar()

    # Get active jobs
    from ..models.job import JobStatus
    active_jobs = db.query(func.count(Job.id)).filter(Job.status == JobStatus.ACTIVE).scalar()

    return {
        "total_users": total_users,
        "total_companies": total_companies,
        "total_jobs": total_jobs,
        "active_jobs": active_jobs,
        "total_applications": total_applications,
        "new_users_today": new_users_today,
        "timestamp": datetime.utcnow()
    }
