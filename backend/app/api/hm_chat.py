"""Hiring Manager Onboarding Chat — Mirrored 6-Category Discovery Interview.

This is the other side of the marketplace. Same depth as talent onboarding,
but focused on understanding the ROLE, the TEAM, and what the hiring manager
REALLY wants (not just the job description).

The 6 categories mirror the talent side:
  Talent Side               →  Hiring Manager Side
  Career Motivations        →  Role Motivations
  Achievements Context      →  Success Expectations
  Work Style               →  Team Working Style
  Leadership Philosophy     →  Management Approach
  Next Role Preferences     →  Ideal Candidate Profile
  Values & Culture         →  Culture & Hidden Criteria
"""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, field_validator
import json

import anthropic
from app.config import ANTHROPIC_API_KEY, QUALITY_THRESHOLD
from app.database import get_db
from app.validation import validate_user_id, sanitize_for_prompt
from app.services.conversation_logger import conversation_logger
from app.services.quality_analyzer import quality_analyzer
from app.services.dspy_learning import dspy_learning

router = APIRouter()


class HMChatRequest(BaseModel):
    user_id: str
    messages: list[dict]
    context: dict = {}

    @field_validator("user_id")
    @classmethod
    def check_user_id(cls, v):
        return validate_user_id(v)

    @field_validator("messages")
    @classmethod
    def check_messages(cls, v):
        if not v:
            raise ValueError("At least one message is required")
        if len(v) > 100:
            v = v[-100:]
        for msg in v:
            if "content" in msg and isinstance(msg["content"], str):
                msg["content"] = sanitize_for_prompt(msg["content"])
        return v


class HMChatResponse(BaseModel):
    response: str
    conversation_id: str | None = None
    learning_triggered: bool = False
    quality_score: float = 0.0
    conversation_count: int = 0
    profile_readiness: int = 0
    onboarding_topics: dict = {}


