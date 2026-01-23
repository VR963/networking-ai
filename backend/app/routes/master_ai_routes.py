import json
from typing import Optional

import anthropic
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from supabase import create_client

from app.config import SUPABASE_URL, SUPABASE_SERVICE_KEY, ANTHROPIC_API_KEY
from app.services.master_ai_control_center import master_ai_control_center
from app.services.ai_analytics import ai_analytics
from app.services.cost_tracker import cost_tracker
from app.services.agent_training_center import agent_training_center
from app.services.market_intelligence import market_intelligence
from app.services.ai_council import ai_council
from app.services.marketing_ai_agent import marketing_ai_agent
from app.services.campaign_manager import campaign_manager

router = APIRouter()


class CertifyRequest(BaseModel):
    user_id: str


class CouncilRequest(BaseModel):
    topic: str
    context: Optional[dict] = None
    members: Optional[list] = None


class TrainAgentRequest(BaseModel):
    agent_id: str
    training_type: str = "correction"  # correction, integrity, full_retrain


class MarketDataRequest(BaseModel):
    source: str
    data: dict


class CampaignActionRequest(BaseModel):
    campaign_id: str
    reason: str = ""


class CampaignMetricsRequest(BaseModel):
    campaign_id: str
    metrics: dict


class CampaignApproveRequest(BaseModel):
    campaign_id: str
    budget_override: Optional[float] = None


def _get_supabase():
    if not SUPABASE_URL or not SUPABASE_SERVICE_KEY:
        raise HTTPException(status_code=503, detail="Database not configured. Set SUPABASE_URL and SUPABASE_SERVICE_KEY.")
    return create_client(SUPABASE_URL, SUPABASE_SERVICE_KEY)


@router.get("/dashboard")
async def dashboard_stats():
    client = _get_supabase()

    users = client.table("cv2_users").select("id", count="exact").execute()
    agents = client.table("cv2_agents").select("id", count="exact").execute()
    conversations = client.table("cv2_conversations").select("id", count="exact").execute()
    matches = client.table("cv2_a2a_matches").select("id", count="exact").execute()
    patterns = client.table("cv2_collective_patterns").select("id", count="exact").execute()

    return {
        "users": users.count or 0,
        "agents": agents.count or 0,
        "conversations": conversations.count or 0,
        "matches": matches.count or 0,
        "patterns": patterns.count or 0,
    }


@router.get("/agents")
async def list_agents():
    client = _get_supabase()
    result = client.table("cv2_agents").select("*").execute()
    return {"agents": result.data or []}


@router.get("/patterns")
async def list_patterns():
    client = _get_supabase()
    result = (
        client.table("cv2_collective_patterns")
        .select("*")
        .order("created_at", desc=True)
        .limit(50)
        .execute()
    )
    return {"patterns": result.data or []}


@router.get("/matches")
async def list_matches():
    client = _get_supabase()
    result = (
        client.table("cv2_a2a_matches")
        .select("*")
        .order("score", desc=True)
        .execute()
    )
    return {"matches": result.data or []}


@router.get("/synthesize/{industry}")
async def synthesize_insights(industry: str):
    from app.services.collective_intelligence import collective_intelligence

    insights = await collective_intelligence.synthesize_industry_insights(industry)
    if not insights:
        return {"industry": industry, "insights": None, "message": "No patterns available for this industry yet."}
    return {"industry": industry, "insights": insights}


