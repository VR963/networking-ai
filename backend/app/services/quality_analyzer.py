from typing import Optional

import anthropic

from app.config import ANTHROPIC_API_KEY
from app.database import get_db


class QualityAnalyzer:
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

    async def analyze(self, conversation_id: str) -> float:
        try:
            result = self.supabase_client.rpc("get_conversation", {"p_id": conversation_id}).execute()
        except Exception:
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
            max_tokens=300,
            messages=[
                {
                    "role": "user",
                    "content": (
                        "Rate this conversation on a scale of 1-10 based on the DEPTH "
                        "and SUBSTANCE of information the USER revealed. Score each "
                        "of these 6 categories (0-10) then average them:\n\n"
                        "1. Career Motivations — Did the user reveal WHY they work, "
                        "real reasons for career moves, what drives them?\n"
                        "2. Achievements — Did the user share specific, verifiable "
                        "accomplishments with details about their actual contribution?\n"
                        "3. Work Style — Did the user describe HOW they prefer to work "
                        "(environment, collaboration, rhythm, communication)?\n"
                        "4. Leadership — Did the user reveal management approach, "
                        "decision-making style, conflict handling?\n"
                        "5. Next Role — Did the user share what they want next, "
                        "dealbreakers, ideal boss/company profile?\n"
                        "6. Values & Culture — Did the user reveal personal values, "
                        "cultural preferences, ethical boundaries, work-life needs?\n\n"
                        "SCORING GUIDE:\n"
                        "- 1-3: Superficial, generic responses with no personal detail\n"
                        "- 4-6: Some substance but still surface-level, missing specifics\n"
                        "- 7-8: Rich detail with specific examples and personal insights\n"
                        "- 9-10: Deep, revealing conversation with behavioral evidence\n\n"
                        "Respond with ONLY a single number (the average score).\n\n"
                        f"Conversation:\n{conversation_text}"
                    ),
                }
            ],
        )

        try:
            raw = response.content[0].text.strip()
            # Extract first number from response
            import re
            match = re.search(r"(\d+\.?\d*)", raw)
            score = float(match.group(1)) if match else 5.0
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
