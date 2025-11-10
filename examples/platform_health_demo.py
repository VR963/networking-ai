"""
Platform Health System - Critical Threshold Demonstration.

This example demonstrates the Master AI's primary responsibility:
KEEPING THE NETWORK ALIVE AND MANAGEABLE.

CRITICAL THRESHOLD: 69%
- Below 69% = Platform facing SHUTDOWN
- Master AI must prevent this at all costs
- Daily, Weekly, Monthly, and Quarterly reports required

Health is calculated from:
1. User interaction with AI agents (25% weight)
2. Organic growth of platform (20% weight)
3. Balance between users and companies (15% weight)
4. Supply/demand matching success (25% weight)
5. Post-work impact (15% weight)
"""

import os
from datetime import datetime, timedelta

# Set API key
os.environ['ANTHROPIC_API_KEY'] = 'your-api-key-here'

from networking_ai.platform_health_system import (
    UserInteractionMetrics,
    OrganicGrowthMetrics,
    BalanceMetrics,
    MatchingSuccessMetrics,
    PostWorkImpactMetrics,
    PlatformHealthCalculator,
    HealthReportingSystem,
    CRITICAL_THRESHOLD,
    ACCEPTABLE_THRESHOLD,
    HealthLevel,
)


def print_section(title: str):
    """Print section header."""
    print("\n" + "=" * 80)
    print(f"  {title}")
    print("=" * 80)


def scenario_healthy_platform():
    """Scenario 1: Healthy platform operation."""
    print_section("SCENARIO 1: Healthy Platform (Above 75%)")

    # Create healthy metrics
    interaction = UserInteractionMetrics(
        total_users=10000,
        active_users_daily=3500,
        active_users_weekly=5500,
        active_users_monthly=7500,
        users_with_agent_interactions=6500,
        avg_interactions_per_user=8.5,
        user_satisfaction_score=82.0,
        agent_response_quality_score=88.0,
        timestamp=datetime.now().isoformat(),
    )

    growth = OrganicGrowthMetrics(
        new_users_today=45,
        new_users_this_week=320,
        new_users_this_month=1250,
        new_users_this_quarter=3800,
        referral_signups=450,
        organic_signups=900,
        paid_campaign_signups=350,
        user_retention_rate=0.78,
        growth_rate_monthly=12.5,
        churn_rate_monthly=3.2,
        timestamp=datetime.now().isoformat(),
    )

    balance = BalanceMetrics(
        total_individual_users=8500,
        total_companies=175,
        active_job_seekers=3200,
        active_job_posters=140,
        jobs_posted_this_month=580,
        applications_this_month=8900,
        timestamp=datetime.now().isoformat(),
    )

    matching = MatchingSuccessMetrics(
        total_matches_attempted=1200,
        successful_matches=850,
        interviews_scheduled=520,
        offers_made=240,
        offers_accepted=195,
        candidates_placed=185,
        avg_time_to_match_days=12.5,
        match_quality_score=84.0,
        timestamp=datetime.now().isoformat(),
    )

    impact = PostWorkImpactMetrics(
        successful_placements_total=185,
        placements_still_employed_30_days=172,
        placements_still_employed_90_days=158,
        avg_employee_satisfaction=86.0,
        avg_employer_satisfaction=88.0,
        repeat_hiring_rate=0.68,
        candidate_referral_rate=0.42,
        platform_nps_score=55.0,
        timestamp=datetime.now().isoformat(),
    )

    # Calculate health
    calculator = PlatformHealthCalculator()
    health = calculator.calculate_health(
        interaction, growth, balance, matching, impact
    )

    # Generate report
    reporting = HealthReportingSystem()
    report = reporting.generate_report('daily', health)

    # Print report
    reporting.print_report(report)

    return health


