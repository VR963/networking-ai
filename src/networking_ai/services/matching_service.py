"""
AI Matching Service.

Connects the semantic matching system with the database layer.
Automatically generates matches between job seekers and jobs.
"""

from typing import List, Dict, Optional, Tuple
from datetime import datetime, timedelta
from sqlalchemy.orm import Session
from sqlalchemy import and_, or_
import json

from ..semantic import SemanticMatcher
from ..ai_agent import AnthropicAgent
from ..models.user import User, UserRole
from ..models.profile import UserProfile
from ..models.job import Job, JobStatus
from ..models.match import Match, MatchStatus
from ..models.ai_agent import AIAgent
from ..config import config


class MatchingService:
    """
    AI-powered matching service.

    Generates matches between job seekers and jobs using semantic similarity,
    skill matching, and AI-powered explanations.
    """

    def __init__(self, db: Session, api_key: Optional[str] = None):
        """
        Initialize matching service.

        Args:
            db: Database session
            api_key: Optional Anthropic API key for AI explanations
        """
        self.db = db
        self.semantic_matcher = SemanticMatcher()
        self.ai_agent: Optional[AnthropicAgent] = None

        # Initialize AI agent if enabled
        if config.ENABLE_AI_ANALYSIS:
            try:
                self.ai_agent = AnthropicAgent(api_key=api_key)
            except (ValueError, Exception) as e:
                print(f"[MATCHING] Warning: AI agent disabled - {e}")

    def profile_to_dict(self, profile: UserProfile) -> Dict:
        """
        Convert database UserProfile to dict format for semantic matching.

        Args:
            profile: Database UserProfile model

        Returns:
            Dictionary representation for matching
        """
        user = profile.user

        # Build comprehensive text representation
        parts = []
        if profile.headline:
            parts.append(profile.headline)
        if profile.current_title:
            parts.append(f"Current: {profile.current_title}")
        if profile.bio:
            parts.append(profile.bio)
        if profile.career_goals:
            parts.append(f"Goals: {profile.career_goals}")

        return {
            "user_id": str(profile.id),
            "name": user.full_name if user else "Unknown",
            "skills": profile.skills or [],
            "interests": profile.interests or [],
            "bio": " | ".join(parts),
            "goals": profile.career_goals,
            "current_title": profile.current_title,
            "years_of_experience": profile.years_of_experience or 0,
            "desired_roles": profile.desired_roles or [],
            "desired_salary_min": profile.desired_salary_min,
            "desired_salary_max": profile.desired_salary_max,
            "location": profile.location,
            "is_remote_only": profile.is_remote_only,
        }

    def job_to_dict(self, job: Job) -> Dict:
        """
        Convert database Job to dict format for semantic matching.

        Args:
            job: Database Job model

        Returns:
            Dictionary representation for matching
        """
        # Build comprehensive text representation
        parts = []
        if job.title:
            parts.append(job.title)
        if job.description:
            parts.append(job.description)
        if job.responsibilities:
            parts.append(f"Responsibilities: {job.responsibilities}")
        if job.benefits:
            parts.append(f"Benefits: {job.benefits}")

        return {
            "job_id": str(job.id),
            "title": job.title,
            "skills": job.required_skills or [],
            "description": " | ".join(parts),
            "experience_level": job.experience_level.value if job.experience_level else None,
            "required_experience_years": job.required_experience_years or 0,
            "salary_min": job.salary_min,
            "salary_max": job.salary_max,
            "location": job.location,
            "is_remote": job.is_remote,
            "job_type": job.job_type.value if job.job_type else None,
        }

    def calculate_match_score(
        self,
        profile_dict: Dict,
        job_dict: Dict
    ) -> Tuple[float, Dict[str, float]]:
        """
        Calculate comprehensive match score between profile and job.

        Args:
            profile_dict: Profile dictionary
            job_dict: Job dictionary

        Returns:
            Tuple of (final_score, component_scores)
        """
        # Semantic similarity between profile and job description
        profile_text = self.semantic_matcher.generate_profile_text(profile_dict)
        job_text = f"Title: {job_dict['title']} | Description: {job_dict['description']}"

        profile_embedding = self.semantic_matcher.generate_embedding(profile_text)
        job_embedding = self.semantic_matcher.generate_embedding(job_text)

        semantic_score = self.semantic_matcher.calculate_similarity(
            profile_embedding, job_embedding
        )

        # Skill matching score
        skill_score = 0.0
        if profile_dict.get("skills") and job_dict.get("skills"):
            skill_score = self.semantic_matcher.calculate_skill_similarity(
                profile_dict["skills"],
                job_dict["skills"]
            )

        # Experience alignment score
        experience_score = self._calculate_experience_score(
            profile_dict.get("years_of_experience", 0),
            job_dict.get("required_experience_years", 0)
        )

        # Salary alignment score
        salary_score = self._calculate_salary_score(
            profile_dict.get("desired_salary_min"),
            profile_dict.get("desired_salary_max"),
            job_dict.get("salary_min"),
            job_dict.get("salary_max")
        )

        # Location compatibility score
        location_score = self._calculate_location_score(
            profile_dict.get("location"),
            profile_dict.get("is_remote_only", False),
            job_dict.get("location"),
            job_dict.get("is_remote", False)
        )

        # Weighted final score
        # Skills and semantic are most important, then experience, salary, location
        final_score = (
            0.35 * skill_score +
            0.30 * semantic_score +
            0.15 * experience_score +
            0.10 * salary_score +
            0.10 * location_score
        )

        component_scores = {
            "semantic_score": float(semantic_score),
            "skill_score": float(skill_score),
            "experience_score": float(experience_score),
            "salary_score": float(salary_score),
            "location_score": float(location_score),
        }

        return float(final_score), component_scores

    def _calculate_experience_score(
        self,
        candidate_years: int,
        required_years: int
    ) -> float:
        """Calculate experience alignment score."""
        if required_years == 0:
            return 1.0

        if candidate_years >= required_years:
            # Perfect match or overqualified (slight penalty for massive overqualification)
            diff = candidate_years - required_years
            if diff <= 2:
                return 1.0
            elif diff <= 5:
                return 0.9
            else:
                return 0.8
        else:
            # Underqualified - scale linearly
            return max(0.0, candidate_years / required_years)

    def _calculate_salary_score(
        self,
        desired_min: Optional[int],
        desired_max: Optional[int],
        offered_min: Optional[int],
        offered_max: Optional[int]
    ) -> float:
        """Calculate salary alignment score."""
        # If no salary info, return neutral score
        if not desired_min or not offered_min:
            return 0.7

        # Check for overlap in ranges
        if offered_max and desired_min <= offered_max:
            if offered_min >= desired_min:
                return 1.0  # Perfect overlap
            else:
                # Partial overlap
                return 0.8
        elif offered_min >= desired_min * 0.9:  # Within 10%
            return 0.9
        elif offered_min >= desired_min * 0.8:  # Within 20%
            return 0.7
        else:
            return 0.5  # Significant gap

    def _calculate_location_score(
        self,
        candidate_location: Optional[str],
        candidate_remote_only: bool,
        job_location: Optional[str],
        job_is_remote: bool
    ) -> float:
        """Calculate location compatibility score."""
        # Remote job always works
        if job_is_remote:
            return 1.0

        # Candidate requires remote but job isn't
        if candidate_remote_only and not job_is_remote:
            return 0.0

        # Same location (simple string match)
        if candidate_location and job_location:
            if candidate_location.lower() == job_location.lower():
                return 1.0
            # TODO: Add city/region matching logic
            return 0.5

        return 0.7  # Neutral if no location info

    def generate_match_explanation(
        self,
        profile_dict: Dict,
        job_dict: Dict,
        match_score: float,
        component_scores: Dict[str, float]
    ) -> Optional[str]:
        """
        Generate AI-powered explanation for why this is a good match.

        Args:
            profile_dict: Profile data
            job_dict: Job data
            match_score: Overall match score
            component_scores: Breakdown of scores

        Returns:
            Explanation text or None
        """
        if not self.ai_agent:
            return self._generate_simple_explanation(
                profile_dict, job_dict, component_scores
            )

        try:
            # Use AI agent to generate detailed explanation
            explanation = self.ai_agent.explain_match(
                profile_dict,
                job_dict,
                {"weighted_score": match_score, **component_scores}
            )
            return explanation
        except Exception as e:
            print(f"[MATCHING] Could not generate AI explanation: {e}")
            return self._generate_simple_explanation(
                profile_dict, job_dict, component_scores
            )

    def _generate_simple_explanation(
        self,
        profile_dict: Dict,
        job_dict: Dict,
        component_scores: Dict[str, float]
    ) -> str:
        """Generate a simple rule-based explanation."""
        parts = []

        # Skill match
        if component_scores["skill_score"] >= 0.8:
            parts.append("Strong skill alignment")
        elif component_scores["skill_score"] >= 0.6:
            parts.append("Good skill match")

        # Experience
        if component_scores["experience_score"] >= 0.9:
            parts.append("Experience level matches requirements")

        # Salary
        if component_scores["salary_score"] >= 0.9:
            parts.append("Salary expectations align well")

        # Location
        if component_scores["location_score"] == 1.0:
            parts.append("Location is a perfect fit")

        if not parts:
            parts.append("Profile shows potential for this role")

        return ". ".join(parts) + "."

    def find_matching_skills(
        self,
        candidate_skills: List[str],
        required_skills: List[str]
    ) -> List[str]:
        """Find which required skills the candidate has."""
        if not candidate_skills or not required_skills:
            return []

        matching = []
        for req_skill in required_skills:
            req_emb = self.semantic_matcher.generate_embedding(req_skill.lower())

            for cand_skill in candidate_skills:
                cand_emb = self.semantic_matcher.generate_embedding(cand_skill.lower())
                similarity = self.semantic_matcher.calculate_similarity(req_emb, cand_emb)

                if similarity >= 0.75:  # High similarity threshold
                    matching.append(req_skill)
                    break

        return matching

    def find_skill_gaps(
        self,
        candidate_skills: List[str],
        required_skills: List[str]
    ) -> List[str]:
        """Find which required skills the candidate lacks."""
        if not required_skills:
            return []

        matching = self.find_matching_skills(candidate_skills, required_skills)
        return [skill for skill in required_skills if skill not in matching]

    def create_match(
        self,
        profile: UserProfile,
        job: Job,
        min_score: float = 0.5
    ) -> Optional[Match]:
        """
        Create a match between a profile and job if score is high enough.

        Args:
            profile: UserProfile model
            job: Job model
            min_score: Minimum score threshold (default 0.5)

        Returns:
            Created Match object or None if below threshold
        """
        # Check if match already exists
        existing = self.db.query(Match).filter(
            and_(
                Match.profile_id == profile.id,
                Match.job_id == job.id
            )
        ).first()

        if existing:
            print(f"[MATCHING] Match already exists: Profile {profile.id} <-> Job {job.id}")
            return existing

        # Convert to dicts for matching
        profile_dict = self.profile_to_dict(profile)
        job_dict = self.job_to_dict(job)

        # Calculate match score
        match_score, component_scores = self.calculate_match_score(profile_dict, job_dict)

        # Check threshold
        if match_score < min_score:
            print(f"[MATCHING] Score {match_score:.2f} below threshold {min_score}")
            return None

        # Classify confidence level
        if match_score >= 0.8:
            confidence = "high"
        elif match_score >= 0.65:
            confidence = "medium"
        else:
            confidence = "low"

        # Find matching skills and gaps
        matching_skills = self.find_matching_skills(
            profile.skills or [],
            job.required_skills or []
        )
        skill_gaps = self.find_skill_gaps(
            profile.skills or [],
            job.required_skills or []
        )

        # Classify salary alignment
        salary_score = component_scores["salary_score"]
        if salary_score >= 0.9:
            salary_alignment = "excellent"
        elif salary_score >= 0.7:
            salary_alignment = "good"
        else:
            salary_alignment = "acceptable"

        # Classify location compatibility
        location_score = component_scores["location_score"]
        if location_score == 1.0:
            location_compat = "perfect"
        elif location_score >= 0.7:
            location_compat = "good"
        else:
            location_compat = "requires_relocation"

        # Generate explanation
        explanation = self.generate_match_explanation(
            profile_dict, job_dict, match_score, component_scores
        )

        # Create match record
        match = Match(
            profile_id=profile.id,
            job_id=job.id,
            match_score=match_score,
            confidence_level=confidence,
            ai_explanation=explanation,
            matching_skills=json.dumps(matching_skills),
            skill_gaps=json.dumps(skill_gaps),
            salary_alignment=salary_alignment,
            location_compatibility=location_compat,
            created_by_agent="matching_service",
            match_strategy="semantic_hybrid",
            status=MatchStatus.PENDING,
            expires_at=datetime.utcnow() + timedelta(days=30)  # Matches expire in 30 days
        )

        self.db.add(match)
        self.db.commit()
        self.db.refresh(match)

        print(f"[MATCHING] Created match: Profile {profile.id} <-> Job {job.id} (score: {match_score:.2f})")

        return match

    def match_profile_to_jobs(
        self,
        profile_id: int,
        limit: int = 10,
        min_score: float = 0.5
    ) -> List[Match]:
        """
        Find and create matches for a profile against all active jobs.

        Args:
            profile_id: Profile ID to match
            limit: Maximum number of matches to create
            min_score: Minimum match score threshold

        Returns:
            List of created Match objects
        """
        # Get profile
        profile = self.db.query(UserProfile).filter(UserProfile.id == profile_id).first()
        if not profile:
            print(f"[MATCHING] Profile {profile_id} not found")
            return []

        # Get active jobs
        jobs = self.db.query(Job).filter(
            Job.status == JobStatus.ACTIVE
        ).all()

        print(f"[MATCHING] Matching profile {profile_id} against {len(jobs)} active jobs")

        # Calculate scores for all jobs
        matches_data = []
        for job in jobs:
            profile_dict = self.profile_to_dict(profile)
            job_dict = self.job_to_dict(job)
            score, components = self.calculate_match_score(profile_dict, job_dict)

            if score >= min_score:
                matches_data.append((job, score, components))

        # Sort by score and take top N
        matches_data.sort(key=lambda x: x[1], reverse=True)
        matches_data = matches_data[:limit]

        # Create match records
        created_matches = []
        for job, score, components in matches_data:
            match = self.create_match(profile, job, min_score=min_score)
            if match:
                created_matches.append(match)

        print(f"[MATCHING] Created {len(created_matches)} matches for profile {profile_id}")

        return created_matches

    def match_job_to_profiles(
        self,
        job_id: int,
        limit: int = 20,
        min_score: float = 0.5
    ) -> List[Match]:
        """
        Find and create matches for a job against all active profiles.

        Args:
            job_id: Job ID to match
            limit: Maximum number of matches to create
            min_score: Minimum match score threshold

        Returns:
            List of created Match objects
        """
        # Get job
        job = self.db.query(Job).filter(Job.id == job_id).first()
        if not job:
            print(f"[MATCHING] Job {job_id} not found")
            return []

        # Get active profiles (users who are job seekers)
        profiles = self.db.query(UserProfile).join(User).filter(
            User.role == UserRole.JOB_SEEKER,
            User.status == "active"
        ).all()

        print(f"[MATCHING] Matching job {job_id} against {len(profiles)} active profiles")

        # Calculate scores for all profiles
        matches_data = []
        for profile in profiles:
            profile_dict = self.profile_to_dict(profile)
            job_dict = self.job_to_dict(job)
            score, components = self.calculate_match_score(profile_dict, job_dict)

            if score >= min_score:
                matches_data.append((profile, score, components))

        # Sort by score and take top N
        matches_data.sort(key=lambda x: x[1], reverse=True)
        matches_data = matches_data[:limit]

        # Create match records
        created_matches = []
        for profile, score, components in matches_data:
            match = self.create_match(profile, job, min_score=min_score)
            if match:
                created_matches.append(match)

        print(f"[MATCHING] Created {len(created_matches)} matches for job {job_id}")

        return created_matches

    def batch_match_all(
        self,
        limit_per_entity: int = 10,
        min_score: float = 0.5
    ) -> Dict[str, int]:
        """
        Run matching for all profiles and jobs in the system.

        This is useful for:
        - Initial seeding of matches
        - Periodic re-matching jobs

        Args:
            limit_per_entity: Max matches per profile/job
            min_score: Minimum score threshold

        Returns:
            Dictionary with matching statistics
        """
        print("[MATCHING] Starting batch matching for all entities...")

        # Get all active profiles
        profiles = self.db.query(UserProfile).join(User).filter(
            User.role == UserRole.JOB_SEEKER,
            User.status == "active"
        ).all()

        # Match each profile to jobs
        total_matches = 0
        for profile in profiles:
            matches = self.match_profile_to_jobs(
                profile.id,
                limit=limit_per_entity,
                min_score=min_score
            )
            total_matches += len(matches)

        print(f"[MATCHING] Batch matching complete. Created {total_matches} matches")

        return {
            "profiles_matched": len(profiles),
            "total_matches_created": total_matches,
        }


def create_matching_service(db: Session, api_key: Optional[str] = None) -> MatchingService:
    """
    Factory function to create a MatchingService instance.

    Args:
        db: Database session
        api_key: Optional Anthropic API key

    Returns:
        Configured MatchingService instance
    """
    return MatchingService(db=db, api_key=api_key)
