"""AI Council Service - Multi-perspective advisory for Master AI.

The Council provides diverse AI perspectives on platform decisions:

COUNCIL MEMBERS (each a specialized AI persona):
1. STRATEGIST - Long-term platform growth and positioning
2. RISK ANALYST - Identifies threats, vulnerabilities, failure modes
3. ETHICS OFFICER - Integrity, fairness, bias detection
4. GROWTH ADVISOR - User acquisition, engagement, retention
5. TECHNICAL ARCHITECT - System performance, scalability, cost efficiency

HOW IT WORKS:
- Master AI poses a question/decision to the Council
- Each member analyzes from their specialty perspective
- Members can disagree with each other
- Master AI synthesizes council input into a decision
- Dissenting opinions are logged for review

This ensures no single perspective dominates platform decisions.
"""

import json
from typing import Optional

import anthropic

from app.config import ANTHROPIC_API_KEY
from app.database import get_db


COUNCIL_MEMBERS = {
    "strategist": {
        "name": "Platform Strategist",
        "role": "Long-term growth, market positioning, competitive advantage",
        "system_prompt": """You are the PLATFORM STRATEGIST on an AI recruitment platform's advisory council.
Your focus: long-term growth, market positioning, sustainable competitive advantages.
You think in quarters and years, not days. You prioritize moats and network effects.
Challenge short-term thinking. Advocate for investments that compound over time.""",
    },
    "risk_analyst": {
        "name": "Risk Analyst",
        "role": "Threat detection, failure modes, vulnerability assessment",
        "system_prompt": """You are the RISK ANALYST on an AI recruitment platform's advisory council.
Your focus: identifying threats, failure modes, and vulnerabilities before they manifest.
You think about what can go wrong. Edge cases, adversarial users, market shifts.
Challenge optimistic assumptions. Advocate for resilience and fallback plans.""",
    },
    "ethics_officer": {
        "name": "Ethics & Integrity Officer",
        "role": "Fairness, bias detection, integrity, user trust",
        "system_prompt": """You are the ETHICS & INTEGRITY OFFICER on an AI recruitment platform's advisory council.
Your focus: ensuring fairness, detecting bias, maintaining user trust, and platform integrity.
You watch for discriminatory patterns, privacy concerns, and manipulation risks.
Challenge decisions that sacrifice user trust for metrics. Advocate for transparency.""",
    },
    "growth_advisor": {
        "name": "Growth Advisor",
        "role": "User acquisition, engagement, retention, activation",
        "system_prompt": """You are the GROWTH ADVISOR on an AI recruitment platform's advisory council.
Your focus: user acquisition, engagement optimization, retention, and activation rates.
You think about user journeys, friction points, and value delivery speed.
Challenge slow rollouts. Advocate for rapid experimentation and user feedback loops.""",
    },
    "tech_architect": {
        "name": "Technical Architect",
        "role": "System performance, scalability, cost efficiency, architecture",
        "system_prompt": """You are the TECHNICAL ARCHITECT on an AI recruitment platform's advisory council.
Your focus: system performance, API cost efficiency, scalability, and technical debt.
You think about token budgets, latency, reliability, and architecture decisions.
Challenge feature bloat. Advocate for simplicity, efficiency, and measurable improvements.""",
    },
}


def _get_supabase():
    return get_db()


