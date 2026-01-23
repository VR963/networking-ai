"""Network Discovery Service - Lightweight pre-filter before full negotiation.

Instead of running expensive Claude negotiations for every possible pair,
this service uses feature-based compatibility scoring to identify promising
pairs that are worth a full multi-round negotiation.

Scoring dimensions:
- Industry alignment (same/adjacent/different)
- Seniority match (role level compatibility)
- Values overlap (keyword intersection)
- Dealbreaker check (instant rejection before negotiation)
- Location/remote compatibility
"""

import json
from typing import Optional

from supabase import create_client
from app.config import SUPABASE_URL, SUPABASE_SERVICE_KEY


# Industry adjacency map - industries that commonly cross-hire
INDUSTRY_ADJACENCY = {
    "tech": ["engineering", "creative", "finance"],
    "engineering": ["tech", "healthcare"],
    "finance": ["tech", "marketing"],
    "healthcare": ["engineering", "tech"],
    "creative": ["tech", "marketing"],
    "marketing": ["creative", "tech", "finance"],
}

DISCOVERY_THRESHOLD = 30  # Minimum pre-filter score to enter negotiation


def _get_supabase():
    if not SUPABASE_URL or not SUPABASE_SERVICE_KEY:
        return None
    return create_client(SUPABASE_URL, SUPABASE_SERVICE_KEY)


