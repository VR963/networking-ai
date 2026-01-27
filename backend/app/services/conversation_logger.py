import logging
import uuid
from datetime import datetime, timezone
from typing import Optional

from app.database import get_db

logger = logging.getLogger(__name__)


class ConversationLogger:
    def __init__(self):
        self._embedding_store = None

    @property
    def embedding_store(self):
        if self._embedding_store is None:
            from app.services.embedding_store import embedding_store
            self._embedding_store = embedding_store
        return self._embedding_store

    @property
    def client(self):
        return get_db()

    async def log_conversation(
        self, user_id: str, messages: list[dict], metadata: Optional[dict] = None
    ) -> str:
        conversation_id = str(uuid.uuid4())
        record = {
            "id": conversation_id,
            "user_id": user_id,
            "messages": messages,
            "message_count": len(messages),
            "metadata": metadata or {},
            "created_at": datetime.now(timezone.utc).isoformat(),
        }
        self.client.table("cv2_conversations").insert(record).execute()

        # Index in RAG store for semantic retrieval in future conversations
        try:
            text_content = " ".join(
                m.get("content", "") for m in messages if m.get("content")
            )
            if text_content.strip():
                await self.embedding_store.index_content(
                    content_type="conversation",
                    content_id=conversation_id,
                    text_content=text_content[:5000],
                    user_id=user_id,
                    metadata=metadata or {},
                )
        except Exception as e:
            logger.debug(f"RAG indexing failed for conversation: {e}")

        return conversation_id

    async def get_conversation(self, conversation_id: str) -> Optional[dict]:
        result = (
            self.client.table("cv2_conversations")
            .select("*")
            .eq("id", conversation_id)
            .execute()
        )
        if result.data:
            return result.data[0]
        return None

    async def get_user_conversations(self, user_id: str) -> list[dict]:
        result = (
            self.client.table("cv2_conversations")
            .select("*")
            .eq("user_id", user_id)
            .order("created_at", desc=True)
            .execute()
        )
        return result.data or []


conversation_logger = ConversationLogger()
