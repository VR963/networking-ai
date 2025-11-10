"""
Shared Learning Engine for Real-Time Cross-Conversation Learning.

As agent conducts conversations, extracts insights and patterns.
Uses these to optimize questions and strategy for remaining conversations.

Key Innovation: Conversation #20 is smarter than conversation #1.
"""

from typing import Dict, List, Optional, Any, Set
from dataclasses import dataclass, field
from datetime import datetime
from collections import defaultdict, Counter
import re


@dataclass
class ConversationInsight:
    """Insight extracted from a single conversation."""
    conversation_id: str
    turn_number: int
    insight_type: str  # priority, disqualifier, common_question, differentiator
    topic: str
    value: Any
    confidence: float
    evidence: str
    timestamp: datetime = field(default_factory=datetime.now)


@dataclass
class DetectedPattern:
    """Pattern detected across multiple conversations."""
    pattern_type: str  # common_motivation, frequent_question, disqualifying_factor
    topic: str
    frequency: int  # How many conversations showed this
    total_conversations: int  # Total conversations analyzed
    examples: List[str] = field(default_factory=list)
    confidence: float = 0.0  # frequency / total_conversations


class PatternDetector:
    """Detects patterns across multiple conversations."""

    def __init__(self, min_frequency: int = 3):
        """
        Initialize pattern detector.

        Args:
            min_frequency: Minimum occurrences to consider a pattern
        """
        self.min_frequency = min_frequency
        self.topic_counter = Counter()
        self.question_counter = Counter()
        self.disqualifier_counter = Counter()
        self.motivation_counter = Counter()

    def analyze_insights(
        self,
        insights: List[ConversationInsight]
    ) -> List[DetectedPattern]:
        """
        Analyze insights to detect patterns.

        Args:
            insights: List of insights from multiple conversations

        Returns:
            List of detected patterns
        """
        patterns = []

        # Count topics
        topic_conversations = defaultdict(set)
        for insight in insights:
            topic_conversations[insight.topic].add(insight.conversation_id)

        total_conversations = len(set(i.conversation_id for i in insights))

        # Detect common topics
        for topic, conv_ids in topic_conversations.items():
            frequency = len(conv_ids)
            if frequency >= self.min_frequency:
                patterns.append(DetectedPattern(
                    pattern_type="common_topic",
                    topic=topic,
                    frequency=frequency,
                    total_conversations=total_conversations,
                    examples=[
                        i.evidence for i in insights
                        if i.topic == topic
                    ][:3],  # First 3 examples
                    confidence=frequency / total_conversations
                ))

        # Detect common questions (topics candidates ask about)
        question_insights = [i for i in insights if i.insight_type == "common_question"]
        question_topics = defaultdict(int)
        for insight in question_insights:
            question_topics[insight.topic] += 1

        for topic, count in question_topics.items():
            if count >= self.min_frequency:
                patterns.append(DetectedPattern(
                    pattern_type="common_question",
                    topic=topic,
                    frequency=count,
                    total_conversations=total_conversations,
                    confidence=count / total_conversations
                ))

        # Detect disqualifying factors
        disqualifier_insights = [i for i in insights if i.insight_type == "disqualifier"]
        disqualifier_topics = defaultdict(int)
        for insight in disqualifier_insights:
            disqualifier_topics[insight.topic] += 1

        for topic, count in disqualifier_topics.items():
            if count >= self.min_frequency:
                patterns.append(DetectedPattern(
                    pattern_type="disqualifying_factor",
                    topic=topic,
                    frequency=count,
                    total_conversations=total_conversations,
                    confidence=count / total_conversations
                ))

        # Detect differentiators (topics that help distinguish candidates)
        differentiator_insights = [i for i in insights if i.insight_type == "differentiator"]
        differentiator_topics = defaultdict(set)
        for insight in differentiator_insights:
            differentiator_topics[insight.topic].add(insight.value)

        for topic, values in differentiator_topics.items():
            # If topic has diverse values, it's a good differentiator
            if len(values) >= 3:  # At least 3 different responses
                patterns.append(DetectedPattern(
                    pattern_type="differentiator",
                    topic=topic,
                    frequency=len(values),
                    total_conversations=total_conversations,
                    examples=list(values)[:3],
                    confidence=0.8  # High confidence if diverse
                ))

        return patterns


