"""
Knowledge Learning System with Semantic Deduplication.

This module handles:
- Learning from user interactions
- Semantic deduplication to avoid storing repetitive information
- Pattern extraction from conversations
- Quality filtering for valuable insights
"""

from typing import List, Dict, Optional, Tuple
from datetime import datetime
import hashlib
import json

from .rag_system import DualRAGSystem
from .semantic import SemanticMatcher
from .config import config


class ConversationDeduplicator:
    """
    Detects and filters duplicate or near-duplicate conversation content.

    Uses semantic similarity to identify repetitive questions/answers
    that don't add new value to the knowledge base.
    """

    def __init__(self, similarity_threshold: float = 0.95):
        """
        Initialize deduplicator.

        Args:
            similarity_threshold: Threshold for considering content duplicate
        """
        self.matcher = SemanticMatcher()
        self.threshold = similarity_threshold
        self._seen_embeddings: List[Tuple[str, any]] = []

    def is_duplicate(self, content: str) -> Tuple[bool, Optional[str]]:
        """
        Check if content is a duplicate of previously seen content.

        Args:
            content: Content to check

        Returns:
            Tuple of (is_duplicate, similar_content_id)
        """
        if not content or len(content.strip()) < 10:
            return True, None  # Too short, consider duplicate

        # Generate embedding
        embedding = self.matcher.generate_embedding(content)

        # Check against seen embeddings
        for content_id, seen_emb in self._seen_embeddings:
            similarity = self.matcher.calculate_similarity(embedding, seen_emb)
            if similarity >= self.threshold:
                return True, content_id

        # Not a duplicate, cache it
        content_id = hashlib.sha256(content.encode()).hexdigest()[:16]
        self._seen_embeddings.append((content_id, embedding))

        # Limit cache size
        if len(self._seen_embeddings) > 1000:
            self._seen_embeddings = self._seen_embeddings[-500:]

        return False, None

    def clear_cache(self):
        """Clear the deduplication cache."""
        self._seen_embeddings.clear()


class QualityFilter:
    """
    Filters conversation content based on quality and value.

    Ensures only high-quality, informative interactions are stored
    in the knowledge base.
    """

    @staticmethod
    def calculate_quality_score(conversation: Dict) -> float:
        """
        Calculate quality score for a conversation.

        Args:
            conversation: Conversation dict with 'question' and 'answer'

        Returns:
            Quality score between 0 and 1
        """
        score = 0.0
        weights = {
            "length": 0.2,
            "informativeness": 0.3,
            "specificity": 0.3,
            "relevance": 0.2,
        }

        question = conversation.get("question", "")
        answer = conversation.get("answer", "")

        # Length score (prefer substantive content)
        total_length = len(question) + len(answer)
        if total_length > 100:
            score += weights["length"]
        elif total_length > 50:
            score += weights["length"] * 0.5

        # Informativeness (check for meaningful words)
        meaningful_words = [
            "because",
            "therefore",
            "however",
            "specifically",
            "example",
            "such as",
        ]
        if any(word in answer.lower() for word in meaningful_words):
            score += weights["informativeness"]

        # Specificity (check for concrete information)
        specific_indicators = ["skill", "experience", "project", "years", "expertise"]
        if any(indicator in question.lower() or indicator in answer.lower() for indicator in specific_indicators):
            score += weights["specificity"]

        # Relevance (not error messages or system responses)
        error_indicators = ["error", "sorry", "don't understand", "try again"]
        if not any(indicator in answer.lower() for indicator in error_indicators):
            score += weights["relevance"]

        return min(score, 1.0)

    @staticmethod
    def is_high_quality(conversation: Dict, min_score: float = 0.7) -> bool:
        """
        Check if conversation meets quality threshold.

        Args:
            conversation: Conversation dict
            min_score: Minimum quality score

        Returns:
            True if high quality
        """
        score = QualityFilter.calculate_quality_score(conversation)
        return score >= min_score


