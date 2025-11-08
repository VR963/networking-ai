"""
Advanced AI Features Models - Phase 8.

Models for resume parsing, AI screening, and predictions.
"""

from datetime import datetime
from enum import Enum
from typing import Optional, Dict, Any, List
from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, Boolean, Text, JSON, Float, Enum as SQLEnum
from sqlalchemy.orm import relationship

from ..database import Base


class ResumeParseStatus(str, Enum):
    """Resume parsing status."""
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"


class ScreeningDecision(str, Enum):
    """AI screening decision."""
    STRONGLY_RECOMMENDED = "strongly_recommended"
    RECOMMENDED = "recommended"
    MAYBE = "maybe"
    NOT_RECOMMENDED = "not_recommended"
    REJECTED = "rejected"


class PredictionType(str, Enum):
    """Type of prediction."""
    JOB_MATCH = "job_match"
    INTERVIEW_SUCCESS = "interview_success"
    OFFER_ACCEPTANCE = "offer_acceptance"
    CANDIDATE_QUALITY = "candidate_quality"
    TIME_TO_HIRE = "time_to_hire"
    ATTRITION_RISK = "attrition_risk"


class ParsedResume(Base):
    """
    Parsed resume data.

    Stores structured data extracted from resume documents.
    """
    __tablename__ = "parsed_resumes"

    # Primary Key
    id = Column(Integer, primary_key=True, index=True)

    # Owner
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, unique=True, index=True)

    # Source
    source_file_url = Column(String(1000), nullable=True)
    source_file_name = Column(String(500), nullable=True)
    source_text = Column(Text, nullable=True)

    # Contact Information
    email = Column(String(255), nullable=True)
    phone = Column(String(50), nullable=True)
    location = Column(String(255), nullable=True)
    linkedin_url = Column(String(500), nullable=True)
    github_url = Column(String(500), nullable=True)
    portfolio_url = Column(String(500), nullable=True)
    website = Column(String(500), nullable=True)

    # Personal Information
    full_name = Column(String(255), nullable=True)
    professional_title = Column(String(255), nullable=True)
    summary = Column(Text, nullable=True)

    # Structured Data
    work_experience = Column(JSON, default=list)  # List of work experiences
    education = Column(JSON, default=list)  # List of education entries
    skills = Column(JSON, default=list)  # List of skills
    certifications = Column(JSON, default=list)  # List of certifications
    languages = Column(JSON, default=list)  # List of languages
    projects = Column(JSON, default=list)  # List of projects
    publications = Column(JSON, default=list)  # List of publications
    awards = Column(JSON, default=list)  # List of awards

    # Derived Information
    total_years_experience = Column(Float, nullable=True)
    highest_education_level = Column(String(100), nullable=True)
    top_skills = Column(JSON, default=list)  # Top 10 skills
    industry_experience = Column(JSON, default=list)  # Industries worked in
    company_names = Column(JSON, default=list)  # Previous companies

    # AI Analysis
    ai_summary = Column(Text, nullable=True)
    key_achievements = Column(JSON, default=list)
    career_trajectory = Column(String(100), nullable=True)  # upward, stable, varied
    specializations = Column(JSON, default=list)

    # Metadata
    parsing_status = Column(SQLEnum(ResumeParseStatus), default=ResumeParseStatus.PENDING, index=True)
    parsing_confidence = Column(Float, nullable=True)  # 0-100
    parsing_errors = Column(JSON, default=list)

    # Embeddings
    resume_embedding = Column(Text, nullable=True)  # Vector embedding for semantic search

    # Timestamps
    parsed_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, index=True)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    user = relationship("User", foreign_keys=[user_id], back_populates="parsed_resume")

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "id": self.id,
            "full_name": self.full_name,
            "professional_title": self.professional_title,
            "email": self.email,
            "phone": self.phone,
            "location": self.location,
            "summary": self.summary,
            "total_years_experience": self.total_years_experience,
            "highest_education_level": self.highest_education_level,
            "top_skills": self.top_skills,
            "work_experience": self.work_experience,
            "education": self.education,
            "parsing_status": self.parsing_status.value if self.parsing_status else None,
        }


