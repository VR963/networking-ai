from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
import json

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
    onboarding_topics: dict = {}  # {topic: bool} - which topics have been covered


# =============================================================================
# 6-CATEGORY ONBOARDING METHODOLOGY
# Based on professional recruiter discovery methodology + psychometric principles
# Each category has: label, description, example_questions (CV-contextual),
# behavioral_probes, what_to_listen_for, and collective_key for DSPy sharing
# =============================================================================
ONBOARDING_TOPICS = {
    "career_motivations": {
        "label": "Motivations",
        "description": "WHY they work, not just WHAT they do. What drives them. Why they left previous roles (real reasons). What success means to THEM.",
        "example_questions": [
            "Your CV shows {role_count} roles in {years} years. What was the common thread that made you move each time?",
            "You've spent {years_in_field} years in {field}. Was this always the plan, or did something pull you toward this path?",
            "Looking at your trajectory, what's the one thing you're still searching for?",
        ],
        "behavioral_probes": [
            "Tell me about a moment in your career when you felt completely energized. What were you doing?",
            "What would make you stay somewhere forever?",
            "When you picture the perfect Monday morning, what does it look like?",
        ],
        "what_to_listen_for": "Passion vs obligation, intrinsic vs extrinsic motivation, patterns in job changes, what they light up about vs what they rush past",
        "collective_key": "motivations",
    },
    "achievements": {
        "label": "Achievements",
        "description": "Separate facts from self-reported claims. Understand ACTUAL contribution vs team/market factors. Evidence-based verification of CV claims.",
        "example_questions": [
            "You mention '{achievement}'. Walk me through the specific intervention that had the biggest impact.",
            "That's an impressive result. What was the situation BEFORE you arrived, and what would have happened without your intervention?",
            "What's one initiative that completely failed, and what did you learn?",
        ],
        "behavioral_probes": [
            "Tell me about a project where the outcome wasn't what you expected. How did you adapt?",
            "What achievement are you most proud of that ISN'T on your CV?",
            "If I asked your last manager what your unique contribution was, what would they say?",
        ],
        "what_to_listen_for": "Specificity of examples, ownership vs deflection, ability to discuss failures honestly, self-awareness about actual impact vs team effort",
        "collective_key": "achievements",
    },
    "work_style": {
        "label": "Work Style",
        "description": "Match HOW they work. Remote/hybrid/office preference and why. Team size comfort zone. Collaboration vs independence ratio. Communication style.",
        "example_questions": [
            "You've worked at both {company_types}. Which environment brought out your best work, and why?",
            "Describe your ideal Tuesday. What does your calendar look like?",
            "How do you prefer to receive feedback — direct and immediate, or processed and scheduled?",
        ],
        "behavioral_probes": [
            "When you're doing your best work, are you usually alone or with others?",
            "What meeting culture drives you crazy, and what kind works for you?",
            "How much structure do you need vs how much autonomy?",
        ],
        "what_to_listen_for": "Introvert vs extrovert work patterns, flexibility vs structure needs, communication preferences, energy sources and drains",
        "collective_key": "work_style",
    },
    "leadership": {
        "label": "Leadership",
        "description": "Management DNA. How they handle underperformers and develop high performers. Decision-making style. Conflict resolution. Beliefs about motivation.",
        "example_questions": [
            "You managed {team_size} people. Tell me about someone who surprised you — either positively or negatively.",
            "What's your philosophy on making unpopular decisions?",
            "How do you know when to step in and when to let someone fail?",
        ],
        "behavioral_probes": [
            "Describe the best boss you ever had. What made them different?",
            "How do you handle someone on your team who's talented but difficult to work with?",
            "When you disagree with a decision from above, how do you handle it?",
        ],
        "what_to_listen_for": "Empathy vs authority balance, delegation comfort, conflict avoidance vs confrontation, coaching vs directing instinct, emotional intelligence signals",
        "collective_key": "leadership",
    },
    "next_role": {
        "label": "Next Role",
        "description": "The HIDDEN job description. What they DON'T want to repeat. The role they'd take a pay cut for. Real dealbreakers. Ideal boss profile.",
        "example_questions": [
            "If money wasn't a factor, what would your next role look like?",
            "What's one thing from your last role that you absolutely don't want to repeat?",
            "Describe the boss you'd run through walls for. What makes them different?",
        ],
        "behavioral_probes": [
            "What would make you turn down an otherwise perfect role?",
            "Are you looking for growth and challenge, or stability and mastery?",
            "If you could design your next role from scratch, what would a typical week look like?",
        ],
        "what_to_listen_for": "Push vs pull factors, compensation vs meaning tradeoffs, risk tolerance, hidden non-negotiables that won't appear in any job description",
        "collective_key": "next_role",
    },
    "values_culture": {
        "label": "Values",
        "description": "UNSPOKEN factors that make or break a match. Company ethics standards. Work-life boundaries. Mission alignment. Cultural must-haves.",
        "example_questions": [
            "Tell me about a time you walked away from an opportunity. What was the trigger?",
            "What would a company have to do for you to turn them down, even if the role was perfect?",
            "Beyond salary, what makes you feel valued at work?",
        ],
        "behavioral_probes": [
            "What kind of company would you be embarrassed to work for?",
            "How important is the company's mission vs the day-to-day work itself?",
            "When you think about the culture where you did your best work, what three words describe it?",
        ],
        "what_to_listen_for": "Ethical boundaries, work-life balance signals, mission-driven vs pragmatic orientation, team culture preferences, what they find intolerable",
        "collective_key": "values",
    },
}


