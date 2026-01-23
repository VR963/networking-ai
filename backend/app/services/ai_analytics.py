"""AI Analytics Service - Deep analysis of agent behavior and performance.

Provides Master AI with insights on:
- Agent performance rankings and trends
- Communication pattern analysis (user-facing and A2A)
- Behavior comparison between top and bottom performers
- Data collection metrics (what we're gathering, gaps)
- Negotiation style effectiveness
- User satisfaction correlation with agent behavior

This is the Master AI's eyes - it sees everything agents do and how well they do it.
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


class AIAnalytics:
    """Analytics engine for the Master AI Control Center."""

    def __init__(self):
        self._anthropic = None

    @property
    def client(self):
        if self._anthropic is None:
            self._anthropic = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)
        return self._anthropic

    async def get_agent_rankings(self) -> dict:
        """Rank all agents by performance metrics.

        Metrics:
        - Match success rate (matches that humans accepted)
        - Reputation score
        - Negotiation effectiveness (avg match score)
        - Hallucination record (violations)
        - Activity level (negotiations participated in)

        Returns ordered list from best to worst performing.
        """
        client = _get_supabase()
        if not client:
            return {"rankings": [], "status": "unavailable"}

        # Get all agents with their data
        agents = (
            client.table("cv2_agents")
            .select("id, agent_type, industry, reputation, active, profile")
            .execute()
        )
        if not agents.data:
            return {"rankings": [], "total_agents": 0}

        # Get match data per agent
        matches = (
            client.table("cv2_a2a_matches")
            .select("candidate_id, job_id, score, status, match_level")
            .execute()
        )
        match_data = matches.data or []

        # Get memory/history data
        memories = (
            client.table("cv2_agent_memory")
            .select("agent_id, event_type")
            .execute()
        )
        memory_data = memories.data or []

        # Build rankings
        rankings = []
        for agent in agents.data:
            agent_id = agent["id"]
            user_id = agent.get("profile", {}).get("user_id", "") if isinstance(agent.get("profile"), dict) else ""

            # Count matches
            agent_matches = [
                m for m in match_data
                if m.get("candidate_id") == user_id or m.get("job_id") == agent_id
            ]
            total_matches = len(agent_matches)
            avg_score = (
                sum(m.get("score", 0) for m in agent_matches) / max(total_matches, 1)
            )

            # Count events
            agent_events = [e for e in memory_data if e.get("agent_id") == agent_id]
            accepted = sum(1 for e in agent_events if e.get("event_type") == "human_accepted")
            rejected = sum(1 for e in agent_events if e.get("event_type") == "human_rejected")

            # Compute performance score
            reputation = agent.get("reputation", 50)
            success_rate = accepted / max(accepted + rejected, 1)
            performance_score = int(
                reputation * 0.3
                + success_rate * 100 * 0.3
                + min(avg_score, 100) * 0.2
                + min(total_matches * 5, 100) * 0.2
            )

            rankings.append({
                "agent_id": agent_id,
                "agent_type": agent.get("agent_type", "unknown"),
                "industry": agent.get("industry", "general"),
                "active": agent.get("active", False),
                "reputation": reputation,
                "performance_score": performance_score,
                "total_matches": total_matches,
                "avg_match_score": round(avg_score, 1),
                "human_accepted": accepted,
                "human_rejected": rejected,
                "success_rate": round(success_rate * 100, 1),
            })

        # Sort by performance score
        rankings.sort(key=lambda x: -x["performance_score"])

        # Add rank position
        for i, r in enumerate(rankings):
            r["rank"] = i + 1

        return {
            "rankings": rankings,
            "total_agents": len(rankings),
            "top_performer": rankings[0] if rankings else None,
            "avg_performance": round(
                sum(r["performance_score"] for r in rankings) / max(len(rankings), 1), 1
            ),
            "active_agents": sum(1 for r in rankings if r["active"]),
        }

    async def get_behavior_analysis(self, agent_id: Optional[str] = None) -> dict:
        """Analyze agent behavior patterns.

        If agent_id provided, analyze that specific agent.
        Otherwise, analyze network-wide patterns.
        """
        client = _get_supabase()
        if not client:
            return {"status": "unavailable"}

        if agent_id:
            return await self._analyze_single_agent(client, agent_id)
        return await self._analyze_network_behavior(client)

    async def _analyze_single_agent(self, client, agent_id: str) -> dict:
        """Deep behavior analysis for one agent."""
        # Get agent profile
        agent = (
            client.table("cv2_agents")
            .select("*")
            .eq("id", agent_id)
            .execute()
        )
        if not agent.data:
            return {"status": "agent_not_found"}

        agent_data = agent.data[0]
        profile = agent_data.get("profile", {})

        # Get negotiation history
        user_id = agent_data.get("user_id", "")
        matches = (
            client.table("cv2_a2a_matches")
            .select("score, match_level, status, negotiation_notes, created_at")
            .or_(f"candidate_id.eq.{user_id},job_id.eq.{agent_id}")
            .order("created_at", desc=True)
            .limit(20)
            .execute()
        )

        # Get conversation history
        conversations = (
            client.table("cv2_conversations")
            .select("messages, created_at")
            .eq("user_id", user_id)
            .order("created_at", desc=True)
            .limit(5)
            .execute()
        )

        # Compute behavior metrics
        match_list = matches.data or []
        scores = [m.get("score", 0) for m in match_list]

        return {
            "agent_id": agent_id,
            "agent_type": agent_data.get("agent_type"),
            "industry": agent_data.get("industry"),
            "reputation": agent_data.get("reputation", 50),
            "behavior_metrics": {
                "total_negotiations": len(match_list),
                "avg_score": round(sum(scores) / max(len(scores), 1), 1),
                "score_trend": self._compute_trend(scores),
                "score_consistency": self._compute_consistency(scores),
                "highest_score": max(scores) if scores else 0,
                "lowest_score": min(scores) if scores else 0,
            },
            "communication_profile": {
                "style": profile.get("communication_style", {}),
                "personality": profile.get("agent_personality", ""),
                "negotiation_priorities": profile.get("negotiation_priorities", []),
            },
            "user_interactions": {
                "total_conversations": len(conversations.data or []),
            },
            "integrity": {
                "has_directive": bool(profile.get("integrity_directive")),
                "personality_includes_integrity": "never exaggerate" in profile.get("agent_personality", "").lower(),
            },
        }

    async def _analyze_network_behavior(self, client) -> dict:
        """Network-wide behavior analysis."""
        agents = (
            client.table("cv2_agents")
            .select("id, agent_type, industry, reputation, active")
            .eq("active", True)
            .execute()
        )
        agent_list = agents.data or []

        # Get all recent matches
        matches = (
            client.table("cv2_a2a_matches")
            .select("score, match_level, status")
            .order("created_at", desc=True)
            .limit(200)
            .execute()
        )
        match_list = matches.data or []

        scores = [m.get("score", 0) for m in match_list]
        statuses = [m.get("status", "") for m in match_list]

        # Industry breakdown
        industry_performance = {}
        for a in agent_list:
            ind = a.get("industry", "general")
            if ind not in industry_performance:
                industry_performance[ind] = {"agents": 0, "avg_reputation": 0, "reputations": []}
            industry_performance[ind]["agents"] += 1
            industry_performance[ind]["reputations"].append(a.get("reputation", 50))

        for ind, data in industry_performance.items():
            reps = data.pop("reputations")
            data["avg_reputation"] = round(sum(reps) / max(len(reps), 1), 1)

        return {
            "network_behavior": {
                "total_active_agents": len(agent_list),
                "total_negotiations": len(match_list),
                "avg_match_score": round(sum(scores) / max(len(scores), 1), 1),
                "score_distribution": {
                    "exceptional": sum(1 for s in scores if s >= 85),
                    "strong": sum(1 for s in scores if 75 <= s < 85),
                    "moderate": sum(1 for s in scores if 65 <= s < 75),
                    "weak": sum(1 for s in scores if 55 <= s < 65),
                    "poor": sum(1 for s in scores if s < 55),
                },
                "status_distribution": {
                    "matched": statuses.count("matched"),
                    "rejected": statuses.count("rejected"),
                    "voided": statuses.count("voided"),
                    "partial": statuses.count("partial"),
                },
            },
            "industry_performance": industry_performance,
            "talent_vs_hm": {
                "talent_agents": sum(1 for a in agent_list if a.get("agent_type") == "talent"),
                "hm_agents": sum(1 for a in agent_list if a.get("agent_type") == "hm"),
                "talent_avg_rep": round(
                    sum(a.get("reputation", 50) for a in agent_list if a.get("agent_type") == "talent")
                    / max(sum(1 for a in agent_list if a.get("agent_type") == "talent"), 1), 1
                ),
                "hm_avg_rep": round(
                    sum(a.get("reputation", 50) for a in agent_list if a.get("agent_type") == "hm")
                    / max(sum(1 for a in agent_list if a.get("agent_type") == "hm"), 1), 1
                ),
            },
        }

    async def get_data_collection_report(self) -> dict:
        """Report on what data the platform is collecting and gaps.

        Shows what information we have vs what's missing for optimal matching.
        """
        client = _get_supabase()
        if not client:
            return {"status": "unavailable"}

        # Check profiles completeness
        profiles = (
            client.table("cv2_profiles")
            .select("user_id, stage, industry, ai_profile")
            .execute()
        )
        profile_list = profiles.data or []

        # Check documents
        documents = (
            client.table("cv2_documents")
            .select("user_id, doc_type, analysis")
            .execute()
        )
        doc_list = documents.data or []

        # Check interviews
        interviews = (
            client.table("cv2_interviews")
            .select("user_id, agent_type, answers")
            .execute()
        )
        interview_list = interviews.data or []

        # Compute gaps
        users_with_cv = set(d.get("user_id") for d in doc_list if d.get("doc_type") == "cv" and d.get("analysis"))
        users_with_interview = set(i.get("user_id") for i in interview_list if i.get("answers"))
        users_with_profile = set(p.get("user_id") for p in profile_list if p.get("ai_profile"))
        all_users = set(p.get("user_id") for p in profile_list)

        stage_distribution = {}
        for p in profile_list:
            stage = p.get("stage", "unknown")
            stage_distribution[stage] = stage_distribution.get(stage, 0) + 1

        return {
            "total_users": len(all_users),
            "data_coverage": {
                "have_cv": len(users_with_cv),
                "have_interview": len(users_with_interview),
                "have_ai_profile": len(users_with_profile),
                "fully_complete": len(users_with_cv & users_with_interview & users_with_profile),
                "missing_cv": len(all_users - users_with_cv),
                "missing_interview": len(all_users - users_with_interview),
                "missing_profile": len(all_users - users_with_profile),
            },
            "stage_distribution": stage_distribution,
            "data_quality": {
                "cvs_analyzed": len(users_with_cv),
                "interviews_completed": len(users_with_interview),
                "profiles_generated": len(users_with_profile),
                "completion_rate": round(
                    len(users_with_cv & users_with_interview & users_with_profile)
                    / max(len(all_users), 1) * 100, 1
                ),
            },
            "recommendations": self._get_data_recommendations(
                len(all_users), len(users_with_cv), len(users_with_interview), len(users_with_profile)
            ),
        }

    async def get_communication_analysis(self) -> dict:
        """Analyze how AI communicates with users and with other AI.

        Patterns: response length, question types, user engagement, etc.
        """
        client = _get_supabase()
        if not client:
            return {"status": "unavailable"}

        # Get recent conversations
        conversations = (
            client.table("cv2_conversations")
            .select("messages, user_id, created_at")
            .order("created_at", desc=True)
            .limit(50)
            .execute()
        )
        conv_list = conversations.data or []

        total_messages = 0
        ai_messages = 0
        user_messages = 0
        avg_ai_length = 0
        avg_user_length = 0

        for conv in conv_list:
            messages = conv.get("messages", [])
            if not isinstance(messages, list):
                continue
            for msg in messages:
                total_messages += 1
                content = msg.get("content", "")
                if msg.get("role") == "assistant":
                    ai_messages += 1
                    avg_ai_length += len(content)
                elif msg.get("role") == "user":
                    user_messages += 1
                    avg_user_length += len(content)

        # Get A2A negotiation data
        negotiations = (
            client.table("cv2_a2a_matches")
            .select("negotiation_notes, score")
            .order("created_at", desc=True)
            .limit(50)
            .execute()
        )
        neg_list = negotiations.data or []

        return {
            "user_facing": {
                "total_conversations": len(conv_list),
                "total_messages": total_messages,
                "ai_messages": ai_messages,
                "user_messages": user_messages,
                "avg_ai_response_length": round(avg_ai_length / max(ai_messages, 1)),
                "avg_user_message_length": round(avg_user_length / max(user_messages, 1)),
                "messages_per_conversation": round(total_messages / max(len(conv_list), 1), 1),
            },
            "agent_to_agent": {
                "total_negotiations": len(neg_list),
                "avg_negotiation_score": round(
                    sum(n.get("score", 0) for n in neg_list) / max(len(neg_list), 1), 1
                ),
            },
        }

    def _compute_trend(self, scores: list) -> str:
        """Compute if scores are trending up, down, or stable."""
        if len(scores) < 3:
            return "insufficient_data"
        recent = scores[:len(scores)//2]
        older = scores[len(scores)//2:]
        recent_avg = sum(recent) / len(recent)
        older_avg = sum(older) / len(older)
        diff = recent_avg - older_avg
        if diff > 5:
            return "improving"
        elif diff < -5:
            return "declining"
        return "stable"

    def _compute_consistency(self, scores: list) -> str:
        """Compute score consistency (standard deviation category)."""
        if len(scores) < 2:
            return "insufficient_data"
        avg = sum(scores) / len(scores)
        variance = sum((s - avg) ** 2 for s in scores) / len(scores)
        std_dev = variance ** 0.5
        if std_dev < 10:
            return "very_consistent"
        elif std_dev < 20:
            return "consistent"
        elif std_dev < 30:
            return "variable"
        return "inconsistent"

    def _get_data_recommendations(self, total, with_cv, with_interview, with_profile) -> list:
        """Generate recommendations for improving data coverage."""
        recs = []
        if total == 0:
            recs.append("No users yet - focus on user acquisition")
            return recs

        cv_rate = with_cv / total
        if cv_rate < 0.5:
            recs.append(f"Only {cv_rate*100:.0f}% of users have uploaded CVs - improve upload UX")

        interview_rate = with_interview / total
        if interview_rate < 0.4:
            recs.append(f"Only {interview_rate*100:.0f}% completed interviews - consider shorter interview flow")

        profile_rate = with_profile / total
        if profile_rate < 0.3:
            recs.append(f"Only {profile_rate*100:.0f}% have AI profiles - check activation threshold")

        if not recs:
            recs.append("Data coverage is healthy across all metrics")

        return recs


ai_analytics = AIAnalytics()
