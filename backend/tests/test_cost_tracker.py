"""Tests for cost tracker service."""

import pytest
from unittest.mock import patch, MagicMock

from app.services.cost_tracker import CostTracker, MODEL_PRICING, OPERATION_CATEGORIES


class TestModelPricing:
    """Test pricing constants."""

    def test_sonnet_pricing(self):
        pricing = MODEL_PRICING["claude-sonnet-4-20250514"]
        assert pricing["input"] == 3.00
        assert pricing["output"] == 15.00

    def test_haiku_pricing(self):
        pricing = MODEL_PRICING["claude-haiku-3-20240307"]
        assert pricing["input"] == 0.25
        assert pricing["output"] == 1.25

    def test_opus_pricing(self):
        pricing = MODEL_PRICING["claude-opus-4-20250514"]
        assert pricing["input"] == 15.00
        assert pricing["output"] == 75.00

    def test_all_models_have_both_rates(self):
        for model, pricing in MODEL_PRICING.items():
            assert "input" in pricing, f"Missing input pricing for {model}"
            assert "output" in pricing, f"Missing output pricing for {model}"
            assert pricing["input"] > 0
            assert pricing["output"] > 0


class TestOperationCategories:
    """Test operation categories are defined."""

    def test_categories_exist(self):
        assert "profile_generation" in OPERATION_CATEGORIES
        assert "negotiation_round" in OPERATION_CATEGORIES
        assert "hallucination_check" in OPERATION_CATEGORIES
        assert "governance_cycle" in OPERATION_CATEGORIES

    def test_all_categories_have_descriptions(self):
        for cat, desc in OPERATION_CATEGORIES.items():
            assert len(desc) > 0, f"Empty description for {cat}"


class TestRecordApiCall:
    """Test recording individual API calls."""

    def setup_method(self):
        self.tracker = CostTracker()

    def test_basic_recording(self):
        result = self.tracker.record_api_call(
            model="claude-sonnet-4-20250514",
            input_tokens=1000,
            output_tokens=500,
            operation="profile_generation",
        )
        assert "cost_usd" in result
        assert "running_total" in result
        assert result["cost_usd"] > 0

    def test_sonnet_cost_calculation(self):
        result = self.tracker.record_api_call(
            model="claude-sonnet-4-20250514",
            input_tokens=1_000_000,
            output_tokens=1_000_000,
            operation="test",
        )
        # 1M input at $3 + 1M output at $15 = $18
        assert abs(result["cost_usd"] - 18.0) < 0.01

    def test_haiku_cost_calculation(self):
        tracker = CostTracker()
        result = tracker.record_api_call(
            model="claude-haiku-3-20240307",
            input_tokens=1_000_000,
            output_tokens=1_000_000,
            operation="test",
        )
        # 1M input at $0.25 + 1M output at $1.25 = $1.50
        assert abs(result["cost_usd"] - 1.50) < 0.01

    def test_unknown_model_uses_default(self):
        result = self.tracker.record_api_call(
            model="unknown-model-v9",
            input_tokens=1000,
            output_tokens=500,
            operation="test",
        )
        # Default is Sonnet pricing ($3/$15)
        assert result["cost_usd"] > 0

    def test_running_total_accumulates(self):
        tracker = CostTracker()
        r1 = tracker.record_api_call("claude-sonnet-4-20250514", 1000, 500, "test")
        r2 = tracker.record_api_call("claude-sonnet-4-20250514", 1000, 500, "test")
        assert r2["running_total"] > r1["running_total"]
        assert abs(r2["running_total"] - r1["running_total"] - r1["cost_usd"]) < 0.0001

    def test_agent_id_stored(self):
        self.tracker.record_api_call(
            model="claude-sonnet-4-20250514",
            input_tokens=100,
            output_tokens=50,
            operation="test",
            agent_id="agent_123",
        )
        assert self.tracker._session_costs[-1]["agent_id"] == "agent_123"

    def test_metadata_stored(self):
        self.tracker.record_api_call(
            model="claude-sonnet-4-20250514",
            input_tokens=100,
            output_tokens=50,
            operation="test",
            metadata={"round": 1},
        )
        assert self.tracker._session_costs[-1]["metadata"]["round"] == 1

    def test_flush_triggered_at_10_records(self):
        tracker = CostTracker()
        with patch.object(tracker, "_flush_to_db") as mock_flush:
            for i in range(9):
                tracker.record_api_call("claude-sonnet-4-20250514", 100, 50, "test")
            assert mock_flush.call_count == 0

            tracker.record_api_call("claude-sonnet-4-20250514", 100, 50, "test")
            assert mock_flush.call_count == 1


class TestSessionSummary:
    """Test in-memory session summary."""

    def test_empty_session(self):
        tracker = CostTracker()
        summary = tracker._get_session_summary()
        assert summary["total_cost_usd"] == 0.0
        assert summary["api_calls"] == 0
        assert summary["period"] == "session"

    def test_session_with_records(self):
        tracker = CostTracker()
        tracker.record_api_call("claude-sonnet-4-20250514", 1000, 500, "test")
        tracker.record_api_call("claude-sonnet-4-20250514", 2000, 1000, "test")

        summary = tracker._get_session_summary()
        assert summary["api_calls"] == 2
        assert summary["total_cost_usd"] > 0
        assert summary["total_input_tokens"] == 3000
        assert summary["total_output_tokens"] == 1500


class TestBudgetStatus:
    """Test budget monitoring."""

    @pytest.mark.asyncio
    async def test_healthy_budget(self):
        tracker = CostTracker()
        with patch.object(tracker, "get_cost_summary") as mock_summary:
            mock_summary.return_value = {"total_cost_usd": 10.0, "monthly_projection_usd": 30.0}
            status = await tracker.get_budget_status(monthly_budget_usd=100.0)
            assert status["status"] == "healthy"
            assert status["usage_percent"] == 10.0

    @pytest.mark.asyncio
    async def test_warning_budget(self):
        tracker = CostTracker()
        with patch.object(tracker, "get_cost_summary") as mock_summary:
            mock_summary.return_value = {"total_cost_usd": 80.0, "monthly_projection_usd": None}
            status = await tracker.get_budget_status(monthly_budget_usd=100.0)
            assert status["status"] == "warning"
            assert len(status["alerts"]) > 0

    @pytest.mark.asyncio
    async def test_critical_budget(self):
        tracker = CostTracker()
        with patch.object(tracker, "get_cost_summary") as mock_summary:
            mock_summary.return_value = {"total_cost_usd": 95.0, "monthly_projection_usd": None}
            status = await tracker.get_budget_status(monthly_budget_usd=100.0)
            assert status["status"] == "critical"
            assert any(a["level"] == "critical" for a in status["alerts"])


class TestFlush:
    """Test DB flushing."""

    def test_flush_without_db(self):
        tracker = CostTracker()
        tracker.record_api_call("claude-sonnet-4-20250514", 100, 50, "test")
        with patch("app.services.cost_tracker.get_db", return_value=None):
            tracker.flush()
            assert len(tracker._session_costs) == 1  # Still in memory

    def test_flush_with_db(self):
        tracker = CostTracker()
        tracker.record_api_call("claude-sonnet-4-20250514", 100, 50, "test")

        mock_client = MagicMock()
        mock_table = MagicMock()
        mock_table.insert.return_value = mock_table
        mock_table.execute.return_value = MagicMock(data=[])
        mock_client.table.return_value = mock_table

        with patch("app.services.cost_tracker.get_db", return_value=mock_client):
            tracker.flush()
            assert len(tracker._session_costs) == 0
            mock_client.table.assert_called_with("cv2_cost_tracking")
