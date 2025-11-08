"""
Onboarding API Endpoints.

Handles CV upload, parsing, and AI interview process.
"""

import os
import shutil
from typing import Optional
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session
from pydantic import BaseModel

from ..database import get_db
from ..models.user import User
from ..models.personal_ai_agent import PersonalAIAgent, AgentType, AgentStatus
from ..models.interview_session import InterviewSession, InterviewStatus
from ..models.agent_conversation import AgentConversation, ConversationType, ConversationStatus
from ..models.audit_log import AuditLog
from ..api.auth import get_current_active_user
from ..services.cv_parser import create_cv_parser
from ..services.chromadb_service import create_chromadb_service
from ..agents.recruiter_agent import create_recruiter_agent
from ..master_ai import create_master_rag


router = APIRouter()

# Upload directory
UPLOAD_DIR = "./data/cv_uploads"
os.makedirs(UPLOAD_DIR, exist_ok=True)


# ============================================================================
# Request/Response Models
# ============================================================================

class CVUploadResponse(BaseModel):
    """Response after CV upload."""
    session_id: int
    message: str
    parsed_data: dict
    detected_industry: str
    detected_role: str
    confidence: dict


class StartInterviewRequest(BaseModel):
    """Request to start interview."""
    session_id: int


class StartInterviewResponse(BaseModel):
    """Response when starting interview."""
    conversation_id: int
    session_id: int
    opening_message: str
    recruiter_name: str


class InterviewMessageRequest(BaseModel):
    """Request to send message in interview."""
    conversation_id: int
    message: str


class InterviewMessageResponse(BaseModel):
    """Response from interview."""
    conversation_id: int
    recruiter_message: str
    completion_percentage: int
    topics_covered: list


class InterviewStatusResponse(BaseModel):
    """Interview status response."""
    session_id: int
    status: str
    completion_percentage: int
    topics_covered: list
    knowledge_extracted: dict


# ============================================================================
# CV Upload
# ============================================================================

@router.post("/cv-upload", response_model=CVUploadResponse, status_code=status.HTTP_201_CREATED)
async def upload_cv(
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """
    Upload CV for parsing.

    Step 1 of onboarding: User uploads their CV/resume.
    """
    # Validate file type
    allowed_extensions = ['.pdf', '.docx', '.doc']
    file_ext = os.path.splitext(file.filename)[1].lower()

    if file_ext not in allowed_extensions:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"File type not supported. Allowed: {', '.join(allowed_extensions)}"
        )

    # Save file
    file_id = f"{current_user.id}_{datetime.utcnow().timestamp()}"
    file_path = os.path.join(UPLOAD_DIR, f"{file_id}{file_ext}")

    try:
        with open(file_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)

        # Parse CV
        cv_parser = create_cv_parser()
        parsed_result = cv_parser.parse_cv_file(file_path)

        # Extract data
        parsed_data = parsed_result["parsed_data"]
        classification = parsed_result["classification"]

        # Generate user segment ID
        user_segment_id = cv_parser.generate_user_segment_id(classification)

        # Create interview session
        interview_session = InterviewSession(
            user_id=current_user.id,
            cv_file_path=file_path,
            cv_file_name=file.filename,
            cv_mime_type=file.content_type,
            cv_parsed_data=parsed_data,
            detected_industry=classification.get("industry"),
            detected_role=classification.get("role"),
            detected_skills=classification.get("primary_skills"),
            status=InterviewStatus.IN_PROGRESS
        )

        # We'll create the conversation when interview starts
        # For now, create a placeholder
        conversation = AgentConversation(
            agent1_id=None,  # Will be set when personal agent is created
            conversation_type=ConversationType.INTERVIEW,
            status=ConversationStatus.ACTIVE
        )
        db.add(conversation)
        db.flush()

        interview_session.conversation_id = conversation.id

        db.add(interview_session)
        db.commit()
        db.refresh(interview_session)

        # Audit log
        AuditLog.log_action(
            db_session=db,
            user_id=current_user.id,
            action_type="cv_uploaded",
            action_details={
                "filename": file.filename,
                "detected_industry": classification.get("industry"),
                "detected_role": classification.get("role")
            },
            interview_session_id=interview_session.id
        )

        print(f"[ONBOARDING] CV uploaded for user {current_user.id}: {classification.get('industry')}/{classification.get('role')}")

        return CVUploadResponse(
            session_id=interview_session.id,
            message="CV parsed successfully. Ready to start interview.",
            parsed_data=parsed_data,
            detected_industry=classification.get("industry", "unknown"),
            detected_role=classification.get("role", "unknown"),
            confidence={
                "industry": classification.get("industry_confidence", 0.0),
                "role": classification.get("role_confidence", 0.0)
            }
        )

    except Exception as e:
        # Clean up file if parsing failed
        if os.path.exists(file_path):
            os.remove(file_path)

        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error processing CV: {str(e)}"
        )


