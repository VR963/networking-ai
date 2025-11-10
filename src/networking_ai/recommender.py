"""Connection recommendation engine combining semantic matching and AI insights."""

from typing import List, Dict, Optional, Tuple
from .core import UserProfile, NetworkingAgent
from .semantic import SemanticMatcher
from .ai_agent import AnthropicAgent
from .config import config


class ConnectionRecommender:
    """
    Advanced recommendation engine for professional networking.

    Combines semantic similarity, AI-powered analysis, and intelligent
    filtering to provide high-quality connection recommendations.
    """

    def __init__(self, api_key: Optional[str] = None):
        """
        Initialize the recommendation engine.

        Args:
            api_key: Optional Anthropic API key
        """
        self.semantic_matcher = SemanticMatcher()
        self.ai_agent: Optional[AnthropicAgent] = None

        if config.ENABLE_AI_ANALYSIS:
            try:
                self.ai_agent = AnthropicAgent(api_key=api_key)
            except ValueError:
                pass

    def recommend_connections(
        self,
        user: UserProfile,
        candidates: List[UserProfile],
        top_n: Optional[int] = None,
        min_score: Optional[float] = None,
        include_explanations: bool = True,
        include_introductions: bool = False,
    ) -> List[Dict]:
        """
        Generate personalized connection recommendations.

        Args:
            user: User profile to generate recommendations for
            candidates: List of candidate profiles to match against
            top_n: Number of recommendations to return
            min_score: Minimum similarity threshold
            include_explanations: Whether to include AI explanations
            include_introductions: Whether to generate intro messages

        Returns:
            List of recommendation dictionaries with profiles and metadata
        """
        user_dict = user.to_dict()
        candidate_dicts = [c.to_dict() for c in candidates]

        # Get semantic matches
        matches = self.semantic_matcher.find_best_matches(
            user_dict, candidate_dicts, top_n=top_n, min_score=min_score
        )

        recommendations = []
        for profile_dict, scores in matches:
            recommendation = {
                "user_id": profile_dict["user_id"],
                "name": profile_dict["name"],
                "profile": profile_dict,
                "match_scores": scores,
                "match_strength": self._classify_match_strength(
                    scores["weighted_score"]
                ),
            }

            # Add AI-generated explanation
            if include_explanations and self.ai_agent:
                try:
                    explanation = self.ai_agent.explain_match(
                        user_dict, profile_dict, scores
                    )
                    recommendation["explanation"] = explanation
                except Exception as e:
                    print(f"Warning: Could not generate explanation - {e}")

            # Add AI-generated introduction
            if include_introductions and self.ai_agent:
                try:
                    introduction = self.ai_agent.generate_introduction(
                        user_dict, profile_dict, scores
                    )
                    recommendation["introduction"] = introduction
                except Exception as e:
                    print(f"Warning: Could not generate introduction - {e}")

            recommendations.append(recommendation)

        return recommendations

    def find_skill_matches(
        self,
        user: UserProfile,
        candidates: List[UserProfile],
        required_skills: Optional[List[str]] = None,
        top_n: Optional[int] = None,
    ) -> List[Dict]:
        """
        Find connections based on specific skill requirements.

        Args:
            user: User profile
            candidates: Candidate profiles
            required_skills: Specific skills to match (uses user skills if None)
            top_n: Number of matches to return

        Returns:
            List of skill-based matches
        """
        skills_to_match = required_skills or user.skills
        matches = []

        for candidate in candidates:
            if candidate.user_id == user.user_id:
                continue

            skill_score = self.semantic_matcher.calculate_skill_similarity(
                skills_to_match, candidate.skills
            )

            if skill_score > 0:
                matches.append(
                    {
                        "user_id": candidate.user_id,
                        "name": candidate.name,
                        "profile": candidate.to_dict(),
                        "skill_score": skill_score,
                        "matching_skills": self._find_matching_skills(
                            skills_to_match, candidate.skills
                        ),
                    }
                )

        # Sort by skill score
        matches.sort(key=lambda x: x["skill_score"], reverse=True)

        return matches[:top_n] if top_n else matches

    def batch_recommend(
        self,
        users: List[UserProfile],
        candidates: List[UserProfile],
        top_n_per_user: int = 5,
    ) -> Dict[str, List[Dict]]:
        """
        Generate recommendations for multiple users in batch.

        Args:
            users: List of users to generate recommendations for
            candidates: Pool of candidate profiles
            top_n_per_user: Number of recommendations per user

        Returns:
            Dictionary mapping user_id to list of recommendations
        """
        results = {}

        for user in users:
            recommendations = self.recommend_connections(
                user,
                candidates,
                top_n=top_n_per_user,
                include_explanations=False,  # Disable for performance
                include_introductions=False,
            )
            results[user.user_id] = recommendations

        return results

    def _classify_match_strength(self, score: float) -> str:
        """
        Classify match strength based on score.

        Args:
            score: Weighted similarity score

        Returns:
            Match strength classification
        """
        if score >= 0.9:
            return "excellent"
        elif score >= 0.8:
            return "strong"
        elif score >= 0.7:
            return "good"
        elif score >= 0.6:
            return "moderate"
        else:
            return "weak"

    def _find_matching_skills(
        self, skills1: List[str], skills2: List[str]
    ) -> List[Tuple[str, str, float]]:
        """
        Find matching skills between two skill lists.

        Args:
            skills1: First skill list
            skills2: Second skill list

        Returns:
            List of tuples (skill1, skill2, similarity_score)
        """
        matches = []

        for skill1 in skills1:
            emb1 = self.semantic_matcher.generate_embedding(skill1)

            for skill2 in skills2:
                emb2 = self.semantic_matcher.generate_embedding(skill2)
                similarity = self.semantic_matcher.calculate_similarity(emb1, emb2)

                if similarity >= 0.7:  # High similarity threshold
                    matches.append((skill1, skill2, similarity))

        # Sort by similarity
        matches.sort(key=lambda x: x[2], reverse=True)
        return matches


def create_recommender(api_key: Optional[str] = None) -> ConnectionRecommender:
    """
    Factory function to create a ConnectionRecommender instance.

    Args:
        api_key: Optional Anthropic API key

    Returns:
        Configured ConnectionRecommender instance
    """
    return ConnectionRecommender(api_key=api_key)
