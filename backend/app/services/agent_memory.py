"""Agent Memory & Reputation System - Persistent state for each agent in the network.

Each agent accumulates:
- Negotiation history (who, outcome, score)
- Rejection patterns (what they keep saying no to)
- Success signals (when their human accepts/rejects a presented match)
- Reputation score (how reliable their matches are)
- Learning log (insights gained from each interaction)

Reputation formula:
  reputation = (successful_matches * 10 - failed_matches * 5 + total_negotiations * 0.5)
             / max(total_negotiations, 1) * 10

Higher reputation agents get priority in network scheduling.
"""

import json
from typing import Optional
from datetime import datetime

from app.database import get_db, get_cache, invalidate_agent


def _get_supabase():
    return get_db()


class AgentMemory:
    """Manages persistent memory and reputation for agents."""

    async def record_negotiation(
        self,
        agent_id: str,
        partner_agent_id: str,
        outcome: str,
        score: int,
        round_reached: int,
        insights: Optional[dict] = None,
    ) -> None:
        """Record a negotiation result in agent memory.

        Args:
            agent_id: This agent's ID
            partner_agent_id: The other agent's ID
            outcome: "matched", "rejected", "partial"
            score: Final negotiation score
            round_reached: Which round was reached (1, 2, or 3)
            insights: What was learned from this negotiation
        """
        client = _get_supabase()
        if not client:
            return

        record = {
            "agent_id": agent_id,
            "partner_agent_id": partner_agent_id,
            "outcome": outcome,
            "score": score,
            "round_reached": round_reached,
            "insights": insights or {},
        }
        client.table("cv2_agent_memory").insert(record).execute()

        # Update agent reputation
        await self._update_reputation(agent_id)

    async def record_human_feedback(
        self,
        agent_id: str,
        match_id: str,
        accepted: bool,
        feedback: Optional[str] = None,
    ) -> None:
        """Record when a human accepts or rejects a match their agent found.

        This is the strongest learning signal - it tells us if the agent
        is making good decisions on behalf of the human.
        """
        client = _get_supabase()
        if not client:
            return

        record = {
            "agent_id": agent_id,
            "match_id": match_id,
            "accepted": accepted,
            "feedback": feedback or "",
            "signal_type": "human_feedback",
        }
        client.table("cv2_agent_memory").insert(record).execute()

        # Update reputation based on human feedback
        await self._update_reputation(agent_id)

        # If rejected, learn from it
        if not accepted and feedback:
            await self._learn_from_rejection(agent_id, match_id, feedback)

    async def get_agent_history(self, agent_id: str) -> dict:
        """Get an agent's complete negotiation history and stats."""
        client = _get_supabase()
        if not client:
            return {"negotiations": 0, "matches": 0, "reputation": 50}

        history = (
            client.table("cv2_agent_memory")
            .select("*")
            .eq("agent_id", agent_id)
            .order("created_at", desc=True)
            .limit(100)
            .execute()
        )

        records = history.data or []

        negotiations = [r for r in records if r.get("outcome")]
        feedback = [r for r in records if r.get("signal_type") == "human_feedback"]

        matched = sum(1 for n in negotiations if n.get("outcome") == "matched")
        rejected = sum(1 for n in negotiations if n.get("outcome") == "rejected")
        human_accepted = sum(1 for f in feedback if f.get("accepted"))
        human_rejected = sum(1 for f in feedback if not f.get("accepted"))

        return {
            "total_negotiations": len(negotiations),
            "matched": matched,
            "rejected_by_agent": rejected,
            "human_accepted": human_accepted,
            "human_rejected": human_rejected,
            "avg_score": (
                sum(n.get("score", 0) for n in negotiations) / max(len(negotiations), 1)
            ),
            "reputation": await self.get_reputation(agent_id),
            "recent_partners": [n.get("partner_agent_id") for n in negotiations[:5]],
        }

    async def get_reputation(self, agent_id: str) -> int:
        """Get an agent's reputation score (0-100)."""
        cache = get_cache()
        cached = cache.get(f"agent:rep:{agent_id}")
        if cached is not None:
            return cached

        client = _get_supabase()
        if not client:
            return 50

        # Get from agents table
        agent = (
            client.table("cv2_agents")
            .select("reputation")
            .eq("id", agent_id)
            .execute()
        )
        rep = 50
        if agent.data and agent.data[0].get("reputation") is not None:
            rep = agent.data[0]["reputation"]
        cache.set(f"agent:rep:{agent_id}", rep)
        return rep

    async def get_rejection_patterns(self, agent_id: str) -> list[str]:
        """Get patterns from what this agent's human keeps rejecting.

        Used to improve future matching - avoid similar proposals.
        """
        client = _get_supabase()
        if not client:
            return []

        rejections = (
            client.table("cv2_agent_memory")
            .select("feedback, insights")
            .eq("agent_id", agent_id)
            .eq("signal_type", "human_feedback")
            .eq("accepted", False)
            .order("created_at", desc=True)
            .limit(10)
            .execute()
        )

        patterns = []
        for r in (rejections.data or []):
            if r.get("feedback"):
                patterns.append(r["feedback"])
            if r.get("insights", {}).get("rejection_pattern"):
                patterns.append(r["insights"]["rejection_pattern"])

        return patterns

    async def get_high_reputation_agents(self, agent_type: str = "talent", limit: int = 20) -> list[dict]:
        """Get agents with highest reputation for priority scheduling."""
        client = _get_supabase()
        if not client:
            return []

        result = (
            client.table("cv2_agents")
            .select("*")
            .eq("agent_type", agent_type)
            .eq("active", True)
            .order("reputation", desc=True)
            .limit(limit)
            .execute()
        )
        return result.data or []

    async def _update_reputation(self, agent_id: str) -> None:
        """Recalculate and store agent reputation."""
        client = _get_supabase()
        if not client:
            return

        history = (
            client.table("cv2_agent_memory")
            .select("outcome, accepted, signal_type")
            .eq("agent_id", agent_id)
            .execute()
        )

        records = history.data or []
        if not records:
            return

        negotiations = [r for r in records if r.get("outcome")]
        feedback = [r for r in records if r.get("signal_type") == "human_feedback"]

        matched = sum(1 for n in negotiations if n.get("outcome") == "matched")
        human_accepted = sum(1 for f in feedback if f.get("accepted"))
        human_rejected = sum(1 for f in feedback if not f.get("accepted"))

        total = max(len(negotiations), 1)

        # Reputation formula:
        # Base: 50
        # +10 per successful match that human accepted
        # +5 per match found
        # -15 per match that human rejected (agent made bad decision)
        # Normalized to 0-100
        raw_score = 50 + (human_accepted * 10) + (matched * 5) - (human_rejected * 15)
        reputation = max(0, min(100, raw_score))

        try:
            client.table("cv2_agents").update({"reputation": reputation}).eq("id", agent_id).execute()
            invalidate_agent(agent_id)
        except Exception:
            pass

    async def _learn_from_rejection(self, agent_id: str, match_id: str, feedback: str) -> None:
        """Analyze a human rejection to improve future matching.

        Updates the agent's profile with learned rejection patterns.
        """
        client = _get_supabase()
        if not client:
            return

        # Get the match details
        match_data = (
            client.table("cv2_a2a_matches")
            .select("*")
            .eq("id", match_id)
            .execute()
        )

        if not match_data.data:
            return

        match = match_data.data[0]

        # Store rejection insight
        insight = {
            "rejection_pattern": feedback,
            "match_score_was": match.get("score", 0),
            "match_level_was": match.get("match_level", ""),
        }

        # Update the memory record with insight
        client.table("cv2_agent_memory").update({
            "insights": insight,
        }).eq("agent_id", agent_id).eq("match_id", match_id).eq("signal_type", "human_feedback").execute()


agent_memory = AgentMemory()
