"""Multi-Round Negotiation Protocol - Agents negotiate in structured rounds.

Replaces single-shot matching with a 3-round negotiation:

Round 1: Surface Compatibility (skills, experience, basics)
  → Can REJECT early if fundamental mismatch
  → Low token cost (~300 tokens)

Round 2: Values & Culture Alignment
  → Agents argue from their user's perspective
  → Medium token cost (~600 tokens)

Round 3: Deep Fit (hidden criteria, growth, gut check)
  → Full negotiation with personality
  → Higher token cost (~1000 tokens)

Each round produces a partial score. Final score is weighted:
  Round 1: 30% | Round 2: 40% | Round 3: 30%

Early rejection at any round saves tokens and prevents weak matches.
"""

import json
from typing import Optional

import anthropic

from app.config import ANTHROPIC_API_KEY, MAX_NEGOTIATION_TOKENS


ROUND_1_THRESHOLD = 40  # Minimum score to proceed to round 2
ROUND_2_THRESHOLD = 50  # Minimum score to proceed to round 3
FINAL_THRESHOLD = 60    # Minimum final score for a valid match


class NegotiationProtocol:
    """Manages multi-round negotiations between agent pairs."""

    def __init__(self):
        self._anthropic = None

    @property
    def client(self):
        if self._anthropic is None:
            self._anthropic = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)
        return self._anthropic

    async def negotiate(
        self,
        talent_agent: dict,
        hm_agent: dict,
        discovery_context: Optional[dict] = None,
    ) -> dict:
        """Run full multi-round negotiation between two agents.

        Args:
            talent_agent: Full agent record with profile
            hm_agent: Full agent record with profile
            discovery_context: Pre-filter results (compatibility_score, reasons)

        Returns:
            {
                "status": "matched|rejected|partial",
                "final_score": 0-100,
                "rounds": [round1_result, round2_result, round3_result],
                "rejection_round": null or 1/2/3,
                "candidate_synopsis": {...},
                "hm_synopsis": {...},
                "negotiation_log": "summary of the negotiation"
            }
        """
        if not ANTHROPIC_API_KEY:
            return {"status": "error", "detail": "API key required"}

        talent_profile = talent_agent.get("profile", {})
        hm_profile = hm_agent.get("profile", {})

        # Extract agent personalities
        talent_personality = talent_profile.get("agent_personality", "Professional and balanced")
        hm_personality = hm_profile.get("agent_personality", "Professional and selective")

        # Round 1: Surface Compatibility
        r1 = await self._round_1_surface(talent_profile, hm_profile)
        if r1.get("score", 0) < ROUND_1_THRESHOLD:
            return {
                "status": "rejected",
                "final_score": r1["score"],
                "rounds": [r1],
                "rejection_round": 1,
                "rejection_reason": r1.get("reason", "Fundamental skills/experience mismatch"),
                "negotiation_log": f"Rejected at Round 1: {r1.get('reason', 'mismatch')}",
            }

        # Round 2: Values & Culture
        r2 = await self._round_2_values(
            talent_profile, hm_profile, talent_personality, hm_personality, r1
        )
        if r2.get("score", 0) < ROUND_2_THRESHOLD:
            combined = int(r1["score"] * 0.5 + r2["score"] * 0.5)
            return {
                "status": "rejected",
                "final_score": combined,
                "rounds": [r1, r2],
                "rejection_round": 2,
                "rejection_reason": r2.get("reason", "Values/culture misalignment"),
                "negotiation_log": f"Rejected at Round 2: {r2.get('reason', 'misalignment')}",
            }

        # Round 3: Deep Fit
        r3 = await self._round_3_deep(
            talent_profile, hm_profile, talent_personality, hm_personality, r1, r2
        )

        # Final weighted score
        final_score = int(r1["score"] * 0.3 + r2["score"] * 0.4 + r3["score"] * 0.3)

        if final_score < FINAL_THRESHOLD:
            return {
                "status": "partial",
                "final_score": final_score,
                "rounds": [r1, r2, r3],
                "rejection_round": None,
                "negotiation_log": f"Completed all rounds but below threshold ({final_score}<{FINAL_THRESHOLD})",
            }

        # Build synopses from round 3
        return {
            "status": "matched",
            "final_score": final_score,
            "rounds": [r1, r2, r3],
            "rejection_round": None,
            "candidate_synopsis": r3.get("candidate_synopsis", {}),
            "hm_synopsis": r3.get("hm_synopsis", {}),
            "negotiation_log": r3.get("negotiation_summary", "Match found through 3-round negotiation"),
            "match_level": self._score_to_level(final_score),
        }

    async def _round_1_surface(self, talent: dict, hm: dict) -> dict:
        """Round 1: Quick skills and experience compatibility check."""
        talent_summary = {
            "skills": talent.get("skills_verified", [])[:10],
            "synopsis": talent.get("synopsis", ""),
            "environment": talent.get("environment_preferences", {}),
        }
        hm_summary = {
            "requirements": hm.get("role_requirements", {}),
            "synopsis": hm.get("synopsis", ""),
            "team_culture": hm.get("team_culture", {}),
        }

        prompt = f"""ROUND 1: Surface Compatibility Check

TALENT: {json.dumps(talent_summary)}
ROLE: {json.dumps(hm_summary)}

Quick check: Does this person have the fundamental skills and experience for this role?
Consider must-have requirements vs verified skills.

Return JSON:
{{
    "score": 0-100,
    "skills_match": "strong/moderate/weak/none",
    "experience_fit": "overqualified/right-level/stretch/underqualified",
    "proceed": true/false,
    "reason": "1-sentence explanation"
}}
Return ONLY JSON."""

        return await self._call_round(prompt, max_tokens=300)

    async def _round_2_values(
        self, talent: dict, hm: dict,
        talent_personality: str, hm_personality: str,
        r1: dict
    ) -> dict:
        """Round 2: Values and culture alignment negotiation."""
        talent_values = {
            "values": talent.get("values", []),
            "dealbreakers": talent.get("dealbreakers", []),
            "communication_style": talent.get("communication_style", {}),
            "negotiation_priorities": talent.get("negotiation_priorities", []),
        }
        hm_values = {
            "team_culture": hm.get("team_culture", {}),
            "hidden_preferences": hm.get("hidden_preferences", []),
            "dealbreakers": hm.get("dealbreakers", []),
            "decision_profile": hm.get("decision_profile", {}),
        }

        prompt = f"""ROUND 2: Values & Culture Negotiation

CONTEXT FROM ROUND 1: Skills match = {r1.get('skills_match', 'unknown')}, {r1.get('reason', '')}

TALENT AGENT (style: {talent_personality}) represents:
{json.dumps(talent_values)}

HM AGENT (style: {hm_personality}) represents:
{json.dumps(hm_values)}

Negotiate from each agent's perspective:
- Talent agent: Would my user's values clash with this culture?
- HM agent: Does this person's style match what we really need?
- Check dealbreakers on BOTH sides

Return JSON:
{{
    "score": 0-100,
    "values_alignment": "strong/moderate/weak/conflicting",
    "culture_fit": "natural/adaptable/stretch/mismatch",
    "dealbreaker_hit": true/false,
    "talent_agent_concern": "main concern from talent perspective or null",
    "hm_agent_concern": "main concern from HM perspective or null",
    "proceed": true/false,
    "reason": "1-sentence explanation"
}}
Return ONLY JSON."""

        return await self._call_round(prompt, max_tokens=500)

    async def _round_3_deep(
        self, talent: dict, hm: dict,
        talent_personality: str, hm_personality: str,
        r1: dict, r2: dict
    ) -> dict:
        """Round 3: Deep fit analysis with full agent personalities."""
        prompt = f"""ROUND 3: Deep Fit Negotiation

PREVIOUS ROUNDS:
- Round 1: Score {r1.get('score')}, {r1.get('reason', '')}
- Round 2: Score {r2.get('score')}, {r2.get('reason', '')}
  Talent concern: {r2.get('talent_agent_concern', 'none')}
  HM concern: {r2.get('hm_agent_concern', 'none')}

TALENT AGENT (personality: {talent_personality}) full profile:
- About: {talent.get('about', '')[:500]}
- Psychometric: {json.dumps(talent.get('psychometric_profile', {}))}
- Priorities: {talent.get('negotiation_priorities', [])}

HM AGENT (personality: {hm_personality}) full profile:
- About: {hm.get('about', '')[:500]}
- Decision weights: {json.dumps(hm.get('decision_profile', {}).get('weights', {}))}
- Green flags: {hm.get('decision_profile', {}).get('green_flags', [])}
- Offer flexibility: {json.dumps(hm.get('offer_flexibility', {}))}

Now conduct the deep negotiation. Each agent argues for their user:
- Talent agent: Is this truly where my user will thrive? Growth potential?
- HM agent: Will this person succeed long-term? What's the gut check?
- Consider hidden criteria, personality fit, growth trajectory

Return JSON:
{{
    "score": 0-100,
    "deep_fit": "exceptional/strong/moderate/uncertain/poor",
    "growth_potential": "high/moderate/limited",
    "long_term_success": "likely/possible/unlikely",
    "candidate_synopsis": {{
        "recommendation": "2-sentence recommendation for the candidate",
        "what_excites": "what about this role would excite them",
        "watch_out": "what to be cautious about"
    }},
    "hm_synopsis": {{
        "recommendation": "2-sentence recommendation for the HM",
        "standout_quality": "what makes this candidate special",
        "risk_factor": "potential concern to probe in interview"
    }},
    "negotiation_summary": "2-3 sentence summary of how the agents negotiated",
    "reason": "final verdict in one sentence"
}}
Return ONLY JSON."""

        return await self._call_round(prompt, max_tokens=1000)

    async def _call_round(self, prompt: str, max_tokens: int = 500) -> dict:
        """Execute a negotiation round via Claude."""
        try:
            response = self.client.messages.create(
                model="claude-sonnet-4-20250514",
                max_tokens=max_tokens,
                messages=[{"role": "user", "content": prompt}],
            )
            text = response.content[0].text.strip()
            if text.startswith("```"):
                text = text.split("\n", 1)[1].rsplit("```", 1)[0]
            return json.loads(text)
        except (json.JSONDecodeError, IndexError):
            return {"score": 50, "reason": "Parse error", "proceed": True}
        except Exception as e:
            return {"score": 0, "reason": f"Error: {type(e).__name__}", "proceed": False}

    def _score_to_level(self, score: int) -> str:
        if score >= 85:
            return "exceptional_match"
        elif score >= 75:
            return "strong_match"
        elif score >= 65:
            return "moderate_match"
        elif score >= 55:
            return "weak_match"
        return "no_match"


negotiation_protocol = NegotiationProtocol()
