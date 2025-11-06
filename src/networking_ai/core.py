"""
Core functionality for the Networking AI platform.

This module contains the main classes and functions for:
- User profile management
- Semantic discovery
- AI agent interactions
"""

from typing import List, Dict, Optional
from .semantic import SemanticMatcher
from .ai_agent import AnthropicAgent
from .config import config


class UserProfile:
    """Represents a user profile in the networking platform."""

    def __init__(
        self,
        user_id: str,
        name: str,
        skills: Optional[List[str]] = None,
        interests: Optional[List[str]] = None,
        bio: Optional[str] = None,
        goals: Optional[str] = None,
    ):
        """
        Initialize a user profile.

        Args:
            user_id: Unique identifier for the user
            name: User's name
            skills: List of user skills
            interests: List of user interests
            bio: User biography
            goals: Professional goals
        """
        self.user_id = user_id
        self.name = name
        self.skills = skills or []
        self.interests = interests or []
        self.bio = bio
        self.goals = goals

    def to_dict(self) -> Dict:
        """Convert profile to dictionary representation."""
        return {
            "user_id": self.user_id,
            "name": self.name,
            "skills": self.skills,
            "interests": self.interests,
            "bio": self.bio,
            "goals": self.goals,
        }

    @classmethod
    def from_dict(cls, data: Dict) -> "UserProfile":
        """
        Create UserProfile from dictionary.

        Args:
            data: Dictionary containing profile data

        Returns:
            UserProfile instance
        """
        return cls(
            user_id=data.get("user_id", ""),
            name=data.get("name", ""),
            skills=data.get("skills", []),
            interests=data.get("interests", []),
            bio=data.get("bio"),
            goals=data.get("goals"),
        )


class NetworkingAgent:
    """AI-powered networking agent for discovering and facilitating connections."""

    def __init__(self, name: str, api_key: Optional[str] = None):
        """
        Initialize a networking agent.

        Args:
            name: The name of the agent
            api_key: Optional Anthropic API key
        """
        self.name = name
        self.semantic_matcher = SemanticMatcher()
        self.ai_agent: Optional[AnthropicAgent] = None

        # Initialize AI agent if API key is available
        if config.ENABLE_AI_ANALYSIS:
            try:
                self.ai_agent = AnthropicAgent(api_key=api_key)
            except ValueError as e:
                print(f"Warning: AI agent disabled - {e}")

    def discover_connections(
        self,
        user_profile: Dict,
        candidate_profiles: List[Dict],
        top_n: Optional[int] = None,
        min_score: Optional[float] = None,
    ) -> List[Dict]:
        """
        Discover potential connections based on user profile.

        Args:
            user_profile: Dictionary containing user information
            candidate_profiles: List of potential connection profiles
            top_n: Number of top matches to return
            min_score: Minimum similarity score threshold

        Returns:
            List of potential connections with match information
        """
        matches = self.semantic_matcher.find_best_matches(
            user_profile, candidate_profiles, top_n=top_n, min_score=min_score
        )

        results = []
        for profile, scores in matches:
            match_info = {
                "profile": profile,
                "scores": scores,
            }

            # Add AI-generated explanation if available
            if self.ai_agent:
                try:
                    explanation = self.ai_agent.explain_match(
                        user_profile, profile, scores
                    )
                    match_info["explanation"] = explanation
                except Exception as e:
                    print(f"Warning: Could not generate explanation - {e}")

            results.append(match_info)

        return results

    def enrich_profile(self, profile: Dict) -> Dict:
        """
        Enrich a profile with AI-generated insights.

        Args:
            profile: User profile dictionary

        Returns:
            Enhanced profile with AI insights
        """
        if not self.ai_agent:
            return profile

        return self.ai_agent.enrich_profile(profile)

    def generate_introduction(
        self, profile1: Dict, profile2: Dict, match_scores: Dict
    ) -> Optional[str]:
        """
        Generate a personalized introduction between two profiles.

        Args:
            profile1: First user's profile
            profile2: Second user's profile
            match_scores: Similarity scores

        Returns:
            Introduction message or None if AI agent unavailable
        """
        if not self.ai_agent:
            return None

        try:
            return self.ai_agent.generate_introduction(profile1, profile2, match_scores)
        except Exception as e:
            print(f"Warning: Could not generate introduction - {e}")
            return None
