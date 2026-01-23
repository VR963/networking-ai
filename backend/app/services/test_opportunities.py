import json
from typing import Optional

import anthropic

from app.config import ANTHROPIC_API_KEY
from app.database import get_db


class TestOpportunities:
    """Generates and manages test opportunities for calibrating agent understanding.

    Flow:
    1. After onboarding, present 3 deliberately imperfect opportunities
    2. User rejects -> AI asks "What doesn't feel right?" -> Store hidden criteria
    3. Agent learns both spoken AND unspoken preferences from rejection patterns
    """

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

    async def generate_test_opportunities(self, user_id: str) -> list[dict]:
        profile = await self._get_user_profile(user_id)
        if not profile:
            return []

        opportunities = await self._create_calibration_set(profile)
        if opportunities:
            await self._store_opportunities(user_id, opportunities)
        return opportunities

    async def _get_user_profile(self, user_id: str) -> Optional[dict]:
        result = (
            self.supabase_client.table("cv2_profiles")
            .select("*")
            .eq("user_id", user_id)
            .execute()
        )
        if result.data:
            return result.data[0]
        return None

    async def _create_calibration_set(self, profile: dict) -> list[dict]:
        profile_text = json.dumps(profile, indent=2)

        response = self.anthropic_client.messages.create(
            model="claude-sonnet-4-20250514",
            max_tokens=2000,
            messages=[
                {
                    "role": "user",
                    "content": (
                        "Based on this professional profile, generate 3 test job opportunities. "
                        "Each should be deliberately imperfect in different ways to reveal "
                        "the user's hidden preferences through their rejection reasons.\n\n"
                        "Opportunity 1: Good role match but culture mismatch\n"
                        "Opportunity 2: Good culture but slight role stretch\n"
                        "Opportunity 3: Perfect on paper but something subtle is off\n\n"
                        "Return a JSON array of 3 objects, each with:\n"
                        "- title: job title\n"
                        "- company: fictional company name\n"
                        "- description: 2-3 sentence description\n"
                        "- salary_range: salary range string\n"
                        "- deliberate_gap: what's intentionally imperfect (hidden from user)\n"
                        "- expected_rejection_reason: what we expect them to say\n\n"
                        f"Profile:\n{profile_text}"
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
            return []

    async def _store_opportunities(self, user_id: str, opportunities: list[dict]) -> None:
        import uuid

        for i, opp in enumerate(opportunities):
            record = {
                "id": str(uuid.uuid4()),
                "user_id": user_id,
                "opportunity_index": i,
                "opportunity_data": opp,
                "status": "pending",
            }
            self.supabase_client.table("cv2_test_opportunities").insert(record).execute()

    async def record_response(
        self, user_id: str, opportunity_index: int, accepted: bool, rejection_reason: Optional[str] = None
    ) -> dict:
        result = (
            self.supabase_client.table("cv2_test_opportunities")
            .select("*")
            .eq("user_id", user_id)
            .eq("opportunity_index", opportunity_index)
            .execute()
        )
        if not result.data:
            return {"error": "Opportunity not found"}

        opportunity = result.data[0]

        update = {
            "status": "accepted" if accepted else "rejected",
            "user_response": rejection_reason or "accepted",
        }
        self.supabase_client.table("cv2_test_opportunities").update(update).eq(
            "id", opportunity["id"]
        ).execute()

        if not accepted and rejection_reason:
            hidden_criteria = await self._extract_hidden_criteria(
                opportunity["opportunity_data"], rejection_reason
            )
            if hidden_criteria:
                await self._store_hidden_criteria(user_id, hidden_criteria)
            return {"learned": hidden_criteria}

        return {"status": "recorded"}

    async def _extract_hidden_criteria(self, opportunity: dict, rejection_reason: str) -> Optional[dict]:
        response = self.anthropic_client.messages.create(
            model="claude-sonnet-4-20250514",
            max_tokens=500,
            messages=[
                {
                    "role": "user",
                    "content": (
                        "A user rejected this opportunity with this reason. "
                        "What hidden criteria does this reveal?\n\n"
                        f"Opportunity: {json.dumps(opportunity)}\n"
                        f"Rejection reason: {rejection_reason}\n\n"
                        "Return JSON with:\n"
                        "- explicit_criteria: what they directly said\n"
                        "- inferred_criteria: what this implies about their preferences\n"
                        "- values_revealed: deeper values this suggests"
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

    async def _store_hidden_criteria(self, user_id: str, criteria: dict) -> None:
        record = {
            "user_id": user_id,
            "patterns": criteria,
            "pattern_type": "hidden_criteria",
        }
        self.supabase_client.table("cv2_collective_patterns").insert(record).execute()

        # Share to collective intelligence network
        try:
            from app.services.collective_intelligence import collective_intelligence

            profile = await self._get_user_profile(user_id)
            industry = (profile or {}).get("industry", "general") or "general"
            await collective_intelligence.share_pattern(user_id, industry, criteria)
        except Exception:
            pass  # Network sharing is non-critical

    async def get_calibration_status(self, user_id: str) -> dict:
        result = (
            self.supabase_client.table("cv2_test_opportunities")
            .select("*")
            .eq("user_id", user_id)
            .execute()
        )
        opportunities = result.data or []
        return {
            "total": len(opportunities),
            "pending": sum(1 for o in opportunities if o["status"] == "pending"),
            "accepted": sum(1 for o in opportunities if o["status"] == "accepted"),
            "rejected": sum(1 for o in opportunities if o["status"] == "rejected"),
            "calibration_complete": all(o["status"] != "pending" for o in opportunities) and len(opportunities) > 0,
        }


test_opportunities = TestOpportunities()
