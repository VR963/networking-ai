"""
Anti-Hallucination Control System.

This module implements comprehensive safeguards against AI hallucinations:
- Grounding engine: Verifies responses against RAG knowledge base
- Response validator: Detects hallucinations and confidence issues
- Fact checker agent: Validates other agents' outputs
- Source attribution: Requires evidence for claims
- Confidence scoring: Forces uncertainty expression when appropriate
- Behavioral constraints: Ensures realistic conversation patterns
"""

from typing import Dict, List, Optional, Tuple, Any
from datetime import datetime
from dataclasses import dataclass
from enum import Enum
import re
import json

from .rag_system import DualRAGSystem
from .semantic import SemanticMatcher


class ConfidenceLevel(Enum):
    """Confidence levels for agent responses."""
    VERIFIED = "verified"  # 0.9+: Backed by RAG or user data
    HIGH = "high"  # 0.7-0.9: Strong evidence
    MEDIUM = "medium"  # 0.5-0.7: Moderate evidence
    LOW = "low"  # 0.3-0.5: Weak evidence
    UNCERTAIN = "uncertain"  # <0.3: No evidence, guessing


@dataclass
class GroundingEvidence:
    """Evidence from RAG system to ground a claim."""
    claim: str
    source_documents: List[Dict]
    confidence: float
    similarity_scores: List[float]
    is_grounded: bool


@dataclass
class ValidationResult:
    """Result of response validation."""
    is_valid: bool
    confidence_level: ConfidenceLevel
    hallucination_flags: List[str]
    grounding_evidence: List[GroundingEvidence]
    corrections: List[str]
    risk_score: float  # 0-1, higher = more risky


class GroundingEngine:
    """
    Forces agents to ground responses in RAG knowledge base.

    Every claim must be verified against stored knowledge or explicitly
    marked as uncertain.
    """

    def __init__(
        self,
        rag_system: DualRAGSystem,
        matcher: Optional[SemanticMatcher] = None,
        min_similarity: float = 0.7,
    ):
        """
        Initialize grounding engine.

        Args:
            rag_system: RAG system for verification
            matcher: Semantic matcher for similarity
            min_similarity: Minimum similarity to consider grounded
        """
        self.rag_system = rag_system
        self.matcher = matcher or SemanticMatcher()
        self.min_similarity = min_similarity

    def extract_claims(self, text: str) -> List[str]:
        """
        Extract factual claims from text.

        Args:
            text: Text to analyze

        Returns:
            List of factual claims
        """
        claims = []

        # Split into sentences
        sentences = re.split(r'[.!?]+', text)

        for sentence in sentences:
            sentence = sentence.strip()
            if not sentence:
                continue

            # Filter out questions, greetings, etc.
            if sentence.endswith('?'):
                continue
            if len(sentence.split()) < 3:
                continue

            # Look for factual indicators
            factual_indicators = [
                'is', 'are', 'was', 'were', 'has', 'have', 'can', 'will',
                'should', 'must', 'requires', 'provides', 'offers'
            ]

            if any(indicator in sentence.lower() for indicator in factual_indicators):
                claims.append(sentence)

        return claims

    def verify_claim(
        self,
        claim: str,
        user_id: Optional[str] = None,
        password: Optional[str] = None,
    ) -> GroundingEvidence:
        """
        Verify a claim against RAG system.

        Args:
            claim: Claim to verify
            user_id: Optional user ID for private data
            password: Optional password for private data

        Returns:
            Grounding evidence
        """
        # Query public knowledge
        public_results = self.rag_system.query_public(claim, n_results=3)

        # Query private data if authenticated
        private_results = []
        if user_id and password:
            private_results = self.rag_system.query_private(
                user_id, password, claim, n_results=3
            )

        all_results = public_results + private_results

        if not all_results:
            return GroundingEvidence(
                claim=claim,
                source_documents=[],
                confidence=0.0,
                similarity_scores=[],
                is_grounded=False,
            )

        # Calculate similarities
        claim_embedding = self.matcher.generate_embedding(claim)
        similarities = []

        for result in all_results:
            doc_embedding = self.matcher.generate_embedding(result['content'])
            similarity = self.matcher.calculate_similarity(claim_embedding, doc_embedding)
            similarities.append(similarity)

        max_similarity = max(similarities) if similarities else 0.0
        is_grounded = max_similarity >= self.min_similarity

        return GroundingEvidence(
            claim=claim,
            source_documents=all_results,
            confidence=max_similarity,
            similarity_scores=similarities,
            is_grounded=is_grounded,
        )

    def ground_response(
        self,
        response: str,
        user_id: Optional[str] = None,
        password: Optional[str] = None,
    ) -> Dict:
        """
        Ground an entire response by verifying all claims.

        Args:
            response: Response to ground
            user_id: Optional user ID
            password: Optional password

        Returns:
            Grounding report
        """
        claims = self.extract_claims(response)
        evidences = []

        for claim in claims:
            evidence = self.verify_claim(claim, user_id, password)
            evidences.append(evidence)

        # Calculate overall grounding
        grounded_count = sum(1 for e in evidences if e.is_grounded)
        total_count = len(evidences) if evidences else 1
        grounding_percentage = grounded_count / total_count

        ungrounded_claims = [e.claim for e in evidences if not e.is_grounded]

        return {
            "response": response,
            "total_claims": len(claims),
            "grounded_claims": grounded_count,
            "ungrounded_claims": ungrounded_claims,
            "grounding_percentage": grounding_percentage,
            "evidences": evidences,
            "is_fully_grounded": grounding_percentage >= 0.8,
        }


