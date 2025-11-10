"""
Intelligent Question Generator for Agent-to-Agent Conversations.

Generates context-aware questions based on:
1. Conversation phase (screening, deep dive, verification)
2. Profile information
3. Real-time learnings from other conversations
"""

from typing import Dict, List, Optional, Any
from dataclasses import dataclass
from enum import Enum
from langchain_anthropic import ChatAnthropic

from ..config import config


class ConversationPhase(str, Enum):
    """Phases of agent-to-agent conversation."""
    SCREENING = "screening"  # Phase 1: Quick filtering (2-3 turns)
    DEEP_DIVE = "deepdive"   # Phase 2: Detailed exploration (5-7 turns)
    VERIFICATION = "verification"  # Phase 3: Final confirmation (3-4 turns)


@dataclass
class Question:
    """A generated question with metadata."""
    text: str
    purpose: str  # What this question aims to learn
    category: str  # technical, cultural, logistical, etc.
    priority: int  # 1-5, higher = more important
    expected_signals: List[str]  # Keywords/phrases indicating positive response
    disqualifying_responses: List[str]  # Responses that indicate mismatch
    follow_up_enabled: bool = False  # Whether to ask follow-up based on response


@dataclass
class QuestionContext:
    """Context for generating questions."""
    agent_type: str  # "talent" or "company"
    phase: ConversationPhase
    profile: Dict[str, Any]  # Candidate/job profile
    conversation_history: List[Dict[str, str]]  # Previous messages
    learnings: Dict[str, Any]  # Insights from other conversations
    insights_so_far: Dict[str, Any]  # What we've learned in this conversation