@router.post("/message", response_model=ChatResponse)
async def chat_message(request: ChatRequest):
    if not ANTHROPIC_API_KEY:
        raise HTTPException(status_code=503, detail="ANTHROPIC_API_KEY environment variable is required")

    # Ensure user profile exists (creates on first chat)
    await _ensure_profile(request.user_id, request.context.get("industry", "general"))

    # Build enriched context from knowledge base and learned patterns
    agent_context = {}
    user_patterns = []
    collective_patterns = []
    pre_conversation_context = ""
    cv_analysis = None
    try:
        agent_context = await ai_agent_knowledge_base.build_agent_context(request.user_id)
        user_patterns = await dspy_learning.get_user_patterns(request.user_id)
    except Exception:
        pass

    # Fetch collective intelligence from DSPy — patterns from OTHER users
    # in the same industry/role to inform better questions
    try:
        collective_patterns = await _get_collective_intelligence(
            request.user_id, request.context.get("industry", "general")
        )
    except Exception:
        pass

    # Fetch pre-conversation context from uploaded documents/social profiles
    try:
        from app.services.profile_analyzer import profile_analyzer
        db_client = get_db()

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
        pass

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
        pass

    try:
        client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)

        # Detect topics covered so far (before AI responds)
        covered_topics = _detect_onboarding_topics(request.messages)

        system_prompt = _build_system_prompt(
            context=request.context,
            agent_context=agent_context,
            user_patterns=user_patterns,
            collective_patterns=collective_patterns,
            pre_conversation_context=pre_conversation_context,
            rag_context=rag_context,
            covered_topics=covered_topics,
            cv_analysis=cv_analysis,
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
    except TypeError:
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

    # Detect which onboarding topics have been covered (after full exchange)
    onboarding_topics = _detect_onboarding_topics(full_messages)

    return ChatResponse(
        response=ai_response,
        conversation_id=conversation_id,
        learning_triggered=learning_triggered,
        quality_score=round(quality_score, 1),
        conversation_count=conversation_count,
        profile_readiness=profile_readiness,
        onboarding_topics=onboarding_topics,
    )


# =============================================================================
# SYSTEM PROMPT — Recruiter Methodology + CV-Contextual + Collective Intelligence
# =============================================================================
def _build_system_prompt(
    context: dict,
    agent_context: dict = None,
    user_patterns: list = None,
    collective_patterns: list = None,
    pre_conversation_context: str = "",
    rag_context: str = "",
    covered_topics: dict = None,
    cv_analysis: dict = None,
) -> str:
    base = (
        "You are an elite AI career agent trained in professional recruiter methodology "
        "and psychometric interviewing techniques. You conduct structured onboarding "
        "conversations that go far deeper than traditional recruitment.\n\n"
        "YOUR APPROACH — RECRUITER METHODOLOGY:\n"
        "You interview like a top executive recruiter, not a chatbot. This means:\n"
        "1. You've already READ the candidate's CV before the conversation starts.\n"
        "2. You NEVER ask generic questions like 'Tell me about yourself' — you reference "
        "SPECIFIC entries from their CV and dig deeper into what the CV cannot reveal.\n"
        "3. You use BEHAVIORAL questions: 'Tell me about a time when...' to get real examples.\n"
        "4. You probe what's UNSAID — gaps in the CV, quick role changes, missing context.\n"
        "5. You listen for TONE — enthusiasm vs obligation, confidence vs hedging, "
        "specificity vs vagueness. When someone is vague, you probe deeper.\n"
        "6. You separate CLAIMS from EVIDENCE — when someone says 'I led a transformation', "
        "you ask for the specific steps, the resistance faced, the measurable outcome.\n\n"
        "PSYCHOMETRIC AWARENESS:\n"
        "As you converse, you're building a psychological profile:\n"
        "- Motivation type: intrinsic (purpose, mastery, autonomy) vs extrinsic (status, money, title)\n"
        "- Risk tolerance: seek challenge vs seek stability\n"
        "- Leadership style: directive vs coaching vs collaborative\n"
        "- Conflict approach: confrontational vs avoidant vs diplomatic\n"
        "- Communication preference: direct vs nuanced\n"
        "- Decision-making: analytical vs intuitive vs consensus-driven\n"
        "You don't announce these assessments. You observe and adapt your questions.\n\n"
        "YOUR 6 ONBOARDING CATEGORIES:\n"
        "You're exploring 6 areas to build a complete professional identity:\n"
        "1. Career Motivations — WHY they work, not WHAT they do\n"
        "2. Achievements Context — Verify CV claims, separate fact from self-report\n"
        "3. Working Style — HOW they work best (environment, rhythm, collaboration)\n"
        "4. Leadership Philosophy — Their management DNA and decision-making\n"
        "5. Next Role Preferences — The hidden job description they carry in their head\n"
        "6. Values & Culture — Unspoken factors that make or break a match\n\n"
        "COMMUNICATION STYLE:\n"
        "- Write in clear, well-spaced paragraphs. Use double line breaks between paragraphs.\n"
        "- Keep each paragraph focused on one idea — short and easy to read.\n"
        "- Be warm but professionally sharp. Like a trusted advisor, not a corporate chatbot.\n"
        "- Ask ONE or TWO focused questions at a time. Let the conversation breathe.\n"
        "- Keep responses concise — 3 to 5 short paragraphs maximum.\n"
        "- When reflecting back, be precise — quote or reference exactly what they said.\n"
        "- Never use bullet points or numbered lists. Write in natural flowing prose.\n"
        "- Show genuine curiosity. React to what they say before asking the next question.\n\n"
        "IMPORTANT: Your purpose is to build such a deep understanding of this person that "
        "their AI agent can authentically represent them to recruiters and hiring managers. "
        "Everything you learn here will be used to speak AS them, filter opportunities by their "
        "hidden criteria, and negotiate based on THEIR priorities."
    )

    # --- CV-CONTEXTUAL QUESTIONING ---
    if cv_analysis:
        base += "\n\n--- CV ANALYSIS (READ BEFORE CONVERSATION) ---\n"
        if cv_analysis.get("name"):
            base += f"Candidate name: {cv_analysis['name']}\n"
        if cv_analysis.get("current_role"):
            base += f"Current/most recent role: {cv_analysis['current_role']}\n"
        if cv_analysis.get("experience"):
            base += f"Experience summary: {cv_analysis['experience']}\n"
        if cv_analysis.get("skills"):
            base += f"Key skills: {', '.join(cv_analysis['skills'][:10])}\n"
        if cv_analysis.get("education"):
            base += f"Education: {cv_analysis['education']}\n"
        if cv_analysis.get("achievements"):
            achievements = cv_analysis["achievements"]
            if isinstance(achievements, list):
                base += f"Notable achievements: {'; '.join(achievements[:5])}\n"
            else:
                base += f"Notable achievements: {achievements}\n"
        if cv_analysis.get("companies"):
            base += f"Companies: {', '.join(cv_analysis['companies'][:5])}\n"
        base += (
            "\nUSE THIS CV DATA to ask CV-CONTEXTUAL questions. Reference specific roles, "
            "achievements, and companies. Example: Instead of 'What do you do?', ask "
            "'Your CV shows you led HR transformation at [company] — what was the most "
            "resistance you faced during that transformation?'\n"
            "--- END CV ANALYSIS ---"
        )

    # --- ONBOARDING PROGRESS ---
    if covered_topics is not None:
        covered = [t for t, v in covered_topics.items() if v]
        uncovered = [t for t, v in covered_topics.items() if not v]
        total = len(ONBOARDING_TOPICS)
        done = len(covered)

        if uncovered:
            next_topic_id = uncovered[0]
            next_topic = ONBOARDING_TOPICS[next_topic_id]
            base += (
                f"\n\nONBOARDING PROGRESS: {done}/{total} categories explored."
                f"\nCompleted: {', '.join(ONBOARDING_TOPICS[t]['label'] for t in covered) or 'None yet'}."
                f"\n\nNEXT CATEGORY: {next_topic['label']}"
                f"\nPurpose: {next_topic['description']}"
                f"\nWhat to listen for: {next_topic['what_to_listen_for']}"
            )
            # Provide CV-contextual example questions if CV available
            if cv_analysis:
                base += f"\nSuggested probes (adapt to CV context): {'; '.join(next_topic['behavioral_probes'][:2])}"
            else:
                base += f"\nSuggested probes: {'; '.join(next_topic['behavioral_probes'][:2])}"
            if len(uncovered) > 1:
                base += f"\nStill remaining: {', '.join(ONBOARDING_TOPICS[t]['label'] for t in uncovered[1:])}."
            base += (
                "\n\nNaturally guide toward this category. Don't announce it mechanically — "
                "weave it from what the user just shared. Acknowledge their answer, show you "
                "understood, then transition with genuine curiosity."
            )
        else:
            base += (
                f"\n\nONBOARDING COMPLETE: All {total} categories explored!"
                "\nYou now have a comprehensive professional identity for this candidate."
                "\nSummarize what you've learned: their motivations, verified achievements, "
                "work style, leadership approach, ideal next role, and core values."
                "\nLet them know their AI agent now has a deep understanding and is ready to "
                "represent them authentically to recruiters and hiring managers."
                "\nAsk if there's anything they'd like to add or correct."
            )

    # --- COLLECTIVE INTELLIGENCE FROM DSPY ---
    if collective_patterns:
        industry = context.get("industry", "general")
        base += (
            f"\n\nCOLLECTIVE INTELLIGENCE (from {len(collective_patterns)} professionals in {industry}):\n"
            "The platform has learned the following patterns from other candidates in similar roles. "
            "Use this to ask BETTER questions — you know what typically matters to people in this field.\n"
        )
        # Aggregate insights
        all_values = []
        all_criteria = []
        all_goals = []
        for p in collective_patterns[:10]:
            pattern_data = p.get("patterns", p.get("pattern_data", {}))
            if isinstance(pattern_data, str):
                try:
                    pattern_data = json.loads(pattern_data)
                except Exception:
                    continue
            if not isinstance(pattern_data, dict):
                continue
            all_values.extend(pattern_data.get("values", [])[:2])
            all_criteria.extend(pattern_data.get("hidden_criteria", [])[:2])
            all_goals.extend(pattern_data.get("goals", [])[:2])

        if all_values:
            # Count frequency to find most common
            from collections import Counter
            top_values = [v for v, _ in Counter(all_values).most_common(5)]
            base += f"- Common values in this industry: {', '.join(top_values)}\n"
        if all_criteria:
            from collections import Counter
            top_criteria = [v for v, _ in Counter(all_criteria).most_common(3)]
            base += f"- Hidden criteria others reveal: {', '.join(top_criteria)}\n"
        if all_goals:
            from collections import Counter
            top_goals = [v for v, _ in Counter(all_goals).most_common(3)]
            base += f"- Common career goals: {', '.join(top_goals)}\n"
        base += (
            "Use these insights to probe deeper. If this candidate's answers differ from the "
            "collective pattern, that's INTERESTING — explore why they're different."
        )

    # Inject additional pre-conversation context
    if pre_conversation_context:
        base += f"\n\n{pre_conversation_context}"

    # Inject industry expertise
    industry = context.get("industry") or (agent_context or {}).get("industry")
    if industry and industry != "general":
        base += f"\n\nThe user works in {industry}."
        knowledge = (agent_context or {}).get("knowledge", {})
        if knowledge.get("skill_benchmarks"):
            base += f" Skill benchmarks: {', '.join(f'{k}: {v}' for k, v in list(knowledge['skill_benchmarks'].items())[:3])}."
        if knowledge.get("hidden_criteria"):
            base += f" Industry insight: {'; '.join(knowledge['hidden_criteria'][:2])}."

    # Inject previously learned patterns about THIS user
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
                "\n\nFROM PREVIOUS CONVERSATIONS WITH THIS USER:\n- "
                + "\n- ".join(pattern_notes)
                + "\nBuild on this. Don't re-ask what you know. Go deeper into areas "
                "where understanding is still shallow."
            )

    # Inject RAG context
    if rag_context:
        base += f"\n\nRelevant context from previous interactions:\n{rag_context}"

    if context.get("stage") == "calibration":
        base += (
            "\n\nCALIBRATION MODE: The user just rejected a test opportunity. "
            "Gently explore what didn't feel right. This is a goldmine for hidden criteria. "
            "Listen for what they DON'T say as much as what they do."
        )

    return base


