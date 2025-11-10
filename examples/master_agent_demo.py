"""
Master Agent System - Complete End-to-End Demonstration.

This example demonstrates the fully autonomous Master Agent system:

1. Master Agent monitors platform health
2. Master's sub-agents report status (Traffic, Audit, Security, Performance, R&D)
3. Master identifies demand gaps (missing user types)
4. Master creates funding request for marketing campaign
5. Admin reviews and approves request
6. Master instructs Marketing Agent to create campaign
7. Marketing Agent designs and launches campaign
8. Campaign tracks performance and reports to Master
9. Master rewards high-performing agents
10. Master assists underperforming agents
11. Admin views comprehensive dashboard

This demonstrates the complete autonomous AI ecosystem with human oversight.
"""

import os
from datetime import datetime, timedelta

# Set API key
os.environ['ANTHROPIC_API_KEY'] = 'your-api-key-here'

from networking_ai.master_agent import create_master_agent, DemandGap
from networking_ai.marketing_agent import create_marketing_agent, CampaignStatus
from networking_ai.admin_interface import create_admin_interface
from networking_ai.master_sub_agents import create_master_sub_agents
from networking_ai.core import UserProfile


def print_section(title: str):
    """Print section header."""
    print("\n" + "=" * 80)
    print(f"  {title}")
    print("=" * 80)


