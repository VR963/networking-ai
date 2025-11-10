"""
Platform Health System - Critical monitoring and reporting for Master AI.

The Master AI's primary responsibility is to keep the network alive and manageable.
This is a critical ecosystem that must be nurtured constantly.

CRITICAL THRESHOLD: 69%
- Below 69% = Platform facing shutdown
- This indicates users are not benefiting from AI agents
- The overall process is at risk of failure

The Master AI must submit platform health reports:
- Daily reports
- Weekly reports
- Monthly reports
- Quarterly reports

Health calculation is based on:
1. User interaction with AI agents
2. Organic growth of the platform
3. Balance between users and companies
4. Supply and demand outcome ratio
5. Success rate of matching candidates to jobs
6. Overall post-work impact
"""

from typing import Dict, List, Optional, Tuple
from datetime import datetime, timedelta
from dataclasses import dataclass, field
from enum import Enum
import json

from langchain_anthropic import ChatAnthropic
from langchain.schema import HumanMessage, SystemMessage

from .config import config


# ============================================================================
# CRITICAL THRESHOLDS
# ============================================================================

class HealthLevel(Enum):
    """Platform health levels."""
    EXCELLENT = "excellent"  # 90-100%
    GOOD = "good"  # 75-89%
    ACCEPTABLE = "acceptable"  # 69-74% (just above critical)
    CRITICAL = "critical"  # Below 69% - SHUTDOWN RISK
    SHUTDOWN = "shutdown"  # System terminated


class AlertSeverity(Enum):
    """Alert severity levels."""
    INFO = "info"
    WARNING = "warning"
    CRITICAL = "critical"
    EMERGENCY = "emergency"  # Below 69% threshold


CRITICAL_THRESHOLD = 69.0  # Below this = platform shutdown risk
ACCEPTABLE_THRESHOLD = 75.0  # Minimum for healthy operation
EXCELLENT_THRESHOLD = 90.0  # Optimal performance


# ============================================================================
# DATA STRUCTURES
# ============================================================================

@dataclass
class UserInteractionMetrics:
    """Metrics for user interaction with AI agents."""
    total_users: int
    active_users_daily: int
    active_users_weekly: int
    active_users_monthly: int
    users_with_agent_interactions: int
    avg_interactions_per_user: float
    user_satisfaction_score: float  # 0-100
    agent_response_quality_score: float  # 0-100
    timestamp: str

    def calculate_interaction_health(self) -> float:
        """Calculate health score from user interactions (0-100)."""
        if self.total_users == 0:
            return 0.0

        # Active user rate (40% weight)
        active_rate = (self.users_with_agent_interactions / self.total_users) * 40

        # Interaction frequency (30% weight)
        interaction_score = min(self.avg_interactions_per_user / 10, 1.0) * 30

        # Quality scores (30% weight)
        quality_score = (
            (self.user_satisfaction_score / 100 * 15) +
            (self.agent_response_quality_score / 100 * 15)
        )

        return min(active_rate + interaction_score + quality_score, 100.0)


@dataclass
class OrganicGrowthMetrics:
    """Metrics for organic platform growth."""
    new_users_today: int
    new_users_this_week: int
    new_users_this_month: int
    new_users_this_quarter: int
    referral_signups: int
    organic_signups: int  # Non-paid, non-referred
    paid_campaign_signups: int
    user_retention_rate: float  # Percentage staying active after 30 days
    growth_rate_monthly: float  # Percentage growth
    churn_rate_monthly: float  # Percentage leaving
    timestamp: str

    def calculate_growth_health(self) -> float:
        """Calculate health score from growth (0-100)."""
        # Organic growth rate (40% weight)
        total_new = self.new_users_this_month
        if total_new == 0:
            organic_score = 0
        else:
            organic_ratio = self.organic_signups / total_new
            organic_score = organic_ratio * 40

        # Retention rate (35% weight)
        retention_score = self.user_retention_rate * 35

        # Growth vs churn (25% weight)
        net_growth = max(0, self.growth_rate_monthly - self.churn_rate_monthly)
        growth_score = min(net_growth / 10, 1.0) * 25  # 10% monthly growth = full score

        return min(organic_score + retention_score + growth_score, 100.0)