# =============================================================================
# COLLECTIVE INTELLIGENCE — DSPy patterns from other users
# =============================================================================
async def _get_collective_intelligence(user_id: str, industry: str) -> list:
    """Fetch DSPy-learned patterns from other users in the same industry.

    This is the flywheel: each onboarding conversation feeds patterns back
    into the collective, making every subsequent onboarding smarter.
    After 100 users, the AI knows what HR Directors typically value,
    what software engineers' hidden criteria are, etc.
    """
    try:
        db = get_db()
        if not db:
            return []
        # Get patterns from other users (not this user) for collective intelligence
        result = (
            db.table("cv2_collective_patterns")
            .select("patterns, industry, created_at")
            .eq("industry", industry)
            .neq("user_id", user_id)
            .order("created_at", desc=True)
            .limit(20)
            .execute()
        )
        return result.data or []
    except Exception:
        return []


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


def _detect_onboarding_topics(messages: list[dict]) -> dict:
    """Detect which onboarding topics have been meaningfully discussed.

    Uses Claude to analyze conversation content rather than simple keyword matching.
    This is more accurate because users discuss career goals without saying 'goal',
    or describe their values without using the word 'values'.

    Falls back to keyword heuristic if the Claude analysis call fails.
    """
    user_messages = [
        m.get("content", "") for m in messages if m.get("role") == "user"
    ]
    if not user_messages or not any(msg.strip() for msg in user_messages):
        return {topic_id: False for topic_id in ONBOARDING_TOPICS}

    # Try Claude-based analysis (more accurate, catches implicit topic coverage)
    try:
        client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)
        user_text = "\n---\n".join(user_messages)

        analysis_prompt = (
            "Analyze this conversation from a candidate. Determine which of these 6 "
            "onboarding categories have been MEANINGFULLY discussed (not just mentioned "
            "in passing — the user must have shared substantive information):\n\n"
            "1. career_motivations — WHY they work, career drivers, reasons for job changes\n"
            "2. achievements — Specific accomplishments, project details, measurable results\n"
            "3. work_style — Work preferences, remote/office, collaboration style, daily rhythm\n"
            "4. leadership — Management approach, decision-making, handling conflict/teams\n"
            "5. next_role — What they want next, dealbreakers, ideal role/boss/company\n"
            "6. values_culture — Personal values, culture preferences, ethics, work-life balance\n\n"
            f"CANDIDATE'S MESSAGES:\n{user_text}\n\n"
            "Respond ONLY with a JSON object like: "
            '{"career_motivations": true, "achievements": false, "work_style": true, '
            '"leadership": false, "next_role": false, "values_culture": false}\n'
            "Set true ONLY if the user shared meaningful substance on that topic."
        )

        response = client.messages.create(
            model="claude-sonnet-4-20250514",
            max_tokens=200,
            messages=[{"role": "user", "content": analysis_prompt}],
        )

        raw = response.content[0].text.strip()
        # Extract JSON from response (might have markdown wrapping)
        if "{" in raw:
            json_str = raw[raw.index("{"):raw.rindex("}") + 1]
            result = json.loads(json_str)
            # Ensure all keys present
            for topic_id in ONBOARDING_TOPICS:
                if topic_id not in result:
                    result[topic_id] = False
            return result
    except Exception:
        pass

    # Fallback: keyword heuristic
    user_text = " ".join(msg.lower() for msg in user_messages)
    keyword_map = {
        "career_motivations": ["goal", "aspir", "want to", "dream", "next step", "future", "ambition", "moved", "left", "why i", "passion", "drive", "motivat", "career path", "searching for"],
        "achievements": ["led", "built", "delivered", "achieved", "reduced", "increased", "managed", "launched", "created", "result", "impact", "proud", "failed", "learned"],
        "work_style": ["remote", "office", "hybrid", "team", "collaborate", "independent", "flexible", "structure", "calendar", "meetings", "feedback", "communicate", "async"],
        "leadership": ["manage", "lead", "team of", "decision", "conflict", "mentor", "coach", "delegate", "hire", "fire", "underperform", "boss", "report to"],
        "next_role": ["next role", "looking for", "ideal", "don't want", "dealbreak", "pay cut", "perfect role", "opportunity", "salary", "compensation", "growth", "stability"],
        "values_culture": ["value", "culture", "ethics", "work-life", "mission", "purpose", "diverse", "inclusive", "environment", "toxic", "respect", "trust", "balance"],
    }
    result = {}
    for topic_id in ONBOARDING_TOPICS:
        keywords = keyword_map.get(topic_id, [])
        result[topic_id] = any(kw in user_text for kw in keywords)
    return result


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


