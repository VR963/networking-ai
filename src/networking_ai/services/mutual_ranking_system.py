"""
Mutual Ranking System for Agent-to-Agent Conversations.

Both agents score each other to find TOP 3 mutual matches.
Match quality = min(talent_score, company_score) - both must be interested.
"""

from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum


class MatchStrength(str, Enum):
    """Match strength classification."""
    EXCELLENT = "excellent"  # 90-100 mutual score
    STRONG = "strong"  # 80-89 mutual score
    GOOD = "good"  # 70-79 mutual score
    MODERATE = "moderate"  # 60-69 mutual score
    WEAK = "weak"  # < 60 mutual score


@dataclass
class ConversationScore:
    """Score for one conversation from one agent's perspective."""
    conversation_id: str
    agent_id: int
    agent_type: str  # "talent" or "company"

    # Score components (0-100 each)
    technical_fit: float = 0.0  # Technical skills alignment
    cultural_fit: float = 0.0  # Culture/values alignment
    motivation_alignment: float = 0.0  # Goals/motivations alignment
    communication_quality: float = 0.0  # Response quality
    interest_level: float = 0.0  # Expressed interest (1-10 scale × 10)

    # Calculated scores
    total_score: float = 0.0  # Weighted total (0-100)
    confidence: float = 0.0  # Confidence in score (0.0-1.0)

    # Metadata
    conversation_turns: int = 0
    deal_breakers_found: List[str] = field(default_factory=list)
    positive_signals: List[str] = field(default_factory=list)
    concerns: List[str] = field(default_factory=list)
    timestamp: datetime = field(default_factory=datetime.now)


@dataclass
class MutualMatch:
    """Mutual match between talent and company agents."""
    conversation_id: str
    talent_agent_id: int
    company_agent_id: int
    job_id: int

    # Individual scores
    talent_score: ConversationScore
    company_score: ConversationScore

    # Mutual scores
    mutual_score: float  # min(talent_score, company_score)
    match_strength: MatchStrength
    balance_score: float  # How balanced the interest is

    # Match details
    strengths: List[str] = field(default_factory=list)
    concerns: List[str] = field(default_factory=list)
    next_steps: str = ""
    synopsis: str = ""

    # Recommendation
    recommend_meeting: bool = False
    priority_rank: Optional[int] = None  # 1, 2, or 3 for top 3


