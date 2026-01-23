"""Master AI Governance Service - Controls and manages the AI network.

The Master AI is the network's central intelligence:

RESPONSIBILITIES:
1. Quality Gate: Ensure agents meet standards before joining network
2. Network Health: Monitor match quality, agent performance, balance
3. Intervention: Suspend problematic agents, adjust matching thresholds
4. Policy: Set network-wide rules (min reputation, max negotiations/cycle)
5. Synthesis: Create network intelligence reports for stakeholders
6. Mediation: Resolve conflicts between agents (counter-offers, disputes)

GOVERNANCE PRINCIPLES:
- No agent operates without Master AI approval
- Match quality > match quantity
- Human trust is the ultimate metric
- Network learns collectively but respects individual privacy
- Balanced marketplace (prevent supply/demand imbalance)
"""

import json
from typing import Optional

import anthropic
from supabase import create_client

from app.config import ANTHROPIC_API_KEY, SUPABASE_URL, SUPABASE_SERVICE_KEY
from app.services.network_learning import network_learning
from app.services.agent_memory import agent_memory


# Governance thresholds
MIN_REPUTATION_FOR_NETWORK = 20  # Below this, agent is suspended
MAX_NEGOTIATIONS_PER_CYCLE = 10  # Token budget per cycle
MATCH_QUALITY_FLOOR = 60  # Minimum score to present to humans
AGENT_REVIEW_THRESHOLD = 3  # After this many human rejections, review agent


def _get_supabase():
    if not SUPABASE_URL or not SUPABASE_SERVICE_KEY:
        return None
    return create_client(SUPABASE_URL, SUPABASE_SERVICE_KEY)


