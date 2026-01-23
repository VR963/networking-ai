"""AI Profile Generation Service - Creates agent profiles from interview + context data.

Generates structured profiles for both Talent and HM agents:
- 3-paragraph "about" (as if the person wrote it)
- Synopsis (quick match summary)
- Communication style profile
- Psychometric profile
- Values/dealbreakers/priorities

These profiles are what agents USE during A2A negotiations.
"""

import json
from typing import Optional

import anthropic

from app.config import ANTHROPIC_API_KEY


class AIProfileService:
    def __init__(self):
        self._anthropic = None

    @property
    def client(self):
        if self._anthropic is None:
            self._anthropic = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)
        return self._anthropic

    async def generate_talent_profile(
        self,
        cv_analysis: Optional[dict],
        interview_answers: list[dict],
        industry: str = "general",
    ) -> dict:
        """Generate a complete AI agent profile for a talent.

        Combines CV facts with interview insights to create a rich representation
        that the agent uses to represent the person in negotiations.

        Returns:
            {
                "about": "3-paragraph first-person description",
                "synopsis": "2-sentence match summary",
                "skills_verified": [...],
                "values": [...],
                "dealbreakers": [...],
                "environment_preferences": {...},
                "communication_style": {...},
                "psychometric_profile": {...},
                "negotiation_priorities": [...],
                "agent_personality": "how the agent should behave in negotiations"
            }
        """
        if not ANTHROPIC_API_KEY:
            return self._basic_talent_profile(cv_analysis, interview_answers)

        cv_context = json.dumps(cv_analysis or {}, indent=2)[:2000]
        interview_context = json.dumps(interview_answers[:7], indent=2)[:3000]

        prompt = f"""Generate a complete AI agent profile for a talent/candidate.

CV ANALYSIS:
{cv_context}

INTERVIEW ANSWERS (questions + answers + analysis):
{interview_context}

INDUSTRY: {industry}

Create a comprehensive profile that an AI agent will use to represent this person
in job negotiations. The profile should capture WHO they are, not just what they do.

Return JSON:
{{
    "about": "3-paragraph first-person description written AS the person. Natural, authentic voice. Para 1: who they are professionally. Para 2: what drives them. Para 3: what they're looking for.",
    "synopsis": "2-sentence summary for quick matching. Include role focus + key differentiator.",
    "skills_verified": ["top 10 skills confirmed by CV + interview"],
    "values": ["top 5 core professional values revealed by interview"],
    "dealbreakers": ["things that would make them reject an opportunity, inferred from interview"],
    "environment_preferences": {{
        "pace": "fast/moderate/measured",
        "structure": "structured/flexible/autonomous",
        "team_size": "small/medium/large/any",
        "remote_preference": "remote/hybrid/onsite/flexible",
        "culture_type": "startup/corporate/agency/nonprofit/any"
    }},
    "communication_style": {{
        "primary": "direct/diplomatic/analytical/expressive",
        "decision_making": "quick/deliberate/collaborative",
        "conflict_approach": "confrontational/avoidant/mediating/pragmatic",
        "feedback_preference": "blunt/gentle/data-driven"
    }},
    "psychometric_profile": {{
        "openness": "high/moderate/low",
        "conscientiousness": "high/moderate/low",
        "extraversion": "high/moderate/low",
        "agreeableness": "high/moderate/low",
        "neuroticism": "high/moderate/low",
        "dominant_trait": "the most defining personality characteristic"
    }},
    "negotiation_priorities": ["ordered list of what matters most in a role: compensation, growth, impact, flexibility, team, etc."],
    "agent_personality": "1-2 sentences describing how the AI agent should behave when representing this person - their tone, assertiveness level, what to emphasize"
}}

Return ONLY valid JSON."""

        try:
            response = self.client.messages.create(
                model="claude-sonnet-4-20250514",
                max_tokens=2500,
                messages=[{"role": "user", "content": prompt}],
            )
            text = response.content[0].text.strip()
            if text.startswith("```"):
                text = text.split("\n", 1)[1].rsplit("```", 1)[0]
            return json.loads(text)
        except Exception:
            return self._basic_talent_profile(cv_analysis, interview_answers)

    async def generate_hm_profile(
        self,
        job_description: dict,
        interview_answers: list[dict],
        industry: str = "general",
    ) -> dict:
        """Generate a complete AI agent profile for a hiring manager.

        Combines job description with interview insights to create a profile
        the HM agent uses to evaluate and negotiate with talent agents.

        Returns:
            {
                "about": "what this role/team is about",
                "synopsis": "2-sentence role summary for matching",
                "role_requirements": {...},
                "team_culture": {...},
                "hidden_preferences": [...],
                "dealbreakers": [...],
                "communication_style": {...},
                "decision_profile": {...},
                "offer_flexibility": {...},
                "agent_personality": "how the HM agent should behave"
            }
        """
        if not ANTHROPIC_API_KEY:
            return self._basic_hm_profile(job_description, interview_answers)

        job_context = json.dumps(job_description or {}, indent=2)[:2000]
        interview_context = json.dumps(interview_answers[:5], indent=2)[:3000]

        prompt = f"""Generate a complete AI agent profile for a hiring manager/role.

JOB DESCRIPTION:
{job_context}

INTERVIEW ANSWERS (questions + answers + analysis):
{interview_context}

INDUSTRY: {industry}

Create a comprehensive profile that an AI agent will use to evaluate candidates
and negotiate on behalf of this hiring manager. Capture the REAL requirements,
not just the job posting.

Return JSON:
{{
    "about": "2-paragraph description of the role and team. Para 1: what the team does and the role's impact. Para 2: what kind of person thrives here.",
    "synopsis": "2-sentence summary for matching. Role + what makes it unique.",
    "role_requirements": {{
        "must_have": ["non-negotiable skills/experience"],
        "nice_to_have": ["preferred but flexible"],
        "overrated": ["things on the JD that they'd actually overlook for the right person"]
    }},
    "team_culture": {{
        "pace": "fast/moderate/measured",
        "autonomy": "high/moderate/guided",
        "communication": "async/sync/mixed",
        "growth_style": "sink-or-swim/mentored/structured-program",
        "vibe": "1-sentence team personality"
    }},
    "hidden_preferences": ["things not on the JD that actually matter - personality traits, work style, etc."],
    "dealbreakers": ["what would disqualify a candidate regardless of skills"],
    "communication_style": {{
        "interviewing_approach": "structured/conversational/technical-heavy",
        "decision_speed": "fast/deliberate/committee",
        "what_impresses": "what makes a candidate stand out in their eyes"
    }},
    "decision_profile": {{
        "weights": {{
            "skills_match": 0.0-1.0,
            "culture_fit": 0.0-1.0,
            "growth_potential": 0.0-1.0,
            "gut_feeling": 0.0-1.0
        }},
        "red_flags": ["instant disqualifiers"],
        "green_flags": ["instant positives"]
    }},
    "offer_flexibility": {{
        "salary_negotiable": true/false,
        "remote_negotiable": true/false,
        "title_negotiable": true/false,
        "start_date_flexible": true/false
    }},
    "agent_personality": "1-2 sentences on how the HM agent should behave - how selective, how transparent about requirements, tone"
}}

Return ONLY valid JSON."""

        try:
            response = self.client.messages.create(
                model="claude-sonnet-4-20250514",
                max_tokens=2500,
                messages=[{"role": "user", "content": prompt}],
            )
            text = response.content[0].text.strip()
            if text.startswith("```"):
                text = text.split("\n", 1)[1].rsplit("```", 1)[0]
            return json.loads(text)
        except Exception:
            return self._basic_hm_profile(job_description, interview_answers)

    def _basic_talent_profile(self, cv_analysis: Optional[dict], answers: list) -> dict:
        """Fallback profile when API is unavailable."""
        skills = cv_analysis.get("skills", []) if cv_analysis else []
        role = cv_analysis.get("current_role", "Professional") if cv_analysis else "Professional"
        return {
            "about": f"I'm a {role} looking for my next opportunity.",
            "synopsis": f"{role} seeking new challenges.",
            "skills_verified": skills[:10],
            "values": [],
            "dealbreakers": [],
            "environment_preferences": {},
            "communication_style": {"primary": "direct"},
            "psychometric_profile": {},
            "negotiation_priorities": ["growth", "compensation", "team"],
            "agent_personality": "Professional and balanced.",
        }

    def _basic_hm_profile(self, job_desc: Optional[dict], answers: list) -> dict:
        """Fallback profile when API is unavailable."""
        title = job_desc.get("title", "Role") if job_desc else "Role"
        return {
            "about": f"Looking for the right person to join as {title}.",
            "synopsis": f"Hiring for {title}.",
            "role_requirements": {"must_have": [], "nice_to_have": []},
            "team_culture": {},
            "hidden_preferences": [],
            "dealbreakers": [],
            "communication_style": {},
            "decision_profile": {},
            "offer_flexibility": {},
            "agent_personality": "Professional and selective.",
        }


ai_profile_service = AIProfileService()
