"""Auto-Activation Service - Symmetric agent activation for Talent and HM.

Replaces manual certification gates with automatic readiness scoring:
- CV/JD upload → readiness from document quality
- Structured interview → readiness from answer quality
- Combined score >= threshold → agent auto-activates

Formula: combined_score = (document_readiness * 0.7) + (interview_quality * 0.3)
Threshold: 60/100

Both talent and HM agents use the same activation logic.
"""

from typing import Optional

from supabase import create_client
from fastapi import HTTPException

from app.config import SUPABASE_URL, SUPABASE_SERVICE_KEY
from app.services.interview_service import interview_service
from app.services.ai_profile_service import ai_profile_service


ACTIVATION_THRESHOLD = 60  # 0-100 score needed to auto-activate
DOCUMENT_WEIGHT = 0.7
INTERVIEW_WEIGHT = 0.3


def _get_supabase():
    if not SUPABASE_URL or not SUPABASE_SERVICE_KEY:
        raise HTTPException(status_code=503, detail="Database not configured.")
    return create_client(SUPABASE_URL, SUPABASE_SERVICE_KEY)


class AutoActivation:
    """Manages auto-activation for both agent types."""

    async def compute_talent_readiness(
        self, user_id: str, cv_analysis: Optional[dict] = None
    ) -> dict:
        """Compute readiness score for a talent agent.

        Returns:
            {
                "document_score": 0-100,
                "interview_score": 0-100,
                "combined_score": 0-100,
                "ready": bool,
                "missing": ["what's needed to improve score"]
            }
        """
        client = _get_supabase()

        # Document readiness
        if cv_analysis is None:
            docs = (
                client.table("cv2_documents")
                .select("analysis")
                .eq("user_id", user_id)
                .eq("doc_type", "cv")
                .execute()
            )
            if docs.data and docs.data[0].get("analysis"):
                cv_analysis = docs.data[0]["analysis"]

        document_score = self._score_cv_analysis(cv_analysis)

        # Interview readiness
        interview_data = (
            client.table("cv2_interviews")
            .select("answers")
            .eq("user_id", user_id)
            .eq("agent_type", "talent")
            .order("created_at", desc=True)
            .limit(1)
            .execute()
        )

        interview_score = 0
        if interview_data.data and interview_data.data[0].get("answers"):
            answers = interview_data.data[0]["answers"]
            quality = await interview_service.compute_interview_quality(answers)
            interview_score = quality.get("quality_score", 0)

        combined = int(document_score * DOCUMENT_WEIGHT + interview_score * INTERVIEW_WEIGHT)

        missing = []
        if document_score < 50:
            missing.append("Upload a CV with more detail")
        if interview_score < 40:
            missing.append("Complete the structured interview")

        return {
            "document_score": document_score,
            "interview_score": interview_score,
            "combined_score": combined,
            "ready": combined >= ACTIVATION_THRESHOLD,
            "missing": missing,
        }

    async def compute_hm_readiness(
        self, user_id: str, job_id: str, job_analysis: Optional[dict] = None
    ) -> dict:
        """Compute readiness score for a hiring manager agent.

        Returns same structure as talent readiness.
        """
        client = _get_supabase()

        # Document readiness (job description quality)
        if job_analysis is None:
            job = (
                client.table("cv2_jobs")
                .select("*")
                .eq("id", job_id)
                .execute()
            )
            if job.data:
                job_analysis = job.data[0]

        document_score = self._score_job_description(job_analysis)

        # Interview readiness
        interview_data = (
            client.table("cv2_interviews")
            .select("answers")
            .eq("user_id", user_id)
            .eq("agent_type", "hm")
            .eq("context_id", job_id)
            .order("created_at", desc=True)
            .limit(1)
            .execute()
        )

        interview_score = 0
        if interview_data.data and interview_data.data[0].get("answers"):
            answers = interview_data.data[0]["answers"]
            quality = await interview_service.compute_interview_quality(answers)
            interview_score = quality.get("quality_score", 0)

        combined = int(document_score * DOCUMENT_WEIGHT + interview_score * INTERVIEW_WEIGHT)

        missing = []
        if document_score < 50:
            missing.append("Add more detail to the job description")
        if interview_score < 40:
            missing.append("Complete the structured interview about your hiring preferences")

        return {
            "document_score": document_score,
            "interview_score": interview_score,
            "combined_score": combined,
            "ready": combined >= ACTIVATION_THRESHOLD,
            "missing": missing,
        }

    async def activate_talent_agent(self, user_id: str) -> dict:
        """Activate a talent agent if readiness threshold is met.

        Steps:
        1. Compute readiness
        2. If ready, generate AI profile
        3. Register as A2A candidate
        4. Update stage to 'matchable'

        Returns activation result.
        """
        readiness = await self.compute_talent_readiness(user_id)

        if not readiness["ready"]:
            return {
                "status": "not_ready",
                "score": readiness["combined_score"],
                "threshold": ACTIVATION_THRESHOLD,
                "missing": readiness["missing"],
            }

        client = _get_supabase()

        # Get CV analysis and interview answers
        docs = (
            client.table("cv2_documents")
            .select("analysis")
            .eq("user_id", user_id)
            .eq("doc_type", "cv")
            .execute()
        )
        cv_analysis = docs.data[0]["analysis"] if docs.data and docs.data[0].get("analysis") else None

        interview_data = (
            client.table("cv2_interviews")
            .select("answers")
            .eq("user_id", user_id)
            .eq("agent_type", "talent")
            .order("created_at", desc=True)
            .limit(1)
            .execute()
        )
        answers = interview_data.data[0]["answers"] if interview_data.data else []

        profile = (
            client.table("cv2_profiles")
            .select("industry")
            .eq("user_id", user_id)
            .execute()
        )
        industry = profile.data[0]["industry"] if profile.data else "general"

        # Generate AI profile
        ai_profile = await ai_profile_service.generate_talent_profile(
            cv_analysis=cv_analysis,
            interview_answers=answers,
            industry=industry,
        )

        # Store AI profile
        client.table("cv2_profiles").update({
            "ai_profile": ai_profile,
            "stage": "matchable",
            "activation_score": readiness["combined_score"],
        }).eq("user_id", user_id).execute()

        # Register as A2A candidate
        candidate_record = {
            "id": user_id,
            "user_id": user_id,
            "industry": industry,
            "profile": ai_profile,
            "active": True,
        }
        client.table("cv2_a2a_candidates").upsert(candidate_record).execute()

        # Register agent
        agent_record = {
            "id": f"agent_{user_id}",
            "user_id": user_id,
            "agent_type": "talent",
            "industry": industry,
            "profile": ai_profile,
            "active": True,
        }
        client.table("cv2_agents").upsert(agent_record).execute()

        return {
            "status": "activated",
            "score": readiness["combined_score"],
            "profile_synopsis": ai_profile.get("synopsis", ""),
            "agent_id": f"agent_{user_id}",
        }

    async def activate_hm_agent(self, user_id: str, job_id: str) -> dict:
        """Activate a hiring manager agent for a specific job.

        Steps:
        1. Compute readiness
        2. If ready, generate HM AI profile
        3. Register as A2A job agent
        4. Mark job as 'active'

        Returns activation result.
        """
        readiness = await self.compute_hm_readiness(user_id, job_id)

        if not readiness["ready"]:
            return {
                "status": "not_ready",
                "score": readiness["combined_score"],
                "threshold": ACTIVATION_THRESHOLD,
                "missing": readiness["missing"],
            }

        client = _get_supabase()

        # Get job description
        job_data = (
            client.table("cv2_jobs")
            .select("*")
            .eq("id", job_id)
            .execute()
        )
        job_description = job_data.data[0] if job_data.data else {}
        industry = job_description.get("industry", "general")

        # Get interview answers
        interview_data = (
            client.table("cv2_interviews")
            .select("answers")
            .eq("user_id", user_id)
            .eq("agent_type", "hm")
            .eq("context_id", job_id)
            .order("created_at", desc=True)
            .limit(1)
            .execute()
        )
        answers = interview_data.data[0]["answers"] if interview_data.data else []

        # Generate HM AI profile
        ai_profile = await ai_profile_service.generate_hm_profile(
            job_description=job_description,
            interview_answers=answers,
            industry=industry,
        )

        # Update job with AI profile and mark active
        client.table("cv2_jobs").update({
            "ai_profile": ai_profile,
            "status": "active",
            "activation_score": readiness["combined_score"],
        }).eq("id", job_id).execute()

        # Register HM agent
        agent_record = {
            "id": f"hm_agent_{job_id}",
            "user_id": user_id,
            "job_id": job_id,
            "agent_type": "hm",
            "industry": industry,
            "profile": ai_profile,
            "active": True,
        }
        client.table("cv2_agents").upsert(agent_record).execute()

        return {
            "status": "activated",
            "score": readiness["combined_score"],
            "profile_synopsis": ai_profile.get("synopsis", ""),
            "agent_id": f"hm_agent_{job_id}",
        }

    def _score_cv_analysis(self, cv_analysis: Optional[dict]) -> int:
        """Score CV analysis completeness (0-100)."""
        if not cv_analysis or cv_analysis.get("error"):
            return 0

        score = 0
        if cv_analysis.get("name"):
            score += 10
        if cv_analysis.get("current_role"):
            score += 15
        if cv_analysis.get("experience_years"):
            score += 10
        if cv_analysis.get("skills"):
            score += min(20, len(cv_analysis["skills"]) * 2)
        if cv_analysis.get("experience"):
            score += min(25, len(cv_analysis["experience"]) * 5)
        if cv_analysis.get("education"):
            score += 10
        if cv_analysis.get("career_trajectory"):
            score += 10

        return min(100, score)

    def _score_job_description(self, job: Optional[dict]) -> int:
        """Score job description completeness (0-100)."""
        if not job:
            return 0

        score = 0
        if job.get("title"):
            score += 15
        if job.get("company"):
            score += 10
        if job.get("description") and len(job["description"]) > 50:
            score += 20
        if job.get("requirements"):
            reqs = job["requirements"]
            if isinstance(reqs, list):
                score += min(20, len(reqs) * 4)
            elif isinstance(reqs, str) and len(reqs) > 30:
                score += 15
        if job.get("values"):
            score += 15
        if job.get("culture"):
            score += 10
        if job.get("salary_range"):
            score += 10

        return min(100, score)


auto_activation = AutoActivation()
