"""Campaign Manager - Lifecycle management for marketing campaigns.

Handles the full campaign lifecycle under Master AI oversight:

LIFECYCLE:
1. PROPOSED   - Marketing AI creates a campaign proposal
2. REVIEWING  - Master AI is evaluating the proposal
3. APPROVED   - Master AI approved (with possible modifications)
4. REJECTED   - Master AI rejected (with reason)
5. CONTENT_READY - All content generated and reviewed
6. ACTIVE     - Campaign is live
7. PAUSED     - Temporarily halted (budget concern, performance issue)
8. COMPLETED  - Campaign finished, final metrics recorded
9. TERMINATED - Master AI killed the campaign early

BUDGET ENFORCEMENT:
- Campaigns cannot exceed approved budget
- Spending is tracked in real-time
- Master AI can reduce budget mid-campaign
- Marketing AI must justify any budget increase requests

PERFORMANCE TRACKING:
- Impressions, clicks, signups tracked per campaign
- ROI calculated against spend
- Underperforming campaigns flagged for review
- Kill criteria checked automatically
"""

import json
from typing import Optional
from datetime import datetime, timezone

import anthropic
from supabase import create_client

from app.config import ANTHROPIC_API_KEY, SUPABASE_URL, SUPABASE_SERVICE_KEY


def _get_supabase():
    if not SUPABASE_URL or not SUPABASE_SERVICE_KEY:
        return None
    return create_client(SUPABASE_URL, SUPABASE_SERVICE_KEY)


VALID_TRANSITIONS = {
    "proposed": ["reviewing", "approved", "rejected"],
    "reviewing": ["approved", "rejected"],
    "approved": ["content_ready", "terminated"],
    "content_ready": ["active", "terminated"],
    "active": ["paused", "completed", "terminated"],
    "paused": ["active", "terminated"],
}