class AIScreening(Base):
    """
    AI screening result for application.

    Stores AI-powered screening analysis and recommendations.
    """
    __tablename__ = "ai_screenings"

    # Primary Key
    id = Column(Integer, primary_key=True, index=True)

    # Application
    application_id = Column(Integer, ForeignKey("applications.id"), nullable=False, unique=True, index=True)
    job_id = Column(Integer, ForeignKey("jobs.id"), nullable=False, index=True)
    candidate_user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)

    # Decision
    decision = Column(SQLEnum(ScreeningDecision), nullable=False, index=True)
    confidence_score = Column(Float, nullable=False)  # 0-100

    # Scores (0-100 each)
    overall_match_score = Column(Float, nullable=False)
    skills_match_score = Column(Float, nullable=False)
    experience_match_score = Column(Float, nullable=False)
    education_match_score = Column(Float, nullable=False)
    cultural_fit_score = Column(Float, nullable=True)
    communication_score = Column(Float, nullable=True)

    # Detailed Analysis
    matching_skills = Column(JSON, default=list)  # Skills that match job requirements
    missing_skills = Column(JSON, default=list)  # Required skills candidate lacks
    bonus_skills = Column(JSON, default=list)  # Extra skills candidate has
    experience_relevance = Column(JSON, default=dict)  # Relevant experience breakdown

    # Strengths and Weaknesses
    strengths = Column(JSON, default=list)  # List of candidate strengths
    weaknesses = Column(JSON, default=list)  # List of areas for improvement
    red_flags = Column(JSON, default=list)  # Potential concerns

    # Recommendations
    interview_questions = Column(JSON, default=list)  # Suggested interview questions
    focus_areas = Column(JSON, default=list)  # Areas to focus on in interview
    role_recommendations = Column(JSON, default=list)  # Alternative roles that might fit

    # Summary
    summary = Column(Text, nullable=False)
    reasoning = Column(Text, nullable=False)

    # AI Model Info
    model_version = Column(String(100), nullable=True)
    model_name = Column(String(100), nullable=True)

    # Timestamps
    screened_at = Column(DateTime, default=datetime.utcnow, index=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    # Relationships
    application = relationship("Application", foreign_keys=[application_id])
    job = relationship("Job", foreign_keys=[job_id])
    candidate = relationship("User", foreign_keys=[candidate_user_id])

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "id": self.id,
            "decision": self.decision.value if self.decision else None,
            "confidence_score": self.confidence_score,
            "overall_match_score": self.overall_match_score,
            "skills_match_score": self.skills_match_score,
            "experience_match_score": self.experience_match_score,
            "education_match_score": self.education_match_score,
            "matching_skills": self.matching_skills,
            "missing_skills": self.missing_skills,
            "strengths": self.strengths,
            "weaknesses": self.weaknesses,
            "summary": self.summary,
            "screened_at": self.screened_at.isoformat() if self.screened_at else None,
        }