class NetworkDiscovery:
    """Discovers compatible agent pairs for negotiation."""

    async def find_matches_for_talent(self, talent_agent: dict) -> list[dict]:
        """Find HM agents worth negotiating with for a given talent agent.

        Returns list of {hm_agent, compatibility_score, reasons} sorted by score.
        """
        client = _get_supabase()
        if not client:
            return []

        # Get all active HM agents
        hm_agents = (
            client.table("cv2_agents")
            .select("*")
            .eq("agent_type", "hm")
            .eq("active", True)
            .execute()
        )

        compatible = []
        for hm in (hm_agents.data or []):
            score, reasons = self._compute_compatibility(talent_agent, hm)
            if score >= DISCOVERY_THRESHOLD:
                compatible.append({
                    "agent": hm,
                    "compatibility_score": score,
                    "reasons": reasons,
                })

        # Sort by score descending
        compatible.sort(key=lambda x: x["compatibility_score"], reverse=True)
        return compatible[:20]  # Cap at top 20

    async def find_matches_for_hm(self, hm_agent: dict) -> list[dict]:
        """Find talent agents worth negotiating with for a given HM agent.

        Returns list of {talent_agent, compatibility_score, reasons} sorted by score.
        """
        client = _get_supabase()
        if not client:
            return []

        # Get all active talent agents
        talent_agents = (
            client.table("cv2_agents")
            .select("*")
            .eq("agent_type", "talent")
            .eq("active", True)
            .execute()
        )

        compatible = []
        for talent in (talent_agents.data or []):
            score, reasons = self._compute_compatibility(talent, hm_agent)
            if score >= DISCOVERY_THRESHOLD:
                compatible.append({
                    "agent": talent,
                    "compatibility_score": score,
                    "reasons": reasons,
                })

        compatible.sort(key=lambda x: x["compatibility_score"], reverse=True)
        return compatible[:20]

    async def discover_all_pairs(self) -> list[dict]:
        """Run discovery across all active agents, return compatible pairs.

        Used by the network scheduler for batch matching cycles.
        """
        client = _get_supabase()
        if not client:
            return []

        talent_agents = (
            client.table("cv2_agents")
            .select("*")
            .eq("agent_type", "talent")
            .eq("active", True)
            .execute()
        )

        hm_agents = (
            client.table("cv2_agents")
            .select("*")
            .eq("agent_type", "hm")
            .eq("active", True)
            .execute()
        )

        # Check existing matches to avoid re-negotiating
        existing = (
            client.table("cv2_a2a_matches")
            .select("candidate_id, job_id")
            .execute()
        )
        existing_pairs = set()
        for m in (existing.data or []):
            existing_pairs.add(f"{m['candidate_id']}_{m['job_id']}")

        pairs = []
        for talent in (talent_agents.data or []):
            for hm in (hm_agents.data or []):
                pair_key = f"{talent.get('user_id', talent.get('id'))}_{hm.get('job_id', hm.get('id'))}"
                if pair_key in existing_pairs:
                    continue  # Already matched

                score, reasons = self._compute_compatibility(talent, hm)
                if score >= DISCOVERY_THRESHOLD:
                    pairs.append({
                        "talent_agent": talent,
                        "hm_agent": hm,
                        "compatibility_score": score,
                        "reasons": reasons,
                    })

        pairs.sort(key=lambda x: x["compatibility_score"], reverse=True)
        return pairs

    def _compute_compatibility(self, talent: dict, hm: dict) -> tuple[int, list[str]]:
        """Compute lightweight compatibility score between talent and HM agents.

        Returns (score 0-100, list of reasons).
        """
        talent_profile = talent.get("profile", {})
        hm_profile = hm.get("profile", {})
        reasons = []
        score = 0

        # 1. Industry alignment (0-25 points)
        talent_industry = talent.get("industry", "general")
        hm_industry = hm.get("industry", "general")
        if talent_industry == hm_industry:
            score += 25
            reasons.append(f"Same industry: {talent_industry}")
        elif hm_industry in INDUSTRY_ADJACENCY.get(talent_industry, []):
            score += 15
            reasons.append(f"Adjacent industries: {talent_industry}/{hm_industry}")
        else:
            score += 5  # Different industry, still possible

        # 2. Skills overlap (0-25 points)
        talent_skills = set(s.lower() for s in (talent_profile.get("skills_verified", []) or []))
        hm_must_have = set()
        role_reqs = hm_profile.get("role_requirements", {})
        if isinstance(role_reqs, dict):
            for req in (role_reqs.get("must_have", []) or []):
                hm_must_have.update(req.lower().split())
        hm_nice = set()
        if isinstance(role_reqs, dict):
            for req in (role_reqs.get("nice_to_have", []) or []):
                hm_nice.update(req.lower().split())

        if talent_skills and hm_must_have:
            overlap = talent_skills & hm_must_have
            if overlap:
                skill_score = min(25, int(len(overlap) / max(len(hm_must_have), 1) * 25))
                score += skill_score
                reasons.append(f"Skills match: {len(overlap)} keywords")
        elif talent_skills:
            score += 10  # Has skills, just can't compare

        # 3. Values alignment (0-20 points)
        talent_values = set(v.lower() for v in (talent_profile.get("values", []) or []))
        hm_culture = hm_profile.get("team_culture", {})
        hm_hidden = set(p.lower() for p in (hm_profile.get("hidden_preferences", []) or []))

        if talent_values:
            # Check values against culture and hidden preferences
            all_hm_signals = hm_hidden
            if isinstance(hm_culture, dict) and hm_culture.get("vibe"):
                all_hm_signals.update(hm_culture["vibe"].lower().split())

            if all_hm_signals:
                value_overlap = talent_values & all_hm_signals
                if value_overlap:
                    score += min(20, len(value_overlap) * 7)
                    reasons.append(f"Values alignment: {', '.join(list(value_overlap)[:3])}")
            else:
                score += 8  # Can't compare, neutral

        # 4. Dealbreaker check (-50 points if hit)
        talent_dealbreakers = [d.lower() for d in (talent_profile.get("dealbreakers", []) or [])]
        hm_dealbreakers = [d.lower() for d in (hm_profile.get("dealbreakers", []) or [])]

        # Check talent dealbreakers against HM profile
        hm_about = (hm_profile.get("about", "") or "").lower()
        for db in talent_dealbreakers:
            if any(word in hm_about for word in db.split() if len(word) > 3):
                score -= 25
                reasons.append(f"Possible dealbreaker: {db}")
                break

        # 5. Environment compatibility (0-15 points)
        talent_env = talent_profile.get("environment_preferences", {})
        hm_team = hm_profile.get("team_culture", {})
        if isinstance(talent_env, dict) and isinstance(hm_team, dict):
            env_matches = 0
            if talent_env.get("pace") and hm_team.get("pace"):
                if talent_env["pace"] == hm_team["pace"]:
                    env_matches += 1
            if talent_env.get("structure") and hm_team.get("autonomy"):
                # Map: structured->guided, flexible->moderate, autonomous->high
                structure_map = {"structured": "guided", "flexible": "moderate", "autonomous": "high"}
                if structure_map.get(talent_env["structure"]) == hm_team["autonomy"]:
                    env_matches += 1
            if env_matches:
                score += env_matches * 7
                reasons.append(f"Environment fit: {env_matches} dimensions match")

        # 6. Communication style (0-15 points)
        talent_comm = talent_profile.get("communication_style", {})
        hm_comm = hm_profile.get("communication_style", {})
        if isinstance(talent_comm, dict) and isinstance(hm_comm, dict):
            # Direct communicators with direct HMs = good match
            if talent_comm.get("primary") and hm_comm.get("what_impresses"):
                if talent_comm["primary"] in (hm_comm.get("what_impresses", "") or "").lower():
                    score += 10
                    reasons.append("Communication style alignment")

        return max(0, min(100, score)), reasons

    async def get_network_stats(self) -> dict:
        """Get current network statistics for the dashboard."""
        client = _get_supabase()
        if not client:
            return {"talent_agents": 0, "hm_agents": 0, "potential_pairs": 0}

        talent = (
            client.table("cv2_agents")
            .select("id", count="exact")
            .eq("agent_type", "talent")
            .eq("active", True)
            .execute()
        )

        hm = (
            client.table("cv2_agents")
            .select("id", count="exact")
            .eq("agent_type", "hm")
            .eq("active", True)
            .execute()
        )

        matches = (
            client.table("cv2_a2a_matches")
            .select("id", count="exact")
            .execute()
        )

        return {
            "talent_agents": talent.count or 0,
            "hm_agents": hm.count or 0,
            "total_matches": matches.count or 0,
            "potential_pairs": (talent.count or 0) * (hm.count or 0),
        }


network_discovery = NetworkDiscovery()