@router.post("/certify")
async def certify_agent(request: CertifyRequest):
    """Master AI certification: verify that the agent truly knows the user.

    This is step 4 in the CV 2.0 process. The Master AI reviews all learned
    patterns and conversation history to determine if the agent has sufficient
    understanding of the user to represent them in negotiations.

    Requirements:
    - User must be at 'calibration' stage with completed calibration
    - Must have learned patterns from conversations and calibration
    - Master AI evaluates depth of understanding

    On success: advances user to 'certified' stage.
    """
    client = _get_supabase()

    # Verify profile exists and is at correct stage
    profile_result = (
        client.table("cv2_profiles")
        .select("*")
        .eq("user_id", request.user_id)
        .execute()
    )
    if not profile_result.data:
        raise HTTPException(status_code=404, detail="Profile not found.")

    profile = profile_result.data[0]
    current_stage = profile.get("stage", "onboarding")

    if current_stage == "certified" or current_stage == "matchable":
        return {"status": "already_certified", "user_id": request.user_id, "stage": current_stage}

    if current_stage != "calibration":
        raise HTTPException(
            status_code=400,
            detail=f"User is at stage '{current_stage}'. Must complete calibration before certification."
        )

    # Check calibration is complete
    opp_result = (
        client.table("cv2_test_opportunities")
        .select("status")
        .eq("user_id", request.user_id)
        .execute()
    )
    opps = opp_result.data or []
    if not opps or any(o["status"] == "pending" for o in opps):
        raise HTTPException(status_code=400, detail="Calibration not complete. All test opportunities must be reviewed.")

    # Gather all learned patterns
    patterns_result = (
        client.table("cv2_collective_patterns")
        .select("patterns, pattern_type")
        .eq("user_id", request.user_id)
        .order("created_at", desc=True)
        .execute()
    )
    patterns = patterns_result.data or []

    if not patterns:
        raise HTTPException(
            status_code=400,
            detail="Insufficient learning. The agent needs more conversation data to be certified."
        )

    # Master AI evaluation: does the agent know enough?
    if not ANTHROPIC_API_KEY:
        raise HTTPException(status_code=503, detail="ANTHROPIC_API_KEY required for certification.")

    patterns_summary = json.dumps([p["patterns"] for p in patterns[:5]], indent=2)

    try:
        ai_client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)
        response = ai_client.messages.create(
            model="claude-sonnet-4-20250514",
            max_tokens=500,
            messages=[{
                "role": "user",
                "content": (
                    "You are the Master AI evaluating whether an agent has sufficient understanding "
                    "of a user to represent them in job negotiations. Review these learned patterns:\n\n"
                    f"{patterns_summary}\n\n"
                    "Evaluate:\n"
                    "1. Does the agent understand the user's core values?\n"
                    "2. Has it identified hidden criteria (things the user won't say explicitly)?\n"
                    "3. Does it understand career goals and motivations?\n"
                    "4. Is there enough depth to negotiate on behalf of this person?\n\n"
                    "Return JSON: {\"certified\": true/false, \"confidence\": 0-100, "
                    "\"reasoning\": \"brief explanation\", \"gaps\": [\"missing areas if any\"]}"
                ),
            }],
        )

        text = response.content[0].text.strip()
        if text.startswith("```"):
            text = text.split("\n", 1)[1].rsplit("```", 1)[0]
        evaluation = json.loads(text)
    except (json.JSONDecodeError, IndexError):
        # If parsing fails, default to certified if patterns exist
        evaluation = {"certified": len(patterns) >= 2, "confidence": 60, "reasoning": "Fallback evaluation"}
    except Exception as e:
        raise HTTPException(status_code=503, detail=f"Certification evaluation failed: {type(e).__name__}")

    if evaluation.get("certified"):
        # Advance to certified stage
        client.table("cv2_profiles").update({"stage": "certified"}).eq("user_id", request.user_id).execute()
        return {
            "status": "certified",
            "user_id": request.user_id,
            "confidence": evaluation.get("confidence", 0),
            "reasoning": evaluation.get("reasoning", ""),
        }
    else:
        return {
            "status": "not_certified",
            "user_id": request.user_id,
            "confidence": evaluation.get("confidence", 0),
            "reasoning": evaluation.get("reasoning", ""),
            "gaps": evaluation.get("gaps", []),
        }


# --- CONTROL CENTER ENDPOINTS ---

@router.get("/control-center")
async def get_control_center_dashboard():
    """Full Master AI Control Center dashboard data."""
    return await master_ai_control_center.get_full_dashboard()


