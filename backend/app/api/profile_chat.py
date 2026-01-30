from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

import anthropic
from app.config import ANTHROPIC_API_KEY, QUALITY_THRESHOLD
from app.database import get_db
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
    quality_score: float = 0.0
    conversation_count: int = 0
    profile_readiness: int = 0


@router.post("/message", response_model=ChatResponse)
async def chat_message(request: ChatRequest):
    if not ANTHROPIC_API_KEY:
        raise HTTPException(status_code=503, detail="ANTHROPIC_API_KEY environment variable is required")

    # Ensure user profile exists (creates on first chat)
    await _ensure_profile(request.user_id, request.context.get("industry", "general"))

    # Build enriched context from knowledge base and learned patterns
    agent_context = {}
    user_patterns = []
    pre_conversation_context = ""
    try:
        agent_context = await ai_agent_knowledge_base.build_agent_context(request.user_id)
        user_patterns = await dspy_learning.get_user_patterns(request.user_id)
    except Exception:
        pass  # Non-critical: proceed with base prompt if knowledge unavailable

    # Fetch pre-conversation context from uploaded documents/social profiles
    try:
        from app.services.profile_analyzer import profile_analyzer
        db_client = get_db()

        # Use RPCs to bypass RLS
        try:
            profile_data = db_client.rpc("get_cv2_profile", {"p_user_id": request.user_id}).execute()
        except Exception:
            profile_data = (
                db_client.table("cv2_profiles")
                .select("social_analysis")
                .eq("user_id", request.user_id)
                .execute()
            )
        try:
            docs_data = db_client.rpc("get_user_documents", {"p_user_id": request.user_id}).execute()
        except Exception:
            docs_data = (
                db_client.table("cv2_documents")
                .select("filename, doc_type, analysis")
                .eq("user_id", request.user_id)
                .execute()
            )

        cv_analysis = None
        documents = []
        for doc in (docs_data.data or []):
            documents.append({"filename": doc.get("filename", ""), "doc_type": doc.get("doc_type", "")})
            if doc.get("analysis") and doc.get("doc_type") == "cv":
                cv_analysis = doc["analysis"]

        social_analysis = (profile_data.data[0].get("social_analysis") if profile_data.data else None)

        if cv_analysis or social_analysis or documents:
            pre_conversation_context = await profile_analyzer.build_pre_conversation_context(
                cv_analysis=cv_analysis,
                social_analysis=social_analysis,
                documents=documents if documents else None,
            )
    except Exception:
        pass  # Pre-conversation context is non-critical

    # RAG: Retrieve semantically relevant past context
    rag_context = ""
    try:
        from app.services.embedding_store import embedding_store
        last_message = next(
            (m["content"] for m in reversed(request.messages) if m.get("role") == "user"),
            "",
        )
        if last_message:
            rag_context = await embedding_store.get_context_for_agent(
                agent_id=request.user_id,
                query=last_message,
            )
    except Exception:
        pass  # RAG is non-critical enhancement

    try:
        client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)

        system_prompt = _build_system_prompt(
            request.context, agent_context, user_patterns,
            pre_conversation_context, rag_context,
        )

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

    quality_score = 0.0
    conversation_count = 0
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

    # Calculate profile readiness and conversation count
    try:
        db = get_db()
        conv_result = db.rpc("get_user_conversation_count", {"p_user_id": request.user_id}).execute()
        conversation_count = conv_result.data[0]["count"] if conv_result.data else 0
    except Exception:
        try:
            db = get_db()
            conv_result = (
                db.table("cv2_conversations")
                .select("id", count="exact")
                .eq("user_id", request.user_id)
                .execute()
            )
            conversation_count = conv_result.count or 0
        except Exception:
            pass

    profile_readiness = _calculate_readiness(
        has_cv=bool(pre_conversation_context),
        has_patterns=bool(user_patterns),
        conversation_count=conversation_count,
        quality_score=quality_score,
        learning_triggered=learning_triggered,
    )

    return ChatResponse(
        response=ai_response,
        conversation_id=conversation_id,
        learning_triggered=learning_triggered,
        quality_score=round(quality_score, 1),
        conversation_count=conversation_count,
        profile_readiness=profile_readiness,
    )


