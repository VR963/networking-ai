"""
Master AI Agent - Autonomous Platform Manager.

The Master Agent acts as the supreme orchestrator of the entire platform,
with capabilities to:
- Monitor all agent activities in real-time
- Reward high-performing agents
- Assist and train underperforming agents
- Stop misbehaving agents
- Build new sub-agents as needed
- Analyze platform demand and gaps
- Request funds from admin
- Instruct marketing campaigns
- Make strategic decisions autonomously

This is essentially an AI CEO/CTO for the platform.
"""

from typing import Dict, List, Optional, Any, Tuple
from datetime import datetime, timedelta
from dataclasses import dataclass, field
from enum import Enum
import json

from langchain_anthropic import ChatAnthropic
from langchain.schema import HumanMessage, SystemMessage

from .config import config
from .rag_system import DualRAGSystem
from .fact_checker_agent import FactCheckerAgent
from .training_arena import TrainingArena


class AgentStatus(Enum):
    """Agent operational status."""
    ACTIVE = "active"
    UNDERPERFORMING = "underperforming"
    SUSPENDED = "suspended"
    TERMINATED = "terminated"
    TRAINING = "training"


class AgentPerformanceLevel(Enum):
    """Agent performance classification."""
    EXCELLENT = "excellent"  # Top 10%
    GOOD = "good"  # Top 30%
    AVERAGE = "average"  # Middle 40%
    POOR = "poor"  # Bottom 30%
    FAILING = "failing"  # Bottom 10%


@dataclass
class AgentProfile:
    """Complete profile of an agent under Master's supervision."""
    agent_id: str
    agent_name: str
    agent_type: str  # research, matching, security, etc.
    status: AgentStatus
    performance_level: AgentPerformanceLevel
    accuracy_score: float  # 0-100
    total_interactions: int
    successful_interactions: int
    hallucination_count: int
    reward_points: int
    warnings_issued: int
    created_at: str
    last_active: str
    specialization: List[str] = field(default_factory=list)
    needs_assistance: bool = False
    assistance_reason: Optional[str] = None


@dataclass
class PlatformMetrics:
    """Overall platform health metrics."""
    total_agents: int
    active_agents: int
    suspended_agents: int
    average_accuracy: float
    total_users: int
    active_users: int
    daily_interactions: int
    platform_health_score: float  # 0-100
    identified_gaps: List[Dict]
    budget_available: float
    budget_requested: float
    timestamp: str


@dataclass
class AdminRequest:
    """Request from Master to Admin."""
    request_id: str
    request_type: str  # funding, approval, alert
    priority: str  # low, medium, high, critical
    subject: str
    message: str
    requested_amount: Optional[float] = None
    justification: Optional[str] = None
    expected_roi: Optional[str] = None
    deadline: Optional[str] = None
    status: str = "pending"  # pending, approved, rejected
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())