@router.post("/control-center/cycle")
async def run_master_cycle():
    """Run a complete Master AI operational cycle."""
    return await master_ai_control_center.run_full_cycle()


@router.get("/control-center/strategic")
async def get_strategic_overview():
    """Strategic overview for platform leadership."""
    return await master_ai_control_center.get_strategic_overview()


@router.get("/control-center/rd")
async def get_rd_status():
    """R&D status - capabilities and improvements."""
    return await master_ai_control_center.get_rd_status()


# --- ANALYTICS ---

@router.get("/analytics/rankings")
async def get_agent_rankings():
    """Get agent performance rankings."""
    return await ai_analytics.get_agent_rankings()


@router.get("/analytics/behavior")
async def get_network_behavior():
    """Get network-wide behavior analysis."""
    return await ai_analytics.get_behavior_analysis()


@router.get("/analytics/behavior/{agent_id}")
async def get_agent_behavior(agent_id: str):
    """Get behavior analysis for a specific agent."""
    return await ai_analytics.get_behavior_analysis(agent_id)


@router.get("/analytics/data")
async def get_data_report():
    """Get data collection and coverage report."""
    return await ai_analytics.get_data_collection_report()


@router.get("/analytics/communication")
async def get_communication_analysis():
    """Get communication pattern analysis."""
    return await ai_analytics.get_communication_analysis()


@router.get("/analytics/deep-dive/{agent_id}")
async def get_agent_deep_dive(agent_id: str):
    """Deep dive into a specific agent."""
    return await master_ai_control_center.get_agent_deep_dive(agent_id)


# --- COSTS ---

@router.get("/costs")
async def get_costs(period: str = "today"):
    """Get cost summary for a period (today, week, month, all)."""
    return await cost_tracker.get_cost_summary(period)


@router.get("/costs/budget")
async def get_budget_status(monthly_budget: float = 100.0):
    """Get budget status and alerts."""
    return await cost_tracker.get_budget_status(monthly_budget)


@router.get("/costs/agent/{agent_id}")
async def get_agent_costs(agent_id: str):
    """Get cost breakdown for a specific agent."""
    return await cost_tracker.get_agent_costs(agent_id)


# --- TRAINING CENTER ---

@router.get("/training/queue")
async def get_training_queue():
    """Get list of agents needing training."""
    return await agent_training_center.get_training_queue()


@router.get("/training/diagnose/{agent_id}")
async def diagnose_agent(agent_id: str):
    """Diagnose why an agent is underperforming."""
    return await agent_training_center.diagnose_agent(agent_id)


@router.post("/training/run")
async def train_agent(request: TrainAgentRequest):
    """Run training for a specific agent."""
    if request.training_type == "correction":
        return await agent_training_center.run_correction_training(request.agent_id)
    elif request.training_type == "integrity":
        return await agent_training_center.run_integrity_reinforcement(request.agent_id)
    elif request.training_type == "full_retrain":
        return await agent_training_center.run_full_retrain(request.agent_id)
    else:
        raise HTTPException(status_code=400, detail=f"Unknown training type: {request.training_type}")


@router.post("/training/cycle")
async def run_training_cycle():
    """Run a full training cycle for all agents in queue."""
    return await agent_training_center.run_training_cycle()


# --- MARKET INTELLIGENCE ---

@router.get("/market/snapshot")
async def get_market_snapshot():
    """Get current market intelligence snapshot."""
    return await market_intelligence.get_market_snapshot()


@router.get("/market/industry/{industry}")
async def get_industry_report(industry: str):
    """Get detailed market report for an industry."""
    return await market_intelligence.get_industry_report(industry)


@router.get("/market/trends")
async def get_hiring_trends():
    """Get hiring trend analysis."""
    return await market_intelligence.get_hiring_trends()


@router.get("/market/strategic-brief")
async def get_strategic_brief():
    """Get AI-synthesized strategic brief."""
    return await market_intelligence.synthesize_strategic_brief()


@router.post("/market/ingest")
async def ingest_market_data(request: MarketDataRequest):
    """Ingest external market data from 3rd party sources."""
    return await market_intelligence.ingest_market_data(request.source, request.data)


