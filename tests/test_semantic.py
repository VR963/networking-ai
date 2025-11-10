"""Tests for semantic matching functionality."""

import pytest
import numpy as np
from src.networking_ai.semantic import SemanticMatcher


class TestSemanticMatcher:
    """Test cases for SemanticMatcher class."""

    def test_matcher_initialization(self):
        """Test creating a semantic matcher."""
        matcher = SemanticMatcher()
        assert matcher.model_name is not None
        assert matcher._cache == {}

    def test_generate_embedding(self):
        """Test embedding generation."""
        matcher = SemanticMatcher()
        embedding = matcher.generate_embedding("Python programming")

        assert isinstance(embedding, np.ndarray)
        assert len(embedding.shape) == 1
        assert embedding.shape[0] > 0

    def test_embedding_caching(self):
        """Test that embeddings are cached."""
        matcher = SemanticMatcher()
        text = "Machine Learning Engineer"

        # Generate embedding twice
        emb1 = matcher.generate_embedding(text)
        emb2 = matcher.generate_embedding(text)

        # Should be the same object from cache
        assert np.array_equal(emb1, emb2)

    def test_generate_profile_text(self):
        """Test profile text generation."""
        matcher = SemanticMatcher()
        profile = {
            "name": "John Doe",
            "skills": ["Python", "AI"],
            "interests": ["Machine Learning"],
            "bio": "Software engineer",
        }

        text = matcher.generate_profile_text(profile)

        assert "John Doe" in text
        assert "Python" in text
        assert "AI" in text
        assert "Machine Learning" in text

    def test_calculate_similarity(self):
        """Test similarity calculation between embeddings."""
        matcher = SemanticMatcher()

        emb1 = matcher.generate_embedding("Python programming")
        emb2 = matcher.generate_embedding("Python development")
        emb3 = matcher.generate_embedding("Cooking recipes")

        # Similar texts should have high similarity
        sim_high = matcher.calculate_similarity(emb1, emb2)
        assert sim_high > 0.7

        # Different texts should have lower similarity
        sim_low = matcher.calculate_similarity(emb1, emb3)
        assert sim_low < sim_high

    def test_calculate_skill_similarity(self):
        """Test skill similarity calculation."""
        matcher = SemanticMatcher()

        skills1 = ["Python", "Machine Learning"]
        skills2 = ["Python", "AI"]
        skills3 = ["Cooking", "Baking"]

        # Related skills should have high similarity
        sim_high = matcher.calculate_skill_similarity(skills1, skills2)
        assert sim_high > 0.5

        # Unrelated skills should have low similarity
        sim_low = matcher.calculate_skill_similarity(skills1, skills3)
        assert sim_low < sim_high

    def test_match_profiles(self):
        """Test profile matching."""
        matcher = SemanticMatcher()

        profile1 = {
            "user_id": "user1",
            "name": "Alice",
            "skills": ["Python", "Machine Learning"],
        }

        profile2 = {
            "user_id": "user2",
            "name": "Bob",
            "skills": ["Python", "AI"],
        }

        scores = matcher.match_profiles(profile1, profile2)

        assert "overall_score" in scores
        assert "skill_score" in scores
        assert "weighted_score" in scores
        assert 0 <= scores["overall_score"] <= 1
        assert 0 <= scores["skill_score"] <= 1
        assert 0 <= scores["weighted_score"] <= 1

    def test_find_best_matches(self):
        """Test finding best matches from candidates."""
        matcher = SemanticMatcher()

        target = {
            "user_id": "target",
            "name": "Target User",
            "skills": ["Python", "Machine Learning"],
        }

        candidates = [
            {
                "user_id": "user1",
                "name": "User 1",
                "skills": ["Python", "AI"],
            },
            {
                "user_id": "user2",
                "name": "User 2",
                "skills": ["JavaScript", "React"],
            },
            {
                "user_id": "user3",
                "name": "User 3",
                "skills": ["Python", "Data Science"],
            },
        ]

        matches = matcher.find_best_matches(target, candidates, top_n=2, min_score=0.0)

        assert len(matches) <= 2
        # Verify structure
        for profile, scores in matches:
            assert "user_id" in profile
            assert "weighted_score" in scores

    def test_clear_cache(self):
        """Test cache clearing."""
        matcher = SemanticMatcher()

        matcher.generate_embedding("test")
        assert len(matcher._cache) > 0

        matcher.clear_cache()
        assert len(matcher._cache) == 0
