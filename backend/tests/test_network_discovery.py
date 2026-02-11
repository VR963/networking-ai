"""Tests for network discovery service."""

import pytest
from unittest.mock import patch, MagicMock

from app.services.network_discovery import (
    NetworkDiscovery,
    INDUSTRY_ADJACENCY,
    DISCOVERY_THRESHOLD,
)


class TestIndustryAdjacency:
    """Test industry adjacency map."""

    def test_tech_adjacencies(self):
        assert "engineering" in INDUSTRY_ADJACENCY["tech"]
        assert "finance" in INDUSTRY_ADJACENCY["tech"]

    def test_adjacency_is_symmetric_for_key_pairs(self):
        # tech <-> engineering
        assert "engineering" in INDUSTRY_ADJACENCY["tech"]
        assert "tech" in INDUSTRY_ADJACENCY["engineering"]

    def test_all_adjacencies_are_lists(self):
        for industry, adjacencies in INDUSTRY_ADJACENCY.items():
            assert isinstance(adjacencies, list), f"{industry} adjacencies should be a list"


class TestComputeCompatibility:
    """Test the lightweight compatibility scoring."""

    def setup_method(self):
        self.discovery = NetworkDiscovery()

    def test_same_industry_bonus(self):
        talent = {"industry": "tech", "profile": {}}
        hm = {"industry": "tech", "profile": {}}
        score, reasons = self.discovery._compute_compatibility(talent, hm)
        assert score >= 25
        assert any("Same industry" in r for r in reasons)

    def test_adjacent_industry_bonus(self):
        talent = {"industry": "tech", "profile": {}}
        hm = {"industry": "engineering", "profile": {}}
        score, reasons = self.discovery._compute_compatibility(talent, hm)
        assert score >= 15
        assert any("Adjacent" in r for r in reasons)

    def test_different_industry_low_bonus(self):
        talent = {"industry": "tech", "profile": {}}
        hm = {"industry": "agriculture", "profile": {}}
        score, reasons = self.discovery._compute_compatibility(talent, hm)
        assert score >= 5  # Still gets base points

    def test_skills_overlap_scoring(self):
        talent = {
            "industry": "tech",
            "profile": {"skills_verified": ["Python", "Machine Learning", "AWS"]},
        }
        hm = {
            "industry": "tech",
            "profile": {"role_requirements": {"must_have": ["Python", "AWS", "Docker"]}},
        }
        score, reasons = self.discovery._compute_compatibility(talent, hm)
        assert score > 25  # Industry + skills
        assert any("Skills match" in r for r in reasons)

    def test_dealbreaker_penalty(self):
        talent = {
            "industry": "tech",
            "profile": {"dealbreakers": ["no remote work", "micromanagement"]},
        }
        hm = {
            "industry": "tech",
            "profile": {"about": "We require all employees on-site, no remote work allowed."},
        }
        score, reasons = self.discovery._compute_compatibility(talent, hm)
        assert any("dealbreaker" in r.lower() for r in reasons)

    def test_score_clamped_to_0_100(self):
        # Even with massive dealbreaker penalty, score shouldn't go below 0
        talent = {
            "industry": "tech",
            "profile": {"dealbreakers": ["toxic culture"]},
        }
        hm = {
            "industry": "tech",
            "profile": {"about": "Our toxic culture is legendary"},
        }
        score, _ = self.discovery._compute_compatibility(talent, hm)
        assert 0 <= score <= 100

    def test_values_alignment_scoring(self):
        talent = {
            "industry": "tech",
            "profile": {"values": ["innovation", "autonomy", "transparency"]},
        }
        hm = {
            "industry": "tech",
            "profile": {
                "hidden_preferences": ["innovation", "self-starter"],
                "team_culture": {"vibe": "fast-paced innovative environment"},
            },
        }
        score, reasons = self.discovery._compute_compatibility(talent, hm)
        assert any("Values" in r for r in reasons)

    def test_environment_compatibility(self):
        talent = {
            "industry": "tech",
            "profile": {"environment_preferences": {"pace": "fast"}},
        }
        hm = {
            "industry": "tech",
            "profile": {"team_culture": {"pace": "fast"}},
        }
        score, reasons = self.discovery._compute_compatibility(talent, hm)
        assert any("Environment" in r for r in reasons)

    def test_empty_profiles_no_crash(self):
        talent = {"industry": "general", "profile": {}}
        hm = {"industry": "general", "profile": {}}
        score, reasons = self.discovery._compute_compatibility(talent, hm)
        assert isinstance(score, int)
        assert isinstance(reasons, list)


class TestFindMatches:
    """Test match finding with mocked DB."""

    def setup_method(self):
        self.discovery = NetworkDiscovery()

    @pytest.mark.asyncio
    async def test_find_matches_no_db(self):
        with patch("app.services.network_discovery.get_db", return_value=None):
            result = await self.discovery.find_matches_for_talent({"industry": "tech", "profile": {}})
            assert result == []

    @pytest.mark.asyncio
    async def test_find_matches_returns_sorted(self):
        mock_client = MagicMock()
        mock_table = MagicMock()
        mock_table.select.return_value = mock_table
        mock_table.eq.return_value = mock_table
        mock_table.execute.return_value = MagicMock(data=[
            {"id": "hm1", "agent_type": "hm", "active": True, "industry": "tech",
             "profile": {"skills_verified": ["Python"]}},
            {"id": "hm2", "agent_type": "hm", "active": True, "industry": "finance",
             "profile": {}},
        ])
        mock_client.table.return_value = mock_table

        with patch("app.services.network_discovery.get_db", return_value=mock_client):
            talent = {"industry": "tech", "profile": {"skills_verified": ["Python"]}}
            results = await self.discovery.find_matches_for_talent(talent)
            # Results should be sorted by score descending
            if len(results) >= 2:
                assert results[0]["compatibility_score"] >= results[1]["compatibility_score"]

    @pytest.mark.asyncio
    async def test_discover_all_pairs_skips_existing(self):
        mock_client = MagicMock()

        call_count = [0]
        def table_side_effect(name):
            call_count[0] += 1
            mock_table = MagicMock()
            mock_table.select.return_value = mock_table
            mock_table.eq.return_value = mock_table
            mock_table.execute.return_value = MagicMock(data=[])

            if name == "cv2_agents" and call_count[0] == 1:
                # Talent agents
                mock_table.execute.return_value = MagicMock(data=[
                    {"id": "t1", "user_id": "u1", "agent_type": "talent",
                     "active": True, "industry": "tech", "profile": {}},
                ])
            elif name == "cv2_agents" and call_count[0] == 2:
                # HM agents
                mock_table.execute.return_value = MagicMock(data=[
                    {"id": "h1", "job_id": "j1", "agent_type": "hm",
                     "active": True, "industry": "tech", "profile": {}},
                ])
            elif name == "cv2_a2a_matches":
                # Existing match for this pair
                mock_table.execute.return_value = MagicMock(data=[
                    {"candidate_id": "u1", "job_id": "j1"},
                ])
            return mock_table

        mock_client.table.side_effect = table_side_effect

        with patch("app.services.network_discovery.get_db", return_value=mock_client):
            pairs = await self.discovery.discover_all_pairs()
            assert len(pairs) == 0  # Should skip existing pair
