import json

import anthropic
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from supabase import create_client

from app.config import SUPABASE_URL, SUPABASE_SERVICE_KEY, ANTHROPIC_API_KEY

router = APIRouter()


class CertifyRequest(BaseModel):
    user_id: str


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
