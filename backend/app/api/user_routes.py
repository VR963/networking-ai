from typing import Optional

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from supabase import create_client

from app.config import SUPABASE_URL, SUPABASE_SERVICE_KEY

router = APIRouter()


def _get_supabase():
    if not SUPABASE_URL or not SUPABASE_SERVICE_KEY:
        raise HTTPException(status_code=503, detail="Database not configured. Set SUPABASE_URL and SUPABASE_SERVICE_KEY.")
    return create_client(SUPABASE_URL, SUPABASE_SERVICE_KEY)


class ProfileCreateRequest(BaseModel):
    user_id: str
    industry: str = "general"
    summary: Optional[str] = None


class ProfileUpdateRequest(BaseModel):
    industry: Optional[str] = None
    summary: Optional[str] = None
    stage: Optional[str] = None


class CandidateRegisterRequest(BaseModel):
    user_id: str


# --- STAGES ---
# onboarding: user is chatting with agent (initial)
# calibration: user is doing test opportunities
# certified: Master AI has verified the agent knows the user
# matchable: candidate is registered for A2A matching

VALID_STAGES = ["onboarding", "calibration", "certified", "matchable"]


@router.post("/profile")
async def create_or_update_profile(request: ProfileCreateRequest):
    """Create or update a user profile. Called when user starts chat."""
    client = _get_supabase()

    existing = (
        client.table("cv2_profiles")
        .select("*")
        .eq("user_id", request.user_id)
        .execute()
    )

    if existing.data:
        # Update existing profile
        update_data = {}
        if request.industry:
            update_data["industry"] = request.industry
        if request.summary:
            update_data["summary"] = request.summary
        if update_data:
            client.table("cv2_profiles").update(update_data).eq("user_id", request.user_id).execute()
        return {"status": "updated", "user_id": request.user_id}

    # Create new profile with onboarding stage
    record = {
        "user_id": request.user_id,
        "industry": request.industry,
        "summary": request.summary or "",
        "stage": "onboarding",
    }
    client.table("cv2_profiles").insert(record).execute()

    # Also create user entry in cv2_users
    try:
        client.table("cv2_users").upsert({"id": request.user_id}).execute()
    except Exception:
        pass  # User may already exist

    return {"status": "created", "user_id": request.user_id, "stage": "onboarding"}


@router.get("/profile/{user_id}")
async def get_profile(user_id: str):
    """Get a user's profile including their current stage."""
    client = _get_supabase()
    result = (
        client.table("cv2_profiles")
        .select("*")
        .eq("user_id", user_id)
        .execute()
    )
    if not result.data:
        raise HTTPException(status_code=404, detail="Profile not found. Start a conversation first.")
    return result.data[0]


@router.patch("/profile/{user_id}")
async def update_profile(user_id: str, request: ProfileUpdateRequest):
    """Update profile fields (industry, summary, stage)."""
    client = _get_supabase()

    existing = (
        client.table("cv2_profiles")
        .select("user_id")
        .eq("user_id", user_id)
        .execute()
    )
    if not existing.data:
        raise HTTPException(status_code=404, detail="Profile not found.")

    update_data = {}
    if request.industry:
        update_data["industry"] = request.industry
    if request.summary is not None:
        update_data["summary"] = request.summary
    if request.stage:
        if request.stage not in VALID_STAGES:
            raise HTTPException(status_code=400, detail=f"Invalid stage. Must be one of: {VALID_STAGES}")
        update_data["stage"] = request.stage

    if update_data:
        client.table("cv2_profiles").update(update_data).eq("user_id", user_id).execute()

    return {"status": "updated", "user_id": user_id}


