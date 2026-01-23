from fastapi import APIRouter, HTTPException

from app.services.a2a_engine import a2a_engine

router = APIRouter()


@router.post("/run-matching")
async def run_matching():
    result = await a2a_engine.run_matching()
    return result


@router.get("/status")
async def get_status():
    return await a2a_engine.get_status()


@router.get("/match/{match_id}")
async def get_match(match_id: str):
    match = await a2a_engine.get_match(match_id)
    if not match:
        raise HTTPException(status_code=404, detail="Match not found")
    return match