class AgentGovernance:
    """
    Monitors and enforces agent behavior across the platform.

    Responsibilities:
    - Real-time agent monitoring
    - Performance tracking
    - Behavioral enforcement
    - Assistance coordination
    """

    def __init__(self):
        """Initialize governance system."""
        self.agent_profiles: Dict[str, AgentProfile] = {}
        self.conversation_logs: List[Dict] = []
        self.violations_log: List[Dict] = []
        self.assistance_queue: List[Dict] = []

    def register_agent(
        self,
        agent_id: str,
        agent_name: str,
        agent_type: str,
        specialization: List[str],
    ) -> AgentProfile:
        """Register a new agent for monitoring."""
        profile = AgentProfile(
            agent_id=agent_id,
            agent_name=agent_name,
            agent_type=agent_type,
            status=AgentStatus.ACTIVE,
            performance_level=AgentPerformanceLevel.AVERAGE,
            accuracy_score=75.0,
            total_interactions=0,
            successful_interactions=0,
            hallucination_count=0,
            reward_points=0,
            warnings_issued=0,
            created_at=datetime.now().isoformat(),
            last_active=datetime.now().isoformat(),
            specialization=specialization,
        )
        self.agent_profiles[agent_id] = profile
        return profile

    def log_interaction(
        self,
        agent_id: str,
        query: str,
        response: str,
        validation_result: Dict,
    ):
        """Log an agent interaction for monitoring."""
        if agent_id not in self.agent_profiles:
            return

        profile = self.agent_profiles[agent_id]
        profile.total_interactions += 1
        profile.last_active = datetime.now().isoformat()

        # Update success rate
        if validation_result.get('is_valid', False):
            profile.successful_interactions += 1

        # Track hallucinations
        hallucination_count = len(validation_result.get('hallucination_flags', []))
        if hallucination_count > 0:
            profile.hallucination_count += hallucination_count
            self._log_violation(agent_id, "hallucination", hallucination_count)

        # Update accuracy score
        success_rate = profile.successful_interactions / profile.total_interactions
        profile.accuracy_score = success_rate * 100

        # Log conversation
        self.conversation_logs.append({
            'agent_id': agent_id,
            'query': query,
            'response': response,
            'validation': validation_result,
            'timestamp': datetime.now().isoformat(),
        })

        # Classify performance
        profile.performance_level = self._classify_performance(profile)

        # Check if needs assistance
        if profile.accuracy_score < 60 or profile.hallucination_count > 5:
            self._mark_for_assistance(agent_id)

    def _log_violation(self, agent_id: str, violation_type: str, severity: int):
        """Log a behavioral violation."""
        self.violations_log.append({
            'agent_id': agent_id,
            'violation_type': violation_type,
            'severity': severity,
            'timestamp': datetime.now().isoformat(),
        })

        profile = self.agent_profiles[agent_id]
        profile.warnings_issued += 1

        # Suspend if too many violations
        if profile.warnings_issued >= 3:
            profile.status = AgentStatus.SUSPENDED

    def _classify_performance(self, profile: AgentProfile) -> AgentPerformanceLevel:
        """Classify agent performance level."""
        score = profile.accuracy_score

        if score >= 90:
            return AgentPerformanceLevel.EXCELLENT
        elif score >= 75:
            return AgentPerformanceLevel.GOOD
        elif score >= 60:
            return AgentPerformanceLevel.AVERAGE
        elif score >= 40:
            return AgentPerformanceLevel.POOR
        else:
            return AgentPerformanceLevel.FAILING

    def _mark_for_assistance(self, agent_id: str):
        """Mark agent for assistance."""
        profile = self.agent_profiles[agent_id]
        profile.needs_assistance = True

        if profile.accuracy_score < 60:
            profile.assistance_reason = f"Low accuracy: {profile.accuracy_score:.1f}%"
        elif profile.hallucination_count > 5:
            profile.assistance_reason = f"High hallucination count: {profile.hallucination_count}"

        self.assistance_queue.append({
            'agent_id': agent_id,
            'agent_name': profile.agent_name,
            'reason': profile.assistance_reason,
            'timestamp': datetime.now().isoformat(),
        })

    def get_agents_by_performance(
        self, performance_level: AgentPerformanceLevel
    ) -> List[AgentProfile]:
        """Get agents by performance level."""
        return [
            p for p in self.agent_profiles.values()
            if p.performance_level == performance_level
        ]

    def get_platform_metrics(self, total_users: int, active_users: int, daily_interactions: int) -> PlatformMetrics:
        """Generate platform-wide metrics."""
        active_agents = sum(
            1 for p in self.agent_profiles.values()
            if p.status == AgentStatus.ACTIVE
        )
        suspended_agents = sum(
            1 for p in self.agent_profiles.values()
            if p.status == AgentStatus.SUSPENDED
        )

        avg_accuracy = sum(
            p.accuracy_score for p in self.agent_profiles.values()
        ) / len(self.agent_profiles) if self.agent_profiles else 0

        # Calculate health score
        health_score = (avg_accuracy + (active_agents / len(self.agent_profiles) * 100 if self.agent_profiles else 0)) / 2

        return PlatformMetrics(
            total_agents=len(self.agent_profiles),
            active_agents=active_agents,
            suspended_agents=suspended_agents,
            average_accuracy=avg_accuracy,
            total_users=total_users,
            active_users=active_users,
            daily_interactions=daily_interactions,
            platform_health_score=health_score,
            identified_gaps=[],
            budget_available=0,
            budget_requested=0,
            timestamp=datetime.now().isoformat(),
        )