@dataclass
class BalanceMetrics:
    """Metrics for user/company balance."""
    total_individual_users: int
    total_companies: int
    active_job_seekers: int
    active_job_posters: int
    jobs_posted_this_month: int
    applications_this_month: int
    optimal_user_to_company_ratio: float = 50.0  # 50 users per company ideal
    timestamp: str

    def calculate_balance_health(self) -> float:
        """Calculate health score from balance (0-100)."""
        if self.total_companies == 0:
            return 0.0

        # Current ratio
        current_ratio = self.total_individual_users / self.total_companies

        # How close to optimal? (50% weight)
        ratio_score = (1 - abs(current_ratio - self.optimal_user_to_company_ratio) / self.optimal_user_to_company_ratio) * 50
        ratio_score = max(0, ratio_score)

        # Activity balance (50% weight)
        if self.jobs_posted_this_month == 0:
            activity_score = 0
        else:
            apps_per_job = self.applications_this_month / self.jobs_posted_this_month
            # Optimal: 10-30 applications per job
            if 10 <= apps_per_job <= 30:
                activity_score = 50
            elif apps_per_job < 10:
                activity_score = (apps_per_job / 10) * 50
            else:
                activity_score = max(0, 50 - ((apps_per_job - 30) / 10) * 10)

        return min(ratio_score + activity_score, 100.0)


@dataclass
class MatchingSuccessMetrics:
    """Metrics for supply/demand matching success."""
    total_matches_attempted: int
    successful_matches: int
    interviews_scheduled: int
    offers_made: int
    offers_accepted: int
    candidates_placed: int
    avg_time_to_match_days: float
    match_quality_score: float  # 0-100 based on feedback
    timestamp: str

    def calculate_matching_health(self) -> float:
        """Calculate health score from matching success (0-100)."""
        if self.total_matches_attempted == 0:
            return 0.0

        # Match success rate (30% weight)
        success_rate = (self.successful_matches / self.total_matches_attempted) * 30

        # Conversion funnel (40% weight)
        # Matches → Interviews → Offers → Acceptances → Placements
        if self.successful_matches > 0:
            interview_rate = (self.interviews_scheduled / self.successful_matches) * 10
            offer_rate = (self.offers_made / max(1, self.interviews_scheduled)) * 10
            acceptance_rate = (self.offers_accepted / max(1, self.offers_made)) * 10
            placement_rate = (self.candidates_placed / max(1, self.offers_accepted)) * 10
            conversion_score = interview_rate + offer_rate + acceptance_rate + placement_rate
        else:
            conversion_score = 0

        # Match quality (30% weight)
        quality_score = (self.match_quality_score / 100) * 30

        return min(success_rate + conversion_score + quality_score, 100.0)


@dataclass
class PostWorkImpactMetrics:
    """Metrics for overall post-work impact."""
    successful_placements_total: int
    placements_still_employed_30_days: int
    placements_still_employed_90_days: int
    avg_employee_satisfaction: float  # 0-100
    avg_employer_satisfaction: float  # 0-100
    repeat_hiring_rate: float  # Companies hiring again
    candidate_referral_rate: float  # Placed candidates referring others
    platform_nps_score: float  # Net Promoter Score (-100 to 100)
    timestamp: str

    def calculate_impact_health(self) -> float:
        """Calculate health score from post-work impact (0-100)."""
        if self.successful_placements_total == 0:
            return 50.0  # Neutral if no data yet

        # Employment retention (40% weight)
        retention_30 = (self.placements_still_employed_30_days / self.successful_placements_total) * 20
        retention_90 = (self.placements_still_employed_90_days / self.successful_placements_total) * 20
        retention_score = retention_30 + retention_90

        # Satisfaction (35% weight)
        satisfaction_score = (
            (self.avg_employee_satisfaction / 100 * 17.5) +
            (self.avg_employer_satisfaction / 100 * 17.5)
        )

        # Platform loyalty (25% weight)
        loyalty_score = (
            (self.repeat_hiring_rate * 12.5) +
            (self.candidate_referral_rate * 12.5)
        )

        return min(retention_score + satisfaction_score + loyalty_score, 100.0)