class CampaignManager:
    """Manages the lifecycle of marketing campaigns under Master AI control."""

    def __init__(self):
        self._anthropic = None

    @property
    def client(self):
        if self._anthropic is None:
            self._anthropic = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)
        return self._anthropic

    async def master_review_campaign(self, campaign_id: str) -> dict:
        """Master AI reviews a campaign proposal.

        Evaluates:
        - Is the target audience aligned with platform needs?
        - Is the budget reasonable for expected outcomes?
        - Are the claims honest and accurate?
        - Is the strategy sound for the channels chosen?

        Returns approval/rejection with reasoning.
        """
        if not ANTHROPIC_API_KEY:
            return {"status": "api_required"}

        campaign = await self._get_campaign(campaign_id)
        if not campaign:
            return {"status": "campaign_not_found"}

        campaign_text = json.dumps(campaign, indent=2)[:4000]

        prompt = f"""You are the MASTER AI reviewing a marketing campaign proposed by your Marketing AI agent.

CAMPAIGN PROPOSAL:
{campaign_text}

Evaluate this campaign critically:
1. Does the target audience match our actual platform gaps?
2. Is the budget justified and reasonable?
3. Are ALL claims about the platform honest and accurate?
4. Is the strategy appropriate for the chosen channels?
5. Are the expected outcomes realistic (not inflated)?
6. Does this align with our brand values (integrity, transparency)?

Be SKEPTICAL. Only approve campaigns that:
- Target real platform gaps
- Have reasonable ROI expectations
- Make no exaggerated claims
- Stay within approved channels
- Have clear success metrics and kill criteria

Return JSON:
{{
    "decision": "approve/reject/modify",
    "reasoning": "2-3 sentence explanation",
    "concerns": ["any concerns even if approving"],
    "modifications": ["required changes before approval"] or null,
    "budget_approved": original amount or reduced amount,
    "conditions": ["conditions for approval"],
    "review_score": 0-100 (quality of the proposal)
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
            review = json.loads(text)

            # Apply decision
            decision = review.get("decision", "reject")
            if decision == "approve":
                campaign["status"] = "approved"
                campaign["approved_at"] = datetime.now(timezone.utc).isoformat()
                campaign["approved_budget"] = review.get("budget_approved", campaign.get("budget", {}).get("total_usd", 0))
                campaign["approval_conditions"] = review.get("conditions", [])
            elif decision == "modify":
                campaign["status"] = "proposed"  # Back to proposed for modifications
                campaign["master_feedback"] = review.get("modifications", [])
            else:
                campaign["status"] = "rejected"
                campaign["rejected_at"] = datetime.now(timezone.utc).isoformat()
                campaign["rejection_reason"] = review.get("reasoning", "")

            campaign["master_review"] = review
            await self._update_campaign(campaign)

            # Log the review event
            await self._log_event("campaign_reviewed", {
                "campaign_id": campaign_id,
                "decision": decision,
                "review_score": review.get("review_score", 0),
            })

            return {
                "campaign_id": campaign_id,
                "decision": decision,
                "review": review,
                "new_status": campaign["status"],
            }
        except Exception as e:
            return {"status": "error", "detail": str(type(e).__name__)}

    async def approve_campaign(self, campaign_id: str, budget_override: Optional[float] = None) -> dict:
        """Manual approval by Master AI (bypass AI review)."""
        campaign = await self._get_campaign(campaign_id)
        if not campaign:
            return {"status": "campaign_not_found"}

        campaign["status"] = "approved"
        campaign["approved_at"] = datetime.now(timezone.utc).isoformat()
        campaign["approved_budget"] = budget_override or campaign.get("budget", {}).get("total_usd", 0)
        await self._update_campaign(campaign)

        return {"status": "approved", "campaign_id": campaign_id, "budget": campaign["approved_budget"]}

    async def reject_campaign(self, campaign_id: str, reason: str = "") -> dict:
        """Manual rejection by Master AI."""
        campaign = await self._get_campaign(campaign_id)
        if not campaign:
            return {"status": "campaign_not_found"}

        campaign["status"] = "rejected"
        campaign["rejected_at"] = datetime.now(timezone.utc).isoformat()
        campaign["rejection_reason"] = reason
        await self._update_campaign(campaign)

        return {"status": "rejected", "campaign_id": campaign_id, "reason": reason}

    async def activate_campaign(self, campaign_id: str) -> dict:
        """Set a campaign to active (start running it)."""
        campaign = await self._get_campaign(campaign_id)
        if not campaign:
            return {"status": "campaign_not_found"}

        current = campaign.get("status", "")
        if current not in ["approved", "content_ready"]:
            return {"status": "invalid_transition", "current_status": current}

        campaign["status"] = "active"
        campaign["activated_at"] = datetime.now(timezone.utc).isoformat()
        campaign["actual_metrics"] = {"reach": 0, "clicks": 0, "signups": 0, "spent_usd": 0}
        await self._update_campaign(campaign)

        await self._log_event("campaign_activated", {"campaign_id": campaign_id})
        return {"status": "activated", "campaign_id": campaign_id}

    async def pause_campaign(self, campaign_id: str, reason: str = "") -> dict:
        """Pause an active campaign."""
        campaign = await self._get_campaign(campaign_id)
        if not campaign:
            return {"status": "campaign_not_found"}

        if campaign.get("status") != "active":
            return {"status": "not_active"}

        campaign["status"] = "paused"
        campaign["paused_at"] = datetime.now(timezone.utc).isoformat()
        campaign["pause_reason"] = reason
        await self._update_campaign(campaign)

        return {"status": "paused", "campaign_id": campaign_id, "reason": reason}

    async def terminate_campaign(self, campaign_id: str, reason: str = "") -> dict:
        """Master AI terminates a campaign (permanent stop)."""
        campaign = await self._get_campaign(campaign_id)
        if not campaign:
            return {"status": "campaign_not_found"}

        campaign["status"] = "terminated"
        campaign["terminated_at"] = datetime.now(timezone.utc).isoformat()
        campaign["termination_reason"] = reason
        await self._update_campaign(campaign)

        await self._log_event("campaign_terminated", {
            "campaign_id": campaign_id,
            "reason": reason,
        })
        return {"status": "terminated", "campaign_id": campaign_id}

    async def record_metrics(self, campaign_id: str, metrics: dict) -> dict:
        """Record actual performance metrics for a campaign.

        metrics: {reach, clicks, signups, spent_usd}
        """
        campaign = await self._get_campaign(campaign_id)
        if not campaign:
            return {"status": "campaign_not_found"}

        actual = campaign.get("actual_metrics", {})
        for key in ["reach", "clicks", "signups", "spent_usd"]:
            if key in metrics:
                actual[key] = actual.get(key, 0) + metrics[key]

        campaign["actual_metrics"] = actual

        # Check budget overrun
        approved_budget = campaign.get("approved_budget", float("inf"))
        if actual.get("spent_usd", 0) >= approved_budget:
            campaign["status"] = "paused"
            campaign["pause_reason"] = "Budget exhausted"

        # Check kill criteria
        if await self._check_kill_criteria(campaign):
            campaign["status"] = "terminated"
            campaign["termination_reason"] = "Kill criteria met - underperforming"

        await self._update_campaign(campaign)

        return {
            "campaign_id": campaign_id,
            "metrics_recorded": metrics,
            "total_metrics": actual,
            "budget_remaining": max(0, approved_budget - actual.get("spent_usd", 0)),
        }

    async def get_all_campaigns(self, status_filter: Optional[str] = None) -> dict:
        """Get all campaigns, optionally filtered by status."""
        client = _get_supabase()
        if not client:
            return {"campaigns": []}

        try:
            query = client.table("cv2_marketing_campaigns").select("*").order("created_at", desc=True)
            if status_filter:
                query = query.eq("status", status_filter)
            result = query.limit(50).execute()

            campaigns = []
            for r in (result.data or []):
                data = r.get("data", {})
                data["db_status"] = r.get("status")
                campaigns.append(data)

            return {
                "campaigns": campaigns,
                "total": len(campaigns),
                "active_count": sum(1 for c in campaigns if c.get("status") == "active"),
                "pending_approval": sum(1 for c in campaigns if c.get("status") == "proposed"),
            }
        except Exception:
            return {"campaigns": []}

    async def get_marketing_dashboard(self) -> dict:
        """Get marketing department dashboard data."""
        all_campaigns = await self.get_all_campaigns()
        campaigns = all_campaigns.get("campaigns", [])

        total_budget = sum(c.get("approved_budget", 0) for c in campaigns if c.get("status") in ["active", "completed"])
        total_spent = sum(c.get("actual_metrics", {}).get("spent_usd", 0) for c in campaigns)
        total_signups = sum(c.get("actual_metrics", {}).get("signups", 0) for c in campaigns)

        return {
            "overview": {
                "total_campaigns": len(campaigns),
                "active": sum(1 for c in campaigns if c.get("status") == "active"),
                "pending_approval": sum(1 for c in campaigns if c.get("status") == "proposed"),
                "completed": sum(1 for c in campaigns if c.get("status") == "completed"),
                "rejected": sum(1 for c in campaigns if c.get("status") == "rejected"),
            },
            "budget": {
                "total_approved_usd": total_budget,
                "total_spent_usd": total_spent,
                "remaining_usd": total_budget - total_spent,
            },
            "performance": {
                "total_signups": total_signups,
                "avg_cpa": round(total_spent / max(total_signups, 1), 2),
            },
            "campaigns": [{
                "id": c.get("id"),
                "name": c.get("campaign_name"),
                "status": c.get("status"),
                "budget": c.get("approved_budget", c.get("budget", {}).get("total_usd", 0)),
                "signups": c.get("actual_metrics", {}).get("signups", 0),
            } for c in campaigns[:10]],
        }

    async def _check_kill_criteria(self, campaign: dict) -> bool:
        """Check if a campaign should be automatically killed."""
        actual = campaign.get("actual_metrics", {})
        expected = campaign.get("expected_outcomes", {})

        # Kill if spent > 50% of budget but < 10% of expected signups
        budget = campaign.get("approved_budget", 0)
        if budget > 0 and actual.get("spent_usd", 0) > budget * 0.5:
            expected_signups = expected.get("signups", 1)
            if actual.get("signups", 0) < expected_signups * 0.1:
                return True

        return False

    async def _get_campaign(self, campaign_id: str) -> Optional[dict]:
        """Get campaign by ID."""
        client = _get_supabase()
        if not client:
            return None
        try:
            result = (
                client.table("cv2_marketing_campaigns")
                .select("data")
                .eq("id", campaign_id)
                .execute()
            )
            if result.data:
                return result.data[0].get("data", {})
        except Exception:
            pass
        return None

    async def _update_campaign(self, campaign: dict) -> None:
        """Update campaign in DB."""
        client = _get_supabase()
        if not client:
            return
        try:
            client.table("cv2_marketing_campaigns").update({
                "data": campaign,
                "status": campaign.get("status", "proposed"),
            }).eq("id", campaign["id"]).execute()
        except Exception:
            pass

    async def _log_event(self, event_type: str, data: dict) -> None:
        """Log a marketing event."""
        client = _get_supabase()
        if not client:
            return
        try:
            client.table("cv2_network_events").insert({
                "event_type": f"marketing_{event_type}",
                "data": data,
            }).execute()
        except Exception:
            pass


campaign_manager = CampaignManager()
