"""
Enhanced Registration API.

Supports Phase 2 multi-user architecture:
- Everyone starts as Talent (free trial)
- Can add Hiring Manager function
- Can add Recruiter function
- Admin accounts are separate
"""

from typing import Optional
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from pydantic import BaseModel, EmailStr, Field

from ..database import get_db
from ..models.user import User, UserRole, AccountStatus
from ..models.profile import UserProfile
from ..models.personal_ai_agent import PersonalAIAgent, AgentType as PersonalAgentType
from ..models.subscription import Subscription
from ..models.company_v2 import Company
from ..models.hiring_manager_role import HiringManagerRole
from ..models.company_admin_agent import CompanyAdminAgent
from ..models.audit_log import AgentAuditLog as AuditLog
from ..api.auth import get_current_active_user
from ..services.subscription_manager import SubscriptionManager
from ..services.company_agent_factory import CompanyAgentFactory
from ..security import hash_password, generate_verification_token


router = APIRouter()
subscription_manager = SubscriptionManager()
company_agent_factory = CompanyAgentFactory()


# ============================================================================
# Request/Response Models
# ============================================================================

class TalentRegisterRequest(BaseModel):
    """Request to register as Talent user."""
    email: EmailStr
    password: str = Field(..., min_length=8)
    first_name: str = Field(..., min_length=1, max_length=100)
    last_name: str = Field(..., min_length=1, max_length=100)


class TalentRegisterResponse(BaseModel):
    """Response after Talent registration."""
    user_id: int
    email: str
    full_name: str
    subscription_type: str
    subscription_expires_at: str
    message: str


class AddHiringManagerRequest(BaseModel):
    """Request to add Hiring Manager function to account."""
    company_id: Optional[int] = None  # If None, creates new company
    company_name: Optional[str] = None  # Required if creating new company
    company_description: Optional[str] = None
    company_industry: Optional[str] = None


class AddHiringManagerResponse(BaseModel):
    """Response after adding HM function."""
    hiring_manager_role_id: int
    company_id: int
    company_name: str
    message: str


class AddRecruiterRequest(BaseModel):
    """Request to add Recruiter function to account."""
    recruitment_company_name: str
    recruitment_company_description: Optional[str]


class AddRecruiterResponse(BaseModel):
    """Response after adding Recruiter function."""
    recruiter_agent_id: int
    subscription_id: int
    message: str


class UserTypeStatusResponse(BaseModel):
    """Response showing all user types/functions."""
    user_id: int
    email: str
    has_talent_function: bool
    has_hiring_manager_function: bool
    has_recruiter_function: bool
    talent_subscription_active: bool
    hiring_manager_company: Optional[str]
    recruiter_company: Optional[str]


# ============================================================================
# Talent Registration (Base Account)
# ============================================================================

@router.post("/register/talent", response_model=TalentRegisterResponse, status_code=status.HTTP_201_CREATED)
async def register_talent(
    request: TalentRegisterRequest,
    db: Session = Depends(get_db)
):
    """
    Register as Talent user (job seeker).

    This is the base account type. Everyone starts here.
    Creates:
    - User account
    - User profile
    - Free trial subscription (12 months)

    After registration, user completes CV upload + interview to activate their Personal AI Agent.
    """
    # Check if email already exists
    existing_user = db.query(User).filter(User.email == request.email).first()
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email already registered"
        )

    # Create user account
    user = User(
        email=request.email,
        hashed_password=hash_password(request.password),
        first_name=request.first_name,
        last_name=request.last_name,
        full_name=f"{request.first_name} {request.last_name}",
        role=UserRole.JOB_SEEKER,  # Base role (legacy compatibility)
        status=AccountStatus.PENDING_VERIFICATION,
        email_verification_token=generate_verification_token(),
        created_at=datetime.utcnow(),
        updated_at=datetime.utcnow()
    )

    db.add(user)
    db.commit()
    db.refresh(user)

    # Create user profile
    profile = UserProfile(
        user_id=user.id,
        created_at=datetime.utcnow(),
        updated_at=datetime.utcnow()
    )
    db.add(profile)

    # Create free trial subscription (12 months)
    subscription = subscription_manager.create_talent_free_trial(
        user_id=user.id,
        db=db
    )

    # Audit log
    audit = AuditLog(
        user_id=user.id,
        action="talent_registration",
        details={
            "email": user.email,
            "subscription_type": subscription.subscription_type.value
        }
    )
    db.add(audit)
    db.commit()

    return TalentRegisterResponse(
        user_id=user.id,
        email=user.email,
        full_name=user.full_name,
        subscription_type=subscription.subscription_type.value,
        subscription_expires_at=subscription.expires_at.isoformat(),
        message="Registration successful! Complete CV upload and interview to activate your AI agent."
    )


# ============================================================================
# Add Hiring Manager Function
# ============================================================================

