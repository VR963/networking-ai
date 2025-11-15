"""
Company Management API Endpoints.

Manage companies, company admin agents, hiring managers, and subscriptions.
"""

from typing import Optional, List
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from pydantic import BaseModel, Field

from ..database import get_db
from ..models.user import User
from ..models.company_v2 import CompanyV2 as Company
from ..models.company_admin_agent import CompanyAdminAgent, AdminAgentStatus
from ..models.hiring_manager_role import HiringManagerRole
from ..models.company_admin_user import CompanyAdminUser
from ..models.subscription import Subscription, SubscriptionType, SubscriptionStatus
from ..api.auth import get_current_active_user
from ..services.company_agent_factory import CompanyAgentFactory
from ..services.subscription_manager import SubscriptionManager
from ..models.audit_log import AgentAuditLog as AuditLog


router = APIRouter()
company_agent_factory = CompanyAgentFactory()
subscription_manager = SubscriptionManager()


# ============================================================================
# Request/Response Models
# ============================================================================

class CompanyCreateRequest(BaseModel):
    """Request to create a new company."""
    name: str = Field(..., min_length=2, max_length=255)
    description: Optional[str]
    industry: Optional[str]
    size: Optional[str]
    website: Optional[str]
    hiring_manager_seats: int = Field(default=5, ge=1)
    talent_seats: int = Field(default=10, ge=0)


class CompanyResponse(BaseModel):
    """Company details response."""
    id: int
    name: str
    description: Optional[str]
    industry: Optional[str]
    size: Optional[str]
    website: Optional[str]
    hiring_manager_seats_allocated: int
    hiring_manager_seats_used: int
    talent_seats_allocated: int
    talent_seats_used: int
    has_admin_agent: bool
    subscription_active: bool
    created_at: str


class CompanyAdminAgentResponse(BaseModel):
    """Company Admin Agent response."""
    id: int
    company_id: int
    status: str
    total_hiring_managers: int
    active_hiring_managers: int
    total_conversations: int
    total_hires: int
    rag_collection_id: str
    created_at: str


class HiringManagerLinkRequest(BaseModel):
    """Request to link hiring manager to company."""
    company_id: int
    hiring_manager_knowledge: dict  # From interview


class HiringManagerRoleResponse(BaseModel):
    """Hiring manager role response."""
    id: int
    user_id: int
    company_id: int
    hiring_manager_agent_id: int
    company_admin_agent_id: int
    is_active: bool
    joined_at: str
    left_at: Optional[str]


class SubscriptionCreateRequest(BaseModel):
    """Request to create subscription."""
    subscription_type: str
    duration_months: int = Field(default=12, ge=1, le=36)
    hiring_manager_seats: Optional[int] = Field(default=None, ge=1)
    talent_seats: Optional[int] = Field(default=None, ge=0)


class SubscriptionResponse(BaseModel):
    """Subscription response."""
    id: int
    user_id: Optional[int]
    company_id: Optional[int]
    subscription_type: str
    status: str
    starts_at: str
    expires_at: Optional[str]
    data_retention_expires_at: Optional[str]
    has_data_access: bool
    billing_amount: Optional[float]
    auto_renew: bool


class CompanyKnowledgeQueryRequest(BaseModel):
    """Request to query company knowledge."""
    query: str = Field(..., min_length=3)
    n_results: int = Field(default=5, ge=1, le=20)


# ============================================================================
# Company Management Endpoints
# ============================================================================

