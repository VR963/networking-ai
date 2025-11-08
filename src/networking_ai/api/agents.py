"""
Personal AI Agent API Endpoints.

Manage personal agent lifecycle: creation, activation, pause, resume.
"""

from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from pydantic import BaseModel

from ..database import get_db
from ..models.user import User
from ..models.personal_ai_agent import PersonalAIAgent, AgentStatus
from ..models.interview_session import InterviewSession
from ..api.auth import get_current_active_user
from ..services.personal_agent_factory import create_personal_agent_factory
from ..models.audit_log import AgentAuditLog as AuditLog


router = APIRouter()


# ============================================================================
# Request/Response Models
# ============================================================================

class AgentActivationResponse(BaseModel):
    """Response after agent activation."""
    agent_id: int
    status: str
    collection_id: str
    industry: str
    role: str
    user_segment_id: str
    activated_at: Optional[str]
    message: str


class AgentStatusResponse(BaseModel):
    """Agent status response."""
    agent_id: int
    status: str
    industry: Optional[str]
    role: Optional[str]
    total_conversations: int
    successful_matches: int
    learning_score: float
    activated_at: Optional[str]
    last_search_at: Optional[str]
    can_search: bool


class AgentControlRequest(BaseModel):
    """Request to control agent (pause/resume)."""
    action: str  # "pause" or "resume"


# ============================================================================
# Agent Activation
# ============================================================================

@router.post("/activate/{session_id}", response_model=AgentActivationResponse, status_code=status.HTTP_201_CREATED)
async def activate_agent_from_interview(
    session_id: int,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """
    Activate personal AI agent from completed interview.

    Steps:
    1. Verify interview is complete
    2. Create personal RAG collection
    3. Populate with interview knowledge
    4. Create PersonalAIAgent record
    5. Activate agent for matching

    Returns:
        Agent details and status
    """
    # Verify interview belongs to user
    session = db.query(InterviewSession).filter(
        InterviewSession.id == session_id,
        InterviewSession.user_id == current_user.id
    ).first()

    if not session:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Interview session not found"
        )

    # Check if agent already exists
    existing_agent = db.query(PersonalAIAgent).filter(
        PersonalAIAgent.user_id == current_user.id
    ).first()

    if existing_agent:
        # If exists but not active, activate it
        if existing_agent.status != AgentStatus.ACTIVE:
            factory = create_personal_agent_factory()
            agent = factory.activate_agent(existing_agent.id, db)

            return AgentActivationResponse(
                agent_id=agent.id,
                status=agent.status.value,
                collection_id=agent.personal_rag_collection_id,
                industry=agent.industry or "",
                role=agent.role or "",
                user_segment_id=agent.user_segment_id or "",
                activated_at=agent.activated_at.isoformat() if agent.activated_at else None,
                message="Agent reactivated successfully"
            )
        else:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Personal agent already exists and is active"
            )

    # Create agent from interview
    try:
        factory = create_personal_agent_factory()
        agent = factory.create_from_interview(session_id, db)

        # Automatically activate
        agent = factory.activate_agent(agent.id, db)

        # Audit log
        AuditLog.log_action(
            db_session=db,
            user_id=current_user.id,
            agent_id=agent.id,
            action_type="agent_activated",
            action_details={
                "session_id": session_id,
                "industry": agent.industry,
                "role": agent.role,
                "collection_id": agent.personal_rag_collection_id
            }
        )

        print(f"[API] Agent {agent.id} activated for user {current_user.id}")

        return AgentActivationResponse(
            agent_id=agent.id,
            status=agent.status.value,
            collection_id=agent.personal_rag_collection_id,
            industry=agent.industry or "",
            role=agent.role or "",
            user_segment_id=agent.user_segment_id or "",
            activated_at=agent.activated_at.isoformat() if agent.activated_at else None,
            message="Personal agent created and activated successfully"
        )

    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error creating agent: {str(e)}"
        )


# ============================================================================
# Agent Status
# ============================================================================

@router.get("/me", response_model=AgentStatusResponse)
async def get_my_agent_status(
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """
    Get current user's personal agent status.

    Returns:
        Agent details and metrics
    """
    agent = db.query(PersonalAIAgent).filter(
        PersonalAIAgent.user_id == current_user.id
    ).first()

    if not agent:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No personal agent found. Complete onboarding interview first."
        )

    return AgentStatusResponse(
        agent_id=agent.id,
        status=agent.status.value,
        industry=agent.industry,
        role=agent.role,
        total_conversations=agent.total_conversations,
        successful_matches=agent.successful_matches,
        learning_score=agent.learning_score,
        activated_at=agent.activated_at.isoformat() if agent.activated_at else None,
        last_search_at=agent.last_search_at.isoformat() if agent.last_search_at else None,
        can_search=agent.status == AgentStatus.ACTIVE
    )


# ============================================================================
# Agent Control
# ============================================================================

@router.post("/me/control", response_model=AgentStatusResponse)
async def control_my_agent(
    request: AgentControlRequest,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """
    Control personal agent (pause/resume).

    Actions:
    - pause: Stop agent from searching for matches
    - resume: Resume agent matching

    Returns:
        Updated agent status
    """
    agent = db.query(PersonalAIAgent).filter(
        PersonalAIAgent.user_id == current_user.id
    ).first()

    if not agent:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No personal agent found"
        )

    factory = create_personal_agent_factory()

    try:
        if request.action == "pause":
            agent = factory.pause_agent(agent.id, db)
        elif request.action == "resume":
            agent = factory.resume_agent(agent.id, db)
        else:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid action: {request.action}. Use 'pause' or 'resume'."
            )

        # Audit log
        AuditLog.log_action(
            db_session=db,
            user_id=current_user.id,
            agent_id=agent.id,
            action_type=f"agent_{request.action}",
            action_details={"action": request.action}
        )

        return AgentStatusResponse(
            agent_id=agent.id,
            status=agent.status.value,
            industry=agent.industry,
            role=agent.role,
            total_conversations=agent.total_conversations,
            successful_matches=agent.successful_matches,
            learning_score=agent.learning_score,
            activated_at=agent.activated_at.isoformat() if agent.activated_at else None,
            last_search_at=agent.last_search_at.isoformat() if agent.last_search_at else None,
            can_search=agent.status == AgentStatus.ACTIVE
        )

    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )


# ============================================================================
# Agent Metrics
# ============================================================================

@router.get("/me/metrics")
async def get_my_agent_metrics(
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """
    Get detailed metrics for personal agent.

    Returns:
        Comprehensive metrics and performance data
    """
    agent = db.query(PersonalAIAgent).filter(
        PersonalAIAgent.user_id == current_user.id
    ).first()

    if not agent:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No personal agent found"
        )

    success_rate = agent.get_success_rate()

    return {
        "agent_id": agent.id,
        "status": agent.status.value,
        "metrics": {
            "total_conversations": agent.total_conversations,
            "successful_matches": agent.successful_matches,
            "success_rate": round(success_rate, 2),
            "learning_score": round(agent.learning_score, 2),
            "active_conversations": agent.active_conversations_count,
            "max_concurrent": agent.max_concurrent_conversations
        },
        "profile": {
            "industry": agent.industry,
            "role": agent.role,
            "user_segment": agent.user_segment_id
        },
        "timeline": {
            "created_at": agent.created_at.isoformat(),
            "activated_at": agent.activated_at.isoformat() if agent.activated_at else None,
            "last_activity_at": agent.last_activity_at.isoformat() if agent.last_activity_at else None,
            "last_search_at": agent.last_search_at.isoformat() if agent.last_search_at else None
        }
    }
