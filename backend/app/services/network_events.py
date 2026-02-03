"""Network Event System - Orchestrates the AI networking space.

Events:
- agent_activated: New agent joins → discover compatible partners → negotiate
- match_found: Negotiation succeeded → notify both sides → await human feedback
- human_feedback: Human accepted/rejected → update memory → learn → adjust
- network_cycle: Periodic full-network scan → discover new pairs → negotiate

This is the "brain" of the networking space - it ties together:
discovery → negotiation → memory → learning → governance
"""

import json
from typing import Optional

from app.database import get_db

from app.services.network_discovery import network_discovery
from app.services.negotiation_protocol import negotiation_protocol
from app.services.agent_memory import agent_memory
from app.services.network_learning import network_learning


def _get_supabase():
    return get_db()


class NetworkEvents:
    """Orchestrates the AI networking space events."""

    async def on_agent_activated(self, agent_id: str, agent_type: str) -> dict:
        """Handle new agent activation.

        1. Discover compatible partners
        2. Run negotiations with top candidates
        3. Store results
        4. Notify if matches found

        Returns summary of what happened.
        """
        client = _get_supabase()
        if not client:
            return {"status": "error", "detail": "Database not configured"}

        # Get the new agent
        agent_data = (
            client.table("cv2_agents")
            .select("*")
            .eq("id", agent_id)
            .execute()
        )
        if not agent_data.data:
            return {"status": "error", "detail": "Agent not found"}

        agent = agent_data.data[0]

        # Log event
        await self._log_event("agent_activated", {
            "agent_id": agent_id,
            "agent_type": agent_type,
            "industry": agent.get("industry", "general"),
        })

        # Discover compatible partners
        if agent_type == "talent":
            compatible = await network_discovery.find_matches_for_talent(agent)
        else:
            compatible = await network_discovery.find_matches_for_hm(agent)

        if not compatible:
            return {
                "status": "no_matches",
                "agent_id": agent_id,
                "message": "No compatible partners found yet. Will check again next cycle.",
            }

        # Negotiate with top 5 most compatible
        results = []
        for partner_data in compatible[:5]:
            partner = partner_data["agent"]

            if agent_type == "talent":
                talent_agent = agent
                hm_agent = partner
            else:
                talent_agent = partner
                hm_agent = agent

            # Run multi-round negotiation
            negotiation_result = await negotiation_protocol.negotiate(
                talent_agent=talent_agent,
                hm_agent=hm_agent,
                discovery_context=partner_data,
            )

            # Record in memory for both agents
            partner_id = partner.get("id", "")
            await agent_memory.record_negotiation(
                agent_id=agent_id,
                partner_agent_id=partner_id,
                outcome=negotiation_result["status"],
                score=negotiation_result.get("final_score", 0),
                round_reached=negotiation_result.get("rejection_round") or 3,
                insights={"rounds": len(negotiation_result.get("rounds", []))},
            )
            await agent_memory.record_negotiation(
                agent_id=partner_id,
                partner_agent_id=agent_id,
                outcome=negotiation_result["status"],
                score=negotiation_result.get("final_score", 0),
                round_reached=negotiation_result.get("rejection_round") or 3,
            )

            # If matched, store the match
            if negotiation_result["status"] == "matched":
                talent_id = talent_agent.get("user_id", talent_agent.get("id", ""))
                job_id = hm_agent.get("job_id", hm_agent.get("id", ""))
                match_id = f"{talent_id}_{job_id}"

                match_record = {
                    "id": match_id,
                    "candidate_id": talent_id,
                    "job_id": job_id,
                    "score": negotiation_result["final_score"],
                    "match_level": negotiation_result.get("match_level", "moderate_match"),
                    "status": "mutual_agreement",
                    "candidate_synopsis": negotiation_result.get("candidate_synopsis", {}),
                    "hiring_manager_synopsis": negotiation_result.get("hm_synopsis", {}),
                    "negotiation_notes": negotiation_result.get("negotiation_log", ""),
                    "negotiation_rounds": len(negotiation_result.get("rounds", [])),
                }
                client.table("cv2_a2a_matches").upsert(match_record).execute()

                # Create notification
                await self._notify_match(talent_id, job_id, negotiation_result)

                results.append({
                    "partner_id": partner_id,
                    "status": "matched",
                    "score": negotiation_result["final_score"],
                })
            else:
                results.append({
                    "partner_id": partner_id,
                    "status": negotiation_result["status"],
                    "score": negotiation_result.get("final_score", 0),
                    "rejection_round": negotiation_result.get("rejection_round"),
                })

            # Learn from every negotiation (success or failure)
            try:
                await network_learning.learn_from_negotiation(
                    talent_agent=talent_agent,
                    hm_agent=hm_agent,
                    negotiation_result=negotiation_result,
                )
            except Exception:
                pass  # Learning is non-critical

        matches_found = sum(1 for r in results if r["status"] == "matched")
        return {
            "status": "completed",
            "agent_id": agent_id,
            "partners_evaluated": len(results),
            "matches_found": matches_found,
            "results": results,
        }

    async def on_human_feedback(
        self, agent_id: str, match_id: str, accepted: bool, feedback: Optional[str] = None
    ) -> dict:
        """Handle human accepting/rejecting a match.

        1. Record feedback in agent memory
        2. Update reputation
        3. If rejected, learn from it
        4. Share learning with network

        Returns learning result.
        """
        # Record in memory
        await agent_memory.record_human_feedback(
            agent_id=agent_id,
            match_id=match_id,
            accepted=accepted,
            feedback=feedback,
        )

        # Log event
        await self._log_event("human_feedback", {
            "agent_id": agent_id,
            "match_id": match_id,
            "accepted": accepted,
        })

        # If rejected, trigger network learning
        learning_result = None
        if not accepted and feedback:
            from app.services.network_learning import network_learning
            learning_result = await network_learning.learn_from_rejection(
                agent_id=agent_id,
                match_id=match_id,
                feedback=feedback,
            )

        return {
            "status": "recorded",
            "accepted": accepted,
            "reputation_updated": True,
            "learning": learning_result,
        }

    async def run_network_cycle(self) -> dict:
        """Run a full network matching cycle.

        1. Discover all compatible pairs (excluding existing matches)
        2. Prioritize by compatibility score and agent reputation
        3. Run negotiations for top pairs
        4. Store results
        5. Return summary

        This should be called periodically (e.g., every hour).
        """
        # Discover all pairs
        pairs = await network_discovery.discover_all_pairs()

        if not pairs:
            return {"status": "no_pairs", "message": "No new compatible pairs found"}

        # Sort by compatibility + reputation
        for pair in pairs:
            talent_rep = await agent_memory.get_reputation(
                pair["talent_agent"].get("id", "")
            )
            hm_rep = await agent_memory.get_reputation(
                pair["hm_agent"].get("id", "")
            )
            pair["priority"] = pair["compatibility_score"] + (talent_rep + hm_rep) / 4

        pairs.sort(key=lambda x: x["priority"], reverse=True)

        # Negotiate top 10 pairs per cycle (token budget management)
        max_negotiations = 10
        results = []

        for pair in pairs[:max_negotiations]:
            negotiation_result = await negotiation_protocol.negotiate(
                talent_agent=pair["talent_agent"],
                hm_agent=pair["hm_agent"],
                discovery_context=pair,
            )

            talent_id = pair["talent_agent"].get("id", "")
            hm_id = pair["hm_agent"].get("id", "")

            # Record in memory
            await agent_memory.record_negotiation(
                agent_id=talent_id,
                partner_agent_id=hm_id,
                outcome=negotiation_result["status"],
                score=negotiation_result.get("final_score", 0),
                round_reached=negotiation_result.get("rejection_round") or 3,
            )
            await agent_memory.record_negotiation(
                agent_id=hm_id,
                partner_agent_id=talent_id,
                outcome=negotiation_result["status"],
                score=negotiation_result.get("final_score", 0),
                round_reached=negotiation_result.get("rejection_round") or 3,
            )

            # Store match if found
            if negotiation_result["status"] == "matched":
                client = _get_supabase()
                talent_user_id = pair["talent_agent"].get("user_id", talent_id)
                job_id = pair["hm_agent"].get("job_id", hm_id)
                match_id = f"{talent_user_id}_{job_id}"

                match_record = {
                    "id": match_id,
                    "candidate_id": talent_user_id,
                    "job_id": job_id,
                    "score": negotiation_result["final_score"],
                    "match_level": negotiation_result.get("match_level", "moderate_match"),
                    "status": "mutual_agreement",
                    "candidate_synopsis": negotiation_result.get("candidate_synopsis", {}),
                    "hiring_manager_synopsis": negotiation_result.get("hm_synopsis", {}),
                    "negotiation_notes": negotiation_result.get("negotiation_log", ""),
                    "negotiation_rounds": len(negotiation_result.get("rounds", [])),
                }
                if client:
                    client.table("cv2_a2a_matches").upsert(match_record).execute()

                await self._notify_match(talent_user_id, job_id, negotiation_result)

            results.append({
                "talent_id": talent_id,
                "hm_id": hm_id,
                "status": negotiation_result["status"],
                "score": negotiation_result.get("final_score", 0),
            })

        # Log cycle
        await self._log_event("network_cycle", {
            "pairs_discovered": len(pairs),
            "negotiations_run": len(results),
            "matches_found": sum(1 for r in results if r["status"] == "matched"),
        })

        matches_found = sum(1 for r in results if r["status"] == "matched")
        return {
            "status": "cycle_complete",
            "pairs_discovered": len(pairs),
            "negotiations_run": len(results),
            "matches_found": matches_found,
            "results": results,
        }

    async def get_network_activity(self, limit: int = 20) -> list[dict]:
        """Get recent network activity log for dashboard."""
        client = _get_supabase()
        if not client:
            return []

        result = (
            client.table("cv2_network_events")
            .select("*")
            .order("created_at", desc=True)
            .limit(limit)
            .execute()
        )
        return result.data or []

    async def _log_event(self, event_type: str, data: dict) -> None:
        """Log a network event."""
        client = _get_supabase()
        if not client:
            return

        try:
            client.table("cv2_network_events").insert({
                "event_type": event_type,
                "data": data,
            }).execute()
        except Exception:
            pass  # Non-critical

    async def _notify_match(self, talent_user_id: str, job_id: str, result: dict) -> None:
        """Create notifications for both sides of a match."""
        client = _get_supabase()
        if not client:
            return

        try:
            # Notify talent
            client.table("cv2_notifications").insert({
                "user_id": talent_user_id,
                "type": "match_found",
                "data": {
                    "job_id": job_id,
                    "score": result.get("final_score", 0),
                    "synopsis": result.get("candidate_synopsis", {}),
                },
            }).execute()

            # Notify HM (need to find HM user_id from job)
            job = (
                client.table("cv2_jobs")
                .select("user_id")
                .eq("id", job_id)
                .execute()
            )
            if job.data:
                client.table("cv2_notifications").insert({
                    "user_id": job.data[0]["user_id"],
                    "type": "candidate_found",
                    "data": {
                        "candidate_id": talent_user_id,
                        "score": result.get("final_score", 0),
                        "synopsis": result.get("hm_synopsis", {}),
                    },
                }).execute()
        except Exception:
            pass  # Notifications are non-critical


network_events = NetworkEvents()
