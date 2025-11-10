"""
Marketing AI Agent - Autonomous Campaign Creator & User Acquisition.

This agent is instructed by the Master Agent to:
- Create marketing campaigns
- Target specific audiences
- Bring new users to the platform
- Track campaign performance
- Optimize spending and ROI
- Report results back to Master
"""

from typing import Dict, List, Optional, Tuple
from datetime import datetime, timedelta
from dataclasses import dataclass, field
from enum import Enum
import json

from langchain_anthropic import ChatAnthropic
from langchain.schema import HumanMessage, SystemMessage

from .config import config


class CampaignStatus(Enum):
    """Campaign status."""
    DRAFT = "draft"
    PENDING_APPROVAL = "pending_approval"
    APPROVED = "approved"
    ACTIVE = "active"
    PAUSED = "paused"
    COMPLETED = "completed"
    CANCELLED = "cancelled"


class CampaignChannel(Enum):
    """Marketing channels."""
    LINKEDIN = "linkedin"
    TWITTER = "twitter"
    FACEBOOK = "facebook"
    GOOGLE_ADS = "google_ads"
    REDDIT = "reddit"
    HACKERNEWS = "hackernews"
    GITHUB = "github"
    STACKOVERFLOW = "stackoverflow"
    TECH_BLOGS = "tech_blogs"
    EMAIL = "email"


@dataclass
class MarketingCampaign:
    """Complete marketing campaign definition."""
    campaign_id: str
    campaign_name: str
    target_audience: str
    target_skills: List[str]
    channels: List[CampaignChannel]
    budget_allocated: float
    budget_spent: float
    expected_users: int
    actual_users: int
    cost_per_user: float
    messaging: Dict[str, str]  # channel -> message
    creative_assets: List[str]
    duration_days: int
    status: CampaignStatus
    start_date: Optional[str] = None
    end_date: Optional[str] = None
    performance_metrics: Dict = field(default_factory=dict)
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())
    created_by: str = "MasterAgent"


@dataclass
class CampaignPerformance:
    """Campaign performance metrics."""
    impressions: int
    clicks: int
    conversions: int
    click_through_rate: float
    conversion_rate: float
    cost_per_click: float
    cost_per_acquisition: float
    roi: float  # Return on investment
    engagement_score: float
    timestamp: str