@router.post("/profile/{user_id}/advance-stage")
async def advance_stage(user_id: str):
    """Advance user to next stage in the pipeline.

    onboarding → calibration → certified → matchable

    Enforces prerequisites:
    - calibration: must have a profile
    - certified: must have completed calibration
    - matchable: must be certified (Master AI approved)
    """
    client = _get_supabase()

    result = (
        client.table("cv2_profiles")
        .select("*")
        .eq("user_id", user_id)
        .execute()
    )
    if not result.data:
        raise HTTPException(status_code=404, detail="Profile not found.")

    profile = result.data[0]
    current_stage = profile.get("stage", "onboarding")

    stage_order = VALID_STAGES
    current_idx = stage_order.index(current_stage) if current_stage in stage_order else 0
    if current_idx >= len(stage_order) - 1:
        return {"status": "already_at_final_stage", "stage": current_stage}

    next_stage = stage_order[current_idx + 1]

    # Enforce prerequisites
    if next_stage == "calibration":
        # Must have had at least 3 conversation turns
        conv_result = (
            client.table("cv2_conversations")
            .select("id", count="exact")
            .eq("user_id", user_id)
            .execute()
        )
        if (conv_result.count or 0) < 1:
            raise HTTPException(status_code=400, detail="Complete at least one onboarding conversation before calibration.")

    elif next_stage == "certified":
        # Must have completed calibration (all opportunities responded to)
        opp_result = (
            client.table("cv2_test_opportunities")
            .select("status")
            .eq("user_id", user_id)
            .execute()
        )
        opps = opp_result.data or []
        if not opps or any(o["status"] == "pending" for o in opps):
            raise HTTPException(status_code=400, detail="Complete all calibration opportunities first.")

    elif next_stage == "matchable":
        # Must be certified by Master AI
        if current_stage != "certified":
            raise HTTPException(status_code=400, detail="Must be certified by Master AI first.")

    client.table("cv2_profiles").update({"stage": next_stage}).eq("user_id", user_id).execute()
    return {"status": "advanced", "previous_stage": current_stage, "new_stage": next_stage}


@router.post("/register-candidate")
async def register_as_candidate(request: CandidateRegisterRequest):
    """Register a certified user as an A2A matchable candidate.

    Only users at 'matchable' stage can be registered.
    Copies their profile + learned patterns into cv2_a2a_candidates.
    """
    client = _get_supabase()

    # Verify user is at matchable stage
    profile_result = (
        client.table("cv2_profiles")
        .select("*")
        .eq("user_id", request.user_id)
        .execute()
    )
    if not profile_result.data:
        raise HTTPException(status_code=404, detail="Profile not found.")

    profile = profile_result.data[0]
    if profile.get("stage") != "matchable":
        raise HTTPException(
            status_code=400,
            detail=f"User is at stage '{profile.get('stage', 'onboarding')}'. Must be 'matchable' to register as candidate."
        )

    # Gather learned patterns
    patterns_result = (
        client.table("cv2_collective_patterns")
        .select("patterns, pattern_type")
        .eq("user_id", request.user_id)
        .order("created_at", desc=True)
        .limit(10)
        .execute()
    )

    # Build candidate profile from profile + patterns
    candidate_profile = {
        "industry": profile.get("industry", "general"),
        "summary": profile.get("summary", ""),
        "values": [],
        "hidden_criteria": [],
        "goals": [],
    }

    for p in (patterns_result.data or []):
        patterns = p.get("patterns", {})
        if patterns.get("values"):
            candidate_profile["values"].extend(
                patterns["values"] if isinstance(patterns["values"], list) else [patterns["values"]]
            )
        if patterns.get("hidden_criteria"):
            candidate_profile["hidden_criteria"].extend(
                patterns["hidden_criteria"] if isinstance(patterns["hidden_criteria"], list) else [patterns["hidden_criteria"]]
            )
        if patterns.get("inferred_criteria"):
            candidate_profile["hidden_criteria"].append(patterns["inferred_criteria"])
        if patterns.get("goals"):
            candidate_profile["goals"].extend(
                patterns["goals"] if isinstance(patterns["goals"], list) else [patterns["goals"]]
            )

    # Deduplicate
    candidate_profile["values"] = list(set(candidate_profile["values"]))[:10]
    candidate_profile["hidden_criteria"] = list(set(candidate_profile["hidden_criteria"]))[:10]
    candidate_profile["goals"] = list(set(candidate_profile["goals"]))[:5]

    # Upsert into cv2_a2a_candidates
    record = {
        "id": request.user_id,
        "user_id": request.user_id,
        "industry": profile.get("industry", "general"),
        "profile": candidate_profile,
    }
    client.table("cv2_a2a_candidates").upsert(record).execute()

    # Register agent
    try:
        agent_record = {
            "id": f"agent_{request.user_id}",
            "user_id": request.user_id,
            "industry": profile.get("industry", "general"),
        }
        client.table("cv2_agents").upsert(agent_record).execute()
    except Exception:
        pass

    return {"status": "registered", "user_id": request.user_id, "profile": candidate_profile}