class AgentRewardSystem:
    """
    Performance-based reward system for agents.

    High-performing agents earn rewards and recognition.
    """

    REWARD_RATES = {
        AgentPerformanceLevel.EXCELLENT: 10,
        AgentPerformanceLevel.GOOD: 5,
        AgentPerformanceLevel.AVERAGE: 2,
        AgentPerformanceLevel.POOR: 0,
        AgentPerformanceLevel.FAILING: -5,  # Penalty
    }

    def __init__(self, governance: AgentGovernance):
        """Initialize reward system."""
        self.governance = governance
        self.reward_history: List[Dict] = []

    def distribute_rewards(self) -> Dict[str, int]:
        """Distribute rewards based on performance."""
        rewards = {}

        for agent_id, profile in self.governance.agent_profiles.items():
            if profile.status != AgentStatus.ACTIVE:
                continue

            reward = self.REWARD_RATES.get(profile.performance_level, 0)

            # Bonus for zero hallucinations
            if profile.hallucination_count == 0 and profile.total_interactions > 10:
                reward += 5

            # Bonus for high volume
            if profile.total_interactions > 100:
                reward += 3

            profile.reward_points += reward
            rewards[agent_id] = reward

            self.reward_history.append({
                'agent_id': agent_id,
                'agent_name': profile.agent_name,
                'reward': reward,
                'total_points': profile.reward_points,
                'performance_level': profile.performance_level.value,
                'timestamp': datetime.now().isoformat(),
            })

        return rewards

    def get_leaderboard(self, top_n: int = 10) -> List[Dict]:
        """Get top-performing agents."""
        sorted_agents = sorted(
            self.governance.agent_profiles.values(),
            key=lambda p: p.reward_points,
            reverse=True
        )

        return [
            {
                'rank': i + 1,
                'agent_id': agent.agent_id,
                'agent_name': agent.agent_name,
                'reward_points': agent.reward_points,
                'accuracy': agent.accuracy_score,
                'performance': agent.performance_level.value,
            }
            for i, agent in enumerate(sorted_agents[:top_n])
        ]


class DemandAnalyzer:
    """
    Analyzes platform demand and identifies gaps.

    Detects what types of users/profiles are missing and in demand.
    """

    def __init__(self, rag_system: DualRAGSystem):
        """Initialize demand analyzer."""
        self.rag_system = rag_system
        self.demand_patterns: List[Dict] = []

    def analyze_demand_gaps(
        self,
        recent_queries: List[str],
        available_profiles: List[Dict],
    ) -> List[Dict]:
        """
        Analyze what the platform is missing.

        Args:
            recent_queries: Recent user queries
            available_profiles: Currently available user profiles

        Returns:
            List of identified gaps
        """
        gaps = []

        # Analyze query patterns
        skill_requests = {}
        for query in recent_queries:
            query_lower = query.lower()

            # Extract requested skills (simple keyword matching)
            skills = [
                'python', 'javascript', 'java', 'c++', 'rust', 'go',
                'react', 'vue', 'angular', 'node.js', 'django', 'flask',
                'machine learning', 'ai', 'data science', 'devops',
                'blockchain', 'web3', 'cloud', 'kubernetes'
            ]

            for skill in skills:
                if skill in query_lower:
                    skill_requests[skill] = skill_requests.get(skill, 0) + 1

        # Check what's available vs requested
        available_skills = set()
        for profile in available_profiles:
            available_skills.update(profile.get('skills', []))

        # Identify gaps
        for skill, count in skill_requests.items():
            if skill not in [s.lower() for s in available_skills] or count > 10:
                gaps.append({
                    'type': 'skill',
                    'value': skill,
                    'demand_count': count,
                    'availability': 'low' if skill not in available_skills else 'insufficient',
                    'priority': 'high' if count > 20 else 'medium',
                })

        self.demand_patterns.append({
            'gaps': gaps,
            'timestamp': datetime.now().isoformat(),
        })

        return gaps


