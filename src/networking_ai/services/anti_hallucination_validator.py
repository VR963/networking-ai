"""
Anti-Hallucination Validator for Agent Conversations.

Validates all agent messages against their Personal RAG to prevent hallucinations.
Agents can ONLY make claims that are supported by evidence in their RAG.
"""

from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass
import re
from langchain_anthropic import ChatAnthropic

from ..config import config


@dataclass
class Claim:
    """A factual claim extracted from agent message."""
    text: str
    category: str  # technical, preference, compensation, timeline, etc.
    confidence: float  # 0.0-1.0


@dataclass
class ValidationResult:
    """Result of validating a claim against RAG."""
    claim: Claim
    is_supported: bool
    evidence: Optional[str] = None
    similarity_score: Optional[float] = None
    error: Optional[str] = None


@dataclass
class MessageValidation:
    """Complete validation result for an agent message."""
    message: str
    is_valid: bool
    claims: List[Claim]
    validation_results: List[ValidationResult]
    hallucinations: List[ValidationResult]
    supported_claims: List[ValidationResult]
    corrected_message: Optional[str] = None


class ClaimExtractor:
    """Extracts factual claims from agent messages."""

    def __init__(self):
        """Initialize claim extractor with Claude."""
        self.llm = ChatAnthropic(
            model="claude-3-5-sonnet-20241022",
            api_key=config.anthropic_api_key,
            temperature=0.0  # Deterministic extraction
        )

    def extract_claims(self, message: str, agent_type: str) -> List[Claim]:
        """
        Extract all factual claims from agent message.

        Args:
            message: Agent message to analyze
            agent_type: "talent" or "company"

        Returns:
            List of extracted claims
        """
        if agent_type == "talent":
            extraction_prompt = self._build_talent_extraction_prompt(message)
        else:
            extraction_prompt = self._build_company_extraction_prompt(message)

        response = self.llm.invoke(extraction_prompt)

        # Parse response into claims
        claims = self._parse_claims_response(response.content)

        return claims

    def _build_talent_extraction_prompt(self, message: str) -> str:
        """Build extraction prompt for talent agent message."""
        return f"""
Extract ALL factual claims from this talent agent's message.

A claim is a statement about the user that could be true or false.

Categories:
- technical: Skills, experience, technologies
- preference: Work preferences, company preferences, team preferences
- compensation: Salary expectations, benefits priorities
- timeline: Availability, start date, constraints
- motivation: Career goals, reasons for job search
- soft_skills: Leadership, collaboration, communication style

Message:
\"\"\"{message}\"\"\"

For each claim, extract:
1. The exact claim text
2. The category
3. Confidence that this is a factual claim (0.0-1.0)

Format as JSON array:
[
  {{"text": "User has 5 years Python experience", "category": "technical", "confidence": 1.0}},
  {{"text": "User prefers remote work", "category": "preference", "confidence": 0.9}}
]

Return ONLY the JSON array, no other text.
"""

    def _build_company_extraction_prompt(self, message: str) -> str:
        """Build extraction prompt for company agent message."""
        return f"""
Extract ALL factual claims from this company agent's message.

A claim is a statement about the company/role that could be true or false.

Categories:
- technical: Required skills, technologies, technical environment
- role_details: Job title, responsibilities, seniority level
- team: Team size, structure, culture
- compensation: Salary range, benefits offered
- timeline: Hiring timeline, urgency
- company: Company stage, industry, size

Message:
\"\"\"{message}\"\"\"

For each claim, extract:
1. The exact claim text
2. The category
3. Confidence that this is a factual claim (0.0-1.0)

Format as JSON array:
[
  {{"text": "Role requires 5+ years Python experience", "category": "technical", "confidence": 1.0}},
  {{"text": "Company offers flexible hours", "category": "compensation", "confidence": 0.9}}
]

Return ONLY the JSON array, no other text.
"""

    def _parse_claims_response(self, response: str) -> List[Claim]:
        """Parse Claude's response into Claim objects."""
        import json

        try:
            # Extract JSON array from response
            # Handle cases where Claude adds explanation text
            json_match = re.search(r'\[.*\]', response, re.DOTALL)
            if json_match:
                json_str = json_match.group(0)
                claims_data = json.loads(json_str)
            else:
                claims_data = json.loads(response)

            claims = []
            for claim_dict in claims_data:
                claims.append(Claim(
                    text=claim_dict["text"],
                    category=claim_dict["category"],
                    confidence=claim_dict.get("confidence", 1.0)
                ))

            return claims

        except (json.JSONDecodeError, KeyError) as e:
            # Fallback: If parsing fails, extract claims with regex
            return self._fallback_claim_extraction(response)

    def _fallback_claim_extraction(self, text: str) -> List[Claim]:
        """Fallback claim extraction using simple heuristics."""
        claims = []

        # Look for sentences that make factual statements
        sentences = re.split(r'[.!?]', text)

        for sentence in sentences:
            sentence = sentence.strip()
            if not sentence:
                continue

            # Heuristic: Statements with "has", "is", "prefers", "requires", etc.
            if any(keyword in sentence.lower() for keyword in [
                "has", "is", "are", "prefers", "requires", "offers",
                "needs", "wants", "expects", "provides"
            ]):
                claims.append(Claim(
                    text=sentence,
                    category="unknown",
                    confidence=0.7
                ))

        return claims


