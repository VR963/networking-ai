"""
Tests for AI Service - Phase 8.

Comprehensive tests for resume parsing, AI screening, and predictions.
"""

import pytest
from datetime import datetime
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session

from src.networking_ai.database import Base
from src.networking_ai.models import (
    User, UserRole, Company, CompanySize,
    Job, JobStatus, JobType, ExperienceLevel,
    Application, ApplicationStatus
)
from src.networking_ai.models.ai_features import (
    ParsedResume,
    AIScreening,
    AIPrediction,
    CandidateInsight,
    ResumeParseStatus,
    ScreeningDecision,
    PredictionType
)
from src.networking_ai.services.ai_service import (
    AIService,
    create_ai_service
)
from tests.fixtures.sample_resumes import (
    SAMPLE_RESUME_SENIOR_ENGINEER,
    SAMPLE_RESUME_DATA_SCIENTIST,
    SAMPLE_RESUME_JUNIOR_FRONTEND,
    SAMPLE_RESUME_ENTRY_DATA_ANALYST,
    SAMPLE_RESUME_CAREER_CHANGER,
    get_sample_resume
)


# ==================== Test Database Setup ====================

@pytest.fixture(scope="function")
def db_session():
    """Create a test database session."""
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    TestingSessionLocal = sessionmaker(bind=engine)
    session = TestingSessionLocal()

    yield session

    session.close()


@pytest.fixture
def ai_service():
    """Create AI service instance."""
    return create_ai_service()


# ==================== Test Fixtures ====================

@pytest.fixture
def test_user(db_session: Session):
    """Create a test user."""
    user = User(
        email="candidate@example.com",
        hashed_password="hashed_password",
        full_name="Test Candidate",
        role=UserRole.TALENT
    )
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)
    return user


@pytest.fixture
def test_company(db_session: Session):
    """Create a test company."""
    user = User(
        email="company@example.com",
        hashed_password="hashed_password",
        full_name="Company Admin",
        role=UserRole.COMPANY
    )
    db_session.add(user)
    db_session.flush()

    company = Company(
        user_id=user.id,
        company_name="TechCorp",
        industry="Technology",
        company_size=CompanySize.MEDIUM,
        company_description="Technology company"
    )
    db_session.add(company)
    db_session.commit()
    db_session.refresh(company)
    return company


@pytest.fixture
def test_job(db_session: Session, test_company):
    """Create a test job."""
    hiring_manager = User(
        email="manager@example.com",
        hashed_password="hashed_password",
        full_name="Hiring Manager",
        role=UserRole.HIRING_MANAGER
    )
    db_session.add(hiring_manager)
    db_session.flush()

    job = Job(
        company_id=test_company.id,
        hiring_manager_id=hiring_manager.id,
        title="Senior Software Engineer",
        description="Looking for experienced software engineer",
        location="San Francisco, CA",
        job_type=JobType.FULL_TIME,
        experience_level=ExperienceLevel.SENIOR_LEVEL,
        status=JobStatus.ACTIVE
    )
    db_session.add(job)
    db_session.commit()
    db_session.refresh(job)
    return job


@pytest.fixture
def test_application(db_session: Session, test_user, test_job):
    """Create a test application."""
    application = Application(
        user_id=test_user.id,
        job_id=test_job.id,
        talent_user_id=test_user.id,
        status=ApplicationStatus.PENDING
    )
    db_session.add(application)
    db_session.commit()
    db_session.refresh(application)
    return application


# ==================== Resume Parsing Tests ====================

def test_parse_senior_engineer_resume(
    ai_service: AIService,
    db_session: Session,
    test_user
):
    """Test parsing a senior engineer resume."""
    parsed = ai_service.parse_resume(
        user_id=test_user.id,
        resume_text=SAMPLE_RESUME_SENIOR_ENGINEER,
        source_file_name="john_doe_resume.pdf",
        db=db_session
    )

    assert parsed is not None
    assert parsed.user_id == test_user.id
    assert parsed.parsing_status == ResumeParseStatus.COMPLETED
    assert parsed.email == "john.doe@email.com"
    assert parsed.phone == "+1-555-123-4567"
    assert "linkedin.com/in/johndoe" in (parsed.linkedin_url or "")
    assert "github.com/johndoe" in (parsed.github_url or "")
    assert len(parsed.skills) > 0
    assert parsed.total_years_experience is not None
    assert parsed.total_years_experience >= 8.0  # Should detect 8+ years
    assert parsed.parsing_confidence is not None


