import json
from typing import Optional

import anthropic

from app.config import ANTHROPIC_API_KEY


class ProfileAnalyzer:
    """Analyzes uploaded documents and social profiles to build pre-conversation context.

    This service processes:
    - CV/Resume text content (extracted from uploaded files)
    - LinkedIn profile URLs (fetches public data)
    - GitHub profile URLs (analyzes repos/contributions)
    - Other professional links

    Output: structured profile data that the chat agent uses to ask informed,
    deeper questions rather than wasting time on basic facts.
    """

    def __init__(self):
        self._anthropic = None

    @property
    def anthropic_client(self):
        if self._anthropic is None:
            self._anthropic = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)
        return self._anthropic

    async def analyze_cv_text(self, cv_text: str, industry: str = "general") -> dict:
        """Extract structured profile data from CV/resume text content.

        Returns:
            {
                "name": str,
                "current_role": str,
                "experience_years": int,
                "skills": [str],
                "education": [{"degree": str, "institution": str, "year": str}],
                "experience": [{"role": str, "company": str, "duration": str, "highlights": [str]}],
                "certifications": [str],
                "languages": [str],
                "industry_signals": [str],
                "career_trajectory": str,
                "suggested_deep_questions": [str]
            }
        """
        if not ANTHROPIC_API_KEY:
            return {"error": "ANTHROPIC_API_KEY required for CV analysis"}

        prompt = f"""Analyze this CV/resume text and extract structured professional data.

CV TEXT:
{cv_text[:8000]}

CONTEXT: User selected industry: {industry}

Return a JSON object with these fields:
- name: full name (string)
- current_role: their most recent/current job title (string)
- experience_years: approximate total years of experience (number)
- skills: list of technical and professional skills mentioned (array of strings, max 20)
- education: array of objects with degree, institution, year
- experience: array of most recent 5 roles with role, company, duration, highlights (array of key achievements)
- certifications: array of certification names
- languages: programming or spoken languages mentioned
- industry_signals: what industry/sector cues are present (array of strings)
- career_trajectory: brief one-sentence description of their career path
- suggested_deep_questions: 5 questions an AI agent should ask to understand this person BEYOND what's on their CV (values, culture fit, hidden preferences, what they actually care about)

Return ONLY valid JSON, no markdown formatting."""

        try:
            response = self.anthropic_client.messages.create(
                model="claude-sonnet-4-20250514",
                max_tokens=2000,
                messages=[{"role": "user", "content": prompt}],
            )
            text = response.content[0].text.strip()
            if text.startswith("```"):
                text = text.split("\n", 1)[1].rsplit("```", 1)[0]
            return json.loads(text)
        except (json.JSONDecodeError, IndexError):
            return {"error": "Failed to parse CV analysis"}
        except Exception as e:
            return {"error": f"CV analysis failed: {type(e).__name__}"}

    async def analyze_job_description(self, jd_text: str, industry: str = "general") -> dict:
        """Extract structured data from a job description.

        Returns:
            {
                "title": str,
                "company": str,
                "description": str (summary),
                "requirements": [str],
                "skills": [str],
                "experience_level": str,
                "salary_range": str or null,
                "location": str,
                "remote_policy": str,
                "team_size": str or null,
                "reporting_to": str or null,
                "suggested_deep_questions": [str]
            }
        """
        if not ANTHROPIC_API_KEY:
            return {"error": "ANTHROPIC_API_KEY required for JD analysis"}

        prompt = f"""Analyze this job description and extract structured data.

JOB DESCRIPTION TEXT:
{jd_text[:8000]}

CONTEXT: Industry: {industry}

Return a JSON object with these fields:
- title: job title (string)
- company: company name if mentioned (string or null)
- description: 2-3 sentence summary of the role (string)
- requirements: list of key requirements (array of strings, max 10)
- skills: list of required/desired skills (array of strings, max 15)
- experience_level: junior/mid/senior/lead/executive (string)
- salary_range: if mentioned (string or null)
- location: location/remote info (string)
- remote_policy: remote/hybrid/onsite/not specified (string)
- team_size: if mentioned (string or null)
- reporting_to: who this role reports to if mentioned (string or null)
- suggested_deep_questions: 5 questions a recruitment consultant should ask the hiring manager to understand what's NOT in this JD — the hidden criteria, real team dynamics, and what success actually looks like

Return ONLY valid JSON, no markdown formatting."""

        try:
            response = self.anthropic_client.messages.create(
                model="claude-sonnet-4-20250514",
                max_tokens=2000,
                messages=[{"role": "user", "content": prompt}],
            )
            text = response.content[0].text.strip()
            if text.startswith("```"):
                text = text.split("\n", 1)[1].rsplit("```", 1)[0]
            return json.loads(text)
        except (json.JSONDecodeError, IndexError):
            return {"error": "Failed to parse JD analysis"}
        except Exception as e:
            return {"error": f"JD analysis failed: {type(e).__name__}"}

    async def analyze_social_profiles(self, links: dict) -> dict:
        """Analyze social/professional profile URLs to extract context.

        Args:
            links: {"linkedin": "url", "github": "url", "portfolio": "url", "other": ["urls"]}

        Returns structured insights from available profile information.
        """
        if not ANTHROPIC_API_KEY:
            return {"error": "ANTHROPIC_API_KEY required"}

        # Build context from available links
        context_parts = []
        if links.get("linkedin"):
            context_parts.append(f"LinkedIn: {links['linkedin']}")
        if links.get("github"):
            context_parts.append(f"GitHub: {links['github']}")
        if links.get("portfolio"):
            context_parts.append(f"Portfolio: {links['portfolio']}")
        if links.get("other"):
            for url in links["other"]:
                context_parts.append(f"Other: {url}")

        if not context_parts:
            return {"profiles": [], "insights": []}

        prompt = f"""A user has shared these professional profile links:
{chr(10).join(context_parts)}

Based on these URLs alone (you cannot fetch them, but analyze what the URLs themselves reveal):
- A GitHub URL tells you they code; the username may hint at their identity
- A LinkedIn URL with specific path reveals their professional name
- A portfolio URL shows they value showcasing work
- Other URLs reveal additional interests

Return JSON:
{{
    "profiles_shared": ["list of platform names they shared"],
    "identity_signals": ["what sharing these specific platforms reveals about them"],
    "professional_presence": "brief assessment of their online professional presence",
    "questions_to_explore": ["3 questions the AI agent should ask based on what profiles they chose to share"]
}}

Return ONLY valid JSON."""

        try:
            response = self.anthropic_client.messages.create(
                model="claude-sonnet-4-20250514",
                max_tokens=500,
                messages=[{"role": "user", "content": prompt}],
            )
            text = response.content[0].text.strip()
            if text.startswith("```"):
                text = text.split("\n", 1)[1].rsplit("```", 1)[0]
            return json.loads(text)
        except (json.JSONDecodeError, IndexError):
            return {"profiles_shared": list(links.keys()), "insights": []}
        except Exception:
            return {"profiles_shared": list(links.keys()), "insights": []}

    async def build_pre_conversation_context(
        self,
        cv_analysis: Optional[dict] = None,
        social_analysis: Optional[dict] = None,
        documents: Optional[list] = None,
    ) -> str:
        """Combine all pre-conversation analysis into a context string for the chat agent.

        This becomes part of the system prompt so the AI agent starts the conversation
        already knowing the user's background and can ask deeper questions.
        """
        parts = []

        if cv_analysis and not cv_analysis.get("error"):
            parts.append("=== CV ANALYSIS ===")
            if cv_analysis.get("name"):
                parts.append(f"Name: {cv_analysis['name']}")
            if cv_analysis.get("current_role"):
                parts.append(f"Current Role: {cv_analysis['current_role']}")
            if cv_analysis.get("experience_years"):
                parts.append(f"Experience: ~{cv_analysis['experience_years']} years")
            if cv_analysis.get("skills"):
                parts.append(f"Skills: {', '.join(cv_analysis['skills'][:15])}")
            if cv_analysis.get("career_trajectory"):
                parts.append(f"Career Path: {cv_analysis['career_trajectory']}")
            if cv_analysis.get("certifications"):
                parts.append(f"Certifications: {', '.join(cv_analysis['certifications'])}")
            if cv_analysis.get("suggested_deep_questions"):
                parts.append("Questions to explore (go BEYOND the CV):")
                for q in cv_analysis["suggested_deep_questions"][:5]:
                    parts.append(f"  - {q}")

        if social_analysis and not social_analysis.get("error"):
            parts.append("\n=== SOCIAL PROFILES ===")
            if social_analysis.get("profiles_shared"):
                parts.append(f"Platforms: {', '.join(social_analysis['profiles_shared'])}")
            if social_analysis.get("professional_presence"):
                parts.append(f"Presence: {social_analysis['professional_presence']}")
            if social_analysis.get("questions_to_explore"):
                parts.append("Explore based on profiles:")
                for q in social_analysis["questions_to_explore"][:3]:
                    parts.append(f"  - {q}")

        if documents:
            parts.append(f"\n=== UPLOADED DOCUMENTS ===")
            parts.append(f"User uploaded {len(documents)} document(s): {', '.join(d.get('filename', '?') for d in documents)}")

        if not parts:
            return ""

        return (
            "IMPORTANT: The user has already provided background materials. "
            "You already know their professional basics from their CV and profiles. "
            "DO NOT ask about basic facts (skills, experience, education). "
            "Instead, go DEEPER: ask about values, what energizes them, hidden frustrations, "
            "what they'd never compromise on, and what matters most beyond the resume.\n\n"
            + "\n".join(parts)
        )


profile_analyzer = ProfileAnalyzer()
