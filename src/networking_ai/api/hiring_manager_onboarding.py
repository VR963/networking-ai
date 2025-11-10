"""
Hiring Manager Onboarding API Endpoints.

Handles HM interview process to activate Hiring Manager agent.
"""

from typing import Optional
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from pydantic import BaseModel

from ..database import get_db
from ..models.user import User
from ..models.personal_ai_agent import PersonalAIAgent, AgentType, AgentStatus
from ..models.interview_session import InterviewSession, InterviewStatus
from ..models.agent_conversation import AgentConversation, ConversationType, ConversationStatus
from ..models.hiring_manager_role import HiringManagerRole
from ..models.company_admin_agent import CompanyAdminAgent
from ..models.audit_log import AgentAuditLog as AuditLog
from ..api.auth import get_current_active_user
from ..agents.hiring_manager_interview_agent import create_hiring_manager_interview_agent
from ..services.company_agent_factory import CompanyAgentFactory
from ..services.chromadb_service import create_chromadb_service


router = APIRouter()
company_agent_factory = CompanyAgentFactory()


# ============================================================================
# Request/Response Models
# ============================================================================

class StartHMInterviewRequest(BaseModel):
    """Request to start HM interview."""
    company_id: int


class StartHMInterviewResponse(BaseModel):
    """Response when starting HM interview."""
    conversation_id: int
    session_id: int
    opening_message: str
    interviewer_name: str = "Sarah - Talent Acquisition Specialist"


class HMInterviewMessageRequest(BaseModel):
    """Request to send message in HM interview."""
    conversation_id: int
    message: str


class HMInterviewMessageResponse(BaseModel):
    """Response from HM interview."""
    conversation_id: int
    interviewer_message: str
    completion_percentage: int
    topics_covered: list
    is_complete: bool


class HMInterviewStatusResponse(BaseModel):
    """HM interview status response."""
    session_id: int
    status: str
    completion_percentage: int
    topics_covered: list
    knowledge_extracted: dict


class ActivateHMAgentRequest(BaseModel):
    """Request to activate HM agent."""
    session_id: int


class ActivateHMAgentResponse(BaseModel):
    """Response after HM agent activation."""
    agent_id: int
    hiring_manager_role_id: int
    status: str
    company_id: int
    company_name: str
    message: str


# ============================================================================
# HM Interview Flow
# ============================================================================

@router.post("/start-interview", response_model=StartHMInterviewResponse, status_code=status.HTTP_201_CREATED)
async def start_hm_interview(
    request: StartHMInterviewRequest,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """
    Start Hiring Manager interview.

    Prerequisites:
    - User must have added HM function (HiringManagerRole exists)
    - Company must exist
    - HM agent must be in PENDING state

    Flow:
    1. Verify prerequisites
    2. Create interview session
    3. Create conversation
    4. Initialize HM interview agent
    5. Return opening message
    """
    # Verify HM role exists
    hm_role = db.query(HiringManagerRole).filter(
        HiringManagerRole.user_id == current_user.id,
        HiringManagerRole.company_id == request.company_id,
        HiringManagerRole.is_active == True
    ).first()

    if not hm_role:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="User must add Hiring Manager function first"
        )

    # Get company
    from ..models.company_v2 import Company
    company = db.query(Company).filter(Company.id == request.company_id).first()
    if not company:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Company {request.company_id} not found"
        )

    # Check if HM agent already exists and is active
    existing_agent = db.query(PersonalAIAgent).filter(
        PersonalAIAgent.user_id == current_user.id,
        PersonalAIAgent.agent_type == AgentType.HIRING_MANAGER
    ).first()

    if existing_agent and existing_agent.status == AgentStatus.ACTIVE:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Hiring Manager agent already activated"
        )

    # Create interview session
    interview_session = InterviewSession(
        user_id=current_user.id,
        session_type="hiring_manager",
        status=InterviewStatus.IN_PROGRESS,
        industry=company.industry or "general",
        role="hiring_manager",
        completion_percentage=0,
        started_at=datetime.utcnow()
    )
    db.add(interview_session)
    db.commit()
    db.refresh(interview_session)

    # Create conversation
    conversation = AgentConversation(
        user_id=current_user.id,
        conversation_type=ConversationType.INTERVIEW,
        status=ConversationStatus.ACTIVE,
        metadata={
            "session_id": interview_session.id,
            "company_id": company.id,
            "company_name": company.name,
            "interview_type": "hiring_manager"
        }
    )
    db.add(conversation)
    db.commit()
    db.refresh(conversation)

    # Initialize HM interview agent
    hm_interview_agent = create_hiring_manager_interview_agent(
        company_name=company.name,
        industry=company.industry or "general"
    )

    # Get opening message
    opening_message = hm_interview_agent.start_interview()

    # Store agent in session/cache (in production, use Redis or similar)
    # For now, we'll recreate it on each message

    # Audit log
    audit = AuditLog(
        user_id=current_user.id,
        action="hm_interview_started",
        details={
            "session_id": interview_session.id,
            "conversation_id": conversation.id,
            "company_id": company.id
        }
    )
    db.add(audit)
    db.commit()

    return StartHMInterviewResponse(
        conversation_id=conversation.id,
        session_id=interview_session.id,
        opening_message=opening_message,
        interviewer_name="Sarah - Talent Acquisition Specialist"
    )