def _build_system_prompt(
    context: dict,
    agent_context: dict = None,
    user_patterns: list = None,
    pre_conversation_context: str = "",
    rag_context: str = "",
) -> str:
    base = (
        "You are an AI career agent conducting a deep onboarding conversation. "
        "Your goal is to understand this person deeply - their values, goals, "
        "fears, hidden criteria, and what truly matters to them professionally. "
        "Ask thoughtful follow-up questions. Listen for what they don't say explicitly.\n\n"
        "COMMUNICATION STYLE:\n"
        "- Write in clear, well-spaced paragraphs. Use double line breaks between paragraphs.\n"
        "- Keep each paragraph focused on one idea — short and easy to read.\n"
        "- Be warm, conversational, and human. Write like a thoughtful friend, not a corporate chatbot.\n"
        "- Ask ONE or TWO focused questions at a time, not five. Let the conversation breathe.\n"
        "- Keep responses concise — 3 to 5 short paragraphs maximum.\n"
        "- When reflecting back what the user said, keep it brief — one sentence, then go deeper.\n"
        "- Never use bullet points or numbered lists. Write in natural flowing prose."
    )

    # Inject pre-conversation context from uploaded documents/social profiles
    if pre_conversation_context:
        base += f"\n\n{pre_conversation_context}"

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

    # Inject RAG-retrieved context from past interactions
    if rag_context:
        base += f"\n\nRelevant context from previous interactions:\n{rag_context}"

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
    try:
        client = get_db()
        if not client:
            return

        # Use RPC to bypass RLS (single call creates both user + profile)
        try:
            client.rpc("ensure_cv2_profile", {
                "uid": user_id,
                "p_industry": industry or "general",
            }).execute()
            return
        except Exception:
            pass  # RPC not available, try direct approach

        existing = (
            client.table("cv2_profiles")
            .select("user_id")
            .eq("user_id", user_id)
            .execute()
        )
        if existing.data:
            if industry and industry != "general":
                client.table("cv2_profiles").update({"industry": industry}).eq("user_id", user_id).execute()
            return

        try:
            client.rpc("ensure_cv2_user", {"uid": user_id}).execute()
        except Exception:
            try:
                client.table("cv2_users").insert({"id": user_id}).execute()
            except Exception:
                pass

        client.table("cv2_profiles").insert({
            "user_id": user_id,
            "industry": industry or "general",
            "summary": "",
            "stage": "onboarding",
        }).execute()
    except Exception:
        pass  # Profile creation failure should not block chat


def _calculate_readiness(
    has_cv: bool, has_patterns: bool, conversation_count: int,
    quality_score: float, learning_triggered: bool,
) -> int:
    """Calculate profile readiness percentage (0-100)."""
    score = 0
    if has_cv:
        score += 30  # CV uploaded and analyzed
    score += min(conversation_count * 10, 30)  # Up to 30 for conversations
    if has_patterns:
        score += 15  # Patterns learned
    if quality_score >= 7.0:
        score += 15  # High quality conversation
    if learning_triggered:
        score += 10  # Learning pipeline fired
    return min(score, 100)


@router.get("/history/{user_id}")
async def get_conversation_history(user_id: str):
    """Get past conversation summaries for a user."""
    db = get_db()
    if not db:
        return {"conversations": []}
    try:
        result = db.rpc("get_user_conversations", {"p_user_id": user_id}).execute()
        return {"conversations": result.data or []}
    except Exception:
        try:
            result = (
                db.table("cv2_conversations")
                .select("id, messages, quality_score, created_at")
                .eq("user_id", user_id)
                .order("created_at", desc=True)
                .limit(20)
                .execute()
            )
            return {"conversations": result.data or []}
        except Exception:
            return {"conversations": []}
