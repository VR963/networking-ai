from fastapi import APIRouter

from supabase import create_client

from app.config import SUPABASE_URL, SUPABASE_SERVICE_KEY

router = APIRouter()


def _get_supabase():
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
