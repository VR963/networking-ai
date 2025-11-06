"""Tests for connection recommendation engine."""

import pytest
from networking_ai.core import UserProfile
from networking_ai.recommender import ConnectionRecommender, create_recommender


class TestConnectionRecommender:
    """Test cases for ConnectionRecommender class."""

    def test_recommender_initialization(self):
        """Test creating a recommender."""
        recommender = ConnectionRecommender()
        assert recommender.semantic_matcher is not None

    def test_create_recommender_factory(self):
        """Test factory function."""
        recommender = create_recommender()
        assert isinstance(recommender, ConnectionRecommender)

    def test_recommend_connections_basic(self):
        """Test basic connection recommendations."""
        recommender = ConnectionRecommender()

        user = UserProfile(
            user_id="user1",
            name="Alice",
            skills=["Python", "Machine Learning"],
        )

        candidates = [
            UserProfile(
                user_id="user2",
                name="Bob",
                skills=["Python", "AI"],
            ),
            UserProfile(
                user_id="user3",
                name="Charlie",
                skills=["JavaScript", "React"],
            ),
        ]

        recommendations = recommender.recommend_connections(
            user, candidates, include_explanations=False, include_introductions=False
        )

        assert isinstance(recommendations, list)
        if len(recommendations) > 0:
            rec = recommendations[0]
            assert "user_id" in rec
            assert "name" in rec
            assert "match_scores" in rec
            assert "match_strength" in rec

    def test_find_skill_matches(self):
        """Test skill-based matching."""
        recommender = ConnectionRecommender()

        user = UserProfile(
            user_id="user1",
            name="Alice",
            skills=["Python", "Machine Learning"],
        )

        candidates = [
            UserProfile(
                user_id="user2",
                name="Bob",
                skills=["Python", "AI"],
            ),
            UserProfile(
                user_id="user3",
                name="Charlie",
                skills=["Python", "Data Science"],
            ),
        ]

        matches = recommender.find_skill_matches(user, candidates)

        assert isinstance(matches, list)
        for match in matches:
            assert "user_id" in match
            assert "skill_score" in match

    def test_batch_recommend(self):
        """Test batch recommendations."""
        recommender = ConnectionRecommender()

        users = [
            UserProfile(user_id="user1", name="Alice", skills=["Python"]),
            UserProfile(user_id="user2", name="Bob", skills=["JavaScript"]),
        ]

        candidates = [
            UserProfile(user_id="user3", name="Charlie", skills=["Python", "AI"]),
            UserProfile(user_id="user4", name="David", skills=["React", "Node.js"]),
        ]

        results = recommender.batch_recommend(users, candidates, top_n_per_user=2)

        assert isinstance(results, dict)
        assert "user1" in results
        assert "user2" in results

    def test_match_strength_classification(self):
        """Test match strength classification."""
        recommender = ConnectionRecommender()

        assert recommender._classify_match_strength(0.95) == "excellent"
        assert recommender._classify_match_strength(0.85) == "strong"
        assert recommender._classify_match_strength(0.75) == "good"
        assert recommender._classify_match_strength(0.65) == "moderate"
        assert recommender._classify_match_strength(0.55) == "weak"

    def test_find_matching_skills(self):
        """Test finding matching skills."""
        recommender = ConnectionRecommender()

        skills1 = ["Python", "Machine Learning"]
        skills2 = ["Python", "AI", "Deep Learning"]

        matches = recommender._find_matching_skills(skills1, skills2)

        assert isinstance(matches, list)
        if len(matches) > 0:
            skill1, skill2, score = matches[0]
            assert isinstance(skill1, str)
            assert isinstance(skill2, str)
            assert 0 <= score <= 1