@router.post("/interview/message", response_model=HMInterviewMessageResponse)
async def send_hm_interview_message(
    request: HMInterviewMessageRequest,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """
    Send message in HM interview.

    Args:
        request: Message request
        current_user: Current authenticated user
        db: Database session

    Returns:
        Interviewer's response with progress info
    """
    # Get conversation
    conversation = db.query(AgentConversation).filter(
        AgentConversation.id == request.conversation_id,
        AgentConversation.user_id == current_user.id
    ).first()

    if not conversation:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Conversation {request.conversation_id} not found"
        )

    if conversation.status != ConversationStatus.ACTIVE:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Conversation is not active"
        )

    # Get session
    session_id = conversation.metadata.get("session_id")
    interview_session = db.query(InterviewSession).filter(
        InterviewSession.id == session_id
    ).first()

    if not interview_session:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Interview session not found"
        )

    # Recreate HM interview agent with conversation history
    # (In production, store agent state in Redis/cache)
    company_name = conversation.metadata.get("company_name")
    industry = interview_session.industry

    hm_interview_agent = create_hiring_manager_interview_agent(
        company_name=company_name,
        industry=industry
    )

    # Send message and get response
    response = hm_interview_agent.send_message(request.message)

    # Update interview session
    interview_session.completion_percentage = response["completion_percentage"]
    interview_session.topics_covered = response["topics_covered"]

    if response["is_complete"]:
        interview_session.status = InterviewStatus.COMPLETED
        interview_session.completed_at = datetime.utcnow()

        # Extract knowledge
        knowledge = hm_interview_agent.get_extracted_knowledge()
        interview_session.knowledge_extracted = knowledge

    interview_session.updated_at = datetime.utcnow()
    db.commit()

    return HMInterviewMessageResponse(
        conversation_id=conversation.id,
        interviewer_message=response["message"],
        completion_percentage=response["completion_percentage"],
        topics_covered=response["topics_covered"],
        is_complete=response["is_complete"]
    )


