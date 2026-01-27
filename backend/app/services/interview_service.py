"""Structured Interview Service - Symmetric for both Talent and HM agents.

Generates personalized interview questions from uploaded context (CV for talent,
job description for HM), handles one-question-at-a-time flow, and analyzes
responses including psychometric signals.
"""

import json
from typing import Optional

import anthropic

from app.config import ANTHROPIC_API_KEY


TALENT_QUESTION_COUNT = 7
HM_QUESTION_COUNT = 5


class InterviewService:
    def __init__(self):
        self._anthropic = None

    @property
    def client(self):
        if self._anthropic is None:
            self._anthropic = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)
        return self._anthropic

    async def generate_talent_questions(
        self, cv_analysis: dict, industry: str = "general"
    ) -> list[dict]:
        """Generate structured interview questions for a talent based on CV analysis.

        Questions go BEYOND the CV - focus on values, culture fit, hidden preferences,
        what energizes them, what they'd never compromise on.

        Returns list of {question, purpose, psychometric_target}
        """
        if not ANTHROPIC_API_KEY:
            return self._fallback_talent_questions()

        cv_context = json.dumps(cv_analysis, indent=2)[:3000]

        prompt = f"""You are designing a structured interview for a professional AI agent
that will represent this person in job negotiations.

CV ANALYSIS:
{cv_context}

INDUSTRY: {industry}

Generate exactly {TALENT_QUESTION_COUNT} interview questions that reveal what CANNOT be learned from a CV:
- Values and non-negotiables
- Work environment preferences
- What energizes vs drains them
- Leadership/collaboration style
- Hidden frustrations with their industry
- What "success" means to them personally
- Career direction beyond the obvious trajectory

Each question should feel conversational and natural, not like a formal interview.
Questions should build on CV context (reference their actual experience).

Return JSON array of objects:
[
  {{
    "question": "the question text",
    "purpose": "what this reveals about the person",
    "psychometric_target": "one of: values, environment, motivation, collaboration, direction, boundaries, identity"
  }}
]

Return ONLY valid JSON."""

        try:
            response = self.client.messages.create(
                model="claude-sonnet-4-20250514",
                max_tokens=2000,
                messages=[{"role": "user", "content": prompt}],
            )
            text = response.content[0].text.strip()
            if text.startswith("```"):
                text = text.split("\n", 1)[1].rsplit("```", 1)[0]
            questions = json.loads(text)
            return questions[:TALENT_QUESTION_COUNT]
        except Exception:
            return self._fallback_talent_questions()

    async def generate_hm_questions(
        self, job_analysis: dict, industry: str = "general"
    ) -> list[dict]:
        """Generate structured interview questions for a hiring manager.

        Questions reveal what the HM REALLY wants beyond the job description:
        - Team dynamics and culture
        - What previous hires got wrong
        - Unwritten requirements
        - Growth trajectory for the role
        - Decision-making style

        Returns list of {question, purpose, psychometric_target}
        """
        if not ANTHROPIC_API_KEY:
            return self._fallback_hm_questions()

        job_context = json.dumps(job_analysis, indent=2)[:3000]

        prompt = f"""You are designing a structured interview for an AI agent that will
represent this hiring manager in candidate matching.

JOB/ROLE CONTEXT:
{job_context}

INDUSTRY: {industry}

Generate exactly {HM_QUESTION_COUNT} interview questions that reveal what CANNOT be learned from a job description:
- What the team culture actually looks like day-to-day
- What made previous hires succeed or fail
- Unwritten requirements (personality, communication style, pace)
- How they make hiring decisions (gut vs structured)
- What would make them overlook a "perfect resume"

Each question should feel conversational. Reference specifics from their job context.

Return JSON array:
[
  {{
    "question": "the question text",
    "purpose": "what this reveals about their hiring preferences",
    "psychometric_target": "one of: culture, dealbreakers, team_dynamics, decision_style, growth_expectations"
  }}
]

Return ONLY valid JSON."""

        try:
            response = self.client.messages.create(
                model="claude-sonnet-4-20250514",
                max_tokens=1500,
                messages=[{"role": "user", "content": prompt}],
            )
            text = response.content[0].text.strip()
            if text.startswith("```"):
                text = text.split("\n", 1)[1].rsplit("```", 1)[0]
            questions = json.loads(text)
            return questions[:HM_QUESTION_COUNT]
        except Exception:
            return self._fallback_hm_questions()

    async def analyze_answer(
        self,
        question: dict,
        answer: str,
        agent_type: str = "talent",
        previous_answers: Optional[list] = None,
    ) -> dict:
        """Analyze a single interview answer for content AND psychometric signals.

        Extracts:
        - Explicit content (what they said)
        - Inferred values (what it reveals)
        - Psychometric signals (HOW they said it)
        - Communication style markers

        Returns analysis dict.
        """
        if not ANTHROPIC_API_KEY:
            return {"content_summary": answer[:200], "signals": []}

        prev_context = ""
        if previous_answers:
            prev_context = "\n".join(
                f"Q: {a['question']}\nA: {a['answer']}" for a in previous_answers[-3:]
            )

        prompt = f"""Analyze this interview answer from a {agent_type}.

QUESTION: {question.get('question', '')}
PURPOSE: {question.get('purpose', '')}
TARGET: {question.get('psychometric_target', '')}

ANSWER: {answer}

{f"PREVIOUS CONTEXT:{chr(10)}{prev_context}" if prev_context else ""}

Analyze both WHAT they said and HOW they said it. Return JSON:
{{
    "content_summary": "brief summary of their actual answer",
    "explicit_values": ["values they directly stated"],
    "inferred_values": ["values implied by their answer"],
    "psychometric_signals": {{
        "communication_style": "direct/diplomatic/analytical/expressive",
        "decision_approach": "gut/structured/collaborative/independent",
        "response_depth": "surface/moderate/deep",
        "emotional_markers": ["any emotional cues detected"]
    }},
    "key_insights": ["1-2 key takeaways for the AI agent to remember"],
    "follow_up_hint": "optional follow-up the agent could ask if needed"
}}

Return ONLY valid JSON."""

        try:
            response = self.client.messages.create(
                model="claude-sonnet-4-20250514",
                max_tokens=800,
                messages=[{"role": "user", "content": prompt}],
            )
            text = response.content[0].text.strip()
            if text.startswith("```"):
                text = text.split("\n", 1)[1].rsplit("```", 1)[0]
            return json.loads(text)
        except Exception:
            return {"content_summary": answer[:200], "signals": []}

    async def compute_interview_quality(self, answers: list[dict]) -> dict:
        """Compute interview quality score from all answers.

        Used for auto-activation readiness scoring.

        Returns:
            {
                "quality_score": 0-100,
                "depth_score": 0-100,
                "consistency_score": 0-100,
                "completeness": float (0-1),
                "ready": bool
            }
        """
        if not answers:
            return {"quality_score": 0, "depth_score": 0, "completeness": 0, "ready": False}

        answered = [a for a in answers if a.get("answer")]
        completeness = len(answered) / len(answers) if answers else 0

        # Depth: average word count as proxy
        avg_words = (
            sum(len(a.get("answer", "").split()) for a in answered) / len(answered)
            if answered
            else 0
        )
        depth_score = min(100, int(avg_words * 2.5))  # 40 words = 100

        # Quality: check for substantive answers (not just "yes/no")
        substantive = sum(1 for a in answered if len(a.get("answer", "").split()) > 10)
        quality_score = int((substantive / len(answers)) * 100) if answers else 0

        # Consistency: check psychometric signals align
        consistency_score = 80  # Default; would need more data for real analysis

        return {
            "quality_score": quality_score,
            "depth_score": depth_score,
            "consistency_score": consistency_score,
            "completeness": completeness,
            "ready": completeness >= 0.7 and quality_score >= 50,
        }

    def _fallback_talent_questions(self) -> list[dict]:
        return [
            {"question": "What kind of work environment brings out your best?", "purpose": "environment preferences", "psychometric_target": "environment"},
            {"question": "Tell me about a time you turned down an opportunity that looked great on paper. What was wrong?", "purpose": "hidden dealbreakers", "psychometric_target": "boundaries"},
            {"question": "What does a great Monday morning look like for you?", "purpose": "motivation and energy sources", "psychometric_target": "motivation"},
            {"question": "How do you prefer to work with others - what's your ideal collaboration style?", "purpose": "teamwork preferences", "psychometric_target": "collaboration"},
            {"question": "What's something about your industry that frustrates you that most people accept?", "purpose": "values and standards", "psychometric_target": "values"},
            {"question": "If you could design your next role from scratch, what would it look like?", "purpose": "career direction", "psychometric_target": "direction"},
            {"question": "What would your closest colleague say is your superpower - and your blind spot?", "purpose": "self-awareness", "psychometric_target": "identity"},
        ]

    def _fallback_hm_questions(self) -> list[dict]:
        return [
            {"question": "Describe the person who thrived most on your team - what made them special?", "purpose": "ideal candidate profile", "psychometric_target": "culture"},
            {"question": "What's the most common reason new hires don't work out in this role?", "purpose": "hidden dealbreakers", "psychometric_target": "dealbreakers"},
            {"question": "How does your team make decisions day-to-day?", "purpose": "team dynamics", "psychometric_target": "team_dynamics"},
            {"question": "What would make you hire someone whose resume doesn't perfectly match the requirements?", "purpose": "flexibility and priorities", "psychometric_target": "decision_style"},
            {"question": "Where do you see this role in 18 months - how will it grow?", "purpose": "growth trajectory", "psychometric_target": "growth_expectations"},
        ]


interview_service = InterviewService()
