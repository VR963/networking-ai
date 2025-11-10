"""
Master AI Conversation Monitor.

Master AI oversees all agent-to-agent conversations and:
1. Monitors conversation progress
2. Detects and kills stuck conversations (no progress after 5 turns)
3. Extracts learnings for network-wide knowledge sharing
4. Enforces resource limits
5. Provides intervention when needed
"""

from typing import Dict, List, Optional, Any
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum

from ..services.parallel_conversation_manager import ConversationContext, ConversationState


class InterventionType(str, Enum):
    """Types of Master AI interventions."""
    KILL_STUCK = "kill_stuck"  # No progress after 5 turns
    KILL_TOO_LONG = "kill_too_long"  # > 10 turns
    RESOURCE_LIMIT = "resource_limit"  # Too many active conversations
    QUALITY_CHECK = "quality_check"  # Response quality issues


@dataclass
class ConversationHealth:
    """Health assessment of a conversation."""
    conversation_id: str
    is_healthy: bool
    progress_score: float  # 0-100, how much progress is being made
    concerns: List[str] = field(default_factory=list)
    recommendations: List[str] = field(default_factory=list)


@dataclass
class Intervention:
    """Master AI intervention record."""
    conversation_id: str
    intervention_type: InterventionType
    reason: str
    timestamp: datetime = field(default_factory=datetime.now)
    action_taken: str = ""


@dataclass
class NetworkLearning:
    """Learning extracted for network-wide knowledge sharing."""
    user_segment: str  # e.g., "system_engineer_finance_5yrs_python"
    pattern_type: str  # e.g., "preference", "disqualifier", "common_question"
    pattern_data: Dict[str, Any]
    confidence: float
    sample_size: int  # How many users this learning is based on
    timestamp: datetime = field(default_factory=datetime.now)