@dataclass
class ComprehensivePlatformHealth:
    """Complete platform health assessment."""
    interaction_metrics: UserInteractionMetrics
    growth_metrics: OrganicGrowthMetrics
    balance_metrics: BalanceMetrics
    matching_metrics: MatchingSuccessMetrics
    impact_metrics: PostWorkImpactMetrics

    # Component scores
    interaction_health: float
    growth_health: float
    balance_health: float
    matching_health: float
    impact_health: float

    # Overall score
    overall_health_score: float
    health_level: HealthLevel

    # Status
    is_critical: bool
    days_until_shutdown: Optional[int]
    timestamp: str

    # Alerts
    alerts: List[Dict] = field(default_factory=list)
    recommendations: List[str] = field(default_factory=list)


@dataclass
class HealthReport:
    """Health report for admin."""
    report_id: str
    report_type: str  # daily, weekly, monthly, quarterly
    period_start: str
    period_end: str
    platform_health: ComprehensivePlatformHealth
    critical_issues: List[str]
    action_items: List[str]
    master_assessment: str
    requires_immediate_action: bool
    generated_at: str


# ============================================================================
# PLATFORM HEALTH CALCULATOR
# ============================================================================

class PlatformHealthCalculator:
    """
    Calculates comprehensive platform health score.

    CRITICAL: Below 69% = Shutdown risk
    """

    # Component weights (must sum to 1.0)
    WEIGHTS = {
        'interaction': 0.25,  # 25% - User interaction with agents
        'growth': 0.20,  # 20% - Organic growth
        'balance': 0.15,  # 15% - User/company balance
        'matching': 0.25,  # 25% - Matching success
        'impact': 0.15,  # 15% - Post-work impact
    }

    def calculate_health(
        self,
        interaction_metrics: UserInteractionMetrics,
        growth_metrics: OrganicGrowthMetrics,
        balance_metrics: BalanceMetrics,
        matching_metrics: MatchingSuccessMetrics,
        impact_metrics: PostWorkImpactMetrics,
    ) -> ComprehensivePlatformHealth:
        """
        Calculate comprehensive platform health.

        Returns:
            Complete health assessment
        """
        # Calculate component scores
        interaction_health = interaction_metrics.calculate_interaction_health()
        growth_health = growth_metrics.calculate_growth_health()
        balance_health = balance_metrics.calculate_balance_health()
        matching_health = matching_metrics.calculate_matching_health()
        impact_health = impact_metrics.calculate_impact_health()

        # Calculate weighted overall score
        overall_score = (
            interaction_health * self.WEIGHTS['interaction'] +
            growth_health * self.WEIGHTS['growth'] +
            balance_health * self.WEIGHTS['balance'] +
            matching_health * self.WEIGHTS['matching'] +
            impact_health * self.WEIGHTS['impact']
        )

        # Determine health level
        health_level = self._determine_health_level(overall_score)

        # Check if critical
        is_critical = overall_score < CRITICAL_THRESHOLD

        # Estimate days until shutdown if declining
        days_until_shutdown = None
        if is_critical:
            days_until_shutdown = 0  # Already critical
        elif overall_score < ACCEPTABLE_THRESHOLD:
            # Rough estimate based on how close to critical
            days_until_shutdown = int((overall_score - CRITICAL_THRESHOLD) * 10)

        # Generate alerts
        alerts = self._generate_alerts(
            overall_score,
            interaction_health,
            growth_health,
            balance_health,
            matching_health,
            impact_health,
        )

        # Generate recommendations
        recommendations = self._generate_recommendations(
            interaction_health,
            growth_health,
            balance_health,
            matching_health,
            impact_health,
        )

        return ComprehensivePlatformHealth(
            interaction_metrics=interaction_metrics,
            growth_metrics=growth_metrics,
            balance_metrics=balance_metrics,
            matching_metrics=matching_metrics,
            impact_metrics=impact_metrics,
            interaction_health=interaction_health,
            growth_health=growth_health,
            balance_health=balance_health,
            matching_health=matching_health,
            impact_health=impact_health,
            overall_health_score=overall_score,
            health_level=health_level,
            is_critical=is_critical,
            days_until_shutdown=days_until_shutdown,
            timestamp=datetime.now().isoformat(),
            alerts=alerts,
            recommendations=recommendations,
        )

    def _determine_health_level(self, score: float) -> HealthLevel:
        """Determine health level from score."""
        if score >= EXCELLENT_THRESHOLD:
            return HealthLevel.EXCELLENT
        elif score >= ACCEPTABLE_THRESHOLD:
            return HealthLevel.GOOD
        elif score >= CRITICAL_THRESHOLD:
            return HealthLevel.ACCEPTABLE
        else:
            return HealthLevel.CRITICAL

    def _generate_alerts(
        self,
        overall: float,
        interaction: float,
        growth: float,
        balance: float,
        matching: float,
        impact: float,
    ) -> List[Dict]:
        """Generate alerts based on scores."""
        alerts = []

        # Critical overall alert
        if overall < CRITICAL_THRESHOLD:
            alerts.append({
                'severity': AlertSeverity.EMERGENCY.value,
                'category': 'overall',
                'message': f'🚨 EMERGENCY: Platform health at {overall:.1f}% - BELOW CRITICAL THRESHOLD OF 69%',
                'action_required': 'IMMEDIATE',
                'details': 'Platform is at risk of shutdown. All hands on deck required.',
            })
        elif overall < ACCEPTABLE_THRESHOLD:
            alerts.append({
                'severity': AlertSeverity.CRITICAL.value,
                'category': 'overall',
                'message': f'⚠️ CRITICAL: Platform health at {overall:.1f}% - Approaching shutdown threshold',
                'action_required': 'URGENT',
                'details': f'Only {overall - CRITICAL_THRESHOLD:.1f} points above critical threshold.',
            })

        # Component-specific alerts
        if interaction < 60:
            alerts.append({
                'severity': AlertSeverity.CRITICAL.value,
                'category': 'interaction',
                'message': f'User interaction score critically low: {interaction:.1f}%',
                'action_required': 'HIGH',
                'details': 'Users not effectively benefiting from AI agents.',
            })

        if growth < 60:
            alerts.append({
                'severity': AlertSeverity.WARNING.value,
                'category': 'growth',
                'message': f'Organic growth declining: {growth:.1f}%',
                'action_required': 'MEDIUM',
                'details': 'Platform growth is stagnating.',
            })

        if balance < 60:
            alerts.append({
                'severity': AlertSeverity.WARNING.value,
                'category': 'balance',
                'message': f'User/company balance unhealthy: {balance:.1f}%',
                'action_required': 'MEDIUM',
                'details': 'Supply-demand imbalance detected.',
            })

        if matching < 60:
            alerts.append({
                'severity': AlertSeverity.CRITICAL.value,
                'category': 'matching',
                'message': f'Matching success rate poor: {matching:.1f}%',
                'action_required': 'HIGH',
                'details': 'Core platform function underperforming.',
            })

        if impact < 60:
            alerts.append({
                'severity': AlertSeverity.WARNING.value,
                'category': 'impact',
                'message': f'Post-work impact low: {impact:.1f}%',
                'action_required': 'MEDIUM',
                'details': 'Long-term value proposition at risk.',
            })

        return alerts

    def _generate_recommendations(
        self,
        interaction: float,
        growth: float,
        balance: float,
        matching: float,
        impact: float,
    ) -> List[str]:
        """Generate actionable recommendations."""
        recommendations = []

        # Prioritize by severity
        component_scores = [
            ('interaction', interaction, 'User Interaction'),
            ('growth', growth, 'Organic Growth'),
            ('balance', balance, 'Platform Balance'),
            ('matching', matching, 'Matching Success'),
            ('impact', impact, 'Post-Work Impact'),
        ]

        # Sort by score (lowest first)
        component_scores.sort(key=lambda x: x[1])

        for component, score, name in component_scores:
            if score < 70:
                if component == 'interaction':
                    recommendations.append(
                        f"🎯 {name} ({score:.1f}%): Improve agent response quality and user engagement features"
                    )
                elif component == 'growth':
                    recommendations.append(
                        f"📈 {name} ({score:.1f}%): Launch marketing campaigns to boost organic signups and reduce churn"
                    )
                elif component == 'balance':
                    recommendations.append(
                        f"⚖️ {name} ({score:.1f}%): Actively recruit companies or users to restore balance"
                    )
                elif component == 'matching':
                    recommendations.append(
                        f"🎲 {name} ({score:.1f}%): Enhance matching algorithms and agent training"
                    )
                elif component == 'impact':
                    recommendations.append(
                        f"💼 {name} ({score:.1f}%): Improve post-placement support and satisfaction monitoring"
                    )

        return recommendations