# ============================================================================
# Start Interview
# ============================================================================

@router.post("/start-interview", response_model=StartInterviewResponse)
async def start_interview(
    request: StartInterviewRequest,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """
    Start AI interview.

    Step 2 of onboarding: Begin conversation with recruiter agent.
    """
    # Get interview session
    session = db.query(InterviewSession).filter(
        InterviewSession.id == request.session_id,
        InterviewSession.user_id == current_user.id
    ).first()

    if not session:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Interview session not found"
        )

    if session.status != InterviewStatus.IN_PROGRESS:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Interview already completed or abandoned"
        )

    # Get Master RAG
    master_rag = create_master_rag()

    # Load recruiter training
    recruiter_training = master_rag.get_recruiter_training(session.detected_industry)

    if not recruiter_training:
        recruiter_training = "General recruiter training. Conduct professional interview."

    # Create recruiter agent
    recruiter = create_recruiter_agent(
        industry=session.detected_industry or "general",
        role=session.detected_role or "general",
        recruiter_training=recruiter_training
    )

    # Start interview
    opening_message = recruiter.start_interview(session.cv_parsed_data)

    # Save opening message to conversation
    conversation = db.query(AgentConversation).filter(
        AgentConversation.id == session.conversation_id
    ).first()

    conversation.add_message(
        role="recruiter",
        content=opening_message
    )

    db.commit()

    # Audit log
    AuditLog.log_action(
        db_session=db,
        user_id=current_user.id,
        action_type="interview_started",
        action_details={
            "session_id": session.id,
            "industry": session.detected_industry,
            "role": session.detected_role
        },
        conversation_id=conversation.id,
        interview_session_id=session.id
    )

    print(f"[ONBOARDING] Interview started for user {current_user.id}")

    return StartInterviewResponse(
        conversation_id=conversation.id,
        session_id=session.id,
        opening_message=opening_message,
        recruiter_name=f"{session.detected_industry.title()} Recruiter"
    )


# ============================================================================
# Interview Conversation
# ============================================================================

@router.post("/interview-message", response_model=InterviewMessageResponse)
async def send_interview_message(
    request: InterviewMessageRequest,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """
    Send message in interview conversation.

    Continues the AI interview dialogue.
    """
    # Get conversation
    conversation = db.query(AgentConversation).filter(
        AgentConversation.id == request.conversation_id
    ).first()

    if not conversation:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Conversation not found"
        )

    # Get interview session
    session = db.query(InterviewSession).filter(
        InterviewSession.conversation_id == conversation.id,
        InterviewSession.user_id == current_user.id
    ).first()

    if not session:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized"
        )

    # Add user message to conversation
    conversation.add_message(
        role="user",
        content=request.message
    )
    db.commit()

    # Get recruiter training
    master_rag = create_master_rag()
    recruiter_training = master_rag.get_recruiter_training(session.detected_industry)

    if not recruiter_training:
        recruiter_training = "General recruiter training."

    # Recreate recruiter agent (with conversation history)
    recruiter = create_recruiter_agent(
        industry=session.detected_industry or "general",
        role=session.detected_role or "general",
        recruiter_training=recruiter_training
    )

    # Continue interview
    recruiter_response = recruiter.ask_question(request.message)

    # Add recruiter response to conversation
    conversation.add_message(
        role="recruiter",
        content=recruiter_response
    )

    # Update session with extracted knowledge
    knowledge = recruiter.get_knowledge_extracted()
    if knowledge:
        if not session.knowledge_extracted:
            session.knowledge_extracted = {}
        session.knowledge_extracted.update(knowledge)

    # Update topics covered
    topics = list(knowledge.keys())
    if topics:
        if not session.topics_covered:
            session.topics_covered = []
        for topic in topics:
            if topic not in session.topics_covered:
                session.topics_covered.append(topic)

    session.update_completion()

    db.commit()

    # Audit log
    AuditLog.log_action(
        db_session=db,
        user_id=current_user.id,
        action_type="interview_message",
        action_details={
            "turn": conversation.turn_count,
            "knowledge_extracted": list(knowledge.keys())
        },
        conversation_id=conversation.id,
        interview_session_id=session.id
    )

    print(f"[ONBOARDING] Interview turn {conversation.turn_count} for user {current_user.id}")

    return InterviewMessageResponse(
        conversation_id=conversation.id,
        recruiter_message=recruiter_response,
        completion_percentage=session.completion_percentage,
        topics_covered=session.topics_covered or []
    )


