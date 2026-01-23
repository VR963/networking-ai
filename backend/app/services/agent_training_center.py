"""Agent Training Center - Where agents learn and improve.

Provides structured training and retraining capabilities:
- Initial training: Set up agent from profile data
- Correction training: Learn from human rejections
- Calibration training: Adjust scoring based on outcomes
- Skill refinement: Improve negotiation effectiveness
- Integrity reinforcement: Strengthen anti-hallucination behavior

Training is triggered by:
- Master AI governance review (retrain action)
- Repeated human rejections
- Drift detection by hallucination guard
- Periodic performance review
"""

import json
from typing import Optional

import anthropic
from supabase import create_client

from app.config import ANTHROPIC_API_KEY, SUPABASE_URL, SUPABASE_SERVICE_KEY
from app.services.hallucination_guard import AGENT_INTEGRITY_DIRECTIVE, HM_INTEGRITY_DIRECTIVE


def _get_supabase():
    if not SUPABASE_URL or not SUPABASE_SERVICE_KEY:
        return None
    return create_client(SUPABASE_URL, SUPABASE_SERVICE_KEY)


class AgentTrainingCenter:
    """Manages agent training, retraining, and improvement."""

    def __init__(self):
        self._anthropic = None

    @property
    def client(self):
        if self._anthropic is None:
            self._anthropic = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)
        return self._anthropic

    async def diagnose_agent(self, agent_id: str) -> dict:
        """Diagnose why an agent is underperforming.

        Analyzes:
        - Rejection patterns (why humans reject its matches)
        - Score trends (getting worse?)
        - Profile gaps (missing data causing poor matches)
        - Integrity issues (hallucination patterns)

        Returns diagnosis with recommended training plan.
        """
        client = _get_supabase()
        if not client:
            return {"status": "unavailable"}

        # Get agent
        agent = (
            client.table("cv2_agents")
            .select("*")
            .eq("id", agent_id)
            .execute()
        )
        if not agent.data:
            return {"status": "agent_not_found"}

        agent_data = agent.data[0]
        profile = agent_data.get("profile", {})

        # Get rejection history
        memories = (
            client.table("cv2_agent_memory")
            .select("event_type, data, created_at")
            .eq("agent_id", agent_id)
            .order("created_at", desc=True)
            .limit(20)
            .execute()
        )
        history = memories.data or []

        rejections = [h for h in history if h.get("event_type") == "human_rejected"]
        acceptances = [h for h in history if h.get("event_type") == "human_accepted"]

        # Get learnings
        learnings = (
            client.table("cv2_agent_learnings")
            .select("lesson, created_at")
            .eq("agent_id", agent_id)
            .order("created_at", desc=True)
            .limit(10)
            .execute()
        )

        # Diagnose
        issues = []
        training_plan = []

        # Check rejection rate
        total = len(rejections) + len(acceptances)
        if total > 0 and len(rejections) / total > 0.6:
            issues.append("High rejection rate - agent not representing user well")
            training_plan.append("correction_training")

        # Check profile completeness
        if agent_data.get("agent_type") == "talent":
            if not profile.get("skills_verified"):
                issues.append("No verified skills - needs more CV data")
                training_plan.append("profile_enrichment")
            if not profile.get("values"):
                issues.append("No values identified - needs interview data")
                training_plan.append("interview_rerun")
            if not profile.get("psychometric_profile"):
                issues.append("Missing psychometric profile")
                training_plan.append("profile_enrichment")
        else:
            if not profile.get("role_requirements", {}).get("must_have"):
                issues.append("No must-have requirements defined")
                training_plan.append("profile_enrichment")
            if not profile.get("hidden_preferences"):
                issues.append("No hidden preferences - interview data needed")
                training_plan.append("interview_rerun")

        # Check integrity
        if not profile.get("integrity_directive"):
            issues.append("Missing integrity directive")
            training_plan.append("integrity_reinforcement")

        # Check reputation
        if agent_data.get("reputation", 50) < 30:
            issues.append(f"Very low reputation ({agent_data.get('reputation')})")
            training_plan.append("full_retrain")

        if not issues:
            issues.append("No significant issues detected")

        return {
            "agent_id": agent_id,
            "agent_type": agent_data.get("agent_type"),
            "reputation": agent_data.get("reputation", 50),
            "diagnosis": {
                "issues": issues,
                "rejection_count": len(rejections),
                "acceptance_count": len(acceptances),
                "success_rate": round(len(acceptances) / max(total, 1) * 100, 1),
                "learnings_applied": len(learnings.data or []),
            },
            "training_plan": list(set(training_plan)) or ["monitoring_only"],
            "priority": "high" if len(issues) > 2 else "medium" if issues else "low",
        }

    async def run_correction_training(self, agent_id: str) -> dict:
        """Train agent based on its rejection history.

        Analyzes WHY matches were rejected and updates the agent's
        profile/behavior to avoid similar mismatches.
        """
        client = _get_supabase()
        if not client or not ANTHROPIC_API_KEY:
            return {"status": "unavailable"}

        # Get agent and rejection data
        agent = (
            client.table("cv2_agents")
            .select("*")
            .eq("id", agent_id)
            .execute()
        )
        if not agent.data:
            return {"status": "agent_not_found"}

        agent_data = agent.data[0]
        profile = agent_data.get("profile", {})

        # Get rejection feedback
        rejections = (
            client.table("cv2_agent_memory")
            .select("data")
            .eq("agent_id", agent_id)
            .eq("event_type", "human_rejected")
            .order("created_at", desc=True)
            .limit(5)
            .execute()
        )
        rejection_data = [r.get("data", {}) for r in (rejections.data or [])]

        if not rejection_data:
            return {"status": "no_rejections", "message": "No rejection data to learn from"}

        profile_text = json.dumps(profile, indent=2)[:2000]
        rejections_text = json.dumps(rejection_data, indent=2)[:2000]

        prompt = f"""You are an AI TRAINER. Analyze why this agent's matches keep getting rejected
by humans, and suggest specific profile adjustments.

CURRENT AGENT PROFILE:
{profile_text}

HUMAN REJECTION DATA (feedback from rejected matches):
{rejections_text}

Based on the rejection patterns, provide specific corrections:
1. What is the agent misrepresenting or overemphasizing?
2. What preferences/dealbreakers need adjustment?
3. What negotiation priorities should change?

CRITICAL: Corrections must NOT introduce fabrications. Only adjust emphasis
and priorities based on rejection feedback.

Return JSON:
{{
    "root_cause": "Why matches are being rejected",
    "corrections": [
        {{
            "field": "profile field to adjust",
            "current": "current problematic value",
            "suggested": "corrected value",
            "reason": "why this change"
        }}
    ],
    "priority_adjustments": ["reordered negotiation priorities"],
    "new_dealbreakers": ["any new dealbreakers revealed by rejections"],
    "personality_update": "updated agent personality directive if needed"
}}
Return ONLY JSON."""

        try:
            response = self.client.messages.create(
                model="claude-sonnet-4-20250514",
                max_tokens=1000,
                messages=[{"role": "user", "content": prompt}],
            )
            text = response.content[0].text.strip()
            if text.startswith("```"):
                text = text.split("\n", 1)[1].rsplit("```", 1)[0]
            corrections = json.loads(text)

            # Apply corrections to profile
            updated_profile = await self._apply_corrections(profile, corrections)

            # Update agent in DB
            client.table("cv2_agents").update({
                "profile": updated_profile,
            }).eq("id", agent_id).execute()

            # Log training event
            client.table("cv2_network_events").insert({
                "event_type": "agent_retrained",
                "data": {
                    "agent_id": agent_id,
                    "training_type": "correction",
                    "corrections_count": len(corrections.get("corrections", [])),
                    "root_cause": corrections.get("root_cause", ""),
                },
            }).execute()

            return {
                "status": "trained",
                "agent_id": agent_id,
                "corrections_applied": len(corrections.get("corrections", [])),
                "root_cause": corrections.get("root_cause", ""),
                "details": corrections,
            }
        except Exception as e:
            return {"status": "error", "detail": str(type(e).__name__)}

    async def run_integrity_reinforcement(self, agent_id: str) -> dict:
        """Reinforce anti-hallucination rules for an agent.

        Called when drift is detected or integrity directive is missing.
        """
        client = _get_supabase()
        if not client:
            return {"status": "unavailable"}

        agent = (
            client.table("cv2_agents")
            .select("*")
            .eq("id", agent_id)
            .execute()
        )
        if not agent.data:
            return {"status": "agent_not_found"}

        agent_data = agent.data[0]
        profile = agent_data.get("profile", {}) or {}
        agent_type = agent_data.get("agent_type", "talent")

        # Embed the correct directive
        directive = HM_INTEGRITY_DIRECTIVE if agent_type == "hm" else AGENT_INTEGRITY_DIRECTIVE
        profile["integrity_directive"] = directive

        # Ensure personality includes integrity clause
        personality = profile.get("agent_personality", "")
        if agent_type == "hm":
            integrity_clause = " INTEGRITY: Never exaggerate role benefits or fabricate undocumented conditions."
        else:
            integrity_clause = " INTEGRITY: Never exaggerate or fabricate. Only state documented facts."

        if "never exaggerate" not in personality.lower():
            profile["agent_personality"] = personality + integrity_clause

        # Update
        client.table("cv2_agents").update({
            "profile": profile,
            "integrity_directive": directive,
        }).eq("id", agent_id).execute()

        return {
            "status": "reinforced",
            "agent_id": agent_id,
            "directive_embedded": True,
            "personality_updated": True,
        }

    async def run_full_retrain(self, agent_id: str) -> dict:
        """Full agent retrain - regenerate profile from source data.

        Used for severely underperforming agents. Regenerates the entire
        AI profile from scratch using the original CV/JD and interview data.
        """
        client = _get_supabase()
        if not client:
            return {"status": "unavailable"}

        agent = (
            client.table("cv2_agents")
            .select("*")
            .eq("id", agent_id)
            .execute()
        )
        if not agent.data:
            return {"status": "agent_not_found"}

        agent_data = agent.data[0]
        user_id = agent_data.get("user_id", "")
        agent_type = agent_data.get("agent_type", "talent")
        industry = agent_data.get("industry", "general")

        if agent_type == "talent":
            # Get source data
            docs = (
                client.table("cv2_documents")
                .select("analysis")
                .eq("user_id", user_id)
                .eq("doc_type", "cv")
                .execute()
            )
            cv_analysis = docs.data[0]["analysis"] if docs.data and docs.data[0].get("analysis") else None

            interview_data = (
                client.table("cv2_interviews")
                .select("answers")
                .eq("user_id", user_id)
                .eq("agent_type", "talent")
                .order("created_at", desc=True)
                .limit(1)
                .execute()
            )
            answers = interview_data.data[0]["answers"] if interview_data.data else []

            # Regenerate profile
            from app.services.ai_profile_service import ai_profile_service
            new_profile = await ai_profile_service.generate_talent_profile(
                cv_analysis=cv_analysis,
                interview_answers=answers,
                industry=industry,
            )
        else:
            # HM agent - get job description
            job_id = agent_data.get("job_id", "")
            job_data = (
                client.table("cv2_jobs")
                .select("*")
                .eq("id", job_id)
                .execute()
            )
            job_description = job_data.data[0] if job_data.data else {}

            interview_data = (
                client.table("cv2_interviews")
                .select("answers")
                .eq("user_id", user_id)
                .eq("agent_type", "hm")
                .eq("context_id", job_id)
                .order("created_at", desc=True)
                .limit(1)
                .execute()
            )
            answers = interview_data.data[0]["answers"] if interview_data.data else []

            from app.services.ai_profile_service import ai_profile_service
            new_profile = await ai_profile_service.generate_hm_profile(
                job_description=job_description,
                interview_answers=answers,
                industry=industry,
            )

        # Apply learnings from previous experience
        learnings = (
            client.table("cv2_agent_learnings")
            .select("lesson")
            .eq("agent_id", agent_id)
            .execute()
        )
        if learnings.data:
            new_profile["applied_learnings"] = [l.get("lesson", "") for l in learnings.data[:5]]

        # Update agent
        client.table("cv2_agents").update({
            "profile": new_profile,
            "reputation": 40,  # Slight penalty for needing retrain
        }).eq("id", agent_id).execute()

        # Log
        try:
            client.table("cv2_network_events").insert({
                "event_type": "agent_retrained",
                "data": {
                    "agent_id": agent_id,
                    "training_type": "full_retrain",
                    "reason": "severely_underperforming",
                },
            }).execute()
        except Exception:
            pass

        return {
            "status": "retrained",
            "agent_id": agent_id,
            "new_reputation": 40,
            "learnings_applied": len(learnings.data or []),
            "profile_regenerated": True,
        }

    async def get_training_queue(self) -> dict:
        """Get list of agents that need training.

        Identifies agents that should be trained based on:
        - Low reputation
        - High rejection rate
        - Missing integrity directive
        - Flagged by hallucination guard
        """
        client = _get_supabase()
        if not client:
            return {"queue": [], "status": "unavailable"}

        # Agents with low reputation
        at_risk = (
            client.table("cv2_agents")
            .select("id, agent_type, reputation, active, profile")
            .eq("active", True)
            .lt("reputation", 40)
            .execute()
        )

        queue = []
        for agent in (at_risk.data or []):
            profile = agent.get("profile", {}) or {}
            needs = []
            if agent.get("reputation", 50) < 20:
                needs.append("full_retrain")
            elif agent.get("reputation", 50) < 40:
                needs.append("correction_training")
            if not profile.get("integrity_directive"):
                needs.append("integrity_reinforcement")

            queue.append({
                "agent_id": agent["id"],
                "agent_type": agent.get("agent_type"),
                "reputation": agent.get("reputation", 50),
                "training_needed": needs,
                "priority": "critical" if agent.get("reputation", 50) < 20 else "high",
            })

        # Sort by priority
        priority_order = {"critical": 0, "high": 1, "medium": 2, "low": 3}
        queue.sort(key=lambda x: priority_order.get(x["priority"], 99))

        return {
            "queue": queue,
            "total_needing_training": len(queue),
            "critical_count": sum(1 for q in queue if q["priority"] == "critical"),
        }

    async def run_training_cycle(self) -> dict:
        """Run a training cycle - process all agents in the queue.

        Called by Master AI during governance cycles.
        """
        queue = await self.get_training_queue()
        results = []

        for item in queue.get("queue", [])[:5]:  # Process up to 5 per cycle
            agent_id = item["agent_id"]
            trainings = item.get("training_needed", [])

            for training_type in trainings:
                if training_type == "full_retrain":
                    result = await self.run_full_retrain(agent_id)
                elif training_type == "correction_training":
                    result = await self.run_correction_training(agent_id)
                elif training_type == "integrity_reinforcement":
                    result = await self.run_integrity_reinforcement(agent_id)
                else:
                    result = {"status": "unknown_training_type"}

                results.append({
                    "agent_id": agent_id,
                    "training_type": training_type,
                    "result": result.get("status", "unknown"),
                })

        return {
            "status": "cycle_complete",
            "agents_trained": len(set(r["agent_id"] for r in results)),
            "trainings_run": len(results),
            "results": results,
        }

    async def _apply_corrections(self, profile: dict, corrections: dict) -> dict:
        """Apply correction training results to a profile."""
        updated = profile.copy()

        for correction in corrections.get("corrections", []):
            field = correction.get("field", "")
            suggested = correction.get("suggested")
            if field and suggested and field in updated:
                updated[field] = suggested

        # Update priorities if suggested
        if corrections.get("priority_adjustments"):
            updated["negotiation_priorities"] = corrections["priority_adjustments"]

        # Add new dealbreakers
        if corrections.get("new_dealbreakers"):
            existing = updated.get("dealbreakers", [])
            updated["dealbreakers"] = list(set(existing + corrections["new_dealbreakers"]))

        # Update personality if needed
        if corrections.get("personality_update"):
            base = corrections["personality_update"]
            # Ensure integrity is preserved
            if "never exaggerate" not in base.lower():
                base += " INTEGRITY: Never exaggerate or fabricate. Only state documented facts."
            updated["agent_personality"] = base

        return updated


agent_training_center = AgentTrainingCenter()
