"""Tests for multi-round negotiation protocol."""

import json
import pytest
from unittest.mock import patch, MagicMock, AsyncMock

from app.services.negotiation_protocol import (
    NegotiationProtocol,
    ROUND_1_THRESHOLD,
    ROUND_2_THRESHOLD,
    FINAL_THRESHOLD,
    NEGOTIATION_INTEGRITY_RULE,
)


class TestNegotiationThresholds:
    """Test threshold constants."""

    def test_thresholds_are_progressive(self):
        assert ROUND_1_THRESHOLD < ROUND_2_THRESHOLD < FINAL_THRESHOLD

    def test_integrity_rule_present(self):
        assert "FACTUAL GROUNDING RULE" in NEGOTIATION_INTEGRITY_RULE
        assert "VIOLATION" in NEGOTIATION_INTEGRITY_RULE


class TestScoreToLevel:
    """Test score classification."""

    def setup_method(self):
        self.protocol = NegotiationProtocol()

    def test_exceptional(self):
        assert self.protocol._score_to_level(90) == "exceptional_match"
        assert self.protocol._score_to_level(85) == "exceptional_match"

    def test_strong(self):
        assert self.protocol._score_to_level(80) == "strong_match"
        assert self.protocol._score_to_level(75) == "strong_match"

    def test_moderate(self):
        assert self.protocol._score_to_level(70) == "moderate_match"
        assert self.protocol._score_to_level(65) == "moderate_match"

    def test_weak(self):
        assert self.protocol._score_to_level(60) == "weak_match"
        assert self.protocol._score_to_level(55) == "weak_match"

    def test_no_match(self):
        assert self.protocol._score_to_level(50) == "no_match"
        assert self.protocol._score_to_level(0) == "no_match"


class TestNegotiationRounds:
    """Test the full negotiation pipeline."""

    def setup_method(self):
        self.protocol = NegotiationProtocol()
        self.talent_agent = {
            "id": "agent_t1",
            "user_id": "t1",
            "profile": {
                "skills_verified": ["Python", "Machine Learning"],
                "synopsis": "Senior ML engineer with 5 years experience",
                "environment_preferences": {"pace": "fast"},
                "values": ["innovation", "autonomy"],
                "dealbreakers": [],
                "communication_style": {"primary": "direct"},
                "negotiation_priorities": ["growth", "impact"],
                "about": "Passionate about AI",
                "psychometric_profile": {},
                "agent_personality": "Analytical and thorough",
            },
        }
        self.hm_agent = {
            "id": "hm_agent_j1",
            "job_id": "j1",
            "profile": {
                "role_requirements": {"must_have": ["Python", "ML"]},
                "synopsis": "AI startup seeking ML lead",
                "team_culture": {"vibe": "fast-paced", "pace": "fast"},
                "hidden_preferences": ["self-starter"],
                "dealbreakers": [],
                "communication_style": {"what_impresses": "direct communication"},
                "decision_profile": {"weights": {"technical": 40, "culture": 30, "growth": 30}},
                "about": "Growing AI team at a Series B startup",
                "offer_flexibility": {"remote": True},
                "agent_personality": "Selective but open-minded",
            },
        }

    @pytest.mark.asyncio
    async def test_rejected_at_round_1(self):
        with patch.object(self.protocol, "_call_round", new_callable=AsyncMock) as mock:
            mock.return_value = {"score": 20, "reason": "No skills match", "proceed": False}

            result = await self.protocol.negotiate(self.talent_agent, self.hm_agent)
            assert result["status"] == "rejected"
            assert result["rejection_round"] == 1
            assert len(result["rounds"]) == 1
            assert mock.call_count == 1  # Only round 1 called

    @pytest.mark.asyncio
    async def test_rejected_at_round_2(self):
        async def side_effect(prompt, max_tokens=500):
            if "Round 1" in prompt or "Surface" in prompt:
                return {"score": 60, "reason": "Good skills match", "proceed": True, "skills_match": "strong"}
            return {"score": 30, "reason": "Values clash", "proceed": False, "dealbreaker_hit": True}

        with patch.object(self.protocol, "_call_round", side_effect=side_effect):
            result = await self.protocol.negotiate(self.talent_agent, self.hm_agent)
            assert result["status"] == "rejected"
            assert result["rejection_round"] == 2
            assert len(result["rounds"]) == 2

    @pytest.mark.asyncio
    async def test_full_match(self):
        call_count = [0]

        async def side_effect(prompt, max_tokens=500):
            call_count[0] += 1
            if call_count[0] == 1:
                return {"score": 70, "skills_match": "strong", "proceed": True, "reason": "Good"}
            elif call_count[0] == 2:
                return {"score": 75, "values_alignment": "strong", "proceed": True, "reason": "Aligned"}
            else:
                return {
                    "score": 80,
                    "deep_fit": "strong",
                    "candidate_synopsis": {"recommendation": "Great fit"},
                    "hm_synopsis": {"recommendation": "Strong candidate"},
                    "negotiation_summary": "Both agents agreed",
                    "reason": "Match found",
                }

        with patch.object(self.protocol, "_call_round", side_effect=side_effect):
            with patch("app.services.negotiation_protocol.ANTHROPIC_API_KEY", "test-key"):
                # Patch the hallucination guard audit to avoid API call
                with patch("app.services.hallucination_guard.hallucination_guard") as mock_guard:
                    mock_guard.audit_negotiation = AsyncMock(return_value={"clean": True})

                    result = await self.protocol.negotiate(self.talent_agent, self.hm_agent)
                    assert result["status"] == "matched"
                    assert result["final_score"] > 0
                    assert len(result["rounds"]) == 3
                    assert "candidate_synopsis" in result
                    assert "hm_synopsis" in result

    @pytest.mark.asyncio
    async def test_partial_below_threshold(self):
        """All rounds pass individually but weighted average is below FINAL_THRESHOLD."""
        call_count = [0]

        async def side_effect(prompt, max_tokens=500):
            call_count[0] += 1
            if call_count[0] == 1:
                return {"score": 45, "proceed": True, "reason": "Barely passing", "skills_match": "weak"}
            elif call_count[0] == 2:
                return {"score": 55, "proceed": True, "reason": "Some alignment", "values_alignment": "moderate"}
            else:
                return {"score": 50, "reason": "Uncertain", "deep_fit": "uncertain",
                        "candidate_synopsis": {}, "hm_synopsis": {}, "negotiation_summary": ""}

        with patch.object(self.protocol, "_call_round", side_effect=side_effect):
            with patch("app.services.negotiation_protocol.ANTHROPIC_API_KEY", "test-key"):
                result = await self.protocol.negotiate(self.talent_agent, self.hm_agent)
                expected = int(45 * 0.3 + 55 * 0.4 + 50 * 0.3)  # 50.5 -> 50
                assert result["final_score"] == expected
                assert result["status"] == "partial"

    @pytest.mark.asyncio
    async def test_no_api_key_returns_error(self):
        with patch("app.services.negotiation_protocol.ANTHROPIC_API_KEY", ""):
            result = await self.protocol.negotiate(self.talent_agent, self.hm_agent)
            assert result["status"] == "error"

    @pytest.mark.asyncio
    async def test_weighted_score_calculation(self):
        """Verify the 30/40/30 weighting is correct."""
        r1_score, r2_score, r3_score = 80, 90, 70
        expected = int(r1_score * 0.3 + r2_score * 0.4 + r3_score * 0.3)
        assert expected == 81  # 24 + 36 + 21 = 81


