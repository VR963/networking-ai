"""Demo data for when Supabase is unavailable.

Provides realistic sample data with 1 talent agent and 1 HM agent
so the Master Control Center can be demonstrated without a database connection.
"""

from datetime import datetime, timezone, timedelta

TALENT_AGENT_ID = "agent_sarah-chen-001"
HM_AGENT_ID = "hm_agent_dataflow-sre-001"

TALENT_PROFILE = {
    "about": "Senior full-stack engineer with 8 years of experience specializing in React, Python, and cloud architecture. Led teams of 5-10 engineers at two Y Combinator startups. Passionate about clean code, mentoring, and building products that matter.",
    "synopsis": "Versatile senior engineer who combines deep technical skill in Python/React/AWS with strong leadership and mentoring. Thrives in fast-paced, collaborative environments with high autonomy.",
    "skills_verified": ["Python", "React", "TypeScript", "Node.js", "PostgreSQL", "Redis", "AWS", "Docker", "Kubernetes", "System Design"],
    "values": ["Engineering excellence", "Mentorship", "Sustainable pace", "Honest communication"],
    "dealbreakers": ["Toxic blame culture", "No remote flexibility", "Feature velocity over quality"],
    "environment_preferences": {
        "pace": "fast",
        "structure": "flexible",
        "team_size": "medium",
        "remote_preference": "hybrid",
        "culture_type": "startup",
    },
    "communication_style": {
        "primary": "direct",
        "decision_making": "collaborative",
        "conflict_approach": "pragmatic",
        "feedback_preference": "data-driven",
    },
}

HM_PROFILE = {
    "about": "DataFlow Inc platform team seeking a Senior Backend Engineer to design and build scalable backend services for our data analytics platform. Small team, high autonomy, remote-first.",
    "synopsis": "High-autonomy backend role scaling a data pipeline from 10M to 100M events/day. Values intellectual curiosity and constructive culture over specific language background.",
    "role_requirements": {
        "must_have": ["5+ years backend", "Distributed systems", "PostgreSQL", "Cloud infrastructure"],
        "nice_to_have": ["ML pipelines", "Kubernetes", "Technical leadership"],
        "overrated": ["Specific language experience"],
    },
    "team_culture": {
        "pace": "fast",
        "autonomy": "high",
        "communication": "mixed",
        "growth_style": "mentored",
        "vibe": "Direct and supportive",
    },
    "dealbreakers": ["Blame-oriented attitude", "No curiosity", "Claims perfection"],
    "offer_flexibility": {
        "salary_range": "$180,000 - $220,000",
        "equity": "0.1-0.3%",
        "remote": True,
    },
}

def get_demo_dashboard():
    return {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "network_health": {
            "status": "healthy",
            "agents": {
                "talent_active": 1,
                "hm_active": 1,
                "supply_demand_ratio": 1.0,
                "balance": "balanced",
            },
            "matches": {
                "total": 1,
                "avg_score": 82,
                "recent_24h": 1,
            },
            "reputation": {
                "average": 68,
                "at_risk": 0,
            },
            "integrity": {
                "hallucination_violations": 0,
                "agents_with_directive": 2,
            },
        },
        "agent_overview": {
            "total": 2,
            "active": 2,
            "top_performer": {
                "agent_id": TALENT_AGENT_ID,
                "score": 78,
            },
            "avg_performance": 72,
            "needing_training": 0,
            "critical_agents": 0,
        },
        "costs": {
            "today_usd": 0.0247,
            "api_calls_today": 12,
            "budget_status": "healthy",
            "budget_usage_percent": 2.5,
            "monthly_projection": 0.74,
        },
        "data_health": {
            "total_users": 2,
            "completion_rate": 100,
            "recommendations": [],
        },
        "alerts": [
            {
                "level": "info",
                "source": "system",
                "message": "Demo mode: Supabase not reachable from this environment. Showing sample data with 1 talent + 1 HM agent.",
            },
        ],
    }


def get_demo_rankings():
    return {
        "total_agents": 2,
        "active_agents": 2,
        "avg_performance": 72,
        "top_performer": {"agent_id": TALENT_AGENT_ID, "score": 78},
        "rankings": [
            {
                "rank": 1,
                "agent_id": TALENT_AGENT_ID,
                "agent_type": "talent",
                "performance_score": 78,
                "reputation": 72,
                "total_matches": 1,
                "success_rate": 100,
            },
            {
                "rank": 2,
                "agent_id": HM_AGENT_ID,
                "agent_type": "hm",
                "performance_score": 66,
                "reputation": 65,
                "total_matches": 1,
                "success_rate": 100,
            },
        ],
    }


