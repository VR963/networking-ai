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
            skills=["Python", "AI", "Machine Learning"]
        )
        assert profile.user_id == "user123"
        assert profile.name == "John Doe"
        assert len(profile.skills) == 3

    def test_user_profile_to_dict(self):
        """Test converting profile to dictionary."""
        profile = UserProfile(user_id="user123", name="John Doe")
        profile_dict = profile.to_dict()
        assert isinstance(profile_dict, dict)
        assert profile_dict["user_id"] == "user123"
        assert profile_dict["name"] == "John Doe"


class TestNetworkingAgent:
    """Test cases for NetworkingAgent class."""

    def test_agent_creation(self):
        """Test creating a networking agent."""
        agent = NetworkingAgent(name="TestAgent")
        assert agent.name == "TestAgent"

    def test_discover_connections(self):
        """Test connection discovery."""
        agent = NetworkingAgent(name="TestAgent")
        user_profile = {"user_id": "user123", "name": "John Doe"}
        connections = agent.discover_connections(user_profile)
        assert isinstance(connections, list)
