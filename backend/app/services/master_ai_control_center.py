"""Master AI Control Center - The brain of the CV 2.0 platform.

This is the CENTRAL ORCHESTRATOR that brings everything together:

DEPARTMENTS:
1. AGENT MANAGEMENT  - Create, train, monitor, suspend agents
2. TRAINING CENTER   - Diagnose, retrain, improve agent performance
3. ANALYTICS         - Performance rankings, behavior analysis, data metrics
4. MARKET INTELLIGENCE - External data, hiring trends, industry reports
5. COST MANAGEMENT   - API spending, budget tracking, cost optimization
6. AI COUNCIL        - Multi-perspective advisory for strategic decisions
7. GOVERNANCE        - Network health, policy management, interventions
8. R&D              - Platform development direction, new capabilities

The Master AI uses all these departments to make informed decisions
about how to run the network, develop the platform, and ensure quality.
"""

import json
from typing import Optional
from datetime import datetime, timezone

from app.database import get_db

from app.services.ai_analytics import ai_analytics
from app.services.cost_tracker import cost_tracker
from app.services.agent_training_center import agent_training_center
from app.services.market_intelligence import market_intelligence
from app.services.ai_council import ai_council
from app.services.master_ai_governance import master_ai_governance
from app.services.hallucination_guard import hallucination_guard
from app.services.network_learning import network_learning


def _get_supabase():
    return get_db()


