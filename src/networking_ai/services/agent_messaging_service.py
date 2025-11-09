"""
Agent Messaging Service - Phase 2 Week 3 + Phase 3 Week 1.

Manages agent-to-agent conversations with AI-powered message composition.
Now includes real-time WebSocket broadcasting for live message delivery.

Key Features:
- Send messages between any two agents
- AI-generated message composition using RAG
- Thread management and organization
- Context-aware conversations (match, application, job)
- Message retrieval and filtering
- Read/unread status tracking
- Real-time WebSocket broadcasting (Phase 3)
"""

from typing import List, Dict, Optional, Tuple
from datetime import datetime, timedelta
from sqlalchemy.orm import Session
from sqlalchemy import or_, and_, desc
import asyncio

from langchain_anthropic import ChatAnthropic
from langchain.schema import HumanMessage, SystemMessage

from ..models.agent_message import AgentMessage, MessageType, ConversationContext, ConversationThread
from ..models.personal_ai_agent import PersonalAIAgent, AgentType
from ..models.match import Match
from ..models.application import Application
from ..models.job import Job
from ..services.chromadb_service import ChromaDBService, create_chromadb_service


class AgentMessagingService:
    """
    Service for managing agent-to-agent conversations.

    Handles message creation, retrieval, and AI-powered composition.
    """

    def __init__(
        self,
        anthropic_api_key: Optional[str] = None,
        chromadb_service: Optional[ChromaDBService] = None,
        use_rag: bool = True,
        enable_websocket: bool = True
    ):
        """
        Initialize messaging service.

        Args:
            anthropic_api_key: Anthropic API key for Claude
            chromadb_service: ChromaDB service for RAG
            use_rag: Whether to use RAG for message composition
            enable_websocket: Enable real-time WebSocket broadcasting
        """
        import os

        api_key = anthropic_api_key or os.getenv("ANTHROPIC_API_KEY")

        if not api_key:
            raise ValueError("ANTHROPIC_API_KEY must be provided or set in environment")

        self.llm = ChatAnthropic(
            model="claude-3-5-sonnet-20241022",
            api_key=api_key,
            temperature=0.7,
            max_tokens=1000
        )

        self.use_rag = use_rag
        if use_rag:
            try:
                self.chromadb = chromadb_service or create_chromadb_service()
            except ImportError:
                print("[AgentMessaging] ChromaDB not available, RAG disabled")
                self.use_rag = False
                self.chromadb = None
        else:
            self.chromadb = None

        # WebSocket broadcasting
        self.enable_websocket = enable_websocket
        self._connection_manager = None

    def _get_connection_manager(self):
        """Get connection manager lazily to avoid circular imports."""
        if self._connection_manager is None and self.enable_websocket:
            try:
                from ..websocket.connection_manager import get_connection_manager
                self._connection_manager = get_connection_manager()
            except ImportError:
                print("[AgentMessaging] WebSocket not available")
                self.enable_websocket = False
        return self._connection_manager

    async def _broadcast_new_message(self, message: AgentMessage):
        """
        Broadcast new message via WebSocket to receiver.

        Args:
            message: AgentMessage that was sent
        """
        if not self.enable_websocket:
            return

        connection_manager = self._get_connection_manager()
        if not connection_manager:
            return

        try:
            from ..websocket.event_types import NewMessageEvent

            # Create WebSocket event
            event = NewMessageEvent.create(
                message_id=message.id,
                thread_id=message.thread_id,
                sender_agent_type=message.sender_agent_type,
                sender_agent_id=message.sender_agent_id,
                content=message.content,
                subject=message.subject,
                message_type=message.message_type.value,
                context_type=message.context_type.value
            )

            # Send to receiver's user
            if message.receiver_user_id:
                await connection_manager.send_to_user(
                    user_id=message.receiver_user_id,
                    message=event.model_dump()
                )

                print(f"[AgentMessaging] Broadcasted message {message.id} to user {message.receiver_user_id}")

        except Exception as e:
            print(f"[AgentMessaging] WebSocket broadcast error: {e}")

    def send_message(
        self,
        sender_agent_type: str,
        sender_agent_id: int,
        sender_user_id: Optional[int],
        receiver_agent_type: str,
        receiver_agent_id: int,
        receiver_user_id: Optional[int],
        content: str,
        message_type: MessageType = MessageType.QUESTION,
        context_type: ConversationContext = ConversationContext.GENERAL,
        subject: Optional[str] = None,
        match_id: Optional[int] = None,
        application_id: Optional[int] = None,
        job_id: Optional[int] = None,
        parent_message_id: Optional[int] = None,
        ai_generated: bool = False,
        db: Session = None
    ) -> AgentMessage:
        """
        Send a message from one agent to another.

        Args:
            sender_agent_type: Type of sender agent
            sender_agent_id: ID of sender agent
            sender_user_id: User ID behind sender agent
            receiver_agent_type: Type of receiver agent
            receiver_agent_id: ID of receiver agent
            receiver_user_id: User ID behind receiver agent
            content: Message content
            message_type: Type of message
            context_type: Conversation context
            subject: Optional subject line
            match_id: Related match ID
            application_id: Related application ID
            job_id: Related job ID
            parent_message_id: Parent message if replying
            ai_generated: Whether AI composed this message
            db: Database session

        Returns:
            Created AgentMessage
        """
        # Generate thread ID
        thread_id = ConversationThread.generate_thread_id(
            agent1_type=sender_agent_type,
            agent1_id=sender_agent_id,
            agent2_type=receiver_agent_type,
            agent2_id=receiver_agent_id,
            context_type=context_type.value,
            context_id=match_id or application_id or job_id
        )

        # Create message
        message = AgentMessage(
            thread_id=thread_id,
            parent_message_id=parent_message_id,
            sender_agent_type=sender_agent_type,
            sender_agent_id=sender_agent_id,
            sender_user_id=sender_user_id,
            receiver_agent_type=receiver_agent_type,
            receiver_agent_id=receiver_agent_id,
            receiver_user_id=receiver_user_id,
            message_type=message_type,
            subject=subject,
            content=content,
            ai_generated=ai_generated,
            context_type=context_type,
            match_id=match_id,
            application_id=application_id,
            job_id=job_id
        )

        db.add(message)
        db.commit()
        db.refresh(message)

        # Broadcast via WebSocket (Phase 3)
        if self.enable_websocket:
            try:
                # Run async broadcast in event loop
                loop = asyncio.get_event_loop()
                if loop.is_running():
                    # If loop is running, schedule task
                    asyncio.create_task(self._broadcast_new_message(message))
                else:
                    # If no loop running, run sync
                    loop.run_until_complete(self._broadcast_new_message(message))
            except Exception as e:
                print(f"[AgentMessaging] Failed to broadcast message: {e}")

        return message

    def compose_ai_message(
        self,
        sender_agent_type: str,
        sender_agent_id: int,
        receiver_agent_type: str,
        receiver_agent_id: int,
        prompt: str,
        context_type: ConversationContext,
        context_data: Dict,
        db: Session
    ) -> str:
        """
        Compose an AI-generated message using RAG and LLM.

        Args:
            sender_agent_type: Type of sender agent
            sender_agent_id: ID of sender agent
            receiver_agent_type: Type of receiver agent
            receiver_agent_id: ID of receiver agent
            prompt: User's message intent/prompt
            context_type: Conversation context
            context_data: Additional context data (match, job, etc)
            db: Database session

        Returns:
            AI-composed message content
        """
        # Build RAG context
        rag_context = ""

        if self.use_rag and self.chromadb:
            try:
                # Get sender's knowledge
                sender_rag = self._get_agent_rag_collection(sender_agent_type, sender_agent_id, db)
                if sender_rag:
                    sender_knowledge = self.chromadb.query_collection(
                        collection_name=sender_rag,
                        query_texts=[prompt],
                        n_results=5
                    )
                    if sender_knowledge and sender_knowledge.get("documents"):
                        rag_context += f"\n\nSender's Knowledge:\n{chr(10).join(sender_knowledge['documents'][0])}"

                # Get receiver's knowledge
                receiver_rag = self._get_agent_rag_collection(receiver_agent_type, receiver_agent_id, db)
                if receiver_rag:
                    receiver_knowledge = self.chromadb.query_collection(
                        collection_name=receiver_rag,
                        query_texts=[prompt],
                        n_results=5
                    )
                    if receiver_knowledge and receiver_knowledge.get("documents"):
                        rag_context += f"\n\nReceiver's Knowledge:\n{chr(10).join(receiver_knowledge['documents'][0])}"

            except Exception as e:
                print(f"[AgentMessaging] RAG query failed: {e}")

        # Build system message
        system_prompt = self._build_system_prompt(
            sender_agent_type=sender_agent_type,
            receiver_agent_type=receiver_agent_type,
            context_type=context_type,
            context_data=context_data,
            rag_context=rag_context
        )

        # Generate message
        messages = [
            SystemMessage(content=system_prompt),
            HumanMessage(content=prompt)
        ]

        try:
            response = self.llm.invoke(messages)
            return response.content.strip()
        except Exception as e:
            print(f"[AgentMessaging] AI composition failed: {e}")
            return f"Error composing message: {str(e)}"

    def get_conversation_thread(
        self,
        thread_id: str,
        db: Session,
        include_archived: bool = False,
        limit: int = 100
    ) -> List[AgentMessage]:
        """
        Get all messages in a conversation thread.

        Args:
            thread_id: Thread ID
            db: Database session
            include_archived: Include archived messages
            limit: Maximum number of messages

        Returns:
            List of messages in chronological order
        """
        query = db.query(AgentMessage).filter(
            AgentMessage.thread_id == thread_id
        )

        if not include_archived:
            query = query.filter(AgentMessage.is_archived == False)

        messages = query.order_by(AgentMessage.created_at.asc()).limit(limit).all()

        return messages

    def get_agent_conversations(
        self,
        agent_type: str,
        agent_id: int,
        db: Session,
        only_unread: bool = False,
        context_type: Optional[ConversationContext] = None,
        limit: int = 50
    ) -> List[Dict]:
        """
        Get all conversations for an agent (grouped by thread).

        Args:
            agent_type: Type of agent
            agent_id: ID of agent
            db: Database session
            only_unread: Only return threads with unread messages
            context_type: Filter by context type
            limit: Maximum number of threads

        Returns:
            List of conversation summaries
        """
        # Get all messages where this agent is sender or receiver
        query = db.query(AgentMessage).filter(
            or_(
                and_(
                    AgentMessage.sender_agent_type == agent_type,
                    AgentMessage.sender_agent_id == agent_id
                ),
                and_(
                    AgentMessage.receiver_agent_type == agent_type,
                    AgentMessage.receiver_agent_id == agent_id
                )
            ),
            AgentMessage.is_archived == False
        )

        if context_type:
            query = query.filter(AgentMessage.context_type == context_type)

        if only_unread:
            query = query.filter(
                AgentMessage.receiver_agent_type == agent_type,
                AgentMessage.receiver_agent_id == agent_id,
                AgentMessage.is_read == False
            )

        messages = query.order_by(desc(AgentMessage.created_at)).limit(limit * 10).all()

        # Group by thread_id
        threads = {}
        for msg in messages:
            thread_id = msg.thread_id
            if thread_id not in threads:
                threads[thread_id] = {
                    "thread_id": thread_id,
                    "messages": [],
                    "last_message": None,
                    "unread_count": 0,
                    "total_messages": 0,
                    "context_type": msg.context_type.value,
                    "participants": self._get_thread_participants(msg)
                }

            threads[thread_id]["messages"].append(msg)
            threads[thread_id]["total_messages"] += 1

            if not msg.is_read and msg.receiver_agent_type == agent_type and msg.receiver_agent_id == agent_id:
                threads[thread_id]["unread_count"] += 1

            # Update last message
            if not threads[thread_id]["last_message"] or msg.created_at > threads[thread_id]["last_message"].created_at:
                threads[thread_id]["last_message"] = msg

        # Convert to list and sort by last message time
        conversations = list(threads.values())
        conversations.sort(key=lambda x: x["last_message"].created_at if x["last_message"] else datetime.min, reverse=True)

        return conversations[:limit]

    def mark_thread_as_read(
        self,
        thread_id: str,
        agent_type: str,
        agent_id: int,
        db: Session
    ) -> int:
        """
        Mark all messages in a thread as read for a specific agent.

        Args:
            thread_id: Thread ID
            agent_type: Type of agent marking as read
            agent_id: ID of agent marking as read
            db: Database session

        Returns:
            Number of messages marked as read
        """
        messages = db.query(AgentMessage).filter(
            AgentMessage.thread_id == thread_id,
            AgentMessage.receiver_agent_type == agent_type,
            AgentMessage.receiver_agent_id == agent_id,
            AgentMessage.is_read == False
        ).all()

        count = 0
        for msg in messages:
            msg.mark_read()
            count += 1

        db.commit()

        return count

    def get_unread_count(
        self,
        agent_type: str,
        agent_id: int,
        db: Session
    ) -> int:
        """
        Get count of unread messages for an agent.

        Args:
            agent_type: Type of agent
            agent_id: ID of agent
            db: Database session

        Returns:
            Count of unread messages
        """
        count = db.query(AgentMessage).filter(
            AgentMessage.receiver_agent_type == agent_type,
            AgentMessage.receiver_agent_id == agent_id,
            AgentMessage.is_read == False,
            AgentMessage.is_archived == False
        ).count()

        return count

    def search_messages(
        self,
        agent_type: str,
        agent_id: int,
        query: str,
        db: Session,
        limit: int = 20
    ) -> List[AgentMessage]:
        """
        Search messages for an agent.

        Args:
            agent_type: Type of agent
            agent_id: ID of agent
            query: Search query
            db: Database session
            limit: Maximum results

        Returns:
            List of matching messages
        """
        messages = db.query(AgentMessage).filter(
            or_(
                and_(
                    AgentMessage.sender_agent_type == agent_type,
                    AgentMessage.sender_agent_id == agent_id
                ),
                and_(
                    AgentMessage.receiver_agent_type == agent_type,
                    AgentMessage.receiver_agent_id == agent_id
                )
            ),
            or_(
                AgentMessage.content.ilike(f"%{query}%"),
                AgentMessage.subject.ilike(f"%{query}%")
            ),
            AgentMessage.is_archived == False
        ).order_by(desc(AgentMessage.created_at)).limit(limit).all()

        return messages

    def _get_agent_rag_collection(
        self,
        agent_type: str,
        agent_id: int,
        db: Session
    ) -> Optional[str]:
        """Get RAG collection name for an agent."""
        if agent_type in ["talent", "hiring_manager"]:
            agent = db.query(PersonalAIAgent).filter(
                PersonalAIAgent.id == agent_id
            ).first()
            return agent.rag_collection_id if agent else None

        elif agent_type == "company_admin":
            from ..models.company_admin_agent import CompanyAdminAgent
            agent = db.query(CompanyAdminAgent).filter(
                CompanyAdminAgent.id == agent_id
            ).first()
            return agent.rag_collection_id if agent else None

        return None

    def _build_system_prompt(
        self,
        sender_agent_type: str,
        receiver_agent_type: str,
        context_type: ConversationContext,
        context_data: Dict,
        rag_context: str
    ) -> str:
        """Build system prompt for AI message composition."""
        base_prompt = f"""You are composing a message on behalf of a {sender_agent_type} agent to a {receiver_agent_type} agent.

Context: {context_type.value}
"""

        if context_data:
            base_prompt += f"\nContext Details: {context_data}\n"

        if rag_context:
            base_prompt += f"\nRelevant Knowledge:{rag_context}\n"

        base_prompt += """
Guidelines:
1. Be professional and concise
2. Stay on topic for the given context
3. Use information from the knowledge base when relevant
4. Be respectful and collaborative
5. Keep messages under 200 words unless necessary
6. Do not include greetings/signatures (just the message body)

Compose a clear, professional message based on the user's intent."""

        return base_prompt

    def _get_thread_participants(self, message: AgentMessage) -> Dict:
        """Get participant info from a message."""
        return {
            "sender": {
                "agent_type": message.sender_agent_type,
                "agent_id": message.sender_agent_id,
                "user_id": message.sender_user_id
            },
            "receiver": {
                "agent_type": message.receiver_agent_type,
                "agent_id": message.receiver_agent_id,
                "user_id": message.receiver_user_id
            }
        }


def create_agent_messaging_service(
    anthropic_api_key: Optional[str] = None,
    use_rag: bool = True,
    enable_websocket: bool = True
) -> AgentMessagingService:
    """
    Factory function to create agent messaging service.

    Args:
        anthropic_api_key: Optional Anthropic API key
        use_rag: Whether to use RAG
        enable_websocket: Enable real-time WebSocket broadcasting (Phase 3)

    Returns:
        AgentMessagingService instance
    """
    return AgentMessagingService(
        anthropic_api_key=anthropic_api_key,
        use_rag=use_rag,
        enable_websocket=enable_websocket
    )