def scenario_approaching_critical():
    """Scenario 2: Approaching critical threshold (70-74%)."""
    print_section("SCENARIO 2: Approaching Critical Threshold (70-74%)")

    # Declining metrics
    interaction = UserInteractionMetrics(
        total_users=10000,
        active_users_daily=2100,  # Dropping
        active_users_weekly=3800,
        active_users_monthly=5200,
        users_with_agent_interactions=4200,  # Only 42%
        avg_interactions_per_user=4.8,  # Lower
        user_satisfaction_score=68.0,  # Declining
        agent_response_quality_score=71.0,
        timestamp=datetime.now().isoformat(),
    )

    growth = OrganicGrowthMetrics(
        new_users_today=18,  # Slowing
        new_users_this_week=110,
        new_users_this_month=380,
        new_users_this_quarter=1200,
        referral_signups=95,
        organic_signups=180,  # Low organic
        paid_campaign_signups=200,  # Relying on paid
        user_retention_rate=0.58,  # Poor retention
        growth_rate_monthly=3.8,  # Slow growth
        churn_rate_monthly=4.5,  # High churn
        timestamp=datetime.now().isoformat(),
    )

    balance = BalanceMetrics(
        total_individual_users=8800,
        total_companies=120,  # Companies leaving
        active_job_seekers=4200,
        active_job_posters=75,  # Low activity
        jobs_posted_this_month=220,  # Dropping
        applications_this_month=4100,
        timestamp=datetime.now().isoformat(),
    )

    matching = MatchingSuccessMetrics(
        total_matches_attempted=950,
        successful_matches=480,  # Only 50%
        interviews_scheduled=185,
        offers_made=72,
        offers_accepted=48,
        candidates_placed=42,  # Low placements
        avg_time_to_match_days=28.5,  # Slow
        match_quality_score=62.0,  # Poor quality
        timestamp=datetime.now().isoformat(),
    )

    impact = PostWorkImpactMetrics(
        successful_placements_total=42,
        placements_still_employed_30_days=32,
        placements_still_employed_90_days=24,
        avg_employee_satisfaction=64.0,
        avg_employer_satisfaction=66.0,
        repeat_hiring_rate=0.38,  # Low loyalty
        candidate_referral_rate=0.22,
        platform_nps_score=12.0,  # Low NPS
        timestamp=datetime.now().isoformat(),
    )

    # Calculate health
    calculator = PlatformHealthCalculator()
    health = calculator.calculate_health(
        interaction, growth, balance, matching, impact
    )

    # Generate report
    reporting = HealthReportingSystem()
    report = reporting.generate_report('weekly', health)

    # Print report
    reporting.print_report(report)

    print("\n⚠️  WARNING: Platform health approaching critical threshold!")
    print(f"Current: {health.overall_health_score:.1f}%")
    print(f"Critical Threshold: {CRITICAL_THRESHOLD}%")
    print(f"Buffer: {health.overall_health_score - CRITICAL_THRESHOLD:.1f} points")

    return health


def scenario_critical_shutdown_risk():
    """Scenario 3: CRITICAL - Below 69% threshold."""
    print_section("SCENARIO 3: 🚨 CRITICAL - SHUTDOWN RISK (Below 69%)")

    # Critical metrics
    interaction = UserInteractionMetrics(
        total_users=10000,
        active_users_daily=850,  # Very low
        active_users_weekly=1800,
        active_users_monthly=3200,
        users_with_agent_interactions=2100,  # Only 21%!
        avg_interactions_per_user=2.1,  # Minimal
        user_satisfaction_score=48.0,  # Poor
        agent_response_quality_score=52.0,
        timestamp=datetime.now().isoformat(),
    )

    growth = OrganicGrowthMetrics(
        new_users_today=4,  # Nearly stopped
        new_users_this_week=22,
        new_users_this_month=85,  # Critical
        new_users_this_quarter=320,
        referral_signups=12,
        organic_signups=28,  # Almost no organic
        paid_campaign_signups=60,
        user_retention_rate=0.32,  # Terrible
        growth_rate_monthly=0.85,  # Stagnant
        churn_rate_monthly=8.2,  # High churn!
        timestamp=datetime.now().isoformat(),
    )

    balance = BalanceMetrics(
        total_individual_users=7200,  # Users leaving
        total_companies=58,  # Companies fled
        active_job_seekers=1800,
        active_job_posters=22,  # Almost none
        jobs_posted_this_month=45,  # Critical low
        applications_this_month=680,
        timestamp=datetime.now().isoformat(),
    )

    matching = MatchingSuccessMetrics(
        total_matches_attempted=380,
        successful_matches=95,  # Only 25%!
        interviews_scheduled=28,
        offers_made=8,
        offers_accepted=4,
        candidates_placed=3,  # Almost none
        avg_time_to_match_days=45.0,  # Very slow
        match_quality_score=38.0,  # Poor
        timestamp=datetime.now().isoformat(),
    )

    impact = PostWorkImpactMetrics(
        successful_placements_total=3,
        placements_still_employed_30_days=2,
        placements_still_employed_90_days=1,
        avg_employee_satisfaction=42.0,
        avg_employer_satisfaction=38.0,
        repeat_hiring_rate=0.12,  # No loyalty
        candidate_referral_rate=0.05,
        platform_nps_score=-28.0,  # Negative NPS!
        timestamp=datetime.now().isoformat(),
    )

    # Calculate health
    calculator = PlatformHealthCalculator()
    health = calculator.calculate_health(
        interaction, growth, balance, matching, impact
    )

    # Generate emergency report
    reporting = HealthReportingSystem()
    report = reporting.generate_report('daily', health)

    # Print report
    reporting.print_report(report)

    print("\n" + "🚨" * 40)
    print("EMERGENCY STATUS: PLATFORM SHUTDOWN RISK")
    print("🚨" * 40)
    print(f"\nPlatform health: {health.overall_health_score:.1f}%")
    print(f"Critical threshold: {CRITICAL_THRESHOLD}%")
    print(f"BELOW THRESHOLD BY: {CRITICAL_THRESHOLD - health.overall_health_score:.1f} POINTS")
    print("\nUsers are NOT effectively benefiting from AI agents.")
    print("Overall process is at risk of FAILURE.")
    print("\n⚠️  IMMEDIATE INTERVENTION REQUIRED")
    print("⚠️  ALL STRATEGIC RESOURCES MUST FOCUS ON RECOVERY")
    print("⚠️  MASTER AI MUST TAKE EMERGENCY ACTIONS")
    print("🚨" * 40)

    return health


