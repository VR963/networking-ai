from typing import Optional

import anthropic

from app.config import ANTHROPIC_API_KEY
from app.database import get_db


class CollectiveIntelligence:
    """Network-level learning across all agents in the same industry."""

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

    async def share_pattern(self, user_id: str, industry: str, pattern: dict) -> None:
        try:
            record = {
                "user_id": user_id,
                "industry": industry,
                "patterns": pattern,
                "pattern_type": "collective_shared",
            }
            self.supabase_client.table("cv2_collective_patterns").insert(record).execute()
        except Exception:
            # Fallback without industry column if it doesn't exist yet
            record = {
                "user_id": user_id,
                "patterns": pattern,
                "pattern_type": "collective_shared",
            }
            self.supabase_client.table("cv2_collective_patterns").insert(record).execute()

    async def get_industry_patterns(self, industry: str) -> list[dict]:
        result = (
            self.supabase_client.table("cv2_collective_patterns")
            .select("patterns")
            .eq("industry", industry)
            .eq("pattern_type", "collective_shared")
            .order("created_at", desc=True)
            .limit(50)
            .execute()
        )
        return [r["patterns"] for r in result.data] if result.data else []

    async def synthesize_industry_insights(self, industry: str) -> Optional[dict]:
        patterns = await self.get_industry_patterns(industry)
        if not patterns:
            return None

        import json

        patterns_text = json.dumps(patterns, indent=2)

        response = self.anthropic_client.messages.create(
            model="claude-sonnet-4-20250514",
            max_tokens=1000,
            messages=[
                {
                    "role": "user",
                    "content": (
                        f"Analyze these patterns from {industry} professionals and "
                        "synthesize the key trends. Return JSON with:\n"
                        "- common_values: shared values across professionals\n"
                        "- emerging_trends: career trends in this industry\n"
                        "- hidden_preferences: common unspoken criteria\n"
                        "- advice_patterns: what successful matches have in common\n\n"
                        f"Patterns:\n{patterns_text}"
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


collective_intelligence = CollectiveIntelligence()
