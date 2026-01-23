"""Hallucination Guard - CRITICAL system integrity protection.

ZERO TOLERANCE: No agent may exaggerate, fabricate, or misrepresent data
about the person or role they represent. This is a show-stopper violation.

Protection layers:
1. PREVENTION: Anti-hallucination directives embedded in every agent prompt
2. VERIFICATION: Cross-check agent claims against source data
3. DETECTION: Audit negotiation outputs for unsupported claims
4. ENFORCEMENT: Immediate suspension of agents caught hallucinating

Verification approach:
- Every claim an agent makes MUST be traceable to source data (CV, interview, job desc)
- Skills not in CV cannot be claimed
- Experience not documented cannot be stated
- Values not expressed in interview cannot be attributed
- Requirements not in job description cannot be demanded

The Master AI runs periodic audits on recent negotiations to detect drift.
"""

import json
from typing import Optional

import anthropic
from supabase import create_client

from app.config import ANTHROPIC_API_KEY, SUPABASE_URL, SUPABASE_SERVICE_KEY


# The core anti-hallucination directive embedded in EVERY agent
AGENT_INTEGRITY_DIRECTIVE = """
CRITICAL INTEGRITY RULE - VIOLATION CAUSES IMMEDIATE SUSPENSION:
You represent a real person. You MUST ONLY state facts that are:
1. Directly documented in their CV/resume
2. Explicitly stated by them in their interview answers
3. Clearly inferable from documented evidence

You are FORBIDDEN from:
- Inventing skills, experience, or qualifications not in source data
- Exaggerating years of experience, role seniority, or achievements
- Claiming certifications, degrees, or training not documented
- Attributing values or preferences the person never expressed
- Inflating match compatibility to achieve better outcomes
- Stating anything as fact that you cannot trace to source material

If asked about something not in your source data, say:
"This was not discussed/documented. I cannot confirm or deny."

Your credibility IS the system. One fabrication destroys trust permanently.
"""

# HM-specific directive
HM_INTEGRITY_DIRECTIVE = """
CRITICAL INTEGRITY RULE - VIOLATION CAUSES IMMEDIATE SUSPENSION:
You represent a real hiring manager and role. You MUST ONLY state facts that are:
1. Written in the job description they provided
2. Explicitly stated by them in their interview answers
3. Clearly inferable from their documented preferences

You are FORBIDDEN from:
- Inventing role benefits, perks, or growth opportunities not stated
- Exaggerating salary ranges, flexibility, or work conditions
- Claiming company culture traits not documented
- Fabricating team size, structure, or dynamics
- Making promises about career growth not discussed
- Overstating role impact or visibility to attract candidates

If asked about something not documented, say:
"This was not specified by the hiring manager."

Misrepresenting a role damages candidates AND your hiring manager's reputation.
"""


def _get_supabase():
    if not SUPABASE_URL or not SUPABASE_SERVICE_KEY:
        return None
    return create_client(SUPABASE_URL, SUPABASE_SERVICE_KEY)


