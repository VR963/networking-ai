"""
Mobile Messages Router.

Endpoints:
- GET /conversations - List user's conversations
- GET /conversations/{conversation_id} - Get conversation messages
- POST /conversations/{conversation_id}/messages - Send message
"""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from sqlalchemy import desc, or_
from datetime import datetime
from typing import List

from ...database import get_db
from ...models.user import User
from ...models.message import Conversation, Message, MessageStatus
from ...models.application import Application
from .schemas import (
    ConversationCompact,
    ConversationDetail,
    ConversationListResponse,
    ParticipantCompact,
    LastMessage,
    RelatedTo,
    MessageDetail,
    SendMessageRequest,
    MessageResponse
)
from .responses import create_success_response, create_error_response, ErrorCode
from .dependencies import mobile_auth_required

messages_router = APIRouter()


def get_participant_info(user_id: int, current_user_id: int, db: Session) -> ParticipantCompact:
    """Get participant information."""
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        return None

    # Get profile for additional info
    from ...models.profile import UserProfile
    profile = db.query(UserProfile).filter(UserProfile.user_id == user_id).first()

    # Get company name if applicable
    company_name = None
    if user.role.value in ["hiring_manager", "recruiter"]:
        from ...models.company import Company
        company = db.query(Company).filter(Company.user_id == user_id).first()
        if company:
            company_name = company.name

    return ParticipantCompact(
        id=user.id,
        name=user.full_name,
        role=user.role.value,
        avatar_url=profile.profile_picture if profile else None,
        company=company_name
    )


@messages_router.get("/conversations", response_model=dict)
async def list_conversations(
    db: Session = Depends(get_db),
    user: User = Depends(mobile_auth_required)
):
    """
    List user's conversations.

    Returns all conversations with last message preview.
    """
    # Find conversations where user is participant
    conversations = db.query(Conversation).filter(
        or_(
            Conversation.user1_id == user.id,
            Conversation.user2_id == user.id
        )
    ).order_by(desc(Conversation.updated_at)).all()

    # Build response
    conversation_responses = []
    for conv in conversations:
        # Determine other participant
        other_user_id = conv.user2_id if conv.user1_id == user.id else conv.user1_id
        participant = get_participant_info(other_user_id, user.id, db)

        # Get last message
        last_msg = db.query(Message).filter(
            Message.conversation_id == conv.id
        ).order_by(desc(Message.created_at)).first()

        last_message = None
        if last_msg:
            last_message = LastMessage(
                text=last_msg.content,
                timestamp=last_msg.created_at,
                is_from_me=(last_msg.sender_id == user.id)
            )

        # Count unread messages
        unread_count = db.query(Message).filter(
            Message.conversation_id == conv.id,
            Message.sender_id != user.id,
            Message.status != MessageStatus.READ
        ).count()

        # Get related entity (application/job)
        related_to = None
        # TODO: Track conversation context (which application/job it's about)
        # For now, leave as None

        conversation_responses.append(
            ConversationCompact(
                id=conv.id,
                participant=participant,
                last_message=last_message,
                unread_count=unread_count,
                related_to=related_to
            )
        )

    return create_success_response(
        data={"data": [c.model_dump() for c in conversation_responses]},
        self_link="/api/v1/mobile/messages/conversations"
    )


@messages_router.get("/conversations/{conversation_id}", response_model=dict)
async def get_conversation_messages(
    conversation_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(mobile_auth_required)
):
    """
    Get conversation messages.

    Returns all messages in the conversation, sorted by timestamp.
    """
    # Find conversation
    conversation = db.query(Conversation).filter(
        Conversation.id == conversation_id
    ).first()

    if not conversation:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=create_error_response(
                code=ErrorCode.NOT_FOUND,
                message="Conversation not found"
            )
        )

    # Verify user is participant
    if conversation.user1_id != user.id and conversation.user2_id != user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=create_error_response(
                code=ErrorCode.FORBIDDEN,
                message="You are not a participant in this conversation"
            )
        )

    # Get other participant
    other_user_id = conversation.user2_id if conversation.user1_id == user.id else conversation.user1_id
    participant = get_participant_info(other_user_id, user.id, db)

    # Get messages
    messages = db.query(Message).filter(
        Message.conversation_id == conversation_id
    ).order_by(Message.created_at).all()

    # Build message responses
    message_responses = [
        MessageDetail(
            id=msg.id,
            from_user_id=msg.sender_id,
            text=msg.content,
            timestamp=msg.created_at,
            is_read=(msg.status == MessageStatus.READ)
        )
        for msg in messages
    ]

    # Mark messages as read
    unread_messages = [m for m in messages if m.sender_id != user.id and m.status != MessageStatus.READ]
    for msg in unread_messages:
        msg.status = MessageStatus.READ
        msg.read_at = datetime.utcnow()

    if unread_messages:
        db.commit()

    # Get related entity
    related_to = None
    # TODO: Get conversation context

    response = ConversationDetail(
        id=conversation.id,
        participant=participant,
        messages=message_responses,
        related_to=related_to
    )

    return create_success_response(
        data=response.model_dump(),
        self_link=f"/api/v1/mobile/messages/conversations/{conversation_id}"
    )


@messages_router.post("/conversations/{conversation_id}/messages", response_model=dict, status_code=status.HTTP_201_CREATED)
async def send_message(
    conversation_id: int,
    request: SendMessageRequest,
    db: Session = Depends(get_db),
    user: User = Depends(mobile_auth_required)
):
    """
    Send message in conversation.

    Creates a new message in the specified conversation.
    """
    # Find conversation
    conversation = db.query(Conversation).filter(
        Conversation.id == conversation_id
    ).first()

    if not conversation:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=create_error_response(
                code=ErrorCode.NOT_FOUND,
                message="Conversation not found"
            )
        )

    # Verify user is participant
    if conversation.user1_id != user.id and conversation.user2_id != user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=create_error_response(
                code=ErrorCode.FORBIDDEN,
                message="You are not a participant in this conversation"
            )
        )

    # Create message
    message = Message(
        conversation_id=conversation_id,
        sender_id=user.id,
        content=request.text,
        status=MessageStatus.SENT,
        created_at=datetime.utcnow()
    )
    db.add(message)

    # Update conversation timestamp
    conversation.updated_at = datetime.utcnow()

    db.commit()
    db.refresh(message)

    response = MessageResponse(
        id=message.id,
        text=message.content,
        timestamp=message.created_at
    )

    return create_success_response(
        data=response.model_dump(),
        self_link=f"/api/v1/mobile/messages/conversations/{conversation_id}/messages"
    )
