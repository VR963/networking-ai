"""
Agent Messaging API - Phase 2 Week 3.

REST API endpoints for agent-to-agent conversations.

Endpoints:
- POST /agent-messages/send - Send a message
- POST /agent-messages/compose - AI-compose and send a message
- GET /agent-messages/conversations - Get all conversations
- GET /agent-messages/thread/{thread_id} - Get a specific thread
- POST /agent-messages/thread/{thread_id}/read - Mark thread as read
- GET /agent-messages/unread-count - Get unread count
- GET /agent-messages/search - Search messages
"""

from typing import Optional, List
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session
from pydantic import BaseModel, Field

from ..database import get_db
from ..models.user import User
from ..models.personal_ai_agent import PersonalAIAgent, AgentType
from ..models.agent_message import MessageType, ConversationContext
from ..services.agent_messaging_service import create_agent_messaging_service
from ..api.auth import get_current_active_user


router = APIRouter(prefix="/agent-messages", tags=["Agent Messaging"])


# ==================== Request/Response Models ====================

class SendMessageRequest(BaseModel):
    """Request to send a message."""
    receiver_agent_type: str = Field(..., description="Type of receiver agent (talent/hiring_manager/company_admin)")
    receiver_agent_id: int = Field(..., description="ID of receiver agent")
    content: str = Field(..., min_length=1, max_length=5000, description="Message content")
    message_type: str = Field(default="question", description="Message type")
    context_type: str = Field(default="general", description="Conversation context")
    subject: Optional[str] = Field(None, max_length=200, description="Optional subject line")
    match_id: Optional[int] = None
    application_id: Optional[int] = None
    job_id: Optional[int] = None
    parent_message_id: Optional[int] = Field(None, description="Parent message ID if replying")

    class Config:
        json_schema_extra = {
            "example": {
                "receiver_agent_type": "hiring_manager",
                "receiver_agent_id": 5,
                "content": "I noticed your job posting for Senior Engineer. Could you tell me more about the team structure?",
                "message_type": "question",
                "context_type": "match",
                "match_id": 42
            }
        }


class ComposeMessageRequest(BaseModel):
    """Request to compose an AI-generated message."""
    receiver_agent_type: str = Field(..., description="Type of receiver agent")
    receiver_agent_id: int = Field(..., description="ID of receiver agent")
    prompt: str = Field(..., min_length=1, max_length=1000, description="What you want the message to say")
    message_type: str = Field(default="question", description="Message type")
    context_type: str = Field(default="general", description="Conversation context")
    subject: Optional[str] = Field(None, max_length=200)
    match_id: Optional[int] = None
    application_id: Optional[int] = None
    job_id: Optional[int] = None
    parent_message_id: Optional[int] = None
    send_immediately: bool = Field(default=True, description="Send immediately or return draft")

    class Config:
        json_schema_extra = {
            "example": {
                "receiver_agent_type": "talent",
                "receiver_agent_id": 12,
                "prompt": "Ask about their Python experience and machine learning projects",
                "context_type": "application",
                "application_id": 15,
                "send_immediately": True
            }
        }


class MessageResponse(BaseModel):
    """Message response."""
    id: int
    thread_id: str
    sender: dict
    receiver: dict
    message_type: str
    subject: Optional[str]
    content: str
    ai_generated: bool
    context: dict
    is_read: bool
    read_at: Optional[datetime]
    created_at: datetime

    class Config:
        from_attributes = True


class ConversationSummary(BaseModel):
    """Conversation thread summary."""
    thread_id: str
    context_type: str
    participants: dict
    last_message_content: str
    last_message_time: datetime
    unread_count: int
    total_messages: int


class UnreadCountResponse(BaseModel):
    """Unread count response."""
    unread_count: int
    agent_type: str
    agent_id: int


# ==================== Helper Functions ====================

def get_current_user_agent(
    current_user: User,
    db: Session
) -> tuple[str, int, int]:
    """
    Get the current user's primary agent.

    Returns:
        Tuple of (agent_type, agent_id, user_id)
    """
    # Check for Talent agent
    talent_agent = db.query(PersonalAIAgent).filter(
        PersonalAIAgent.user_id == current_user.id,
        PersonalAIAgent.agent_type == AgentType.TALENT
    ).first()

    if talent_agent:
        return ("talent", talent_agent.id, current_user.id)

    # Check for HM agent
    hm_agent = db.query(PersonalAIAgent).filter(
        PersonalAIAgent.user_id == current_user.id,
        PersonalAIAgent.agent_type == AgentType.HIRING_MANAGER
    ).first()

    if hm_agent:
        return ("hiring_manager", hm_agent.id, current_user.id)

    # Check for Company Admin agent
    from ..models.company_admin_agent import CompanyAdminAgent
    admin_agent = db.query(CompanyAdminAgent).filter(
        CompanyAdminAgent.created_by_user_id == current_user.id
    ).first()

    if admin_agent:
        return ("company_admin", admin_agent.id, current_user.id)

    raise HTTPException(
        status_code=status.HTTP_404_NOT_FOUND,
        detail="No active agent found for current user"
    )


