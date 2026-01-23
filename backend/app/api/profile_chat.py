from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

import anthropic
from supabase import create_client

from app.config import ANTHROPIC_API_KEY, QUALITY_THRESHOLD, SUPABASE_URL, SUPABASE_SERVICE_KEY
from app.services.conversation_logger import conversation_logger
from app.services.quality_analyzer import quality_analyzer
from app.services.dspy_learning import dspy_learning
from app.services.ai_agent_knowledge_base import ai_agent_knowledge_base

router = APIRouter()


class ChatRequest(BaseModel):
    user_id: str
    messages: list[dict]
    context: dict = {}


class ChatResponse(BaseModel):
    response: str
    conversation_id: str | None = None
    learning_triggered: bool = False


@router.post("/message", response_model=ChatResponse)
async def chat_message(request: ChatRequest):
    if not ANTHROPIC_API_KEY:
        raise HTTPException(status_code=503, detail="ANTHROPIC_API_KEY environment variable is required")

    # Ensure user profile exists (creates on first chat)
    await _ensure_profile(request.user_id, request.context.get("industry", "general"))

    # Build enriched context from knowledge base and learned patterns
    agent_context = {}
    user_patterns = []
    try:
        agent_context = await ai_agent_knowledge_base.build_agent_context(request.user_id)
        user_patterns = await dspy_learning.get_user_patterns(request.user_id)
    except Exception:
        pass  # Non-critical: proceed with base prompt if knowledge unavailable

    try:
        client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)

        system_prompt = _build_system_prompt(request.context, agent_context, user_patterns)

        api_messages = [
            {"role": m["role"], "content": m["content"]}
            for m in request.messages
        ]

        response = client.messages.create(
            model="claude-sonnet-4-20250514",
            max_tokens=1000,
            system=system_prompt,
            messages=api_messages,
        )

        ai_response = response.content[0].text
    except TypeError as e:
        raise HTTPException(status_code=503, detail="API credentials not configured. Set ANTHROPIC_API_KEY.")
    except anthropic.AuthenticationError:
        raise HTTPException(status_code=503, detail="Invalid ANTHROPIC_API_KEY")

    # --- DSPy Learning Pipeline (Connected) ---
    full_messages = request.messages + [{"role": "assistant", "content": ai_response}]

    try:
        conversation_id = await conversation_logger.log_conversation(
            request.user_id, full_messages, metadata=request.context
        )

        quality_score = await quality_analyzer.analyze(conversation_id)

        learning_triggered = False
        if quality_score >= QUALITY_THRESHOLD:
            await dspy_learning.learn_from_conversation(conversation_id)
            learning_triggered = True
    except Exception:
        # Learning pipeline failure should not block chat response
        conversation_id = None
        learning_triggered = False
    # --- End Learning Pipeline ---

    return ChatResponse(
        response=ai_response,
        conversation_id=conversation_id,
        learning_triggered=learning_triggered,
    )


def _build_system_prompt(
    context: dict,
    agent_context: dict = None,
    user_patterns: list = None,
) -> str:
    base = (
        "You are an AI career agent conducting a deep onboarding conversation. "
        "Your goal is to understand this person deeply - their values, goals, "
        "fears, hidden criteria, and what truly matters to them professionally. "
        "Ask thoughtful follow-up questions. Listen for what they don't say explicitly."
    )

    # Inject industry expertise from knowledge base
    industry = context.get("industry") or (agent_context or {}).get("industry")
    if industry and industry != "general":
        base += f"\n\nThe user works in {industry}."
        knowledge = (agent_context or {}).get("knowledge", {})
        if knowledge.get("skill_benchmarks"):
            base += f" Skill levels in this field: {', '.join(f'{k}: {v}' for k, v in list(knowledge['skill_benchmarks'].items())[:3])}."
        if knowledge.get("hidden_criteria"):
            base += f" Industry insight: {'; '.join(knowledge['hidden_criteria'][:2])}."
        base += " Apply this expertise to ask relevant probing questions."

    # Inject previously learned patterns about this user
    if user_patterns:
        latest = user_patterns[0] if user_patterns else {}
        pattern_notes = []
        if latest.get("values"):
            pattern_notes.append(f"Known values: {', '.join(latest['values'][:3])}")
        if latest.get("hidden_criteria"):
            pattern_notes.append(f"Hidden preferences: {', '.join(latest['hidden_criteria'][:2])}")
        if latest.get("goals"):
            pattern_notes.append(f"Goals: {', '.join(latest['goals'][:2])}")
        if pattern_notes:
            base += (
                "\n\nYou already know the following about this user from previous conversations:\n- "
                + "\n- ".join(pattern_notes)
                + "\nBuild on this knowledge. Don't re-ask what you already know. Go deeper."
            )

    if context.get("stage") == "calibration":
        base += (
            "\n\nYou are in calibration mode. The user just rejected a test opportunity. "
            "Gently explore what didn't feel right. Listen for hidden criteria."
        )

    return base


async def _ensure_profile(user_id: str, industry: str = "general") -> None:
    """Create user profile on first chat if it doesn't exist.

    This bridges the gap: chat is the entry point, and all downstream
    services (calibration, A2A matching) depend on cv2_profiles existing.
    """
    if not SUPABASE_URL or not SUPABASE_SERVICE_KEY:
        return  # Skip if DB not configured

    try:
        client = create_client(SUPABASE_URL, SUPABASE_SERVICE_KEY)

        existing = (
            client.table("cv2_profiles")
            .select("user_id")
            .eq("user_id", user_id)
            .execute()
        )
        if existing.data:
            # Update industry if provided and different
            if industry and industry != "general":
                client.table("cv2_profiles").update({"industry": industry}).eq("user_id", user_id).execute()
            return

        # Create new profile
        client.table("cv2_profiles").insert({
            "user_id": user_id,
            "industry": industry or "general",
            "summary": "",
            "stage": "onboarding",
        }).execute()

        # Ensure user exists in cv2_users
        client.table("cv2_users").upsert({"id": user_id}).execute()
    except Exception:
        pass  # Profile creation failure should not block chat