class IntelligentQuestionGenerator:
    """
    Generates smart, adaptive questions for agent-to-agent conversations.

    Questions adapt based on:
    - Conversation phase
    - Profile information
    - Real-time learnings from parallel conversations
    """

    def __init__(self):
        """Initialize question generator with Claude."""
        self.llm = ChatAnthropic(
            model="claude-3-5-sonnet-20241022",
            api_key=config.anthropic_api_key,
            temperature=0.7  # Creative but controlled
        )

    def generate_questions(
        self,
        context: QuestionContext,
        num_questions: int = 3
    ) -> List[Question]:
        """
        Generate questions for current conversation state.

        Args:
            context: Question context with phase, profile, learnings
            num_questions: Number of questions to generate

        Returns:
            List of generated questions
        """
        if context.phase == ConversationPhase.SCREENING:
            return self._generate_screening_questions(context, num_questions)
        elif context.phase == ConversationPhase.DEEP_DIVE:
            return self._generate_deepdive_questions(context, num_questions)
        elif context.phase == ConversationPhase.VERIFICATION:
            return self._generate_verification_questions(context, num_questions)
        else:
            raise ValueError(f"Unknown phase: {context.phase}")

    def _generate_screening_questions(
        self,
        context: QuestionContext,
        num_questions: int
    ) -> List[Question]:
        """
        Generate Phase 1 screening questions (quick filtering).

        Goal: Filter out obvious mismatches quickly
        Focus: Deal-breakers, must-haves, basic compatibility
        """
        prompt = self._build_screening_prompt(context)
        response = self.llm.invoke(prompt)

        # Parse response into questions
        questions = self._parse_questions_response(
            response.content,
            phase=ConversationPhase.SCREENING
        )

        return questions[:num_questions]

    def _build_screening_prompt(self, context: QuestionContext) -> str:
        """Build prompt for screening questions."""
        if context.agent_type == "company":
            # Company agent asking talent agent
            return f"""
You are a company AI agent evaluating a candidate for a position.

Role Information:
{self._format_profile(context.profile)}

Conversation Phase: SCREENING (quick filtering)
Goal: Identify deal-breakers and must-haves quickly

Previous conversation:
{self._format_conversation_history(context.conversation_history)}

Insights from other conversations:
{self._format_learnings(context.learnings)}

Generate 3 screening questions to quickly assess compatibility.
Focus on:
1. Critical technical requirements (must-haves)
2. Location/remote work compatibility
3. Timeline/availability
4. Compensation alignment (rough range)

For each question, provide:
- question_text: The actual question to ask
- purpose: What you're trying to learn
- category: technical/logistical/compensation/preferences
- priority: 1-5 (5 = most critical)
- expected_signals: Keywords indicating positive match
- disqualifying_responses: Responses indicating mismatch

Format as JSON array:
[
  {{
    "text": "I see you have Python experience. We need someone with 5+ years building distributed systems at scale. Have you designed systems handling 10K+ requests/second?",
    "purpose": "verify_technical_depth_requirement",
    "category": "technical",
    "priority": 5,
    "expected_signals": ["yes", "built systems", "experience with", "handled", "scaled"],
    "disqualifying_responses": ["no", "never", "not yet", "planning to learn"]
  }}
]

Return ONLY the JSON array.
"""
        else:
            # Talent agent asking company agent
            return f"""
You are a talent AI agent exploring a job opportunity for your user.

User Profile:
{self._format_profile(context.profile)}

Conversation Phase: SCREENING (quick filtering)
Goal: Identify deal-breakers quickly

Previous conversation:
{self._format_conversation_history(context.conversation_history)}

Insights from other conversations:
{self._format_learnings(context.learnings)}

Generate 3 screening questions to quickly assess if this job matches user's needs.
Focus on:
1. Work arrangement (remote/hybrid/office)
2. Technical environment and tools
3. Company stage and culture
4. Role expectations and responsibilities

For each question, provide:
- question_text: The actual question
- purpose: What you're trying to learn
- category: technical/cultural/logistical/compensation
- priority: 1-5 (5 = most critical)
- expected_signals: Keywords indicating good match
- disqualifying_responses: Responses indicating mismatch

Format as JSON array.
Return ONLY the JSON array.
"""

    def _generate_deepdive_questions(
        self,
        context: QuestionContext,
        num_questions: int
    ) -> List[Question]:
        """
        Generate Phase 2 deep dive questions (detailed exploration).

        Goal: Deeply understand compatibility beyond surface level
        Focus: Technical depth, culture fit, motivations, team dynamics
        """
        prompt = self._build_deepdive_prompt(context)
        response = self.llm.invoke(prompt)

        questions = self._parse_questions_response(
            response.content,
            phase=ConversationPhase.DEEP_DIVE
        )

        return questions[:num_questions]

    def _build_deepdive_prompt(self, context: QuestionContext) -> str:
        """Build prompt for deep dive questions."""
        if context.agent_type == "company":
            return f"""
You are a company AI agent conducting deep evaluation of a candidate.

Role Information:
{self._format_profile(context.profile)}

Conversation Phase: DEEP DIVE (detailed exploration)
Previous screening passed - now exploring depth.

What we've learned so far:
{self._format_insights(context.insights_so_far)}

Previous conversation:
{self._format_conversation_history(context.conversation_history)}

Patterns from similar conversations:
{self._format_learnings(context.learnings)}

Generate 3 deep dive questions to thoroughly assess:
1. Technical problem-solving ability (real examples)
2. Collaboration and team fit
3. Motivation and engagement (why this role/company?)
4. Leadership potential (if relevant)
5. Communication style

Questions should:
- Request specific examples/stories
- Probe deeper based on what we've learned
- Explore areas of uncertainty
- Validate assumptions from screening

Use patterns from learnings - if 8/10 candidates mentioned work-life balance,
ask about it proactively.

Format as JSON array with same structure.
Return ONLY the JSON array.
"""
        else:
            return f"""
You are a talent AI agent deeply exploring a job opportunity.

User Profile:
{self._format_profile(context.profile)}

Conversation Phase: DEEP DIVE
Screening passed - now exploring details.

What we've learned so far:
{self._format_insights(context.insights_so_far)}

Previous conversation:
{self._format_conversation_history(context.conversation_history)}

Patterns from similar conversations:
{self._format_learnings(context.learnings)}

Generate 3 deep dive questions to thoroughly understand:
1. Day-to-day responsibilities and expectations
2. Team dynamics and collaboration style
3. Growth opportunities and career path
4. Technical challenges and learning opportunities
5. Work-life balance and company culture

Questions should:
- Request specific examples
- Probe deeper on critical factors for user
- Explore potential concerns
- Validate job posting claims

Format as JSON array with same structure.
Return ONLY the JSON array.
"""

    def _generate_verification_questions(
        self,
        context: QuestionContext,
        num_questions: int
    ) -> List[Question]:
        """
        Generate Phase 3 verification questions (final confirmation).

        Goal: Confirm mutual interest and clarify logistics
        Focus: Interest level, next steps, remaining concerns
        """
        prompt = self._build_verification_prompt(context)
        response = self.llm.invoke(prompt)

        questions = self._parse_questions_response(
            response.content,
            phase=ConversationPhase.VERIFICATION
        )

        return questions[:num_questions]

    def _build_verification_prompt(self, context: QuestionContext) -> str:
        """Build prompt for verification questions."""
        if context.agent_type == "company":
            return f"""
You are a company AI agent in final verification phase.

Role Information:
{self._format_profile(context.profile)}

Conversation Phase: VERIFICATION (final confirmation)
Screening and deep dive complete - high potential match.

What we've learned:
{self._format_insights(context.insights_so_far)}

Generate 2-3 verification questions to:
1. Gauge candidate's interest level (1-10 scale)
2. Understand remaining questions/concerns
3. Clarify logistics (start date, constraints)
4. Confirm readiness to proceed to formal interview

Questions should be direct and action-oriented.

Format as JSON array.
Return ONLY the JSON array.
"""
        else:
            return f"""
You are a talent AI agent in final verification phase.

User Profile:
{self._format_profile(context.profile)}

Conversation Phase: VERIFICATION
Screening and deep dive complete - strong potential match.

What we've learned:
{self._format_insights(context.insights_so_far)}

Generate 2-3 verification questions to:
1. Gauge interest level from company
2. Ask any final clarifying questions
3. Understand next steps in process
4. Confirm timeline and expectations

Questions should be direct and forward-looking.

Format as JSON array.
Return ONLY the JSON array.
"""

    def _parse_questions_response(
        self,
        response: str,
        phase: ConversationPhase
    ) -> List[Question]:
        """Parse Claude's JSON response into Question objects."""
        import json
        import re

        try:
            # Extract JSON from response
            json_match = re.search(r'\[.*\]', response, re.DOTALL)
            if json_match:
                json_str = json_match.group(0)
                questions_data = json.loads(json_str)
            else:
                questions_data = json.loads(response)

            questions = []
            for q_dict in questions_data:
                questions.append(Question(
                    text=q_dict.get("text", ""),
                    purpose=q_dict.get("purpose", "unknown"),
                    category=q_dict.get("category", "general"),
                    priority=q_dict.get("priority", 3),
                    expected_signals=q_dict.get("expected_signals", []),
                    disqualifying_responses=q_dict.get("disqualifying_responses", []),
                    follow_up_enabled=q_dict.get("follow_up_enabled", phase == ConversationPhase.DEEP_DIVE)
                ))

            return questions

        except (json.JSONDecodeError, KeyError) as e:
            # Fallback: Return generic question
            return [Question(
                text="Tell me more about your experience and what you're looking for.",
                purpose="general_exploration",
                category="general",
                priority=3,
                expected_signals=[],
                disqualifying_responses=[],
                follow_up_enabled=False
            )]

    def _format_profile(self, profile: Dict[str, Any]) -> str:
        """Format profile for prompt."""
        if not profile:
            return "No profile information available"

        lines = []
        for key, value in profile.items():
            if value:
                lines.append(f"- {key}: {value}")

        return "\n".join(lines) if lines else "No profile information"

    def _format_conversation_history(
        self,
        history: List[Dict[str, str]]
    ) -> str:
        """Format conversation history for prompt."""
        if not history:
            return "No previous conversation"

        lines = []
        for msg in history[-5:]:  # Last 5 messages
            role = msg.get("role", "unknown")
            content = msg.get("content", "")
            lines.append(f"{role}: {content}")

        return "\n".join(lines)

    def _format_learnings(self, learnings: Dict[str, Any]) -> str:
        """Format learnings from other conversations."""
        if not learnings:
            return "No learnings available yet"

        lines = []
        for key, value in learnings.items():
            lines.append(f"- {key}: {value}")

        return "\n".join(lines) if lines else "No learnings yet"

    def _format_insights(self, insights: Dict[str, Any]) -> str:
        """Format insights learned so far in this conversation."""
        if not insights:
            return "No insights yet"

        lines = []
        for key, value in insights.items():
            if isinstance(value, dict):
                value = value.get("value", value)
            lines.append(f"- {key}: {value}")

        return "\n".join(lines)