def get_demo_behavior():
    return {
        "network_behavior": {
            "total_active_agents": 2,
            "total_negotiations": 1,
            "avg_match_score": 82,
            "score_distribution": {
                "exceptional": 0,
                "strong": 1,
                "moderate": 0,
                "weak": 0,
                "poor": 0,
            },
        },
    }


def get_demo_communication():
    return {
        "user_facing": {
            "total_conversations": 2,
            "total_messages": 14,
            "avg_ai_response_length": 320,
            "messages_per_conversation": 7,
        },
    }


def get_demo_data_report():
    return {
        "total_users": 2,
        "data_coverage": {
            "have_cv": 1,
            "have_interview": 2,
            "have_ai_profile": 2,
            "fully_complete": 2,
        },
        "data_quality": {
            "completion_rate": 100,
        },
        "recommendations": [],
    }


def get_demo_costs(period="today"):
    return {
        "period": period,
        "total_cost_usd": 0.0247,
        "api_calls": 12,
        "monthly_projection_usd": 0.74,
        "by_operation": {
            "profile_generation": {"cost_usd": 0.0120, "calls": 2},
            "interview_analysis": {"cost_usd": 0.0087, "calls": 7},
            "matching": {"cost_usd": 0.0040, "calls": 3},
        },
        "by_model": {
            "claude-3-5-haiku-20241022": {"cost_usd": 0.0087, "calls": 7},
            "claude-sonnet-4-20250514": {"cost_usd": 0.0160, "calls": 5},
        },
        "by_agent": {
            TALENT_AGENT_ID: {"cost_usd": 0.0147, "calls": 8},
            HM_AGENT_ID: {"cost_usd": 0.0100, "calls": 4},
        },
    }


def get_demo_budget():
    return {
        "monthly_budget_usd": 100,
        "spent_usd": 0.0247,
        "remaining_usd": 99.9753,
        "usage_percent": 0.025,
        "status": "healthy",
        "projection_usd": 0.74,
    }


def get_demo_training_queue():
    return {
        "total_needing_training": 0,
        "critical_count": 0,
        "queue": [],
    }


def get_demo_market_snapshot():
    return {
        "internal_metrics": {
            "total_agents": 2,
            "talent_agents": 1,
            "hm_agents": 1,
            "matchable_users": 2,
        },
        "market_synthesis": {
            "network_maturity": "early",
            "market_health": "healthy",
            "supply_demand_balance": "balanced",
            "industry_diversity": 1,
        },
        "recommendations": [
            {"priority": "high", "action": "Grow talent pipeline — add more candidates to increase matching pool."},
            {"priority": "medium", "action": "Add HM roles in adjacent industries to diversify."},
        ],
    }


def get_demo_trends():
    return {
        "hiring_activity": {
            "total_jobs": 1,
            "active_jobs": 1,
            "industries_active": 1,
        },
        "match_trends": {
            "success_rate": 100,
            "avg_match_score": 82,
        },
        "market_signals": [
            {"signal": "Strong demand for backend engineers in technology sector."},
        ],
    }


def get_demo_rd():
    return {
        "capabilities": {
            "ai_profiling": {"status": "active", "version": "2.0"},
            "a2a_matching": {"status": "active", "version": "2.0"},
            "structured_interviews": {"status": "active", "version": "1.0"},
            "agent_training": {"status": "active", "version": "1.0"},
            "hallucination_guard": {"status": "active", "version": "1.0"},
            "market_intelligence": {"status": "active", "version": "1.0"},
            "ai_council": {"status": "active", "version": "1.0"},
            "marketing_ai": {"status": "active", "version": "1.0"},
        },
        "architecture": {
            "backend": "FastAPI + Python 3.11",
            "ai_provider": "Anthropic Claude",
            "models_used": ["claude-sonnet-4-20250514", "claude-3-5-haiku-20241022"],
            "services_count": 12,
        },
        "feature_utilization": {
            "profile_generation": 2,
            "interview_analysis": 7,
            "a2a_matching": 1,
            "cost_tracking": 12,
        },
        "suggested_improvements": [],
    }


def get_demo_marketing_dashboard():
    return {
        "overview": {
            "total_campaigns": 0,
            "active": 0,
            "pending_approval": 0,
            "completed": 0,
            "rejected": 0,
        },
        "budget": {
            "total_approved_usd": 0,
            "total_spent_usd": 0,
            "remaining_usd": 0,
        },
        "performance": {
            "total_signups": 2,
            "avg_cpa": 0,
        },
        "campaigns": [],
    }