class RAGValidator:
    """Validates claims against Personal RAG."""

    def __init__(self, chromadb_service):
        """
        Initialize RAG validator.

        Args:
            chromadb_service: ChromaDB service instance
        """
        self.chromadb_service = chromadb_service

    def validate_claim(
        self,
        claim: Claim,
        rag_collection_id: str
    ) -> ValidationResult:
        """
        Validate a single claim against Personal RAG.

        Args:
            claim: Claim to validate
            rag_collection_id: ChromaDB collection ID for this agent

        Returns:
            ValidationResult with support status and evidence
        """
        try:
            # Search RAG for supporting evidence
            results = self.chromadb_service.query_collection(
                collection_name=rag_collection_id,
                query_texts=[claim.text],
                n_results=3
            )

            if not results or not results.get('documents'):
                # No results found - claim not supported
                return ValidationResult(
                    claim=claim,
                    is_supported=False,
                    error="No evidence found in RAG"
                )

            # Get best match
            best_document = results['documents'][0][0]
            best_distance = results['distances'][0][0]

            # Convert distance to similarity (0.0 = identical, 1.0 = very different)
            similarity_score = 1.0 - best_distance

            # Threshold for support: similarity >= 0.7
            # This means the claim is strongly related to something in the RAG
            similarity_threshold = 0.7

            if similarity_score >= similarity_threshold:
                # Claim is supported
                return ValidationResult(
                    claim=claim,
                    is_supported=True,
                    evidence=best_document,
                    similarity_score=similarity_score
                )
            else:
                # Claim not sufficiently supported
                return ValidationResult(
                    claim=claim,
                    is_supported=False,
                    evidence=best_document,
                    similarity_score=similarity_score,
                    error=f"Insufficient similarity: {similarity_score:.2f} < {similarity_threshold}"
                )

        except Exception as e:
            return ValidationResult(
                claim=claim,
                is_supported=False,
                error=f"Validation error: {str(e)}"
            )


