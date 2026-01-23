from typing import Optional

import anthropic

from app.config import ANTHROPIC_API_KEY, SUPABASE_URL, SUPABASE_SERVICE_KEY
from supabase import create_client


class QualityAnalyzer:
    def __init__(self):
        self._anthropic = None
        self._supabase = None

    @property
    def anthropic_client(self):
        if self._anthropic is None:
            self._anthropic = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)
        return self._anthropic

    @property
    def supabase_client(self):
        if self._supabase is None:
            self._supabase = create_client(SUPABASE_URL, SUPABASE_SERVICE_KEY)
        return self._supabase

    async def analyze(self, conversation_id: str) -> float:
        result = (
            self.supabase_client.table("cv2_conversations")
            .select("messages")
            .eq("id", conversation_id)
            .execute()
        )
        if not result.data:
            return 0.0

        messages = result.data[0]["messages"]
        return await self._score_conversation(messages)

    async def _score_conversation(self, messages: list[dict]) -> float:
        conversation_text = "\n".join(
            f"{m.get('role', 'unknown')}: {m.get('content', '')}" for m in messages
        )

        response = self.anthropic_client.messages.create(
            model="claude-sonnet-4-20250514",
            max_tokens=200,
            messages=[
                {
                    "role": "user",
                    "content": (
                        "Rate this conversation on a scale of 1-10 for quality of "
                        "information revealed about the user's professional profile, "
                        "values, goals, and hidden preferences. "
                        "Respond with ONLY a number.\n\n"
                        f"Conversation:\n{conversation_text}"
                    ),
                }
            ],
        )

        try:
            score = float(response.content[0].text.strip())
            return min(max(score, 0.0), 10.0)
        except (ValueError, IndexError):
            return 5.0

    async def analyze_with_feedback(
        self, conversation_id: str
    ) -> dict:
        score = await self.analyze(conversation_id)
        feedback = {
            "score": score,
            "meets_threshold": score >= 7.0,
            "recommendation": (
                "High quality - suitable for learning"
                if score >= 7.0
                else "Needs more depth before learning extraction"
            ),
        }
        return feedback


quality_analyzer = QualityAnalyzer()
