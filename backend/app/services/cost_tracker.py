"""Cost Tracker Service - Real-time platform cost monitoring.

Tracks every API call, token usage, and computes running costs:
- Per-agent token consumption
- Per-operation cost breakdown (profile generation, negotiation, governance)
- Running totals by time period (hourly, daily, monthly)
- Cost projections and budget alerts
- Model-specific pricing (Sonnet, Haiku, etc.)

Pricing (as of 2025):
- Claude Sonnet 4: $3/M input, $15/M output
- Claude Haiku: $0.25/M input, $1.25/M output

This is critical for platform sustainability and business model decisions.
"""

import time
from datetime import datetime, timezone
from typing import Optional

from supabase import create_client
from app.config import SUPABASE_URL, SUPABASE_SERVICE_KEY


# Model pricing per million tokens (USD)
MODEL_PRICING = {
    "claude-sonnet-4-20250514": {"input": 3.00, "output": 15.00},
    "claude-haiku-3-20240307": {"input": 0.25, "output": 1.25},
    "claude-opus-4-20250514": {"input": 15.00, "output": 75.00},
}

# Operation categories for cost allocation
OPERATION_CATEGORIES = {
    "profile_generation": "Profile generation (talent/HM)",
    "negotiation_round": "Negotiation round execution",
    "hallucination_check": "Hallucination verification/audit",
    "governance_cycle": "Master AI governance cycle",
    "market_intelligence": "Market data analysis",
    "agent_training": "Agent training/retraining",
    "council_session": "AI council deliberation",
    "interview_analysis": "Interview quality analysis",
    "drift_monitoring": "Hallucination drift monitoring",
}


def _get_supabase():
    if not SUPABASE_URL or not SUPABASE_SERVICE_KEY:
        return None
    return create_client(SUPABASE_URL, SUPABASE_SERVICE_KEY)