class InsightExtractor:
    """Extracts insights from conversation responses."""

    def extract_insight(
        self,
        conversation_id: str,
        turn_number: int,
        question: str,
        response: str,
        question_purpose: str
    ) -> Optional[ConversationInsight]:
        """
        Extract insight from a conversation turn.

        Args:
            conversation_id: Conversation identifier
            turn_number: Turn number in conversation
            question: Question asked
            response: Response received
            question_purpose: Purpose of the question

        Returns:
            ConversationInsight if insight found, None otherwise
        """
        # Detect disqualifying responses
        disqualifying_keywords = [
            "no", "not possible", "can't", "won't", "never",
            "not interested", "don't have", "unable to"
        ]

        if any(keyword in response.lower() for keyword in disqualifying_keywords):
            return ConversationInsight(
                conversation_id=conversation_id,
                turn_number=turn_number,
                insight_type="disqualifier",
                topic=question_purpose,
                value="negative_response",
                confidence=0.8,
                evidence=response[:200]
            )

        # Detect priorities (what candidates care about)
        priority_keywords = {
            "work_life_balance": ["balance", "flexible", "hours", "remote", "wfh"],
            "growth": ["learn", "grow", "career", "advancement", "development"],
            "impact": ["impact", "meaningful", "change", "difference"],
            "compensation": ["salary", "pay", "compensation", "benefits"],
            "team": ["team", "collaborate", "culture", "people"],
            "technology": ["tech", "stack", "tools", "modern", "cutting-edge"]
        }

        for priority, keywords in priority_keywords.items():
            if any(keyword in response.lower() for keyword in keywords):
                return ConversationInsight(
                    conversation_id=conversation_id,
                    turn_number=turn_number,
                    insight_type="priority",
                    topic=priority,
                    value=True,
                    confidence=0.7,
                    evidence=response[:200]
                )

        # Detect common questions (if response asks a question)
        if "?" in response:
            # Extract question from response
            questions = re.findall(r'[^.!?]*\?', response)
            if questions:
                # Categorize question
                question_text = questions[0].strip()
                topic = self._categorize_question(question_text)

                return ConversationInsight(
                    conversation_id=conversation_id,
                    turn_number=turn_number,
                    insight_type="common_question",
                    topic=topic,
                    value=question_text,
                    confidence=0.9,
                    evidence=question_text
                )

        return None

    def _categorize_question(self, question: str) -> str:
        """Categorize a question by topic."""
        question_lower = question.lower()

        categories = {
            "remote_work": ["remote", "wfh", "work from home", "office", "location"],
            "team": ["team", "coworkers", "colleagues", "people", "culture"],
            "technology": ["tech", "stack", "tools", "languages", "framework"],
            "growth": ["learn", "grow", "training", "development", "career"],
            "compensation": ["salary", "pay", "compensation", "benefits", "equity"],
            "timeline": ["when", "start", "timeline", "process", "how long"],
            "responsibilities": ["do", "responsibilities", "day-to-day", "typical day"],
            "company": ["company", "mission", "vision", "stage", "funding"]
        }

        for category, keywords in categories.items():
            if any(keyword in question_lower for keyword in keywords):
                return category

        return "general"