class ConversationScorer:
    """Scores a conversation from one agent's perspective."""

    def __init__(self):
        """Initialize conversation scorer."""
        self.weights = {
            "technical_fit": 0.35,  # 35%
            "cultural_fit": 0.25,  # 25%
            "motivation_alignment": 0.20,  # 20%
            "communication_quality": 0.10,  # 10%
            "interest_level": 0.10  # 10%
        }

    def score_conversation(
        self,
        conversation_id: str,
        agent_id: int,
        agent_type: str,
        conversation_data: Dict[str, Any]
    ) -> ConversationScore:
        """
        Score a conversation from agent's perspective.

        Args:
            conversation_id: Conversation identifier
            agent_id: Scoring agent's ID
            agent_type: "talent" or "company"
            conversation_data: Dict with insights and responses

        Returns:
            ConversationScore
        """
        score = ConversationScore(
            conversation_id=conversation_id,
            agent_id=agent_id,
            agent_type=agent_type,
            conversation_turns=conversation_data.get("turns", 0)
        )

        # Score each component
        score.technical_fit = self._score_technical_fit(
            conversation_data.get("technical_insights", {}),
            agent_type
        )

        score.cultural_fit = self._score_cultural_fit(
            conversation_data.get("cultural_insights", {}),
            agent_type
        )

        score.motivation_alignment = self._score_motivation_alignment(
            conversation_data.get("motivation_insights", {}),
            agent_type
        )

        score.communication_quality = self._score_communication_quality(
            conversation_data.get("responses", []),
            agent_type
        )

        score.interest_level = self._score_interest_level(
            conversation_data.get("interest_indicators", {}),
            agent_type
        )

        # Calculate total weighted score
        score.total_score = (
            score.technical_fit * self.weights["technical_fit"] +
            score.cultural_fit * self.weights["cultural_fit"] +
            score.motivation_alignment * self.weights["motivation_alignment"] +
            score.communication_quality * self.weights["communication_quality"] +
            score.interest_level * self.weights["interest_level"]
        )

        # Calculate confidence based on data completeness
        score.confidence = self._calculate_confidence(conversation_data)

        # Extract deal breakers and positive signals
        score.deal_breakers_found = conversation_data.get("deal_breakers", [])
        score.positive_signals = conversation_data.get("positive_signals", [])
        score.concerns = conversation_data.get("concerns", [])

        return score

    def _score_technical_fit(
        self,
        technical_insights: Dict[str, Any],
        agent_type: str
    ) -> float:
        """
        Score technical fit (0-100).

        For company: Does candidate have required skills?
        For talent: Does job match desired technical environment?
        """
        if not technical_insights:
            return 50.0  # Neutral if no data

        # Skills match
        required_skills = technical_insights.get("required_skills", [])
        candidate_skills = technical_insights.get("candidate_skills", [])

        if required_skills and candidate_skills:
            matches = len(set(required_skills) & set(candidate_skills))
            match_rate = matches / len(required_skills) if required_skills else 0
            skill_score = match_rate * 100
        else:
            skill_score = 50.0

        # Experience level match
        experience_match = technical_insights.get("experience_level_match", 0.5)
        experience_score = experience_match * 100

        # Technical depth assessment
        technical_depth = technical_insights.get("technical_depth", "adequate")
        depth_scores = {
            "expert": 100,
            "strong": 85,
            "adequate": 70,
            "weak": 40,
            "insufficient": 20
        }
        depth_score = depth_scores.get(technical_depth, 50)

        # Weighted average
        return (skill_score * 0.5 + experience_score * 0.3 + depth_score * 0.2)

    def _score_cultural_fit(
        self,
        cultural_insights: Dict[str, Any],
        agent_type: str
    ) -> float:
        """
        Score cultural fit (0-100).

        Values alignment, work style, team preferences.
        """
        if not cultural_insights:
            return 50.0

        # Work style match
        work_style_match = cultural_insights.get("work_style_match", 0.5)
        work_style_score = work_style_match * 100

        # Values alignment
        values_alignment = cultural_insights.get("values_alignment", 0.5)
        values_score = values_alignment * 100

        # Team dynamics fit
        team_fit = cultural_insights.get("team_fit", 0.5)
        team_score = team_fit * 100

        # Company stage preference (for talent)
        if agent_type == "talent":
            stage_match = cultural_insights.get("company_stage_match", 0.5)
            stage_score = stage_match * 100
        else:
            stage_score = 70.0  # Default for company

        return (work_style_score * 0.3 + values_score * 0.3 +
                team_score * 0.2 + stage_score * 0.2)

    def _score_motivation_alignment(
        self,
        motivation_insights: Dict[str, Any],
        agent_type: str
    ) -> float:
        """
        Score motivation alignment (0-100).

        Are goals and motivations aligned?
        """
        if not motivation_insights:
            return 50.0

        # Primary motivation match
        primary_match = motivation_insights.get("primary_motivation_match", False)
        primary_score = 90.0 if primary_match else 40.0

        # Career goals alignment
        career_alignment = motivation_insights.get("career_goals_alignment", 0.5)
        career_score = career_alignment * 100

        # Timeline match
        timeline_match = motivation_insights.get("timeline_aligned", True)
        timeline_score = 80.0 if timeline_match else 30.0

        return (primary_score * 0.4 + career_score * 0.4 + timeline_score * 0.2)

    def _score_communication_quality(
        self,
        responses: List[str],
        agent_type: str
    ) -> float:
        """
        Score communication quality (0-100).

        Detailed, thoughtful responses vs brief/vague.
        """
        if not responses:
            return 50.0

        # Average response length
        avg_length = sum(len(r) for r in responses) / len(responses)

        # Length score (100-500 chars = good)
        if avg_length < 50:
            length_score = 30.0  # Too brief
        elif avg_length < 100:
            length_score = 60.0
        elif avg_length < 500:
            length_score = 90.0  # Good detail
        else:
            length_score = 70.0  # Maybe too verbose

        # Engagement score (asks questions, shows interest)
        engagement_count = sum(1 for r in responses if "?" in r)
        engagement_rate = engagement_count / len(responses)
        engagement_score = min(engagement_rate * 150, 100)  # Cap at 100

        return (length_score * 0.6 + engagement_score * 0.4)

    def _score_interest_level(
        self,
        interest_indicators: Dict[str, Any],
        agent_type: str
    ) -> float:
        """
        Score expressed interest level (0-100).

        Based on explicit interest statements (1-10 scale).
        """
        # Explicit interest rating (if asked)
        explicit_interest = interest_indicators.get("explicit_rating", 0)
        if explicit_interest > 0:
            return explicit_interest * 10  # Convert 1-10 to 0-100

        # Implicit interest indicators
        asked_questions = interest_indicators.get("asked_questions", False)
        quick_responses = interest_indicators.get("quick_responses", False)
        positive_language = interest_indicators.get("positive_language", False)

        implicit_score = 0
        if asked_questions:
            implicit_score += 35
        if quick_responses:
            implicit_score += 30
        if positive_language:
            implicit_score += 35

        return implicit_score if implicit_score > 0 else 50.0

    def _calculate_confidence(self, conversation_data: Dict[str, Any]) -> float:
        """
        Calculate confidence in score (0.0-1.0).

        Based on data completeness and conversation depth.
        """
        # Minimum turns for confidence
        turns = conversation_data.get("turns", 0)
        turns_confidence = min(turns / 7.0, 1.0)  # 7+ turns = full confidence

        # Data completeness
        required_data = [
            "technical_insights",
            "cultural_insights",
            "motivation_insights",
            "responses",
            "interest_indicators"
        ]
        present_data = sum(1 for key in required_data if conversation_data.get(key))
        data_confidence = present_data / len(required_data)

        return (turns_confidence * 0.6 + data_confidence * 0.4)


