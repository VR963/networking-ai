import json
from typing import Optional

import anthropic

from app.config import ANTHROPIC_API_KEY
from app.database import get_db


class DSPyLearning:
    """Learns patterns from high-quality conversations to improve agent responses."""

    def __init__(self):
        self._anthropic = None

    @property
    def anthropic_client(self):
        if self._anthropic is None:
            self._anthropic = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)
        return self._anthropic

    @property
    def supabase_client(self):
        return get_db()

    async def learn_from_conversation(self, conversation_id: str) -> Optional[dict]:
        try:
            result = self.supabase_client.rpc("get_conversation", {"p_id": conversation_id}).execute()
        except Exception:
            result = (
                self.supabase_client.table("cv2_conversations")
                .select("*")
                .eq("id", conversation_id)
                .execute()
            )
        if not result.data:
            return None

        conversation = result.data[0]
        messages = conversation["messages"]
        user_id = conversation["user_id"]

        patterns = await self._extract_patterns(messages)
        if patterns:
            await self._store_patterns(user_id, conversation_id, patterns)
            # Share to collective intelligence network
            await self._share_to_network(user_id, patterns)

        return patterns

    async def _share_to_network(self, user_id: str, patterns: dict) -> None:
        """Share learned patterns with the collective intelligence network."""
        from app.services.collective_intelligence import collective_intelligence

        try:
            # Determine user's industry from profile
            profile_result = (
                self.supabase_client.table("cv2_profiles")
                .select("industry")
                .eq("user_id", user_id)
                .execute()
            )
            industry = "general"
            if profile_result.data:
                industry = profile_result.data[0].get("industry", "general") or "general"

            await collective_intelligence.share_pattern(user_id, industry, patterns)
        except Exception:
            pass  # Network sharing is non-critical

    async def _extract_patterns(self, messages: list[dict]) -> Optional[dict]:
        conversation_text = "\n".join(
            f"{m.get('role', 'unknown')}: {m.get('content', '')}" for m in messages
        )

        response = self.anthropic_client.messages.create(
            model="claude-sonnet-4-20250514",
            max_tokens=1000,
            messages=[
                {
                    "role": "user",
                    "content": (
                        "Analyze this conversation and extract key patterns about the user. "
                        "Return a JSON object with these fields:\n"
                        "- values: list of core professional values revealed\n"
                        "- goals: list of career goals mentioned\n"
                        "- hidden_criteria: list of unspoken preferences inferred\n"
                        "- communication_style: brief description of how they communicate\n"
                        "- key_insights: list of important observations\n\n"
                        f"Conversation:\n{conversation_text}"
                    ),
                }
            ],
        )

        try:
            text = response.content[0].text.strip()
            if text.startswith("```"):
                text = text.split("\n", 1)[1].rsplit("```", 1)[0]
            return json.loads(text)
        except (json.JSONDecodeError, IndexError):
            return None

    async def _store_patterns(
        self, user_id: str, conversation_id: str, patterns: dict
    ) -> None:
        try:
            self.supabase_client.rpc("insert_cv2_pattern", {
                "p_user_id": user_id,
                "p_conversation_id": conversation_id,
                "p_patterns": patterns,
                "p_pattern_type": "conversation_learning",
            }).execute()
        except Exception:
            record = {
                "user_id": user_id,
                "conversation_id": conversation_id,
                "patterns": patterns,
                "pattern_type": "conversation_learning",
            }
            self.supabase_client.table("cv2_collective_patterns").insert(record).execute()

    async def get_user_patterns(self, user_id: str) -> list[dict]:
        try:
            result = self.supabase_client.rpc("get_user_patterns", {"p_user_id": user_id}).execute()
        except Exception:
            result = (
                self.supabase_client.table("cv2_collective_patterns")
                .select("patterns")
                .eq("user_id", user_id)
                .order("created_at", desc=True)
                .execute()
            )
        return [r["patterns"] for r in result.data] if result.data else []


dspy_learning = DSPyLearning()