def get_receiver_user_id(
    receiver_agent_type: str,
    receiver_agent_id: int,
    db: Session
) -> Optional[int]:
    """Get the user ID for a receiver agent."""
    if receiver_agent_type in ["talent", "hiring_manager"]:
        agent = db.query(PersonalAIAgent).filter(
            PersonalAIAgent.id == receiver_agent_id
        ).first()
        return agent.user_id if agent else None

    elif receiver_agent_type == "company_admin":
        from ..models.company_admin_agent import CompanyAdminAgent
        agent = db.query(CompanyAdminAgent).filter(
            CompanyAdminAgent.id == receiver_agent_id
        ).first()
        return agent.created_by_user_id if agent else None

    return None


# ==================== API Endpoints ====================

@router.post("/send", response_model=MessageResponse)
async def send_message(
    request: SendMessageRequest,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """
    Send a message from current user's agent to another agent.

    The message is sent directly without AI composition.
    """
    # Get sender agent
    sender_agent_type, sender_agent_id, sender_user_id = get_current_user_agent(current_user, db)

    # Get receiver user ID
    receiver_user_id = get_receiver_user_id(request.receiver_agent_type, request.receiver_agent_id, db)

    if not receiver_user_id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Receiver agent not found"
        )

    # Create messaging service
    messaging_service = create_agent_messaging_service()

    # Send message
    try:
        message = messaging_service.send_message(
            sender_agent_type=sender_agent_type,
            sender_agent_id=sender_agent_id,
            sender_user_id=sender_user_id,
            receiver_agent_type=request.receiver_agent_type,
            receiver_agent_id=request.receiver_agent_id,
            receiver_user_id=receiver_user_id,
            content=request.content,
            message_type=MessageType(request.message_type),
            context_type=ConversationContext(request.context_type),
            subject=request.subject,
            match_id=request.match_id,
            application_id=request.application_id,
            job_id=request.job_id,
            parent_message_id=request.parent_message_id,
            ai_generated=False,
            db=db
        )

        return MessageResponse(**message.to_dict())

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to send message: {str(e)}"
        )


@router.post("/compose", response_model=MessageResponse)
async def compose_and_send_message(
    request: ComposeMessageRequest,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """
    Compose an AI-generated message and optionally send it.

    The AI will compose a professional message based on your prompt,
    using knowledge from both agents' RAG collections.
    """
    # Get sender agent
    sender_agent_type, sender_agent_id, sender_user_id = get_current_user_agent(current_user, db)

    # Get receiver user ID
    receiver_user_id = get_receiver_user_id(request.receiver_agent_type, request.receiver_agent_id, db)

    if not receiver_user_id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Receiver agent not found"
        )

    # Create messaging service
    messaging_service = create_agent_messaging_service()

    # Build context data
    context_data = {}
    if request.match_id:
        context_data["match_id"] = request.match_id
    if request.application_id:
        context_data["application_id"] = request.application_id
    if request.job_id:
        context_data["job_id"] = request.job_id

    try:
        # Compose AI message
        ai_content = messaging_service.compose_ai_message(
            sender_agent_type=sender_agent_type,
            sender_agent_id=sender_agent_id,
            receiver_agent_type=request.receiver_agent_type,
            receiver_agent_id=request.receiver_agent_id,
            prompt=request.prompt,
            context_type=ConversationContext(request.context_type),
            context_data=context_data,
            db=db
        )

        # Send if requested
        if request.send_immediately:
            message = messaging_service.send_message(
                sender_agent_type=sender_agent_type,
                sender_agent_id=sender_agent_id,
                sender_user_id=sender_user_id,
                receiver_agent_type=request.receiver_agent_type,
                receiver_agent_id=request.receiver_agent_id,
                receiver_user_id=receiver_user_id,
                content=ai_content,
                message_type=MessageType(request.message_type),
                context_type=ConversationContext(request.context_type),
                subject=request.subject,
                match_id=request.match_id,
                application_id=request.application_id,
                job_id=request.job_id,
                parent_message_id=request.parent_message_id,
                ai_generated=True,
                db=db
            )

            return MessageResponse(**message.to_dict())
        else:
            # Return draft (not saved)
            return MessageResponse(
                id=0,
                thread_id="draft",
                sender={
                    "agent_type": sender_agent_type,
                    "agent_id": sender_agent_id,
                    "user_id": sender_user_id
                },
                receiver={
                    "agent_type": request.receiver_agent_type,
                    "agent_id": request.receiver_agent_id,
                    "user_id": receiver_user_id
                },
                message_type=request.message_type,
                subject=request.subject,
                content=ai_content,
                ai_generated=True,
                context={
                    "type": request.context_type,
                    "match_id": request.match_id,
                    "application_id": request.application_id,
                    "job_id": request.job_id
                },
                is_read=False,
                read_at=None,
                created_at=datetime.utcnow()
            )

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to compose message: {str(e)}"
        )


