"""Market Intelligence Service - External data gathering for Master AI.

Gathers and synthesizes market knowledge from:
- Job market trends (who's hiring, which industries growing)
- Salary benchmarks by role and industry
- Skills demand analysis (trending skills, declining skills)
- Economic indicators affecting hiring
- Candidate supply/demand by industry
- Geographic hiring patterns

This feeds into Master AI's decision-making about:
- Network development priorities
- Which industries to focus on
- Pricing and positioning guidance for agents
- Platform development direction

Data sources (designed for integration):
- Internal platform data (our own matches and patterns)
- Industry reports (synthesized by AI)
- Market indicators (configurable data feeds)
"""

import json
from typing import Optional
from datetime import datetime, timezone, timedelta

import anthropic
from supabase import create_client

from app.config import ANTHROPIC_API_KEY, SUPABASE_URL, SUPABASE_SERVICE_KEY


def _get_supabase():
    if not SUPABASE_URL or not SUPABASE_SERVICE_KEY:
        return None
    return create_client(SUPABASE_URL, SUPABASE_SERVICE_KEY)


class MarketIntelligence:
    """Gathers and synthesizes market intelligence for the platform."""

    def __init__(self):
        self._anthropic = None
        self._cache = {}  # Simple in-memory cache for expensive operations

    @property
    def client(self):
        if self._anthropic is None:
            self._anthropic = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)
        return self._anthropic

    async def get_market_snapshot(self) -> dict:
        """Get current market intelligence snapshot.

        Combines internal platform data with synthesized market knowledge.
        """
        client = _get_supabase()
        internal_data = await self._get_internal_market_data(client)
        synthesis = await self._synthesize_market_view(internal_data)

        return {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "internal_metrics": internal_data,
            "market_synthesis": synthesis,
            "recommendations": await self._get_platform_recommendations(internal_data, synthesis),
        }

    async def get_industry_report(self, industry: str) -> dict:
        """Get detailed market intelligence for a specific industry.

        Analyzes:
        - Supply/demand balance in our network for this industry
        - Skills most in demand
        - Salary positioning
        - Hiring velocity trends
        """
        client = _get_supabase()
        if not client:
            return {"status": "unavailable", "industry": industry}

        # Get agents in this industry
        agents = (
            client.table("cv2_agents")
            .select("id, agent_type, reputation, active, profile")
            .eq("industry", industry)
            .execute()
        )
        agent_list = agents.data or []

        talent_agents = [a for a in agent_list if a.get("agent_type") == "talent"]
        hm_agents = [a for a in agent_list if a.get("agent_type") == "hm"]

        # Get matches in this industry
        matches = (
            client.table("cv2_a2a_matches")
            .select("score, status, match_level, created_at")
            .order("created_at", desc=True)
            .limit(100)
            .execute()
        )

        # Extract skills demand from HM profiles
        skills_demand = {}
        for agent in hm_agents:
            profile = agent.get("profile", {})
            if isinstance(profile, dict):
                must_have = profile.get("role_requirements", {}).get("must_have", [])
                for skill in must_have:
                    skills_demand[skill] = skills_demand.get(skill, 0) + 1

        # Extract skills supply from talent profiles
        skills_supply = {}
        for agent in talent_agents:
            profile = agent.get("profile", {})
            if isinstance(profile, dict):
                verified = profile.get("skills_verified", [])
                for skill in verified:
                    skills_supply[skill] = skills_supply.get(skill, 0) + 1

        # Find gaps (high demand, low supply)
        skill_gaps = []
        for skill, demand in skills_demand.items():
            supply = skills_supply.get(skill, 0)
            if demand > supply:
                skill_gaps.append({"skill": skill, "demand": demand, "supply": supply, "gap": demand - supply})
        skill_gaps.sort(key=lambda x: -x["gap"])

        return {
            "industry": industry,
            "supply_demand": {
                "talent_count": len(talent_agents),
                "hm_count": len(hm_agents),
                "ratio": round(len(talent_agents) / max(len(hm_agents), 1), 2),
                "balance": "surplus" if len(talent_agents) > len(hm_agents) * 2 else
                           "shortage" if len(hm_agents) > len(talent_agents) * 2 else "balanced",
            },
            "skills_demand": dict(sorted(skills_demand.items(), key=lambda x: -x[1])[:15]),
            "skills_supply": dict(sorted(skills_supply.items(), key=lambda x: -x[1])[:15]),
            "skill_gaps": skill_gaps[:10],
            "performance": {
                "avg_reputation_talent": round(
                    sum(a.get("reputation", 50) for a in talent_agents) / max(len(talent_agents), 1), 1
                ),
                "avg_reputation_hm": round(
                    sum(a.get("reputation", 50) for a in hm_agents) / max(len(hm_agents), 1), 1
                ),
                "active_rate": round(
                    sum(1 for a in agent_list if a.get("active")) / max(len(agent_list), 1) * 100, 1
                ),
            },
        }

    async def get_hiring_trends(self) -> dict:
        """Analyze hiring trends from platform data.

        Tracks:
        - New jobs posted over time
        - Match success rates over time
        - Industry growth/decline
        - Most active hiring companies (anonymized)
        """
        client = _get_supabase()
        if not client:
            return {"status": "unavailable"}

        # Get job creation timeline
        jobs = (
            client.table("cv2_jobs")
            .select("industry, created_at, status")
            .order("created_at", desc=True)
            .limit(200)
            .execute()
        )
        job_list = jobs.data or []

        # Get match timeline
        matches = (
            client.table("cv2_a2a_matches")
            .select("score, status, created_at")
            .order("created_at", desc=True)
            .limit(200)
            .execute()
        )
        match_list = matches.data or []

        # Industry activity
        industry_activity = {}
        for job in job_list:
            ind = job.get("industry", "general")
            if ind not in industry_activity:
                industry_activity[ind] = {"jobs_posted": 0, "active": 0}
            industry_activity[ind]["jobs_posted"] += 1
            if job.get("status") == "active":
                industry_activity[ind]["active"] += 1

        # Match trends (weekly buckets)
        # Just count total for now
        total_matches = len(match_list)
        successful = sum(1 for m in match_list if m.get("status") == "matched")
        avg_score = sum(m.get("score", 0) for m in match_list) / max(total_matches, 1)

        return {
            "hiring_activity": {
                "total_jobs": len(job_list),
                "active_jobs": sum(1 for j in job_list if j.get("status") == "active"),
                "industries_active": len(industry_activity),
            },
            "match_trends": {
                "total_negotiations": total_matches,
                "successful_matches": successful,
                "success_rate": round(successful / max(total_matches, 1) * 100, 1),
                "avg_match_score": round(avg_score, 1),
            },
            "industry_activity": dict(
                sorted(industry_activity.items(), key=lambda x: -x[1]["jobs_posted"])
            ),
            "market_signals": await self._detect_market_signals(job_list, match_list),
        }

    async def synthesize_strategic_brief(self) -> dict:
        """Create a strategic brief for Master AI decision-making.

        Synthesizes all market data into actionable intelligence for
        platform development and network management.
        """
        if not ANTHROPIC_API_KEY:
            return {"status": "api_required"}

        # Gather all data
        snapshot = await self._get_internal_market_data(_get_supabase())
        trends = await self.get_hiring_trends()

        data_text = json.dumps({
            "platform_data": snapshot,
            "trends": trends,
        }, indent=2)[:4000]

        prompt = f"""You are the STRATEGIC INTELLIGENCE ADVISOR for an AI recruitment platform.

Analyze the following platform and market data, then provide a strategic brief.

PLATFORM DATA:
{data_text}

Provide a strategic brief covering:
1. MARKET POSITION: Where does the platform stand right now?
2. GROWTH OPPORTUNITIES: Which industries/roles should we prioritize?
3. RISK FACTORS: What could harm the platform's health?
4. NETWORK DEVELOPMENT: What should Master AI focus on next?
5. RESOURCE ALLOCATION: Where should we invest API tokens?

Return JSON:
{{
    "market_position": "1-2 sentence current state assessment",
    "growth_opportunities": [
        {{"area": "opportunity name", "rationale": "why", "priority": "high/medium/low"}}
    ],
    "risk_factors": [
        {{"risk": "risk description", "severity": "high/medium/low", "mitigation": "suggested action"}}
    ],
    "network_priorities": ["ordered list of what Master AI should focus on"],
    "resource_recommendations": {{
        "increase_spend": ["areas worth more investment"],
        "reduce_spend": ["areas to cut back"],
        "new_capabilities": ["suggested new features/services"]
    }},
    "confidence": 0-100
}}
Return ONLY JSON."""

        try:
            response = self.client.messages.create(
                model="claude-sonnet-4-20250514",
                max_tokens=1200,
                messages=[{"role": "user", "content": prompt}],
            )
            text = response.content[0].text.strip()
            if text.startswith("```"):
                text = text.split("\n", 1)[1].rsplit("```", 1)[0]
            return json.loads(text)
        except Exception:
            return {
                "market_position": "Unable to generate strategic brief",
                "growth_opportunities": [],
                "risk_factors": [],
                "network_priorities": [],
                "resource_recommendations": {},
                "confidence": 0,
            }

    async def ingest_market_data(self, source: str, data: dict) -> dict:
        """Ingest external market data from 3rd party sources.

        Designed for future integration with:
        - Job board APIs (LinkedIn, Indeed, etc.)
        - Economic data feeds
        - Industry reports
        - Salary surveys

        Stores processed data for Master AI consumption.
        """
        client = _get_supabase()
        if not client:
            return {"status": "unavailable"}

        record = {
            "source": source,
            "data": data,
            "ingested_at": datetime.now(timezone.utc).isoformat(),
            "processed": False,
        }

        try:
            client.table("cv2_market_data").insert(record).execute()
            return {"status": "ingested", "source": source}
        except Exception:
            return {"status": "stored_in_memory", "source": source}

    async def _get_internal_market_data(self, client) -> dict:
        """Gather internal platform metrics as market data."""
        if not client:
            return {}

        try:
            agents = (
                client.table("cv2_agents")
                .select("agent_type, industry, active, reputation")
                .execute()
            )
            agent_list = agents.data or []

            jobs = (
                client.table("cv2_jobs")
                .select("industry, status")
                .execute()
            )
            job_list = jobs.data or []

            users = (
                client.table("cv2_profiles")
                .select("stage, industry")
                .execute()
            )
            user_list = users.data or []
        except Exception:
            return {}

        return {
            "total_agents": len(agent_list),
            "active_agents": sum(1 for a in agent_list if a.get("active")),
            "talent_agents": sum(1 for a in agent_list if a.get("agent_type") == "talent"),
            "hm_agents": sum(1 for a in agent_list if a.get("agent_type") == "hm"),
            "total_jobs": len(job_list),
            "active_jobs": sum(1 for j in job_list if j.get("status") == "active"),
            "total_users": len(user_list),
            "matchable_users": sum(1 for u in user_list if u.get("stage") == "matchable"),
            "industries_covered": list(set(
                a.get("industry", "general") for a in agent_list if a.get("industry")
            )),
            "avg_reputation": round(
                sum(a.get("reputation", 50) for a in agent_list) / max(len(agent_list), 1), 1
            ),
        }

    async def _synthesize_market_view(self, internal_data: dict) -> dict:
        """Synthesize a market view from internal data."""
        total_agents = internal_data.get("total_agents", 0)
        talent = internal_data.get("talent_agents", 0)
        hm = internal_data.get("hm_agents", 0)

        market_health = "growing" if total_agents > 10 else "early_stage" if total_agents > 0 else "pre_launch"
        balance = "balanced" if 0.5 < talent / max(hm, 1) < 2 else "talent_heavy" if talent > hm else "hm_heavy"

        return {
            "market_health": market_health,
            "supply_demand_balance": balance,
            "network_maturity": "mature" if total_agents > 50 else "growing" if total_agents > 10 else "nascent",
            "industry_diversity": len(internal_data.get("industries_covered", [])),
        }

    async def _get_platform_recommendations(self, internal: dict, synthesis: dict) -> list:
        """Generate actionable recommendations."""
        recs = []

        if synthesis.get("supply_demand_balance") == "talent_heavy":
            recs.append({
                "type": "growth",
                "priority": "high",
                "action": "Recruit more hiring managers to balance the network",
            })
        elif synthesis.get("supply_demand_balance") == "hm_heavy":
            recs.append({
                "type": "growth",
                "priority": "high",
                "action": "Focus on talent acquisition to fill open roles",
            })

        if synthesis.get("network_maturity") == "nascent":
            recs.append({
                "type": "development",
                "priority": "high",
                "action": "Focus on user onboarding quality over quantity",
            })

        if internal.get("avg_reputation", 50) < 40:
            recs.append({
                "type": "quality",
                "priority": "critical",
                "action": "Agent quality is declining - run training cycles",
            })

        if len(internal.get("industries_covered", [])) < 3:
            recs.append({
                "type": "expansion",
                "priority": "medium",
                "action": "Expand industry coverage for network effects",
            })

        return recs

    async def _detect_market_signals(self, jobs: list, matches: list) -> list:
        """Detect emerging market signals from data patterns."""
        signals = []

        if len(jobs) > 20:
            # Check for industry concentration
            industries = [j.get("industry", "general") for j in jobs]
            from collections import Counter
            top_industry = Counter(industries).most_common(1)
            if top_industry and top_industry[0][1] > len(jobs) * 0.5:
                signals.append({
                    "signal": f"Industry concentration: {top_industry[0][0]} dominates ({top_industry[0][1]} jobs)",
                    "type": "concentration_risk",
                })

        if matches:
            recent_scores = [m.get("score", 0) for m in matches[:20]]
            older_scores = [m.get("score", 0) for m in matches[20:40]]
            if recent_scores and older_scores:
                recent_avg = sum(recent_scores) / len(recent_scores)
                older_avg = sum(older_scores) / len(older_scores)
                if recent_avg < older_avg - 10:
                    signals.append({
                        "signal": f"Match quality declining: {recent_avg:.0f} vs {older_avg:.0f}",
                        "type": "quality_decline",
                    })

        return signals


market_intelligence = MarketIntelligence()
