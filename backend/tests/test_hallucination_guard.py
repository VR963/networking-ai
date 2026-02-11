"""Tests for hallucination guard service."""

import json
import pytest
from unittest.mock import patch, MagicMock, AsyncMock

from app.services.hallucination_guard import HallucinationGuard, AGENT_INTEGRITY_DIRECTIVE, HM_INTEGRITY_DIRECTIVE


class TestHallucinationGuardDirectives:
    """Test integrity directives."""

    def test_talent_directive(self):
        guard = HallucinationGuard()
        directive = guard.get_agent_directive("talent")
        assert "CRITICAL INTEGRITY RULE" in directive
        assert "FORBIDDEN" in directive
        assert "Inventing skills" in directive

    def test_hm_directive(self):
        guard = HallucinationGuard()
        directive = guard.get_agent_directive("hm")
        assert "CRITICAL INTEGRITY RULE" in directive
        assert "Exaggerating salary" in directive

    def test_directive_constants_not_empty(self):
        assert len(AGENT_INTEGRITY_DIRECTIVE) > 100
        assert len(HM_INTEGRITY_DIRECTIVE) > 100


class TestProfileCleaning:
    """Test _clean_profile logic."""

    def setup_method(self):
        self.guard = HallucinationGuard()

    @pytest.mark.asyncio
    async def test_clean_profile_removes_fabricated_string_fields(self):
        profile = {
            "skills": ["Python", "Java", "Kubernetes"],
            "experience": "10 years of AI research",
            "values": ["integrity", "teamwork"],
        }
        violations = [
            {"field": "experience", "claim": "10 years of AI research", "verdict": "fabricated"},
        ]
        cleaned = await self.guard._clean_profile(profile, violations)
        assert cleaned["experience"] == "[Removed: unsupported claim]"
        assert cleaned["skills"] == ["Python", "Java", "Kubernetes"]  # untouched

    @pytest.mark.asyncio
    async def test_clean_profile_removes_fabricated_list_items(self):
        profile = {
            "skills": ["Python", "Quantum Computing", "Java"],
        }
        violations = [
            {"field": "skills", "claim": "Quantum Computing", "verdict": "fabricated"},
        ]
        cleaned = await self.guard._clean_profile(profile, violations)
        assert "Quantum Computing" not in cleaned["skills"]
        assert "Python" in cleaned["skills"]
        assert "Java" in cleaned["skills"]

    @pytest.mark.asyncio
    async def test_clean_profile_ignores_acceptable_inferences(self):
        profile = {"skills": ["Python", "Django"]}
        violations = [
            {"field": "skills", "claim": "Django", "verdict": "inferred_acceptable"},
        ]
        cleaned = await self.guard._clean_profile(profile, violations)
        assert "Django" in cleaned["skills"]

    @pytest.mark.asyncio
    async def test_clean_profile_empty_violations(self):
        profile = {"skills": ["Python"], "values": ["integrity"]}
        cleaned = await self.guard._clean_profile(profile, [])
        assert cleaned == profile

    @pytest.mark.asyncio
    async def test_clean_profile_does_not_mutate_original(self):
        profile = {"skills": ["Python", "Fake"], "name": "Test"}
        violations = [{"field": "skills", "claim": "Fake", "verdict": "fabricated"}]
        cleaned = await self.guard._clean_profile(profile, violations)
        assert "Fake" in profile["skills"]  # original unchanged
        assert "Fake" not in cleaned["skills"]


class TestVerifyProfile:
    """Test profile verification."""

    def setup_method(self):
        self.guard = HallucinationGuard()

    @pytest.mark.asyncio
    async def test_verify_returns_true_without_api_key(self):
        with patch("app.services.hallucination_guard.ANTHROPIC_API_KEY", ""):
            result = await self.guard.verify_profile("talent", {"skills": ["Python"]}, {"cv": "text"})
            assert result["verified"] is True
            assert result["violations"] == []

    @pytest.mark.asyncio
    async def test_verify_profile_with_mock_api(self):
        mock_response = MagicMock()
        mock_response.content = [MagicMock(text=json.dumps({
            "verified": False,
            "violations": [{"claim": "PhD in AI", "field": "education", "verdict": "fabricated", "evidence": "not mentioned"}],
            "severity": "major",
            "fields_to_clean": ["education"],
        }))]

        with patch.object(self.guard, "_anthropic") as mock_client:
            mock_client.messages.create.return_value = mock_response
            self.guard._anthropic = mock_client

            with patch.object(self.guard, "_log_violation", new_callable=AsyncMock):
                result = await self.guard.verify_profile(
                    "talent",
                    {"education": "PhD in AI", "skills": ["Python"]},
                    {"cv_analysis": {"education": "BSc Computer Science"}},
                )
                assert result["verified"] is False
                assert len(result["violations"]) == 1
                assert result["severity"] == "major"


class TestAuditNegotiation:
    """Test negotiation auditing."""

    def setup_method(self):
        self.guard = HallucinationGuard()

    @pytest.mark.asyncio
    async def test_audit_returns_clean_without_api_key(self):
        with patch("app.services.hallucination_guard.ANTHROPIC_API_KEY", ""):
            result = await self.guard.audit_negotiation({}, {}, {})
            assert result["clean"] is True

    @pytest.mark.asyncio
    async def test_audit_with_clean_result(self):
        mock_response = MagicMock()
        mock_response.content = [MagicMock(text=json.dumps({
            "clean": True,
            "violations": [],
            "score_justified": True,
            "recommended_action": "none",
        }))]

        with patch.object(self.guard, "_anthropic") as mock_client:
            mock_client.messages.create.return_value = mock_response
            self.guard._anthropic = mock_client

            result = await self.guard.audit_negotiation(
                {"profile": {"skills": ["Python"]}},
                {"profile": {"requirements": ["Python"]}},
                {"score": 75, "status": "matched"},
            )
            assert result["clean"] is True