class SharedLearningEngine:
    """
    Main learning engine that coordinates cross-conversation learning.

    Continuously learns from active conversations and optimizes strategy.
    """

    def __init__(self):
        """Initialize shared learning engine."""
        self.insights_buffer: List[ConversationInsight] = []
        self.detected_patterns: List[DetectedPattern] = []
        self.pattern_detector = PatternDetector()
        self.insight_extractor = InsightExtractor()
        self.conversations_analyzed: Set[str] = set()

    def add_conversation_turn(
        self,
        conversation_id: str,
        turn_number: int,
        question: str,
        response: str,
        question_purpose: str
    ):
        """
        Process a conversation turn and extract insights.

        Args:
            conversation_id: Conversation identifier
            turn_number: Turn number
            question: Question asked
            response: Response received
            question_purpose: Purpose of question
        """
        # Extract insight
        insight = self.insight_extractor.extract_insight(
            conversation_id,
            turn_number,
            question,
            response,
            question_purpose
        )

        if insight:
            self.insights_buffer.append(insight)
            self.conversations_analyzed.add(conversation_id)

        # Detect patterns periodically (every 5 conversations)
        if len(self.conversations_analyzed) % 5 == 0:
            self._update_patterns()

    def _update_patterns(self):
        """Detect and update patterns from insights buffer."""
        new_patterns = self.pattern_detector.analyze_insights(
            self.insights_buffer
        )

        # Update patterns list (replace or add)
        pattern_map = {
            (p.pattern_type, p.topic): p for p in self.detected_patterns
        }

        for new_pattern in new_patterns:
            key = (new_pattern.pattern_type, new_pattern.topic)
            pattern_map[key] = new_pattern

        self.detected_patterns = list(pattern_map.values())

    def get_learnings(self) -> Dict[str, Any]:
        """
        Get current learnings for use in question generation.

        Returns:
            Dict of learnings with patterns and recommendations
        """
        learnings = {
            "total_conversations": len(self.conversations_analyzed),
            "total_insights": len(self.insights_buffer),
            "patterns": {},
            "recommendations": []
        }

        # Organize patterns by type
        for pattern in self.detected_patterns:
            pattern_type = pattern.pattern_type
            if pattern_type not in learnings["patterns"]:
                learnings["patterns"][pattern_type] = []

            learnings["patterns"][pattern_type].append({
                "topic": pattern.topic,
                "frequency": pattern.frequency,
                "confidence": pattern.confidence,
                "examples": pattern.examples[:2]  # Top 2 examples
            })

        # Generate recommendations
        learnings["recommendations"] = self._generate_recommendations()

        return learnings

    def _generate_recommendations(self) -> List[str]:
        """Generate recommendations for improving conversations."""
        recommendations = []

        # Common questions - address proactively
        common_questions = [
            p for p in self.detected_patterns
            if p.pattern_type == "common_question" and p.confidence > 0.3
        ]

        if common_questions:
            topics = [p.topic for p in common_questions[:3]]
            recommendations.append(
                f"Address these topics proactively: {', '.join(topics)}"
            )

        # Disqualifying factors - ask early
        disqualifiers = [
            p for p in self.detected_patterns
            if p.pattern_type == "disqualifying_factor" and p.confidence > 0.2
        ]

        if disqualifiers:
            topics = [p.topic for p in disqualifiers[:2]]
            recommendations.append(
                f"Screen for these deal-breakers early: {', '.join(topics)}"
            )

        # Differentiators - explore deeply
        differentiators = [
            p for p in self.detected_patterns
            if p.pattern_type == "differentiator"
        ]

        if differentiators:
            topics = [p.topic for p in differentiators[:2]]
            recommendations.append(
                f"These topics help distinguish candidates: {', '.join(topics)}"
            )

        return recommendations

    def get_optimized_strategy(
        self,
        phase: str,
        conversations_completed: int
    ) -> Dict[str, Any]:
        """
        Get optimized conversation strategy based on learnings.

        Args:
            phase: Current phase (screening, deepdive, verification)
            conversations_completed: Number of conversations completed so far

        Returns:
            Optimized strategy dict
        """
        strategy = {
            "phase": phase,
            "priority_topics": [],
            "skip_topics": [],
            "early_screening_topics": [],
            "deep_dive_topics": []
        }

        # Priority topics (common questions - address upfront)
        common_questions = [
            p for p in self.detected_patterns
            if p.pattern_type == "common_question" and p.confidence > 0.3
        ]
        strategy["priority_topics"] = [p.topic for p in common_questions]

        # Early screening topics (disqualifiers)
        disqualifiers = [
            p for p in self.detected_patterns
            if p.pattern_type == "disqualifying_factor" and p.confidence > 0.2
        ]
        strategy["early_screening_topics"] = [p.topic for p in disqualifiers]

        # Deep dive topics (differentiators)
        differentiators = [
            p for p in self.detected_patterns
            if p.pattern_type == "differentiator"
        ]
        strategy["deep_dive_topics"] = [p.topic for p in differentiators]

        return strategy

    def reset(self):
        """Reset learning state (use between different batches)."""
        self.insights_buffer.clear()
        self.detected_patterns.clear()
        self.conversations_analyzed.clear()

    def get_stats(self) -> Dict[str, Any]:
        """Get statistics about learning progress."""
        return {
            "conversations_analyzed": len(self.conversations_analyzed),
            "insights_collected": len(self.insights_buffer),
            "patterns_detected": len(self.detected_patterns),
            "pattern_breakdown": Counter(
                p.pattern_type for p in self.detected_patterns
            )
        }