def scenario_recovery_plan():
    """Scenario 4: Master AI implements recovery plan."""
    print_section("SCENARIO 4: Master AI Recovery Plan")

    print("""
🤖 MASTER AI RECOVERY STRATEGY

Based on critical health assessment, implementing emergency recovery plan:

PHASE 1: IMMEDIATE ACTIONS (Days 1-7)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
1. User Interaction Crisis (Score: 42%)
   Action: Emergency agent retraining
   - Suspend underperforming agents immediately
   - Deploy fact-checker to ALL responses
   - Implement response quality monitoring
   Target: Increase to 60% within 7 days

2. Matching Failure (Score: 38%)
   Action: Algorithm emergency fix
   - Review and optimize matching logic
   - Deploy additional matching agents
   - Implement success tracking
   Target: Increase to 55% within 7 days

3. Growth Collapse (Score: 48%)
   Action: Emergency marketing campaign
   - Request $50,000 emergency budget from Admin
   - Launch multi-channel acquisition campaign
   - Focus on high-quality user acquisition
   Target: 500 new users in 7 days

PHASE 2: STABILIZATION (Days 8-30)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
4. Platform Balance Restoration (Score: 52%)
   Action: Targeted company recruitment
   - Launch B2B sales campaign
   - Offer incentives to returning companies
   - Create company success stories
   Target: 100 active companies within 30 days

5. Impact Improvement (Score: 54%)
   Action: Post-placement support
   - Implement 30/60/90 day check-ins
   - Create support resources for placements
   - Gather and act on feedback
   Target: 75% retention at 30 days

PHASE 3: GROWTH RESTORATION (Days 31-90)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
6. Overall Health Recovery
   Target: Restore platform health above 75%
   - Sustained organic growth
   - High user satisfaction
   - Successful matching outcomes
   - Strong retention and impact

BUDGET REQUEST TO ADMIN
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Emergency Budget: $150,000
- Marketing campaigns: $80,000
- Agent improvements: $30,000
- Platform features: $20,000
- Support infrastructure: $20,000

Expected Outcome:
- Restore health above 75% within 90 days
- Prevent platform shutdown
- Return to sustainable growth

ROI Justification:
Platform shutdown cost: $10M+ (lost investment, reputation)
Recovery cost: $150K
ROI: 66x return on investment

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
⚠️  TIME SENSITIVE: Admin approval required within 24 hours
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
""")