class HallucinationDetector:
    """
    Detects hallucinations in agent responses.

    Checks for:
    - Unsupported factual claims
    - Exaggerations
    - Contradictions
    - Overly confident statements without evidence
    """

    # Patterns that indicate potential hallucination
    EXAGGERATION_PATTERNS = [
        r'\ball\b.*\balways\b',
        r'\bnever\b.*\bever\b',
        r'\beveryone\b',
        r'\bno one\b',
        r'\bcompletely\b.*\bimpossible\b',
        r'\b100%\b',
        r'\bguaranteed\b',
        r'\bcertainly\b.*\bwill\b',
        r'\bdefinitely\b.*\bwill\b',
    ]

    UNCERTAINTY_REQUIRED = [
        'predict', 'future', 'will happen', 'going to',
        'might', 'could', 'possibly', 'probably'
    ]

    @classmethod
    def detect_exaggerations(cls, text: str) -> List[str]:
        """Detect exaggerated claims."""
        flags = []

        for pattern in cls.EXAGGERATION_PATTERNS:
            if re.search(pattern, text, re.IGNORECASE):
                flags.append(f"Exaggeration pattern detected: {pattern}")

        return flags

    @classmethod
    def detect_missing_uncertainty(cls, text: str) -> List[str]:
        """Detect statements that should express uncertainty but don't."""
        flags = []

        for phrase in cls.UNCERTAINTY_REQUIRED:
            if phrase in text.lower():
                # Check if uncertainty markers are present
                uncertainty_markers = ['might', 'could', 'possibly', 'probably', 'may', 'uncertain', 'unclear']
                if not any(marker in text.lower() for marker in uncertainty_markers):
                    flags.append(f"Missing uncertainty for: {phrase}")

        return flags

    @classmethod
    def detect_contradictions(cls, text: str, context: List[str]) -> List[str]:
        """Detect contradictions with previous statements."""
        flags = []

        # Simple contradiction detection (can be enhanced with NLP)
        text_lower = text.lower()

        for prev_statement in context:
            prev_lower = prev_statement.lower()

            # Check for direct contradictions
            if 'not' in text_lower and any(word in prev_lower for word in text_lower.split()):
                flags.append(f"Potential contradiction with: {prev_statement[:50]}")

        return flags

    @classmethod
    def calculate_confidence_score(cls, text: str, grounding_evidence: List[GroundingEvidence]) -> float:
        """
        Calculate confidence score based on evidence.

        Args:
            text: Response text
            grounding_evidence: Evidence from grounding engine

        Returns:
            Confidence score (0-1)
        """
        if not grounding_evidence:
            return 0.2  # Very low confidence without evidence

        # Average confidence from evidence
        avg_confidence = sum(e.confidence for e in grounding_evidence) / len(grounding_evidence)

        # Penalize exaggerations
        exaggerations = cls.detect_exaggerations(text)
        exaggeration_penalty = len(exaggerations) * 0.1

        # Penalize missing uncertainty
        missing_uncertainty = cls.detect_missing_uncertainty(text)
        uncertainty_penalty = len(missing_uncertainty) * 0.1

        final_confidence = max(0.0, avg_confidence - exaggeration_penalty - uncertainty_penalty)

        return min(1.0, final_confidence)