def test_parse_data_scientist_resume(
    ai_service: AIService,
    db_session: Session,
    test_user
):
    """Test parsing a data scientist resume."""
    parsed = ai_service.parse_resume(
        user_id=test_user.id,
        resume_text=SAMPLE_RESUME_DATA_SCIENTIST,
        db=db_session
    )

    assert parsed is not None
    assert parsed.parsing_status == ResumeParseStatus.COMPLETED
    assert parsed.email == "jane.smith@email.com"
    assert len(parsed.skills) > 0
    assert parsed.education is not None
    assert len(parsed.education) >= 2  # Should detect both MS and BS


def test_parse_junior_frontend_resume(
    ai_service: AIService,
    db_session: Session,
    test_user
):
    """Test parsing a junior frontend developer resume."""
    parsed = ai_service.parse_resume(
        user_id=test_user.id,
        resume_text=SAMPLE_RESUME_JUNIOR_FRONTEND,
        db=db_session
    )

    assert parsed is not None
    assert parsed.parsing_status == ResumeParseStatus.COMPLETED
    assert parsed.email == "alex.johnson@email.com"
    assert parsed.total_years_experience is not None
    assert parsed.total_years_experience < 3  # Junior developer


def test_parse_career_changer_resume(
    ai_service: AIService,
    db_session: Session,
    test_user
):
    """Test parsing a career changer resume."""
    parsed = ai_service.parse_resume(
        user_id=test_user.id,
        resume_text=SAMPLE_RESUME_CAREER_CHANGER,
        db=db_session
    )

    assert parsed is not None
    assert parsed.parsing_status == ResumeParseStatus.COMPLETED
    assert parsed.email == "david.martinez@email.com"
    assert len(parsed.skills) > 0


def test_update_existing_resume(
    ai_service: AIService,
    db_session: Session,
    test_user
):
    """Test updating an existing parsed resume."""
    # Parse first resume
    parsed1 = ai_service.parse_resume(
        user_id=test_user.id,
        resume_text=SAMPLE_RESUME_JUNIOR_FRONTEND,
        db=db_session
    )

    first_id = parsed1.id

    # Parse second resume for same user (should update)
    parsed2 = ai_service.parse_resume(
        user_id=test_user.id,
        resume_text=SAMPLE_RESUME_SENIOR_ENGINEER,
        db=db_session
    )

    assert parsed2.id == first_id  # Should be same record
    assert parsed2.email == "john.doe@email.com"  # Should have new data


# ==================== AI Screening Tests ====================

def test_screen_application_strong_candidate(
    ai_service: AIService,
    db_session: Session,
    test_user,
    test_job,
    test_application
):
    """Test screening a strong candidate."""
    # First parse resume
    ai_service.parse_resume(
        user_id=test_user.id,
        resume_text=SAMPLE_RESUME_SENIOR_ENGINEER,
        db=db_session
    )

    # Then screen
    screening = ai_service.screen_application(
        application_id=test_application.id,
        job_id=test_job.id,
        candidate_user_id=test_user.id,
        db=db_session
    )

    assert screening is not None
    assert screening.application_id == test_application.id
    assert screening.decision in [ScreeningDecision.STRONGLY_RECOMMENDED, ScreeningDecision.RECOMMENDED]
    assert screening.overall_match_score > 0
    assert screening.skills_match_score >= 0
    assert screening.experience_match_score >= 0
    assert screening.education_match_score >= 0
    assert screening.confidence_score > 0
    assert len(screening.summary) > 0
    assert len(screening.reasoning) > 0


def test_screen_application_junior_candidate(
    ai_service: AIService,
    db_session: Session,
    test_user,
    test_job,
    test_application
):
    """Test screening a junior candidate for senior role."""
    # Parse junior resume
    ai_service.parse_resume(
        user_id=test_user.id,
        resume_text=SAMPLE_RESUME_JUNIOR_FRONTEND,
        db=db_session
    )

    # Screen for senior role
    screening = ai_service.screen_application(
        application_id=test_application.id,
        job_id=test_job.id,
        candidate_user_id=test_user.id,
        db=db_session
    )

    assert screening is not None
    # Junior candidate for senior role should get lower score
    assert screening.overall_match_score < 80


def test_screening_without_resume_fails(
    ai_service: AIService,
    db_session: Session,
    test_user,
    test_job,
    test_application
):
    """Test that screening fails without a parsed resume."""
    with pytest.raises(ValueError):
        ai_service.screen_application(
            application_id=test_application.id,
            job_id=test_job.id,
            candidate_user_id=test_user.id,
            db=db_session
        )