class MarketingAgent:
    """
    Autonomous Marketing AI Agent.

    Reports to Master Agent and executes marketing campaigns to bring
    new users to the platform based on identified demand gaps.
    """

    def __init__(self, llm: Optional[ChatAnthropic] = None):
        """Initialize Marketing Agent."""
        self.llm = llm or ChatAnthropic(
            model=config.DEFAULT_MODEL,
            temperature=0.7,  # Creative for marketing
        )
        self.campaigns: List[MarketingCampaign] = []
        self.budget_available: float = 0.0
        self.budget_spent: float = 0.0
        self.total_users_acquired: int = 0

        print("[MARKETING AGENT] Initialized and ready for campaigns.")

    def receive_instruction_from_master(
        self,
        target_audience: str,
        skills_needed: List[str],
        budget: float,
        expected_users: int,
        master_notes: Optional[str] = None,
    ) -> MarketingCampaign:
        """
        Receive campaign instruction from Master Agent.

        Args:
            target_audience: Who to target
            skills_needed: Skills to look for
            budget: Campaign budget
            expected_users: Target user count
            master_notes: Additional context from Master

        Returns:
            Created campaign
        """
        print(f"\n[MARKETING AGENT] Instruction received from Master:")
        print(f"  Target: {target_audience}")
        print(f"  Skills: {', '.join(skills_needed)}")
        print(f"  Budget: ${budget:,.2f}")
        print(f"  Goal: {expected_users} new users")

        # Create campaign
        campaign = self._design_campaign(
            target_audience,
            skills_needed,
            budget,
            expected_users,
            master_notes,
        )

        self.campaigns.append(campaign)
        self.budget_available += budget

        print(f"[MARKETING AGENT] Campaign created: {campaign.campaign_name}")
        print(f"  Status: {campaign.status.value}")
        print(f"  Channels: {len(campaign.channels)}")

        return campaign

    def _design_campaign(
        self,
        target_audience: str,
        skills_needed: List[str],
        budget: float,
        expected_users: int,
        master_notes: Optional[str],
    ) -> MarketingCampaign:
        """
        Design complete marketing campaign using AI.

        Args:
            target_audience: Target audience description
            skills_needed: Required skills
            budget: Budget available
            expected_users: Expected user acquisition
            master_notes: Additional context

        Returns:
            Designed campaign
        """
        # Use Claude to design campaign strategy
        campaign_strategy = self._generate_campaign_strategy(
            target_audience, skills_needed, budget, expected_users, master_notes
        )

        # Select optimal channels
        channels = self._select_channels(target_audience, skills_needed, budget)

        # Generate messaging per channel
        messaging = self._generate_messaging(target_audience, skills_needed, channels)

        # Calculate cost per user
        cost_per_user = budget / expected_users if expected_users > 0 else 0

        # Create campaign
        campaign_id = f"CAMP-{datetime.now().strftime('%Y%m%d%H%M%S')}"

        campaign = MarketingCampaign(
            campaign_id=campaign_id,
            campaign_name=f"{target_audience} Acquisition Campaign",
            target_audience=target_audience,
            target_skills=skills_needed,
            channels=channels,
            budget_allocated=budget,
            budget_spent=0.0,
            expected_users=expected_users,
            actual_users=0,
            cost_per_user=cost_per_user,
            messaging=messaging,
            creative_assets=[],
            duration_days=30,  # Default 30-day campaign
            status=CampaignStatus.DRAFT,
        )

        return campaign

    def _generate_campaign_strategy(
        self,
        target_audience: str,
        skills_needed: List[str],
        budget: float,
        expected_users: int,
        master_notes: Optional[str],
    ) -> Dict:
        """Generate campaign strategy using AI."""
        system_prompt = """You are an expert Marketing AI Agent specialized in user acquisition
for professional networking platforms.

Your goal is to design effective campaigns that attract the right users while
optimizing budget and ROI.

Consider:
- Target audience characteristics and behaviors
- Best channels to reach them
- Compelling value propositions
- Budget efficiency
- Conversion optimization"""

        user_prompt = f"""Design a marketing campaign:

Target Audience: {target_audience}
Skills Needed: {', '.join(skills_needed)}
Budget: ${budget:,.2f}
Expected Users: {expected_users}
{f'Master Notes: {master_notes}' if master_notes else ''}

Provide campaign strategy as JSON with:
- value_proposition: String
- key_messages: List of strings
- targeting_criteria: Dict
- success_metrics: List of strings"""

        try:
            messages = [
                SystemMessage(content=system_prompt),
                HumanMessage(content=user_prompt),
            ]

            response = self.llm.invoke(messages)
            content = response.content

            # Parse JSON
            if "```json" in content:
                json_start = content.find("```json") + 7
                json_end = content.find("```", json_start)
                content = content[json_start:json_end].strip()
            elif "```" in content:
                json_start = content.find("```") + 3
                json_end = content.find("```", json_start)
                content = content[json_start:json_end].strip()

            strategy = json.loads(content)

        except Exception as e:
            # Fallback strategy
            strategy = {
                "value_proposition": f"Connect with top {target_audience} professionals",
                "key_messages": [
                    "AI-powered professional networking",
                    "Find connections that matter",
                    "Privacy-first platform"
                ],
                "targeting_criteria": {"skills": skills_needed},
                "success_metrics": ["User signups", "Profile completions", "First connections"]
            }

        return strategy

    def _select_channels(
        self,
        target_audience: str,
        skills_needed: List[str],
        budget: float,
    ) -> List[CampaignChannel]:
        """Select optimal marketing channels based on audience."""
        channels = []

        target_lower = target_audience.lower()
        skills_lower = [s.lower() for s in skills_needed]

        # Tech professionals -> LinkedIn, GitHub, StackOverflow
        if any(word in target_lower for word in ['developer', 'engineer', 'programmer', 'tech']):
            channels.extend([
                CampaignChannel.LINKEDIN,
                CampaignChannel.GITHUB,
                CampaignChannel.STACKOVERFLOW,
            ])

        # Specific tech skills -> Reddit, HackerNews
        if any(skill in skills_lower for skill in ['python', 'javascript', 'ai', 'ml', 'blockchain']):
            channels.extend([
                CampaignChannel.REDDIT,
                CampaignChannel.HACKERNEWS,
            ])

        # Large budget -> Add paid channels
        if budget > 5000:
            channels.extend([
                CampaignChannel.GOOGLE_ADS,
                CampaignChannel.TWITTER,
            ])

        # Always include targeted email
        channels.append(CampaignChannel.EMAIL)

        # Remove duplicates
        channels = list(set(channels))

        return channels[:5]  # Limit to 5 channels

    def _generate_messaging(
        self,
        target_audience: str,
        skills_needed: List[str],
        channels: List[CampaignChannel],
    ) -> Dict[str, str]:
        """Generate channel-specific messaging."""
        messaging = {}

        base_message = f"Join AI-powered networking for {target_audience}. Connect with professionals in {', '.join(skills_needed[:3])}."

        for channel in channels:
            if channel == CampaignChannel.LINKEDIN:
                messaging[channel.value] = f"Professional {target_audience}? Discover intelligent connections on our AI-native platform. {', '.join(skills_needed[:2])} experts welcome!"

            elif channel == CampaignChannel.TWITTER:
                messaging[channel.value] = f"🤖 AI-powered networking for {target_audience}\n🔗 Smart connections, not random follows\n🎯 {skills_needed[0]} community\n👉 Join now"

            elif channel == CampaignChannel.REDDIT:
                messaging[channel.value] = f"Fellow {target_audience} - built an AI networking platform that actually understands {skills_needed[0]}. No spam, just intelligent introductions."

            elif channel == CampaignChannel.HACKERNEWS:
                messaging[channel.value] = f"Show HN: AI-Native Professional Networking for {target_audience}"

            elif channel == CampaignChannel.GITHUB:
                messaging[channel.value] = f"💻 {target_audience} community\n🤖 AI-powered connections\n🔐 Privacy-first\n⭐ {', '.join(skills_needed[:3])}"

            else:
                messaging[channel.value] = base_message

        return messaging

    def launch_campaign(self, campaign_id: str) -> bool:
        """
        Launch an approved campaign.

        Args:
            campaign_id: Campaign to launch

        Returns:
            Success status
        """
        campaign = self._find_campaign(campaign_id)
        if not campaign:
            return False

        if campaign.status != CampaignStatus.APPROVED:
            print(f"[MARKETING AGENT] Campaign {campaign_id} not approved yet")
            return False

        campaign.status = CampaignStatus.ACTIVE
        campaign.start_date = datetime.now().isoformat()
        campaign.end_date = (datetime.now() + timedelta(days=campaign.duration_days)).isoformat()

        print(f"[MARKETING AGENT] Campaign LAUNCHED: {campaign.campaign_name}")
        print(f"  Channels: {', '.join([c.value for c in campaign.channels])}")
        print(f"  Duration: {campaign.duration_days} days")
        print(f"  Budget: ${campaign.budget_allocated:,.2f}")

        return True

    def track_campaign_performance(
        self,
        campaign_id: str,
        impressions: int,
        clicks: int,
        conversions: int,
        cost_spent: float,
    ) -> CampaignPerformance:
        """
        Track campaign performance metrics.

        Args:
            campaign_id: Campaign ID
            impressions: Ad impressions
            clicks: Ad clicks
            conversions: User signups
            cost_spent: Money spent

        Returns:
            Performance metrics
        """
        campaign = self._find_campaign(campaign_id)
        if not campaign:
            return None

        # Calculate metrics
        ctr = (clicks / impressions * 100) if impressions > 0 else 0
        cvr = (conversions / clicks * 100) if clicks > 0 else 0
        cpc = cost_spent / clicks if clicks > 0 else 0
        cpa = cost_spent / conversions if conversions > 0 else 0

        # Calculate ROI (simplified - assumes $100 value per user)
        user_value = conversions * 100
        roi = ((user_value - cost_spent) / cost_spent * 100) if cost_spent > 0 else 0

        # Engagement score (0-100)
        engagement = min(100, (ctr * 10) + (cvr * 20))

        performance = CampaignPerformance(
            impressions=impressions,
            clicks=clicks,
            conversions=conversions,
            click_through_rate=ctr,
            conversion_rate=cvr,
            cost_per_click=cpc,
            cost_per_acquisition=cpa,
            roi=roi,
            engagement_score=engagement,
            timestamp=datetime.now().isoformat(),
        )

        # Update campaign
        campaign.budget_spent += cost_spent
        campaign.actual_users += conversions
        campaign.performance_metrics = {
            'impressions': impressions,
            'clicks': clicks,
            'conversions': conversions,
            'ctr': ctr,
            'cvr': cvr,
            'cpc': cpc,
            'cpa': cpa,
            'roi': roi,
        }

        self.budget_spent += cost_spent
        self.total_users_acquired += conversions

        return performance

    def report_to_master(self, campaign_id: str) -> Dict:
        """
        Generate report for Master Agent.

        Args:
            campaign_id: Campaign to report on

        Returns:
            Campaign report
        """
        campaign = self._find_campaign(campaign_id)
        if not campaign:
            return {'error': 'Campaign not found'}

        performance = campaign.performance_metrics

        report = {
            'campaign_id': campaign.campaign_id,
            'campaign_name': campaign.campaign_name,
            'status': campaign.status.value,
            'target_audience': campaign.target_audience,
            'budget_allocated': campaign.budget_allocated,
            'budget_spent': campaign.budget_spent,
            'budget_remaining': campaign.budget_allocated - campaign.budget_spent,
            'expected_users': campaign.expected_users,
            'actual_users': campaign.actual_users,
            'goal_achievement': (campaign.actual_users / campaign.expected_users * 100) if campaign.expected_users > 0 else 0,
            'performance': performance,
            'recommendation': self._generate_recommendation(campaign, performance),
        }

        print(f"\n[MARKETING AGENT] Report to Master - {campaign.campaign_name}:")
        print(f"  Users Acquired: {campaign.actual_users}/{campaign.expected_users}")
        print(f"  Budget Used: ${campaign.budget_spent:,.2f}/${campaign.budget_allocated:,.2f}")
        print(f"  ROI: {performance.get('roi', 0):.1f}%")

        return report

    def _generate_recommendation(
        self,
        campaign: MarketingCampaign,
        performance: Dict,
    ) -> str:
        """Generate recommendation based on performance."""
        if not performance:
            return "Insufficient data for recommendation"

        roi = performance.get('roi', 0)
        users = campaign.actual_users
        expected = campaign.expected_users

        if users >= expected and roi > 50:
            return "EXCELLENT - Scale up budget for this audience"
        elif users >= expected * 0.8 and roi > 0:
            return "GOOD - Continue campaign with current strategy"
        elif users >= expected * 0.5:
            return "MODERATE - Optimize messaging and channels"
        elif users < expected * 0.3:
            return "POOR - Pause campaign and reassess strategy"
        else:
            return "UNDERPERFORMING - Immediate optimization needed"

    def _find_campaign(self, campaign_id: str) -> Optional[MarketingCampaign]:
        """Find campaign by ID."""
        for campaign in self.campaigns:
            if campaign.campaign_id == campaign_id:
                return campaign
        return None

    def get_all_campaigns_summary(self) -> Dict:
        """Get summary of all campaigns."""
        return {
            'total_campaigns': len(self.campaigns),
            'active_campaigns': len([c for c in self.campaigns if c.status == CampaignStatus.ACTIVE]),
            'total_budget': self.budget_available,
            'total_spent': self.budget_spent,
            'total_users_acquired': self.total_users_acquired,
            'average_cost_per_user': self.budget_spent / self.total_users_acquired if self.total_users_acquired > 0 else 0,
            'campaigns': [
                {
                    'id': c.campaign_id,
                    'name': c.campaign_name,
                    'status': c.status.value,
                    'users': c.actual_users,
                    'budget': c.budget_spent,
                }
                for c in self.campaigns
            ],
        }


def create_marketing_agent() -> MarketingAgent:
    """Factory function to create Marketing Agent."""
    return MarketingAgent()
