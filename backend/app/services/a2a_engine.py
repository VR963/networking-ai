import json
from typing import Optional

import anthropic
from supabase import create_client

from app.config import ANTHROPIC_API_KEY, SUPABASE_URL, SUPABASE_SERVICE_KEY, MAX_NEGOTIATION_TOKENS


class A2AEngine:
    """Agent-to-Agent matching engine.

    Orchestrates negotiations between candidate agents and job agents,
    generating match scores and synopses for both perspectives.
    """

    def __init__(self):
        self._anthropic = None
        self._supabase = None

    @property
    def anthropic_client(self):
        if self._anthropic is None:
            self._anthropic = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)
        return self._anthropic

    @property
    def supabase_client(self):
        if self._supabase is None:
            if not SUPABASE_URL or not SUPABASE_SERVICE_KEY:
                raise RuntimeError("SUPABASE_URL and SUPABASE_SERVICE_KEY environment variables are required")
            self._supabase = create_client(SUPABASE_URL, SUPABASE_SERVICE_KEY)
        return self._supabase

    async def run_matching(self) -> dict:
        candidates = await self._get_candidates()
        jobs = await self._get_jobs()

        matches = []
        for candidate in candidates:
            for job in jobs:
                match = await self._deep_negotiation(candidate, job)
                if match and match.get("score", 0) >= 60:
                    await self._store_match(candidate, job, match)
                    matches.append(match)

        return {"matches_found": len(matches), "matches": matches}

    async def _get_candidates(self) -> list[dict]:
        result = (
            self.supabase_client.table("cv2_a2a_candidates")
            .select("*")
            .execute()
        )
        return result.data or []

    async def _get_jobs(self) -> list[dict]:
        result = (
            self.supabase_client.table("cv2_a2a_jobs")
            .select("*")
            .execute()
        )
        return result.data or []

    async def _deep_negotiation(self, candidate: dict, job: dict) -> Optional[dict]:
        candidate_profile = json.dumps(candidate.get("profile", {}), indent=2)
        job_profile = json.dumps(job.get("profile", {}), indent=2)

        prompt = f"""You are the Master AI overseeing a negotiation between two agents.

CANDIDATE AGENT represents:
{candidate_profile}

JOB AGENT represents:
{job_profile}

Conduct a deep negotiation between these agents. Consider:
1. Skills alignment (both hard and soft skills)
2. Values alignment (culture, work style, goals)
3. Growth potential (can this person grow into the role?)
4. Hidden criteria (what might each party not say explicitly?)

Return a JSON object with:
{{
    "score": <0-100 match score>,
    "match_level": "<no_match|weak_match|moderate_match|strong_match|exceptional_match>",
    "candidate_synopsis": {{
        "my_take": "<2-3 sentences from candidate agent perspective - why this is good for the candidate>",
        "heads_up": "<1-2 things the candidate should know>",
        "question_to_consider": "<one thoughtful question for the candidate>"
    }},
    "hiring_manager_synopsis": {{
        "summary": "<2-3 sentences from HM perspective - why this candidate>",
        "key_alignments": ["<strength 1>", "<strength 2>", "<strength 3>"],
        "concerns": ["<concern 1>", "<concern 2>"],
        "recommended_questions": ["<interview question 1>", "<interview question 2>"]
    }},
    "negotiation_notes": "<brief summary of the negotiation>"
}}"""

        response = self.anthropic_client.messages.create(
            model="claude-sonnet-4-20250514",
            max_tokens=MAX_NEGOTIATION_TOKENS,
            messages=[{"role": "user", "content": prompt}],
        )

        try:
            text = response.content[0].text.strip()
            if text.startswith("```"):
                text = text.split("\n", 1)[1].rsplit("```", 1)[0]
            return json.loads(text)
        except (json.JSONDecodeError, IndexError):
            return None

    async def _store_match(self, candidate: dict, job: dict, match: dict) -> None:
        candidate_id = candidate.get("user_id", candidate.get("id", ""))
        job_id = job.get("job_id", job.get("id", ""))
        match_id = f"{candidate_id}_{job_id}"

        record = {
            "id": match_id,
            "candidate_id": candidate_id,
            "job_id": job_id,
            "score": match.get("score", 0),
            "match_level": match.get("match_level", "no_match"),
            "candidate_synopsis": match.get("candidate_synopsis", {}),
            "hiring_manager_synopsis": match.get("hiring_manager_synopsis", {}),
            "negotiation_notes": match.get("negotiation_notes", ""),
        }
        self.supabase_client.table("cv2_a2a_matches").upsert(record).execute()

    async def get_status(self) -> dict:
        candidates = await self._get_candidates()
        jobs = await self._get_jobs()
        matches_result = (
            self.supabase_client.table("cv2_a2a_matches")
            .select("id, score, match_level")
            .execute()
        )
        return {
            "candidates": len(candidates),
            "jobs": len(jobs),
            "matches": len(matches_result.data or []),
        }

    async def get_match(self, match_id: str) -> Optional[dict]:
        result = (
            self.supabase_client.table("cv2_a2a_matches")
            .select("*")
            .eq("id", match_id)
            .execute()
        )
        if result.data:
            return result.data[0]
        return None


a2a_engine = A2AEngine()