class MasterAIControlCenter:
    """Central control center orchestrating all platform AI operations."""

    async def get_full_dashboard(self) -> dict:
        """Get comprehensive dashboard data for the control center.

        This is the main view - everything the Master AI needs to see
        at a glance to understand platform health and make decisions.
        """
        # Gather data from all departments
        health = await master_ai_governance.get_network_health()
        rankings = await ai_analytics.get_agent_rankings()
        costs = await cost_tracker.get_cost_summary("today")
        budget = await cost_tracker.get_budget_status()
        training_queue = await agent_training_center.get_training_queue()
        data_report = await ai_analytics.get_data_collection_report()

        return {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "network_health": health,
            "agent_overview": {
                "total": rankings.get("total_agents", 0),
                "active": rankings.get("active_agents", 0),
                "top_performer": rankings.get("top_performer"),
                "avg_performance": rankings.get("avg_performance", 0),
                "needing_training": training_queue.get("total_needing_training", 0),
                "critical_agents": training_queue.get("critical_count", 0),
            },
            "costs": {
                "today_usd": costs.get("total_cost_usd", 0),
                "api_calls_today": costs.get("api_calls", 0),
                "budget_status": budget.get("status", "unknown"),
                "budget_usage_percent": budget.get("usage_percent", 0),
                "monthly_projection": budget.get("projection_usd"),
            },
            "data_health": {
                "total_users": data_report.get("total_users", 0),
                "completion_rate": data_report.get("data_quality", {}).get("completion_rate", 0),
                "recommendations": data_report.get("recommendations", []),
            },
            "alerts": self._generate_alerts(health, budget, training_queue, rankings),
        }

    async def run_full_cycle(self) -> dict:
        """Run a complete Master AI operational cycle.

        This is the periodic heartbeat of the platform:
        1. Check network health
        2. Run governance (review at-risk agents)
        3. Run training cycle (retrain underperformers)
        4. Monitor hallucination drift
        5. Update market intelligence
        6. Generate strategic brief
        7. Log cycle results

        Should be triggered periodically (e.g., every hour in production).
        """
        cycle_start = datetime.now(timezone.utc)
        results = {}

        # 1. Governance cycle
        governance = await master_ai_governance.run_governance_cycle()
        results["governance"] = {
            "status": governance.get("governance_status"),
            "actions_taken": len(governance.get("actions_taken", [])),
        }

        # 2. Training cycle
        training = await agent_training_center.run_training_cycle()
        results["training"] = {
            "agents_trained": training.get("agents_trained", 0),
            "trainings_run": training.get("trainings_run", 0),
        }

        # 3. Market intelligence update
        try:
            trends = await market_intelligence.get_hiring_trends()
            results["market"] = {
                "active_jobs": trends.get("hiring_activity", {}).get("active_jobs", 0),
                "match_success_rate": trends.get("match_trends", {}).get("success_rate", 0),
            }
        except Exception:
            results["market"] = {"status": "error"}

        # 4. Cost check
        budget = await cost_tracker.get_budget_status()
        results["costs"] = {
            "status": budget.get("status"),
            "usage_percent": budget.get("usage_percent", 0),
        }

        # 5. Flush cost records
        cost_tracker.flush()

        # Log cycle completion
        client = _get_supabase()
        if client:
            try:
                client.table("cv2_network_events").insert({
                    "event_type": "master_cycle_complete",
                    "data": {
                        "duration_ms": int(
                            (datetime.now(timezone.utc) - cycle_start).total_seconds() * 1000
                        ),
                        "results": results,
                    },
                }).execute()
            except Exception:
                pass

        return {
            "status": "cycle_complete",
            "started_at": cycle_start.isoformat(),
            "results": results,
        }

    async def get_agent_deep_dive(self, agent_id: str) -> dict:
        """Deep dive into a specific agent - everything we know about it.

        Combines analytics, training diagnosis, cost data, and behavior analysis.
        """
        behavior = await ai_analytics.get_behavior_analysis(agent_id)
        diagnosis = await agent_training_center.diagnose_agent(agent_id)
        costs = await cost_tracker.get_agent_costs(agent_id)

        return {
            "agent_id": agent_id,
            "behavior": behavior,
            "diagnosis": diagnosis,
            "costs": costs,
            "recommended_actions": self._get_agent_actions(behavior, diagnosis),
        }

    async def consult_council(self, topic: str, context: Optional[dict] = None) -> dict:
        """Consult the AI council on a platform decision.

        Wrapper that adds platform context to council deliberations.
        """
        # Add platform state to context
        full_context = context or {}
        try:
            health = await master_ai_governance.get_network_health()
            full_context["network_health"] = {
                "status": health.get("status"),
                "agents": health.get("agents", {}),
                "matches": health.get("matches", {}),
            }
        except Exception:
            pass

        return await ai_council.convene(
            topic=topic,
            context=full_context,
        )

    async def get_strategic_overview(self) -> dict:
        """High-level strategic overview for platform leadership.

        Combines market intelligence, analytics, and council insights.
        """
        brief = await market_intelligence.synthesize_strategic_brief()
        analytics = await ai_analytics.get_behavior_analysis()
        data = await ai_analytics.get_data_collection_report()

        return {
            "strategic_brief": brief,
            "network_analytics": analytics,
            "data_health": data,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }

    async def get_rd_status(self) -> dict:
        """R&D status - what capabilities exist and what's needed.

        Reports on:
        - Current platform capabilities
        - Feature utilization rates
        - Suggested new capabilities (from council + market data)
        - Technical debt indicators
        """
        client = _get_supabase()
        if not client:
            return {"status": "unavailable"}

        # Capability inventory
        capabilities = {
            "onboarding": {"status": "active", "type": "user_journey"},
            "cv_analysis": {"status": "active", "type": "document_processing"},
            "structured_interview": {"status": "active", "type": "data_collection"},
            "ai_profile_generation": {"status": "active", "type": "ai_core"},
            "multi_round_negotiation": {"status": "active", "type": "ai_core"},
            "hallucination_guard": {"status": "active", "type": "integrity"},
            "agent_memory": {"status": "active", "type": "learning"},
            "network_learning": {"status": "active", "type": "learning"},
            "master_ai_governance": {"status": "active", "type": "governance"},
            "ai_council": {"status": "active", "type": "decision_support"},
            "market_intelligence": {"status": "active", "type": "intelligence"},
            "cost_tracking": {"status": "active", "type": "operations"},
            "agent_training": {"status": "active", "type": "improvement"},
            "analytics": {"status": "active", "type": "monitoring"},
        }

        # Feature utilization (based on event counts)
        try:
            events = (
                client.table("cv2_network_events")
                .select("event_type")
                .execute()
            )
            event_counts = {}
            for e in (events.data or []):
                et = e.get("event_type", "unknown")
                event_counts[et] = event_counts.get(et, 0) + 1
        except Exception:
            event_counts = {}

        # Suggested improvements
        suggested = []
        if not event_counts.get("council_session"):
            suggested.append({
                "capability": "ai_council",
                "suggestion": "Council not yet used - convene for strategic decisions",
            })
        if not event_counts.get("agent_retrained"):
            suggested.append({
                "capability": "agent_training",
                "suggestion": "No agents retrained yet - run training cycle",
            })

        return {
            "capabilities": capabilities,
            "total_capabilities": len(capabilities),
            "feature_utilization": event_counts,
            "suggested_improvements": suggested,
            "architecture": {
                "backend": "FastAPI + Supabase",
                "ai_provider": "Anthropic Claude",
                "models_used": ["claude-sonnet-4-20250514"],
                "services_count": len(capabilities),
            },
        }

    def _generate_alerts(self, health: dict, budget: dict, training: dict, rankings: dict) -> list:
        """Generate priority alerts for the dashboard."""
        alerts = []

        # Health alerts
        if health.get("status") == "needs_attention":
            alerts.append({"level": "warning", "source": "health", "message": "Network health needs attention"})

        # Budget alerts
        if budget.get("status") == "critical":
            alerts.append({"level": "critical", "source": "budget", "message": f"Budget {budget.get('usage_percent', 0):.0f}% used"})
        elif budget.get("status") == "warning":
            alerts.append({"level": "warning", "source": "budget", "message": f"Budget {budget.get('usage_percent', 0):.0f}% used"})

        # Training alerts
        if training.get("critical_count", 0) > 0:
            alerts.append({
                "level": "critical",
                "source": "training",
                "message": f"{training['critical_count']} agents need critical training",
            })

        # Agent performance alerts
        if rankings.get("avg_performance", 100) < 40:
            alerts.append({"level": "warning", "source": "performance", "message": "Average agent performance below threshold"})

        # Integrity alerts
        integrity = health.get("integrity", {})
        if integrity.get("hallucination_violations", 0) > 5:
            alerts.append({
                "level": "critical",
                "source": "integrity",
                "message": f"{integrity['hallucination_violations']} hallucination violations detected",
            })

        # Sort by severity
        level_order = {"critical": 0, "warning": 1, "info": 2}
        alerts.sort(key=lambda x: level_order.get(x["level"], 99))

        return alerts

    def _get_agent_actions(self, behavior: dict, diagnosis: dict) -> list:
        """Recommend actions for a specific agent based on analysis."""
        actions = []

        if diagnosis.get("priority") == "critical":
            actions.append({"action": "full_retrain", "urgency": "immediate"})
        elif diagnosis.get("priority") == "high":
            actions.append({"action": "correction_training", "urgency": "soon"})

        if not behavior.get("integrity", {}).get("has_directive"):
            actions.append({"action": "integrity_reinforcement", "urgency": "immediate"})

        if behavior.get("behavior_metrics", {}).get("score_trend") == "declining":
            actions.append({"action": "investigate_decline", "urgency": "soon"})

        if not actions:
            actions.append({"action": "monitor", "urgency": "routine"})

        return actions


master_ai_control_center = MasterAIControlCenter()