def test_screening_analysis_components(
    ai_service: AIService,
    db_session: Session,
    test_user,
    test_job,
    test_application
):
    """Test that screening includes all analysis components."""
    ai_service.parse_resume(
        user_id=test_user.id,
        resume_text=SAMPLE_RESUME_DATA_SCIENTIST,
        db=db_session
    )

    screening = ai_service.screen_application(
        application_id=test_application.id,
        job_id=test_job.id,
        candidate_user_id=test_user.id,
        db=db_session
    )

    # Check all analysis components are present
    assert isinstance(screening.matching_skills, list)
    assert isinstance(screening.missing_skills, list)
    assert isinstance(screening.strengths, list)
    assert isinstance(screening.weaknesses, list)
    assert screening.summary is not None
    assert screening.reasoning is not None
    assert screening.model_name is not None


# ==================== Prediction Tests ====================

def test_predict_interview_success(
    ai_service: AIService,
    db_session: Session,
    test_user,
    test_job,
    test_application
):
    """Test predicting interview success."""
    # Setup: Parse resume and screen
    ai_service.parse_resume(
        user_id=test_user.id,
        resume_text=SAMPLE_RESUME_SENIOR_ENGINEER,
        db=db_session
    )

    ai_service.screen_application(
        application_id=test_application.id,
        job_id=test_job.id,
        candidate_user_id=test_user.id,
        db=db_session
    )

    # Predict
    prediction = ai_service.predict_interview_success(
        application_id=test_application.id,
        job_id=test_job.id,
        candidate_user_id=test_user.id,
        db=db_session
    )

    assert prediction is not None
    assert prediction.prediction_type == PredictionType.INTERVIEW_SUCCESS
    assert 0 <= prediction.predicted_value <= 100
    assert 0 <= prediction.confidence <= 100
    assert prediction.predicted_outcome is not None
    assert prediction.explanation is not None


def test_predict_time_to_hire(
    ai_service: AIService,
    db_session: Session,
    test_job
):
    """Test predicting time to hire."""
    prediction = ai_service.predict_time_to_hire(
        job_id=test_job.id,
        db=db_session
    )

    assert prediction is not None
    assert prediction.prediction_type == PredictionType.TIME_TO_HIRE
    assert prediction.predicted_value > 0  # Should be positive number of days
    assert prediction.confidence > 0
    assert prediction.explanation is not None


def test_prediction_accuracy_calculation():
    """Test prediction accuracy calculation."""
    prediction = AIPrediction(
        application_id=1,
        prediction_type=PredictionType.INTERVIEW_SUCCESS,
        predicted_value=80.0,
        confidence=75.0,
        actual_value=85.0  # Actual outcome
    )

    accuracy = prediction.calculate_accuracy()

    assert accuracy is not None
    assert 0 <= accuracy <= 100
    assert accuracy > 90  # Should be high accuracy for 5-point difference


# ==================== Candidate Insights Tests ====================

def test_generate_candidate_insights(
    ai_service: AIService,
    db_session: Session,
    test_user
):
    """Test generating candidate insights."""
    # First parse resume
    ai_service.parse_resume(
        user_id=test_user.id,
        resume_text=SAMPLE_RESUME_SENIOR_ENGINEER,
        db=db_session
    )

    # Generate insights
    insights = ai_service.generate_candidate_insights(
        user_id=test_user.id,
        db=db_session
    )

    assert insights is not None
    assert insights.user_id == test_user.id
    assert insights.career_stage in ["early", "mid", "senior", "executive"]
    assert insights.skill_level in ["junior", "mid-level", "senior", "expert"]
    assert insights.salary_estimate_min is not None
    assert insights.salary_estimate_max is not None
    assert insights.salary_estimate_max > insights.salary_estimate_min


def test_career_stage_determination(
    ai_service: AIService,
    db_session: Session,
    test_user
):
    """Test career stage determination based on experience."""
    # Test with junior candidate
    parsed = ParsedResume(
        user_id=test_user.id,
        total_years_experience=2.0,
        parsing_status=ResumeParseStatus.COMPLETED
    )
    career_stage = ai_service._determine_career_stage(parsed.total_years_experience)
    assert career_stage == "early"

    # Test with mid-level candidate
    parsed.total_years_experience = 5.0
    career_stage = ai_service._determine_career_stage(parsed.total_years_experience)
    assert career_stage == "mid"

    # Test with senior candidate
    parsed.total_years_experience = 10.0
    career_stage = ai_service._determine_career_stage(parsed.total_years_experience)
    assert career_stage == "senior"


# ==================== Helper Method Tests ====================