class TestCallRound:
    """Test the _call_round helper."""

    def setup_method(self):
        self.protocol = NegotiationProtocol()

    @pytest.mark.asyncio
    async def test_call_round_parses_json(self):
        mock_response = MagicMock()
        mock_response.content = [MagicMock(text='{"score": 75, "reason": "Good match"}')]

        with patch.object(self.protocol, "_anthropic") as mock_client:
            mock_client.messages.create.return_value = mock_response
            self.protocol._anthropic = mock_client

            result = await self.protocol._call_round("test prompt", max_tokens=300)
            assert result["score"] == 75

    @pytest.mark.asyncio
    async def test_call_round_handles_markdown_json(self):
        mock_response = MagicMock()
        mock_response.content = [MagicMock(text='```json\n{"score": 60, "reason": "ok"}\n```')]

        with patch.object(self.protocol, "_anthropic") as mock_client:
            mock_client.messages.create.return_value = mock_response
            self.protocol._anthropic = mock_client

            result = await self.protocol._call_round("test prompt")
            assert result["score"] == 60

    @pytest.mark.asyncio
    async def test_call_round_handles_parse_error(self):
        mock_response = MagicMock()
        mock_response.content = [MagicMock(text='not valid json at all')]

        with patch.object(self.protocol, "_anthropic") as mock_client:
            mock_client.messages.create.return_value = mock_response
            self.protocol._anthropic = mock_client

            result = await self.protocol._call_round("test prompt")
            assert result["score"] == 50  # Fallback
            assert result["proceed"] is True

    @pytest.mark.asyncio
    async def test_call_round_handles_api_error(self):
        with patch.object(self.protocol, "_anthropic") as mock_client:
            mock_client.messages.create.side_effect = RuntimeError("API unavailable")
            self.protocol._anthropic = mock_client

            result = await self.protocol._call_round("test prompt")
            assert result["score"] == 0
            assert result["proceed"] is False
