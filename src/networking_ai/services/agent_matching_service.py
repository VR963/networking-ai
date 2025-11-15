"""
Agent Matching Service - Phase 2 + Phase 3 Week 1.

Performs semantic matching between:
- Talent Personal Agents (with personal RAG)
- Job Postings (Company AI Agents with dual RAG access)

Now includes real-time WebSocket notifications for new matches.

Matching Strategy:
1. Query Talent Personal Agent RAG for candidate profile
2. Query Job RAG (includes HM preferences + company culture)
3. Perform semantic similarity matching
4. Score on multiple dimensions (skills, preferences, culture)
5. Generate AI explanation for why it's a match
6. Broadcast new match via WebSocket (Phase 3)
"""

import os
from typing import List, Dict, Optional
from datetime import datetime, timedelta
from sqlalchemy.orm import Session
from langchain_anthropic import ChatAnthropic
import asyncio

from ..models.user import User
from ..models.personal_ai_agent import PersonalAIAgent, AgentType
from ..models.job import Job, JobStatus
from ..models.match import Match, MatchStatus
from ..models.company_v2 import CompanyV2 as Company
from .chromadb_service import create_chromadb_service, ChromaDBService


class AgentMatchingService:
    """
    Service for matching Talent Personal Agents with Job Postings (Company AI Agents).

    Uses dual RAG systems:
    - Talent RAG: Skills, preferences, career goals
    - Job RAG: Requirements + HM preferences + company culture
    """

    def __init__(
        self,
        anthropic_api_key: Optional[str] = None,
        chromadb_service: Optional[ChromaDBService] = None,
        use_rag: bool = True,
        enable_websocket: bool = True
    ):
        """
        Initialize matching service.

        Args:
            anthropic_api_key: Anthropic API key for Claude
            chromadb_service: ChromaDB service instance (optional)
            use_rag: Whether to use RAG queries (True) or placeholders (False)
            enable_websocket: Enable real-time WebSocket notifications (Phase 3)
        """
        api_key = anthropic_api_key or os.getenv("ANTHROPIC_API_KEY")

        if not api_key:
            raise ValueError("Anthropic API key required for matching")

        # Initialize Claude for match explanations
        self.llm = ChatAnthropic(
            model="claude-3-5-sonnet-20241022",
            api_key=api_key,
            temperature=0.7
        )

        # Initialize ChromaDB service
        self.use_rag = use_rag
        if use_rag:
            self.chromadb = chromadb_service or create_chromadb_service()
        else:
            self.chromadb = None

        # WebSocket broadcasting
        self.enable_websocket = enable_websocket
        self._connection_manager = None

    def _get_connection_manager(self):
        """Get connection manager lazily to avoid circular imports."""
        if self._connection_manager is None and self.enable_websocket:
            try:
                from ..websocket.connection_manager import get_connection_manager
                self._connection_manager = get_connection_manager()
            except ImportError:
                print("[AgentMatching] WebSocket not available")
                self.enable_websocket = False
        return self._connection_manager

    async def _broadcast_new_match(self, match: Match):
        """
        Broadcast new match via WebSocket to talent user.

        Args:
            match: Match object that was created
        """
        if not self.enable_websocket:
            return

        connection_manager = self._get_connection_manager()
        if not connection_manager:
            return

        try:
            from ..websocket.event_types import NewMatchEvent

            # Create WebSocket event
            event = NewMatchEvent.create(
                match_id=match.id,
                job_id=match.job_id,
                job_title=match.job_title,
                company_name=match.company_name,
                match_score=match.match_score,
                matched_skills=match.matched_skills or [],
                ai_explanation=match.ai_explanation or "Great match based on your profile!"
            )

            # Send to talent user
            await connection_manager.send_to_user(
                user_id=match.talent_user_id,
                message=event.model_dump()
            )

            print(f"[AgentMatching] Broadcasted match {match.id} to user {match.talent_user_id}")

        except Exception as e:
            print(f"[AgentMatching] WebSocket broadcast error: {e}")

    def find_matches_for_talent(
        self,
        talent_user: User,
        talent_agent: PersonalAIAgent,
        db: Session,
        limit: int = 3
    ) -> List[Match]:
        """
        Find top job matches for a talent user.

        Args:
            talent_user: Talent user
            talent_agent: Talent's personal AI agent
            db: Database session
            limit: Max number of matches to return (default: 3 per day)

        Returns:
            List of Match objects
        """
        # Get talent profile from RAG
        talent_profile = self._get_talent_profile(talent_agent)

        # Get active jobs
        active_jobs = db.query(Job).filter(
            Job.status == JobStatus.ACTIVE
        ).all()

        if not active_jobs:
            return []

        # Score each job
        scored_jobs = []
        for job in active_jobs:
            score_result = self._score_job_match(
                talent_profile=talent_profile,
                job=job,
                talent_agent=talent_agent,
                db=db
            )

            if score_result["match_score"] >= 0.6:  # Minimum threshold
                scored_jobs.append({
                    "job": job,
                    "score_result": score_result
                })

        # Sort by match score
        scored_jobs.sort(key=lambda x: x["score_result"]["match_score"], reverse=True)

        # Take top N matches
        top_matches = scored_jobs[:limit]

        # Create Match records
        matches = []
        for item in top_matches:
            job = item["job"]
            score_result = item["score_result"]

            # Get company
            company = db.query(Company).filter(Company.id == job.company_id).first()

            match = Match(
                talent_user_id=talent_user.id,
                talent_agent_id=talent_agent.id,
                job_id=job.id,
                job_title=job.title,
                company_id=job.company_id,
                company_name=company.name if company else "Unknown",
                match_score=score_result["match_score"],
                skill_match_score=score_result["skill_match_score"],
                preference_match_score=score_result["preference_match_score"],
                culture_match_score=score_result["culture_match_score"],
                ai_explanation=score_result["explanation"],
                matched_skills=score_result["matched_skills"],
                skill_gaps=score_result["skill_gaps"],
                matched_preferences=score_result["matched_preferences"],
                growth_opportunities=score_result["growth_opportunities"],
                confidence_level=score_result["confidence_level"],
                status=MatchStatus.PENDING,
                created_by_agent="agent_matching_service",
                match_strategy="semantic_dual_rag",
                expires_at=datetime.utcnow() + timedelta(days=7)  # Matches expire in 7 days
            )

            db.add(match)
            matches.append(match)

        db.commit()

        # Broadcast new matches via WebSocket (Phase 3)
        if self.enable_websocket and matches:
            for match in matches:
                try:
                    # Run async broadcast in event loop
                    loop = asyncio.get_event_loop()
                    if loop.is_running():
                        asyncio.create_task(self._broadcast_new_match(match))
                    else:
                        loop.run_until_complete(self._broadcast_new_match(match))
                except Exception as e:
                    print(f"[AgentMatching] Failed to broadcast match {match.id}: {e}")

        return matches

    def find_matches_for_job(
        self,
        job: Job,
        db: Session,
        limit: int = 10
    ) -> List[Match]:
        """
        Find top talent matches for a job posting.

        Args:
            job: Job posting
            db: Database session
            limit: Max number of matches to return

        Returns:
            List of Match objects
        """
        # Get job requirements
        job_requirements = self._get_job_requirements(job)

        # Get active talent agents
        active_agents = db.query(PersonalAIAgent).filter(
            PersonalAIAgent.agent_type == AgentType.TALENT,
            PersonalAIAgent.status == "active"
        ).all()

        if not active_agents:
            return []

        # Score each talent
        scored_talents = []
        for agent in active_agents:
            # Get user
            user = db.query(User).filter(User.id == agent.user_id).first()
            if not user:
                continue

            talent_profile = self._get_talent_profile(agent)

            score_result = self._score_job_match(
                talent_profile=talent_profile,
                job=job,
                talent_agent=agent,
                db=db
            )

            if score_result["match_score"] >= 0.6:  # Minimum threshold
                scored_talents.append({
                    "user": user,
                    "agent": agent,
                    "score_result": score_result
                })

        # Sort by match score
        scored_talents.sort(key=lambda x: x["score_result"]["match_score"], reverse=True)

        # Take top N matches
        top_matches = scored_talents[:limit]

        # Get company
        company = db.query(Company).filter(Company.id == job.company_id).first()

        # Create Match records
        matches = []
        for item in top_matches:
            user = item["user"]
            agent = item["agent"]
            score_result = item["score_result"]

            match = Match(
                talent_user_id=user.id,
                talent_agent_id=agent.id,
                job_id=job.id,
                job_title=job.title,
                company_id=job.company_id,
                company_name=company.name if company else "Unknown",
                match_score=score_result["match_score"],
                skill_match_score=score_result["skill_match_score"],
                preference_match_score=score_result["preference_match_score"],
                culture_match_score=score_result["culture_match_score"],
                ai_explanation=score_result["explanation"],
                matched_skills=score_result["matched_skills"],
                skill_gaps=score_result["skill_gaps"],
                matched_preferences=score_result["matched_preferences"],
                growth_opportunities=score_result["growth_opportunities"],
                confidence_level=score_result["confidence_level"],
                status=MatchStatus.PENDING,
                created_by_agent="agent_matching_service",
                match_strategy="semantic_dual_rag",
                expires_at=datetime.utcnow() + timedelta(days=7)
            )

            db.add(match)
            matches.append(match)

        db.commit()

        return matches

    def _get_talent_profile(self, talent_agent: PersonalAIAgent) -> Dict:
        """
        Get talent profile from Personal Agent RAG.

        Queries ChromaDB collection for talent knowledge:
        - Skills (technical and soft)
        - Career preferences (remote, salary range, growth areas)
        - Experience level
        - Career goals
        - Work environment preferences

        Args:
            talent_agent: Talent Personal AI Agent

        Returns:
            Dict with profile data
        """
        # Use RAG if available and enabled
        if self.use_rag and self.chromadb and talent_agent.rag_collection_id:
            try:
                profile = self.chromadb.query_talent_profile(
                    collection_name=talent_agent.rag_collection_id,
                    query="What are the candidate's skills, preferences, and career goals?",
                    n_results=10
                )

                if profile and profile.get("skills"):
                    print(f"[Matching] Loaded talent profile from RAG: {len(profile.get('skills', []))} skills")
                    return profile

            except Exception as e:
                print(f"[Matching] RAG query failed, using placeholder: {e}")

        # Fallback to placeholder data
        return {
            "skills": ["Python", "FastAPI", "Machine Learning", "SQL"],
            "experience_level": "mid_level",
            "preferences": {
                "remote": True,
                "salary_min": 80000,
                "salary_max": 120000,
                "growth_areas": ["AI/ML", "System Design"],
                "company_size": "startup"
            },
            "career_goals": "Looking for ML engineering role with growth potential",
            "work_style": "Collaborative, autonomous, continuous learner"
        }

    def _get_job_requirements(self, job: Job) -> Dict:
        """
        Get job requirements from Job RAG.

        Queries Job RAG collection with dual access:
        - Job requirements
        - HM's hiring preferences (from Personal HM Agent RAG)
        - Company culture and values (from Company Admin Agent RAG)

        Args:
            job: Job posting

        Returns:
            Dict with job requirements and context
        """
        # Use RAG if available and enabled
        if self.use_rag and self.chromadb and job.job_rag_collection_id:
            try:
                # Query job RAG
                job_results = self.chromadb.query_collection(
                    collection_name=job.job_rag_collection_id,
                    query_texts=["What are the job requirements, skills, and experience needed?"],
                    n_results=10
                )

                # Extract skills from RAG
                required_skills = []
                preferred_skills = []

                for doc in job_results.get("documents", [[]])[0]:
                    if "Required skills:" in doc:
                        skills_text = doc.split("Required skills:")[1].strip()
                        required_skills = [s.strip() for s in skills_text.split(",")]
                    elif "Preferred skills:" in doc:
                        skills_text = doc.split("Preferred skills:")[1].strip()
                        preferred_skills = [s.strip() for s in skills_text.split(",")]

                if required_skills or preferred_skills:
                    print(f"[Matching] Loaded job requirements from RAG: {len(required_skills)} required skills")

                    # Combine RAG data with job model data
                    return {
                        "required_skills": required_skills or (job.required_skills or []),
                        "preferred_skills": preferred_skills or (job.preferred_skills or []),
                        "experience_level": job.experience_level.value if job.experience_level else "mid_level",
                        "job_type": job.job_type.value if job.job_type else "full_time",
                        "is_remote": job.is_remote,
                        "salary_range": {
                            "min": job.salary_min,
                            "max": job.salary_max
                        },
                        "description": job.description,
                        "department": job.department,
                        "rag_context": job_results.get("documents", [[]])[0]  # Additional context
                    }

            except Exception as e:
                print(f"[Matching] Job RAG query failed, using job model data: {e}")

        # Fallback to job model data
        return {
            "required_skills": job.required_skills or [],
            "preferred_skills": job.preferred_skills or [],
            "experience_level": job.experience_level.value if job.experience_level else "mid_level",
            "job_type": job.job_type.value if job.job_type else "full_time",
            "is_remote": job.is_remote,
            "salary_range": {
                "min": job.salary_min,
                "max": job.salary_max
            },
            "description": job.description,
            "department": job.department
        }

    def _score_job_match(
        self,
        talent_profile: Dict,
        job: Job,
        talent_agent: PersonalAIAgent,
        db: Session
    ) -> Dict:
        """
        Score a talent-job match using semantic similarity.

        Returns:
            Dict with match scores and explanation
        """
        job_requirements = self._get_job_requirements(job)

        # 1. Skill matching
        talent_skills = set([s.lower() for s in talent_profile.get("skills", [])])
        required_skills = set([s.lower() for s in job_requirements.get("required_skills", [])])
        preferred_skills = set([s.lower() for s in job_requirements.get("preferred_skills", [])])

        matched_required = talent_skills & required_skills
        matched_preferred = talent_skills & preferred_skills
        missing_required = required_skills - talent_skills

        # Skill match score
        required_match_pct = len(matched_required) / len(required_skills) if required_skills else 1.0
        preferred_match_pct = len(matched_preferred) / len(preferred_skills) if preferred_skills else 0.5
        skill_match_score = (required_match_pct * 0.7) + (preferred_match_pct * 0.3)

        # 2. Preference matching
        preference_score = self._score_preferences(talent_profile, job_requirements)

        # 3. Culture matching (TODO: Use company RAG)
        # For now, use simple heuristics
        culture_score = self._score_culture_fit(talent_profile, job)

        # 4. Overall match score (weighted average)
        match_score = (
            skill_match_score * 0.5 +
            preference_score * 0.3 +
            culture_score * 0.2
        )

        # 5. Generate AI explanation
        explanation = self._generate_match_explanation(
            talent_profile=talent_profile,
            job=job,
            job_requirements=job_requirements,
            matched_skills=list(matched_required | matched_preferred),
            skill_gaps=list(missing_required),
            match_score=match_score
        )

        # Determine confidence level
        confidence_level = "high" if match_score >= 0.8 else "medium" if match_score >= 0.65 else "low"

        return {
            "match_score": round(match_score, 3),
            "skill_match_score": round(skill_match_score, 3),
            "preference_match_score": round(preference_score, 3),
            "culture_match_score": round(culture_score, 3),
            "matched_skills": list(matched_required | matched_preferred),
            "skill_gaps": list(missing_required),
            "matched_preferences": self._get_matched_preferences(talent_profile, job_requirements),
            "growth_opportunities": self._identify_growth_opportunities(talent_profile, job),
            "explanation": explanation,
            "confidence_level": confidence_level
        }

    def _score_preferences(self, talent_profile: Dict, job_requirements: Dict) -> float:
        """Score how well job matches talent preferences."""
        score = 0.0
        checks = 0

        preferences = talent_profile.get("preferences", {})

        # Remote preference
        if "remote" in preferences:
            checks += 1
            if preferences["remote"] == job_requirements.get("is_remote", False):
                score += 1.0

        # Salary alignment
        if "salary_min" in preferences and job_requirements.get("salary_range"):
            checks += 1
            job_salary = job_requirements["salary_range"]
            if job_salary.get("max", 0) >= preferences["salary_min"]:
                score += 1.0

        return score / checks if checks > 0 else 0.5

    def _score_culture_fit(self, talent_profile: Dict, job: Job) -> float:
        """
        Score culture fit.

        TODO: Use Company Admin Agent RAG for culture values.
        For now, return moderate score.
        """
        # TODO: Query Company Admin Agent RAG for:
        # - Company values
        # - Team culture
        # - Work environment
        # Then match against talent preferences

        return 0.75  # Placeholder

    def _get_matched_preferences(self, talent_profile: Dict, job_requirements: Dict) -> List[str]:
        """Get list of matched preferences."""
        matched = []
        preferences = talent_profile.get("preferences", {})

        if preferences.get("remote") and job_requirements.get("is_remote"):
            matched.append("Remote work")

        if preferences.get("growth_areas"):
            matched.append(f"Growth in {', '.join(preferences['growth_areas'])}")

        return matched

    def _identify_growth_opportunities(self, talent_profile: Dict, job: Job) -> List[str]:
        """Identify career growth opportunities in this role."""
        opportunities = []

        # Check if job has skills they want to learn
        preferences = talent_profile.get("preferences", {})
        growth_areas = preferences.get("growth_areas", [])

        job_skills = set([s.lower() for s in (job.required_skills or []) + (job.preferred_skills or [])])

        for area in growth_areas:
            if any(area.lower() in skill.lower() for skill in job_skills):
                opportunities.append(f"Learn {area}")

        if not opportunities:
            opportunities.append("Expand technical expertise")

        return opportunities

    def _generate_match_explanation(
        self,
        talent_profile: Dict,
        job: Job,
        job_requirements: Dict,
        matched_skills: List[str],
        skill_gaps: List[str],
        match_score: float
    ) -> str:
        """Generate AI explanation for why this is a good match."""

        prompt = f"""You are a career advisor explaining why a job is a good match for a candidate.

Candidate Profile:
- Skills: {', '.join(talent_profile.get('skills', []))}
- Experience: {talent_profile.get('experience_level', 'Not specified')}
- Career Goals: {talent_profile.get('career_goals', 'Not specified')}
- Preferences: Remote={talent_profile.get('preferences', {}).get('remote', False)}

Job:
- Title: {job.title}
- Required Skills: {', '.join(job_requirements.get('required_skills', []))}
- Experience Level: {job_requirements.get('experience_level', 'Not specified')}
- Remote: {job_requirements.get('is_remote', False)}

Match Details:
- Matched Skills: {', '.join(matched_skills) if matched_skills else 'None'}
- Skill Gaps: {', '.join(skill_gaps) if skill_gaps else 'None'}
- Match Score: {match_score:.1%}

Write a friendly, concise 2-3 sentence explanation of why this is a good match. Focus on:
1. Key skill alignments
2. Career growth potential
3. Preference match (if applicable)

Be encouraging but honest about any skill gaps."""

        try:
            response = self.llm.invoke(prompt)
            return response.content.strip()
        except Exception as e:
            # Fallback to template explanation
            return f"This role matches {len(matched_skills)} of your key skills including {', '.join(matched_skills[:3])}. " + \
                   f"It offers growth opportunities in areas you're interested in."


def create_agent_matching_service(
    anthropic_api_key: Optional[str] = None,
    chromadb_service: Optional[ChromaDBService] = None,
    use_rag: bool = True,
    enable_websocket: bool = True
) -> AgentMatchingService:
    """
    Factory function to create matching service.

    Args:
        anthropic_api_key: Anthropic API key
        chromadb_service: ChromaDB service instance (optional)
        use_rag: Whether to use RAG queries (default: True)
        enable_websocket: Enable real-time WebSocket notifications (Phase 3)

    Returns:
        AgentMatchingService instance
    """
    return AgentMatchingService(
        anthropic_api_key=anthropic_api_key,
        chromadb_service=chromadb_service,
        use_rag=use_rag,
        enable_websocket=enable_websocket
    )
