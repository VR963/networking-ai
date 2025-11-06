"""Semantic matching and similarity scoring for user profiles."""

from typing import List, Dict, Tuple, Optional
import numpy as np
from sentence_transformers import SentenceTransformer
from sklearn.metrics.pairwise import cosine_similarity
from .config import config


class SemanticMatcher:
    """Handles semantic matching and similarity scoring."""

    def __init__(self, model_name: Optional[str] = None):
        """
        Initialize the semantic matcher.

        Args:
            model_name: Name of the sentence transformer model to use.
                       Defaults to config.EMBEDDING_MODEL
        """
        self.model_name = model_name or config.EMBEDDING_MODEL
        self._model: Optional[SentenceTransformer] = None
        self._cache: Dict[str, np.ndarray] = {}

    @property
    def model(self) -> SentenceTransformer:
        """Lazy load the sentence transformer model."""
        if self._model is None:
            self._model = SentenceTransformer(self.model_name)
        return self._model

    def generate_embedding(self, text: str, use_cache: bool = True) -> np.ndarray:
        """
        Generate embedding for a text string.

        Args:
            text: Text to embed
            use_cache: Whether to use cached embeddings

        Returns:
            Numpy array representing the embedding
        """
        if use_cache and config.ENABLE_CACHING and text in self._cache:
            return self._cache[text]

        embedding = self.model.encode(text, convert_to_numpy=True)

        if use_cache and config.ENABLE_CACHING:
            self._cache[text] = embedding

        return embedding

    def generate_profile_text(self, profile: Dict) -> str:
        """
        Generate a text representation of a user profile for embedding.

        Args:
            profile: User profile dictionary

        Returns:
            Text representation of the profile
        """
        parts = []

        if "name" in profile:
            parts.append(f"Name: {profile['name']}")

        if "skills" in profile:
            skills_str = ", ".join(profile["skills"])
            parts.append(f"Skills: {skills_str}")

        if "interests" in profile:
            interests_str = ", ".join(profile["interests"])
            parts.append(f"Interests: {interests_str}")

        if "bio" in profile:
            parts.append(f"Bio: {profile['bio']}")

        if "goals" in profile:
            parts.append(f"Goals: {profile['goals']}")

        return " | ".join(parts)

    def calculate_similarity(
        self, embedding1: np.ndarray, embedding2: np.ndarray
    ) -> float:
        """
        Calculate cosine similarity between two embeddings.

        Args:
            embedding1: First embedding
            embedding2: Second embedding

        Returns:
            Similarity score between 0 and 1
        """
        # Reshape for sklearn
        emb1 = embedding1.reshape(1, -1)
        emb2 = embedding2.reshape(1, -1)

        similarity = cosine_similarity(emb1, emb2)[0][0]
        return float(similarity)

    def calculate_skill_similarity(
        self, skills1: List[str], skills2: List[str]
    ) -> float:
        """
        Calculate similarity between two skill sets.

        Args:
            skills1: First list of skills
            skills2: Second list of skills

        Returns:
            Skill similarity score between 0 and 1
        """
        if not skills1 or not skills2:
            return 0.0

        # Generate embeddings for each skill
        embeddings1 = [self.generate_embedding(skill) for skill in skills1]
        embeddings2 = [self.generate_embedding(skill) for skill in skills2]

        # Calculate average similarity
        similarities = []
        for emb1 in embeddings1:
            max_sim = max(
                self.calculate_similarity(emb1, emb2) for emb2 in embeddings2
            )
            similarities.append(max_sim)

        return float(np.mean(similarities))

    def match_profiles(
        self, profile1: Dict, profile2: Dict
    ) -> Dict[str, float]:
        """
        Calculate comprehensive match score between two profiles.

        Args:
            profile1: First user profile
            profile2: Second user profile

        Returns:
            Dictionary with overall score and component scores
        """
        # Generate profile embeddings
        text1 = self.generate_profile_text(profile1)
        text2 = self.generate_profile_text(profile2)

        embedding1 = self.generate_embedding(text1)
        embedding2 = self.generate_embedding(text2)

        overall_similarity = self.calculate_similarity(embedding1, embedding2)

        # Calculate skill similarity if available
        skill_similarity = 0.0
        if "skills" in profile1 and "skills" in profile2:
            skill_similarity = self.calculate_skill_similarity(
                profile1["skills"], profile2["skills"]
            )

        # Weighted score (60% overall, 40% skills)
        weighted_score = (0.6 * overall_similarity) + (0.4 * skill_similarity)

        return {
            "overall_score": float(overall_similarity),
            "skill_score": float(skill_similarity),
            "weighted_score": float(weighted_score),
        }

    def find_best_matches(
        self,
        target_profile: Dict,
        candidate_profiles: List[Dict],
        top_n: Optional[int] = None,
        min_score: Optional[float] = None,
    ) -> List[Tuple[Dict, Dict[str, float]]]:
        """
        Find best matching profiles from a list of candidates.

        Args:
            target_profile: Profile to match against
            candidate_profiles: List of candidate profiles
            top_n: Number of top matches to return (defaults to config)
            min_score: Minimum weighted score threshold (defaults to config)

        Returns:
            List of tuples (profile, scores) sorted by weighted_score descending
        """
        top_n = top_n or config.TOP_N_RECOMMENDATIONS
        min_score = min_score or config.MIN_SIMILARITY_SCORE

        matches = []
        for candidate in candidate_profiles:
            # Skip matching against self
            if candidate.get("user_id") == target_profile.get("user_id"):
                continue

            scores = self.match_profiles(target_profile, candidate)

            if scores["weighted_score"] >= min_score:
                matches.append((candidate, scores))

        # Sort by weighted score descending
        matches.sort(key=lambda x: x[1]["weighted_score"], reverse=True)

        return matches[:top_n]

    def clear_cache(self):
        """Clear the embedding cache."""
        self._cache.clear()