@router.post("/add-function/hiring-manager", response_model=AddHiringManagerResponse)
async def add_hiring_manager_function(
    request: AddHiringManagerRequest,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """
    Add Hiring Manager function to existing account.

    User can have BOTH Talent and Hiring Manager functions active simultaneously.
    This is the unique feature of the platform!

    Flow:
    1. Check if user already has HM function
    2. Get or create company
    3. Check company has available seats
    4. Create/link Company Admin Agent
    5. Create Hiring Manager subscription (linked to company)
    6. User then completes HM interview to activate HM agent

    Note: User must complete separate HM interview to create their HM Personal Agent.
    """
    # Check if user already has active HM function
    existing_hm = db.query(HiringManagerRole).filter(
        HiringManagerRole.user_id == current_user.id,
        HiringManagerRole.is_active == True
    ).first()

    if existing_hm:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="User already has an active Hiring Manager function"
        )

    # Get or create company
    company = None
    if request.company_id:
        # Link to existing company
        company = db.query(Company).filter(Company.id == request.company_id).first()
        if not company:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Company {request.company_id} not found"
            )
    else:
        # Create new company
        if not request.company_name:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="company_name required when creating new company"
            )

        company = Company(
            name=request.company_name,
            description=request.company_description,
            industry=request.company_industry,
            hiring_manager_seats_allocated=5,  # Default
            hiring_manager_seats_used=0,
            talent_seats_allocated=10,  # Default
            talent_seats_used=0,
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow()
        )
        db.add(company)
        db.commit()
        db.refresh(company)

        # Create Company Admin Agent (first HM)
        company_agent_factory.create_for_company(
            company_id=company.id,
            db=db
        )

    # Check if company has available HM seats
    if not company.has_available_hiring_manager_seats():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No available Hiring Manager seats in company subscription"
        )

    # Create HM subscription (linked to company)
    hm_subscription = subscription_manager.create_hiring_manager_subscription(
        user_id=current_user.id,
        company_id=company.id,
        db=db
    )

    # Create placeholder HM role (will be completed after HM interview)
    # Note: hiring_manager_agent_id will be set after interview completion
    hm_role = HiringManagerRole(
        user_id=current_user.id,
        company_id=company.id,
        hiring_manager_agent_id=None,  # Set after interview
        company_admin_agent_id=None,  # Set after interview
        is_active=True,
        joined_at=datetime.utcnow()
    )
    db.add(hm_role)
    db.commit()
    db.refresh(hm_role)

    # Audit log
    audit = AuditLog(
        user_id=current_user.id,
        action="hiring_manager_function_added",
        details={
            "company_id": company.id,
            "company_name": company.name,
            "hiring_manager_role_id": hm_role.id
        }
    )
    db.add(audit)
    db.commit()

    return AddHiringManagerResponse(
        hiring_manager_role_id=hm_role.id,
        company_id=company.id,
        company_name=company.name,
        message="Hiring Manager function added! Complete HM interview to activate your HM agent."
    )


# ============================================================================
# Add Recruiter Function
# ============================================================================

@router.post("/add-function/recruiter", response_model=AddRecruiterResponse)
async def add_recruiter_function(
    request: AddRecruiterRequest,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """
    Add Recruiter function to existing account.

    User can have Talent + Recruiter functions active simultaneously.

    Flow:
    1. Check if user already has Recruiter function
    2. Create Recruiter subscription (individual, not company-based)
    3. User then completes Recruiter interview to activate Recruiter agent

    Note: Recruiter is for external recruitment agencies.
    One recruiter account = one recruitment company.
    """
    # Check if user already has Recruiter agent
    existing_recruiter = db.query(PersonalAIAgent).filter(
        PersonalAIAgent.user_id == current_user.id,
        PersonalAIAgent.agent_type == PersonalAgentType.RECRUITER
    ).first()

    if existing_recruiter:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="User already has a Recruiter function"
        )

    # Create Recruiter subscription
    recruiter_subscription = subscription_manager.create_recruiter_subscription(
        user_id=current_user.id,
        duration_months=12,
        db=db
    )

    # Create placeholder Recruiter agent (will be completed after interview)
    recruiter_agent = PersonalAIAgent(
        user_id=current_user.id,
        agent_type=PersonalAgentType.RECRUITER,
        status="pending",  # Will be activated after interview
        recruitment_company_name=request.recruitment_company_name,
        recruitment_company_description=request.recruitment_company_description,
        created_at=datetime.utcnow(),
        updated_at=datetime.utcnow()
    )
    db.add(recruiter_agent)
    db.commit()
    db.refresh(recruiter_agent)

    # Audit log
    audit = AuditLog(
        user_id=current_user.id,
        action="recruiter_function_added",
        details={
            "recruiter_agent_id": recruiter_agent.id,
            "recruitment_company": request.recruitment_company_name
        }
    )
    db.add(audit)
    db.commit()

    return AddRecruiterResponse(
        recruiter_agent_id=recruiter_agent.id,
        subscription_id=recruiter_subscription.id,
        message="Recruiter function added! Complete Recruiter interview to activate your Recruiter agent."
    )


# ============================================================================
# User Type Status
# ============================================================================

@router.get("/me/functions", response_model=UserTypeStatusResponse)
async def get_my_user_functions(
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """
    Get all functions/types for current user.

    Shows which functions are active:
    - Talent (base)
    - Hiring Manager (optional)
    - Recruiter (optional)
    """
    # Check for Talent subscription
    talent_sub = db.query(Subscription).filter(
        Subscription.user_id == current_user.id,
        Subscription.subscription_type.in_(["talent_free", "talent_paid"])
    ).first()

    # Check for Hiring Manager role
    hm_role = db.query(HiringManagerRole).filter(
        HiringManagerRole.user_id == current_user.id,
        HiringManagerRole.is_active == True
    ).first()

    hm_company = None
    if hm_role:
        company = db.query(Company).filter(Company.id == hm_role.company_id).first()
        hm_company = company.name if company else None

    # Check for Recruiter agent
    recruiter_agent = db.query(PersonalAIAgent).filter(
        PersonalAIAgent.user_id == current_user.id,
        PersonalAIAgent.agent_type == PersonalAgentType.RECRUITER
    ).first()

    return UserTypeStatusResponse(
        user_id=current_user.id,
        email=current_user.email,
        has_talent_function=talent_sub is not None,
        has_hiring_manager_function=hm_role is not None,
        has_recruiter_function=recruiter_agent is not None,
        talent_subscription_active=talent_sub.is_active() if talent_sub else False,
        hiring_manager_company=hm_company,
        recruiter_company=recruiter_agent.recruitment_company_name if recruiter_agent else None
    )