def test_calculate_total_experience(ai_service: AIService):
    """Test total experience calculation."""
    work_experience = [
        {
            "start_date": "2020-01-01",
            "end_date": "2022-01-01"
        },
        {
            "start_date": "2022-02-01",
            "end_date": None  # Current job
        }
    ]

    total = ai_service._calculate_total_experience(work_experience)

    assert total > 2.0  # At least 2 years from first job
    assert total > 0


def test_get_highest_education(ai_service: AIService):
    """Test highest education level detection."""
    education = [
        {"degree": "Bachelor of Science"},
        {"degree": "Master of Science"}
    ]

    highest = ai_service._get_highest_education(education)

    assert highest is not None
    assert "master" in highest.lower()


def test_skills_match_calculation(
    ai_service: AIService,
    db_session: Session,
    test_user,
    test_job
):
    """Test skills match score calculation."""
    parsed = ParsedResume(
        user_id=test_user.id,
        skills=["Python", "JavaScript", "SQL", "React", "AWS", "Docker"],
        parsing_status=ResumeParseStatus.COMPLETED
    )
    db_session.add(parsed)
    db_session.commit()

    score = ai_service._calculate_skills_match(parsed, test_job)

    assert 0 <= score <= 100
    assert score > 0  # Should have some skills match


def test_experience_match_calculation(
    ai_service: AIService,
    test_job
):
    """Test experience match score calculation."""
    # Test with sufficient experience
    parsed_senior = ParsedResume(
        user_id=1,
        total_years_experience=8.0,
        parsing_status=ResumeParseStatus.COMPLETED
    )

    score_senior = ai_service._calculate_experience_match(parsed_senior, test_job)
    assert score_senior >= 80  # Senior candidate should score high

    # Test with junior experience
    parsed_junior = ParsedResume(
        user_id=2,
        total_years_experience=1.5,
        parsing_status=ResumeParseStatus.COMPLETED
    )

    score_junior = ai_service._calculate_experience_match(parsed_junior, test_job)
    assert score_junior < score_senior  # Junior should score lower


# ==================== Integration Tests ====================

def test_full_ai_pipeline(
    ai_service: AIService,
    db_session: Session,
    test_user,
    test_job,
    test_application
):
    """Test the complete AI pipeline: parse → screen → predict."""
    # Step 1: Parse resume
    parsed = ai_service.parse_resume(
        user_id=test_user.id,
        resume_text=SAMPLE_RESUME_SENIOR_ENGINEER,
        db=db_session
    )
    assert parsed.parsing_status == ResumeParseStatus.COMPLETED

    # Step 2: Screen application
    screening = ai_service.screen_application(
        application_id=test_application.id,
        job_id=test_job.id,
        candidate_user_id=test_user.id,
        db=db_session
    )
    assert screening.decision is not None

    # Step 3: Predict interview success
    prediction = ai_service.predict_interview_success(
        application_id=test_application.id,
        job_id=test_job.id,
        candidate_user_id=test_user.id,
        db=db_session
    )
    assert prediction.predicted_value > 0

    # Step 4: Generate insights
    insights = ai_service.generate_candidate_insights(
        user_id=test_user.id,
        db=db_session
    )
    assert insights.career_stage is not None


def test_screening_multiple_candidates(
    ai_service: AIService,
    db_session: Session,
    test_job
):
    """Test screening multiple candidates and comparing results."""
    candidates_data = [
        ("senior@example.com", SAMPLE_RESUME_SENIOR_ENGINEER),
        ("junior@example.com", SAMPLE_RESUME_JUNIOR_FRONTEND),
        ("data@example.com", SAMPLE_RESUME_DATA_SCIENTIST)
    ]

    screenings = []

    for email, resume_text in candidates_data:
        # Create user
        user = User(
            email=email,
            hashed_password="hashed",
            full_name=email.split("@")[0],
            role=UserRole.TALENT
        )
        db_session.add(user)
        db_session.flush()

        # Create application
        application = Application(
            user_id=user.id,
            job_id=test_job.id,
            talent_user_id=user.id,
            status=ApplicationStatus.PENDING
        )
        db_session.add(application)
        db_session.flush()

        # Parse and screen
        ai_service.parse_resume(
            user_id=user.id,
            resume_text=resume_text,
            db=db_session
        )

        screening = ai_service.screen_application(
            application_id=application.id,
            job_id=test_job.id,
            candidate_user_id=user.id,
            db=db_session
        )

        screenings.append(screening)

    db_session.commit()

    # Verify we got screenings for all candidates
    assert len(screenings) == 3

    # Senior engineer should generally score highest for senior role
    senior_screening = screenings[0]
    assert senior_screening.overall_match_score > 0