@router.post("/", response_model=CompanyResponse, status_code=status.HTTP_201_CREATED)
async def create_company(
    request: CompanyCreateRequest,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """
    Create a new company.

    This is called when the first hiring manager from a company joins.
    Creates the company record and admin agent.
    """
    # Check if company already exists
    existing = db.query(Company).filter(Company.name == request.name).first()
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Company with name '{request.name}' already exists"
        )

    # Create company
    company = Company(
        name=request.name,
        description=request.description,
        industry=request.industry,
        size=request.size,
        website=request.website,
        hiring_manager_seats_allocated=request.hiring_manager_seats,
        hiring_manager_seats_used=0,
        talent_seats_allocated=request.talent_seats,
        talent_seats_used=0,
        created_at=datetime.utcnow(),
        updated_at=datetime.utcnow()
    )

    db.add(company)
    db.commit()
    db.refresh(company)

    # Create Company Admin Agent
    admin_agent = company_agent_factory.create_for_company(
        company_id=company.id,
        db=db
    )

    # Audit log
    audit = AuditLog(
        user_id=current_user.id,
        action="company_created",
        details={"company_id": company.id, "company_name": company.name}
    )
    db.add(audit)
    db.commit()

    return CompanyResponse(
        id=company.id,
        name=company.name,
        description=company.description,
        industry=company.industry,
        size=company.size,
        website=company.website,
        hiring_manager_seats_allocated=company.hiring_manager_seats_allocated,
        hiring_manager_seats_used=company.hiring_manager_seats_used,
        talent_seats_allocated=company.talent_seats_allocated,
        talent_seats_used=company.talent_seats_used,
        has_admin_agent=True,
        subscription_active=False,
        created_at=company.created_at.isoformat()
    )


@router.get("/{company_id}", response_model=CompanyResponse)
async def get_company(
    company_id: int,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Get company details."""
    company = db.query(Company).filter(Company.id == company_id).first()
    if not company:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Company {company_id} not found"
        )

    # Check if admin agent exists
    admin_agent = db.query(CompanyAdminAgent).filter(
        CompanyAdminAgent.company_id == company_id
    ).first()

    return CompanyResponse(
        id=company.id,
        name=company.name,
        description=company.description,
        industry=company.industry,
        size=company.size,
        website=company.website,
        hiring_manager_seats_allocated=company.hiring_manager_seats_allocated,
        hiring_manager_seats_used=company.hiring_manager_seats_used,
        talent_seats_allocated=company.talent_seats_allocated,
        talent_seats_used=company.talent_seats_used,
        has_admin_agent=admin_agent is not None,
        subscription_active=company.is_subscription_active(),
        created_at=company.created_at.isoformat()
    )


@router.get("/{company_id}/admin-agent", response_model=CompanyAdminAgentResponse)
async def get_company_admin_agent(
    company_id: int,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Get company admin agent details."""
    admin_agent = db.query(CompanyAdminAgent).filter(
        CompanyAdminAgent.company_id == company_id
    ).first()

    if not admin_agent:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"No admin agent found for company {company_id}"
        )

    return CompanyAdminAgentResponse(
        id=admin_agent.id,
        company_id=admin_agent.company_id,
        status=admin_agent.status.value,
        total_hiring_managers=admin_agent.total_hiring_managers,
        active_hiring_managers=admin_agent.active_hiring_managers,
        total_conversations=admin_agent.total_conversations,
        total_hires=admin_agent.total_hires,
        rag_collection_id=admin_agent.company_rag_collection_id,
        created_at=admin_agent.created_at.isoformat()
    )


# ============================================================================
# Hiring Manager Management
# ============================================================================

