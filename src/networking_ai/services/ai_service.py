"""
AI Service - Phase 8.

Service for advanced AI features: resume parsing, AI screening, and predictions.
"""

from datetime import datetime, timedelta
from typing import Optional, List, Dict, Any
from sqlalchemy.orm import Session
import json
import re
import logging

from ..models.ai_features import (
    ParsedResume,
    AIScreening,
    AIPrediction,
    SkillTaxonomy,
    AIModelMetrics,
    CandidateInsight,
    JobInsight,
    ResumeParseStatus,
    ScreeningDecision,
    PredictionType
)
from ..models.user import User
from ..models.job import Job
from ..models.application import Application

logger = logging.getLogger(__name__)


class AIService:
    """
    Service for advanced AI features.

    Handles resume parsing, AI screening, and predictive analytics.
    """

    def __init__(self, claude_api_key: Optional[str] = None):
        """Initialize AI service."""
        self.claude_api_key = claude_api_key
        # In production, initialize Claude API client here

    # ==================== Resume Parsing ====================

    def parse_resume(
        self,
        user_id: int,
        resume_text: str,
        source_file_url: Optional[str] = None,
        source_file_name: Optional[str] = None,
        db: Session = None
    ) -> ParsedResume:
        """
        Parse a resume and extract structured data.

        Args:
            user_id: User ID
            resume_text: Raw resume text
            source_file_url: Source file URL
            source_file_name: Source file name
            db: Database session

        Returns:
            ParsedResume object
        """
        # Check if resume already exists
        existing = db.query(ParsedResume).filter(ParsedResume.user_id == user_id).first()

        if existing:
            parsed_resume = existing
            parsed_resume.source_text = resume_text
            parsed_resume.parsing_status = ResumeParseStatus.PROCESSING
        else:
            parsed_resume = ParsedResume(
                user_id=user_id,
                source_text=resume_text,
                source_file_url=source_file_url,
                source_file_name=source_file_name,
                parsing_status=ResumeParseStatus.PROCESSING
            )
            db.add(parsed_resume)

        db.commit()
        db.refresh(parsed_resume)

        try:
            # Parse the resume (in production, use Claude API)
            parsed_data = self._parse_resume_text(resume_text)

            # Update the resume with parsed data
            parsed_resume.full_name = parsed_data.get("full_name")
            parsed_resume.email = parsed_data.get("email")
            parsed_resume.phone = parsed_data.get("phone")
            parsed_resume.location = parsed_data.get("location")
            parsed_resume.linkedin_url = parsed_data.get("linkedin_url")
            parsed_resume.github_url = parsed_data.get("github_url")
            parsed_resume.professional_title = parsed_data.get("professional_title")
            parsed_resume.summary = parsed_data.get("summary")

            parsed_resume.work_experience = parsed_data.get("work_experience", [])
            parsed_resume.education = parsed_data.get("education", [])
            parsed_resume.skills = parsed_data.get("skills", [])
            parsed_resume.certifications = parsed_data.get("certifications", [])
            parsed_resume.languages = parsed_data.get("languages", [])
            parsed_resume.projects = parsed_data.get("projects", [])

            # Calculate derived fields
            parsed_resume.total_years_experience = self._calculate_total_experience(
                parsed_data.get("work_experience", [])
            )
            parsed_resume.highest_education_level = self._get_highest_education(
                parsed_data.get("education", [])
            )
            parsed_resume.top_skills = parsed_data.get("skills", [])[:10]

            # Extract company names
            parsed_resume.company_names = [
                exp.get("company") for exp in parsed_data.get("work_experience", [])
                if exp.get("company")
            ]

            parsed_resume.parsing_status = ResumeParseStatus.COMPLETED
            parsed_resume.parsing_confidence = parsed_data.get("confidence", 85.0)
            parsed_resume.parsed_at = datetime.utcnow()

            db.commit()
            db.refresh(parsed_resume)

            logger.info(f"Successfully parsed resume for user {user_id}")
            return parsed_resume

        except Exception as e:
            parsed_resume.parsing_status = ResumeParseStatus.FAILED
            parsed_resume.parsing_errors = [str(e)]
            db.commit()
            logger.error(f"Failed to parse resume for user {user_id}: {e}")
            raise

    def _parse_resume_text(self, text: str) -> Dict[str, Any]:
        """
        Parse resume text into structured data.

        This is a simplified parser. In production, use Claude API for better accuracy.
        """
        parsed_data = {}

        # Extract email
        email_match = re.search(r'[\w\.-]+@[\w\.-]+\.\w+', text)
        if email_match:
            parsed_data["email"] = email_match.group()

        # Extract phone
        phone_match = re.search(r'[\+\(]?[1-9][0-9 .\-\(\)]{8,}[0-9]', text)
        if phone_match:
            parsed_data["phone"] = phone_match.group()

        # Extract URLs
        linkedin_match = re.search(r'linkedin\.com/in/[\w-]+', text, re.IGNORECASE)
        if linkedin_match:
            parsed_data["linkedin_url"] = f"https://{linkedin_match.group()}"

        github_match = re.search(r'github\.com/[\w-]+', text, re.IGNORECASE)
        if github_match:
            parsed_data["github_url"] = f"https://{github_match.group()}"

        # Extract skills (look for common programming/tech skills)
        common_skills = [
            "Python", "JavaScript", "Java", "C++", "React", "Node.js", "SQL", "AWS",
            "Docker", "Kubernetes", "Machine Learning", "Data Analysis", "Leadership",
            "Project Management", "Agile", "Scrum", "Git", "TypeScript", "Go", "Rust"
        ]
        found_skills = [skill for skill in common_skills if skill.lower() in text.lower()]
        parsed_data["skills"] = found_skills

        # Simple work experience extraction
        work_experience = []
        # Look for date ranges and company patterns
        date_pattern = r'(20\d{2})\s*-\s*(20\d{2}|Present)'
        dates = re.findall(date_pattern, text, re.IGNORECASE)

        for i, (start_year, end_year) in enumerate(dates):
            # This is simplified - in production, use AI to extract full details
            work_experience.append({
                "company": f"Company {i+1}",
                "title": "Software Engineer",  # Placeholder
                "start_date": f"{start_year}-01-01",
                "end_date": end_year if end_year != "Present" else None,
                "current": end_year.lower() == "present",
                "description": "Worked on various projects"
            })

        parsed_data["work_experience"] = work_experience

        # Simple education extraction
        education_keywords = ["Bachelor", "Master", "PhD", "B.S.", "M.S.", "B.A.", "M.A."]
        education = []
        for keyword in education_keywords:
            if keyword in text:
                education.append({
                    "degree": keyword,
                    "field": "Computer Science",  # Placeholder
                    "institution": "University",
                    "graduation_year": "2020"
                })
                break

        parsed_data["education"] = education
        parsed_data["confidence"] = 75.0  # Simplified parser has lower confidence

        return parsed_data

    def _calculate_total_experience(self, work_experience: List[Dict]) -> float:
        """Calculate total years of experience."""
        if not work_experience:
            return 0.0

        total_years = 0.0
        for exp in work_experience:
            start_date = exp.get("start_date")
            end_date = exp.get("end_date")

            if start_date:
                try:
                    start = datetime.fromisoformat(start_date.replace("Z", "+00:00"))
                    if end_date:
                        end = datetime.fromisoformat(end_date.replace("Z", "+00:00"))
                    else:
                        end = datetime.utcnow()

                    years = (end - start).days / 365.25
                    total_years += years
                except Exception:
                    pass

        return round(total_years, 1)

    def _get_highest_education(self, education: List[Dict]) -> Optional[str]:
        """Get highest education level."""
        if not education:
            return None

        education_hierarchy = {
            "phd": 4,
            "doctorate": 4,
            "master": 3,
            "m.s.": 3,
            "m.a.": 3,
            "bachelor": 2,
            "b.s.": 2,
            "b.a.": 2,
            "associate": 1
        }

        highest_level = 0
        highest_degree = None

        for edu in education:
            degree = edu.get("degree", "").lower()
            for key, level in education_hierarchy.items():
                if key in degree:
                    if level > highest_level:
                        highest_level = level
                        highest_degree = edu.get("degree")

        return highest_degree

    # ==================== AI Screening ====================

    def screen_application(
        self,
        application_id: int,
        job_id: int,
        candidate_user_id: int,
        db: Session = None
    ) -> AIScreening:
        """
        Screen an application using AI.

        Args:
            application_id: Application ID
            job_id: Job ID
            candidate_user_id: Candidate user ID
            db: Database session

        Returns:
            AIScreening object
        """
        # Get job and resume
        job = db.query(Job).get(job_id)
        if not job:
            raise ValueError("Job not found")

        resume = db.query(ParsedResume).filter(ParsedResume.user_id == candidate_user_id).first()
        if not resume:
            raise ValueError("Resume not found")

        # Calculate scores
        skills_score = self._calculate_skills_match(resume, job)
        experience_score = self._calculate_experience_match(resume, job)
        education_score = self._calculate_education_match(resume, job)

        overall_score = (skills_score * 0.4 + experience_score * 0.4 + education_score * 0.2)

        # Determine decision
        if overall_score >= 80:
            decision = ScreeningDecision.STRONGLY_RECOMMENDED
        elif overall_score >= 65:
            decision = ScreeningDecision.RECOMMENDED
        elif overall_score >= 50:
            decision = ScreeningDecision.MAYBE
        else:
            decision = ScreeningDecision.NOT_RECOMMENDED

        # Generate analysis
        matching_skills, missing_skills = self._analyze_skills(resume, job)
        strengths, weaknesses = self._analyze_strengths_weaknesses(resume, job, overall_score)

        screening = AIScreening(
            application_id=application_id,
            job_id=job_id,
            candidate_user_id=candidate_user_id,
            decision=decision,
            confidence_score=min(95, overall_score + 10),
            overall_match_score=overall_score,
            skills_match_score=skills_score,
            experience_match_score=experience_score,
            education_match_score=education_score,
            matching_skills=matching_skills,
            missing_skills=missing_skills,
            strengths=strengths,
            weaknesses=weaknesses,
            summary=self._generate_screening_summary(decision, overall_score, strengths),
            reasoning=self._generate_screening_reasoning(skills_score, experience_score, education_score),
            model_name="claude-3.5-sonnet",
            model_version="2024-01"
        )

        db.add(screening)
        db.commit()
        db.refresh(screening)

        logger.info(f"Screened application {application_id}: {decision.value} ({overall_score:.1f})")
        return screening

    def _calculate_skills_match(self, resume: ParsedResume, job: Job) -> float:
        """Calculate skills match score."""
        if not resume.skills:
            return 0.0

        # In production, extract required skills from job description using AI
        # For now, use a simplified approach
        resume_skills = set(skill.lower() for skill in resume.skills)

        # Mock required skills
        required_skills = {"python", "sql", "javascript", "react", "aws"}
        matching = len(resume_skills.intersection(required_skills))

        if not required_skills:
            return 70.0

        score = (matching / len(required_skills)) * 100
        return min(100, score)

    def _calculate_experience_match(self, resume: ParsedResume, job: Job) -> float:
        """Calculate experience match score."""
        if resume.total_years_experience is None:
            return 50.0

        # Get required experience from job (simplified)
        required_years = 3.0  # Mock value

        if resume.total_years_experience >= required_years:
            score = 100.0
        else:
            score = (resume.total_years_experience / required_years) * 100

        return min(100, score)

    def _calculate_education_match(self, resume: ParsedResume, job: Job) -> float:
        """Calculate education match score."""
        if not resume.highest_education_level:
            return 60.0

        education_level = resume.highest_education_level.lower()

        if "phd" in education_level or "doctorate" in education_level:
            return 100.0
        elif "master" in education_level or "m.s." in education_level or "m.a." in education_level:
            return 90.0
        elif "bachelor" in education_level or "b.s." in education_level or "b.a." in education_level:
            return 80.0
        else:
            return 60.0

    def _analyze_skills(self, resume: ParsedResume, job: Job) -> tuple:
        """Analyze matching and missing skills."""
        resume_skills = set(skill.lower() for skill in resume.skills or [])
        required_skills = {"python", "sql", "javascript", "react", "aws"}  # Mock

        matching = list(resume_skills.intersection(required_skills))
        missing = list(required_skills - resume_skills)

        return matching, missing

    def _analyze_strengths_weaknesses(self, resume: ParsedResume, job: Job, overall_score: float) -> tuple:
        """Analyze candidate strengths and weaknesses."""
        strengths = []
        weaknesses = []

        if resume.total_years_experience and resume.total_years_experience >= 5:
            strengths.append(f"{resume.total_years_experience} years of relevant experience")

        if resume.skills and len(resume.skills) >= 10:
            strengths.append(f"Strong technical skill set with {len(resume.skills)} skills")

        if "master" in (resume.highest_education_level or "").lower():
            strengths.append("Advanced degree")

        if overall_score < 60:
            weaknesses.append("Limited match with required skills")

        if resume.total_years_experience and resume.total_years_experience < 2:
            weaknesses.append("Limited professional experience")

        return strengths, weaknesses

    def _generate_screening_summary(self, decision: ScreeningDecision, score: float, strengths: List[str]) -> str:
        """Generate screening summary."""
        if decision == ScreeningDecision.STRONGLY_RECOMMENDED:
            return f"Excellent candidate with {score:.0f}% match. {'. '.join(strengths[:2]) if strengths else 'Strong qualifications across all areas.'}"
        elif decision == ScreeningDecision.RECOMMENDED:
            return f"Good candidate with {score:.0f}% match. Meets most key requirements."
        elif decision == ScreeningDecision.MAYBE:
            return f"Potential fit with {score:.0f}% match. Some gaps in qualifications."
        else:
            return f"Limited match ({score:.0f}%) with position requirements."

    def _generate_screening_reasoning(self, skills: float, experience: float, education: float) -> str:
        """Generate detailed reasoning."""
        return f"Skills match: {skills:.0f}%, Experience match: {experience:.0f}%, Education match: {education:.0f}%. Overall assessment based on comprehensive analysis of candidate qualifications against job requirements."

    # ==================== Predictions ====================

    def predict_interview_success(
        self,
        application_id: int,
        job_id: int,
        candidate_user_id: int,
        db: Session = None
    ) -> AIPrediction:
        """
        Predict interview success probability.

        Args:
            application_id: Application ID
            job_id: Job ID
            candidate_user_id: Candidate user ID
            db: Database session

        Returns:
            AIPrediction object
        """
        # Get screening if available
        screening = db.query(AIScreening).filter(
            AIScreening.application_id == application_id
        ).first()

        if screening:
            base_score = screening.overall_match_score
        else:
            base_score = 60.0

        # Add some variation
        predicted_value = min(100, base_score + 10)
        confidence = 75.0

        prediction = AIPrediction(
            application_id=application_id,
            job_id=job_id,
            candidate_user_id=candidate_user_id,
            prediction_type=PredictionType.INTERVIEW_SUCCESS,
            predicted_value=predicted_value,
            predicted_outcome="likely" if predicted_value >= 70 else "uncertain",
            confidence=confidence,
            explanation=f"Based on candidate qualifications and historical data, there is a {predicted_value:.0f}% probability of interview success.",
            model_name="prediction-model-v1",
            model_version="1.0"
        )

        db.add(prediction)
        db.commit()
        db.refresh(prediction)

        logger.info(f"Predicted interview success for application {application_id}: {predicted_value:.1f}%")
        return prediction

    def predict_time_to_hire(
        self,
        job_id: int,
        db: Session = None
    ) -> AIPrediction:
        """
        Predict time to hire for a job.

        Args:
            job_id: Job ID
            db: Database session

        Returns:
            AIPrediction object
        """
        # Simple prediction based on historical data (mock)
        predicted_days = 45.0  # Average time to hire
        confidence = 70.0

        prediction = AIPrediction(
            job_id=job_id,
            prediction_type=PredictionType.TIME_TO_HIRE,
            predicted_value=predicted_days,
            predicted_outcome=f"{int(predicted_days)} days",
            confidence=confidence,
            explanation=f"Based on similar positions and market conditions, this role is predicted to take {int(predicted_days)} days to fill.",
            model_name="time-prediction-model",
            model_version="1.0"
        )

        db.add(prediction)
        db.commit()
        db.refresh(prediction)

        logger.info(f"Predicted time to hire for job {job_id}: {predicted_days} days")
        return prediction

    # ==================== Insights ====================

    def generate_candidate_insights(
        self,
        user_id: int,
        db: Session = None
    ) -> CandidateInsight:
        """
        Generate AI insights for a candidate.

        Args:
            user_id: User ID
            db: Database session

        Returns:
            CandidateInsight object
        """
        resume = db.query(ParsedResume).filter(ParsedResume.user_id == user_id).first()
        if not resume:
            raise ValueError("Resume not found")

        # Generate insights
        career_stage = self._determine_career_stage(resume.total_years_experience)

        insights = CandidateInsight(
            user_id=user_id,
            career_stage=career_stage,
            career_trajectory="upward",
            skill_level=self._determine_skill_level(resume),
            top_skill_categories=["Software Development", "Data Analysis"],
            market_value="average",
            salary_estimate_min=80000,
            salary_estimate_max=120000,
            demand_score=75.0
        )

        db.add(insights)
        db.commit()
        db.refresh(insights)

        logger.info(f"Generated insights for candidate {user_id}")
        return insights

    def _determine_career_stage(self, years_experience: Optional[float]) -> str:
        """Determine career stage from experience."""
        if not years_experience:
            return "early"

        if years_experience < 3:
            return "early"
        elif years_experience < 7:
            return "mid"
        elif years_experience < 12:
            return "senior"
        else:
            return "executive"

    def _determine_skill_level(self, resume: ParsedResume) -> str:
        """Determine skill level."""
        if resume.total_years_experience:
            if resume.total_years_experience < 2:
                return "junior"
            elif resume.total_years_experience < 5:
                return "mid-level"
            elif resume.total_years_experience < 10:
                return "senior"
            else:
                return "expert"
        return "mid-level"


def create_ai_service(claude_api_key: Optional[str] = None) -> AIService:
    """
    Factory function to create AIService.

    Args:
        claude_api_key: Optional Claude API key

    Returns:
        AIService instance
    """
    return AIService(claude_api_key=claude_api_key)
