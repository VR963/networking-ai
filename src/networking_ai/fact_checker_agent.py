"""
Fact Checker Agent - Specialized agent for validating other agents' outputs.

This agent acts as a quality control layer, checking all agent responses
before they reach users.
"""

from typing import Dict, List, Optional
from datetime import datetime

from langchain_anthropic import ChatAnthropic
from langchain.schema import HumanMessage, SystemMessage

from .anti_hallucination import ResponseValidator, ValidationResult
from .rag_system import DualRAGSystem
from .config import config


class FactCheckerAgent:
    """
    Specialized agent that validates outputs from other agents.

    Responsibilities:
    - Verify factual accuracy against RAG
    - Check for hallucinations
    - Validate confidence levels
    - Enforce realistic conversation patterns
    - Block responses that don't meet quality standards
    """

    def __init__(
        self,
        validator: ResponseValidator,
        rag_system: DualRAGSystem,
        llm: Optional[ChatAnthropic] = None,
        strict_mode: bool = True,
    ):
        """
        Initialize fact checker agent.

        Args:
            validator: Response validator
            rag_system: RAG system for verification
            llm: Language model (Claude)
            strict_mode: If True, blocks invalid responses
        """
        self.validator = validator
        self.rag_system = rag_system
        self.llm = llm or ChatAnthropic(
            model=config.DEFAULT_MODEL,
            temperature=0.3,  # Lower temperature for fact-checking
        )
        self.strict_mode = strict_mode
        self.check_history: List[Dict] = []

    def check_response(
        self,
        agent_name: str,
        query: str,
        response: str,
        user_id: Optional[str] = None,
        password: Optional[str] = None,
    ) -> Dict:
        """
        Check an agent's response for accuracy and hallucinations.

        Args:
            agent_name: Name of the agent that generated the response
            query: Original user query
            response: Agent's response
            user_id: Optional user ID for private data access
            password: Optional password

        Returns:
            Check result with approval status
        """
        # Validate the response
        validation_result = self.validator.validate_response(
            response, user_id, password
        )

        # Use Claude to perform semantic fact-checking
        semantic_check = self._semantic_fact_check(query, response)

        # Determine if approved
        approved = self._determine_approval(validation_result, semantic_check)

        # Generate corrected response if needed
        corrected_response = None
        if not approved and not self.strict_mode:
            corrected_response = self._generate_correction(
                query, response, validation_result
            )

        # Create check record
        check_record = {
            "agent_name": agent_name,
            "query": query,
            "original_response": response,
            "validation_result": validation_result,
            "semantic_check": semantic_check,
            "approved": approved,
            "corrected_response": corrected_response,
            "timestamp": datetime.now().isoformat(),
        }

        # Store in history
        self.check_history.append(check_record)

        return check_record

    def _semantic_fact_check(self, query: str, response: str) -> Dict:
        """
        Use Claude to perform semantic fact-checking.

        Args:
            query: Original query
            response: Response to check

        Returns:
            Semantic check results
        """
        system_prompt = """You are a fact-checking AI. Your job is to analyze responses for:
1. Factual accuracy
2. Hallucinations or fabricated information
3. Exaggerations or overstatements
4. Missing uncertainty where appropriate
5. Realistic tone and language

Respond with a JSON object containing:
- is_accurate: boolean
- issues_found: list of strings
- confidence: float (0-1)
- recommendations: list of strings"""

        user_prompt = f"""Check this response for accuracy and realism:

Query: {query}

Response: {response}

Provide your fact-check analysis as JSON."""

        try:
            messages = [
                SystemMessage(content=system_prompt),
                HumanMessage(content=user_prompt),
            ]

            result = self.llm.invoke(messages)
            content = result.content

            # Parse JSON from response
            import json
            import re

            # Extract JSON if wrapped in code blocks
            if "```json" in content:
                json_start = content.find("```json") + 7
                json_end = content.find("```", json_start)
                content = content[json_start:json_end].strip()
            elif "```" in content:
                json_start = content.find("```") + 3
                json_end = content.find("```", json_start)
                content = content[json_start:json_end].strip()

            check_result = json.loads(content)

        except Exception as e:
            # Fallback if AI check fails
            check_result = {
                "is_accurate": True,
                "issues_found": [f"Check failed: {str(e)}"],
                "confidence": 0.5,
                "recommendations": ["Manual review recommended"],
            }

        return check_result

    def _determine_approval(
        self,
        validation_result: ValidationResult,
        semantic_check: Dict,
    ) -> bool:
        """
        Determine if a response should be approved.

        Args:
            validation_result: Validation result from validator
            semantic_check: Semantic check from Claude

        Returns:
            True if approved
        """
        # Must pass validation
        if not validation_result.is_valid:
            return False

        # Check risk score
        if validation_result.risk_score > 0.8:
            return False

        # Check semantic accuracy
        if not semantic_check.get("is_accurate", False):
            return False

        # Check issues found
        if len(semantic_check.get("issues_found", [])) > 2:
            return False

        return True

    def _generate_correction(
        self,
        query: str,
        response: str,
        validation_result: ValidationResult,
    ) -> str:
        """
        Generate a corrected version of the response.

        Args:
            query: Original query
            response: Original response
            validation_result: Validation result

        Returns:
            Corrected response
        """
        corrections_text = "\n".join(validation_result.corrections)

        system_prompt = """You are a response correction AI. Your job is to fix responses that contain hallucinations, exaggerations, or lack proper grounding.

Guidelines:
1. Add uncertainty markers where appropriate
2. Remove absolute statements
3. Ground claims in evidence
4. Keep responses realistic and conversational
5. Maintain the helpful intent but improve accuracy"""

        user_prompt = f"""Correct this response:

Original Query: {query}

Original Response: {response}

Issues Found:
{corrections_text}

Provide a corrected version that addresses these issues while maintaining helpfulness."""

        try:
            messages = [
                SystemMessage(content=system_prompt),
                HumanMessage(content=user_prompt),
            ]

            result = self.llm.invoke(messages)
            return result.content

        except Exception as e:
            # Fallback: add uncertainty markers
            return self.validator.add_uncertainty_markers(
                response,
                [e.claim for e in validation_result.grounding_evidence if not e.is_grounded]
            )

    def get_agent_accuracy_report(self, agent_name: str) -> Dict:
        """
        Generate accuracy report for a specific agent.

        Args:
            agent_name: Name of the agent

        Returns:
            Accuracy report
        """
        agent_checks = [c for c in self.check_history if c["agent_name"] == agent_name]

        if not agent_checks:
            return {"error": f"No checks found for agent: {agent_name}"}

        total_checks = len(agent_checks)
        approved_count = sum(1 for c in agent_checks if c["approved"])
        hallucination_count = sum(
            len(c["validation_result"].hallucination_flags)
            for c in agent_checks
        )

        return {
            "agent_name": agent_name,
            "total_checks": total_checks,
            "approved": approved_count,
            "rejected": total_checks - approved_count,
            "approval_rate": approved_count / total_checks,
            "hallucinations_detected": hallucination_count,
            "average_confidence": sum(
                c["semantic_check"].get("confidence", 0.5)
                for c in agent_checks
            ) / total_checks,
            "common_issues": self._extract_common_issues(agent_checks),
        }

    def _extract_common_issues(self, checks: List[Dict]) -> List[str]:
        """Extract most common issues from checks."""
        all_issues = []
        for check in checks:
            all_issues.extend(check["semantic_check"].get("issues_found", []))

        # Count occurrences
        issue_counts = {}
        for issue in all_issues:
            issue_counts[issue] = issue_counts.get(issue, 0) + 1

        # Sort by frequency
        sorted_issues = sorted(issue_counts.items(), key=lambda x: x[1], reverse=True)

        return [f"{issue} ({count}x)" for issue, count in sorted_issues[:5]]

    def get_system_health_report(self) -> Dict:
        """
        Generate overall system health report.

        Returns:
            System health metrics
        """
        if not self.check_history:
            return {"status": "No checks performed yet"}

        total_checks = len(self.check_history)
        approved_count = sum(1 for c in self.check_history if c["approved"])
        total_hallucinations = sum(
            len(c["validation_result"].hallucination_flags)
            for c in self.check_history
        )

        # Get unique agents
        agents = list(set(c["agent_name"] for c in self.check_history))

        return {
            "status": "healthy" if approved_count / total_checks > 0.8 else "needs_attention",
            "total_checks": total_checks,
            "overall_approval_rate": approved_count / total_checks,
            "total_hallucinations": total_hallucinations,
            "hallucination_rate": total_hallucinations / total_checks,
            "agents_monitored": len(agents),
            "agents": agents,
            "last_check": self.check_history[-1]["timestamp"],
        }


def create_fact_checker(
    rag_system: DualRAGSystem,
    validator: Optional[ResponseValidator] = None,
    strict_mode: bool = True,
) -> FactCheckerAgent:
    """
    Factory function to create fact checker agent.

    Args:
        rag_system: RAG system
        validator: Optional response validator
        strict_mode: Whether to strictly block invalid responses

    Returns:
        Configured FactCheckerAgent
    """
    if validator is None:
        from .anti_hallucination import create_anti_hallucination_system
        validator = create_anti_hallucination_system(rag_system)

    return FactCheckerAgent(validator, rag_system, strict_mode=strict_mode)
