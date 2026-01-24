"""Network API Routes - Exposes the AI networking space.

Endpoints:
- POST /network/cycle          - Run a matching cycle (discover + negotiate)
- POST /network/activate       - Trigger matching for a newly activated agent
- POST /network/feedback       - Record human accept/reject of a match
- GET  /network/health         - Network health report
- GET  /network/activity       - Recent network events
- GET  /network/agent/{id}     - Agent stats and history
- GET  /network/matches/{uid}  - User's matches
- POST /network/governance     - Run governance cycle
- POST /network/intervene      - Master AI intervention
- GET  /network/intelligence/{industry} - Industry insights
"""

from typing import Optional

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from app.database import get_db

from app.services.network_events import network_events
from app.services.network_discovery import network_discovery
from app.services.network_learning import network_learning
from app.services.master_ai_governance import master_ai_governance
from app.services.agent_memory import agent_memory

router = APIRouter()


def _get_supabase():
    client = get_db()
    if not client:
        raise HTTPException(status_code=503, detail="Database not configured.")
    return client


# --- Request Models ---

class ActivateRequest(BaseModel):
    agent_id: str
    agent_type: str  # "talent" or "hm"


class FeedbackRequest(BaseModel):
    agent_id: str
    match_id: str
    accepted: bool
    feedback: Optional[str] = None


class InterveneRequest(BaseModel):
    action: str  # suspend_agent, reactivate_agent, void_match, boost_priority
    target_id: str
    reason: str = ""


class PolicyRequest(BaseModel):
    min_reputation: Optional[int] = None
    match_quality_floor: Optional[int] = None
    max_negotiations_per_cycle: Optional[int] = None


# --- Network Operations ---

@router.post("/cycle")
async def run_network_cycle():
    """Run a full network matching cycle.

    Discovers compatible pairs, runs multi-round negotiations,
    stores matches, and triggers notifications.
    """
    result = await network_events.run_network_cycle()
    return result


@router.post("/activate")
async def trigger_agent_activation(request: ActivateRequest):
    """Handle a newly activated agent joining the network.

    Runs discovery + negotiation for the new agent against existing agents.
    """
    # First, Master AI approval
    approval = await master_ai_governance.approve_agent_activation(request.agent_id)
    if not approval.get("approved"):
        return {
            "status": "not_approved",
            "reason": approval.get("reason", ""),
            "issues": approval.get("issues", []),
        }

    # Then trigger matching
    result = await network_events.on_agent_activated(
        agent_id=request.agent_id,
        agent_type=request.agent_type,
    )
    return result


@router.post("/feedback")
async def record_human_feedback(request: FeedbackRequest):
    """Record when a human accepts or rejects a match.

    This is the most important learning signal in the network.
    Updates agent reputation and triggers learning if rejected.
    """
    result = await network_events.on_human_feedback(
        agent_id=request.agent_id,
        match_id=request.match_id,
        accepted=request.accepted,
        feedback=request.feedback,
    )

    # Check if agent needs review after rejection
    if not request.accepted:
        history = await agent_memory.get_agent_history(request.agent_id)
        if history.get("human_rejected", 0) >= 3:
            review = await master_ai_governance.review_agent_performance(request.agent_id)
            result["agent_review"] = review

    return result


# --- Network Info ---

@router.get("/health")
async def get_network_health():
    """Get comprehensive network health report."""
    return await master_ai_governance.get_network_health()


@router.get("/activity")
async def get_network_activity():
    """Get recent network events."""
    events = await network_events.get_network_activity(limit=30)
    return {"events": events}


@router.get("/stats")
async def get_network_stats():
    """Get basic network statistics."""
    return await network_discovery.get_network_stats()


@router.get("/agent/{agent_id}")
async def get_agent_info(agent_id: str):
    """Get agent's history, reputation, and stats."""
    client = _get_supabase()

    # Agent data
    agent = (
        client.table("cv2_agents")
        .select("*")
        .eq("id", agent_id)
        .execute()
    )
    if not agent.data:
        raise HTTPException(status_code=404, detail="Agent not found")

    # History and reputation
    history = await agent_memory.get_agent_history(agent_id)
    rejections = await agent_memory.get_rejection_patterns(agent_id)

    return {
        "agent": agent.data[0],
        "history": history,
        "rejection_patterns": rejections,
    }


@router.get("/matches/{user_id}")
async def get_user_matches(user_id: str):
    """Get all matches for a user (both as talent and as HM)."""
    client = _get_supabase()

    # As talent
    talent_matches = (
        client.table("cv2_a2a_matches")
        .select("*")
        .eq("candidate_id", user_id)
        .order("created_at", desc=True)
        .execute()
    )

    # As HM (need to find their jobs first)
    jobs = (
        client.table("cv2_jobs")
        .select("id")
        .eq("user_id", user_id)
        .execute()
    )
    hm_matches = []
    for job in (jobs.data or []):
        matches = (
            client.table("cv2_a2a_matches")
            .select("*")
            .eq("job_id", job["id"])
            .order("created_at", desc=True)
            .execute()
        )
        hm_matches.extend(matches.data or [])

    return {
        "as_talent": talent_matches.data or [],
        "as_hm": hm_matches,
    }


# --- Governance ---

@router.post("/governance")
async def run_governance_cycle():
    """Run Master AI governance cycle.

    Reviews at-risk agents, checks network balance,
    synthesizes intelligence, adjusts policies.
    """
    return await master_ai_governance.run_governance_cycle()


@router.post("/intervene")
async def master_ai_intervene(request: InterveneRequest):
    """Master AI manual intervention."""
    return await master_ai_governance.intervene(
        action=request.action,
        target_id=request.target_id,
        reason=request.reason,
    )


@router.post("/policy")
async def update_network_policy(request: PolicyRequest):
    """Update network governance policies."""
    updates = {}
    if request.min_reputation is not None:
        updates["min_reputation"] = request.min_reputation
    if request.match_quality_floor is not None:
        updates["match_quality_floor"] = request.match_quality_floor
    if request.max_negotiations_per_cycle is not None:
        updates["max_negotiations_per_cycle"] = request.max_negotiations_per_cycle

    if not updates:
        return {"status": "no_changes"}

    return await master_ai_governance.set_network_policy(updates)


# --- Intelligence ---

@router.get("/intelligence/{industry}")
async def get_industry_intelligence(industry: str):
    """Get aggregated intelligence for an industry."""
    return await network_learning.get_industry_intelligence(industry)


@router.get("/intelligence")
async def get_network_intelligence():
    """Get network-wide intelligence synthesis."""
    return await network_learning.synthesize_network_intelligence()
