"""
Messaging API Endpoints.

Handles conversations and messages between users.
"""

from typing import List
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from sqlalchemy import or_, and_

from ..database import get_db
from ..models.user import User
from ..models.message import Conversation, Message, MessageStatus
from ..api.auth import get_current_user, get_current_active_user


router = APIRouter()


# ============================================================================
# Conversation Endpoints
# ============================================================================

@router.get("")
async def get_my_conversations(
    limit: int = 20,
    offset: int = 0,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    """
    Get all conversations for current user.

    Returns conversations sorted by most recent message.
    """
    # Get conversations where user is participant
    conversations = db.query(Conversation).filter(
        or_(
            Conversation.user1_id == current_user.id,
            Conversation.user2_id == current_user.id
        ),
        Conversation.is_active == True,
    ).order_by(
        Conversation.last_message_at.desc()
    ).offset(offset).limit(limit).all()

    # Format response
    result = []
    for conv in conversations:
        # Determine the other user
        other_user_id = conv.user2_id if conv.user1_id == current_user.id else conv.user1_id
        other_user = db.query(User).filter(User.id == other_user_id).first()

        # Get unread count for current user
        unread_count = conv.unread_count_user2 if conv.user1_id == current_user.id else conv.unread_count_user1

        result.append({
            "conversation_id": conv.id,
            "other_user": {
                "id": other_user.id,
                "name": other_user.full_name,
                "role": other_user.role.value,
            },
            "last_message": conv.last_message_preview,
            "last_message_at": conv.last_message_at.isoformat() if conv.last_message_at else None,
            "unread_count": unread_count,
            "job_id": conv.job_id,
            "created_at": conv.created_at.isoformat(),
        })

    return {
        "conversations": result,
        "total": len(result),
    }


@router.post("")
async def start_conversation(
    other_user_id: int,
    job_id: int = None,
    initial_message: str = None,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    """
    Start a new conversation with another user.

    Can optionally be linked to a specific job.
    """
    # Check if other user exists
    other_user = db.query(User).filter(User.id == other_user_id).first()

    if not other_user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found.",
        )

    # Can't start conversation with self
    if other_user_id == current_user.id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot start conversation with yourself.",
        )

    # Check if conversation already exists
    existing_conv = db.query(Conversation).filter(
        or_(
            and_(
                Conversation.user1_id == current_user.id,
                Conversation.user2_id == other_user_id
            ),
            and_(
                Conversation.user1_id == other_user_id,
                Conversation.user2_id == current_user.id
            )
        ),
        Conversation.is_active == True,
    ).first()

    if existing_conv:
        return {
            "message": "Conversation already exists",
            "conversation_id": existing_conv.id,
        }

    # Create new conversation
    conversation = Conversation(
        user1_id=current_user.id,
        user2_id=other_user_id,
        job_id=job_id,
    )

    db.add(conversation)
    db.commit()
    db.refresh(conversation)

    # Send initial message if provided
    if initial_message:
        message = Message(
            conversation_id=conversation.id,
            sender_id=current_user.id,
            content=initial_message,
        )
        db.add(message)

        # Update conversation
        conversation.last_message_at = datetime.utcnow()
        conversation.last_message_preview = initial_message[:500]
        conversation.unread_count_user2 = 1

        db.commit()

    print(f"[MESSAGE] Conversation started between users {current_user.id} and {other_user_id}")

    return {
        "message": "Conversation started successfully",
        "conversation_id": conversation.id,
    }


@router.get("/{conversation_id}")
async def get_conversation(
    conversation_id: int,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    """Get conversation details."""
    conversation = db.query(Conversation).filter(Conversation.id == conversation_id).first()

    if not conversation:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Conversation not found.",
        )

    # Check permission
    if current_user.id not in [conversation.user1_id, conversation.user2_id]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You don't have permission to view this conversation.",
        )

    # Get other user
    other_user_id = conversation.user2_id if conversation.user1_id == current_user.id else conversation.user1_id
    other_user = db.query(User).filter(User.id == other_user_id).first()

    return {
        "conversation_id": conversation.id,
        "other_user": {
            "id": other_user.id,
            "name": other_user.full_name,
            "role": other_user.role.value,
        },
        "job_id": conversation.job_id,
        "is_active": conversation.is_active,
        "created_at": conversation.created_at.isoformat(),
    }


# ============================================================================
# Message Endpoints
# ============================================================================