class MutualRankingSystem:
    """
    Main ranking system for finding top 3 mutual matches.

    Combines scores from both agents to find best mutual fits.
    """

    def __init__(self):
        """Initialize mutual ranking system."""
        self.scorer = ConversationScorer()

    def rank_conversations(
        self,
        conversations: List[Dict[str, Any]]
    ) -> List[MutualMatch]:
        """
        Rank all conversations and identify top 3 mutual matches.

        Args:
            conversations: List of conversation dicts with data from both agents

        Returns:
            Sorted list of MutualMatch objects
        """
        mutual_matches = []

        for conv_data in conversations:
            # Score from both perspectives
            talent_score = self.scorer.score_conversation(
                conversation_id=conv_data["conversation_id"],
                agent_id=conv_data["talent_agent_id"],
                agent_type="talent",
                conversation_data=conv_data.get("talent_perspective", {})
            )

            company_score = self.scorer.score_conversation(
                conversation_id=conv_data["conversation_id"],
                agent_id=conv_data["company_agent_id"],
                agent_type="company",
                conversation_data=conv_data.get("company_perspective", {})
            )

            # Create mutual match
            mutual_match = self._create_mutual_match(
                conv_data,
                talent_score,
                company_score
            )

            # Only include if meets minimum threshold
            if mutual_match.mutual_score >= 60.0:  # Minimum viable match
                mutual_matches.append(mutual_match)

        # Sort by mutual score (descending)
        mutual_matches.sort(key=lambda m: m.mutual_score, reverse=True)

        # Assign priority ranks to top 3
        for i, match in enumerate(mutual_matches[:3]):
            match.priority_rank = i + 1
            match.recommend_meeting = True

        return mutual_matches

    def _create_mutual_match(
        self,
        conv_data: Dict[str, Any],
        talent_score: ConversationScore,
        company_score: ConversationScore
    ) -> MutualMatch:
        """Create MutualMatch from individual scores."""
        # Mutual score = minimum of both scores (both must be interested)
        mutual_score = min(talent_score.total_score, company_score.total_score)

        # Balance score = how similar the interests are
        # Perfect balance = 100, one-sided = lower
        score_diff = abs(talent_score.total_score - company_score.total_score)
        balance_score = max(0, 100 - score_diff)

        # Add bonus for balanced interest
        if balance_score > 90:  # Very balanced
            mutual_score += 5

        # Classify match strength
        if mutual_score >= 90:
            strength = MatchStrength.EXCELLENT
        elif mutual_score >= 80:
            strength = MatchStrength.STRONG
        elif mutual_score >= 70:
            strength = MatchStrength.GOOD
        elif mutual_score >= 60:
            strength = MatchStrength.MODERATE
        else:
            strength = MatchStrength.WEAK

        # Identify strengths and concerns
        strengths = self._identify_strengths(talent_score, company_score)
        concerns = self._identify_concerns(talent_score, company_score)

        # Generate synopsis
        synopsis = self._generate_synopsis(
            conv_data,
            talent_score,
            company_score,
            mutual_score
        )

        # Determine next steps
        next_steps = self._determine_next_steps(mutual_score, concerns)

        return MutualMatch(
            conversation_id=conv_data["conversation_id"],
            talent_agent_id=conv_data["talent_agent_id"],
            company_agent_id=conv_data["company_agent_id"],
            job_id=conv_data["job_id"],
            talent_score=talent_score,
            company_score=company_score,
            mutual_score=mutual_score,
            match_strength=strength,
            balance_score=balance_score,
            strengths=strengths,
            concerns=concerns,
            next_steps=next_steps,
            synopsis=synopsis
        )

    def _identify_strengths(
        self,
        talent_score: ConversationScore,
        company_score: ConversationScore
    ) -> List[str]:
        """Identify match strengths."""
        strengths = []

        # Technical fit
        avg_technical = (talent_score.technical_fit + company_score.technical_fit) / 2
        if avg_technical >= 80:
            strengths.append("Strong technical alignment")

        # Cultural fit
        avg_cultural = (talent_score.cultural_fit + company_score.cultural_fit) / 2
        if avg_cultural >= 80:
            strengths.append("Excellent cultural fit")

        # Motivation alignment
        avg_motivation = (talent_score.motivation_alignment +
                         company_score.motivation_alignment) / 2
        if avg_motivation >= 80:
            strengths.append("Goals and motivations well-aligned")

        # Mutual high interest
        if talent_score.interest_level >= 80 and company_score.interest_level >= 80:
            strengths.append("Strong mutual interest")

        # Positive signals
        all_signals = talent_score.positive_signals + company_score.positive_signals
        if all_signals:
            strengths.append(f"Positive indicators: {', '.join(all_signals[:3])}")

        return strengths if strengths else ["Basic compatibility established"]

    def _identify_concerns(
        self,
        talent_score: ConversationScore,
        company_score: ConversationScore
    ) -> List[str]:
        """Identify potential concerns."""
        concerns = []

        # Deal breakers
        all_deal_breakers = (talent_score.deal_breakers_found +
                            company_score.deal_breakers_found)
        if all_deal_breakers:
            concerns.extend(all_deal_breakers)

        # Low component scores
        if talent_score.technical_fit < 60 or company_score.technical_fit < 60:
            concerns.append("Technical fit may need further discussion")

        if talent_score.cultural_fit < 60 or company_score.cultural_fit < 60:
            concerns.append("Cultural alignment uncertain")

        # Interest imbalance
        interest_diff = abs(talent_score.interest_level - company_score.interest_level)
        if interest_diff > 30:
            concerns.append("Interest levels may be imbalanced")

        # Explicit concerns
        all_concerns = talent_score.concerns + company_score.concerns
        concerns.extend(all_concerns[:2])  # Top 2 concerns

        return concerns

    def _generate_synopsis(
        self,
        conv_data: Dict[str, Any],
        talent_score: ConversationScore,
        company_score: ConversationScore,
        mutual_score: float
    ) -> str:
        """Generate human-readable synopsis of the match."""
        job_title = conv_data.get("job_title", "Position")
        company_name = conv_data.get("company_name", "Company")

        synopsis = f"{job_title} at {company_name}\n\n"
        synopsis += f"Match Quality: {mutual_score:.0f}/100 "

        if mutual_score >= 90:
            synopsis += "(Excellent)\n"
        elif mutual_score >= 80:
            synopsis += "(Strong)\n"
        elif mutual_score >= 70:
            synopsis += "(Good)\n"
        else:
            synopsis += "(Moderate)\n"

        synopsis += f"\nTechnical Fit: {(talent_score.technical_fit + company_score.technical_fit)/2:.0f}/100\n"
        synopsis += f"Cultural Fit: {(talent_score.cultural_fit + company_score.cultural_fit)/2:.0f}/100\n"
        synopsis += f"Mutual Interest: High\n" if min(talent_score.interest_level, company_score.interest_level) >= 70 else f"Mutual Interest: Moderate\n"

        return synopsis

    def _determine_next_steps(
        self,
        mutual_score: float,
        concerns: List[str]
    ) -> str:
        """Determine recommended next steps."""
        if mutual_score >= 85 and not concerns:
            return "Proceed to formal interview - excellent match"
        elif mutual_score >= 75:
            return "Proceed to interview - address any concerns during process"
        elif mutual_score >= 65:
            return "Consider for interview - good potential but needs discussion"
        else:
            return "Exploratory conversation - assess fit further before committing"

    def select_top_3(
        self,
        all_matches: List[MutualMatch]
    ) -> List[MutualMatch]:
        """
        Select top 3 matches for presentation to user.

        Args:
            all_matches: All mutual matches (already sorted)

        Returns:
            Top 3 matches
        """
        # Already sorted by mutual_score, just take top 3
        top_3 = all_matches[:3]

        # Ensure they have priority ranks
        for i, match in enumerate(top_3):
            match.priority_rank = i + 1
            match.recommend_meeting = True

        return top_3
