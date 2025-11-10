"""
Admin Interface - Human administrator's control panel for the Master Agent.

This interface allows human administrators to:
- Review and approve Master Agent's requests (especially funding)
- Monitor platform health and performance
- View agent performance and campaigns
- Override decisions when necessary
- Manage budgets and allocations
- Access system reports
"""

from typing import Dict, List, Optional, Any
from datetime import datetime
from dataclasses import dataclass
from enum import Enum

from .master_agent import MasterAgent, AdminRequest, RequestStatus, RequestType
from .marketing_agent import MarketingAgent
from .master_sub_agents import create_master_sub_agents


class AdminDecision(Enum):
    """Admin decision types."""
    APPROVED = "approved"
    REJECTED = "rejected"
    PENDING_REVIEW = "pending_review"
    APPROVED_WITH_MODIFICATIONS = "approved_with_modifications"


@dataclass
class AdminAction:
    """Record of admin action."""
    action_id: str
    request_id: str
    decision: AdminDecision
    admin_notes: Optional[str]
    modified_budget: Optional[float]
    timestamp: str


class AdminInterface:
    """
    Administrative control panel for managing the Master Agent system.

    This is the human layer that oversees the fully autonomous AI system.
    Admin primarily approves budgets and monitors health.
    """

    def __init__(
        self,
        master_agent: MasterAgent,
        marketing_agent: MarketingAgent,
        sub_agents: Optional[Dict] = None,
    ):
        """
        Initialize Admin Interface.

        Args:
            master_agent: Master Agent instance
            marketing_agent: Marketing Agent instance
            sub_agents: Optional sub-agents dict
        """
        self.master = master_agent
        self.marketing = marketing_agent
        self.sub_agents = sub_agents or create_master_sub_agents()
        self.action_history: List[AdminAction] = []

        print("\n" + "=" * 70)
        print("ADMIN INTERFACE INITIALIZED")
        print("=" * 70)
        print("You now have control over the Master Agent system.")
        print("Master Agent operates autonomously but requires your approval for:")
        print("  - Budget allocations")
        print("  - Major platform changes")
        print("  - Campaign launches")
        print("=" * 70 + "\n")

    # ========================================================================
    # REQUEST MANAGEMENT
    # ========================================================================

    def view_pending_requests(self) -> List[AdminRequest]:
        """
        View all pending requests from Master Agent.

        Returns:
            List of pending requests
        """
        pending = [
            req for req in self.master.admin_requests
            if req.status == RequestStatus.PENDING
        ]

        if not pending:
            print("\n📋 No pending requests from Master Agent.")
            return []

        print(f"\n📋 PENDING REQUESTS FROM MASTER AGENT ({len(pending)})")
        print("=" * 70)

        for i, req in enumerate(pending, 1):
            print(f"\n{i}. Request ID: {req.request_id}")
            print(f"   Type: {req.request_type.value.upper()}")
            print(f"   Priority: {req.priority}")
            print(f"   Created: {req.created_at}")
            print(f"\n   Master's Request:")
            print(f"   {req.reason}")
            print(f"\n   Expected Impact:")
            print(f"   {req.expected_impact}")

            if req.request_type == RequestType.FUNDING:
                print(f"\n   💰 Budget Requested: ${req.data.get('budget', 0):,.2f}")
                print(f"   📊 Expected ROI: {req.data.get('expected_roi', 0):.1%}")
                print(f"   🎯 Target: {req.data.get('target_audience', 'N/A')}")
                print(f"   👥 Expected Users: {req.data.get('expected_users', 0):,}")

            print("-" * 70)

        return pending

    def approve_request(
        self,
        request_id: str,
        admin_notes: Optional[str] = None,
        modified_budget: Optional[float] = None,
    ) -> bool:
        """
        Approve a request from Master Agent.

        Args:
            request_id: Request to approve
            admin_notes: Optional notes from admin
            modified_budget: Optional modified budget (if different from requested)

        Returns:
            Success status
        """
        # Find request
        request = None
        for req in self.master.admin_requests:
            if req.request_id == request_id:
                request = req
                break

        if not request:
            print(f"\n❌ Request {request_id} not found.")
            return False

        if request.status != RequestStatus.PENDING:
            print(f"\n❌ Request {request_id} is not pending (status: {request.status.value}).")
            return False

        # Approve
        request.status = RequestStatus.APPROVED
        request.admin_response = admin_notes or "Approved by administrator"
        request.approved_at = datetime.now().isoformat()

        # Handle modified budget
        final_budget = modified_budget if modified_budget else request.data.get('budget')
        if modified_budget and request.request_type == RequestType.FUNDING:
            request.data['approved_budget'] = modified_budget

        # Record action
        decision = AdminDecision.APPROVED_WITH_MODIFICATIONS if modified_budget else AdminDecision.APPROVED
        action = AdminAction(
            action_id=f"ADMIN-{datetime.now().strftime('%Y%m%d%H%M%S')}",
            request_id=request_id,
            decision=decision,
            admin_notes=admin_notes,
            modified_budget=modified_budget,
            timestamp=datetime.now().isoformat(),
        )
        self.action_history.append(action)

        print(f"\n✅ REQUEST APPROVED")
        print("=" * 70)
        print(f"Request ID: {request_id}")
        print(f"Type: {request.request_type.value}")

        if request.request_type == RequestType.FUNDING:
            print(f"Budget: ${final_budget:,.2f}")
            print("\n🤖 Master Agent has been notified and will proceed with:")
            print(f"   - Instructing Marketing Agent")
            print(f"   - Launching campaign for {request.data.get('target_audience')}")
            print(f"   - Target: {request.data.get('expected_users')} new users")

            # Automatically instruct Marketing Agent
            self._execute_approved_campaign(request, final_budget)

        print("=" * 70)

        return True

    def reject_request(
        self,
        request_id: str,
        reason: str,
    ) -> bool:
        """
        Reject a request from Master Agent.

        Args:
            request_id: Request to reject
            reason: Reason for rejection

        Returns:
            Success status
        """
        # Find request
        request = None
        for req in self.master.admin_requests:
            if req.request_id == request_id:
                request = req
                break

        if not request:
            print(f"\n❌ Request {request_id} not found.")
            return False

        # Reject
        request.status = RequestStatus.REJECTED
        request.admin_response = reason

        # Record action
        action = AdminAction(
            action_id=f"ADMIN-{datetime.now().strftime('%Y%m%d%H%M%S')}",
            request_id=request_id,
            decision=AdminDecision.REJECTED,
            admin_notes=reason,
            modified_budget=None,
            timestamp=datetime.now().isoformat(),
        )
        self.action_history.append(action)

        print(f"\n❌ REQUEST REJECTED")
        print("=" * 70)
        print(f"Request ID: {request_id}")
        print(f"Reason: {reason}")
        print("=" * 70)

        return True

    def _execute_approved_campaign(self, request: AdminRequest, budget: float):
        """
        Execute approved campaign by instructing Marketing Agent.

        Args:
            request: Approved request
            budget: Approved budget
        """
        if request.request_type != RequestType.FUNDING:
            return

        # Master instructs Marketing Agent
        campaign = self.marketing.receive_instruction_from_master(
            target_audience=request.data.get('target_audience'),
            skills_needed=request.data.get('skills_needed', []),
            budget=budget,
            expected_users=request.data.get('expected_users'),
            master_notes=request.reason,
        )

        # Auto-approve campaign (since admin already approved budget)
        campaign.status = self.marketing_agent.CampaignStatus.APPROVED

        print(f"\n✅ Campaign Created: {campaign.campaign_name}")
        print(f"   Campaign ID: {campaign.campaign_id}")
        print(f"   Channels: {len(campaign.channels)}")

    # ========================================================================
    # DASHBOARD & MONITORING
    # ========================================================================

    def view_dashboard(self) -> Dict:
        """
        View comprehensive admin dashboard.

        Returns:
            Dashboard data
        """
        print("\n" + "=" * 70)
        print("🎛️  ADMIN DASHBOARD")
        print("=" * 70)

        # Platform Health
        health = self.master.monitor_platform()
        print(f"\n📊 PLATFORM HEALTH: {health['health_status'].upper()}")
        print(f"   Score: {health['health_score']:.1f}/100")
        print(f"   Active Agents: {health['active_agents']}")
        print(f"   Total Interactions: {health['total_interactions']:,}")

        # Agent Performance
        top_performers = self.master.get_top_performers(5)
        print(f"\n🏆 TOP PERFORMING AGENTS ({len(top_performers)})")
        for agent_id, score in top_performers:
            print(f"   - {agent_id}: {score} points")

        # Budget Status
        campaigns = self.marketing.get_all_campaigns_summary()
        print(f"\n💰 BUDGET & CAMPAIGNS")
        print(f"   Total Budget Allocated: ${campaigns['total_budget']:,.2f}")
        print(f"   Total Spent: ${campaigns['total_spent']:,.2f}")
        print(f"   Active Campaigns: {campaigns['active_campaigns']}")
        print(f"   Total Users Acquired: {campaigns['total_users_acquired']:,}")
        if campaigns['total_users_acquired'] > 0:
            print(f"   Avg Cost per User: ${campaigns['average_cost_per_user']:,.2f}")

        # Pending Requests
        pending_count = len([r for r in self.master.admin_requests if r.status == RequestStatus.PENDING])
        print(f"\n📋 PENDING REQUESTS: {pending_count}")

        # Sub-Agents Status
        print(f"\n🤖 SUB-AGENTS STATUS")

        # Traffic
        traffic_report = self.sub_agents['traffic_analyzer'].report_to_master()
        if 'current_metrics' in traffic_report:
            print(f"   Traffic: {traffic_report['status']}")

        # Security
        security_report = self.sub_agents['security_agent'].report_to_master()
        print(f"   Security: {security_report['security_status']}")

        # Audit
        audit_report = self.sub_agents['audit_agent'].report_to_master()
        print(f"   Compliance: {audit_report['compliance_status']}")

        # Performance
        perf_report = self.sub_agents['performance_optimizer'].report_to_master()
        if 'status' in perf_report:
            print(f"   Performance: {perf_report['status']}")

        print("\n" + "=" * 70)

        return {
            "health": health,
            "campaigns": campaigns,
            "pending_requests": pending_count,
            "sub_agents": {
                "traffic": traffic_report,
                "security": security_report,
                "audit": audit_report,
                "performance": perf_report,
            },
        }

    def view_agent_performance(self, agent_id: Optional[str] = None) -> Dict:
        """
        View detailed agent performance.

        Args:
            agent_id: Optional specific agent ID

        Returns:
            Performance data
        """
        if agent_id:
            performance = self.master.governance.get_agent_performance(agent_id)

            if not performance:
                print(f"\n❌ No performance data for agent: {agent_id}")
                return {}

            print(f"\n📊 AGENT PERFORMANCE: {agent_id}")
            print("=" * 70)
            print(f"Status: {performance['status'].value}")
            print(f"Interactions: {performance['total_interactions']}")
            print(f"Accuracy Rate: {performance['accuracy_rate']:.1%}")
            print(f"Avg Confidence: {performance['avg_confidence']:.2f}")
            print(f"Hallucinations: {performance['hallucination_count']}")
            print(f"Warnings: {performance['warnings']}")
            print("=" * 70)

            return performance

        else:
            # Show all agents
            all_agents = self.master.governance.agents.keys()

            print(f"\n📊 ALL AGENT PERFORMANCE ({len(all_agents)} agents)")
            print("=" * 70)

            performance_data = {}
            for aid in all_agents:
                perf = self.master.governance.get_agent_performance(aid)
                if perf:
                    print(f"\n{aid}:")
                    print(f"  Status: {perf['status'].value}")
                    print(f"  Accuracy: {perf['accuracy_rate']:.1%}")
                    print(f"  Interactions: {perf['total_interactions']}")
                    performance_data[aid] = perf

            print("=" * 70)

            return performance_data

    def view_campaigns(self) -> Dict:
        """
        View all marketing campaigns.

        Returns:
            Campaign data
        """
        summary = self.marketing.get_all_campaigns_summary()

        print(f"\n📢 MARKETING CAMPAIGNS ({summary['total_campaigns']} total)")
        print("=" * 70)

        for campaign in summary['campaigns']:
            print(f"\n{campaign['name']}")
            print(f"  ID: {campaign['id']}")
            print(f"  Status: {campaign['status']}")
            print(f"  Users Acquired: {campaign['users']:,}")
            print(f"  Budget Spent: ${campaign['budget']:,.2f}")

        print("\n" + "=" * 70)
        print(f"SUMMARY:")
        print(f"  Total Budget: ${summary['total_budget']:,.2f}")
        print(f"  Total Spent: ${summary['total_spent']:,.2f}")
        print(f"  Total Users: {summary['total_users_acquired']:,}")
        print(f"  Active Campaigns: {summary['active_campaigns']}")
        print("=" * 70)

        return summary

    def view_security_report(self) -> Dict:
        """
        View detailed security report.

        Returns:
            Security report
        """
        report = self.sub_agents['security_agent'].generate_security_report()

        print(f"\n🔒 SECURITY REPORT")
        print("=" * 70)
        print(f"Status: {report['security_status'].upper()}")
        print(f"Total Incidents: {report['total_incidents']}")
        print(f"Critical Incidents: {report['critical_incidents']}")
        print(f"Unmitigated: {report['unmitigated_incidents']}")
        print(f"Blocked IPs: {report['blocked_ips']}")

        if report['incidents_by_type']:
            print(f"\nIncidents by Type:")
            for threat_type, count in report['incidents_by_type'].items():
                print(f"  - {threat_type}: {count}")

        print(f"\nRecommendation: {report['recommendation']}")
        print("=" * 70)

        return report

    def view_audit_report(self) -> Dict:
        """
        View detailed audit report.

        Returns:
            Audit report
        """
        report = self.sub_agents['audit_agent'].generate_compliance_report()

        print(f"\n📋 COMPLIANCE AUDIT REPORT")
        print("=" * 70)
        print(f"Status: {report['compliance_status'].upper()}")
        print(f"Total Issues: {report['total_issues']}")
        print(f"Critical Issues: {report['critical_issues']}")
        print(f"Unresolved: {report['unresolved_issues']}")

        if report['issues_by_category']:
            print(f"\nIssues by Category:")
            for category, count in report['issues_by_category'].items():
                print(f"  - {category}: {count}")

        print(f"\nRecommendation: {report['recommendation']}")
        print("=" * 70)

        return report

    # ========================================================================
    # OVERRIDES & CONTROLS
    # ========================================================================

    def override_agent_suspension(self, agent_id: str, reason: str) -> bool:
        """
        Override Master's decision to suspend an agent.

        Args:
            agent_id: Agent to reinstate
            reason: Override reason

        Returns:
            Success status
        """
        if agent_id not in self.master.governance.agents:
            print(f"\n❌ Agent {agent_id} not found.")
            return False

        agent_record = self.master.governance.agents[agent_id]

        # Reset status
        from .master_agent import AgentStatus
        agent_record.status = AgentStatus.ACTIVE
        agent_record.warnings = 0

        print(f"\n✅ AGENT REINSTATED")
        print("=" * 70)
        print(f"Agent: {agent_id}")
        print(f"Status: ACTIVE")
        print(f"Override Reason: {reason}")
        print("=" * 70)

        return True

    def set_platform_budget(self, budget: float):
        """
        Set overall platform marketing budget.

        Args:
            budget: Total budget available
        """
        print(f"\n💰 PLATFORM BUDGET SET")
        print("=" * 70)
        print(f"Total Marketing Budget: ${budget:,.2f}")
        print("Master Agent can now request funding up to this amount.")
        print("=" * 70)

    # ========================================================================
    # REPORTS & EXPORTS
    # ========================================================================

    def generate_executive_summary(self) -> Dict:
        """
        Generate executive summary for leadership.

        Returns:
            Executive summary
        """
        health = self.master.monitor_platform()
        campaigns = self.marketing.get_all_campaigns_summary()
        security = self.sub_agents['security_agent'].generate_security_report()
        audit = self.sub_agents['audit_agent'].generate_compliance_report()

        summary = {
            "timestamp": datetime.now().isoformat(),
            "platform_health": {
                "score": health['health_score'],
                "status": health['health_status'],
            },
            "user_acquisition": {
                "total_users_acquired": campaigns['total_users_acquired'],
                "active_campaigns": campaigns['active_campaigns'],
                "total_spent": campaigns['total_spent'],
                "avg_cost_per_user": campaigns['average_cost_per_user'],
            },
            "security_status": security['security_status'],
            "compliance_status": audit['compliance_status'],
            "pending_admin_actions": len([r for r in self.master.admin_requests if r.status == RequestStatus.PENDING]),
        }

        print(f"\n📊 EXECUTIVE SUMMARY")
        print("=" * 70)
        print(f"Generated: {summary['timestamp']}")
        print(f"\nPlatform Health: {summary['platform_health']['status'].upper()} ({summary['platform_health']['score']:.1f}/100)")
        print(f"Users Acquired: {summary['user_acquisition']['total_users_acquired']:,}")
        print(f"Marketing Spend: ${summary['user_acquisition']['total_spent']:,.2f}")
        print(f"Security: {summary['security_status'].upper()}")
        print(f"Compliance: {summary['compliance_status'].upper()}")
        print(f"Pending Actions: {summary['pending_admin_actions']}")
        print("=" * 70)

        return summary


# ============================================================================
# FACTORY FUNCTION
# ============================================================================

def create_admin_interface(
    master_agent: MasterAgent,
    marketing_agent: MarketingAgent,
) -> AdminInterface:
    """
    Create Admin Interface.

    Args:
        master_agent: Master Agent instance
        marketing_agent: Marketing Agent instance

    Returns:
        Configured AdminInterface
    """
    return AdminInterface(master_agent, marketing_agent)
