"""
Agent Readiness Detector Service.

Determines when an agent has learned enough during onboarding to represent their user.
Agents must achieve >= 80% readiness score before activation.
"""

from typing import Dict, List, Optional, Any
from datetime import datetime
from dataclasses import dataclass


@dataclass
class ReadinessBreakdown:
    """Breakdown of readiness score components."""
    phase_completion: float
    insight_quality: float
    topic_coverage: float
    user_validation: float
    total_score: float
    is_ready: bool
    missing_requirements: List[str]


class InterviewPhase:
    """Definition of an interview phase."""

    # Talent Agent Interview Phases
    TALENT_PHASES = {
        "1_technical_depth": {
            "goal": "Understand technical expertise beyond CV",
            "required_insights": [
                "technical_depth_level",
                "preferred_technologies",
                "problem_solving_approach"
            ],
            "min_confidence": 0.7,
            "weight": 15
        },
        "2_motivations": {
            "goal": "Understand why they're looking and what they want",
            "required_insights": [
                "primary_motivation",
                "ideal_role_characteristics",
                "deal_breakers"
            ],
            "min_confidence": 0.7,
            "weight": 15
        },
        "3_work_preferences": {
            "goal": "Understand work style and environment preferences",
            "required_insights": [
                "work_location_preference",
                "team_size_preference",
                "company_stage_preference"
            ],
            "min_confidence": 0.7,
            "weight": 10
        },
        "4_soft_skills": {
            "goal": "Understand interpersonal and leadership skills",
            "required_insights": [
                "leadership_style",
                "collaboration_ability",
                "communication_style"
            ],
            "min_confidence": 0.6,
            "weight": 10
        },
        "5_compensation": {
            "goal": "Understand compensation expectations",
            "required_insights": [
                "current_compensation",
                "target_compensation",
                "benefits_priorities"
            ],
            "min_confidence": 0.8,
            "weight": 5
        },
        "6_timeline_logistics": {
            "goal": "Understand availability and constraints",
            "required_insights": [
                "availability_timeline",
                "constraints",
                "urgency_level"
            ],
            "min_confidence": 0.7,
            "weight": 5
        }
    }

    # Hiring Manager Interview Phases
    HIRING_MANAGER_PHASES = {
        "1_role_requirements": {
            "goal": "Understand the role being hired for",
            "required_insights": [
                "role_title",
                "technical_requirements",
                "experience_level_required"
            ],
            "min_confidence": 0.8,
            "weight": 15
        },
        "2_team_context": {
            "goal": "Understand the team and company",
            "required_insights": [
                "team_size",
                "team_culture",
                "company_stage"
            ],
            "min_confidence": 0.7,
            "weight": 15
        },
        "3_hiring_style": {
            "goal": "Understand hiring preferences",
            "required_insights": [
                "interview_process",
                "evaluation_criteria",
                "ideal_candidate_profile"
            ],
            "min_confidence": 0.7,
            "weight": 15
        },
        "4_deal_breakers": {
            "goal": "Understand red flags and must-haves",
            "required_insights": [
                "red_flags",
                "must_haves",
                "non_negotiables"
            ],
            "min_confidence": 0.8,
            "weight": 10
        },
        "5_compensation_logistics": {
            "goal": "Understand budget and timeline",
            "required_insights": [
                "compensation_range",
                "benefits_offered",
                "hiring_timeline"
            ],
            "min_confidence": 0.7,
            "weight": 5
        }
    }