# =============================================================================
# 6-CATEGORY HIRING MANAGER ONBOARDING — Mirror of Talent Side
# =============================================================================
HM_ONBOARDING_TOPICS = {
    "role_motivations": {
        "label": "Role Why",
        "description": "WHY is this role open? What really happened — did someone leave, is the team growing, did a project fail? What's the real urgency? What happens if they DON'T fill this role?",
        "example_questions": [
            "This role has been open for {duration}. What's driving the urgency to fill it now?",
            "What happened with the previous person in this role? What worked and what didn't?",
            "If you couldn't hire for this role, what would happen to the team in 6 months?",
        ],
        "behavioral_probes": [
            "Tell me about the moment you realized you needed to hire for this role. What triggered it?",
            "What's the real cost of leaving this position unfilled?",
            "Have you tried solving this problem internally before looking externally?",
        ],
        "what_to_listen_for": "Urgency level, whether this is growth or replacement, honest assessment of what went wrong before, organizational politics around the role",
        "collective_key": "role_motivations",
    },
    "success_expectations": {
        "label": "Success",
        "description": "What does SUCCESS look like in 6 months? What's the real bar — not the job description bar, but what would make you say 'this hire was perfect'? What are the measurable outcomes?",
        "example_questions": [
            "If the ideal candidate starts Monday, what should they have accomplished by month 3?",
            "What's the ONE thing this person must deliver that would make the hire a clear success?",
            "What does failure look like in this role? What are the warning signs?",
        ],
        "behavioral_probes": [
            "Think about the best person who ever held a similar role here. What made them exceptional?",
            "What KPIs or metrics will you use to evaluate this hire in their first year?",
            "What's a realistic expectation vs what would exceed your expectations?",
        ],
        "what_to_listen_for": "Clarity of expectations, realistic vs unrealistic goals, whether they've thought through onboarding, hidden priorities beyond the formal KPIs",
        "collective_key": "success_expectations",
    },
    "team_style": {
        "label": "Team",
        "description": "How does this team ACTUALLY work? Daily rhythms, meeting culture, communication style. What's the team dynamic — is it healthy or are there tensions? How does information flow?",
        "example_questions": [
            "Walk me through a typical week for this team. What does the rhythm look like?",
            "How does the team communicate — Slack, email, stand-ups, or something else?",
            "Is this team mostly remote, hybrid, or in-office? What's the actual preference vs the policy?",
        ],
        "behavioral_probes": [
            "Describe the personality of the team. If the team were a person, what would they be like?",
            "What's the biggest tension or challenge the team faces right now?",
            "How does a new person typically integrate into this team? What's the learning curve?",
        ],
        "what_to_listen_for": "Team health, honest assessment of dynamics vs PR version, communication preferences, how welcoming they are to new members, pace and pressure",
        "collective_key": "team_style",
    },
    "management_approach": {
        "label": "Manage",
        "description": "How does the hiring manager ACTUALLY lead? Hands-on or hands-off? How do they handle conflict, underperformance, and feedback? What's their decision-making style?",
        "example_questions": [
            "How would your current team describe your management style?",
            "When someone on your team is underperforming, what's your typical approach?",
            "How much autonomy does this role have? Will they report directly to you?",
        ],
        "behavioral_probes": [
            "Tell me about a time you had to give difficult feedback. How did you handle it?",
            "How do you balance giving guidance vs letting people figure things out?",
            "What's the most important quality you look for in a direct report?",
        ],
        "what_to_listen_for": "Self-awareness about management style, honest vs aspirational answers, micromanagement signals, empathy vs authority balance, growth mindset",
        "collective_key": "management_approach",
    },
    "ideal_candidate": {
        "label": "Ideal Hire",
        "description": "Beyond the job spec — WHO would they love? What personality, background, energy? What would make them say 'this is THE person'? What's the hidden profile?",
        "example_questions": [
            "Forget the job description for a moment. Describe the person you'd be excited to hire.",
            "What trait or experience would make you immediately move a candidate to the top of the list?",
            "Is there a specific background or career path that you think is ideal for this role?",
        ],
        "behavioral_probes": [
            "Think of the best hire you ever made. What was it about them that made it work?",
            "What's more important — technical excellence or cultural fit? Where's the line?",
            "Would you rather hire someone who's done this exact job before, or someone with raw talent who needs to grow into it?",
        ],
        "what_to_listen_for": "Biases (conscious or unconscious), unrealistic expectations, flexibility vs rigidity, whether they value potential or track record, the gap between JD and real preferences",
        "collective_key": "ideal_candidate",
    },
    "culture_criteria": {
        "label": "Culture",
        "description": "Unspoken factors that make or break a match. Company values in PRACTICE (not on the wall). What would make them reject a perfect-on-paper candidate? Work-life expectations.",
        "example_questions": [
            "What's the company culture actually like day-to-day? Not the website version — the real one.",
            "What would make you reject a candidate who checks every box on paper?",
            "What are the unwritten rules of success at your company?",
        ],
        "behavioral_probes": [
            "Tell me about someone who looked perfect on paper but didn't work out. What went wrong?",
            "What's the work-life balance expectation? Is overtime expected, occasional, or discouraged?",
            "If a candidate asked 'what's the worst thing about working here?', what would you honestly say?",
        ],
        "what_to_listen_for": "Honesty vs PR mode, real culture vs aspirational culture, hidden dealbreakers, compensation philosophy, red flags they've learned to screen for",
        "collective_key": "culture_criteria",
    },
}


