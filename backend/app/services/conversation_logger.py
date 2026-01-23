import uuid
from datetime import datetime, timezone
from typing import Optional

from supabase import create_client

from app.config import SUPABASE_URL, SUPABASE_SERVICE_KEY


class ConversationLogger:
    def __init__(self):
        self._client = None

    @property
    def client(self):
        if self._client is None:
            self._client = create_client(SUPABASE_URL, SUPABASE_SERVICE_KEY)
        return self._client

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