# ============================================================================
# AUTOMATED REPORTING SYSTEM
# ============================================================================

class HealthReportingSystem:
    """
    Automated health reporting system for Master AI.

    Generates:
    - Daily reports
    - Weekly reports
    - Monthly reports
    - Quarterly reports
    """

    def __init__(self, llm: Optional[ChatAnthropic] = None):
        """Initialize reporting system."""
        self.llm = llm or ChatAnthropic(
            model=config.DEFAULT_MODEL,
            temperature=0.3,  # Analytical
        )
        self.calculator = PlatformHealthCalculator()
        self.report_history: List[HealthReport] = []

        self.last_daily_report: Optional[datetime] = None
        self.last_weekly_report: Optional[datetime] = None
        self.last_monthly_report: Optional[datetime] = None
        self.last_quarterly_report: Optional[datetime] = None

    def should_generate_report(self, report_type: str) -> bool:
        """Check if report should be generated."""
        now = datetime.now()

        if report_type == 'daily':
            if self.last_daily_report is None:
                return True
            return (now - self.last_daily_report).days >= 1

        elif report_type == 'weekly':
            if self.last_weekly_report is None:
                return True
            return (now - self.last_weekly_report).days >= 7

        elif report_type == 'monthly':
            if self.last_monthly_report is None:
                return True
            return (now - self.last_monthly_report).days >= 30

        elif report_type == 'quarterly':
            if self.last_quarterly_report is None:
                return True
            return (now - self.last_quarterly_report).days >= 90

        return False

    def generate_report(
        self,
        report_type: str,
        health: ComprehensivePlatformHealth,
    ) -> HealthReport:
        """
        Generate health report for admin.

        Args:
            report_type: daily, weekly, monthly, or quarterly
            health: Current platform health

        Returns:
            Health report
        """
        now = datetime.now()

        # Determine period
        if report_type == 'daily':
            period_start = (now - timedelta(days=1)).isoformat()
            self.last_daily_report = now
        elif report_type == 'weekly':
            period_start = (now - timedelta(days=7)).isoformat()
            self.last_weekly_report = now
        elif report_type == 'monthly':
            period_start = (now - timedelta(days=30)).isoformat()
            self.last_monthly_report = now
        else:  # quarterly
            period_start = (now - timedelta(days=90)).isoformat()
            self.last_quarterly_report = now

        # Extract critical issues
        critical_issues = [
            alert['message']
            for alert in health.alerts
            if alert['severity'] in [AlertSeverity.CRITICAL.value, AlertSeverity.EMERGENCY.value]
        ]

        # Generate Master's assessment using AI
        master_assessment = self._generate_master_assessment(health, report_type)

        # Create report
        report = HealthReport(
            report_id=f"HEALTH-{report_type.upper()}-{now.strftime('%Y%m%d%H%M%S')}",
            report_type=report_type,
            period_start=period_start,
            period_end=now.isoformat(),
            platform_health=health,
            critical_issues=critical_issues,
            action_items=health.recommendations,
            master_assessment=master_assessment,
            requires_immediate_action=health.is_critical or len(critical_issues) > 0,
            generated_at=now.isoformat(),
        )

        self.report_history.append(report)

        return report

    def _generate_master_assessment(
        self,
        health: ComprehensivePlatformHealth,
        report_type: str,
    ) -> str:
        """Generate Master AI's strategic assessment using Claude."""
        system_prompt = """You are the Master AI, the supreme orchestrator of an AI networking platform.
Your primary responsibility is to keep the network alive and manageable.

CRITICAL THRESHOLD: 69%
- Below 69% = Platform shutdown risk
- Your job is to prevent this at all costs

Provide a strategic assessment of the platform health with:
- Executive summary (2-3 sentences)
- Key concerns
- Strategic recommendations
- Urgency level

Be direct, strategic, and action-oriented."""

        user_prompt = f"""Platform Health {report_type.upper()} Report:

Overall Health Score: {health.overall_health_score:.1f}%
Status: {health.health_level.value.upper()}
{'🚨 CRITICAL - SHUTDOWN RISK' if health.is_critical else ''}

Component Scores:
- User Interaction: {health.interaction_health:.1f}%
- Organic Growth: {health.growth_health:.1f}%
- Platform Balance: {health.balance_health:.1f}%
- Matching Success: {health.matching_health:.1f}%
- Post-Work Impact: {health.impact_health:.1f}%

Active Alerts: {len(health.alerts)}
Critical Issues: {len([a for a in health.alerts if a['severity'] == AlertSeverity.EMERGENCY.value])}

Provide your strategic assessment."""

        try:
            messages = [
                SystemMessage(content=system_prompt),
                HumanMessage(content=user_prompt),
            ]

            response = self.llm.invoke(messages)
            return response.content

        except Exception as e:
            # Fallback assessment
            if health.is_critical:
                return f"""🚨 EMERGENCY ASSESSMENT:

Platform health has fallen below the critical 69% threshold at {health.overall_health_score:.1f}%.
This platform is at immediate risk of shutdown.

All strategic initiatives must focus on restoring health above 69% within the next 7 days.
Recommend emergency budget allocation for critical interventions.

Urgency: MAXIMUM"""
            else:
                return f"Platform operating at {health.overall_health_score:.1f}% health. Monitoring {len(health.alerts)} active issues."

    def print_report(self, report: HealthReport):
        """Print formatted report."""
        health = report.platform_health

        print("\n" + "=" * 80)
        print(f"📊 PLATFORM HEALTH REPORT - {report.report_type.upper()}")
        print("=" * 80)
        print(f"Report ID: {report.report_id}")
        print(f"Period: {report.period_start} to {report.period_end}")
        print(f"Generated: {report.generated_at}")
        print("=" * 80)

        # Overall Health
        if health.is_critical:
            print(f"\n🚨 OVERALL HEALTH: {health.overall_health_score:.1f}% - CRITICAL")
            print(f"Status: {health.health_level.value.upper()} - SHUTDOWN RISK")
            if health.days_until_shutdown is not None:
                print(f"Days Until Shutdown: {health.days_until_shutdown}")
        else:
            print(f"\nOVERALL HEALTH: {health.overall_health_score:.1f}%")
            print(f"Status: {health.health_level.value.upper()}")

        # Component Scores
        print(f"\nCOMPONENT SCORES:")
        print(f"  User Interaction: {health.interaction_health:.1f}% (Weight: 25%)")
        print(f"  Organic Growth: {health.growth_health:.1f}% (Weight: 20%)")
        print(f"  Platform Balance: {health.balance_health:.1f}% (Weight: 15%)")
        print(f"  Matching Success: {health.matching_health:.1f}% (Weight: 25%)")
        print(f"  Post-Work Impact: {health.impact_health:.1f}% (Weight: 15%)")

        # Critical Issues
        if report.critical_issues:
            print(f"\n🚨 CRITICAL ISSUES ({len(report.critical_issues)}):")
            for issue in report.critical_issues:
                print(f"  - {issue}")

        # Action Items
        if report.action_items:
            print(f"\n📋 ACTION ITEMS ({len(report.action_items)}):")
            for item in report.action_items:
                print(f"  {item}")

        # Master's Assessment
        print(f"\n🤖 MASTER AI ASSESSMENT:")
        print(f"{report.master_assessment}")

        print("\n" + "=" * 80)

        if report.requires_immediate_action:
            print("⚠️  IMMEDIATE ACTION REQUIRED")
            print("=" * 80)


# ============================================================================
# FACTORY FUNCTIONS
# ============================================================================

def create_health_reporting_system() -> HealthReportingSystem:
    """Create health reporting system."""
    return HealthReportingSystem()
