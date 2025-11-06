"""Tests for core functionality."""

import pytest
from networking_ai.core import NetworkingAgent, UserProfile


class TestUserProfile:
    """Test cases for UserProfile class."""

    def test_user_profile_creation(self):
        """Test creating a user profile."""
        profile = UserProfile(
            user_id="user123",
            name="John Doe",
            skills=["Python", "AI", "Machine Learning"],
            interests=["Data Science"],
            bio="Software engineer",
            goals="Build AI products",
        )
        assert profile.user_id == "user123"
        assert profile.name == "John Doe"
        assert len(profile.skills) == 3
        assert len(profile.interests) == 1
        assert profile.bio == "Software engineer"
        assert profile.goals == "Build AI products"

    def test_user_profile_to_dict(self):
        """Test converting profile to dictionary."""
        profile = UserProfile(user_id="user123", name="John Doe")
        profile_dict = profile.to_dict()
        assert isinstance(profile_dict, dict)
        assert profile_dict["user_id"] == "user123"
        assert profile_dict["name"] == "John Doe"
        assert "skills" in profile_dict
        assert "interests" in profile_dict

    def test_user_profile_from_dict(self):
        """Test creating profile from dictionary."""
        data = {
            "user_id": "user123",
            "name": "John Doe",
            "skills": ["Python"],
            "interests": ["AI"],
        }
        profile = UserProfile.from_dict(data)
        assert profile.user_id == "user123"
        assert profile.name == "John Doe"
        assert profile.skills == ["Python"]

    def test_user_profile_defaults(self):
        """Test profile with default values."""
        profile = UserProfile(user_id="user123", name="John Doe")
        assert profile.skills == []
        assert profile.interests == []
        assert profile.bio is None
        assert profile.goals is None


class TestNetworkingAgent:
    """Test cases for NetworkingAgent class."""

    def test_agent_creation(self):
        """Test creating a networking agent."""
        agent = NetworkingAgent(name="TestAgent")
        assert agent.name == "TestAgent"
        assert agent.semantic_matcher is not None

    def test_discover_connections(self):
        """Test connection discovery."""
        agent = NetworkingAgent(name="TestAgent")
        user_profile = {"user_id": "user123", "name": "John Doe", "skills": ["Python"]}
        candidates = [
            {"user_id": "user456", "name": "Jane Doe", "skills": ["Python", "AI"]},
        ]
        connections = agent.discover_connections(user_profile, candidates)
        assert isinstance(connections, list)

    def test_enrich_profile_without_ai(self):
        """Test profile enrichment without AI agent."""
        agent = NetworkingAgent(name="TestAgent")
        profile = {"user_id": "user123", "name": "John Doe"}

        # Without AI agent, should return original profile
        enriched = agent.enrich_profile(profile)
        assert enriched == profile

    def test_generate_introduction_without_ai(self):
        """Test introduction generation without AI agent."""
        agent = NetworkingAgent(name="TestAgent")
        profile1 = {"user_id": "user1", "name": "Alice"}
        profile2 = {"user_id": "user2", "name": "Bob"}
        scores = {"weighted_score": 0.8}

        # Without AI agent, should return None
        intro = agent.generate_introduction(profile1, profile2, scores)
        assert intro is None