class PIIDetector:
    """
    Detects and removes Personally Identifiable Information (PII).

    Ensures data privacy by identifying and handling sensitive information.
    """

    # Patterns that might indicate PII
    PII_INDICATORS = [
        "email",
        "phone",
        "address",
        "ssn",
        "social security",
        "credit card",
        "password",
        "birth date",
        "birthday",
    ]

    @staticmethod
    def contains_pii(text: str) -> Tuple[bool, List[str]]:
        """
        Check if text contains PII.

        Args:
            text: Text to check

        Returns:
            Tuple of (contains_pii, list_of_detected_types)
        """
        text_lower = text.lower()
        detected = []

        for indicator in PIIDetector.PII_INDICATORS:
            if indicator in text_lower:
                detected.append(indicator)

        # Simple regex checks for common patterns
        import re

        # Email pattern
        if re.search(r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b", text):
            detected.append("email_address")

        # Phone pattern
        if re.search(r"\b\d{3}[-.]?\d{3}[-.]?\d{4}\b", text):
            detected.append("phone_number")

        return len(detected) > 0, detected

    @staticmethod
    def anonymize_text(text: str) -> str:
        """
        Anonymize PII in text.

        Args:
            text: Text to anonymize

        Returns:
            Anonymized text
        """
        import re

        # Replace emails
        text = re.sub(
            r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b",
            "[EMAIL]",
            text,
        )

        # Replace phone numbers
        text = re.sub(r"\b\d{3}[-.]?\d{3}[-.]?\d{4}\b", "[PHONE]", text)

        # Replace common PII references
        for indicator in PIIDetector.PII_INDICATORS:
            # Replace specific mentions
            text = re.sub(
                rf"\b{indicator}\s*[:=]\s*\S+",
                f"[{indicator.upper()}_REDACTED]",
                text,
                flags=re.IGNORECASE,
            )

        return text


class KnowledgeLearningSystem:
    """
    Comprehensive knowledge learning system.

    Learns from user interactions while maintaining privacy and
    avoiding duplication.
    """

    def __init__(
        self,
        rag_system: Optional[DualRAGSystem] = None,
        enable_learning: bool = True,
    ):
        """
        Initialize knowledge learning system.

        Args:
            rag_system: Dual RAG system instance
            enable_learning: Whether learning is enabled
        """
        self.rag_system = rag_system or DualRAGSystem()
        self.enable_learning = enable_learning and config.ENABLE_KNOWLEDGE_LEARNING
        self.deduplicator = ConversationDeduplicator(
            similarity_threshold=config.DEDUPLICATION_THRESHOLD
        )
        self.quality_filter = QualityFilter()
        self.pii_detector = PIIDetector()

        self.stats = {
            "total_interactions": 0,
            "learned": 0,
            "duplicates_skipped": 0,
            "low_quality_skipped": 0,
            "pii_detected": 0,
        }

    def process_interaction(
        self,
        question: str,
        answer: str,
        user_id: Optional[str] = None,
        user_password: Optional[str] = None,
        metadata: Optional[Dict] = None,
    ) -> Dict:
        """
        Process a user interaction and learn from it.

        Args:
            question: User's question
            answer: System's answer
            user_id: Optional user identifier
            user_password: Optional user password for private storage
            metadata: Additional metadata

        Returns:
            Processing result with statistics
        """
        self.stats["total_interactions"] += 1

        if not self.enable_learning:
            return {"status": "learning_disabled", "stats": self.stats}

        # Create conversation object
        conversation = {"question": question, "answer": answer, "timestamp": datetime.now().isoformat()}

        if metadata:
            conversation.update(metadata)

        # Check quality
        if not self.quality_filter.is_high_quality(
            conversation, min_score=config.MIN_INTERACTION_QUALITY_SCORE
        ):
            self.stats["low_quality_skipped"] += 1
            return {"status": "low_quality", "stats": self.stats}

        # Check for duplicates
        content_text = f"Q: {question}\nA: {answer}"
        is_duplicate, _ = self.deduplicator.is_duplicate(content_text)
        if is_duplicate:
            self.stats["duplicates_skipped"] += 1
            return {"status": "duplicate", "stats": self.stats}

        # Check for PII
        has_pii, pii_types = self.pii_detector.contains_pii(content_text)

        # If has PII, store privately (if user authenticated)
        if has_pii:
            self.stats["pii_detected"] += 1

            if user_id and user_password:
                # Store in private vault
                doc_id = self.rag_system.add_private_data(
                    user_id=user_id,
                    password=user_password,
                    content=content_text,
                    metadata={
                        "type": "conversation",
                        "pii_types": pii_types,
                        **conversation,
                    },
                )
                self.stats["learned"] += 1
                return {
                    "status": "learned_private",
                    "doc_id": doc_id,
                    "pii_detected": pii_types,
                    "stats": self.stats,
                }
            else:
                # Cannot store PII without user authentication
                return {
                    "status": "pii_no_auth",
                    "pii_detected": pii_types,
                    "stats": self.stats,
                }

        # No PII - anonymize and store in public knowledge base
        anonymized_content = self.pii_detector.anonymize_text(content_text)

        doc_id = self.rag_system.add_public_knowledge(
            content=anonymized_content,
            metadata={"type": "conversation", "source": "user_interaction", **conversation},
        )

        if doc_id:
            self.stats["learned"] += 1
            return {"status": "learned_public", "doc_id": doc_id, "stats": self.stats}
        else:
            return {"status": "failed", "stats": self.stats}

    def extract_patterns(self, conversations: List[Dict]) -> List[Dict]:
        """
        Extract common patterns from conversations.

        Args:
            conversations: List of conversation dicts

        Returns:
            List of extracted patterns
        """
        patterns = []

        # Group by topic/theme
        topics = {}
        for conv in conversations:
            question = conv.get("question", "").lower()

            # Simple topic extraction (can be enhanced with NLP)
            if "skill" in question or "experience" in question:
                topic = "skills_and_experience"
            elif "goal" in question or "objective" in question:
                topic = "goals_and_objectives"
            elif "interest" in question or "passion" in question:
                topic = "interests"
            else:
                topic = "general"

            if topic not in topics:
                topics[topic] = []
            topics[topic].append(conv)

        # Extract patterns from each topic
        for topic, convs in topics.items():
            if len(convs) >= 3:  # Need minimum occurrences
                patterns.append(
                    {
                        "topic": topic,
                        "frequency": len(convs),
                        "examples": convs[:3],  # First 3 examples
                        "extracted_at": datetime.now().isoformat(),
                    }
                )

        return patterns

    def get_learning_insights(self, user_id: str, password: str) -> Dict:
        """
        Get learning insights for a user.

        Args:
            user_id: User identifier
            password: User password

        Returns:
            Insights dict with statistics and patterns
        """
        # Get user's conversations
        results = self.rag_system.query_private(user_id, password, "conversation", n_results=100)

        conversations = [r for r in results if r["metadata"].get("type") == "conversation"]

        # Extract patterns
        patterns = self.extract_patterns(conversations)

        return {
            "total_conversations": len(conversations),
            "patterns": patterns,
            "system_stats": self.stats,
            "generated_at": datetime.now().isoformat(),
        }

    def reset_stats(self):
        """Reset learning statistics."""
        self.stats = {
            "total_interactions": 0,
            "learned": 0,
            "duplicates_skipped": 0,
            "low_quality_skipped": 0,
            "pii_detected": 0,
        }


def create_learning_system(rag_system: Optional[DualRAGSystem] = None) -> KnowledgeLearningSystem:
    """
    Factory function to create a knowledge learning system.

    Args:
        rag_system: Optional RAG system instance

    Returns:
        Configured KnowledgeLearningSystem
    """
    return KnowledgeLearningSystem(rag_system=rag_system)