# ============================================================================
# Interview Status
# ============================================================================

@router.get("/interview-status/{session_id}", response_model=InterviewStatusResponse)
async def get_interview_status(
    session_id: int,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """
    Get interview session status.

    Check progress and extracted knowledge.
    """
    session = db.query(InterviewSession).filter(
        InterviewSession.id == session_id,
        InterviewSession.user_id == current_user.id
    ).first()

    if not session:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Interview session not found"
        )

    return InterviewStatusResponse(
        session_id=session.id,
        status=session.status.value,
        completion_percentage=session.completion_percentage,
        topics_covered=session.topics_covered or [],
        knowledge_extracted=session.knowledge_extracted or {}
    )


# ============================================================================
# Complete Interview (Future)
# ============================================================================

@router.post("/complete-interview/{session_id}")
async def complete_interview(
    session_id: int,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """
    Complete interview and activate personal AI agent.

    Step 3: Create personal agent with learned knowledge and populate RAG.

    Flow:
    1. Mark interview session as completed
    2. Create Talent Personal AI Agent
    3. Create Talent RAG collection in ChromaDB
    4. Populate RAG with interview knowledge and CV data
    5. Activate agent for matching
    """
    session = db.query(InterviewSession).filter(
        InterviewSession.id == session_id,
        InterviewSession.user_id == current_user.id
    ).first()

    if not session:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Interview session not found"
        )

    if session.status == InterviewStatus.COMPLETED:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Interview already completed"
        )

    # Mark session as completed
    session.mark_completed()

    # Phase 2: Create Personal AI Agent
    # Check if agent already exists
    talent_agent = db.query(PersonalAIAgent).filter(
        PersonalAIAgent.user_id == current_user.id,
        PersonalAIAgent.agent_type == AgentType.TALENT
    ).first()

    if not talent_agent:
        # Create new Talent Personal Agent
        talent_agent = PersonalAIAgent(
            user_id=current_user.id,
            agent_type=AgentType.TALENT,
            status=AgentStatus.PENDING,
            industry=session.detected_industry,
            role=session.detected_role,
            created_at=datetime.utcnow()
        )
        db.add(talent_agent)
        db.flush()  # Get agent ID

        print(f"[ONBOARDING] Created Talent Personal Agent {talent_agent.id} for user {current_user.id}")

    # Phase 2: Build Personal RAG from knowledge_extracted
    try:
        chromadb_service = create_chromadb_service()

        # Create Talent RAG collection
        collection_name = chromadb_service.create_talent_rag(
            agent_id=talent_agent.id,
            user_id=current_user.id
        )

        # Update agent with RAG collection ID
        talent_agent.rag_collection_id = collection_name

        # Populate RAG with interview knowledge and CV data
        interview_data = session.knowledge_extracted or {}
        cv_data = session.cv_parsed_data or {}

        chromadb_service.populate_talent_rag(
            collection_name=collection_name,
            interview_data=interview_data,
            cv_data=cv_data
        )

        print(f"[ONBOARDING] Populated Talent RAG '{collection_name}' with interview and CV data")

        # Phase 2: Activate agent for matching
        talent_agent.status = AgentStatus.ACTIVE
        talent_agent.activated_at = datetime.utcnow()

        print(f"[ONBOARDING] Activated Talent Personal Agent {talent_agent.id}")

    except ImportError as e:
        # ChromaDB not installed - graceful degradation
        print(f"[ONBOARDING] ChromaDB not available, skipping RAG population: {e}")
        print(f"[ONBOARDING] Agent will use placeholder data for matching")

        # Still activate agent (matching service has fallback)
        talent_agent.status = AgentStatus.ACTIVE
        talent_agent.activated_at = datetime.utcnow()

    except Exception as e:
        # Other errors - log but continue
        print(f"[ONBOARDING] Error populating RAG: {e}")
        print(f"[ONBOARDING] Agent will use placeholder data for matching")

        # Still activate agent
        talent_agent.status = AgentStatus.ACTIVE
        talent_agent.activated_at = datetime.utcnow()

    db.commit()

    # Audit log
    audit = AuditLog(
        user_id=current_user.id,
        action="talent_agent_activated",
        details={
            "agent_id": talent_agent.id,
            "session_id": session_id,
            "rag_collection": talent_agent.rag_collection_id
        }
    )
    db.add(audit)
    db.commit()

    return {
        "message": "Interview completed! Your personal AI agent has been activated and is ready for matching.",
        "agent_id": talent_agent.id,
        "completion_percentage": session.completion_percentage,
        "knowledge_extracted": session.knowledge_extracted,
        "rag_collection": talent_agent.rag_collection_id
    }