@router.post("/hiring-managers/link", response_model=HiringManagerRoleResponse)
async def link_hiring_manager_to_company(
    request: HiringManagerLinkRequest,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """
    Link hiring manager to company.

    This is called after a hiring manager completes their interview.
    Their knowledge is added to company RAG and they get linked to company admin agent.
    """
    # Get company admin agent
    admin_agent = db.query(CompanyAdminAgent).filter(
        CompanyAdminAgent.company_id == request.company_id
    ).first()

    if not admin_agent:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"No admin agent found for company {request.company_id}"
        )

    # Check if user already has a hiring manager agent
    from ..models.personal_ai_agent import PersonalAIAgent
    hm_agent = db.query(PersonalAIAgent).filter(
        PersonalAIAgent.user_id == current_user.id,
        PersonalAIAgent.agent_type == "hiring_manager"
    ).first()

    if not hm_agent:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="User must complete hiring manager interview first"
        )

    # Check if already linked
    existing_link = db.query(HiringManagerRole).filter(
        HiringManagerRole.user_id == current_user.id,
        HiringManagerRole.company_id == request.company_id,
        HiringManagerRole.is_active == True
    ).first()

    if existing_link:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="User already linked to this company"
        )

    # Link hiring manager
    hm_role = company_agent_factory.link_hiring_manager(
        company_admin_agent_id=admin_agent.id,
        hiring_manager_id=current_user.id,
        hiring_manager_agent_id=hm_agent.id,
        hiring_manager_name=f"{current_user.first_name} {current_user.last_name}",
        hiring_manager_knowledge=request.hiring_manager_knowledge,
        db=db
    )

    # Audit log
    audit = AuditLog(
        user_id=current_user.id,
        action="hiring_manager_linked",
        details={
            "company_id": request.company_id,
            "hiring_manager_role_id": hm_role.id
        }
    )
    db.add(audit)
    db.commit()

    return HiringManagerRoleResponse(
        id=hm_role.id,
        user_id=hm_role.user_id,
        company_id=hm_role.company_id,
        hiring_manager_agent_id=hm_role.hiring_manager_agent_id,
        company_admin_agent_id=hm_role.company_admin_agent_id,
        is_active=hm_role.is_active,
        joined_at=hm_role.joined_at.isoformat(),
        left_at=hm_role.left_at.isoformat() if hm_role.left_at else None
    )


@router.post("/hiring-managers/{role_id}/deactivate")
async def deactivate_hiring_manager(
    role_id: int,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """
    Deactivate a hiring manager (they left the company).

    Their knowledge stays in company RAG, but they are marked as inactive.
    """
    hm_role = db.query(HiringManagerRole).filter(
        HiringManagerRole.id == role_id
    ).first()

    if not hm_role:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Hiring manager role {role_id} not found"
        )

    # Deactivate
    company_agent_factory.deactivate_hiring_manager(
        hiring_manager_role_id=role_id,
        db=db
    )

    # Audit log
    audit = AuditLog(
        user_id=current_user.id,
        action="hiring_manager_deactivated",
        details={"hiring_manager_role_id": role_id}
    )
    db.add(audit)
    db.commit()

    return {"message": "Hiring manager deactivated", "role_id": role_id}


# ============================================================================
# Subscription Management
# ============================================================================

@router.post("/subscriptions", response_model=SubscriptionResponse, status_code=status.HTTP_201_CREATED)
async def create_subscription(
    request: SubscriptionCreateRequest,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """
    Create a new subscription.

    Supports:
    - Talent free trial (automatic for new users)
    - Talent paid
    - Hiring manager (company-based)
    - Recruiter
    - Company seats
    """
    subscription = None

    if request.subscription_type == "talent_free":
        subscription = subscription_manager.create_talent_free_trial(
            user_id=current_user.id,
            db=db
        )
    elif request.subscription_type == "talent_paid":
        # Check if upgrading from free trial
        existing = db.query(Subscription).filter(
            Subscription.user_id == current_user.id,
            Subscription.subscription_type == SubscriptionType.TALENT_FREE
        ).first()

        if existing:
            subscription = subscription_manager.upgrade_talent_to_paid(
                user_id=current_user.id,
                duration_months=request.duration_months,
                db=db
            )
        else:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="No free trial found to upgrade"
            )

    elif request.subscription_type == "recruiter":
        subscription = subscription_manager.create_recruiter_subscription(
            user_id=current_user.id,
            duration_months=request.duration_months,
            db=db
        )

    else:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Unsupported subscription type: {request.subscription_type}"
        )

    # Audit log
    audit = AuditLog(
        user_id=current_user.id,
        action="subscription_created",
        details={
            "subscription_id": subscription.id,
            "subscription_type": subscription.subscription_type.value
        }
    )
    db.add(audit)
    db.commit()

    return SubscriptionResponse(
        id=subscription.id,
        user_id=subscription.user_id,
        company_id=subscription.company_id,
        subscription_type=subscription.subscription_type.value,
        status=subscription.status.value,
        starts_at=subscription.starts_at.isoformat(),
        expires_at=subscription.expires_at.isoformat() if subscription.expires_at else None,
        data_retention_expires_at=subscription.data_retention_expires_at.isoformat() if subscription.data_retention_expires_at else None,
        has_data_access=subscription.has_data_access(),
        billing_amount=subscription.billing_amount,
        auto_renew=subscription.auto_renew
    )