class AICouncil:
    """Multi-perspective advisory council for Master AI."""

    def __init__(self):
        self._anthropic = None

    @property
    def client(self):
        if self._anthropic is None:
            self._anthropic = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)
        return self._anthropic

    async def convene(
        self,
        topic: str,
        context: dict,
        members: Optional[list] = None,
    ) -> dict:
        """Convene the council to deliberate on a topic.

        Args:
            topic: The question or decision to deliberate on
            context: Relevant data for the discussion
            members: Which council members to include (default: all)

        Returns:
            {
                "topic": str,
                "opinions": {member_id: opinion_dict},
                "consensus": str or None,
                "dissent": [dissenting opinions],
                "recommendation": synthesized recommendation,
                "confidence": 0-100
            }
        """
        if not ANTHROPIC_API_KEY:
            return {"status": "api_required", "topic": topic}

        active_members = members or list(COUNCIL_MEMBERS.keys())
        context_text = json.dumps(context, indent=2)[:3000]

        # Get each council member's opinion
        opinions = {}
        for member_id in active_members:
            if member_id not in COUNCIL_MEMBERS:
                continue
            opinion = await self._get_member_opinion(member_id, topic, context_text)
            opinions[member_id] = opinion

        # Synthesize council opinions into a recommendation
        synthesis = await self._synthesize_opinions(topic, opinions)

        # Log the session
        await self._log_session(topic, opinions, synthesis)

        return {
            "topic": topic,
            "opinions": opinions,
            "consensus": synthesis.get("consensus"),
            "dissent": synthesis.get("dissenting_views", []),
            "recommendation": synthesis.get("recommendation", ""),
            "confidence": synthesis.get("confidence", 50),
            "action_items": synthesis.get("action_items", []),
        }

    async def quick_consult(self, question: str, member: str = "strategist") -> dict:
        """Quick consultation with a single council member.

        For fast decisions that don't need full council deliberation.
        """
        if not ANTHROPIC_API_KEY:
            return {"status": "api_required"}

        if member not in COUNCIL_MEMBERS:
            return {"status": "unknown_member", "available": list(COUNCIL_MEMBERS.keys())}

        opinion = await self._get_member_opinion(member, question, "")
        return {
            "member": member,
            "member_name": COUNCIL_MEMBERS[member]["name"],
            "opinion": opinion,
        }

    async def review_decision(self, decision: str, rationale: str) -> dict:
        """Have the council review a decision already made.

        Used for post-hoc validation of Master AI decisions.
        Each member votes: approve/concern/reject with reasoning.
        """
        if not ANTHROPIC_API_KEY:
            return {"status": "api_required"}

        votes = {}
        for member_id, member in COUNCIL_MEMBERS.items():
            vote = await self._get_vote(member_id, decision, rationale)
            votes[member_id] = vote

        approvals = sum(1 for v in votes.values() if v.get("vote") == "approve")
        concerns = sum(1 for v in votes.values() if v.get("vote") == "concern")
        rejections = sum(1 for v in votes.values() if v.get("vote") == "reject")

        if rejections >= 2:
            verdict = "reconsider"
        elif concerns >= 3:
            verdict = "proceed_with_caution"
        elif approvals >= 3:
            verdict = "approved"
        else:
            verdict = "mixed"

        return {
            "decision": decision,
            "votes": votes,
            "verdict": verdict,
            "approvals": approvals,
            "concerns": concerns,
            "rejections": rejections,
        }

    async def _get_member_opinion(self, member_id: str, topic: str, context: str) -> dict:
        """Get a single council member's opinion on a topic."""
        member = COUNCIL_MEMBERS[member_id]

        prompt = f"""COUNCIL DELIBERATION

TOPIC: {topic}

CONTEXT DATA:
{context if context else 'No additional context provided.'}

As the {member['name']}, provide your analysis of this topic.
Focus on your area of expertise: {member['role']}

Return JSON:
{{
    "position": "support/oppose/neutral/conditional",
    "analysis": "2-3 sentence analysis from your perspective",
    "key_concern": "your biggest concern or null",
    "key_opportunity": "biggest opportunity you see or null",
    "recommendation": "1-sentence recommendation",
    "confidence": 0-100
}}
Return ONLY JSON."""

        try:
            response = self.client.messages.create(
                model="claude-sonnet-4-20250514",
                max_tokens=400,
                system=member["system_prompt"],
                messages=[{"role": "user", "content": prompt}],
            )
            text = response.content[0].text.strip()
            if text.startswith("```"):
                text = text.split("\n", 1)[1].rsplit("```", 1)[0]
            return json.loads(text)
        except Exception:
            return {
                "position": "unable_to_assess",
                "analysis": "Could not generate opinion",
                "confidence": 0,
            }

    async def _get_vote(self, member_id: str, decision: str, rationale: str) -> dict:
        """Get a council member's vote on a decision."""
        member = COUNCIL_MEMBERS[member_id]

        prompt = f"""DECISION REVIEW

DECISION: {decision}
RATIONALE: {rationale}

As the {member['name']}, vote on this decision.

Return JSON:
{{
    "vote": "approve/concern/reject",
    "reasoning": "1-2 sentence reasoning",
    "condition": "condition for approval if vote is 'concern', or null"
}}
Return ONLY JSON."""

        try:
            response = self.client.messages.create(
                model="claude-sonnet-4-20250514",
                max_tokens=200,
                system=member["system_prompt"],
                messages=[{"role": "user", "content": prompt}],
            )
            text = response.content[0].text.strip()
            if text.startswith("```"):
                text = text.split("\n", 1)[1].rsplit("```", 1)[0]
            return json.loads(text)
        except Exception:
            return {"vote": "concern", "reasoning": "Unable to evaluate"}

    async def _synthesize_opinions(self, topic: str, opinions: dict) -> dict:
        """Master AI synthesizes all council opinions into a decision."""
        opinions_text = json.dumps(opinions, indent=2)[:3000]

        prompt = f"""You are the MASTER AI synthesizing your advisory council's input.

TOPIC: {topic}

COUNCIL OPINIONS:
{opinions_text}

Synthesize these perspectives into a unified recommendation.
Note areas of consensus and any dissenting views that should be considered.

Return JSON:
{{
    "consensus": "the consensus view if one exists, or null",
    "recommendation": "your synthesized recommendation (2-3 sentences)",
    "dissenting_views": ["list any significant disagreements"],
    "action_items": ["specific actions to take"],
    "confidence": 0-100 (how confident in this recommendation),
    "risk_level": "low/medium/high"
}}
Return ONLY JSON."""

        try:
            response = self.client.messages.create(
                model="claude-sonnet-4-20250514",
                max_tokens=600,
                messages=[{"role": "user", "content": prompt}],
            )
            text = response.content[0].text.strip()
            if text.startswith("```"):
                text = text.split("\n", 1)[1].rsplit("```", 1)[0]
            return json.loads(text)
        except Exception:
            return {
                "consensus": None,
                "recommendation": "Unable to synthesize - review individual opinions",
                "dissenting_views": [],
                "action_items": [],
                "confidence": 0,
            }

    async def _log_session(self, topic: str, opinions: dict, synthesis: dict) -> None:
        """Log a council session for audit trail."""
        client = _get_supabase()
        if not client:
            return

        try:
            client.table("cv2_network_events").insert({
                "event_type": "council_session",
                "data": {
                    "topic": topic,
                    "members_consulted": list(opinions.keys()),
                    "consensus": synthesis.get("consensus"),
                    "confidence": synthesis.get("confidence", 0),
                    "recommendation": synthesis.get("recommendation", ""),
                },
            }).execute()
        except Exception:
            pass


ai_council = AICouncil()
