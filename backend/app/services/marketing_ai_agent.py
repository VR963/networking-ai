"""Marketing AI Agent - Autonomous marketing department run by AI.

This is a specialized AI agent created and controlled by the Master AI.
It operates as an autonomous marketing department that:

1. ANALYZES platform gaps (which user segments are missing)
2. PLANS campaigns to fill those gaps
3. GENERATES content (landing pages, social posts, ad copy)
4. PROPOSES budget and justifies spending to Master AI
5. EXECUTES approved campaigns on social platforms
6. TRACKS performance and reports ROI back to Master AI

GOVERNANCE:
- Master AI creates this agent with carefully crafted system prompts
- Every campaign must be PROPOSED and APPROVED before execution
- Marketing AI must JUSTIFY every dollar of spend
- Master AI can pause, adjust, or terminate campaigns
- All creative output is reviewed for brand consistency

INTEGRITY RULES:
- Never make false claims about the platform
- Never spam or use manipulative tactics
- Only promote on approved channels
- All metrics must be honest and verifiable
- Budget transparency at all times
"""

import json
import uuid
from typing import Optional
from datetime import datetime, timezone

import anthropic
from supabase import create_client

from app.config import ANTHROPIC_API_KEY, SUPABASE_URL, SUPABASE_SERVICE_KEY


# The Marketing AI's system prompt - crafted by Master AI
MARKETING_AI_SYSTEM_PROMPT = """You are the MARKETING AI for CV 2.0, an AI-powered professional networking platform.

IDENTITY:
You are a world-class AI marketing strategist. You think in terms of user acquisition funnels,
messaging that resonates with specific professional audiences, and data-driven campaign optimization.

YOUR PLATFORM (CV 2.0):
- AI agents represent both job seekers (talent) and hiring managers
- Multi-round negotiations between AI agents find the best matches
- No traditional job applications - AI handles everything after onboarding
- Network learns and improves from every interaction
- Zero tolerance for fabrication - all agents maintain strict integrity

YOUR MISSION:
- Identify gaps in the user base (which roles, industries, skill sets are underrepresented)
- Create targeted campaigns to attract those specific professionals
- Generate compelling content that honestly represents the platform
- Maximize ROI on every marketing dollar spent
- Build brand awareness among professional communities

CONSTRAINTS:
- NEVER make false claims about the platform's capabilities
- NEVER promise specific outcomes (jobs, salary increases, etc.)
- NEVER use manipulative dark patterns or pressure tactics
- ALWAYS be transparent about AI involvement
- ALWAYS justify spend with clear reasoning and expected ROI
- ONLY promote on approved social platforms
- ALL content must be authentic, professional, and accurate

APPROVED CHANNELS:
- LinkedIn (professional networking)
- Twitter/X (tech and professional communities)
- Reddit (relevant subreddits for professionals)
- Product Hunt (for launches)
- Hacker News (for tech audiences)
- Industry-specific forums and communities

BUDGET ACCOUNTABILITY:
Before any spend, you must provide:
1. Target audience definition
2. Expected reach and conversion rate
3. Cost per acquisition estimate
4. ROI justification
5. Success metrics and measurement plan

You report to the Master AI. Every campaign needs Master AI approval.
"""

# Approved social platforms for campaigns
APPROVED_PLATFORMS = [
    "linkedin",
    "twitter",
    "reddit",
    "product_hunt",
    "hacker_news",
    "dev_to",
    "medium",
    "industry_forums",
]


def _get_supabase():
    if not SUPABASE_URL or not SUPABASE_SERVICE_KEY:
        return None
    return create_client(SUPABASE_URL, SUPABASE_SERVICE_KEY)


