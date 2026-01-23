"""Network Learning Service - DSPy-style cross-agent knowledge sharing.

Learns from:
- Successful negotiations (what patterns lead to good matches)
- Human rejections (what the agents got wrong)
- Industry trends (what's changing in each sector)
- Agent behavior (which agent strategies work best)

Knowledge flows:
1. Individual agent learns from its own negotiations
2. Industry-level patterns emerge from aggregating agent learnings
3. Network-level insights feed back into all agents
4. Master AI uses collective intelligence for governance decisions

Learning loop:
  negotiate → outcome → extract_pattern → score → share → synthesize → improve
"""

import json
from typing import Optional

import anthropic

from app.config import ANTHROPIC_API_KEY
from app.database import get_db


LEARNING_SCORE_THRESHOLD = 7.0  # Minimum quality to share a pattern


def _get_supabase():
    return get_db()


class NetworkLearning:
    """Manages cross-agent learning and knowledge sharing."""

    def __init__(self):
        self._anthropic = None

    @property
    def client(self):
        if self._anthropic is None:
            self._anthropic = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)
        return self._anthropic

    async def learn_from_negotiation(
        self,
        talent_agent: dict,
        hm_agent: dict,
        negotiation_result: dict,
    ) -> Optional[dict]:
        """Extract learnings from a completed negotiation.

        Analyzes what worked/didn't work and creates shareable patterns.
        """
        if not ANTHROPIC_API_KEY:
            return None

        outcome = negotiation_result.get("status", "unknown")
        score = negotiation_result.get("final_score", 0)
        rounds = negotiation_result.get("rounds", [])

        talent_industry = talent_agent.get("industry", "general")
        hm_industry = hm_agent.get("industry", "general")

        prompt = f"""Analyze this agent-to-agent negotiation and extract learning patterns.

OUTCOME: {outcome} (score: {score})
ROUNDS COMPLETED: {len(rounds)}
TALENT INDUSTRY: {talent_industry}
HM INDUSTRY: {hm_industry}

ROUND DETAILS:
{json.dumps(rounds, indent=2)[:2000]}

Extract patterns that would help OTHER agents in the same industry negotiate better.
DO NOT include any personally identifiable information.

Return JSON:
{{
    "pattern_type": "success_pattern" or "failure_pattern" or "insight",
    "industry": "{talent_industry}",
    "learning": {{
        "what_worked": ["generalizable insights about what led to match/rejection"],
        "what_to_avoid": ["patterns that led to failure"],
        "industry_signal": "what this reveals about the industry",
        "negotiation_tip": "advice for agents in similar negotiations"
    }},
    "quality_score": 1-10 (how useful is this learning for other agents),
    "applicable_to": "talent" or "hm" or "both"
}}
Return ONLY JSON."""

        try:
            response = self.client.messages.create(
                model="claude-sonnet-4-20250514",
                max_tokens=600,
                messages=[{"role": "user", "content": prompt}],
            )
            text = response.content[0].text.strip()
            if text.startswith("```"):
                text = text.split("\n", 1)[1].rsplit("```", 1)[0]
            pattern = json.loads(text)

            # Only share if quality is high enough
            if pattern.get("quality_score", 0) >= LEARNING_SCORE_THRESHOLD:
                await self._store_network_pattern(pattern, talent_industry)

            return pattern
        except Exception:
            return None

    async def learn_from_rejection(
        self,
        agent_id: str,
        match_id: str,
        feedback: str,
    ) -> Optional[dict]:
        """Learn from a human rejecting a match their agent found.

        This is the most valuable learning signal - it means the agent
        made a decision the human disagrees with.
        """
        if not ANTHROPIC_API_KEY:
            return None

        client = _get_supabase()
        if not client:
            return None

        # Get match details
        match = (
            client.table("cv2_a2a_matches")
            .select("*")
            .eq("id", match_id)
            .execute()
        )
        if not match.data:
            return None

        match_data = match.data[0]

        # Get agent details
        agent = (
            client.table("cv2_agents")
            .select("industry, agent_type, profile")
            .eq("id", agent_id)
            .execute()
        )
        agent_data = agent.data[0] if agent.data else {}

        prompt = f"""A human rejected a match that their AI agent found for them.

MATCH SCORE: {match_data.get('score', 0)}
MATCH LEVEL: {match_data.get('match_level', '')}
AGENT TYPE: {agent_data.get('agent_type', 'unknown')}
INDUSTRY: {agent_data.get('industry', 'general')}

HUMAN'S FEEDBACK: "{feedback}"

MATCH SYNOPSIS THAT WAS PRESENTED:
{json.dumps(match_data.get('candidate_synopsis', match_data.get('hiring_manager_synopsis', {})))}

Analyze why the agent got it wrong and what it should learn:

Return JSON:
{{
    "root_cause": "why the agent's judgment was wrong",
    "missed_signal": "what the agent should have caught from the profile",
    "correction": "how to adjust matching for this user going forward",
    "generalizable_lesson": "what other agents in this industry can learn",
    "severity": "minor/moderate/major (how bad was the mismatch)"
}}
Return ONLY JSON."""

        try:
            response = self.client.messages.create(
                model="claude-sonnet-4-20250514",
                max_tokens=500,
                messages=[{"role": "user", "content": prompt}],
            )
            text = response.content[0].text.strip()
            if text.startswith("```"):
                text = text.split("\n", 1)[1].rsplit("```", 1)[0]
            learning = json.loads(text)

            # Store as agent-specific learning
            await self._store_agent_learning(agent_id, learning)

            # If generalizable, share to network
            if learning.get("severity") in ["moderate", "major"]:
                industry = agent_data.get("industry", "general")
                await self._store_network_pattern({
                    "pattern_type": "failure_pattern",
                    "industry": industry,
                    "learning": {
                        "what_to_avoid": [learning.get("generalizable_lesson", "")],
                        "root_cause": learning.get("root_cause", ""),
                    },
                    "quality_score": 8,
                    "applicable_to": agent_data.get("agent_type", "both"),
                }, industry)

            return learning
        except Exception:
            return None

    async def get_industry_intelligence(self, industry: str) -> dict:
        """Synthesize all learnings for an industry into actionable intelligence.

        Called by agents before negotiations to improve their performance.
        """
        client = _get_supabase()
        if not client:
            return {"patterns": [], "insights": []}

        # Get recent patterns for this industry
        patterns = (
            client.table("cv2_network_patterns")
            .select("pattern, pattern_type, quality_score")
            .eq("industry", industry)
            .order("created_at", desc=True)
            .limit(30)
            .execute()
        )

        if not patterns.data:
            return {"patterns": [], "insights": []}

        success_patterns = [
            p["pattern"] for p in patterns.data
            if p.get("pattern_type") == "success_pattern"
        ]
        failure_patterns = [
            p["pattern"] for p in patterns.data
            if p.get("pattern_type") == "failure_pattern"
        ]

        return {
            "industry": industry,
            "total_patterns": len(patterns.data),
            "success_patterns": success_patterns[:10],
            "failure_patterns": failure_patterns[:10],
            "what_works": [
                item
                for p in success_patterns[:5]
                for item in (p.get("what_worked", []) if isinstance(p, dict) else [])
            ][:10],
            "what_to_avoid": [
                item
                for p in failure_patterns[:5]
                for item in (p.get("what_to_avoid", []) if isinstance(p, dict) else [])
            ][:10],
        }

    async def synthesize_network_intelligence(self) -> dict:
        """Create a network-wide intelligence report.

        Used by Master AI for governance decisions and network health monitoring.
        """
        if not ANTHROPIC_API_KEY:
            return {"status": "api_key_required"}

        client = _get_supabase()
        if not client:
            return {"status": "db_required"}

        # Get all recent patterns across industries
        all_patterns = (
            client.table("cv2_network_patterns")
            .select("industry, pattern_type, pattern, quality_score")
            .order("created_at", desc=True)
            .limit(50)
            .execute()
        )

        if not all_patterns.data:
            return {"status": "no_data", "patterns_count": 0}

        # Get network stats
        agents = (
            client.table("cv2_agents")
            .select("agent_type, industry, reputation, active")
            .eq("active", True)
            .execute()
        )

        matches = (
            client.table("cv2_a2a_matches")
            .select("score, match_level, status")
            .order("created_at", desc=True)
            .limit(50)
            .execute()
        )

        prompt = f"""Synthesize network-wide intelligence from these patterns and stats.

NETWORK STATS:
- Active agents: {len(agents.data or [])}
- Recent matches: {len(matches.data or [])}
- Average match score: {sum(m.get('score', 0) for m in (matches.data or [])) / max(len(matches.data or []), 1):.0f}

PATTERNS BY INDUSTRY:
{json.dumps(all_patterns.data[:30], indent=2)[:3000]}

Create a network intelligence report:
Return JSON:
{{
    "network_health": "healthy/growing/stagnant/declining",
    "top_industries": ["most active industries"],
    "emerging_trends": ["cross-industry patterns"],
    "match_quality_trend": "improving/stable/declining",
    "recommendations": ["actions for Master AI to take"],
    "agent_performance": {{
        "top_performers": "pattern in high-reputation agents",
        "common_failures": "pattern in low-reputation agents"
    }},
    "network_gaps": ["unserved areas or imbalances"]
}}
Return ONLY JSON."""

        try:
            response = self.client.messages.create(
                model="claude-sonnet-4-20250514",
                max_tokens=800,
                messages=[{"role": "user", "content": prompt}],
            )
            text = response.content[0].text.strip()
            if text.startswith("```"):
                text = text.split("\n", 1)[1].rsplit("```", 1)[0]
            return json.loads(text)
        except Exception:
            return {"status": "synthesis_failed"}

    async def get_agent_learnings(self, agent_id: str) -> list[dict]:
        """Get all learnings stored for a specific agent."""
        client = _get_supabase()
        if not client:
            return []

        result = (
            client.table("cv2_agent_learnings")
            .select("learning, created_at")
            .eq("agent_id", agent_id)
            .order("created_at", desc=True)
            .limit(20)
            .execute()
        )
        return result.data or []

    async def _store_network_pattern(self, pattern: dict, industry: str) -> None:
        """Store a learning pattern in the network patterns table."""
        client = _get_supabase()
        if not client:
            return

        try:
            client.table("cv2_network_patterns").insert({
                "industry": industry,
                "pattern_type": pattern.get("pattern_type", "insight"),
                "pattern": pattern.get("learning", pattern),
                "quality_score": pattern.get("quality_score", 5),
                "applicable_to": pattern.get("applicable_to", "both"),
            }).execute()
        except Exception:
            pass

    async def _store_agent_learning(self, agent_id: str, learning: dict) -> None:
        """Store a learning specific to one agent."""
        client = _get_supabase()
        if not client:
            return

        try:
            client.table("cv2_agent_learnings").insert({
                "agent_id": agent_id,
                "learning": learning,
            }).execute()
        except Exception:
            pass


network_learning = NetworkLearning()
