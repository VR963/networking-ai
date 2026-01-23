from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

import anthropic

from app.config import ANTHROPIC_API_KEY, QUALITY_THRESHOLD
from app.services.conversation_logger import conversation_logger
from app.services.quality_analyzer import quality_analyzer
from app.services.dspy_learning import dspy_learning

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
    client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)

    system_prompt = _build_system_prompt(request.context)

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

    # --- DSPy Learning Pipeline (Connected) ---
    full_messages = request.messages + [{"role": "assistant", "content": ai_response}]

    conversation_id = await conversation_logger.log_conversation(
        request.user_id, full_messages, metadata=request.context
    )

    quality_score = await quality_analyzer.analyze(conversation_id)

    learning_triggered = False
    if quality_score >= QUALITY_THRESHOLD:
        await dspy_learning.learn_from_conversation(conversation_id)
        learning_triggered = True
    # --- End Learning Pipeline ---

    return ChatResponse(
        response=ai_response,
        conversation_id=conversation_id,
        learning_triggered=learning_triggered,
    )


def _build_system_prompt(context: dict) -> str:
    base = (
        "You are an AI career agent conducting a deep onboarding conversation. "
        "Your goal is to understand this person deeply - their values, goals, "
        "fears, hidden criteria, and what truly matters to them professionally. "
        "Ask thoughtful follow-up questions. Listen for what they don't say explicitly."
    )

    if context.get("industry"):
        base += f"\n\nThe user works in {context['industry']}. "
        base += "Apply your industry expertise to ask relevant probing questions."

    if context.get("stage") == "calibration":
        base += (
            "\n\nYou are in calibration mode. The user just rejected a test opportunity. "
            "Gently explore what didn't feel right. Listen for hidden criteria."
        )

    return base
