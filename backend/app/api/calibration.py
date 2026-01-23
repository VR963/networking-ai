from typing import Optional

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from supabase import create_client

from app.config import SUPABASE_URL, SUPABASE_SERVICE_KEY
from app.services.test_opportunities import test_opportunities

router = APIRouter()


class GenerateRequest(BaseModel):
    user_id: str


class ResponseRequest(BaseModel):
    user_id: str
    opportunity_index: int
    accepted: bool
    rejection_reason: Optional[str] = None


def _advance_to_calibration(user_id: str):
    """Advance user stage to 'calibration' when they start generating test opportunities."""
    if not SUPABASE_URL or not SUPABASE_SERVICE_KEY:
        return
    try:
        client = create_client(SUPABASE_URL, SUPABASE_SERVICE_KEY)
        result = (
            client.table("cv2_profiles")
            .select("stage")
            .eq("user_id", user_id)
            .execute()
        )
        if result.data and result.data[0].get("stage") == "onboarding":
            client.table("cv2_profiles").update({"stage": "calibration"}).eq("user_id", user_id).execute()
    except Exception:
        pass  # Stage advancement is non-critical


def _handle_service_error(e: Exception):
    error_msg = str(e).lower()
    if "supabase_url" in error_msg or "supabase" in type(e).__name__.lower():
        raise HTTPException(status_code=503, detail="Database not configured. Set SUPABASE_URL and SUPABASE_SERVICE_KEY.")
    raise HTTPException(status_code=500, detail=f"Service error: {type(e).__name__}")


@router.post("/generate")
async def generate_opportunities(request: GenerateRequest):
    # Advance user stage to calibration
    _advance_to_calibration(request.user_id)

    try:
        opportunities = await test_opportunities.generate_test_opportunities(request.user_id)
    except Exception as e:
        _handle_service_error(e)
    if not opportunities:
        raise HTTPException(status_code=404, detail="Could not generate opportunities. User profile not found.")
    # Strip hidden fields before returning to user
    visible = [
        {
            "index": i,
            "title": opp.get("title", ""),
            "company": opp.get("company", ""),
            "description": opp.get("description", ""),
            "salary_range": opp.get("salary_range", ""),
        }
        for i, opp in enumerate(opportunities)
    ]
    return {"opportunities": visible}


@router.post("/respond")
async def respond_to_opportunity(request: ResponseRequest):
    try:
        result = await test_opportunities.record_response(
            user_id=request.user_id,
            opportunity_index=request.opportunity_index,
            accepted=request.accepted,
            rejection_reason=request.rejection_reason,
        )
        return result
    except Exception as e:
        _handle_service_error(e)


@router.get("/status/{user_id}")
async def calibration_status(user_id: str):
    try:
        return await test_opportunities.get_calibration_status(user_id)
    except Exception as e:
        _handle_service_error(e)
