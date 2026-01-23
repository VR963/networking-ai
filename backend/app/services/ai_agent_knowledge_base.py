from typing import Optional

from supabase import create_client

from app.config import SUPABASE_URL, SUPABASE_SERVICE_KEY


class AIAgentKnowledgeBase:
    """Domain knowledge store for AI agents.

    Provides pre-loaded industry expertise so agents know the domain
    before meeting users.
    """

    def __init__(self):
        self._supabase = None

    @property
    def supabase_client(self):
        if self._supabase is None:
            self._supabase = create_client(SUPABASE_URL, SUPABASE_SERVICE_KEY)
        return self._supabase

    async def get_agent_knowledge(self, agent_id: str) -> Optional[dict]:
        result = (
            self.supabase_client.table("cv2_agents")
            .select("*")
            .eq("id", agent_id)
            .execute()
        )
        if result.data:
            return result.data[0]
        return None

    async def get_industry_context(self, industry: str) -> dict:
        from app.services.industry_knowledge_modules import industry_knowledge

        return industry_knowledge.get_module(industry)

    async def build_agent_context(self, user_id: str) -> dict:
        profile_result = (
            self.supabase_client.table("cv2_profiles")
            .select("*")
            .eq("user_id", user_id)
            .execute()
        )
        if not profile_result.data:
            return {"industry": "general", "knowledge": {}}

        profile = profile_result.data[0]
        industry = profile.get("industry", "general")
        industry_context = await self.get_industry_context(industry)

        return {
            "industry": industry,
            "knowledge": industry_context,
            "profile_summary": profile.get("summary", ""),
        }


ai_agent_knowledge_base = AIAgentKnowledgeBase()