def main():
    """Run complete Master Agent system demonstration."""

    print("\n" + "🤖" * 40)
    print("MASTER AGENT SYSTEM - FULL DEMONSTRATION")
    print("Autonomous AI Platform with Human Oversight")
    print("🤖" * 40)

    # ========================================================================
    # STEP 1: Initialize System
    # ========================================================================

    print_section("STEP 1: Initialize Master Agent System")

    # Create Master Agent (AI CEO)
    master = create_master_agent()

    # Create Marketing Agent (reports to Master)
    marketing = create_marketing_agent()

    # Create Master's Sub-Agents
    sub_agents = create_master_sub_agents()

    # Create Admin Interface (human oversight)
    admin = create_admin_interface(master, marketing)

    print("\n✅ System initialized successfully!")
    print("   - Master Agent (AI CEO)")
    print("   - Marketing Agent (User Acquisition)")
    print("   - 5 Sub-Agents (Traffic, Audit, Security, Performance, R&D)")
    print("   - Admin Interface (Human Oversight)")

    # ========================================================================
    # STEP 2: Simulate Platform Activity
    # ========================================================================

    print_section("STEP 2: Simulate Platform Activity")

    print("\nRegistering sample agents and simulating interactions...")

    # Register some agents
    agent_ids = ['agent_001', 'agent_002', 'agent_003', 'agent_004', 'agent_005']
    for agent_id in agent_ids:
        master.governance.register_agent(agent_id)

    # Simulate interactions with validation
    print("\nSimulating agent interactions...")

    # Good agent
    from networking_ai.anti_hallucination import ValidationResult, ConfidenceLevel
    good_validation = ValidationResult(
        is_valid=True,
        confidence_level=ConfidenceLevel.HIGH,
        hallucination_flags=[],
        grounding_evidence=[],
        corrections=[],
        risk_score=0.2,
    )

    for i in range(10):
        master.governance.log_interaction(
            agent_id='agent_001',
            query=f"Query {i}",
            response=f"Response {i}",
            validation_result=good_validation,
        )

    # Underperforming agent
    poor_validation = ValidationResult(
        is_valid=False,
        confidence_level=ConfidenceLevel.LOW,
        hallucination_flags=['Exaggeration detected'],
        grounding_evidence=[],
        corrections=['Add uncertainty markers'],
        risk_score=0.8,
    )

    for i in range(5):
        master.governance.log_interaction(
            agent_id='agent_002',
            query=f"Query {i}",
            response=f"Poor response {i}",
            validation_result=poor_validation,
        )

    print("✅ Simulated platform activity completed")

    # ========================================================================
    # STEP 3: Master Monitors Platform
    # ========================================================================

    print_section("STEP 3: Master Agent Monitors Platform")

    health = master.monitor_platform()

    print(f"\nPlatform Health Score: {health['health_score']:.1f}/100")
    print(f"Status: {health['health_status'].upper()}")
    print(f"Active Agents: {health['active_agents']}")
    print(f"Total Interactions: {health['total_interactions']}")

    # ========================================================================
    # STEP 4: Sub-Agents Report to Master
    # ========================================================================

    print_section("STEP 4: Sub-Agents Report Status")

    # Traffic Analyzer
    print("\n📊 TRAFFIC ANALYZER:")
    traffic_metrics = sub_agents['traffic_analyzer'].analyze_current_traffic(
        total_requests=1500,
        unique_users=450,
        active_agents=5,
        avg_response_time=350.5,
        error_rate=0.015,
    )
    print(f"   Pattern: {traffic_metrics.pattern.value}")
    print(f"   Requests: {traffic_metrics.total_requests:,}")

    # Security Agent
    print("\n🔒 SECURITY AGENT:")
    security_report = sub_agents['security_agent'].report_to_master()
    print(f"   Status: {security_report['security_status']}")
    print(f"   Total Incidents: {security_report['total_incidents']}")

    # Audit Agent
    print("\n📋 AUDIT AGENT:")
    audit_report = sub_agents['audit_agent'].report_to_master()
    print(f"   Compliance: {audit_report['compliance_status']}")
    print(f"   Total Issues: {audit_report['total_issues']}")

    # Performance Optimizer
    print("\n⚡ PERFORMANCE OPTIMIZER:")
    perf_metrics = sub_agents['performance_optimizer'].analyze_performance(
        agent_response_times=[250.5, 300.2, 280.1, 320.5, 290.0],
        cache_hits=800,
        cache_misses=200,
        rag_query_times=[120.0, 150.0, 130.0],
        embedding_times=[50.0, 55.0, 52.0],
        total_requests=1000,
    )
    print(f"   Cache Hit Rate: {perf_metrics.cache_hit_rate:.1%}")
    print(f"   Avg Response Time: {perf_metrics.avg_agent_response_time:.2f}ms")

    # R&D Agent
    print("\n🔬 R&D AGENT:")
    rd_report = sub_agents['rd_agent'].report_to_master()
    print(f"   Active Projects: {rd_report['active_projects']}")
    print(f"   Status: {rd_report['status']}")

    # ========================================================================
    # STEP 5: Master Identifies Demand Gap
    # ========================================================================

    print_section("STEP 5: Master Identifies Demand Gap")

    # Simulate recent queries showing demand for ML engineers
    recent_queries = [
        "Looking for machine learning engineer",
        "Need ML expert for project",
        "Seeking data scientist with ML experience",
        "ML engineer wanted",
        "Machine learning specialist needed",
    ]

    # Simulate available profiles (no ML engineers)
    available_profiles = [
        UserProfile(
            user_id="user1",
            name="John Doe",
            skills=["Python", "Web Development"],
            interests=["Backend"],
            bio="Web developer",
            goals=["Career growth"],
        ),
        UserProfile(
            user_id="user2",
            name="Jane Smith",
            skills=["JavaScript", "React"],
            interests=["Frontend"],
            bio="Frontend developer",
            goals=["Learn new frameworks"],
        ),
    ]

    print("\nAnalyzing demand gaps...")
    gaps = master.demand_analyzer.analyze_demand_gaps(
        recent_queries, available_profiles
    )

    if gaps:
        top_gap = gaps[0]
        print(f"\n🎯 DEMAND GAP IDENTIFIED:")
        print(f"   Missing Skill: {top_gap.missing_skill}")
        print(f"   Demand Count: {top_gap.demand_count}")
        print(f"   Priority: {top_gap.priority}")
        print(f"   Target Audience: {top_gap.suggested_target_audience}")

    # ========================================================================
    # STEP 6: Master Requests Funding from Admin
    # ========================================================================

    print_section("STEP 6: Master Requests Marketing Campaign Funding")

    if gaps:
        gap = gaps[0]

        # Master creates funding request
        request = master.request_marketing_campaign(
            target_audience=gap.suggested_target_audience,
            skills_needed=[gap.missing_skill] + gap.related_skills[:2],
            budget=10000.0,
            expected_users=50,
        )

        print(f"\n📤 Master Agent created funding request:")
        print(f"   Request ID: {request.request_id}")
        print(f"   Budget: ${request.data['budget']:,.2f}")
        print(f"   Target: {request.data['target_audience']}")
        print(f"   Expected Users: {request.data['expected_users']}")
        print(f"   Expected ROI: {request.data['expected_roi']:.1%}")

    # ========================================================================
    # STEP 7: Admin Reviews and Approves
    # ========================================================================

    print_section("STEP 7: Admin Reviews and Approves Request")

    # Admin views pending requests
    pending = admin.view_pending_requests()

    if pending:
        print("\n👨‍💼 ADMIN DECISION: Approving request...")

        # Admin approves with notes
        success = admin.approve_request(
            request_id=pending[0].request_id,
            admin_notes="Approved. ML engineers are in high demand. Good ROI projection.",
        )

        if success:
            print("\n✅ Request approved by Admin")
            print("   Master Agent will now execute campaign...")

    # ========================================================================
    # STEP 8: Marketing Agent Executes Campaign
    # ========================================================================

    print_section("STEP 8: Marketing Agent Designs Campaign")

    # Get the created campaign
    campaigns = marketing.get_all_campaigns_summary()

    if campaigns['campaigns']:
        campaign_id = campaigns['campaigns'][0]['id']

        print(f"\n📢 Campaign Details:")
        print(f"   ID: {campaign_id}")
        print(f"   Status: {campaigns['campaigns'][0]['status']}")

        # Find the actual campaign
        campaign = None
        for c in marketing.campaigns:
            if c.campaign_id == campaign_id:
                campaign = c
                break

        if campaign:
            print(f"   Name: {campaign.campaign_name}")
            print(f"   Channels: {', '.join([ch.value for ch in campaign.channels])}")
            print(f"   Duration: {campaign.duration_days} days")
            print(f"   Budget: ${campaign.budget_allocated:,.2f}")

            # Launch campaign
            print("\n🚀 Launching campaign...")
            campaign.status = CampaignStatus.APPROVED
            marketing.launch_campaign(campaign_id)

    # ========================================================================
    # STEP 9: Campaign Runs and Tracks Performance
    # ========================================================================

    print_section("STEP 9: Campaign Performance Tracking")

    if campaigns['campaigns']:
        campaign_id = campaigns['campaigns'][0]['id']

        print("\n⏳ Simulating campaign running for 7 days...")

        # Simulate performance data
        performance = marketing.track_campaign_performance(
            campaign_id=campaign_id,
            impressions=50000,
            clicks=2500,
            conversions=55,  # Exceeded goal of 50!
            cost_spent=8500.0,  # Under budget!
        )

        print(f"\n📊 Campaign Performance:")
        print(f"   Impressions: {performance.impressions:,}")
        print(f"   Clicks: {performance.clicks:,}")
        print(f"   Conversions: {performance.conversions}")
        print(f"   CTR: {performance.click_through_rate:.2f}%")
        print(f"   CVR: {performance.conversion_rate:.2f}%")
        print(f"   CPA: ${performance.cost_per_acquisition:.2f}")
        print(f"   ROI: {performance.roi:.1f}%")

        # Marketing reports to Master
        report = marketing.report_to_master(campaign_id)

        print(f"\n📈 Report to Master:")
        print(f"   Goal Achievement: {report['goal_achievement']:.1f}%")
        print(f"   Budget Remaining: ${report['budget_remaining']:,.2f}")
        print(f"   Recommendation: {report['recommendation']}")

    # ========================================================================
    # STEP 10: Master Rewards High Performers
    # ========================================================================

    print_section("STEP 10: Master Rewards High-Performing Agents")

    # Reward the good agent
    master.reward_high_performers()

    # Get top performers
    top_performers = master.get_top_performers(3)

    print(f"\n🏆 TOP PERFORMERS:")
    for agent_id, score in top_performers:
        print(f"   {agent_id}: {score} points")

    # ========================================================================
    # STEP 11: Master Assists Underperformers
    # ========================================================================

    print_section("STEP 11: Master Assists Underperforming Agents")

    master.assist_underperformers()

    # ========================================================================
    # STEP 12: Admin Views Dashboard
    # ========================================================================

    print_section("STEP 12: Admin Views Comprehensive Dashboard")

    dashboard = admin.view_dashboard()

    # ========================================================================
    # STEP 13: Admin Views Campaign Details
    # ========================================================================

    print_section("STEP 13: Admin Reviews Campaign Results")

    admin.view_campaigns()

    # ========================================================================
    # STEP 14: Generate Executive Summary
    # ========================================================================

    print_section("STEP 14: Executive Summary for Leadership")

    summary = admin.generate_executive_summary()

    # ========================================================================
    # CONCLUSION
    # ========================================================================

    print_section("✅ DEMONSTRATION COMPLETE")

    print("""
🎉 MASTER AGENT SYSTEM SUCCESSFULLY DEMONSTRATED!

Key Achievements:
✅ Master Agent monitored platform autonomously
✅ Sub-agents reported on traffic, security, audit, performance, and R&D
✅ Demand gap identified (ML Engineers needed)
✅ Master requested funding with ROI justification
✅ Admin reviewed and approved request
✅ Marketing Agent designed and launched campaign
✅ Campaign exceeded goals (55/50 users, under budget)
✅ High-performing agents rewarded
✅ Underperforming agents received assistance
✅ Full transparency and human oversight maintained

System Status: FULLY OPERATIONAL

The Master Agent system is a fully autonomous AI ecosystem that:
- Operates independently to maintain platform health
- Identifies opportunities and creates solutions
- Requests human approval only for funding and major decisions
- Monitors and improves all AI agents
- Brings new users to the platform automatically
- Provides complete transparency to human administrators

This is the future of AI platform management! 🚀
""")


if __name__ == "__main__":
    main()