@router.get("/interview/status/{session_id}", response_model=HMInterviewStatusResponse)
async def get_hm_interview_status(
    session_id: int,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Get HM interview status."""
    interview_session = db.query(InterviewSession).filter(
        InterviewSession.id == session_id,
        InterviewSession.user_id == current_user.id
    ).first()

    if not interview_session:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Interview session {session_id} not found"
        )

    return HMInterviewStatusResponse(
        session_id=interview_session.id,
        status=interview_session.status.value,
        completion_percentage=interview_session.completion_percentage,
        topics_covered=interview_session.topics_covered or [],
        knowledge_extracted=interview_session.knowledge_extracted or {}
    )


@router.post("/activate-agent", response_model=ActivateHMAgentResponse)
async def activate_hm_agent(
    request: ActivateHMAgentRequest,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """
    Activate Hiring Manager agent after interview completion.

    Flow:
    1. Verify interview is complete
    2. Create/update HM Personal Agent
    3. Link HM to Company Admin Agent
    4. Populate both RAGs (Personal + Company)
    5. Update HiringManagerRole with agent IDs
    """
    # Get interview session
    interview_session = db.query(InterviewSession).filter(
        InterviewSession.id == request.session_id,
        InterviewSession.user_id == current_user.id
    ).first()

    if not interview_session:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Interview session {request.session_id} not found"
        )

    if interview_session.status != InterviewStatus.COMPLETED:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Interview must be completed before activation"
        )

    # Get knowledge
    knowledge = interview_session.knowledge_extracted

    # Get or create HM agent
    hm_agent = db.query(PersonalAIAgent).filter(
        PersonalAIAgent.user_id == current_user.id,
        PersonalAIAgent.agent_type == AgentType.HIRING_MANAGER
    ).first()

    if not hm_agent:
        # Create HM agent
        hm_agent = PersonalAIAgent(
            user_id=current_user.id,
            agent_type=AgentType.HIRING_MANAGER,
            personal_rag_collection_id=f"user_{current_user.id}_hm_rag",
            status=AgentStatus.PENDING,
            industry=interview_session.industry,
            role="hiring_manager",
            created_at=datetime.utcnow()
        )
        db.add(hm_agent)
        db.commit()
        db.refresh(hm_agent)

    # Activate agent
    hm_agent.status = AgentStatus.ACTIVE
    hm_agent.activated_at = datetime.utcnow()
    hm_agent.updated_at = datetime.utcnow()

    # Get HM role and company
    hm_role = db.query(HiringManagerRole).filter(
        HiringManagerRole.user_id == current_user.id,
        HiringManagerRole.is_active == True
    ).first()

    if not hm_role:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No active Hiring Manager role found"
        )

    # Get company admin agent
    admin_agent = db.query(CompanyAdminAgent).filter(
        CompanyAdminAgent.company_id == hm_role.company_id
    ).first()

    if not admin_agent:
        # Create company admin agent if it doesn't exist
        admin_agent = company_agent_factory.create_for_company(
            company_id=hm_role.company_id,
            db=db
        )

    # Link HM to company admin agent
    hm_role.hiring_manager_agent_id = hm_agent.id
    hm_role.company_admin_agent_id = admin_agent.id

    # Add HM knowledge to company RAG
    company_agent_factory.link_hiring_manager(
        company_admin_agent_id=admin_agent.id,
        hiring_manager_id=current_user.id,
        hiring_manager_agent_id=hm_agent.id,
        hiring_manager_name=f"{current_user.first_name} {current_user.last_name}",
        hiring_manager_knowledge=knowledge,
        db=db
    )

    # Phase 2: Populate Personal HM Agent RAG
    try:
        chromadb_service = create_chromadb_service()

        # Create HM RAG collection
        collection_name = chromadb_service.create_hm_rag(
            agent_id=hm_agent.id,
            user_id=current_user.id,
            company_id=hm_role.company_id
        )

        # Update agent with RAG collection ID
        hm_agent.rag_collection_id = collection_name

        # Populate HM RAG with interview knowledge
        chromadb_service.populate_hm_rag(
            collection_name=collection_name,
            interview_data=knowledge
        )

        print(f"[HM_ONBOARDING] Populated HM RAG '{collection_name}' with hiring preferences and style")

    except ImportError as e:
        # ChromaDB not installed - graceful degradation
        print(f"[HM_ONBOARDING] ChromaDB not available, skipping RAG population: {e}")
        print(f"[HM_ONBOARDING] Agent will use fallback data for job posting")

    except Exception as e:
        # Other errors - log but continue
        print(f"[HM_ONBOARDING] Error populating HM RAG: {e}")
        print(f"[HM_ONBOARDING] Agent will use fallback data")

    db.commit()

    # Get company
    from ..models.company_v2 import Company
    company = db.query(Company).filter(Company.id == hm_role.company_id).first()

    # Audit log
    audit = AuditLog(
        user_id=current_user.id,
        action="hm_agent_activated",
        details={
            "agent_id": hm_agent.id,
            "company_id": hm_role.company_id,
            "session_id": request.session_id
        }
    )
    db.add(audit)
    db.commit()

    return ActivateHMAgentResponse(
        agent_id=hm_agent.id,
        hiring_manager_role_id=hm_role.id,
        status=hm_agent.status.value,
        company_id=hm_role.company_id,
        company_name=company.name,
        message="Hiring Manager agent activated successfully! You can now create job postings."
    )