class AntiHallucinationValidator:
    """
    Main validator for agent-to-agent conversations.

    Ensures agents only make claims supported by their Personal RAG.
    """

    def __init__(self, chromadb_service):
        """
        Initialize anti-hallucination validator.

        Args:
            chromadb_service: ChromaDB service instance
        """
        self.claim_extractor = ClaimExtractor()
        self.rag_validator = RAGValidator(chromadb_service)
        self.llm = ChatAnthropic(
            model="claude-3-5-sonnet-20241022",
            api_key=config.anthropic_api_key,
            temperature=0.3
        )

    def validate_message(
        self,
        message: str,
        agent_type: str,
        rag_collection_id: str,
        auto_correct: bool = True
    ) -> MessageValidation:
        """
        Validate agent message before sending.

        Args:
            message: Agent's message to validate
            agent_type: "talent" or "company"
            rag_collection_id: Agent's Personal RAG collection ID
            auto_correct: If True, automatically generate corrected message

        Returns:
            MessageValidation with full validation results
        """
        # Step 1: Extract all claims from message
        claims = self.claim_extractor.extract_claims(message, agent_type)

        # Step 2: Validate each claim against RAG
        validation_results = []
        for claim in claims:
            result = self.rag_validator.validate_claim(claim, rag_collection_id)
            validation_results.append(result)

        # Step 3: Categorize results
        hallucinations = [r for r in validation_results if not r.is_supported]
        supported_claims = [r for r in validation_results if r.is_supported]

        # Step 4: Determine if message is valid
        is_valid = len(hallucinations) == 0

        # Step 5: Generate corrected message if needed
        corrected_message = None
        if not is_valid and auto_correct:
            corrected_message = self._generate_corrected_message(
                original_message=message,
                supported_claims=supported_claims,
                hallucinations=hallucinations,
                agent_type=agent_type
            )

        return MessageValidation(
            message=message,
            is_valid=is_valid,
            claims=claims,
            validation_results=validation_results,
            hallucinations=hallucinations,
            supported_claims=supported_claims,
            corrected_message=corrected_message
        )

    def _generate_corrected_message(
        self,
        original_message: str,
        supported_claims: List[ValidationResult],
        hallucinations: List[ValidationResult],
        agent_type: str
    ) -> str:
        """
        Generate corrected message with only supported claims.

        Args:
            original_message: Original message with hallucinations
            supported_claims: List of supported claims
            hallucinations: List of hallucinated claims
            agent_type: "talent" or "company"

        Returns:
            Corrected message with hallucinations removed
        """
        # Build correction prompt
        supported_claims_text = "\n".join([
            f"- {r.claim.text} (evidence: {r.evidence[:100]}...)"
            for r in supported_claims
        ])

        hallucinated_claims_text = "\n".join([
            f"- {r.claim.text}"
            for r in hallucinations
        ])

        correction_prompt = f"""
You are a {agent_type} agent in a professional networking platform.

Your original message contained some unsupported claims. Rewrite the message
to include ONLY the supported claims.

Original Message:
\"\"\"{original_message}\"\"\"

Supported Claims (you can say these):
{supported_claims_text if supported_claims else "None"}

Hallucinated Claims (REMOVE these):
{hallucinated_claims_text}

Rewrite the message to:
1. Keep the same conversational tone
2. Include only supported claims
3. Do NOT make up new information
4. Be honest if you don't have certain information

If all claims were hallucinated, say something like:
"I'd need to learn more about this before I can discuss it. Can you tell me more about...?"

Return ONLY the corrected message, no explanation.
"""

        response = self.llm.invoke(correction_prompt)
        return response.content.strip()

    def validate_and_correct(
        self,
        message: str,
        agent_type: str,
        rag_collection_id: str,
        max_retries: int = 2
    ) -> Tuple[str, MessageValidation]:
        """
        Validate message and auto-correct if needed.

        Will retry correction up to max_retries times.

        Args:
            message: Original message
            agent_type: "talent" or "company"
            rag_collection_id: Agent's RAG collection ID
            max_retries: Maximum correction attempts

        Returns:
            Tuple of (corrected_message, final_validation)
        """
        current_message = message
        attempts = 0

        while attempts <= max_retries:
            validation = self.validate_message(
                current_message,
                agent_type,
                rag_collection_id,
                auto_correct=True
            )

            if validation.is_valid:
                # Message is valid
                return current_message, validation

            if not validation.corrected_message:
                # Could not generate correction
                break

            # Try corrected message
            current_message = validation.corrected_message
            attempts += 1

        # Return final state
        return current_message, validation


def format_validation_report(validation: MessageValidation) -> str:
    """
    Format validation result as human-readable report.

    Args:
        validation: MessageValidation object

    Returns:
        Formatted string report
    """
    status = "✅ VALID" if validation.is_valid else "❌ CONTAINS HALLUCINATIONS"

    report = f"""
Message Validation Report
{'=' * 60}

Status: {status}

Original Message:
\"\"\"{validation.message}\"\"\"

Claims Analyzed: {len(validation.claims)}
- Supported: {len(validation.supported_claims)}
- Hallucinated: {len(validation.hallucinations)}

"""

    if validation.hallucinations:
        report += "Hallucinated Claims:\n"
        for i, result in enumerate(validation.hallucinations, 1):
            report += f"  {i}. {result.claim.text}\n"
            report += f"     Error: {result.error}\n"

    if validation.corrected_message:
        report += f"\nCorrected Message:\n\"\"\"{validation.corrected_message}\"\"\"\n"

    return report