@router.get("/conversations", response_model=List[ConversationSummary])
async def get_conversations(
    only_unread: bool = Query(False, description="Only show threads with unread messages"),
    context_type: Optional[str] = Query(None, description="Filter by context type"),
    limit: int = Query(50, ge=1, le=100, description="Maximum number of threads"),
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """
    Get all conversation threads for the current user's agent.

    Returns a list of conversation summaries sorted by most recent activity.
    """
    # Get current user's agent
    agent_type, agent_id, user_id = get_current_user_agent(current_user, db)

    # Create messaging service
    messaging_service = create_agent_messaging_service(use_rag=False)

    # Get conversations
    conversations = messaging_service.get_agent_conversations(
        agent_type=agent_type,
        agent_id=agent_id,
        db=db,
        only_unread=only_unread,
        context_type=ConversationContext(context_type) if context_type else None,
        limit=limit
    )

    # Format response
    summaries = []
    for conv in conversations:
        last_msg = conv["last_message"]
        summaries.append(ConversationSummary(
            thread_id=conv["thread_id"],
            context_type=conv["context_type"],
            participants=conv["participants"],
            last_message_content=last_msg.content[:100] + "..." if len(last_msg.content) > 100 else last_msg.content,
            last_message_time=last_msg.created_at,
            unread_count=conv["unread_count"],
            total_messages=conv["total_messages"]
        ))

    return summaries


@router.get("/thread/{thread_id}", response_model=List[MessageResponse])
async def get_conversation_thread(
    thread_id: str,
    limit: int = Query(100, ge=1, le=500, description="Maximum number of messages"),
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """
    Get all messages in a specific conversation thread.

    Returns messages in chronological order.
    """
    # Verify user has access to this thread
    agent_type, agent_id, user_id = get_current_user_agent(current_user, db)

    # Create messaging service
    messaging_service = create_agent_messaging_service(use_rag=False)

    # Get thread
    messages = messaging_service.get_conversation_thread(
        thread_id=thread_id,
        db=db,
        limit=limit
    )

    if not messages:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Thread not found"
        )

    # Verify user is a participant
    first_msg = messages[0]
    is_participant = (
        (first_msg.sender_agent_type == agent_type and first_msg.sender_agent_id == agent_id) or
        (first_msg.receiver_agent_type == agent_type and first_msg.receiver_agent_id == agent_id)
    )

    if not is_participant:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You do not have access to this conversation"
        )

    return [MessageResponse(**msg.to_dict()) for msg in messages]


@router.post("/thread/{thread_id}/read")
async def mark_thread_as_read(
    thread_id: str,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """
    Mark all messages in a thread as read for the current user's agent.
    """
    # Get current user's agent
    agent_type, agent_id, user_id = get_current_user_agent(current_user, db)

    # Create messaging service
    messaging_service = create_agent_messaging_service(use_rag=False)

    # Mark as read
    count = messaging_service.mark_thread_as_read(
        thread_id=thread_id,
        agent_type=agent_type,
        agent_id=agent_id,
        db=db
    )

    return {
        "thread_id": thread_id,
        "messages_marked_read": count,
        "status": "success"
    }


@router.get("/unread-count", response_model=UnreadCountResponse)
async def get_unread_count(
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """
    Get the count of unread messages for the current user's agent.
    """
    # Get current user's agent
    agent_type, agent_id, user_id = get_current_user_agent(current_user, db)

    # Create messaging service
    messaging_service = create_agent_messaging_service(use_rag=False)

    # Get unread count
    count = messaging_service.get_unread_count(
        agent_type=agent_type,
        agent_id=agent_id,
        db=db
    )

    return UnreadCountResponse(
        unread_count=count,
        agent_type=agent_type,
        agent_id=agent_id
    )


@router.get("/search", response_model=List[MessageResponse])
async def search_messages(
    query: str = Query(..., min_length=2, description="Search query"),
    limit: int = Query(20, ge=1, le=100, description="Maximum results"),
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """
    Search messages for the current user's agent.

    Searches in message content and subjects.
    """
    # Get current user's agent
    agent_type, agent_id, user_id = get_current_user_agent(current_user, db)

    # Create messaging service
    messaging_service = create_agent_messaging_service(use_rag=False)

    # Search
    messages = messaging_service.search_messages(
        agent_type=agent_type,
        agent_id=agent_id,
        query=query,
        db=db,
        limit=limit
    )

    return [MessageResponse(**msg.to_dict()) for msg in messages]