@router.get("/onboarding-status/{user_id}")
async def get_onboarding_status(user_id: str):
    """Get onboarding topic coverage and readiness from stored conversations."""
    db = get_db()
    all_messages = []
    conversation_count = 0
    has_cv = False
    has_patterns = False
    quality_score = 0.0
    learning_triggered = False

    # Gather all conversation messages
    if db:
        try:
            result = db.rpc("get_user_conversations", {"p_user_id": user_id}).execute()
            convos = result.data or []
        except Exception:
            try:
                result = (
                    db.table("cv2_conversations")
                    .select("messages, quality_score")
                    .eq("user_id", user_id)
                    .order("created_at", desc=True)
                    .limit(20)
                    .execute()
                )
                convos = result.data or []
            except Exception:
                convos = []

        conversation_count = len(convos)
        for c in convos:
            msgs = c.get("messages", [])
            all_messages.extend(msgs)
            qs = c.get("quality_score")
            if qs and qs > quality_score:
                quality_score = qs

    # Check for CV / documents
    if db:
        try:
            docs = db.rpc("get_user_documents", {"p_user_id": user_id}).execute()
            doc_list = docs.data or []
            has_cv = any(d.get("doc_type") == "cv" for d in doc_list)
        except Exception:
            pass

    # Check for learned patterns
    try:
        from app.services.dspy_learning import dspy_learning
        patterns = await dspy_learning.get_user_patterns(user_id)
        has_patterns = bool(patterns)
        learning_triggered = bool(patterns)
    except Exception:
        pass

    topics = _detect_onboarding_topics(all_messages) if all_messages else {t: False for t in ONBOARDING_TOPICS}
    readiness = _calculate_readiness(has_cv, has_patterns, conversation_count, quality_score, learning_triggered)

    return {
        "onboarding_topics": topics,
        "profile_readiness": readiness,
        "conversation_count": conversation_count,
    }


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
