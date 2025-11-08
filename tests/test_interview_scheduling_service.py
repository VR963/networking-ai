"""
Tests for Interview Scheduling Service - Phase 4.

Tests cover:
- Availability management
- Interview scheduling
- Finding available slots
- Confirmations
- Rescheduling
- Cancellations
- Reminders
- Query methods
"""

import pytest
from datetime import datetime, timedelta
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from src.networking_ai.database import Base
from src.networking_ai.models.user import User, UserRole
from src.networking_ai.models.company import Company, CompanySize
from src.networking_ai.models.job import Job, JobStatus, JobType, ExperienceLevel
from src.networking_ai.models.application import Application, ApplicationStatus
from src.networking_ai.models.interview import (
    Interview,
    InterviewAvailability,
    InterviewStage,
    InterviewStatus,
    InterviewFormat
)
from src.networking_ai.services.interview_scheduling_service import (
    InterviewSchedulingService,
    create_interview_scheduling_service
)


# ==================== Fixtures ====================

@pytest.fixture
def db_session():
    """Create in-memory database session for testing."""
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    SessionLocal = sessionmaker(bind=engine)
    session = SessionLocal()
    yield session
    session.close()


@pytest.fixture
def candidate_user(db_session):
    """Create test candidate user."""
    user = User(
        email="candidate@test.com",
        hashed_password="hashed_pwd_123",
        full_name="Test Candidate",
        role=UserRole.TALENT,
        is_active=True
    )
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)
    return user


@pytest.fixture
def interviewer_user(db_session):
    """Create test interviewer user."""
    user = User(
        email="interviewer@test.com",
        hashed_password="hashed_pwd_456",
        full_name="Test Interviewer",
        role=UserRole.HIRING_MANAGER,
        is_active=True
    )
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)
    return user


@pytest.fixture
def company(db_session, interviewer_user):
    """Create test company."""
    company = Company(
        user_id=interviewer_user.id,
        company_name="Test Company",
        industry="Technology",
        company_size=CompanySize.MEDIUM,
        company_description="Test company for interviews"
    )
    db_session.add(company)
    db_session.commit()
    db_session.refresh(company)
    return company