class MasterAIConversationMonitor:
    """
    Master AI monitors and manages all agent-to-agent conversations.

    Responsibilities:
    - Real-time monitoring of conversation health
    - Intervention when conversations are stuck or unproductive
    - Resource management (prevent too many concurrent conversations)
    - Knowledge extraction for network-wide learning
    - Pattern detection across conversations
    """

    def __init__(self):
        """Initialize Master AI conversation monitor."""
        self.monitored_conversations: Dict[str, ConversationContext] = {}
        self.interventions: List[Intervention] = []
        self.network_learnings: List[NetworkLearning] = []

        # Monitoring thresholds
        self.stuck_turn_threshold = 5  # No progress after 5 turns
        self.max_turns_threshold = 10  # Force end after 10 turns
        self.max_concurrent_per_agent = 3  # Max active conversations per agent

    def monitor_conversation(
        self,
        ctx: ConversationContext
    ) -> ConversationHealth:
        """
        Monitor a conversation and assess its health.

        Args:
            ctx: Conversation context

        Returns:
            ConversationHealth assessment
        """
        # Track conversation
        self.monitored_conversations[ctx.conversation_id] = ctx

        # Assess health
        health = ConversationHealth(
            conversation_id=ctx.conversation_id,
            is_healthy=True,
            progress_score=100.0
        )

        # Check 1: Stuck conversation (no progress)
        if self._is_stuck(ctx):
            health.is_healthy = False
            health.progress_score -= 50
            health.concerns.append(
                f"No progress after {ctx.turn_number} turns"
            )
            health.recommendations.append("Consider terminating conversation")

        # Check 2: Too long
        if ctx.turn_number > self.max_turns_threshold:
            health.is_healthy = False
            health.progress_score -= 30
            health.concerns.append(
                f"Conversation too long ({ctx.turn_number} turns)"
            )
            health.recommendations.append("Force decision or terminate")

        # Check 3: Deal breakers found
        if ctx.deal_breakers_found:
            health.is_healthy = False
            health.progress_score -= 40
            health.concerns.append(
                f"Deal breakers found: {', '.join(ctx.deal_breakers_found)}"
            )
            health.recommendations.append("Terminate - mismatch detected")

        # Check 4: Message quality
        if ctx.messages:
            avg_length = sum(len(m["content"]) for m in ctx.messages) / len(ctx.messages)
            if avg_length < 50:
                health.progress_score -= 20
                health.concerns.append("Low-quality responses (too brief)")

        # Check 5: Time since last message
        if ctx.last_message_at:
            time_since_last = datetime.now() - ctx.last_message_at
            if time_since_last > timedelta(minutes=5):
                health.progress_score -= 15
                health.concerns.append("Long gap since last message")

        # Final health score
        health.is_healthy = health.progress_score >= 50

        return health

    def should_intervene(
        self,
        ctx: ConversationContext
    ) -> Optional[InterventionType]:
        """
        Determine if Master AI should intervene in conversation.

        Args:
            ctx: Conversation context

        Returns:
            InterventionType if intervention needed, None otherwise
        """
        # Check if stuck
        if self._is_stuck(ctx):
            return InterventionType.KILL_STUCK

        # Check if too long
        if ctx.turn_number > self.max_turns_threshold:
            return InterventionType.KILL_TOO_LONG

        # Check deal breakers
        if ctx.deal_breakers_found and ctx.phase.value == "screening":
            return InterventionType.KILL_STUCK

        return None

    def intervene(
        self,
        ctx: ConversationContext,
        intervention_type: InterventionType
    ) -> Intervention:
        """
        Execute intervention on conversation.

        Args:
            ctx: Conversation context
            intervention_type: Type of intervention

        Returns:
            Intervention record
        """
        if intervention_type == InterventionType.KILL_STUCK:
            reason = f"No progress after {ctx.turn_number} turns"
            action = "Terminated conversation - stuck"
            ctx.state = ConversationState.STUCK

        elif intervention_type == InterventionType.KILL_TOO_LONG:
            reason = f"Exceeded max turns ({ctx.turn_number} > {self.max_turns_threshold})"
            action = "Force-terminated conversation - too long"
            ctx.state = ConversationState.STUCK

        else:
            reason = "Quality concerns"
            action = "Flagged for review"

        intervention = Intervention(
            conversation_id=ctx.conversation_id,
            intervention_type=intervention_type,
            reason=reason,
            action_taken=action
        )

        self.interventions.append(intervention)

        print(f"⚠️  Master AI Intervention: {intervention.conversation_id}")
        print(f"   Type: {intervention_type.value}")
        print(f"   Reason: {reason}")
        print(f"   Action: {action}")

        return intervention

    def _is_stuck(self, ctx: ConversationContext) -> bool:
        """
        Determine if conversation is stuck (no progress).

        Stuck = same type of exchange repeated without progress
        """
        if ctx.turn_number < self.stuck_turn_threshold:
            return False

        # Check if insights are being extracted
        if ctx.turn_number >= 5 and len(ctx.insights) < 2:
            # 5+ turns but less than 2 insights = stuck
            return True

        # Check for repeated patterns
        if len(ctx.messages) >= 6:
            # Check if last 3 exchanges are very similar
            last_6 = ctx.messages[-6:]
            lengths = [len(m["content"]) for m in last_6]

            # If all messages are very short, might be stuck
            if all(l < 100 for l in lengths):
                return True

        return False

    def extract_network_learnings(
        self,
        conversations: List[ConversationContext]
    ) -> List[NetworkLearning]:
        """
        Extract network-wide learnings from conversations.

        Master AI aggregates patterns across users for cross-learning.

        Args:
            conversations: List of completed conversations

        Returns:
            List of NetworkLearning objects
        """
        learnings = []

        # Group conversations by user segment
        segments: Dict[str, List[ConversationContext]] = {}

        for ctx in conversations:
            # Extract user segment from context
            # In production, this would query the agent's user_segment_id
            segment = "default_segment"  # Placeholder

            if segment not in segments:
                segments[segment] = []

            segments[segment].append(ctx)

        # Extract patterns per segment
        for segment, segment_conversations in segments.items():
            if len(segment_conversations) < 3:
                # Need at least 3 conversations for pattern
                continue

            # Pattern 1: Common deal breakers
            all_deal_breakers = []
            for ctx in segment_conversations:
                all_deal_breakers.extend(ctx.deal_breakers_found)

            if all_deal_breakers:
                from collections import Counter
                deal_breaker_counts = Counter(all_deal_breakers)

                for deal_breaker, count in deal_breaker_counts.most_common(3):
                    if count >= 2:  # At least 2 occurrences
                        learnings.append(NetworkLearning(
                            user_segment=segment,
                            pattern_type="common_deal_breaker",
                            pattern_data={"deal_breaker": deal_breaker},
                            confidence=count / len(segment_conversations),
                            sample_size=len(segment_conversations)
                        ))

            # Pattern 2: Common positive signals
            all_positive_signals = []
            for ctx in segment_conversations:
                all_positive_signals.extend(ctx.positive_signals)

            if all_positive_signals:
                from collections import Counter
                signal_counts = Counter(all_positive_signals)

                for signal, count in signal_counts.most_common(3):
                    if count >= 2:
                        learnings.append(NetworkLearning(
                            user_segment=segment,
                            pattern_type="common_priority",
                            pattern_data={"priority": signal},
                            confidence=count / len(segment_conversations),
                            sample_size=len(segment_conversations)
                        ))

            # Pattern 3: Successful conversation patterns
            successful_convs = [
                ctx for ctx in segment_conversations
                if ctx.state == ConversationState.COMPLETED
                and not ctx.deal_breakers_found
            ]

            if successful_convs:
                avg_turns = sum(c.turn_number for c in successful_convs) / len(successful_convs)

                learnings.append(NetworkLearning(
                    user_segment=segment,
                    pattern_type="successful_pattern",
                    pattern_data={
                        "avg_turns": avg_turns,
                        "success_rate": len(successful_convs) / len(segment_conversations)
                    },
                    confidence=0.8,
                    sample_size=len(segment_conversations)
                ))

        self.network_learnings.extend(learnings)

        return learnings

    def share_learnings_with_segment(
        self,
        user_segment: str
    ) -> Dict[str, Any]:
        """
        Get aggregated learnings for a user segment.

        Non-communicative users benefit from communicative users' learnings.

        Args:
            user_segment: User segment ID

        Returns:
            Dict of learnings for this segment
        """
        segment_learnings = [
            l for l in self.network_learnings
            if l.user_segment == user_segment
        ]

        if not segment_learnings:
            return {}

        # Organize by pattern type
        learnings = {
            "deal_breakers": [],
            "priorities": [],
            "successful_patterns": []
        }

        for learning in segment_learnings:
            if learning.pattern_type == "common_deal_breaker":
                learnings["deal_breakers"].append({
                    "deal_breaker": learning.pattern_data["deal_breaker"],
                    "confidence": learning.confidence,
                    "sample_size": learning.sample_size
                })

            elif learning.pattern_type == "common_priority":
                learnings["priorities"].append({
                    "priority": learning.pattern_data["priority"],
                    "confidence": learning.confidence,
                    "sample_size": learning.sample_size
                })

            elif learning.pattern_type == "successful_pattern":
                learnings["successful_patterns"].append(learning.pattern_data)

        return learnings

    def get_monitoring_stats(self) -> Dict[str, Any]:
        """Get monitoring statistics."""
        return {
            "total_conversations_monitored": len(self.monitored_conversations),
            "interventions_performed": len(self.interventions),
            "network_learnings_extracted": len(self.network_learnings),
            "intervention_breakdown": {
                intervention_type.value: len([
                    i for i in self.interventions
                    if i.intervention_type == intervention_type
                ])
                for intervention_type in InterventionType
            }
        }

    def generate_report(self) -> str:
        """Generate Master AI monitoring report."""
        stats = self.get_monitoring_stats()

        report = f"""
{'='*60}
MASTER AI CONVERSATION MONITORING REPORT
{'='*60}

Conversations Monitored: {stats['total_conversations_monitored']}
Interventions Performed: {stats['interventions_performed']}
Network Learnings: {stats['network_learnings_extracted']}

Intervention Breakdown:
"""

        for intervention_type, count in stats['intervention_breakdown'].items():
            if count > 0:
                report += f"  - {intervention_type}: {count}\n"

        report += f"\n{'='*60}\n"

        return report