@router.get("/{conversation_id}/messages")
async def get_messages(
    conversation_id: int,
    limit: int = 50,
    offset: int = 0,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    """
    Get messages in a conversation.

    Returns messages sorted by newest first.
    """
    # Get conversation
    conversation = db.query(Conversation).filter(Conversation.id == conversation_id).first()

    if not conversation:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Conversation not found.",
        )

    # Check permission
    if current_user.id not in [conversation.user1_id, conversation.user2_id]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You don't have permission to view these messages.",
        )

    # Get messages
    messages = db.query(Message).filter(
        Message.conversation_id == conversation_id
    ).order_by(
        Message.created_at.desc()
    ).offset(offset).limit(limit).all()

    # Mark unread messages as read
    unread_messages = [m for m in messages if m.sender_id != current_user.id and not m.is_read]

    if unread_messages:
        for msg in unread_messages:
            msg.is_read = True
            msg.read_at = datetime.utcnow()

        # Update unread count
        if conversation.user1_id == current_user.id:
            conversation.unread_count_user1 = 0
        else:
            conversation.unread_count_user2 = 0

        db.commit()

    # Format response
    result = []
    for msg in reversed(messages):  # Return in chronological order
        result.append({
            "message_id": msg.id,
            "sender_id": msg.sender_id,
            "is_mine": msg.sender_id == current_user.id,
            "content": msg.content,
            "message_type": msg.message_type,
            "attachment_url": msg.attachment_url,
            "is_read": msg.is_read,
            "read_at": msg.read_at.isoformat() if msg.read_at else None,
            "created_at": msg.created_at.isoformat(),
        })

    return {
        "conversation_id": conversation_id,
        "messages": result,
        "total": len(messages),
    }


@router.post("/{conversation_id}/messages")
async def send_message(
    conversation_id: int,
    content: str,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    """Send a message in a conversation."""
    # Get conversation
    conversation = db.query(Conversation).filter(Conversation.id == conversation_id).first()

    if not conversation:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Conversation not found.",
        )

    # Check permission
    if current_user.id not in [conversation.user1_id, conversation.user2_id]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You don't have permission to send messages in this conversation.",
        )

    # Check if conversation is blocked
    if conversation.is_blocked:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="This conversation has been blocked.",
        )

    # Validate content
    if not content or len(content.strip()) == 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Message content cannot be empty.",
        )

    if len(content) > 10000:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Message is too long (max 10,000 characters).",
        )

    # Create message
    message = Message(
        conversation_id=conversation_id,
        sender_id=current_user.id,
        content=content,
        message_type="text",
    )

    db.add(message)

    # Update conversation
    conversation.last_message_at = datetime.utcnow()
    conversation.last_message_preview = content[:500]

    # Increment unread count for other user
    if conversation.user1_id == current_user.id:
        conversation.unread_count_user2 += 1
    else:
        conversation.unread_count_user1 += 1

    db.commit()
    db.refresh(message)

    print(f"[MESSAGE] Message sent in conversation {conversation_id} by user {current_user.id}")

    # TODO: Send push notification to other user
    # TODO: Send email notification if user has email notifications enabled

    return {
        "message": "Message sent successfully",
        "message_id": message.id,
        "created_at": message.created_at.isoformat(),
    }


@router.put("/messages/{message_id}/read")
async def mark_message_as_read(
    message_id: int,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    """Mark a specific message as read."""
    message = db.query(Message).filter(Message.id == message_id).first()

    if not message:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Message not found.",
        )

    # Get conversation
    conversation = message.conversation

    # Check permission
    if current_user.id not in [conversation.user1_id, conversation.user2_id]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You don't have permission to modify this message.",
        )

    # Can only mark messages from other user as read
    if message.sender_id == current_user.id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot mark your own message as read.",
        )

    # Mark as read
    if not message.is_read:
        message.is_read = True
        message.read_at = datetime.utcnow()

        # Decrement unread count
        if conversation.user1_id == current_user.id:
            conversation.unread_count_user1 = max(0, conversation.unread_count_user1 - 1)
        else:
            conversation.unread_count_user2 = max(0, conversation.unread_count_user2 - 1)

        db.commit()

    return {
        "message": "Message marked as read",
        "message_id": message_id,
    }


# ============================================================================
# Conversation Management
# ============================================================================

@router.delete("/{conversation_id}")
async def archive_conversation(
    conversation_id: int,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    """
    Archive a conversation (hide from list).

    Doesn't delete messages, just archives for current user.
    """
    conversation = db.query(Conversation).filter(Conversation.id == conversation_id).first()

    if not conversation:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Conversation not found.",
        )

    # Check permission
    if current_user.id not in [conversation.user1_id, conversation.user2_id]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You don't have permission to archive this conversation.",
        )

    # Archive for current user
    if conversation.user1_id == current_user.id:
        conversation.is_archived_by_user1 = True
    else:
        conversation.is_archived_by_user2 = True

    # If both users archived, mark as inactive
    if conversation.is_archived_by_user1 and conversation.is_archived_by_user2:
        conversation.is_active = False

    db.commit()

    print(f"[MESSAGE] Conversation {conversation_id} archived by user {current_user.id}")

    return {
        "message": "Conversation archived successfully",
    }


@router.get("/unread/count")
async def get_unread_count(
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    """Get total unread message count for current user."""
    # Get all active conversations
    conversations = db.query(Conversation).filter(
        or_(
            Conversation.user1_id == current_user.id,
            Conversation.user2_id == current_user.id
        ),
        Conversation.is_active == True,
    ).all()

    # Sum unread counts
    total_unread = 0
    for conv in conversations:
        if conv.user1_id == current_user.id:
            total_unread += conv.unread_count_user1
        else:
            total_unread += conv.unread_count_user2

    return {
        "total_unread": total_unread,
        "conversations_with_unread": len([c for c in conversations if (c.unread_count_user1 > 0 if c.user1_id == current_user.id else c.unread_count_user2 > 0)]),
    }