class AgentReadinessDetector:
    """
    Detects when an agent is ready to represent their user.

    Readiness Score Breakdown:
    - Phase Completion: 60 points (weighted by phase importance)
    - Insight Quality: 20 points (high-confidence insights)
    - Topic Coverage: 10 points (critical topics covered)
    - User Validation: 10 points (user confirms understanding)

    TOTAL: >= 80 points = READY
    """

    def __init__(self, agent_type: str = "talent"):
        """
        Initialize readiness detector.

        Args:
            agent_type: "talent" or "hiring_manager"
        """
        self.agent_type = agent_type
        self.phases = (
            InterviewPhase.TALENT_PHASES if agent_type == "talent"
            else InterviewPhase.HIRING_MANAGER_PHASES
        )
        self.required_score = 80.0

    def calculate_readiness(
        self,
        knowledge_extracted: Dict[str, Any],
        user_validated: bool = False,
        conversation_turns: int = 0
    ) -> ReadinessBreakdown:
        """
        Calculate agent readiness score.

        Args:
            knowledge_extracted: Dict of extracted insights with evidence
            user_validated: Whether user confirmed agent's understanding
            conversation_turns: Number of conversation turns completed

        Returns:
            ReadinessBreakdown with score and missing requirements
        """
        # 1. Phase Completion (60 points total, weighted)
        phase_score = self._calculate_phase_completion(knowledge_extracted)

        # 2. Insight Quality (20 points)
        insight_quality_score = self._calculate_insight_quality(knowledge_extracted)

        # 3. Topic Coverage (10 points)
        coverage_score = self._calculate_topic_coverage(knowledge_extracted)

        # 4. User Validation (10 points)
        validation_score = 10.0 if user_validated else 0.0

        # Total score
        total_score = (
            phase_score +
            insight_quality_score +
            coverage_score +
            validation_score
        )

        # Determine if ready
        is_ready = total_score >= self.required_score

        # Get missing requirements
        missing_requirements = self._get_missing_requirements(
            knowledge_extracted,
            user_validated,
            conversation_turns
        )

        return ReadinessBreakdown(
            phase_completion=phase_score,
            insight_quality=insight_quality_score,
            topic_coverage=coverage_score,
            user_validation=validation_score,
            total_score=total_score,
            is_ready=is_ready,
            missing_requirements=missing_requirements
        )

    def _calculate_phase_completion(
        self,
        knowledge_extracted: Dict[str, Any]
    ) -> float:
        """
        Calculate phase completion score (0-60 points).

        Each phase has a weight based on importance.
        """
        total_weight = sum(phase["weight"] for phase in self.phases.values())
        earned_points = 0.0

        for phase_id, phase_def in self.phases.items():
            if self._is_phase_complete(phase_def, knowledge_extracted):
                earned_points += phase_def["weight"]

        # Normalize to 60 points
        return (earned_points / total_weight) * 60.0

    def _is_phase_complete(
        self,
        phase_def: Dict,
        knowledge_extracted: Dict[str, Any]
    ) -> bool:
        """
        Check if a phase is complete.

        Phase is complete if:
        - All required insights are present
        - Each insight has sufficient confidence
        - Each insight has supporting evidence
        """
        required_insights = phase_def["required_insights"]
        min_confidence = phase_def["min_confidence"]

        for insight_key in required_insights:
            # Check if insight exists
            if insight_key not in knowledge_extracted:
                return False

            insight = knowledge_extracted[insight_key]

            # Check confidence
            if insight.get("confidence", 0.0) < min_confidence:
                return False

            # Check evidence exists
            if not insight.get("evidence"):
                return False

            # Check value is not empty
            if not insight.get("value"):
                return False

        return True

    def _calculate_insight_quality(
        self,
        knowledge_extracted: Dict[str, Any]
    ) -> float:
        """
        Calculate insight quality score (0-20 points).

        Based on number of high-confidence insights.
        Need 15+ high-confidence insights (>0.8) for full score.
        """
        high_confidence_insights = 0

        for insight in knowledge_extracted.values():
            if isinstance(insight, dict) and insight.get("confidence", 0.0) > 0.8:
                high_confidence_insights += 1

        # 15+ insights = 20 points
        target_insights = 15
        return min((high_confidence_insights / target_insights) * 20.0, 20.0)

    def _calculate_topic_coverage(
        self,
        knowledge_extracted: Dict[str, Any]
    ) -> float:
        """
        Calculate topic coverage score (0-10 points).

        Check if all critical topics are covered.
        """
        if self.agent_type == "talent":
            critical_topics = [
                "technical_depth_level",
                "primary_motivation",
                "work_location_preference",
                "target_compensation"
            ]
        else:  # hiring_manager
            critical_topics = [
                "role_title",
                "technical_requirements",
                "ideal_candidate_profile",
                "compensation_range"
            ]

        covered_count = 0
        for topic in critical_topics:
            if topic in knowledge_extracted:
                insight = knowledge_extracted[topic]
                if isinstance(insight, dict) and insight.get("confidence", 0.0) > 0.6:
                    covered_count += 1

        return (covered_count / len(critical_topics)) * 10.0

    def _get_missing_requirements(
        self,
        knowledge_extracted: Dict[str, Any],
        user_validated: bool,
        conversation_turns: int
    ) -> List[str]:
        """
        Get list of missing requirements preventing readiness.
        """
        missing = []

        # Check each phase
        for phase_id, phase_def in self.phases.items():
            if not self._is_phase_complete(phase_def, knowledge_extracted):
                missing.append(f"Phase '{phase_id}': {phase_def['goal']}")

        # Check user validation
        if not user_validated:
            missing.append("User validation: User must confirm agent's understanding")

        # Check minimum conversation turns
        min_turns = 10 if self.agent_type == "talent" else 8
        if conversation_turns < min_turns:
            missing.append(
                f"Conversation depth: Need at least {min_turns} turns "
                f"(current: {conversation_turns})"
            )

        # Check critical insights
        if self.agent_type == "talent":
            critical = ["technical_depth_level", "primary_motivation", "target_compensation"]
        else:
            critical = ["role_title", "technical_requirements", "compensation_range"]

        for insight_key in critical:
            if insight_key not in knowledge_extracted:
                missing.append(f"Critical insight missing: {insight_key}")
            elif knowledge_extracted[insight_key].get("confidence", 0.0) < 0.7:
                missing.append(
                    f"Low confidence on critical insight: {insight_key} "
                    f"(confidence: {knowledge_extracted[insight_key].get('confidence', 0.0):.2f})"
                )

        return missing if missing else ["All requirements met"]

    def get_next_phase(
        self,
        knowledge_extracted: Dict[str, Any]
    ) -> Optional[Dict[str, Any]]:
        """
        Determine which phase to conduct next.

        Returns:
            Phase definition for next incomplete phase, or None if all complete
        """
        for phase_id, phase_def in self.phases.items():
            if not self._is_phase_complete(phase_def, knowledge_extracted):
                return {
                    "phase_id": phase_id,
                    "phase_def": phase_def
                }

        return None

    def get_missing_insights(
        self,
        phase_id: str,
        knowledge_extracted: Dict[str, Any]
    ) -> List[str]:
        """
        Get list of missing insights for a specific phase.

        Args:
            phase_id: Phase identifier
            knowledge_extracted: Current extracted knowledge

        Returns:
            List of missing insight keys
        """
        if phase_id not in self.phases:
            return []

        phase_def = self.phases[phase_id]
        required_insights = phase_def["required_insights"]
        min_confidence = phase_def["min_confidence"]

        missing = []
        for insight_key in required_insights:
            if insight_key not in knowledge_extracted:
                missing.append(insight_key)
            elif knowledge_extracted[insight_key].get("confidence", 0.0) < min_confidence:
                missing.append(insight_key)

        return missing


def format_readiness_report(readiness: ReadinessBreakdown) -> str:
    """
    Format readiness breakdown as human-readable report.

    Args:
        readiness: ReadinessBreakdown object

    Returns:
        Formatted string report
    """
    status = "✅ READY" if readiness.is_ready else "❌ NOT READY"

    report = f"""
Agent Readiness Report
{'=' * 60}

Status: {status}
Total Score: {readiness.total_score:.1f}/100 (need >= 80)

Score Breakdown:
- Phase Completion:    {readiness.phase_completion:.1f}/60 points
- Insight Quality:     {readiness.insight_quality:.1f}/20 points
- Topic Coverage:      {readiness.topic_coverage:.1f}/10 points
- User Validation:     {readiness.user_validation:.1f}/10 points

Missing Requirements:
"""

    for requirement in readiness.missing_requirements:
        report += f"  • {requirement}\n"

    return report