@router.get("/subscriptions/me", response_model=SubscriptionResponse)
async def get_my_subscription(
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Get current user's subscription status."""
    subscription = db.query(Subscription).filter(
        Subscription.user_id == current_user.id
    ).order_by(Subscription.created_at.desc()).first()

    if not subscription:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No subscription found"
        )

    return SubscriptionResponse(
        id=subscription.id,
        user_id=subscription.user_id,
        company_id=subscription.company_id,
        subscription_type=subscription.subscription_type.value,
        status=subscription.status.value,
        starts_at=subscription.starts_at.isoformat(),
        expires_at=subscription.expires_at.isoformat() if subscription.expires_at else None,
        data_retention_expires_at=subscription.data_retention_expires_at.isoformat() if subscription.data_retention_expires_at else None,
        has_data_access=subscription.has_data_access(),
        billing_amount=subscription.billing_amount,
        auto_renew=subscription.auto_renew
    )


@router.post("/subscriptions/{subscription_id}/cancel")
async def cancel_subscription(
    subscription_id: int,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """
    Cancel a subscription.

    Data access continues until data_retention_expires_at.
    """
    subscription = db.query(Subscription).filter(
        Subscription.id == subscription_id,
        Subscription.user_id == current_user.id
    ).first()

    if not subscription:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Subscription {subscription_id} not found"
        )

    subscription_manager.cancel_subscription(subscription_id=subscription_id, db=db)

    # Audit log
    audit = AuditLog(
        user_id=current_user.id,
        action="subscription_cancelled",
        details={"subscription_id": subscription_id}
    )
    db.add(audit)
    db.commit()

    return {"message": "Subscription cancelled", "subscription_id": subscription_id}


# ============================================================================
# Company Knowledge Query
# ============================================================================

@router.post("/{company_id}/knowledge/query")
async def query_company_knowledge(
    company_id: int,
    request: CompanyKnowledgeQueryRequest,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """
    Query company knowledge base.

    Available to hiring managers and admin users of the company.
    """
    # Check if user is linked to company
    hm_role = db.query(HiringManagerRole).filter(
        HiringManagerRole.user_id == current_user.id,
        HiringManagerRole.company_id == company_id,
        HiringManagerRole.is_active == True
    ).first()

    if not hm_role:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="User not authorized to access company knowledge"
        )

    # Get company admin agent
    admin_agent = db.query(CompanyAdminAgent).filter(
        CompanyAdminAgent.company_id == company_id
    ).first()

    if not admin_agent:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"No admin agent found for company {company_id}"
        )

    # Query knowledge
    results = company_agent_factory.query_company_knowledge(
        company_admin_agent_id=admin_agent.id,
        query=request.query,
        n_results=request.n_results,
        db=db
    )

    # Record conversation
    company_agent_factory.record_conversation(
        company_admin_agent_id=admin_agent.id,
        db=db
    )

    return {
        "query": request.query,
        "results": results,
        "count": len(results)
    }


@router.get("/{company_id}/knowledge/stats")
async def get_company_knowledge_stats(
    company_id: int,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Get statistics about company knowledge."""
    # Check authorization
    hm_role = db.query(HiringManagerRole).filter(
        HiringManagerRole.user_id == current_user.id,
        HiringManagerRole.company_id == company_id,
        HiringManagerRole.is_active == True
    ).first()

    if not hm_role:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="User not authorized to access company stats"
        )

    # Get admin agent
    admin_agent = db.query(CompanyAdminAgent).filter(
        CompanyAdminAgent.company_id == company_id
    ).first()

    if not admin_agent:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"No admin agent found for company {company_id}"
        )

    # Get stats
    stats = company_agent_factory.get_company_knowledge_stats(
        company_admin_agent_id=admin_agent.id,
        db=db
    )

    return stats