def scenario_quarterly_report():
    """Scenario 5: Quarterly health report."""
    print_section("SCENARIO 5: Quarterly Health Report")

    # Healthy metrics for quarterly review
    interaction = UserInteractionMetrics(
        total_users=12500,
        active_users_daily=4200,
        active_users_weekly=6800,
        active_users_monthly=9200,
        users_with_agent_interactions=8100,
        avg_interactions_per_user=12.3,
        user_satisfaction_score=88.0,
        agent_response_quality_score=91.0,
        timestamp=datetime.now().isoformat(),
    )

    growth = OrganicGrowthMetrics(
        new_users_today=68,
        new_users_this_week=480,
        new_users_this_month=1850,
        new_users_this_quarter=5400,
        referral_signups=1200,
        organic_signups=2800,
        paid_campaign_signups=1400,
        user_retention_rate=0.84,
        growth_rate_monthly=14.8,
        churn_rate_monthly=2.1,
        timestamp=datetime.now().isoformat(),
    )

    balance = BalanceMetrics(
        total_individual_users=10800,
        total_companies=220,
        active_job_seekers=4200,
        active_job_posters=185,
        jobs_posted_this_month=820,
        applications_this_month=14500,
        timestamp=datetime.now().isoformat(),
    )

    matching = MatchingSuccessMetrics(
        total_matches_attempted=1850,
        successful_matches=1380,
        interviews_scheduled=880,
        offers_made=420,
        offers_accepted=345,
        candidates_placed=328,
        avg_time_to_match_days=9.5,
        match_quality_score=89.0,
        timestamp=datetime.now().isoformat(),
    )

    impact = PostWorkImpactMetrics(
        successful_placements_total=328,
        placements_still_employed_30_days=310,
        placements_still_employed_90_days=288,
        avg_employee_satisfaction=89.0,
        avg_employer_satisfaction=91.0,
        repeat_hiring_rate=0.78,
        candidate_referral_rate=0.58,
        platform_nps_score=68.0,
        timestamp=datetime.now().isoformat(),
    )

    # Calculate health
    calculator = PlatformHealthCalculator()
    health = calculator.calculate_health(
        interaction, growth, balance, matching, impact
    )

    # Generate quarterly report
    reporting = HealthReportingSystem()
    report = reporting.generate_report('quarterly', health)

    # Print report
    reporting.print_report(report)

    print("\n✅ PLATFORM STATUS: EXCELLENT")
    print(f"Health Score: {health.overall_health_score:.1f}% (Well above {CRITICAL_THRESHOLD}% threshold)")
    print("No immediate action required.")
    print("Platform is thriving and sustainable.")


def main():
    """Run all health system scenarios."""

    print("\n" + "🤖" * 40)
    print("PLATFORM HEALTH SYSTEM DEMONSTRATION")
    print("Master AI's Primary Responsibility: Keep the Network Alive")
    print(f"Critical Threshold: {CRITICAL_THRESHOLD}% - Below this = SHUTDOWN")
    print("🤖" * 40)

    # Scenario 1: Healthy platform
    health1 = scenario_healthy_platform()
    input("\n[Press Enter to continue to Scenario 2...]")

    # Scenario 2: Approaching critical
    health2 = scenario_approaching_critical()
    input("\n[Press Enter to continue to Scenario 3...]")

    # Scenario 3: CRITICAL - Below threshold
    health3 = scenario_critical_shutdown_risk()
    input("\n[Press Enter to see Master AI recovery plan...]")

    # Scenario 4: Recovery plan
    scenario_recovery_plan()
    input("\n[Press Enter to continue to Scenario 5...]")

    # Scenario 5: Quarterly report (recovered)
    health5 = scenario_quarterly_report()

    # Final summary
    print_section("DEMONSTRATION COMPLETE")

    print("""
✅ PLATFORM HEALTH SYSTEM SUCCESSFULLY DEMONSTRATED

Key Capabilities Shown:
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
1. Comprehensive Health Calculation
   - User interaction with AI agents (25%)
   - Organic platform growth (20%)
   - User/company balance (15%)
   - Supply/demand matching success (25%)
   - Post-work impact (15%)

2. Critical Threshold Detection
   - 69% threshold enforced
   - Automatic emergency alerts
   - Shutdown risk assessment

3. Automated Reporting
   - Daily reports
   - Weekly reports
   - Monthly reports
   - Quarterly reports
   - AI-generated strategic assessments

4. Master AI Autonomy
   - Monitors health continuously
   - Generates alerts and recommendations
   - Creates recovery plans
   - Requests emergency budgets
   - Takes corrective actions

5. Admin Oversight
   - Receives regular health reports
   - Approves emergency budgets
   - Monitors Master AI decisions
   - Can override when necessary

The Master AI's primary responsibility is to PREVENT platform health
from falling below 69% and to nurture the network ecosystem for long-term
sustainability and success.

Platform health is the ultimate measure of whether users are effectively
benefiting from AI agents and whether the overall process is succeeding.
""")


if __name__ == "__main__":
    main()
