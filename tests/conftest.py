"""Pytest configuration and fixtures."""

import pytest
from networking_ai.core import UserProfile, NetworkingAgent


@pytest.fixture
def sample_user_profile():
    """Create a sample user profile for testing."""
    return UserProfile(
        user_id="test123",
        name="Test User",
        skills=["Python", "AI", "Machine Learning"]
    )


@pytest.fixture
def sample_agent():
    """Create a sample networking agent for testing."""
    return NetworkingAgent(name="TestAgent")


@pytest.fixture
def multiple_profiles():
    """Create multiple user profiles for testing."""
    return [
        UserProfile(user_id="user1", name="Alice", skills=["Python", "Django"]),
        UserProfile(user_id="user2", name="Bob", skills=["JavaScript", "React"]),
        UserProfile(user_id="user3", name="Charlie", skills=["Python", "AI"]),
    ]