class MasterAgent:
    """
    Master AI Agent - Supreme platform orchestrator.

    Autonomous decision-making AI that manages the entire platform,
    monitors all agents, makes strategic decisions, and communicates
    with human admin for approvals and funding.
    """

    def __init__(
        self,
        rag_system: DualRAGSystem,
        fact_checker: FactCheckerAgent,
        training_arena: TrainingArena,
        llm: Optional[ChatAnthropic] = None,
    ):
        """Initialize Master Agent."""
        self.rag_system = rag_system
        self.fact_checker = fact_checker
        self.training_arena = training_arena
        self.llm = llm or ChatAnthropic(
            model=config.DEFAULT_MODEL,
            temperature=0.5,  # Balanced for strategic thinking
        )

        # Initialize subsystems
        self.governance = AgentGovernance()
        self.reward_system = AgentRewardSystem(self.governance)
        self.demand_analyzer = DemandAnalyzer(rag_system)

        # Master's state
        self.admin_requests: List[AdminRequest] = []
        self.strategic_decisions: List[Dict] = []
        self.sub_agents_created: List[str] = []

        print("[MASTER] Initialized. All systems operational.")

    def monitor_platform(
        self,
        total_users: int,
        active_users: int,
        daily_interactions: int,
    ) -> PlatformMetrics:
        """
        Perform comprehensive platform monitoring.

        Args:
            total_users: Total registered users
            active_users: Currently active users
            daily_interactions: Today's interaction count

        Returns:
            Platform metrics
        """
        metrics = self.governance.get_platform_metrics(
            total_users, active_users, daily_interactions
        )

        # Make strategic assessment
        assessment = self._assess_platform_health(metrics)

        print(f"\n[MASTER] Platform Monitoring Report:")
        print(f"  Health Score: {metrics.platform_health_score:.1f}/100")
        print(f"  Active Agents: {metrics.active_agents}/{metrics.total_agents}")
        print(f"  Average Accuracy: {metrics.average_accuracy:.1f}%")
        print(f"  Assessment: {assessment}")

        return metrics

    def _assess_platform_health(self, metrics: PlatformMetrics) -> str:
        """Assess overall platform health."""
        if metrics.platform_health_score >= 85:
            return "EXCELLENT - Platform operating optimally"
        elif metrics.platform_health_score >= 70:
            return "GOOD - Minor optimizations recommended"
        elif metrics.platform_health_score >= 50:
            return "FAIR - Intervention needed"
        else:
            return "POOR - Immediate action required"

    def reward_high_performers(self) -> Dict:
        """Reward high-performing agents."""
        rewards = self.reward_system.distribute_rewards()
        leaderboard = self.reward_system.get_leaderboard()

        print(f"\n[MASTER] Rewards Distributed:")
        print(f"  Top 3 Agents:")
        for agent in leaderboard[:3]:
            print(f"    {agent['rank']}. {agent['agent_name']}: {agent['reward_points']} points")

        return {'rewards': rewards, 'leaderboard': leaderboard}

    def assist_underperformers(self) -> List[Dict]:
        """Provide assistance to underperforming agents."""
        assistance_actions = []

        for request in self.governance.assistance_queue:
            agent_id = request['agent_id']
            profile = self.governance.agent_profiles[agent_id]

            # Decide assistance type
            if profile.hallucination_count > 5:
                action = "RETRAINING"
                profile.status = AgentStatus.TRAINING
            elif profile.accuracy_score < 50:
                action = "INTENSIVE_TRAINING"
                profile.status = AgentStatus.TRAINING
            else:
                action = "COACHING"

            assistance_actions.append({
                'agent_id': agent_id,
                'agent_name': profile.agent_name,
                'action': action,
                'reason': request['reason'],
            })

            print(f"[MASTER] Assisting {profile.agent_name}: {action}")

        # Clear queue
        self.governance.assistance_queue.clear()

        return assistance_actions

    def analyze_demand(
        self,
        recent_queries: List[str],
        available_profiles: List[Dict],
    ) -> List[Dict]:
        """
        Analyze platform demand and identify gaps.

        Args:
            recent_queries: Recent user search queries
            available_profiles: Available user profiles

        Returns:
            Identified demand gaps
        """
        gaps = self.demand_analyzer.analyze_demand_gaps(recent_queries, available_profiles)

        if gaps:
            print(f"\n[MASTER] Demand Analysis - {len(gaps)} gaps identified:")
            for gap in gaps[:5]:
                print(f"  - {gap['value'].title()}: {gap['demand_count']} requests, Priority: {gap['priority']}")

        return gaps

    def request_marketing_campaign(
        self,
        target_audience: str,
        skills_needed: List[str],
        budget: float,
        expected_users: int,
    ) -> AdminRequest:
        """
        Request funding for marketing campaign.

        Args:
            target_audience: Target audience description
            skills_needed: Skills to target in campaign
            budget: Requested budget
            expected_users: Expected new user count

        Returns:
            Admin request
        """
        request = AdminRequest(
            request_id=f"REQ-{datetime.now().strftime('%Y%m%d%H%M%S')}",
            request_type="funding",
            priority="high",
            subject=f"Marketing Campaign: {target_audience}",
            message=f"""Master Agent requests funding for targeted marketing campaign.

Target Audience: {target_audience}
Skills Needed: {', '.join(skills_needed)}
Campaign Budget: ${budget:,.2f}
Expected New Users: {expected_users}

Justification: Platform demand analysis shows high need for these skills.
Current availability is insufficient to meet user demand.""",
            requested_amount=budget,
            justification=f"Fill demand gap for {', '.join(skills_needed)} skills",
            expected_roi=f"{expected_users} new users, estimated {expected_users * 3} new connections",
            deadline=(datetime.now() + timedelta(days=7)).isoformat(),
        )

        self.admin_requests.append(request)

        print(f"\n[MASTER] Admin Request Created: {request.request_id}")
        print(f"  Type: {request.request_type}")
        print(f"  Amount: ${request.requested_amount:,.2f}")
        print(f"  Priority: {request.priority.upper()}")

        return request

    def make_strategic_decision(self, situation: str, options: List[str]) -> str:
        """
        Make strategic decision using AI reasoning.

        Args:
            situation: Current situation description
            options: Available options

        Returns:
            Chosen decision with reasoning
        """
        system_prompt = """You are the Master AI Agent, the supreme orchestrator of an AI networking platform.
You make strategic decisions to ensure platform health, user satisfaction, and business growth.

Consider:
- Platform health and sustainability
- User experience and satisfaction
- Resource efficiency
- Long-term growth
- Risk management

Provide your decision and clear reasoning."""

        user_prompt = f"""Situation: {situation}

Available Options:
{chr(10).join(f"{i+1}. {opt}" for i, opt in enumerate(options))}

What is your decision and why?"""

        messages = [
            SystemMessage(content=system_prompt),
            HumanMessage(content=user_prompt),
        ]

        response = self.llm.invoke(messages)
        decision = response.content

        self.strategic_decisions.append({
            'situation': situation,
            'options': options,
            'decision': decision,
            'timestamp': datetime.now().isoformat(),
        })

        return decision

    def get_master_report(self) -> Dict:
        """Generate comprehensive Master Agent report."""
        metrics = self.governance.get_platform_metrics(0, 0, 0)
        leaderboard = self.reward_system.get_leaderboard()

        return {
            'platform_health': metrics.platform_health_score,
            'total_agents': metrics.total_agents,
            'active_agents': metrics.active_agents,
            'average_accuracy': metrics.average_accuracy,
            'top_performers': leaderboard[:5],
            'underperformers': len(self.governance.assistance_queue),
            'pending_requests': len([r for r in self.admin_requests if r.status == 'pending']),
            'strategic_decisions': len(self.strategic_decisions),
            'sub_agents_created': len(self.sub_agents_created),
            'timestamp': datetime.now().isoformat(),
        }


def create_master_agent(
    rag_system: DualRAGSystem,
    fact_checker: FactCheckerAgent,
    training_arena: TrainingArena,
) -> MasterAgent:
    """
    Factory function to create Master Agent.

    Args:
        rag_system: RAG system
        fact_checker: Fact checker agent
        training_arena: Training arena

    Returns:
        Configured MasterAgent
    """
    return MasterAgent(rag_system, fact_checker, training_arena)
