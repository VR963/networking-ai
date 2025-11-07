"""
Message Models - Messaging System.

Conversation: Chat thread between two users
Message: Individual messages within a conversation
"""

from datetime import datetime
from enum import Enum
from typing import Dict

from sqlalchemy import Column, Integer, String, Text, Boolean, DateTime, ForeignKey, Enum as SQLEnum
from sqlalchemy.orm import relationship

from ..database import Base


class MessageStatus(str, Enum):
    """Message delivery status."""
    SENT = "sent"
    DELIVERED = "delivered"
    READ = "read"
    FAILED = "failed"


class Conversation(Base):
    """
    Conversation thread between two users.

    Typically between job seeker and company recruiter.
    """
    __tablename__ = "conversations"

    # Primary Key
    id = Column(Integer, primary_key=True, index=True)
    user1_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    user2_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)

    # Context
    job_id = Column(Integer, ForeignKey("jobs.id"), nullable=True, index=True)  # Context job if applicable
    application_id = Column(Integer, ForeignKey("applications.id"), nullable=True)  # Context application

    # Status
    is_active = Column(Boolean, default=True)
    is_archived_by_user1 = Column(Boolean, default=False)
    is_archived_by_user2 = Column(Boolean, default=False)
    is_blocked = Column(Boolean, default=False)

    # Last Message Info
    last_message_at = Column(DateTime(timezone=True), nullable=True, index=True)
    last_message_preview = Column(String(500), nullable=True)

    # Unread Counts
    unread_count_user1 = Column(Integer, default=0)
    unread_count_user2 = Column(Integer, default=0)

    # Timestamps
    created_at = Column(DateTime(timezone=True), default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime(timezone=True), default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    # Relationships
    user1 = relationship("User", foreign_keys=[user1_id], back_populates="conversations_initiated")
    user2 = relationship("User", foreign_keys=[user2_id], back_populates="conversations_received")
    messages = relationship("Message", back_populates="conversation", cascade="all, delete-orphan", order_by="Message.created_at")

    def __repr__(self):
        return f"<Conversation {self.id} between users {self.user1_id} and {self.user2_id}>"

    def to_dict(self) -> Dict:
        """Convert to dictionary."""
        return {
            'id': self.id,
            'user1_id': self.user1_id,
            'user2_id': self.user2_id,
            'job_id': self.job_id,
            'application_id': self.application_id,
            'is_active': self.is_active,
            'is_blocked': self.is_blocked,
            'last_message_at': self.last_message_at.isoformat() if self.last_message_at else None,
            'last_message_preview': self.last_message_preview,
            'unread_count_user1': self.unread_count_user1,
            'unread_count_user2': self.unread_count_user2,
            'created_at': self.created_at.isoformat(),
            'updated_at': self.updated_at.isoformat(),
        }


class Message(Base):
    """
    Individual message within a conversation.
    """
    __tablename__ = "messages"

    # Primary Key
    id = Column(Integer, primary_key=True, index=True)
    conversation_id = Column(Integer, ForeignKey("conversations.id"), nullable=False, index=True)
    sender_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)

    # Message Content
    content = Column(Text, nullable=False)
    message_type = Column(String(50), default="text")  # text, image, file, system

    # Attachments
    attachment_url = Column(String(500), nullable=True)
    attachment_type = Column(String(50), nullable=True)  # image, pdf, etc
    attachment_name = Column(String(255), nullable=True)

    # Status
    status = Column(SQLEnum(MessageStatus), default=MessageStatus.SENT, index=True)
    is_read = Column(Boolean, default=False, index=True)
    read_at = Column(DateTime(timezone=True), nullable=True)

    # AI Features
    is_ai_assisted = Column(Boolean, default=False)  # Was this message AI-assisted?
    ai_suggestions = Column(Text, nullable=True)  # AI suggestions for reply

    # Timestamps
    created_at = Column(DateTime(timezone=True), default=datetime.utcnow, nullable=False, index=True)
    updated_at = Column(DateTime(timezone=True), default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    # Relationships
    conversation = relationship("Conversation", back_populates="messages")
    sender = relationship("User", foreign_keys=[sender_id], back_populates="sent_messages")

    def __repr__(self):
        return f"<Message {self.id} from user {self.sender_id}>"

    def to_dict(self) -> Dict:
        """Convert to dictionary."""
        return {
            'id': self.id,
            'conversation_id': self.conversation_id,
            'sender_id': self.sender_id,
            'content': self.content,
            'message_type': self.message_type,
            'attachment_url': self.attachment_url,
            'attachment_type': self.attachment_type,
            'attachment_name': self.attachment_name,
            'status': self.status.value,
            'is_read': self.is_read,
            'read_at': self.read_at.isoformat() if self.read_at else None,
            'is_ai_assisted': self.is_ai_assisted,
            'created_at': self.created_at.isoformat(),
            'updated_at': self.updated_at.isoformat(),
        }