class CostTracker:
    """Tracks platform costs in real-time."""

    def __init__(self):
        self._session_costs = []  # In-memory buffer before DB flush
        self._total_input_tokens = 0
        self._total_output_tokens = 0
        self._total_cost_usd = 0.0

    def record_api_call(
        self,
        model: str,
        input_tokens: int,
        output_tokens: int,
        operation: str,
        agent_id: Optional[str] = None,
        metadata: Optional[dict] = None,
    ) -> dict:
        """Record a single API call's cost.

        Args:
            model: Model ID used
            input_tokens: Input tokens consumed
            output_tokens: Output tokens consumed
            operation: Operation category (from OPERATION_CATEGORIES)
            agent_id: Which agent made this call (if applicable)
            metadata: Additional context

        Returns:
            {"cost_usd": float, "running_total": float}
        """
        pricing = MODEL_PRICING.get(model, {"input": 3.00, "output": 15.00})
        input_cost = (input_tokens / 1_000_000) * pricing["input"]
        output_cost = (output_tokens / 1_000_000) * pricing["output"]
        total_cost = input_cost + output_cost

        record = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "model": model,
            "input_tokens": input_tokens,
            "output_tokens": output_tokens,
            "input_cost_usd": round(input_cost, 6),
            "output_cost_usd": round(output_cost, 6),
            "total_cost_usd": round(total_cost, 6),
            "operation": operation,
            "agent_id": agent_id,
            "metadata": metadata or {},
        }

        self._session_costs.append(record)
        self._total_input_tokens += input_tokens
        self._total_output_tokens += output_tokens
        self._total_cost_usd += total_cost

        # Flush to DB periodically (every 10 records)
        if len(self._session_costs) >= 10:
            self._flush_to_db()

        return {
            "cost_usd": round(total_cost, 6),
            "running_total": round(self._total_cost_usd, 4),
        }

    async def get_cost_summary(self, period: str = "today") -> dict:
        """Get cost summary for a time period.

        Args:
            period: "today", "week", "month", "all"

        Returns comprehensive cost breakdown.
        """
        client = _get_supabase()
        if not client:
            return self._get_session_summary()

        # Get cost records from DB
        query = client.table("cv2_cost_tracking").select("*")

        if period == "today":
            today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
            query = query.gte("timestamp", today)
        elif period == "week":
            # Last 7 days
            from datetime import timedelta
            week_ago = (datetime.now(timezone.utc) - timedelta(days=7)).isoformat()
            query = query.gte("timestamp", week_ago)
        elif period == "month":
            from datetime import timedelta
            month_ago = (datetime.now(timezone.utc) - timedelta(days=30)).isoformat()
            query = query.gte("timestamp", month_ago)

        try:
            result = query.order("timestamp", desc=True).limit(1000).execute()
            records = result.data or []
        except Exception:
            records = []

        # Combine DB records with in-memory session
        all_records = records + self._session_costs

        if not all_records:
            return {
                "period": period,
                "total_cost_usd": 0.0,
                "total_input_tokens": 0,
                "total_output_tokens": 0,
                "by_operation": {},
                "by_model": {},
                "by_agent": {},
                "api_calls": 0,
            }

        # Aggregate by operation
        by_operation = {}
        for r in all_records:
            op = r.get("operation", "unknown")
            if op not in by_operation:
                by_operation[op] = {"cost_usd": 0.0, "calls": 0, "tokens": 0}
            by_operation[op]["cost_usd"] += r.get("total_cost_usd", 0)
            by_operation[op]["calls"] += 1
            by_operation[op]["tokens"] += r.get("input_tokens", 0) + r.get("output_tokens", 0)

        # Aggregate by model
        by_model = {}
        for r in all_records:
            model = r.get("model", "unknown")
            if model not in by_model:
                by_model[model] = {"cost_usd": 0.0, "calls": 0}
            by_model[model]["cost_usd"] += r.get("total_cost_usd", 0)
            by_model[model]["calls"] += 1

        # Aggregate by agent
        by_agent = {}
        for r in all_records:
            agent = r.get("agent_id", "system")
            if agent not in by_agent:
                by_agent[agent] = {"cost_usd": 0.0, "calls": 0}
            by_agent[agent]["cost_usd"] += r.get("total_cost_usd", 0)
            by_agent[agent]["calls"] += 1

        total_cost = sum(r.get("total_cost_usd", 0) for r in all_records)
        total_input = sum(r.get("input_tokens", 0) for r in all_records)
        total_output = sum(r.get("output_tokens", 0) for r in all_records)

        # Cost projection (daily rate * 30)
        if period == "today" and total_cost > 0:
            daily_projection = total_cost
            monthly_projection = daily_projection * 30
        else:
            monthly_projection = None

        return {
            "period": period,
            "total_cost_usd": round(total_cost, 4),
            "total_input_tokens": total_input,
            "total_output_tokens": total_output,
            "total_tokens": total_input + total_output,
            "api_calls": len(all_records),
            "by_operation": {
                k: {**v, "cost_usd": round(v["cost_usd"], 4)}
                for k, v in sorted(by_operation.items(), key=lambda x: -x[1]["cost_usd"])
            },
            "by_model": {
                k: {**v, "cost_usd": round(v["cost_usd"], 4)}
                for k, v in by_model.items()
            },
            "by_agent": {
                k: {**v, "cost_usd": round(v["cost_usd"], 4)}
                for k, v in sorted(by_agent.items(), key=lambda x: -x[1]["cost_usd"])[:10]
            },
            "monthly_projection_usd": round(monthly_projection, 2) if monthly_projection else None,
            "avg_cost_per_call": round(total_cost / max(len(all_records), 1), 6),
        }

    async def get_agent_costs(self, agent_id: str) -> dict:
        """Get cost breakdown for a specific agent."""
        client = _get_supabase()
        if not client:
            agent_records = [r for r in self._session_costs if r.get("agent_id") == agent_id]
            return {
                "agent_id": agent_id,
                "total_cost_usd": sum(r.get("total_cost_usd", 0) for r in agent_records),
                "api_calls": len(agent_records),
            }

        try:
            result = (
                client.table("cv2_cost_tracking")
                .select("*")
                .eq("agent_id", agent_id)
                .order("timestamp", desc=True)
                .limit(100)
                .execute()
            )
            records = result.data or []
        except Exception:
            records = []

        total_cost = sum(r.get("total_cost_usd", 0) for r in records)
        by_operation = {}
        for r in records:
            op = r.get("operation", "unknown")
            if op not in by_operation:
                by_operation[op] = 0.0
            by_operation[op] += r.get("total_cost_usd", 0)

        return {
            "agent_id": agent_id,
            "total_cost_usd": round(total_cost, 4),
            "api_calls": len(records),
            "by_operation": {k: round(v, 4) for k, v in by_operation.items()},
            "avg_per_call": round(total_cost / max(len(records), 1), 6),
        }

    async def get_budget_status(self, monthly_budget_usd: float = 100.0) -> dict:
        """Check budget status and alerts."""
        summary = await self.get_cost_summary("month")
        spent = summary.get("total_cost_usd", 0)
        remaining = monthly_budget_usd - spent
        usage_percent = (spent / monthly_budget_usd) * 100 if monthly_budget_usd > 0 else 0

        alerts = []
        if usage_percent > 90:
            alerts.append({"level": "critical", "message": f"Budget {usage_percent:.0f}% used"})
        elif usage_percent > 75:
            alerts.append({"level": "warning", "message": f"Budget {usage_percent:.0f}% used"})
        elif usage_percent > 50:
            alerts.append({"level": "info", "message": f"Budget {usage_percent:.0f}% used"})

        return {
            "monthly_budget_usd": monthly_budget_usd,
            "spent_usd": round(spent, 4),
            "remaining_usd": round(remaining, 4),
            "usage_percent": round(usage_percent, 1),
            "projection_usd": summary.get("monthly_projection_usd"),
            "alerts": alerts,
            "status": "critical" if usage_percent > 90 else "warning" if usage_percent > 75 else "healthy",
        }

    def _get_session_summary(self) -> dict:
        """Fallback: summary from in-memory session data only."""
        return {
            "period": "session",
            "total_cost_usd": round(self._total_cost_usd, 4),
            "total_input_tokens": self._total_input_tokens,
            "total_output_tokens": self._total_output_tokens,
            "api_calls": len(self._session_costs),
            "by_operation": {},
            "by_model": {},
            "by_agent": {},
        }

    def _flush_to_db(self) -> None:
        """Flush buffered cost records to database."""
        client = _get_supabase()
        if not client or not self._session_costs:
            return

        try:
            client.table("cv2_cost_tracking").insert(self._session_costs).execute()
            self._session_costs = []
        except Exception:
            pass  # Keep in memory if DB fails

    def flush(self) -> None:
        """Force flush all pending records to DB."""
        self._flush_to_db()


cost_tracker = CostTracker()