@pytest.fixture
def job(db_session, company, interviewer_user):
    """Create test job."""
    job = Job(
        title="Senior Engineer",
        company_id=company.id,
        hiring_manager_id=interviewer_user.id,
        description="Test job description for a senior engineering role",
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
def application(db_session, job, candidate_user):
    """Create test application."""
    app = Application(
        job_id=job.id,
        talent_user_id=candidate_user.id,
        status=ApplicationStatus.REVIEWING
    )
    db_session.add(app)
    db_session.commit()
    db_session.refresh(app)
    return app


@pytest.fixture
def scheduling_service():
    """Create interview scheduling service."""
    return create_interview_scheduling_service(
        enable_notifications=False  # Disable for tests
    )


# ==================== Availability Tests ====================

def test_add_availability(scheduling_service, interviewer_user, db_session):
    """Test adding interviewer availability."""
    start_time = datetime.utcnow() + timedelta(days=1, hours=9)
    end_time = start_time + timedelta(hours=8)

    availability = scheduling_service.add_availability(
        user_id=interviewer_user.id,
        start_time=start_time,
        end_time=end_time,
        timezone="America/New_York",
        max_interviews_per_day=5,
        db=db_session
    )

    assert availability.id is not None
    assert availability.user_id == interviewer_user.id
    assert availability.start_time == start_time
    assert availability.end_time == end_time
    assert availability.timezone == "America/New_York"
    assert availability.max_interviews_per_day == 5
    assert availability.is_available == True


def test_add_recurring_availability(scheduling_service, interviewer_user, db_session):
    """Test adding recurring availability."""
    start_time = datetime.utcnow() + timedelta(days=1, hours=9)
    end_time = start_time + timedelta(hours=8)

    availability = scheduling_service.add_availability(
        user_id=interviewer_user.id,
        start_time=start_time,
        end_time=end_time,
        is_recurring=True,
        recurrence_rule="FREQ=WEEKLY;BYDAY=MO,TU,WE,TH,FR",
        db=db_session
    )

    assert availability.is_recurring == True
    assert availability.recurrence_rule is not None


def test_get_interviewer_availability(scheduling_service, interviewer_user, db_session):
    """Test getting interviewer availability."""
    # Add availability for next week
    start_time = datetime.utcnow() + timedelta(days=7, hours=9)
    end_time = start_time + timedelta(hours=8)

    scheduling_service.add_availability(
        user_id=interviewer_user.id,
        start_time=start_time,
        end_time=end_time,
        db=db_session
    )

    # Query availability
    search_start = datetime.utcnow()
    search_end = datetime.utcnow() + timedelta(days=14)

    slots = scheduling_service.get_interviewer_availability(
        user_id=interviewer_user.id,
        start_date=search_start,
        end_date=search_end,
        db=db_session
    )

    assert len(slots) == 1
    assert slots[0].user_id == interviewer_user.id


# ==================== Finding Available Slots ====================

def test_find_available_slots_empty(scheduling_service, interviewer_user, db_session):
    """Test finding slots with no availability."""
    start_date = datetime.utcnow() + timedelta(days=1)
    end_date = start_date + timedelta(days=7)

    slots = scheduling_service.find_available_slots(
        interviewer_user_id=interviewer_user.id,
        start_date=start_date,
        end_date=end_date,
        duration_minutes=60,
        db=db_session
    )

    assert len(slots) == 0


def test_find_available_slots_with_availability(scheduling_service, interviewer_user, db_session):
    """Test finding available slots."""
    # Add 4-hour availability block
    start_time = datetime.utcnow() + timedelta(days=1, hours=9)
    end_time = start_time + timedelta(hours=4)

    scheduling_service.add_availability(
        user_id=interviewer_user.id,
        start_time=start_time,
        end_time=end_time,
        db=db_session
    )

    # Find slots
    slots = scheduling_service.find_available_slots(
        interviewer_user_id=interviewer_user.id,
        start_date=start_time,
        end_date=end_time,
        duration_minutes=60,
        db=db_session
    )

    # Should have slots (30-minute increments in 4-hour block)
    assert len(slots) > 0
    # Each slot should have required fields
    for slot in slots:
        assert "start_time" in slot
        assert "end_time" in slot
        assert "duration_minutes" in slot
        assert slot["duration_minutes"] == 60


def test_find_available_slots_excludes_booked(
    scheduling_service,
    interviewer_user,
    candidate_user,
    application,
    job,
    company,
    db_session
):
    """Test that booked slots are excluded."""
    # Add availability
    start_time = datetime.utcnow() + timedelta(days=1, hours=9)
    end_time = start_time + timedelta(hours=4)

    scheduling_service.add_availability(
        user_id=interviewer_user.id,
        start_time=start_time,
        end_time=end_time,
        db=db_session
    )

    # Book an interview at 10 AM
    booked_time = start_time + timedelta(hours=1)
    scheduling_service.schedule_interview(
        application_id=application.id,
        job_id=job.id,
        company_id=company.id,
        candidate_user_id=candidate_user.id,
        interviewer_user_id=interviewer_user.id,
        stage=InterviewStage.PHONE_SCREEN,
        scheduled_at=booked_time,
        duration_minutes=60,
        db=db_session
    )

    # Find available slots
    slots = scheduling_service.find_available_slots(
        interviewer_user_id=interviewer_user.id,
        start_date=start_time,
        end_date=end_time,
        duration_minutes=60,
        db=db_session
    )

    # Verify booked slot is not in available slots
    booked_slot_times = [s["start_time"] for s in slots]
    assert booked_time not in booked_slot_times


# ==================== Interview Scheduling Tests ====================

def test_schedule_interview(
    scheduling_service,
    application,
    job,
    company,
    candidate_user,
    interviewer_user,
    db_session
):
    """Test scheduling an interview."""
    scheduled_at = datetime.utcnow() + timedelta(days=2, hours=10)

    interview = scheduling_service.schedule_interview(
        application_id=application.id,
        job_id=job.id,
        company_id=company.id,
        candidate_user_id=candidate_user.id,
        interviewer_user_id=interviewer_user.id,
        stage=InterviewStage.TECHNICAL,
        scheduled_at=scheduled_at,
        duration_minutes=90,
        format=InterviewFormat.VIDEO,
        timezone="America/New_York",
        meeting_url="https://zoom.us/j/123456",
        db=db_session
    )

    assert interview.id is not None
    assert interview.application_id == application.id
    assert interview.job_id == job.id
    assert interview.candidate_user_id == candidate_user.id
    assert interview.interviewer_user_id == interviewer_user.id
    assert interview.stage == InterviewStage.TECHNICAL
    assert interview.status == InterviewStatus.SCHEDULED
    assert interview.scheduled_at == scheduled_at
    assert interview.duration_minutes == 90
    assert interview.meeting_url == "https://zoom.us/j/123456"


def test_schedule_interview_with_materials(
    scheduling_service,
    application,
    job,
    company,
    candidate_user,
    interviewer_user,
    db_session
):
    """Test scheduling interview with preparation materials."""
    scheduled_at = datetime.utcnow() + timedelta(days=2)

    prep_materials = {
        "documents": ["resume.pdf", "portfolio.pdf"],
        "links": ["https://github.com/candidate"]
    }

    questions = [
        "Tell me about your experience with Python",
        "Describe a challenging project"
    ]

    interview = scheduling_service.schedule_interview(
        application_id=application.id,
        job_id=job.id,
        company_id=company.id,
        candidate_user_id=candidate_user.id,
        interviewer_user_id=interviewer_user.id,
        stage=InterviewStage.BEHAVIORAL,
        scheduled_at=scheduled_at,
        preparation_materials=prep_materials,
        interview_questions=questions,
        db=db_session
    )

    assert interview.preparation_materials == prep_materials
    assert interview.interview_questions == questions


# ==================== Confirmation Tests ====================

def test_confirm_interview_by_candidate(
    scheduling_service,
    application,
    job,
    company,
    candidate_user,
    interviewer_user,
    db_session
):
    """Test candidate confirming interview."""
    interview = scheduling_service.schedule_interview(
        application_id=application.id,
        job_id=job.id,
        company_id=company.id,
        candidate_user_id=candidate_user.id,
        interviewer_user_id=interviewer_user.id,
        stage=InterviewStage.PHONE_SCREEN,
        scheduled_at=datetime.utcnow() + timedelta(days=1),
        db=db_session
    )

    success = scheduling_service.confirm_interview(
        interview_id=interview.id,
        user_id=candidate_user.id,
        db=db_session
    )

    assert success == True
    db_session.refresh(interview)
    assert interview.candidate_calendar_confirmed == True
    # Should still be SCHEDULED (need both to confirm)
    assert interview.status == InterviewStatus.SCHEDULED


def test_confirm_interview_by_both_parties(
    scheduling_service,
    application,
    job,
    company,
    candidate_user,
    interviewer_user,
    db_session
):
    """Test both parties confirming interview."""
    interview = scheduling_service.schedule_interview(
        application_id=application.id,
        job_id=job.id,
        company_id=company.id,
        candidate_user_id=candidate_user.id,
        interviewer_user_id=interviewer_user.id,
        stage=InterviewStage.TECHNICAL,
        scheduled_at=datetime.utcnow() + timedelta(days=1),
        db=db_session
    )

    # Candidate confirms
    scheduling_service.confirm_interview(
        interview_id=interview.id,
        user_id=candidate_user.id,
        db=db_session
    )

    # Interviewer confirms
    scheduling_service.confirm_interview(
        interview_id=interview.id,
        user_id=interviewer_user.id,
        db=db_session
    )

    db_session.refresh(interview)
    assert interview.candidate_calendar_confirmed == True
    assert interview.interviewer_calendar_confirmed == True
    assert interview.status == InterviewStatus.CONFIRMED


# ==================== Rescheduling Tests ====================

def test_reschedule_interview(
    scheduling_service,
    application,
    job,
    company,
    candidate_user,
    interviewer_user,
    db_session
):
    """Test rescheduling an interview."""
    original_time = datetime.utcnow() + timedelta(days=2)

    interview = scheduling_service.schedule_interview(
        application_id=application.id,
        job_id=job.id,
        company_id=company.id,
        candidate_user_id=candidate_user.id,
        interviewer_user_id=interviewer_user.id,
        stage=InterviewStage.PHONE_SCREEN,
        scheduled_at=original_time,
        db=db_session
    )

    # Reschedule to next day
    new_time = original_time + timedelta(days=1)
    new_interview = scheduling_service.reschedule_interview(
        interview_id=interview.id,
        new_scheduled_at=new_time,
        reschedule_reason="Conflict in schedule",
        db=db_session
    )

    assert new_interview is not None
    assert new_interview.id != interview.id
    assert new_interview.scheduled_at == new_time
    assert new_interview.rescheduled_from_interview_id == interview.id

    # Original should be marked as rescheduled
    db_session.refresh(interview)
    assert interview.status == InterviewStatus.RESCHEDULED


# ==================== Cancellation Tests ====================

def test_cancel_interview(
    scheduling_service,
    application,
    job,
    company,
    candidate_user,
    interviewer_user,
    db_session
):
    """Test cancelling an interview."""
    interview = scheduling_service.schedule_interview(
        application_id=application.id,
        job_id=job.id,
        company_id=company.id,
        candidate_user_id=candidate_user.id,
        interviewer_user_id=interviewer_user.id,
        stage=InterviewStage.TECHNICAL,
        scheduled_at=datetime.utcnow() + timedelta(days=1),
        db=db_session
    )

    success = scheduling_service.cancel_interview(
        interview_id=interview.id,
        cancelled_by_user_id=candidate_user.id,
        reason="Personal emergency",
        db=db_session
    )

    assert success == True
    db_session.refresh(interview)
    assert interview.status == InterviewStatus.CANCELLED
    assert interview.cancelled_by_user_id == candidate_user.id
    assert interview.cancellation_reason == "Personal emergency"
    assert interview.cancelled_at is not None


# ==================== Lifecycle Tests ====================

def test_start_interview(
    scheduling_service,
    application,
    job,
    company,
    candidate_user,
    interviewer_user,
    db_session
):
    """Test marking interview as started."""
    interview = scheduling_service.schedule_interview(
        application_id=application.id,
        job_id=job.id,
        company_id=company.id,
        candidate_user_id=candidate_user.id,
        interviewer_user_id=interviewer_user.id,
        stage=InterviewStage.PHONE_SCREEN,
        scheduled_at=datetime.utcnow(),
        db=db_session
    )

    success = scheduling_service.start_interview(
        interview_id=interview.id,
        db=db_session
    )

    assert success == True
    db_session.refresh(interview)
    assert interview.status == InterviewStatus.IN_PROGRESS
    assert interview.started_at is not None


def test_complete_interview(
    scheduling_service,
    application,
    job,
    company,
    candidate_user,
    interviewer_user,
    db_session
):
    """Test marking interview as completed."""
    interview = scheduling_service.schedule_interview(
        application_id=application.id,
        job_id=job.id,
        company_id=company.id,
        candidate_user_id=candidate_user.id,
        interviewer_user_id=interviewer_user.id,
        stage=InterviewStage.TECHNICAL,
        scheduled_at=datetime.utcnow(),
        db=db_session
    )

    # Start interview
    scheduling_service.start_interview(interview.id, db_session)

    # Complete interview
    success = scheduling_service.complete_interview(
        interview_id=interview.id,
        db=db_session
    )

    assert success == True
    db_session.refresh(interview)
    assert interview.status == InterviewStatus.COMPLETED
    assert interview.completed_at is not None
    assert interview.actual_duration_minutes is not None


def test_mark_no_show(
    scheduling_service,
    application,
    job,
    company,
    candidate_user,
    interviewer_user,
    db_session
):
    """Test marking interview as no-show."""
    interview = scheduling_service.schedule_interview(
        application_id=application.id,
        job_id=job.id,
        company_id=company.id,
        candidate_user_id=candidate_user.id,
        interviewer_user_id=interviewer_user.id,
        stage=InterviewStage.PHONE_SCREEN,
        scheduled_at=datetime.utcnow() - timedelta(hours=1),
        db=db_session
    )

    success = scheduling_service.mark_no_show(
        interview_id=interview.id,
        db=db_session
    )

    assert success == True
    db_session.refresh(interview)
    assert interview.status == InterviewStatus.NO_SHOW


# ==================== Query Tests ====================

def test_get_interview(
    scheduling_service,
    application,
    job,
    company,
    candidate_user,
    interviewer_user,
    db_session
):
    """Test getting interview by ID."""
    interview = scheduling_service.schedule_interview(
        application_id=application.id,
        job_id=job.id,
        company_id=company.id,
        candidate_user_id=candidate_user.id,
        interviewer_user_id=interviewer_user.id,
        stage=InterviewStage.PHONE_SCREEN,
        scheduled_at=datetime.utcnow() + timedelta(days=1),
        db=db_session
    )

    retrieved = scheduling_service.get_interview(
        interview_id=interview.id,
        db=db_session
    )

    assert retrieved is not None
    assert retrieved.id == interview.id


def test_get_interviews_for_candidate(
    scheduling_service,
    application,
    job,
    company,
    candidate_user,
    interviewer_user,
    db_session
):
    """Test getting all interviews for a candidate."""
    # Schedule multiple interviews
    for i in range(3):
        scheduling_service.schedule_interview(
            application_id=application.id,
            job_id=job.id,
            company_id=company.id,
            candidate_user_id=candidate_user.id,
            interviewer_user_id=interviewer_user.id,
            stage=InterviewStage.TECHNICAL,
            scheduled_at=datetime.utcnow() + timedelta(days=i+1),
            db=db_session
        )

    interviews = scheduling_service.get_interviews_for_candidate(
        candidate_user_id=candidate_user.id,
        db=db_session
    )

    assert len(interviews) == 3


def test_get_upcoming_interviews_for_candidate(
    scheduling_service,
    application,
    job,
    company,
    candidate_user,
    interviewer_user,
    db_session
):
    """Test getting only upcoming interviews."""
    # Schedule upcoming interview
    scheduling_service.schedule_interview(
        application_id=application.id,
        job_id=job.id,
        company_id=company.id,
        candidate_user_id=candidate_user.id,
        interviewer_user_id=interviewer_user.id,
        stage=InterviewStage.PHONE_SCREEN,
        scheduled_at=datetime.utcnow() + timedelta(days=1),
        db=db_session
    )

    # Schedule past interview (completed)
    past_interview = scheduling_service.schedule_interview(
        application_id=application.id,
        job_id=job.id,
        company_id=company.id,
        candidate_user_id=candidate_user.id,
        interviewer_user_id=interviewer_user.id,
        stage=InterviewStage.TECHNICAL,
        scheduled_at=datetime.utcnow() - timedelta(days=1),
        db=db_session
    )
    scheduling_service.complete_interview(past_interview.id, db_session)

    interviews = scheduling_service.get_interviews_for_candidate(
        candidate_user_id=candidate_user.id,
        db=db_session,
        upcoming_only=True
    )

    assert len(interviews) == 1


def test_get_interviews_for_interviewer(
    scheduling_service,
    application,
    job,
    company,
    candidate_user,
    interviewer_user,
    db_session
):
    """Test getting all interviews for an interviewer."""
    # Schedule interviews
    for i in range(2):
        scheduling_service.schedule_interview(
            application_id=application.id,
            job_id=job.id,
            company_id=company.id,
            candidate_user_id=candidate_user.id,
            interviewer_user_id=interviewer_user.id,
            stage=InterviewStage.PHONE_SCREEN,
            scheduled_at=datetime.utcnow() + timedelta(days=i+1),
            db=db_session
        )

    interviews = scheduling_service.get_interviews_for_interviewer(
        interviewer_user_id=interviewer_user.id,
        db=db_session
    )

    assert len(interviews) == 2


def test_get_interviews_for_application(
    scheduling_service,
    application,
    job,
    company,
    candidate_user,
    interviewer_user,
    db_session
):
    """Test getting all interviews for an application."""
    # Schedule multiple stages
    stages = [InterviewStage.PHONE_SCREEN, InterviewStage.TECHNICAL, InterviewStage.BEHAVIORAL]

    for stage in stages:
        scheduling_service.schedule_interview(
            application_id=application.id,
            job_id=job.id,
            company_id=company.id,
            candidate_user_id=candidate_user.id,
            interviewer_user_id=interviewer_user.id,
            stage=stage,
            scheduled_at=datetime.utcnow() + timedelta(days=1),
            db=db_session
        )

    interviews = scheduling_service.get_interviews_for_application(
        application_id=application.id,
        db=db_session
    )

    assert len(interviews) == 3
    interview_stages = [i.stage for i in interviews]
    assert InterviewStage.PHONE_SCREEN in interview_stages
    assert InterviewStage.TECHNICAL in interview_stages
    assert InterviewStage.BEHAVIORAL in interview_stages


# ==================== Reminder Tests ====================

def test_send_reminders_no_interviews(scheduling_service, db_session):
    """Test sending reminders with no interviews."""
    results = scheduling_service.send_interview_reminders(db=db_session)

    assert results["24h_reminders"] == 0
    assert results["1h_reminders"] == 0


def test_needs_24h_reminder(
    scheduling_service,
    application,
    job,
    company,
    candidate_user,
    interviewer_user,
    db_session
):
    """Test 24-hour reminder detection."""
    # Schedule interview 23.5 hours from now
    scheduled_at = datetime.utcnow() + timedelta(hours=23, minutes=30)

    interview = scheduling_service.schedule_interview(
        application_id=application.id,
        job_id=job.id,
        company_id=company.id,
        candidate_user_id=candidate_user.id,
        interviewer_user_id=interviewer_user.id,
        stage=InterviewStage.PHONE_SCREEN,
        scheduled_at=scheduled_at,
        db=db_session
    )

    assert interview.needs_24h_reminder() == True


def test_needs_1h_reminder(
    scheduling_service,
    application,
    job,
    company,
    candidate_user,
    interviewer_user,
    db_session
):
    """Test 1-hour reminder detection."""
    # Schedule interview 45 minutes from now
    scheduled_at = datetime.utcnow() + timedelta(minutes=45)

    interview = scheduling_service.schedule_interview(
        application_id=application.id,
        job_id=job.id,
        company_id=company.id,
        candidate_user_id=candidate_user.id,
        interviewer_user_id=interviewer_user.id,
        stage=InterviewStage.TECHNICAL,
        scheduled_at=scheduled_at,
        db=db_session
    )

    assert interview.needs_1h_reminder() == True


# ==================== Factory Tests ====================

def test_create_interview_scheduling_service():
    """Test factory function."""
    service = create_interview_scheduling_service(
        enable_notifications=False
    )

    assert service is not None
    assert isinstance(service, InterviewSchedulingService)
    assert service.enable_notifications == False