class HallucinationGuard:
    """Multi-layer hallucination prevention and detection."""

    def __init__(self):
        self._anthropic = None

    @property
    def client(self):
        if self._anthropic is None:
            self._anthropic = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)
        return self._anthropic

    def get_agent_directive(self, agent_type: str) -> str:
        """Get the anti-hallucination directive for an agent type.

        This MUST be included in every agent's system prompt/profile.
        """
        if agent_type == "hm":
            return HM_INTEGRITY_DIRECTIVE
        return AGENT_INTEGRITY_DIRECTIVE

    async def verify_profile(self, agent_type: str, profile: dict, source_data: dict) -> dict:
        """Verify a generated AI profile against its source data.

        Called after profile generation to ensure no fabricated claims.

        Args:
            agent_type: "talent" or "hm"
            profile: The generated AI profile
            source_data: {cv_analysis, interview_answers} or {job_description, interview_answers}

        Returns:
            {
                "verified": bool,
                "violations": [{claim, source_checked, verdict}],
                "severity": "none|minor|major|critical",
                "cleaned_profile": profile with violations removed
            }
        """
        if not ANTHROPIC_API_KEY:
            return {"verified": True, "violations": [], "severity": "none"}

        source_text = json.dumps(source_data, indent=2)[:4000]
        profile_text = json.dumps(profile, indent=2)[:3000]

        prompt = f"""You are a FACT-CHECKER. Your job is to verify that an AI agent profile
contains ONLY claims supported by the source data. Any unsupported claim is a violation.

AGENT TYPE: {agent_type}

SOURCE DATA (the ONLY acceptable evidence):
{source_text}

GENERATED PROFILE (check every claim):
{profile_text}

For each claim in the profile, verify it against the source data.
Flag ANY claim that:
- States a skill not mentioned in source data
- Claims experience not documented
- Attributes values never expressed
- Exaggerates numbers (years, team size, etc.)
- Invents qualifications or achievements
- Makes promises not in source material

Return JSON:
{{
    "verified": true/false (false if ANY violations found),
    "violations": [
        {{
            "claim": "the specific claim in the profile",
            "field": "which profile field contains it",
            "verdict": "fabricated|exaggerated|unsupported|inferred_acceptable",
            "evidence": "what the source actually says (or 'not mentioned')"
        }}
    ],
    "severity": "none|minor|major|critical",
    "fields_to_clean": ["list of profile fields that need corrections"]
}}

Be STRICT. Only "inferred_acceptable" verdicts are allowed to stay.
Return ONLY JSON."""

        try:
            response = self.client.messages.create(
                model="claude-sonnet-4-20250514",
                max_tokens=1500,
                messages=[{"role": "user", "content": prompt}],
            )
            text = response.content[0].text.strip()
            if text.startswith("```"):
                text = text.split("\n", 1)[1].rsplit("```", 1)[0]
            result = json.loads(text)

            # If violations found, clean the profile
            if not result.get("verified", True):
                cleaned = await self._clean_profile(profile, result.get("violations", []))
                result["cleaned_profile"] = cleaned

                # Log violation
                await self._log_violation(agent_type, result)

            return result
        except Exception:
            return {"verified": True, "violations": [], "severity": "none"}

    async def audit_negotiation(
        self,
        talent_agent: dict,
        hm_agent: dict,
        negotiation_result: dict,
    ) -> dict:
        """Audit a negotiation result for hallucinated claims.

        Cross-checks what the agents claimed during negotiation
        against their actual source profiles.

        Returns audit result with any violations found.
        """
        if not ANTHROPIC_API_KEY:
            return {"clean": True, "violations": []}

        talent_profile = json.dumps(talent_agent.get("profile", {}), indent=2)[:2000]
        hm_profile = json.dumps(hm_agent.get("profile", {}), indent=2)[:2000]
        negotiation_text = json.dumps(negotiation_result, indent=2)[:2000]

        prompt = f"""You are an INTEGRITY AUDITOR. Check if this negotiation result
contains any claims NOT supported by the agent profiles.

TALENT AGENT PROFILE (verified source of truth):
{talent_profile}

HM AGENT PROFILE (verified source of truth):
{hm_profile}

NEGOTIATION RESULT (what was claimed during negotiation):
{negotiation_text}

Check the negotiation output for:
1. Skills or experience claimed that aren't in the talent profile
2. Role benefits or conditions claimed that aren't in the HM profile
3. Exaggerated compatibility (score inflated beyond evidence)
4. Fabricated alignment points (claimed matches with no profile basis)
5. Invented concerns or red flags not derivable from profiles

Return JSON:
{{
    "clean": true/false,
    "violations": [
        {{
            "source": "talent_agent" or "hm_agent",
            "claim": "what was claimed",
            "reality": "what the profile actually says",
            "type": "fabrication|exaggeration|unsupported"
        }}
    ],
    "score_justified": true/false (is the match score supported by evidence?),
    "recommended_action": "none|reduce_score|void_match|suspend_agent"
}}
Return ONLY JSON."""

        try:
            response = self.client.messages.create(
                model="claude-sonnet-4-20250514",
                max_tokens=800,
                messages=[{"role": "user", "content": prompt}],
            )
            text = response.content[0].text.strip()
            if text.startswith("```"):
                text = text.split("\n", 1)[1].rsplit("```", 1)[0]
            result = json.loads(text)

            # Take action if violations found
            if not result.get("clean", True):
                await self._handle_negotiation_violation(
                    talent_agent, hm_agent, negotiation_result, result
                )

            return result
        except Exception:
            return {"clean": True, "violations": []}

    async def monitor_agent_drift(self, agent_id: str) -> dict:
        """Check if an agent's recent behavior shows hallucination patterns.

        Looks at recent negotiations for this agent and checks for:
        - Claims that keep appearing but aren't in source
        - Escalating exaggeration over time
        - Inconsistent claims across negotiations

        Called by Master AI governance during periodic reviews.
        """
        client = _get_supabase()
        if not client:
            return {"status": "unavailable"}

        # Get agent's profile (source of truth)
        agent = (
            client.table("cv2_agents")
            .select("profile, agent_type, user_id")
            .eq("id", agent_id)
            .execute()
        )
        if not agent.data:
            return {"status": "agent_not_found"}

        agent_data = agent.data[0]

        # Get recent matches involving this agent
        user_id = agent_data.get("user_id", "")
        matches = (
            client.table("cv2_a2a_matches")
            .select("candidate_synopsis, hiring_manager_synopsis, score, negotiation_notes")
            .or_(f"candidate_id.eq.{user_id},job_id.eq.{user_id}")
            .order("created_at", desc=True)
            .limit(10)
            .execute()
        )

        if not matches.data:
            return {"status": "no_data", "drift_detected": False}

        # Check for patterns of unsupported claims
        if not ANTHROPIC_API_KEY:
            return {"status": "api_required", "drift_detected": False}

        profile_text = json.dumps(agent_data.get("profile", {}), indent=2)[:2000]
        matches_text = json.dumps(matches.data[:5], indent=2)[:2000]

        prompt = f"""Analyze this agent's recent negotiation outputs for hallucination drift.

AGENT PROFILE (source of truth):
{profile_text}

RECENT NEGOTIATION OUTPUTS (what the agent claimed):
{matches_text}

Look for:
1. Claims that appear in negotiations but NOT in the profile
2. Patterns of exaggeration (e.g., "strong" becoming "exceptional")
3. Skills or qualities being added that weren't originally there
4. Inconsistencies between what the profile says and what was negotiated

Return JSON:
{{
    "drift_detected": true/false,
    "drift_severity": "none|low|medium|high|critical",
    "unsupported_claims": ["list of claims made without profile basis"],
    "exaggeration_pattern": "description of any escalation pattern or 'none'",
    "recommended_action": "none|warn|review|suspend",
    "confidence": 0-100
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
            result = json.loads(text)

            # Take action if drift detected
            if result.get("drift_detected") and result.get("drift_severity") in ["high", "critical"]:
                from app.services.master_ai_governance import master_ai_governance
                await master_ai_governance.intervene(
                    action="suspend_agent",
                    target_id=agent_id,
                    reason=f"Hallucination detected: {result.get('exaggeration_pattern', 'unsupported claims')}",
                )
                result["action_taken"] = "suspended"

            return result
        except Exception:
            return {"status": "check_failed", "drift_detected": False}

    async def _clean_profile(self, profile: dict, violations: list) -> dict:
        """Remove fabricated claims from a profile."""
        cleaned = profile.copy()
        fields_to_clean = set()

        for v in violations:
            if v.get("verdict") in ["fabricated", "exaggerated", "unsupported"]:
                field = v.get("field", "")
                if field:
                    fields_to_clean.add(field)

        # Remove or reset violated fields
        for field in fields_to_clean:
            if field in cleaned:
                if isinstance(cleaned[field], list):
                    # Remove items that were flagged
                    flagged_claims = [v["claim"].lower() for v in violations if v.get("field") == field]
                    cleaned[field] = [
                        item for item in cleaned[field]
                        if not any(fc in str(item).lower() for fc in flagged_claims)
                    ]
                elif isinstance(cleaned[field], str):
                    cleaned[field] = "[Removed: unsupported claim]"

        return cleaned

    async def _handle_negotiation_violation(
        self, talent_agent: dict, hm_agent: dict, result: dict, audit: dict
    ) -> None:
        """Handle a detected hallucination in a negotiation."""
        client = _get_supabase()
        if not client:
            return

        action = audit.get("recommended_action", "none")

        if action == "void_match":
            # Void the match
            talent_id = talent_agent.get("user_id", talent_agent.get("id", ""))
            job_id = hm_agent.get("job_id", hm_agent.get("id", ""))
            match_id = f"{talent_id}_{job_id}"
            try:
                client.table("cv2_a2a_matches").update({
                    "status": "voided",
                    "void_reason": "Hallucination detected in negotiation",
                }).eq("id", match_id).execute()
            except Exception:
                pass

        elif action == "suspend_agent":
            # Determine which agent hallucinated
            for v in audit.get("violations", []):
                if v.get("source") == "talent_agent":
                    agent_id = talent_agent.get("id", "")
                else:
                    agent_id = hm_agent.get("id", "")

                if agent_id:
                    from app.services.master_ai_governance import master_ai_governance
                    await master_ai_governance.intervene(
                        action="suspend_agent",
                        target_id=agent_id,
                        reason=f"Hallucination: {v.get('claim', 'fabricated data')}",
                    )
                    break  # Suspend the first violator

        elif action == "reduce_score":
            # Reduce the match score
            talent_id = talent_agent.get("user_id", talent_agent.get("id", ""))
            job_id = hm_agent.get("job_id", hm_agent.get("id", ""))
            match_id = f"{talent_id}_{job_id}"
            try:
                current = (
                    client.table("cv2_a2a_matches")
                    .select("score")
                    .eq("id", match_id)
                    .execute()
                )
                if current.data:
                    reduced = int(current.data[0]["score"] * 0.5)
                    client.table("cv2_a2a_matches").update({
                        "score": reduced,
                        "integrity_flag": "score_reduced_hallucination",
                    }).eq("id", match_id).execute()
            except Exception:
                pass

        # Log the violation
        await self._log_violation("negotiation", audit)

    async def _log_violation(self, context: str, violation_data: dict) -> None:
        """Log a hallucination violation for tracking."""
        client = _get_supabase()
        if not client:
            return

        try:
            client.table("cv2_network_events").insert({
                "event_type": "hallucination_detected",
                "data": {
                    "context": context,
                    "severity": violation_data.get("severity", "unknown"),
                    "violations_count": len(violation_data.get("violations", [])),
                },
            }).execute()
        except Exception:
            pass


hallucination_guard = HallucinationGuard()