class QuestionOptimizer:
    """
    Optimizes questions based on real-time learnings.

    As conversations progress, learns what questions work best
    and adjusts future questions accordingly.
    """

    def __init__(self):
        """Initialize optimizer."""
        self.patterns = {}
        self.effective_questions = []
        self.ineffective_questions = []

    def add_pattern(self, pattern_type: str, pattern_data: Any):
        """
        Add a detected pattern.

        Args:
            pattern_type: Type of pattern (common_question, disqualifier, etc.)
            pattern_data: Pattern details
        """
        if pattern_type not in self.patterns:
            self.patterns[pattern_type] = []

        self.patterns[pattern_type].append(pattern_data)

    def should_prioritize_topic(self, topic: str) -> bool:
        """
        Check if topic should be prioritized based on patterns.

        Args:
            topic: Topic to check (e.g., "remote_work", "work_life_balance")

        Returns:
            True if topic frequently comes up in conversations
        """
        common_topics = self.patterns.get("common_topics", [])
        return topic in common_topics

    def get_proactive_topics(self) -> List[str]:
        """
        Get topics that should be addressed proactively.

        Returns:
            List of topic strings
        """
        # Topics that candidates frequently ask about
        # Should be addressed upfront in future conversations
        return self.patterns.get("common_questions", [])

    def optimize_questions(
        self,
        questions: List[Question],
        learnings: Dict[str, Any]
    ) -> List[Question]:
        """
        Optimize question order and content based on learnings.

        Args:
            questions: Generated questions
            learnings: Current learnings

        Returns:
            Optimized questions
        """
        # Adjust priority based on patterns
        for question in questions:
            # If this topic frequently comes up, increase priority
            if self.should_prioritize_topic(question.category):
                question.priority = min(question.priority + 1, 5)

        # Sort by priority
        questions.sort(key=lambda q: q.priority, reverse=True)

        return questions