@router.post("/message", response_model=HMChatResponse)
async def hm_chat_message(request: HMChatRequest):
    if not ANTHROPIC_API_KEY:
        raise HTTPException(status_code=503, detail="ANTHROPIC_API_KEY environment variable is required")

    await _ensure_hm_profile(request.user_id, request.context.get("industry", "general"))

    # Build context
    user_patterns = []
    collective_patterns = []
    job_analysis = None
    try:
        user_patterns = await dspy_learning.get_user_patterns(request.user_id)
    except Exception:
        pass

    # Fetch collective intelligence — patterns from OTHER hiring managers
    try:
        collective_patterns = await _get_hm_collective_intelligence(
            request.user_id, request.context.get("industry", "general")
        )
    except Exception:
        pass

    # Fetch job description analysis if uploaded
    try:
        db_client = get_db()
        docs_data = db_client.rpc("get_user_documents", {"p_user_id": request.user_id}).execute()
        for doc in (docs_data.data or []):
            if doc.get("analysis") and doc.get("doc_type") in ("job_description", "cv"):
                job_analysis = doc["analysis"]
                break
    except Exception:
        pass

    try:
        client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)

        covered_topics = _detect_hm_topics(request.messages)

        system_prompt = _build_hm_system_prompt(
            context=request.context,
            user_patterns=user_patterns,
            collective_patterns=collective_patterns,
            covered_topics=covered_topics,
            job_analysis=job_analysis,
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
        raise HTTPException(status_code=503, detail="API credentials not configured.")
    except anthropic.AuthenticationError:
        raise HTTPException(status_code=503, detail="Invalid ANTHROPIC_API_KEY")

    # DSPy Learning Pipeline
    full_messages = request.messages + [{"role": "assistant", "content": ai_response}]
    quality_score = 0.0
    conversation_count = 0
    conversation_id = None
    learning_triggered = False

    try:
        conversation_id = await conversation_logger.log_conversation(
            request.user_id, full_messages, metadata={**request.context, "agent_type": "hm"}
        )
        quality_score = await quality_analyzer.analyze(conversation_id)
        if quality_score >= QUALITY_THRESHOLD:
            await dspy_learning.learn_from_conversation(conversation_id)
            learning_triggered = True
    except Exception:
        pass

    try:
        db = get_db()
        conv_result = db.rpc("get_user_conversation_count", {"p_user_id": request.user_id}).execute()
        conversation_count = conv_result.data[0]["count"] if conv_result.data else 0
    except Exception:
        pass

    profile_readiness = _calculate_hm_readiness(
        has_job=bool(job_analysis),
        has_patterns=bool(user_patterns),
        conversation_count=conversation_count,
        quality_score=quality_score,
        learning_triggered=learning_triggered,
    )

    onboarding_topics = _detect_hm_topics(full_messages)

    return HMChatResponse(
        response=ai_response,
        conversation_id=conversation_id,
        learning_triggered=learning_triggered,
        quality_score=round(quality_score, 1),
        conversation_count=conversation_count,
        profile_readiness=profile_readiness,
        onboarding_topics=onboarding_topics,
    )


# =============================================================================
# SYSTEM PROMPT — Hiring Manager Discovery Interview
# =============================================================================
def _build_hm_system_prompt(
    context: dict,
    user_patterns: list = None,
    collective_patterns: list = None,
    covered_topics: dict = None,
    job_analysis: dict = None,
) -> str:
    base = (
        "You are an elite AI recruitment consultant conducting a structured discovery "
        "interview with a HIRING MANAGER. Your goal is to understand this role, team, "
        "and hiring manager at the deepest level — far beyond a job description.\n\n"
        "YOUR APPROACH — CONSULTATIVE METHODOLOGY:\n"
        "You interview hiring managers like a top executive search consultant:\n"
        "1. You've already READ the job description (if uploaded) before the conversation starts.\n"
        "2. You NEVER accept surface-level answers. When they say 'we need a strong leader', "
        "you ask: 'What does strong leadership look like in THIS team specifically?'\n"
        "3. You probe for the REAL story — why is this role open, what happened before, "
        "what's the politics around the hire.\n"
        "4. You separate the JOB DESCRIPTION from the REAL REQUIREMENTS — they're rarely the same.\n"
        "5. You uncover HIDDEN CRITERIA — the unspoken preferences that will actually "
        "determine whether a candidate gets hired.\n"
        "6. You assess the HIRING MANAGER's style — because the best candidate match depends "
        "on understanding who they'll be working for, not just what they'll be doing.\n\n"
        "YOUR 6 DISCOVERY CATEGORIES:\n"
        "1. Role Motivations — WHY this role exists, what's the real urgency\n"
        "2. Success Expectations — What 'great' looks like in 6 months, real KPIs\n"
        "3. Team Working Style — How the team actually operates day-to-day\n"
        "4. Management Approach — How the HM leads, gives feedback, makes decisions\n"
        "5. Ideal Candidate Profile — The hidden person they really want\n"
        "6. Culture & Hidden Criteria — Unspoken factors that make or break a hire\n\n"
        "COMMUNICATION STYLE:\n"
        "- Write in clear, well-spaced paragraphs. Use double line breaks between paragraphs.\n"
        "- Be professionally sharp but warm. Like a trusted executive search partner.\n"
        "- Ask ONE or TWO focused questions at a time. Let the conversation breathe.\n"
        "- Keep responses concise — 3 to 5 short paragraphs maximum.\n"
        "- React to what they say before asking the next question. Show you're listening.\n"
        "- Never use bullet points or numbered lists. Write in natural flowing prose.\n\n"
        "IMPORTANT: Everything you learn will be used by the Job Agent to negotiate with "
        "Candidate Agents. The deeper you understand this role, the better the matches. "
        "Your insight is what prevents bad hires and wasted interviews."
    )

    # Job description context
    if job_analysis:
        base += "\n\n--- JOB DESCRIPTION ANALYSIS (READ BEFORE CONVERSATION) ---\n"
        if job_analysis.get("title"):
            base += f"Role title: {job_analysis['title']}\n"
        if job_analysis.get("company"):
            base += f"Company: {job_analysis['company']}\n"
        if job_analysis.get("description"):
            desc = job_analysis["description"]
            if len(desc) > 500:
                desc = desc[:500] + "..."
            base += f"Description: {desc}\n"
        if job_analysis.get("requirements"):
            reqs = job_analysis["requirements"]
            if isinstance(reqs, list):
                base += f"Requirements: {'; '.join(reqs[:8])}\n"
            else:
                base += f"Requirements: {reqs}\n"
        if job_analysis.get("skills"):
            base += f"Key skills: {', '.join(job_analysis['skills'][:10])}\n"
        if job_analysis.get("salary_range"):
            base += f"Salary range: {job_analysis['salary_range']}\n"
        base += (
            "\nUSE THIS JOB DATA to ask specific questions. Reference the requirements, "
            "skills, and role details. Probe what's NOT in the description.\n"
            "--- END JOB ANALYSIS ---"
        )

    # Onboarding progress
    if covered_topics is not None:
        covered = [t for t, v in covered_topics.items() if v]
        uncovered = [t for t, v in covered_topics.items() if not v]
        total = len(HM_ONBOARDING_TOPICS)
        done = len(covered)

        if uncovered:
            next_topic = HM_ONBOARDING_TOPICS[uncovered[0]]
            base += (
                f"\n\nDISCOVERY PROGRESS: {done}/{total} categories explored."
                f"\nCompleted: {', '.join(HM_ONBOARDING_TOPICS[t]['label'] for t in covered) or 'None yet'}."
                f"\n\nNEXT CATEGORY: {next_topic['label']}"
                f"\nPurpose: {next_topic['description']}"
                f"\nWhat to listen for: {next_topic['what_to_listen_for']}"
                f"\nSuggested probes: {'; '.join(next_topic['behavioral_probes'][:2])}"
            )
            if len(uncovered) > 1:
                base += f"\nStill remaining: {', '.join(HM_ONBOARDING_TOPICS[t]['label'] for t in uncovered[1:])}."
            base += (
                "\n\nNaturally guide toward this category. Acknowledge what they shared, "
                "then transition with genuine curiosity."
            )
        else:
            base += (
                f"\n\nDISCOVERY COMPLETE: All {total} categories explored!"
                "\nSummarize the role profile: why the role exists, what success looks like, "
                "team dynamics, management style, ideal candidate, and hidden criteria."
                "\nLet them know their Job Agent now has a deep understanding and is ready "
                "to evaluate candidates authentically — not just matching keywords."
            )

    # Collective intelligence from other hiring managers
    if collective_patterns:
        industry = context.get("industry", "general")
        base += (
            f"\n\nCOLLECTIVE INTELLIGENCE (from {len(collective_patterns)} hiring managers in {industry}):\n"
        )
        all_criteria = []
        all_expectations = []
        for p in collective_patterns[:10]:
            pd = p.get("patterns", {})
            if isinstance(pd, str):
                try:
                    pd = json.loads(pd)
                except Exception:
                    continue
            if not isinstance(pd, dict):
                continue
            all_criteria.extend(pd.get("hidden_criteria", [])[:2])
            all_expectations.extend(pd.get("goals", [])[:2])

        if all_criteria:
            from collections import Counter
            top = [v for v, _ in Counter(all_criteria).most_common(3)]
            base += f"- Common hidden criteria HMs reveal: {', '.join(top)}\n"
        if all_expectations:
            from collections import Counter
            top = [v for v, _ in Counter(all_expectations).most_common(3)]
            base += f"- Common success expectations: {', '.join(top)}\n"
        base += "Probe whether this HM shares or differs from these patterns."

    # Previous patterns about this HM
    if user_patterns:
        latest = user_patterns[0] if user_patterns else {}
        pattern_notes = []
        if latest.get("hidden_criteria"):
            pattern_notes.append(f"Known hiring criteria: {', '.join(latest['hidden_criteria'][:3])}")
        if latest.get("values"):
            pattern_notes.append(f"Values: {', '.join(latest['values'][:3])}")
        if pattern_notes:
            base += (
                "\n\nFROM PREVIOUS CONVERSATIONS WITH THIS HIRING MANAGER:\n- "
                + "\n- ".join(pattern_notes)
                + "\nBuild on this. Go deeper."
            )

    return base


# =============================================================================
# TOPIC DETECTION — Claude-based with keyword fallback
# =============================================================================
def _detect_hm_topics(messages: list[dict]) -> dict:
    user_messages = [m.get("content", "") for m in messages if m.get("role") == "user"]
    if not user_messages or not any(msg.strip() for msg in user_messages):
        return {topic_id: False for topic_id in HM_ONBOARDING_TOPICS}

    try:
        client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)
        user_text = "\n---\n".join(user_messages)

        response = client.messages.create(
            model="claude-sonnet-4-20250514",
            max_tokens=200,
            messages=[{
                "role": "user",
                "content": (
                    "Analyze this hiring manager's messages. Determine which of these 6 "
                    "discovery categories have been MEANINGFULLY discussed:\n\n"
                    "1. role_motivations — Why the role is open, urgency, what happened before\n"
                    "2. success_expectations — What success looks like, KPIs, realistic expectations\n"
                    "3. team_style — How the team works, communication, dynamics, rhythm\n"
                    "4. management_approach — HM's leadership style, feedback, decision-making\n"
                    "5. ideal_candidate — Who they really want beyond the JD, hidden preferences\n"
                    "6. culture_criteria — Real culture, hidden dealbreakers, work-life expectations\n\n"
                    f"HIRING MANAGER'S MESSAGES:\n{user_text}\n\n"
                    "Respond ONLY with a JSON object like: "
                    '{"role_motivations": true, "success_expectations": false, '
                    '"team_style": false, "management_approach": false, '
                    '"ideal_candidate": false, "culture_criteria": false}'
                ),
            }],
        )

        raw = response.content[0].text.strip()
        if "{" in raw:
            json_str = raw[raw.index("{"):raw.rindex("}") + 1]
            result = json.loads(json_str)
            for topic_id in HM_ONBOARDING_TOPICS:
                if topic_id not in result:
                    result[topic_id] = False
            return result
    except Exception:
        pass

    # Keyword fallback
    user_text = " ".join(msg.lower() for msg in user_messages)
    keyword_map = {
        "role_motivations": ["role open", "position", "left", "quit", "growing", "urgent", "backfill", "new role", "expansion", "restructur"],
        "success_expectations": ["success", "kpi", "metric", "deliver", "accomplish", "first 90", "expect", "goal", "outcome", "performance"],
        "team_style": ["team", "remote", "office", "hybrid", "standup", "slack", "meeting", "communicate", "collaborate", "pace"],
        "management_approach": ["manage", "feedback", "decision", "autonomy", "direct report", "1:1", "coaching", "delegate", "review"],
        "ideal_candidate": ["ideal", "perfect candidate", "looking for", "must have", "nice to have", "experience", "background", "fit"],
        "culture_criteria": ["culture", "values", "work-life", "overtime", "unwritten", "reject", "red flag", "wouldn't hire", "dealbreak"],
    }
    result = {}
    for topic_id in HM_ONBOARDING_TOPICS:
        keywords = keyword_map.get(topic_id, [])
        result[topic_id] = any(kw in user_text for kw in keywords)
    return result


# =============================================================================
# HELPERS
# =============================================================================
async def _ensure_hm_profile(user_id: str, industry: str = "general") -> None:
    try:
        client = get_db()
        if not client:
            return
        try:
            client.rpc("ensure_cv2_profile", {
                "uid": user_id,
                "p_industry": industry or "general",
            }).execute()
        except Exception:
            pass
    except Exception:
        pass


def _calculate_hm_readiness(
    has_job: bool, has_patterns: bool, conversation_count: int,
    quality_score: float, learning_triggered: bool,
) -> int:
    score = 0
    if has_job:
        score += 30
    score += min(conversation_count * 10, 30)
    if has_patterns:
        score += 15
    if quality_score >= 7.0:
        score += 15
    if learning_triggered:
        score += 10
    return min(score, 100)


async def _get_hm_collective_intelligence(user_id: str, industry: str) -> list:
    try:
        db = get_db()
        if not db:
            return []
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


@router.get("/history/{user_id}")
async def get_hm_conversation_history(user_id: str):
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