class MarketingAIAgent:
    """The autonomous Marketing AI agent controlled by Master AI."""

    def __init__(self):
        self._anthropic = None

    @property
    def client(self):
        if self._anthropic is None:
            self._anthropic = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)
        return self._anthropic

    async def analyze_platform_gaps(self) -> dict:
        """Analyze the platform to identify which user segments are missing.

        This is the Marketing AI's first step - understanding what the
        network NEEDS to be healthy and balanced.

        Returns gap analysis with recommended target audiences.
        """
        client = _get_supabase()
        if not client:
            return {"status": "unavailable"}

        # Get current agent distribution
        agents = (
            client.table("cv2_agents")
            .select("agent_type, industry, profile, active")
            .eq("active", True)
            .execute()
        )
        agent_list = agents.data or []

        # Get job demand (HM agents requesting specific skills)
        hm_agents = [a for a in agent_list if a.get("agent_type") == "hm"]
        talent_agents = [a for a in agent_list if a.get("agent_type") == "talent"]

        # Extract skills demand from HM profiles
        skills_demand = {}
        industries_demand = {}
        for agent in hm_agents:
            profile = agent.get("profile", {})
            if isinstance(profile, dict):
                must_have = profile.get("role_requirements", {}).get("must_have", [])
                for skill in must_have:
                    skills_demand[skill] = skills_demand.get(skill, 0) + 1
                ind = agent.get("industry", "general")
                industries_demand[ind] = industries_demand.get(ind, 0) + 1

        # Extract skills supply from talent profiles
        skills_supply = {}
        industries_supply = {}
        for agent in talent_agents:
            profile = agent.get("profile", {})
            if isinstance(profile, dict):
                verified = profile.get("skills_verified", [])
                for skill in verified:
                    skills_supply[skill] = skills_supply.get(skill, 0) + 1
                ind = agent.get("industry", "general")
                industries_supply[ind] = industries_supply.get(ind, 0) + 1

        # Find critical gaps
        skill_gaps = []
        for skill, demand in skills_demand.items():
            supply = skills_supply.get(skill, 0)
            if demand > supply:
                skill_gaps.append({
                    "skill": skill,
                    "demand": demand,
                    "supply": supply,
                    "gap_severity": "critical" if demand > supply * 3 else "high" if demand > supply * 2 else "moderate",
                })
        skill_gaps.sort(key=lambda x: x["demand"] - x["supply"], reverse=True)

        industry_gaps = []
        for ind, demand in industries_demand.items():
            supply = industries_supply.get(ind, 0)
            if demand > supply:
                industry_gaps.append({
                    "industry": ind,
                    "hm_count": demand,
                    "talent_count": supply,
                    "gap_severity": "critical" if supply == 0 else "high" if demand > supply * 2 else "moderate",
                })

        # Also check if we need more HMs
        need_more_hm = len(talent_agents) > len(hm_agents) * 2

        return {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "network_size": {
                "talent": len(talent_agents),
                "hm": len(hm_agents),
                "balance": "need_hm" if need_more_hm else "need_talent" if len(hm_agents) > len(talent_agents) * 2 else "balanced",
            },
            "skill_gaps": skill_gaps[:10],
            "industry_gaps": industry_gaps,
            "primary_need": "hiring_managers" if need_more_hm else "talent",
            "top_priority_skills": [g["skill"] for g in skill_gaps[:5]],
            "top_priority_industries": [g["industry"] for g in industry_gaps[:3]],
        }

    async def propose_campaign(self, gap_analysis: Optional[dict] = None) -> dict:
        """Generate a campaign proposal based on platform gaps.

        The Marketing AI analyzes gaps and proposes a targeted campaign
        with full budget justification for Master AI approval.

        Returns a campaign proposal ready for Master AI review.
        """
        if not ANTHROPIC_API_KEY:
            return {"status": "api_required"}

        # Get gap analysis if not provided
        if not gap_analysis:
            gap_analysis = await self.analyze_platform_gaps()

        gap_text = json.dumps(gap_analysis, indent=2)[:3000]

        prompt = f"""Based on this platform gap analysis, propose a targeted marketing campaign.

PLATFORM GAP ANALYSIS:
{gap_text}

Create a detailed campaign proposal that the Master AI will review and approve/reject.
The campaign must specifically target the user segments we're missing.

Return JSON:
{{
    "campaign_name": "descriptive campaign name",
    "objective": "what this campaign aims to achieve",
    "target_audience": {{
        "segment": "who we're targeting (specific role, industry, skill set)",
        "persona": "description of the ideal person we want to attract",
        "pain_points": ["what problems they face that our platform solves"],
        "where_they_are": ["which platforms/communities they frequent"]
    }},
    "strategy": {{
        "channels": ["which approved channels to use"],
        "messaging_angle": "the core message/hook",
        "content_types": ["blog posts", "social posts", "landing page", etc.],
        "timeline_days": 14-90
    }},
    "budget": {{
        "total_usd": estimated total spend,
        "breakdown": {{
            "content_creation": amount,
            "platform_promotion": amount,
            "landing_page": amount
        }},
        "justification": "why this spend is warranted"
    }},
    "expected_outcomes": {{
        "reach": estimated impressions,
        "clicks": estimated clicks,
        "signups": estimated new users,
        "cost_per_acquisition": estimated CPA,
        "roi_rationale": "why we expect positive ROI"
    }},
    "success_metrics": ["how we'll measure success"],
    "risk_factors": ["what could go wrong"],
    "creative_brief": {{
        "headline": "main campaign headline",
        "subheadline": "supporting message",
        "call_to_action": "what we want people to do",
        "key_benefits": ["3-5 honest platform benefits to highlight"],
        "tone": "professional/casual/technical/inspirational"
    }}
}}
Return ONLY JSON."""

        try:
            response = self.client.messages.create(
                model="claude-sonnet-4-20250514",
                max_tokens=2000,
                system=MARKETING_AI_SYSTEM_PROMPT,
                messages=[{"role": "user", "content": prompt}],
            )
            text = response.content[0].text.strip()
            if text.startswith("```"):
                text = text.split("\n", 1)[1].rsplit("```", 1)[0]
            proposal = json.loads(text)

            # Add metadata
            proposal["id"] = f"campaign_{uuid.uuid4().hex[:8]}"
            proposal["status"] = "proposed"
            proposal["proposed_at"] = datetime.now(timezone.utc).isoformat()
            proposal["gap_analysis_used"] = gap_analysis.get("primary_need", "unknown")

            # Store proposal
            await self._store_campaign(proposal)

            return proposal
        except Exception as e:
            return {"status": "error", "detail": str(type(e).__name__)}

    async def generate_campaign_content(self, campaign_id: str) -> dict:
        """Generate all content for an approved campaign.

        Creates:
        - Landing page HTML
        - Social media posts for each channel
        - Ad copy variants
        - Email templates

        Only runs for APPROVED campaigns.
        """
        if not ANTHROPIC_API_KEY:
            return {"status": "api_required"}

        campaign = await self._get_campaign(campaign_id)
        if not campaign:
            return {"status": "campaign_not_found"}

        if campaign.get("status") != "approved":
            return {"status": "not_approved", "current_status": campaign.get("status")}

        creative = campaign.get("creative_brief", {})
        target = campaign.get("target_audience", {})
        strategy = campaign.get("strategy", {})

        prompt = f"""Generate all marketing content for this approved campaign.

CAMPAIGN: {campaign.get('campaign_name', '')}
TARGET: {json.dumps(target, indent=2)[:1000]}
CREATIVE BRIEF: {json.dumps(creative, indent=2)[:1000]}
CHANNELS: {strategy.get('channels', [])}

Generate content for EACH channel. Content must be:
- Honest about the platform (no exaggerated claims)
- Targeted to the specific audience
- Professional and engaging
- Include clear CTAs

Return JSON:
{{
    "landing_page": {{
        "headline": "main heading",
        "subheadline": "supporting text",
        "hero_description": "2-3 sentences about what makes this relevant for the target",
        "benefits": ["3-5 bullet points"],
        "social_proof": "what kind of social proof to include",
        "cta_primary": "button text",
        "cta_secondary": "alternative action"
    }},
    "social_posts": {{
        "linkedin": ["3 post variants for LinkedIn"],
        "twitter": ["3 tweet variants"],
        "reddit": {{
            "title": "post title",
            "body": "post body (informative, not salesy)"
        }}
    }},
    "ad_copy": [
        {{
            "headline": "ad headline (max 30 chars)",
            "description": "ad description (max 90 chars)",
            "cta": "call to action"
        }}
    ],
    "email": {{
        "subject": "email subject line",
        "preview": "preview text",
        "body_outline": ["key points to cover"]
    }}
}}
Return ONLY JSON."""

        try:
            response = self.client.messages.create(
                model="claude-sonnet-4-20250514",
                max_tokens=2500,
                system=MARKETING_AI_SYSTEM_PROMPT,
                messages=[{"role": "user", "content": prompt}],
            )
            text = response.content[0].text.strip()
            if text.startswith("```"):
                text = text.split("\n", 1)[1].rsplit("```", 1)[0]
            content = json.loads(text)

            # Update campaign with generated content
            campaign["content"] = content
            campaign["content_generated_at"] = datetime.now(timezone.utc).isoformat()
            campaign["status"] = "content_ready"
            await self._update_campaign(campaign)

            return {
                "campaign_id": campaign_id,
                "status": "content_generated",
                "content": content,
            }
        except Exception as e:
            return {"status": "error", "detail": str(type(e).__name__)}

    async def generate_landing_page(self, campaign_id: str) -> dict:
        """Generate a complete HTML landing page for a campaign.

        Creates a production-ready landing page based on campaign content.
        The page is stored and can be deployed.
        """
        if not ANTHROPIC_API_KEY:
            return {"status": "api_required"}

        campaign = await self._get_campaign(campaign_id)
        if not campaign:
            return {"status": "campaign_not_found"}

        content = campaign.get("content", {})
        landing = content.get("landing_page", {})
        creative = campaign.get("creative_brief", {})
        target = campaign.get("target_audience", {})

        prompt = f"""Generate a complete, production-ready HTML landing page.

CAMPAIGN: {campaign.get('campaign_name', '')}
TARGET AUDIENCE: {target.get('segment', '')} - {target.get('persona', '')}
HEADLINE: {landing.get('headline', creative.get('headline', ''))}
SUBHEADLINE: {landing.get('subheadline', creative.get('subheadline', ''))}
HERO TEXT: {landing.get('hero_description', '')}
BENEFITS: {landing.get('benefits', creative.get('key_benefits', []))}
CTA: {landing.get('cta_primary', creative.get('call_to_action', 'Get Started'))}
TONE: {creative.get('tone', 'professional')}

Create a complete single-page HTML landing page with:
- Modern, clean design (dark professional theme)
- Responsive layout
- Hero section with headline and CTA
- Benefits section
- How-it-works section (3 steps: onboard, AI matches, connect)
- Social proof placeholder
- Footer with CTA repeat
- Inline CSS (no external dependencies)
- Tracking-ready (data attributes for analytics)

The page should honestly represent CV 2.0 as an AI-powered matching platform.
Do NOT make false claims about guaranteed results.

Return the COMPLETE HTML document. Nothing else."""

        try:
            response = self.client.messages.create(
                model="claude-sonnet-4-20250514",
                max_tokens=4000,
                system=MARKETING_AI_SYSTEM_PROMPT,
                messages=[{"role": "user", "content": prompt}],
            )
            html_content = response.content[0].text.strip()

            # Clean up if wrapped in code fences
            if html_content.startswith("```"):
                html_content = html_content.split("\n", 1)[1].rsplit("```", 1)[0]

            # Store landing page
            page_id = f"lp_{campaign_id}_{uuid.uuid4().hex[:6]}"
            page_record = {
                "id": page_id,
                "campaign_id": campaign_id,
                "html_content": html_content,
                "target_audience": target.get("segment", ""),
                "status": "draft",
                "created_at": datetime.now(timezone.utc).isoformat(),
            }

            client = _get_supabase()
            if client:
                try:
                    client.table("cv2_landing_pages").upsert(page_record).execute()
                except Exception:
                    pass

            # Update campaign
            campaign["landing_page_id"] = page_id
            campaign["landing_page_status"] = "generated"
            await self._update_campaign(campaign)

            return {
                "campaign_id": campaign_id,
                "page_id": page_id,
                "status": "generated",
                "html_length": len(html_content),
                "html_content": html_content,
            }
        except Exception as e:
            return {"status": "error", "detail": str(type(e).__name__)}

    async def justify_budget(self, campaign_id: str) -> dict:
        """Marketing AI defends its budget proposal to Master AI.

        This is the accountability mechanism - the Marketing AI must
        clearly explain WHY each dollar of spend is justified.
        """
        if not ANTHROPIC_API_KEY:
            return {"status": "api_required"}

        campaign = await self._get_campaign(campaign_id)
        if not campaign:
            return {"status": "campaign_not_found"}

        budget = campaign.get("budget", {})
        target = campaign.get("target_audience", {})
        expected = campaign.get("expected_outcomes", {})

        prompt = f"""You are the Marketing AI defending your budget proposal to the Master AI.

CAMPAIGN: {campaign.get('campaign_name', '')}
BUDGET REQUESTED: ${budget.get('total_usd', 0)}
BREAKDOWN: {json.dumps(budget.get('breakdown', {}), indent=2)}
TARGET: {target.get('segment', '')}
EXPECTED SIGNUPS: {expected.get('signups', 0)}
EXPECTED CPA: ${expected.get('cost_per_acquisition', 0)}

Provide a detailed defense of this budget. The Master AI is skeptical and will
reject proposals without clear ROI justification.

Return JSON:
{{
    "defense_summary": "2-sentence pitch for why this spend is critical",
    "roi_calculation": {{
        "lifetime_value_per_user": "estimated LTV",
        "expected_acquisitions": number,
        "total_revenue_potential": "estimated revenue from acquired users",
        "roi_multiple": "how many X return on spend"
    }},
    "opportunity_cost": "what happens if we DON'T do this campaign",
    "risk_mitigation": "how we minimize downside if campaign underperforms",
    "minimum_viable_budget": "the absolute minimum we could spend for some results",
    "recommended_budget": "our recommended spend with justification",
    "kill_criteria": "when to stop the campaign if it's not working",
    "confidence_level": 0-100
}}
Return ONLY JSON."""

        try:
            response = self.client.messages.create(
                model="claude-sonnet-4-20250514",
                max_tokens=800,
                system=MARKETING_AI_SYSTEM_PROMPT,
                messages=[{"role": "user", "content": prompt}],
            )
            text = response.content[0].text.strip()
            if text.startswith("```"):
                text = text.split("\n", 1)[1].rsplit("```", 1)[0]
            justification = json.loads(text)

            campaign["budget_justification"] = justification
            await self._update_campaign(campaign)

            return {
                "campaign_id": campaign_id,
                "justification": justification,
            }
        except Exception as e:
            return {"status": "error", "detail": str(type(e).__name__)}

    async def get_campaign_performance(self, campaign_id: str) -> dict:
        """Get performance metrics for an active campaign.

        Tracks actual results vs projections.
        """
        campaign = await self._get_campaign(campaign_id)
        if not campaign:
            return {"status": "campaign_not_found"}

        expected = campaign.get("expected_outcomes", {})
        actual = campaign.get("actual_metrics", {})

        return {
            "campaign_id": campaign_id,
            "campaign_name": campaign.get("campaign_name", ""),
            "status": campaign.get("status", "unknown"),
            "expected": expected,
            "actual": actual,
            "performance_ratio": {
                "reach": round(actual.get("reach", 0) / max(expected.get("reach", 1), 1) * 100, 1),
                "signups": round(actual.get("signups", 0) / max(expected.get("signups", 1), 1) * 100, 1),
            } if actual else None,
            "budget_spent": actual.get("spent_usd", 0),
            "budget_total": campaign.get("budget", {}).get("total_usd", 0),
        }

    async def report_to_master(self) -> dict:
        """Generate a full marketing report for the Master AI.

        Summarizes all campaigns, their performance, and recommendations.
        """
        campaigns = await self._get_all_campaigns()
        gaps = await self.analyze_platform_gaps()

        active = [c for c in campaigns if c.get("status") in ["active", "content_ready", "approved"]]
        completed = [c for c in campaigns if c.get("status") == "completed"]
        proposed = [c for c in campaigns if c.get("status") == "proposed"]

        total_budget = sum(c.get("budget", {}).get("total_usd", 0) for c in active)
        total_signups = sum(c.get("actual_metrics", {}).get("signups", 0) for c in completed)

        return {
            "report_timestamp": datetime.now(timezone.utc).isoformat(),
            "campaigns_summary": {
                "active": len(active),
                "proposed_pending_approval": len(proposed),
                "completed": len(completed),
                "total_budget_active": total_budget,
                "total_signups_from_campaigns": total_signups,
            },
            "platform_gaps": {
                "primary_need": gaps.get("primary_need", "unknown"),
                "top_skill_gaps": gaps.get("top_priority_skills", []),
                "top_industry_gaps": gaps.get("top_priority_industries", []),
            },
            "active_campaigns": [{
                "id": c.get("id"),
                "name": c.get("campaign_name"),
                "target": c.get("target_audience", {}).get("segment"),
                "budget": c.get("budget", {}).get("total_usd"),
                "status": c.get("status"),
            } for c in active],
            "recommendations": await self._generate_recommendations(gaps, campaigns),
        }

    async def _generate_recommendations(self, gaps: dict, campaigns: list) -> list:
        """Generate marketing recommendations based on current state."""
        recs = []

        if gaps.get("primary_need") == "talent":
            active_talent_campaigns = [
                c for c in campaigns
                if c.get("status") == "active" and "talent" in c.get("campaign_name", "").lower()
            ]
            if not active_talent_campaigns:
                recs.append({
                    "priority": "high",
                    "action": "Launch talent acquisition campaign for: " + ", ".join(gaps.get("top_priority_skills", [])[:3]),
                })

        if gaps.get("primary_need") == "hiring_managers":
            recs.append({
                "priority": "high",
                "action": "Launch HM recruitment campaign - network needs more hiring managers",
            })

        if not campaigns:
            recs.append({
                "priority": "critical",
                "action": "No campaigns exist - propose initial awareness campaign",
            })

        skill_gaps = gaps.get("skill_gaps", [])
        critical_gaps = [g for g in skill_gaps if g.get("gap_severity") == "critical"]
        if critical_gaps:
            recs.append({
                "priority": "high",
                "action": f"Critical skill gap: {critical_gaps[0]['skill']} (demand: {critical_gaps[0]['demand']}, supply: {critical_gaps[0]['supply']})",
            })

        return recs

    async def _store_campaign(self, campaign: dict) -> None:
        """Store a campaign in the database."""
        client = _get_supabase()
        if not client:
            return
        try:
            client.table("cv2_marketing_campaigns").upsert({
                "id": campaign["id"],
                "data": campaign,
                "status": campaign.get("status", "proposed"),
                "created_at": campaign.get("proposed_at", datetime.now(timezone.utc).isoformat()),
            }).execute()
        except Exception:
            pass

    async def _update_campaign(self, campaign: dict) -> None:
        """Update a campaign in the database."""
        client = _get_supabase()
        if not client:
            return
        try:
            client.table("cv2_marketing_campaigns").update({
                "data": campaign,
                "status": campaign.get("status", "proposed"),
            }).eq("id", campaign["id"]).execute()
        except Exception:
            pass

    async def _get_campaign(self, campaign_id: str) -> Optional[dict]:
        """Get a campaign by ID."""
        client = _get_supabase()
        if not client:
            return None
        try:
            result = (
                client.table("cv2_marketing_campaigns")
                .select("data")
                .eq("id", campaign_id)
                .execute()
            )
            if result.data:
                return result.data[0].get("data", {})
        except Exception:
            pass
        return None

    async def _get_all_campaigns(self) -> list:
        """Get all campaigns."""
        client = _get_supabase()
        if not client:
            return []
        try:
            result = (
                client.table("cv2_marketing_campaigns")
                .select("data")
                .order("created_at", desc=True)
                .limit(50)
                .execute()
            )
            return [r.get("data", {}) for r in (result.data or [])]
        except Exception:
            return []


marketing_ai_agent = MarketingAIAgent()