# --- AI COUNCIL ---

@router.post("/council/convene")
async def convene_council(request: CouncilRequest):
    """Convene the AI council for a strategic deliberation."""
    return await ai_council.convene(
        topic=request.topic,
        context=request.context or {},
        members=request.members,
    )


@router.post("/council/consult")
async def consult_council(request: CouncilRequest):
    """Quick consultation with the platform council."""
    return await master_ai_control_center.consult_council(
        topic=request.topic,
        context=request.context,
    )


@router.post("/council/review")
async def council_review_decision(request: CouncilRequest):
    """Have the council review a decision."""
    return await ai_council.review_decision(
        decision=request.topic,
        rationale=json.dumps(request.context or {}),
    )


# --- MARKETING DEPARTMENT ---

@router.get("/marketing/dashboard")
async def get_marketing_dashboard():
    """Get marketing department dashboard with all campaign data."""
    return await campaign_manager.get_marketing_dashboard()


@router.get("/marketing/gaps")
async def analyze_platform_gaps():
    """Analyze platform gaps to identify recruitment targets."""
    return await marketing_ai_agent.analyze_platform_gaps()


@router.post("/marketing/propose")
async def propose_campaign():
    """Marketing AI proposes a new campaign based on gap analysis."""
    gap_analysis = await marketing_ai_agent.analyze_platform_gaps()
    return await marketing_ai_agent.propose_campaign(gap_analysis)


@router.post("/marketing/review/{campaign_id}")
async def review_campaign(campaign_id: str):
    """Master AI reviews a campaign proposal."""
    return await campaign_manager.master_review_campaign(campaign_id)


@router.post("/marketing/approve")
async def approve_campaign(request: CampaignApproveRequest):
    """Master AI manually approves a campaign."""
    return await campaign_manager.approve_campaign(request.campaign_id, request.budget_override)


@router.post("/marketing/reject")
async def reject_campaign(request: CampaignActionRequest):
    """Master AI rejects a campaign."""
    return await campaign_manager.reject_campaign(request.campaign_id, request.reason)


@router.post("/marketing/content/{campaign_id}")
async def generate_campaign_content(campaign_id: str):
    """Generate all content for an approved campaign."""
    return await marketing_ai_agent.generate_campaign_content(campaign_id)


@router.post("/marketing/landing-page/{campaign_id}")
async def generate_landing_page(campaign_id: str):
    """Generate a landing page for a campaign."""
    return await marketing_ai_agent.generate_landing_page(campaign_id)


@router.post("/marketing/justify/{campaign_id}")
async def justify_budget(campaign_id: str):
    """Marketing AI justifies budget spending to Master AI."""
    return await marketing_ai_agent.justify_budget(campaign_id)


@router.post("/marketing/activate")
async def activate_campaign(request: CampaignActionRequest):
    """Activate an approved campaign (start running it)."""
    return await campaign_manager.activate_campaign(request.campaign_id)


@router.post("/marketing/pause")
async def pause_campaign(request: CampaignActionRequest):
    """Pause an active campaign."""
    return await campaign_manager.pause_campaign(request.campaign_id, request.reason)


@router.post("/marketing/terminate")
async def terminate_campaign(request: CampaignActionRequest):
    """Master AI terminates a campaign permanently."""
    return await campaign_manager.terminate_campaign(request.campaign_id, request.reason)


@router.post("/marketing/metrics")
async def record_campaign_metrics(request: CampaignMetricsRequest):
    """Record performance metrics for an active campaign."""
    return await campaign_manager.record_metrics(request.campaign_id, request.metrics)


@router.get("/marketing/campaigns")
async def get_all_campaigns(status: Optional[str] = None):
    """Get all campaigns, optionally filtered by status."""
    return await campaign_manager.get_all_campaigns(status)


@router.get("/marketing/report")
async def get_marketing_report():
    """Full marketing AI report to Master AI."""
    return await marketing_ai_agent.report_to_master()
