import json
from typing import Optional

import anthropic
from supabase import create_client

from app.config import ANTHROPIC_API_KEY, SUPABASE_URL, SUPABASE_SERVICE_KEY, MAX_NEGOTIATION_TOKENS
from app.services.industry_knowledge_modules import industry_knowledge


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
                    # Consensus model: both agents must agree
                    consensus = await self._check_consensus(candidate, job, match)
                    match["consensus"] = consensus
                    if consensus.get("both_agree"):
                        match["status"] = "mutual_agreement"
                        await self._store_match(candidate, job, match)
                        matches.append(match)
                    else:
                        # Store as pending - one side disagreed
                        match["status"] = "pending_consensus"
                        match["score"] = int(match["score"] * 0.7)  # Reduce score for non-consensus
                        await self._store_match(candidate, job, match)

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

        # Enrich with industry knowledge and learned patterns
        industry_context = self._get_industry_context(candidate, job)
        learned_patterns = await self._get_candidate_patterns(candidate)

        prompt = f"""You are the Master AI overseeing a negotiation between two agents.

CANDIDATE AGENT represents:
{candidate_profile}

JOB AGENT represents:
{job_profile}
{industry_context}{learned_patterns}
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

    def _get_industry_context(self, candidate: dict, job: dict) -> str:
        """Build industry expertise context for the negotiation."""
        candidate_industry = (
            candidate.get("profile", {}).get("industry", "")
            or candidate.get("industry", "")
        )
        job_industry = (
            job.get("profile", {}).get("industry", "")
            or job.get("industry", "")
        )

        context_parts = []
        for label, ind in [("CANDIDATE", candidate_industry), ("JOB", job_industry)]:
            if ind:
                module = industry_knowledge.get_module(ind)
                if module.get("skill_benchmarks"):
                    context_parts.append(
                        f"\n{label} INDUSTRY CONTEXT ({ind}):\n"
                        f"- Skill benchmarks: {json.dumps(module['skill_benchmarks'])}\n"
                        f"- Culture signals: {', '.join(module.get('culture_signals', []))}\n"
                        f"- Hidden criteria patterns: {'; '.join(module.get('hidden_criteria', []))}"
                    )

        if context_parts:
            return "\n" + "\n".join(context_parts) + "\n"
        return ""

    async def _get_candidate_patterns(self, candidate: dict) -> str:
        """Fetch previously learned patterns for this candidate."""
        user_id = candidate.get("user_id", candidate.get("id", ""))
        if not user_id:
            return ""

        try:
            result = (
                self.supabase_client.table("cv2_collective_patterns")
                .select("patterns, pattern_type")
                .eq("user_id", user_id)
                .order("created_at", desc=True)
                .limit(5)
                .execute()
            )
            if not result.data:
                return ""

            patterns_summary = []
            for r in result.data:
                p = r.get("patterns", {})
                if r.get("pattern_type") == "hidden_criteria":
                    if p.get("inferred_criteria"):
                        patterns_summary.append(f"- Hidden criteria: {p['inferred_criteria']}")
                    if p.get("values_revealed"):
                        patterns_summary.append(f"- Values: {p['values_revealed']}")
                elif r.get("pattern_type") == "conversation_learning":
                    if p.get("values"):
                        patterns_summary.append(f"- Core values: {', '.join(p['values'][:3])}")
                    if p.get("hidden_criteria"):
                        patterns_summary.append(f"- Unspoken preferences: {', '.join(p['hidden_criteria'][:3])}")

            if patterns_summary:
                return (
                    "\nLEARNED PATTERNS (from previous interactions with this candidate):\n"
                    + "\n".join(patterns_summary) + "\n"
                )
        except Exception:
            pass

        return ""

    async def _check_consensus(self, candidate: dict, job: dict, match: dict) -> dict:
        """Consensus model: both candidate agent and job agent must independently agree.

        Each agent evaluates from their user's perspective whether this match
        should be presented. A match only becomes 'mutual_agreement' when both agree.
        """
        candidate_profile = json.dumps(candidate.get("profile", {}), indent=2)
        job_profile = json.dumps(job.get("profile", {}), indent=2)
        negotiation_result = json.dumps({
            "score": match.get("score"),
            "candidate_synopsis": match.get("candidate_synopsis", {}),
            "hiring_manager_synopsis": match.get("hiring_manager_synopsis", {}),
        }, indent=2)

        prompt = f"""Two AI agents have completed a negotiation about a potential match.
Now each agent must independently decide whether to present this opportunity to their user.

CANDIDATE PROFILE:
{candidate_profile}

JOB PROFILE:
{job_profile}

NEGOTIATION RESULT:
{negotiation_result}

For each agent, answer: Would you recommend presenting this to your user?
Consider: Is it worth their time? Does it align with what you know about them?
Would presenting a weak match erode trust?

Return JSON:
{{
    "candidate_agent_agrees": true/false,
    "candidate_agent_reasoning": "brief explanation",
    "job_agent_agrees": true/false,
    "job_agent_reasoning": "brief explanation",
    "both_agree": true/false
}}"""

        try:
            response = self.anthropic_client.messages.create(
                model="claude-sonnet-4-20250514",
                max_tokens=500,
                messages=[{"role": "user", "content": prompt}],
            )
            text = response.content[0].text.strip()
            if text.startswith("```"):
                text = text.split("\n", 1)[1].rsplit("```", 1)[0]
            result = json.loads(text)
            # Ensure both_agree is consistent
            result["both_agree"] = result.get("candidate_agent_agrees", False) and result.get("job_agent_agrees", False)
            return result
        except (json.JSONDecodeError, IndexError, Exception):
            # Default: if negotiation score >= 75, assume consensus
            return {
                "candidate_agent_agrees": match.get("score", 0) >= 75,
                "job_agent_agrees": match.get("score", 0) >= 75,
                "both_agree": match.get("score", 0) >= 75,
                "reasoning": "Fallback consensus based on score threshold",
            }

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
            "status": match.get("status", "mutual_agreement"),
            "candidate_synopsis": match.get("candidate_synopsis", {}),
            "hiring_manager_synopsis": match.get("hiring_manager_synopsis", {}),
            "negotiation_notes": match.get("negotiation_notes", ""),
            "consensus": match.get("consensus", {}),
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
