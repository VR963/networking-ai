from typing import Optional

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from app.services.test_opportunities import test_opportunities

router = APIRouter()


class GenerateRequest(BaseModel):
    user_id: str


class ResponseRequest(BaseModel):
    user_id: str
    opportunity_index: int
    accepted: bool
    rejection_reason: Optional[str] = None


@router.post("/generate")
async def generate_opportunities(request: GenerateRequest):
    opportunities = await test_opportunities.generate_test_opportunities(request.user_id)
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
    result = await test_opportunities.record_response(
        user_id=request.user_id,
        opportunity_index=request.opportunity_index,
        accepted=request.accepted,
        rejection_reason=request.rejection_reason,
    )
    return result


@router.get("/status/{user_id}")
async def calibration_status(user_id: str):
    return await test_opportunities.get_calibration_status(user_id)