class AIPrediction(Base):
    """
    AI prediction for various hiring outcomes.

    Machine learning predictions for hiring success.
    """
    __tablename__ = "ai_predictions"

    # Primary Key
    id = Column(Integer, primary_key=True, index=True)

    # Subject
    application_id = Column(Integer, ForeignKey("applications.id"), nullable=True, index=True)
    job_id = Column(Integer, ForeignKey("jobs.id"), nullable=True, index=True)
    candidate_user_id = Column(Integer, ForeignKey("users.id"), nullable=True, index=True)

    # Prediction Type
    prediction_type = Column(SQLEnum(PredictionType), nullable=False, index=True)

    # Prediction
    predicted_value = Column(Float, nullable=False)  # 0-100 for scores, days for time predictions
    predicted_outcome = Column(String(100), nullable=True)  # success, failure, high, low, etc.
    confidence = Column(Float, nullable=False)  # 0-100

    # Supporting Data
    features_used = Column(JSON, default=dict)  # Features used for prediction
    feature_importance = Column(JSON, default=dict)  # Importance of each feature
    similar_cases = Column(JSON, default=list)  # Similar historical cases

    # Explanation
    explanation = Column(Text, nullable=True)
    factors = Column(JSON, default=list)  # Key factors influencing prediction

    # Model Info
    model_version = Column(String(100), nullable=True)
    model_name = Column(String(100), nullable=True)
    model_accuracy = Column(Float, nullable=True)

    # Actual Outcome (for model training)
    actual_value = Column(Float, nullable=True)
    actual_outcome = Column(String(100), nullable=True)
    outcome_recorded_at = Column(DateTime, nullable=True)

    # Timestamps
    predicted_at = Column(DateTime, default=datetime.utcnow, index=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    # Relationships
    application = relationship("Application", foreign_keys=[application_id])
    job = relationship("Job", foreign_keys=[job_id])
    candidate = relationship("User", foreign_keys=[candidate_user_id])

    def calculate_accuracy(self) -> Optional[float]:
        """Calculate prediction accuracy if actual outcome is known."""
        if self.actual_value is None:
            return None

        error = abs(self.predicted_value - self.actual_value)
        max_error = 100  # Assuming 0-100 scale
        accuracy = max(0, (1 - (error / max_error)) * 100)
        return accuracy


class SkillTaxonomy(Base):
    """
    Skill taxonomy and relationships.

    Hierarchical skill structure with synonyms and relationships.
    """
    __tablename__ = "skill_taxonomy"

    # Primary Key
    id = Column(Integer, primary_key=True, index=True)

    # Skill Details
    skill_name = Column(String(255), nullable=False, unique=True, index=True)
    skill_category = Column(String(100), nullable=True, index=True)
    skill_level = Column(String(50), nullable=True)  # beginner, intermediate, advanced, expert

    # Hierarchy
    parent_skill_id = Column(Integer, ForeignKey("skill_taxonomy.id"), nullable=True)

    # Synonyms and Variations
    synonyms = Column(JSON, default=list)  # Alternative names for this skill
    related_skills = Column(JSON, default=list)  # Related skill IDs

    # Metadata
    description = Column(Text, nullable=True)
    popularity = Column(Integer, default=0)  # How often this skill appears
    demand_score = Column(Float, default=0.0)  # Industry demand for this skill

    # Embedding
    skill_embedding = Column(Text, nullable=True)  # Vector embedding

    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    parent = relationship("SkillTaxonomy", remote_side=[id], foreign_keys=[parent_skill_id])


class AIModelMetrics(Base):
    """
    AI model performance metrics.

    Tracks accuracy and performance of AI models over time.
    """
    __tablename__ = "ai_model_metrics"

    # Primary Key
    id = Column(Integer, primary_key=True, index=True)

    # Model Info
    model_name = Column(String(100), nullable=False, index=True)
    model_version = Column(String(100), nullable=False, index=True)
    model_type = Column(String(100), nullable=False)  # screening, prediction, parsing, etc.

    # Metrics
    accuracy = Column(Float, nullable=True)
    precision = Column(Float, nullable=True)
    recall = Column(Float, nullable=True)
    f1_score = Column(Float, nullable=True)
    auc_roc = Column(Float, nullable=True)

    # Counts
    total_predictions = Column(Integer, default=0)
    correct_predictions = Column(Integer, default=0)
    false_positives = Column(Integer, default=0)
    false_negatives = Column(Integer, default=0)

    # Performance
    avg_processing_time_ms = Column(Float, nullable=True)
    avg_confidence_score = Column(Float, nullable=True)

    # Metadata
    training_data_size = Column(Integer, nullable=True)
    training_date = Column(DateTime, nullable=True)
    hyperparameters = Column(JSON, default=dict)

    # Time Period
    period_start = Column(DateTime, nullable=True, index=True)
    period_end = Column(DateTime, nullable=True)

    # Timestamps
    calculated_at = Column(DateTime, default=datetime.utcnow, index=True)


class CandidateInsight(Base):
    """
    AI-generated insights about candidates.

    Comprehensive AI analysis of candidate potential.
    """
    __tablename__ = "candidate_insights"

    # Primary Key
    id = Column(Integer, primary_key=True, index=True)

    # Candidate
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, unique=True, index=True)

    # Career Insights
    career_stage = Column(String(100), nullable=True)  # early, mid, senior, executive
    career_trajectory = Column(String(100), nullable=True)  # upward, stable, transitioning
    specialization = Column(String(255), nullable=True)
    potential_roles = Column(JSON, default=list)  # Suggested roles based on profile

    # Skill Analysis
    skill_level = Column(String(50), nullable=True)  # junior, mid-level, senior, expert
    top_skill_categories = Column(JSON, default=list)
    skill_gaps = Column(JSON, default=list)  # Skills to develop
    learning_recommendations = Column(JSON, default=list)

    # Market Analysis
    market_value = Column(String(50), nullable=True)  # below, average, above market
    salary_estimate_min = Column(Integer, nullable=True)
    salary_estimate_max = Column(Integer, nullable=True)
    demand_score = Column(Float, nullable=True)  # 0-100, how in-demand this profile is

    # Behavioral Insights
    communication_style = Column(String(100), nullable=True)
    work_preferences = Column(JSON, default=dict)
    culture_fit_indicators = Column(JSON, default=list)

    # Recommendations
    job_recommendations = Column(JSON, default=list)  # Job IDs and match scores
    company_recommendations = Column(JSON, default=list)  # Company types that fit well
    development_plan = Column(JSON, default=list)  # Career development suggestions

    # Timestamps
    generated_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    user = relationship("User", foreign_keys=[user_id])


class JobInsight(Base):
    """
    AI-generated insights about job postings.

    Analysis of job requirements and market positioning.
    """
    __tablename__ = "job_insights"

    # Primary Key
    id = Column(Integer, primary_key=True, index=True)

    # Job
    job_id = Column(Integer, ForeignKey("jobs.id"), nullable=False, unique=True, index=True)

    # Market Analysis
    competitiveness = Column(String(50), nullable=True)  # highly_competitive, competitive, good, excellent
    market_demand = Column(Float, nullable=True)  # 0-100
    candidate_pool_size = Column(String(50), nullable=True)  # small, medium, large
    avg_time_to_fill = Column(Integer, nullable=True)  # days

    # Salary Analysis
    salary_competitiveness = Column(String(50), nullable=True)  # below, at, above market
    market_salary_min = Column(Integer, nullable=True)
    market_salary_max = Column(Integer, nullable=True)

    # Requirements Analysis
    requirements_clarity = Column(Float, nullable=True)  # 0-100
    requirements_realistic = Column(Boolean, nullable=True)
    nice_to_have_vs_required = Column(JSON, default=dict)

    # Optimization Suggestions
    title_suggestions = Column(JSON, default=list)
    description_improvements = Column(JSON, default=list)
    skill_prioritization = Column(JSON, default=list)  # Which skills to emphasize
    similar_successful_jobs = Column(JSON, default=list)

    # Predictions
    predicted_applications = Column(Integer, nullable=True)
    predicted_time_to_hire = Column(Integer, nullable=True)  # days
    predicted_quality_score = Column(Float, nullable=True)  # 0-100

    # Timestamps
    generated_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    job = relationship("Job", foreign_keys=[job_id])