class ResponseValidator:
    """
    Validates agent responses for hallucinations, grounding, and realism.

    Acts as a gatekeeper before responses are sent to users.
    """

    def __init__(
        self,
        grounding_engine: GroundingEngine,
        min_confidence: float = 0.5,
    ):
        """
        Initialize validator.

        Args:
            grounding_engine: Engine for grounding verification
            min_confidence: Minimum confidence threshold
        """
        self.grounding_engine = grounding_engine
        self.min_confidence = min_confidence
        self.conversation_history: List[str] = []

    def validate_response(
        self,
        response: str,
        user_id: Optional[str] = None,
        password: Optional[str] = None,
    ) -> ValidationResult:
        """
        Validate a response for hallucinations and grounding.

        Args:
            response: Response to validate
            user_id: Optional user ID
            password: Optional password

        Returns:
            Validation result
        """
        # Ground the response
        grounding_report = self.grounding_engine.ground_response(
            response, user_id, password
        )

        # Detect hallucinations
        hallucination_flags = []

        # Check exaggerations
        exaggerations = HallucinationDetector.detect_exaggerations(response)
        hallucination_flags.extend(exaggerations)

        # Check missing uncertainty
        missing_uncertainty = HallucinationDetector.detect_missing_uncertainty(response)
        hallucination_flags.extend(missing_uncertainty)

        # Check contradictions
        contradictions = HallucinationDetector.detect_contradictions(
            response, self.conversation_history[-5:]  # Last 5 statements
        )
        hallucination_flags.extend(contradictions)

        # Calculate confidence
        confidence_score = HallucinationDetector.calculate_confidence_score(
            response, grounding_report['evidences']
        )

        # Determine confidence level
        if confidence_score >= 0.9:
            confidence_level = ConfidenceLevel.VERIFIED
        elif confidence_score >= 0.7:
            confidence_level = ConfidenceLevel.HIGH
        elif confidence_score >= 0.5:
            confidence_level = ConfidenceLevel.MEDIUM
        elif confidence_score >= 0.3:
            confidence_level = ConfidenceLevel.LOW
        else:
            confidence_level = ConfidenceLevel.UNCERTAIN

        # Calculate risk score
        risk_score = 1.0 - confidence_score
        risk_score += len(hallucination_flags) * 0.1
        risk_score = min(1.0, risk_score)

        # Generate corrections
        corrections = []
        if grounding_report['ungrounded_claims']:
            corrections.append("Add uncertainty markers for ungrounded claims")
        if exaggerations:
            corrections.append("Remove exaggerated language")
        if missing_uncertainty:
            corrections.append("Express appropriate uncertainty")

        # Determine if valid
        is_valid = (
            confidence_score >= self.min_confidence and
            risk_score < 0.7 and
            grounding_report['grounding_percentage'] >= 0.5
        )

        # Update history
        self.conversation_history.append(response)

        return ValidationResult(
            is_valid=is_valid,
            confidence_level=confidence_level,
            hallucination_flags=hallucination_flags,
            grounding_evidence=grounding_report['evidences'],
            corrections=corrections,
            risk_score=risk_score,
        )

    def add_uncertainty_markers(self, response: str, ungrounded_claims: List[str]) -> str:
        """
        Automatically add uncertainty markers to ungrounded claims.

        Args:
            response: Original response
            ungrounded_claims: Claims that lack evidence

        Returns:
            Modified response with uncertainty markers
        """
        modified = response

        uncertainty_prefixes = [
            "Based on available information, ",
            "It appears that ",
            "Generally speaking, ",
            "In most cases, ",
        ]

        for claim in ungrounded_claims:
            if claim in modified:
                # Add uncertainty marker
                prefix = uncertainty_prefixes[0]
                modified = modified.replace(claim, f"{prefix}{claim.lower()}")

        return modified

    def clear_history(self):
        """Clear conversation history."""
        self.conversation_history.clear()


def create_anti_hallucination_system(
    rag_system: DualRAGSystem,
    min_confidence: float = 0.5,
) -> ResponseValidator:
    """
    Factory function to create anti-hallucination system.

    Args:
        rag_system: RAG system for grounding
        min_confidence: Minimum confidence threshold

    Returns:
        Configured ResponseValidator
    """
    grounding_engine = GroundingEngine(rag_system)
    return ResponseValidator(grounding_engine, min_confidence=min_confidence)