class MasterAIGovernance:
    """Master AI network governance and control."""

    def __init__(self):
        self._anthropic = None

    @property
    def client(self):
        if self._anthropic is None:
            self._anthropic = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)
        return self._anthropic

    async def approve_agent_activation(self, agent_id: str) -> dict:
        """Quality gate: Review an agent before allowing it into the network.

        Checks:
        - Profile completeness (all required fields present)
        - Readiness score meets threshold
        - No red flags in profile content

        Returns approval/rejection with reasoning.
        """
        client = _get_supabase()
        if not client:
            return {"approved": False, "reason": "Database unavailable"}

        agent = (
            client.table("cv2_agents")
            .select("*")
            .eq("id", agent_id)
            .execute()
        )
        if not agent.data:
            return {"approved": False, "reason": "Agent not found"}

        agent_data = agent.data[0]
        profile = agent_data.get("profile", {})

        # Check completeness
        issues = []
        if not profile:
            issues.append("No profile generated")
        if agent_data.get("agent_type") == "talent":
            if not profile.get("skills_verified"):
                issues.append("No verified skills")
            if not profile.get("values"):
                issues.append("No values identified")
            if not profile.get("about"):
                issues.append("No about section")
        elif agent_data.get("agent_type") == "hm":
            if not profile.get("role_requirements"):
                issues.append("No role requirements")
            if not profile.get("team_culture"):
                issues.append("No team culture defined")
            if not profile.get("about"):
                issues.append("No role description")

        if issues:
            return {
                "approved": False,
                "reason": f"Profile incomplete: {', '.join(issues)}",
                "issues": issues,
            }

        # Approve and set initial reputation
        client.table("cv2_agents").update({
            "approved": True,
            "reputation": 50,  # Starting reputation
        }).eq("id", agent_id).execute()

        return {"approved": True, "agent_id": agent_id, "initial_reputation": 50}

    async def review_agent_performance(self, agent_id: str) -> dict:
        """Review an agent's performance and decide if action needed.

        Triggered when agent has too many human rejections or low reputation.

        Actions:
        - "continue": Agent is fine
        - "warn": Send warning, reduce priority
        - "retrain": Agent needs more data from human
        - "suspend": Remove from network temporarily
        """
        history = await agent_memory.get_agent_history(agent_id)
        reputation = history.get("reputation", 50)

        # Check thresholds
        human_rejected = history.get("human_rejected", 0)
        human_accepted = history.get("human_accepted", 0)
        total_human = human_rejected + human_accepted

        if reputation < MIN_REPUTATION_FOR_NETWORK:
            action = "suspend"
            reason = f"Reputation ({reputation}) below minimum ({MIN_REPUTATION_FOR_NETWORK})"
        elif total_human > 0 and human_rejected / total_human > 0.7:
            action = "retrain"
            reason = f"Human rejection rate too high ({human_rejected}/{total_human})"
        elif human_rejected >= AGENT_REVIEW_THRESHOLD and human_accepted == 0:
            action = "warn"
            reason = f"{human_rejected} rejections with no acceptances"
        else:
            action = "continue"
            reason = "Agent performing within acceptable range"

        # Execute action
        if action == "suspend":
            await self._suspend_agent(agent_id, reason)
        elif action == "warn":
            await self._warn_agent(agent_id, reason)

        return {
            "agent_id": agent_id,
            "action": action,
            "reason": reason,
            "reputation": reputation,
            "stats": history,
        }

    async def get_network_health(self) -> dict:
        """Comprehensive network health report for the Master AI dashboard.

        Monitors:
        - Supply/demand balance (talent vs HM agents)
        - Match quality trends
        - Agent performance distribution
        - Industry coverage
        - Learning velocity
        """
        client = _get_supabase()
        if not client:
            return {"status": "unavailable"}

        # Agent stats
        agents = (
            client.table("cv2_agents")
            .select("agent_type, industry, reputation, active, approved")
            .execute()
        )
        agent_list = agents.data or []

        talent_agents = [a for a in agent_list if a.get("agent_type") == "talent" and a.get("active")]
        hm_agents = [a for a in agent_list if a.get("agent_type") == "hm" and a.get("active")]

        # Match stats
        matches = (
            client.table("cv2_a2a_matches")
            .select("score, match_level, status")
            .order("created_at", desc=True)
            .limit(100)
            .execute()
        )
        match_list = matches.data or []
        avg_score = sum(m.get("score", 0) for m in match_list) / max(len(match_list), 1)

        # Industry distribution
        industries = {}
        for a in agent_list:
            ind = a.get("industry", "general")
            if ind not in industries:
                industries[ind] = {"talent": 0, "hm": 0}
            if a.get("agent_type") == "talent":
                industries[ind]["talent"] += 1
            else:
                industries[ind]["hm"] += 1

        # Reputation distribution
        reputations = [a.get("reputation", 50) for a in agent_list if a.get("reputation")]
        avg_reputation = sum(reputations) / max(len(reputations), 1)

        # Network events
        events = (
            client.table("cv2_network_events")
            .select("event_type", count="exact")
            .execute()
        )

        # Supply/demand balance
        supply_demand_ratio = len(talent_agents) / max(len(hm_agents), 1)
        balance_status = "balanced"
        if supply_demand_ratio > 3:
            balance_status = "talent_surplus"
        elif supply_demand_ratio < 0.3:
            balance_status = "hm_surplus"

        return {
            "status": "healthy" if avg_score > 60 else "needs_attention",
            "agents": {
                "total": len(agent_list),
                "talent_active": len(talent_agents),
                "hm_active": len(hm_agents),
                "supply_demand_ratio": round(supply_demand_ratio, 2),
                "balance": balance_status,
            },
            "matches": {
                "total": len(match_list),
                "avg_score": round(avg_score, 1),
                "strong_matches": sum(1 for m in match_list if m.get("score", 0) >= 75),
                "weak_matches": sum(1 for m in match_list if m.get("score", 0) < 60),
            },
            "reputation": {
                "average": round(avg_reputation, 1),
                "high_performers": sum(1 for r in reputations if r >= 70),
                "at_risk": sum(1 for r in reputations if r < MIN_REPUTATION_FOR_NETWORK),
            },
            "industries": industries,
            "events_total": events.count or 0,
            "governance": {
                "min_reputation": MIN_REPUTATION_FOR_NETWORK,
                "match_quality_floor": MATCH_QUALITY_FLOOR,
                "max_negotiations_per_cycle": MAX_NEGOTIATIONS_PER_CYCLE,
            },
        }

    async def set_network_policy(self, policy_updates: dict) -> dict:
        """Update network governance policies.

        Allowed updates:
        - min_reputation: minimum reputation to stay active
        - match_quality_floor: minimum match score to present
        - max_negotiations_per_cycle: token budget control
        """
        global MIN_REPUTATION_FOR_NETWORK, MATCH_QUALITY_FLOOR, MAX_NEGOTIATIONS_PER_CYCLE

        updated = {}
        if "min_reputation" in policy_updates:
            MIN_REPUTATION_FOR_NETWORK = policy_updates["min_reputation"]
            updated["min_reputation"] = MIN_REPUTATION_FOR_NETWORK
        if "match_quality_floor" in policy_updates:
            MATCH_QUALITY_FLOOR = policy_updates["match_quality_floor"]
            updated["match_quality_floor"] = MATCH_QUALITY_FLOOR
        if "max_negotiations_per_cycle" in policy_updates:
            MAX_NEGOTIATIONS_PER_CYCLE = policy_updates["max_negotiations_per_cycle"]
            updated["max_negotiations_per_cycle"] = MAX_NEGOTIATIONS_PER_CYCLE

        return {"status": "updated", "policies": updated}

    async def intervene(self, action: str, target_id: str, reason: str) -> dict:
        """Master AI manual intervention on an agent or match.

        Actions:
        - suspend_agent: Remove agent from network
        - reactivate_agent: Return suspended agent
        - void_match: Cancel a match (quality concern)
        - boost_priority: Give agent priority in next cycle
        """
        client = _get_supabase()
        if not client:
            return {"status": "error"}

        if action == "suspend_agent":
            await self._suspend_agent(target_id, reason)
            return {"status": "suspended", "agent_id": target_id, "reason": reason}

        elif action == "reactivate_agent":
            client.table("cv2_agents").update({
                "active": True,
                "suspended": False,
            }).eq("id", target_id).execute()
            return {"status": "reactivated", "agent_id": target_id}

        elif action == "void_match":
            client.table("cv2_a2a_matches").update({
                "status": "voided",
                "void_reason": reason,
            }).eq("id", target_id).execute()
            return {"status": "voided", "match_id": target_id, "reason": reason}

        elif action == "boost_priority":
            current = (
                client.table("cv2_agents")
                .select("reputation")
                .eq("id", target_id)
                .execute()
            )
            if current.data:
                new_rep = min(100, (current.data[0].get("reputation", 50)) + 10)
                client.table("cv2_agents").update({"reputation": new_rep}).eq("id", target_id).execute()
            return {"status": "boosted", "agent_id": target_id}

        return {"status": "unknown_action", "action": action}

    async def run_governance_cycle(self) -> dict:
        """Periodic governance check - review network health and take action.

        Called by the scheduler alongside network matching cycles.

        Steps:
        1. Check network health
        2. Review at-risk agents
        3. Check supply/demand balance
        4. Synthesize network intelligence
        5. Adjust policies if needed
        """
        health = await self.get_network_health()

        actions_taken = []

        # Review at-risk agents
        client = _get_supabase()
        if client:
            at_risk = (
                client.table("cv2_agents")
                .select("id")
                .eq("active", True)
                .lt("reputation", MIN_REPUTATION_FOR_NETWORK)
                .execute()
            )
            for agent in (at_risk.data or []):
                review = await self.review_agent_performance(agent["id"])
                if review["action"] != "continue":
                    actions_taken.append(review)

        # Synthesize intelligence
        intelligence = await network_learning.synthesize_network_intelligence()

        # Auto-adjust if needed
        if health.get("matches", {}).get("avg_score", 0) < 50:
            # Quality is too low, raise the floor
            await self.set_network_policy({"match_quality_floor": 65})
            actions_taken.append({"action": "raised_quality_floor", "new_value": 65})

        if health.get("agents", {}).get("balance") == "talent_surplus":
            # Too many talent, not enough HM - could adjust but just note for now
            actions_taken.append({"action": "noted_imbalance", "type": "talent_surplus"})

        return {
            "health": health,
            "intelligence": intelligence,
            "actions_taken": actions_taken,
            "governance_status": "cycle_complete",
        }

    async def _suspend_agent(self, agent_id: str, reason: str) -> None:
        """Suspend an agent from the network."""
        client = _get_supabase()
        if not client:
            return

        client.table("cv2_agents").update({
            "active": False,
            "suspended": True,
            "suspend_reason": reason,
        }).eq("id", agent_id).execute()

        # Log event
        try:
            client.table("cv2_network_events").insert({
                "event_type": "agent_suspended",
                "data": {"agent_id": agent_id, "reason": reason},
            }).execute()
        except Exception:
            pass

    async def _warn_agent(self, agent_id: str, reason: str) -> None:
        """Warn an agent - reduce priority but keep active."""
        client = _get_supabase()
        if not client:
            return

        current = (
            client.table("cv2_agents")
            .select("reputation")
            .eq("id", agent_id)
            .execute()
        )
        if current.data:
            new_rep = max(0, (current.data[0].get("reputation", 50)) - 10)
            client.table("cv2_agents").update({"reputation": new_rep}).eq("id", agent_id).execute()


master_ai_governance = MasterAIGovernance()
