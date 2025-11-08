"""
Comprehensive tests for Onboarding Service - Phase 9.

Tests employee onboarding, training, equipment, documents, time off, and performance reviews.
Tests EVERY action as explicitly requested by the user.
"""

import pytest
from datetime import date, datetime, timedelta
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session

from networking_ai.models.base import Base
from networking_ai.models.user import User, UserRole
from networking_ai.models.company import Company, CompanyStatus
from networking_ai.models.job import Job, JobStatus
from networking_ai.models.application import Application, ApplicationStatus
from networking_ai.models.onboarding import (
    Employee, OnboardingChecklist, OnboardingTask, TrainingProgram,
    EmployeeTraining, Equipment, EmployeeDocument, TimeOffRequest,
    EmployeeReview,
    EmploymentType, EmploymentStatus, OnboardingStatus, TaskStatus,
    TaskCategory, TrainingStatus, TrainingType, EquipmentType,
    EquipmentStatus, DocumentType, DocumentStatus, TimeOffType,
    TimeOffStatus, ReviewType, ReviewStatus
)
from networking_ai.services.onboarding_service import OnboardingService


# ==================== Fixtures ====================

@pytest.fixture(scope="function")
def db_session():
    """Create in-memory SQLite database for testing."""
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    SessionLocal = sessionmaker(bind=engine)
    session = SessionLocal()

    yield session

    session.close()


@pytest.fixture
def onboarding_service():
    """Create onboarding service instance."""
    return OnboardingService()


@pytest.fixture
def test_user(db_session):
    """Create test user."""
    user = User(
        email="candidate@example.com",
        password_hash="hashed_password",
        role=UserRole.TALENT,
        is_active=True
    )
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)
    return user


@pytest.fixture
def test_manager(db_session):
    """Create test manager user."""
    manager = User(
        email="manager@example.com",
        password_hash="hashed_password",
        role=UserRole.EMPLOYER,
        is_active=True
    )
    db_session.add(manager)
    db_session.commit()
    db_session.refresh(manager)
    return manager


@pytest.fixture
def test_company(db_session):
    """Create test company."""
    company = Company(
        name="TechCorp Inc",
        status=CompanyStatus.ACTIVE,
        description="A tech company"
    )
    db_session.add(company)
    db_session.commit()
    db_session.refresh(company)
    return company


@pytest.fixture
def test_job(db_session, test_company):
    """Create test job."""
    job = Job(
        company_id=test_company.id,
        title="Senior Software Engineer",
        description="Senior engineering role",
        status=JobStatus.OPEN,
        required_skills=["Python", "React", "AWS"]
    )
    db_session.add(job)
    db_session.commit()
    db_session.refresh(job)
    return job


@pytest.fixture
def test_application(db_session, test_user, test_job):
    """Create test application."""
    application = Application(
        talent_user_id=test_user.id,
        job_id=test_job.id,
        status=ApplicationStatus.ACCEPTED
    )
    db_session.add(application)
    db_session.commit()
    db_session.refresh(application)
    return application


@pytest.fixture
def test_employee(onboarding_service, db_session, test_user, test_company, test_job, test_application):
    """Create test employee."""
    today = date.today()
    employee = onboarding_service.create_employee(
        user_id=test_user.id,
        company_id=test_company.id,
        job_id=test_job.id,
        application_id=test_application.id,
        job_title="Senior Software Engineer",
        employment_type=EmploymentType.FULL_TIME,
        hire_date=today,
        start_date=today,
        base_salary=150000,
        department="Engineering",
        work_email="engineer@techcorp.com",
        db=db_session
    )
    return employee


@pytest.fixture
def test_training_program(db_session, test_company):
    """Create test training program."""
    program = TrainingProgram(
        company_id=test_company.id,
        title="Security Awareness Training",
        description="Annual security training",
        training_type=TrainingType.COMPLIANCE,
        required=True,
        duration_hours=2.0,
        passing_score=80.0,
        active=True
    )
    db_session.add(program)
    db_session.commit()
    db_session.refresh(program)
    return program


# ==================== Employee Management Tests ====================

def test_create_employee(onboarding_service, db_session, test_user, test_company, test_job, test_application):
    """Test creating an employee record."""
    today = date.today()

    employee = onboarding_service.create_employee(
        user_id=test_user.id,
        company_id=test_company.id,
        job_id=test_job.id,
        application_id=test_application.id,
        job_title="Senior Software Engineer",
        employment_type=EmploymentType.FULL_TIME,
        hire_date=today,
        start_date=today,
        base_salary=150000,
        department="Engineering",
        manager_user_id=None,
        work_email="engineer@techcorp.com",
        db=db_session
    )

    assert employee.id is not None
    assert employee.user_id == test_user.id
    assert employee.company_id == test_company.id
    assert employee.employment_type == EmploymentType.FULL_TIME
    assert employee.employment_status == EmploymentStatus.ACTIVE
    assert employee.job_title == "Senior Software Engineer"
    assert employee.base_salary == 150000
    assert employee.department == "Engineering"
    assert employee.work_email == "engineer@techcorp.com"
    assert employee.onboarding_status == OnboardingStatus.NOT_STARTED
    assert employee.onboarding_progress == 0.0
    assert employee.employee_id.startswith("EMP")
    assert employee.probation_end_date == today + timedelta(days=90)


def test_create_part_time_employee(onboarding_service, db_session, test_company, test_job):
    """Test creating a part-time employee."""
    # Create another user
    user = User(email="parttime@example.com", password_hash="hash", role=UserRole.TALENT, is_active=True)
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)

    # Create application
    app = Application(talent_user_id=user.id, job_id=test_job.id, status=ApplicationStatus.ACCEPTED)
    db_session.add(app)
    db_session.commit()
    db_session.refresh(app)

    today = date.today()
    employee = onboarding_service.create_employee(
        user_id=user.id,
        company_id=test_company.id,
        job_id=test_job.id,
        application_id=app.id,
        job_title="Part-time Developer",
        employment_type=EmploymentType.PART_TIME,
        hire_date=today,
        start_date=today,
        base_salary=75000,
        db=db_session
    )

    assert employee.employment_type == EmploymentType.PART_TIME
    assert employee.base_salary == 75000


def test_get_employee(onboarding_service, db_session, test_employee):
    """Test retrieving employee by ID."""
    employee = onboarding_service.get_employee(test_employee.id, db_session)

    assert employee is not None
    assert employee.id == test_employee.id
    assert employee.job_title == "Senior Software Engineer"


def test_get_employee_by_user(onboarding_service, db_session, test_employee, test_user):
    """Test retrieving employee by user ID."""
    employee = onboarding_service.get_employee_by_user(test_user.id, db_session)

    assert employee is not None
    assert employee.user_id == test_user.id
    assert employee.id == test_employee.id


def test_update_employee(onboarding_service, db_session, test_employee):
    """Test updating employee record."""
    updates = {
        "job_title": "Staff Software Engineer",
        "base_salary": 180000,
        "level": "Staff"
    }

    employee = onboarding_service.update_employee(
        employee_id=test_employee.id,
        updates=updates,
        db=db_session
    )

    assert employee.job_title == "Staff Software Engineer"
    assert employee.base_salary == 180000
    assert employee.level == "Staff"


def test_terminate_employee(onboarding_service, db_session, test_employee):
    """Test terminating an employee."""
    end_date = date.today() + timedelta(days=14)

    employee = onboarding_service.terminate_employee(
        employee_id=test_employee.id,
        end_date=end_date,
        reason="Voluntary resignation",
        db=db_session
    )

    assert employee.employment_status == EmploymentStatus.TERMINATED
    assert employee.end_date == end_date
    assert "Voluntary resignation" in employee.notes


# ==================== Onboarding Tests ====================

def test_start_onboarding(onboarding_service, db_session, test_employee):
    """Test starting onboarding process."""
    employee = onboarding_service.start_onboarding(
        employee_id=test_employee.id,
        db=db_session
    )

    assert employee.onboarding_status == OnboardingStatus.IN_PROGRESS


def test_start_onboarding_with_checklist(onboarding_service, db_session, test_employee, test_company):
    """Test starting onboarding with a checklist template."""
    # Create onboarding checklist
    checklist = OnboardingChecklist(
        company_id=test_company.id,
        name="Engineering Onboarding",
        department="Engineering",
        is_default=True,
        tasks=[
            {
                "title": "Complete I-9 form",
                "category": "paperwork",
                "due_days": 1,
                "priority": 10
            },
            {
                "title": "Setup laptop",
                "category": "it_setup",
                "due_days": 2,
                "priority": 9
            },
            {
                "title": "Complete security training",
                "category": "training",
                "due_days": 7,
                "priority": 8
            }
        ],
        active=True
    )
    db_session.add(checklist)
    db_session.commit()
    db_session.refresh(checklist)

    employee = onboarding_service.start_onboarding(
        employee_id=test_employee.id,
        checklist_id=checklist.id,
        db=db_session
    )

    assert employee.onboarding_status == OnboardingStatus.IN_PROGRESS

    # Check tasks were created
    tasks = onboarding_service.get_onboarding_tasks(test_employee.id, db=db_session)
    assert len(tasks) == 3
    assert tasks[0].title == "Complete I-9 form"
    assert tasks[0].category == TaskCategory.PAPERWORK
    assert tasks[0].priority == 10


def test_create_onboarding_task(onboarding_service, db_session, test_employee):
    """Test creating an individual onboarding task."""
    due_date = date.today() + timedelta(days=3)

    task = onboarding_service.create_onboarding_task(
        employee_id=test_employee.id,
        title="Set up email signature",
        category=TaskCategory.IT_SETUP,
        description="Configure corporate email signature",
        due_date=due_date,
        priority=5,
        db=db_session
    )

    assert task.id is not None
    assert task.employee_id == test_employee.id
    assert task.title == "Set up email signature"
    assert task.category == TaskCategory.IT_SETUP
    assert task.status == TaskStatus.PENDING
    assert task.due_date == due_date
    assert task.priority == 5


def test_complete_task(onboarding_service, db_session, test_employee, test_manager):
    """Test completing an onboarding task."""
    # Create task
    task = onboarding_service.create_onboarding_task(
        employee_id=test_employee.id,
        title="Sign NDA",
        category=TaskCategory.PAPERWORK,
        db=db_session
    )

    # Complete task
    completed_task = onboarding_service.complete_task(
        task_id=task.id,
        completed_by_user_id=test_manager.id,
        notes="Signed and filed",
        db=db_session
    )

    assert completed_task.status == TaskStatus.COMPLETED
    assert completed_task.completed_at is not None
    assert completed_task.completed_by_user_id == test_manager.id
    assert completed_task.notes == "Signed and filed"


def test_onboarding_progress_tracking(onboarding_service, db_session, test_employee, test_manager):
    """Test onboarding progress calculation."""
    # Create 4 tasks
    for i in range(4):
        onboarding_service.create_onboarding_task(
            employee_id=test_employee.id,
            title=f"Task {i+1}",
            category=TaskCategory.ORIENTATION,
            db=db_session
        )

    # Get employee - should have 0% progress
    employee = onboarding_service.get_employee(test_employee.id, db_session)
    assert employee.onboarding_progress == 0.0

    # Complete 2 tasks
    tasks = onboarding_service.get_onboarding_tasks(test_employee.id, db=db_session)
    onboarding_service.complete_task(tasks[0].id, test_manager.id, db=db_session)
    onboarding_service.complete_task(tasks[1].id, test_manager.id, db=db_session)

    # Should have 50% progress
    employee = onboarding_service.get_employee(test_employee.id, db_session)
    assert employee.onboarding_progress == 50.0
    assert employee.onboarding_status == OnboardingStatus.IN_PROGRESS

    # Complete remaining tasks
    onboarding_service.complete_task(tasks[2].id, test_manager.id, db=db_session)
    onboarding_service.complete_task(tasks[3].id, test_manager.id, db=db_session)

    # Should have 100% progress and be completed
    employee = onboarding_service.get_employee(test_employee.id, db_session)
    assert employee.onboarding_progress == 100.0
    assert employee.onboarding_status == OnboardingStatus.COMPLETED
    assert employee.onboarding_completed_at is not None


def test_get_onboarding_tasks_filtered_by_status(onboarding_service, db_session, test_employee, test_manager):
    """Test filtering onboarding tasks by status."""
    # Create tasks
    for i in range(5):
        onboarding_service.create_onboarding_task(
            employee_id=test_employee.id,
            title=f"Task {i+1}",
            category=TaskCategory.ORIENTATION,
            db=db_session
        )

    # Complete 2 tasks
    tasks = onboarding_service.get_onboarding_tasks(test_employee.id, db=db_session)
    onboarding_service.complete_task(tasks[0].id, test_manager.id, db=db_session)
    onboarding_service.complete_task(tasks[1].id, test_manager.id, db=db_session)

    # Get pending tasks
    pending_tasks = onboarding_service.get_onboarding_tasks(
        test_employee.id,
        status=TaskStatus.PENDING,
        db=db_session
    )
    assert len(pending_tasks) == 3

    # Get completed tasks
    completed_tasks = onboarding_service.get_onboarding_tasks(
        test_employee.id,
        status=TaskStatus.COMPLETED,
        db=db_session
    )
    assert len(completed_tasks) == 2


# ==================== Training Tests ====================

def test_enroll_in_training(onboarding_service, db_session, test_employee, test_training_program):
    """Test enrolling employee in training program."""
    due_date = date.today() + timedelta(days=30)

    training = onboarding_service.enroll_in_training(
        employee_id=test_employee.id,
        program_id=test_training_program.id,
        due_date=due_date,
        db=db_session
    )

    assert training.id is not None
    assert training.employee_id == test_employee.id
    assert training.program_id == test_training_program.id
    assert training.status == TrainingStatus.NOT_STARTED
    assert training.progress == 0.0
    assert training.due_date == due_date


def test_enroll_duplicate_prevents_duplicate_enrollment(onboarding_service, db_session, test_employee, test_training_program):
    """Test that enrolling twice returns existing enrollment."""
    training1 = onboarding_service.enroll_in_training(
        employee_id=test_employee.id,
        program_id=test_training_program.id,
        db=db_session
    )

    training2 = onboarding_service.enroll_in_training(
        employee_id=test_employee.id,
        program_id=test_training_program.id,
        db=db_session
    )

    assert training1.id == training2.id


def test_start_training(onboarding_service, db_session, test_employee, test_training_program):
    """Test starting a training program."""
    training = onboarding_service.enroll_in_training(
        employee_id=test_employee.id,
        program_id=test_training_program.id,
        db=db_session
    )

    started_training = onboarding_service.start_training(training.id, db_session)

    assert started_training.status == TrainingStatus.IN_PROGRESS
    assert started_training.started_at is not None


def test_complete_training_with_passing_score(onboarding_service, db_session, test_employee, test_training_program):
    """Test completing training with passing score."""
    training = onboarding_service.enroll_in_training(
        employee_id=test_employee.id,
        program_id=test_training_program.id,
        db=db_session
    )

    onboarding_service.start_training(training.id, db_session)

    completed_training = onboarding_service.complete_training(
        training_id=training.id,
        score=95.0,
        certificate_url="https://example.com/cert/123",
        db=db_session
    )

    assert completed_training.status == TrainingStatus.COMPLETED
    assert completed_training.score == 95.0
    assert completed_training.passed == True
    assert completed_training.progress == 100.0
    assert completed_training.completed_at is not None
    assert completed_training.certificate_url == "https://example.com/cert/123"
    assert completed_training.certificate_issued_at is not None
    assert completed_training.attempts == 1


def test_complete_training_with_failing_score(onboarding_service, db_session, test_employee, test_training_program):
    """Test completing training with failing score."""
    training = onboarding_service.enroll_in_training(
        employee_id=test_employee.id,
        program_id=test_training_program.id,
        db=db_session
    )

    onboarding_service.start_training(training.id, db_session)

    completed_training = onboarding_service.complete_training(
        training_id=training.id,
        score=65.0,  # Below passing score of 80
        db=db_session
    )

    assert completed_training.status == TrainingStatus.FAILED
    assert completed_training.score == 65.0
    assert completed_training.passed == False


def test_get_employee_trainings(onboarding_service, db_session, test_employee, test_company):
    """Test getting all training enrollments for employee."""
    # Create multiple training programs
    programs = []
    for i in range(3):
        program = TrainingProgram(
            company_id=test_company.id,
            title=f"Training {i+1}",
            training_type=TrainingType.TECHNICAL,
            required=True,
            active=True
        )
        db_session.add(program)
        programs.append(program)
    db_session.commit()

    # Enroll in all programs
    for program in programs:
        onboarding_service.enroll_in_training(
            employee_id=test_employee.id,
            program_id=program.id,
            db=db_session
        )

    # Get all trainings
    trainings = onboarding_service.get_employee_trainings(test_employee.id, db=db_session)
    assert len(trainings) == 3


def test_get_employee_trainings_filtered_by_status(onboarding_service, db_session, test_employee, test_company):
    """Test filtering employee trainings by status."""
    # Create and enroll in programs
    programs = []
    for i in range(3):
        program = TrainingProgram(
            company_id=test_company.id,
            title=f"Training {i+1}",
            training_type=TrainingType.TECHNICAL,
            required=True,
            active=True
        )
        db_session.add(program)
        programs.append(program)
    db_session.commit()

    # Enroll in all
    trainings = []
    for program in programs:
        training = onboarding_service.enroll_in_training(
            employee_id=test_employee.id,
            program_id=program.id,
            db=db_session
        )
        trainings.append(training)

    # Complete one
    onboarding_service.start_training(trainings[0].id, db_session)
    onboarding_service.complete_training(trainings[0].id, score=90.0, db=db_session)

    # Get completed trainings
    completed = onboarding_service.get_employee_trainings(
        test_employee.id,
        status=TrainingStatus.COMPLETED,
        db=db_session
    )
    assert len(completed) == 1

    # Get not started trainings
    not_started = onboarding_service.get_employee_trainings(
        test_employee.id,
        status=TrainingStatus.NOT_STARTED,
        db=db_session
    )
    assert len(not_started) == 2


# ==================== Equipment Tests ====================

def test_assign_equipment(onboarding_service, db_session, test_employee, test_company):
    """Test assigning equipment to employee."""
    equipment = onboarding_service.assign_equipment(
        employee_id=test_employee.id,
        equipment_type=EquipmentType.LAPTOP,
        name="MacBook Pro 16-inch",
        company_id=test_company.id,
        serial_number="MB123456",
        asset_tag="ASSET-001",
        db=db_session
    )

    assert equipment.id is not None
    assert equipment.employee_id == test_employee.id
    assert equipment.equipment_type == EquipmentType.LAPTOP
    assert equipment.name == "MacBook Pro 16-inch"
    assert equipment.serial_number == "MB123456"
    assert equipment.asset_tag == "ASSET-001"
    assert equipment.status == EquipmentStatus.ASSIGNED
    assert equipment.assigned_at is not None


def test_assign_multiple_equipment(onboarding_service, db_session, test_employee, test_company):
    """Test assigning multiple pieces of equipment."""
    equipment_items = [
        (EquipmentType.LAPTOP, "MacBook Pro"),
        (EquipmentType.MONITOR, "Dell 27-inch"),
        (EquipmentType.PHONE, "iPhone 13"),
        (EquipmentType.KEYBOARD, "Apple Magic Keyboard")
    ]

    for equipment_type, name in equipment_items:
        onboarding_service.assign_equipment(
            employee_id=test_employee.id,
            equipment_type=equipment_type,
            name=name,
            company_id=test_company.id,
            db=db_session
        )

    equipment = onboarding_service.get_employee_equipment(test_employee.id, db=db_session)
    assert len(equipment) == 4


def test_return_equipment(onboarding_service, db_session, test_employee, test_company):
    """Test returning equipment."""
    equipment = onboarding_service.assign_equipment(
        employee_id=test_employee.id,
        equipment_type=EquipmentType.LAPTOP,
        name="MacBook Pro",
        company_id=test_company.id,
        db=db_session
    )

    returned_equipment = onboarding_service.return_equipment(
        equipment_id=equipment.id,
        condition="Good",
        notes="All accessories included",
        db=db_session
    )

    assert returned_equipment.status == EquipmentStatus.RETURNED
    assert returned_equipment.returned_at is not None
    assert returned_equipment.condition == "Good"
    assert returned_equipment.notes == "All accessories included"


def test_get_employee_equipment_active_only(onboarding_service, db_session, test_employee, test_company):
    """Test getting only active equipment."""
    # Assign two laptops
    eq1 = onboarding_service.assign_equipment(
        employee_id=test_employee.id,
        equipment_type=EquipmentType.LAPTOP,
        name="Laptop 1",
        company_id=test_company.id,
        db=db_session
    )

    eq2 = onboarding_service.assign_equipment(
        employee_id=test_employee.id,
        equipment_type=EquipmentType.MONITOR,
        name="Monitor 1",
        company_id=test_company.id,
        db=db_session
    )

    # Return one
    onboarding_service.return_equipment(eq1.id, db=db_session)

    # Get active equipment
    active_equipment = onboarding_service.get_employee_equipment(
        test_employee.id,
        active_only=True,
        db=db_session
    )
    assert len(active_equipment) == 1
    assert active_equipment[0].id == eq2.id

    # Get all equipment
    all_equipment = onboarding_service.get_employee_equipment(
        test_employee.id,
        active_only=False,
        db=db_session
    )
    assert len(all_equipment) == 2


# ==================== Document Tests ====================

def test_create_document(onboarding_service, db_session, test_employee):
    """Test creating employee document."""
    due_date = date.today() + timedelta(days=7)

    document = onboarding_service.create_document(
        employee_id=test_employee.id,
        document_type=DocumentType.CONTRACT,
        title="Employment Contract",
        file_url="https://example.com/docs/contract.pdf",
        requires_signature=True,
        due_date=due_date,
        db=db_session
    )

    assert document.id is not None
    assert document.employee_id == test_employee.id
    assert document.document_type == DocumentType.CONTRACT
    assert document.title == "Employment Contract"
    assert document.file_url == "https://example.com/docs/contract.pdf"
    assert document.requires_signature == True
    assert document.due_date == due_date
    assert document.status == DocumentStatus.PENDING


def test_sign_document(onboarding_service, db_session, test_employee):
    """Test signing a document."""
    document = onboarding_service.create_document(
        employee_id=test_employee.id,
        document_type=DocumentType.NDA,
        title="Non-Disclosure Agreement",
        requires_signature=True,
        db=db_session
    )

    signed_document = onboarding_service.sign_document(
        document_id=document.id,
        signature_url="https://example.com/signatures/123",
        db=db_session
    )

    assert signed_document.status == DocumentStatus.SIGNED
    assert signed_document.signed_at is not None
    assert signed_document.signature_url == "https://example.com/signatures/123"


def test_get_employee_documents(onboarding_service, db_session, test_employee):
    """Test getting all documents for employee."""
    # Create multiple documents
    doc_types = [DocumentType.CONTRACT, DocumentType.NDA, DocumentType.HANDBOOK]

    for doc_type in doc_types:
        onboarding_service.create_document(
            employee_id=test_employee.id,
            document_type=doc_type,
            title=f"{doc_type.value} document",
            db=db_session
        )

    documents = onboarding_service.get_employee_documents(test_employee.id, db=db_session)
    assert len(documents) == 3


def test_get_employee_documents_filtered_by_type(onboarding_service, db_session, test_employee):
    """Test filtering documents by type."""
    # Create multiple documents
    onboarding_service.create_document(
        employee_id=test_employee.id,
        document_type=DocumentType.CONTRACT,
        title="Contract",
        db=db_session
    )
    onboarding_service.create_document(
        employee_id=test_employee.id,
        document_type=DocumentType.NDA,
        title="NDA",
        db=db_session
    )

    # Get only contracts
    contracts = onboarding_service.get_employee_documents(
        test_employee.id,
        document_type=DocumentType.CONTRACT,
        db=db_session
    )
    assert len(contracts) == 1
    assert contracts[0].document_type == DocumentType.CONTRACT


# ==================== Time Off Tests ====================

def test_request_time_off(onboarding_service, db_session, test_employee):
    """Test creating time off request."""
    start_date = date.today() + timedelta(days=30)
    end_date = start_date + timedelta(days=4)  # 5 days

    request = onboarding_service.request_time_off(
        employee_id=test_employee.id,
        time_off_type=TimeOffType.VACATION,
        start_date=start_date,
        end_date=end_date,
        reason="Family vacation",
        db=db_session
    )

    assert request.id is not None
    assert request.employee_id == test_employee.id
    assert request.time_off_type == TimeOffType.VACATION
    assert request.start_date == start_date
    assert request.end_date == end_date
    assert request.total_days == 5
    assert request.reason == "Family vacation"
    assert request.status == TimeOffStatus.PENDING


def test_approve_time_off(onboarding_service, db_session, test_employee, test_manager):
    """Test approving time off request."""
    start_date = date.today() + timedelta(days=30)
    end_date = start_date + timedelta(days=2)

    request = onboarding_service.request_time_off(
        employee_id=test_employee.id,
        time_off_type=TimeOffType.VACATION,
        start_date=start_date,
        end_date=end_date,
        db=db_session
    )

    approved_request = onboarding_service.approve_time_off(
        request_id=request.id,
        approved_by_user_id=test_manager.id,
        db=db_session
    )

    assert approved_request.status == TimeOffStatus.APPROVED
    assert approved_request.approved_by_user_id == test_manager.id
    assert approved_request.approved_at is not None


def test_reject_time_off(onboarding_service, db_session, test_employee, test_manager):
    """Test rejecting time off request."""
    start_date = date.today() + timedelta(days=30)
    end_date = start_date + timedelta(days=2)

    request = onboarding_service.request_time_off(
        employee_id=test_employee.id,
        time_off_type=TimeOffType.VACATION,
        start_date=start_date,
        end_date=end_date,
        db=db_session
    )

    rejected_request = onboarding_service.reject_time_off(
        request_id=request.id,
        approved_by_user_id=test_manager.id,
        rejection_reason="Insufficient coverage during that period",
        db=db_session
    )

    assert rejected_request.status == TimeOffStatus.REJECTED
    assert rejected_request.approved_by_user_id == test_manager.id
    assert rejected_request.approved_at is not None
    assert rejected_request.rejection_reason == "Insufficient coverage during that period"


def test_request_sick_leave(onboarding_service, db_session, test_employee):
    """Test requesting sick leave."""
    today = date.today()

    request = onboarding_service.request_time_off(
        employee_id=test_employee.id,
        time_off_type=TimeOffType.SICK_LEAVE,
        start_date=today,
        end_date=today,
        reason="Flu symptoms",
        db=db_session
    )

    assert request.time_off_type == TimeOffType.SICK_LEAVE
    assert request.total_days == 1


# ==================== Performance Review Tests ====================

def test_create_review(onboarding_service, db_session, test_employee, test_manager):
    """Test creating performance review."""
    scheduled_date = date.today() + timedelta(days=7)
    period_start = date.today() - timedelta(days=90)
    period_end = date.today()

    review = onboarding_service.create_review(
        employee_id=test_employee.id,
        reviewer_user_id=test_manager.id,
        review_type=ReviewType.QUARTERLY,
        scheduled_date=scheduled_date,
        review_period_start=period_start,
        review_period_end=period_end,
        db=db_session
    )

    assert review.id is not None
    assert review.employee_id == test_employee.id
    assert review.reviewer_user_id == test_manager.id
    assert review.review_type == ReviewType.QUARTERLY
    assert review.scheduled_date == scheduled_date
    assert review.review_period_start == period_start
    assert review.review_period_end == period_end
    assert review.status == ReviewStatus.SCHEDULED


def test_complete_review(onboarding_service, db_session, test_employee, test_manager):
    """Test completing performance review."""
    review = onboarding_service.create_review(
        employee_id=test_employee.id,
        reviewer_user_id=test_manager.id,
        review_type=ReviewType.QUARTERLY,
        db=db_session
    )

    completed_review = onboarding_service.complete_review(
        review_id=review.id,
        overall_rating=4.5,
        manager_comments="Excellent performance this quarter",
        strengths=["Technical excellence", "Team collaboration", "Initiative"],
        areas_for_improvement=["Time management", "Documentation"],
        achievements=["Led major project", "Mentored junior developers"],
        goals=["Take on tech lead role", "Improve system design skills"],
        performance_rating=4.5,
        communication_rating=4.0,
        teamwork_rating=5.0,
        promotion_recommended=True,
        raise_recommended=True,
        raise_amount=10000.0,
        db=db_session
    )

    assert completed_review.status == ReviewStatus.COMPLETED
    assert completed_review.completed_at is not None
    assert completed_review.overall_rating == 4.5
    assert completed_review.manager_comments == "Excellent performance this quarter"
    assert len(completed_review.strengths) == 3
    assert len(completed_review.areas_for_improvement) == 2
    assert len(completed_review.achievements) == 2
    assert len(completed_review.goals) == 2
    assert completed_review.performance_rating == 4.5
    assert completed_review.communication_rating == 4.0
    assert completed_review.teamwork_rating == 5.0
    assert completed_review.promotion_recommended == True
    assert completed_review.raise_recommended == True
    assert completed_review.raise_amount == 10000.0


def test_get_employee_reviews(onboarding_service, db_session, test_employee, test_manager):
    """Test getting all reviews for employee."""
    # Create multiple reviews
    review_types = [ReviewType.PROBATION, ReviewType.QUARTERLY, ReviewType.ANNUAL]

    for review_type in review_types:
        onboarding_service.create_review(
            employee_id=test_employee.id,
            reviewer_user_id=test_manager.id,
            review_type=review_type,
            db=db_session
        )

    reviews = onboarding_service.get_employee_reviews(test_employee.id, db=db_session)
    assert len(reviews) == 3


def test_probation_review(onboarding_service, db_session, test_employee, test_manager):
    """Test probation review."""
    review = onboarding_service.create_review(
        employee_id=test_employee.id,
        reviewer_user_id=test_manager.id,
        review_type=ReviewType.PROBATION,
        db=db_session
    )

    completed_review = onboarding_service.complete_review(
        review_id=review.id,
        overall_rating=4.0,
        manager_comments="Successfully completed probation",
        strengths=["Quick learner", "Good attitude"],
        areas_for_improvement=["Domain knowledge"],
        db=db_session
    )

    assert completed_review.review_type == ReviewType.PROBATION
    assert completed_review.overall_rating == 4.0


# ==================== Integration Tests ====================

def test_full_employee_lifecycle(onboarding_service, db_session, test_user, test_company, test_job, test_application, test_manager):
    """Test complete employee lifecycle from hire to termination."""
    today = date.today()

    # 1. Create employee
    employee = onboarding_service.create_employee(
        user_id=test_user.id,
        company_id=test_company.id,
        job_id=test_job.id,
        application_id=test_application.id,
        job_title="Software Engineer",
        employment_type=EmploymentType.FULL_TIME,
        hire_date=today,
        start_date=today,
        base_salary=120000,
        db=db_session
    )

    assert employee.onboarding_status == OnboardingStatus.NOT_STARTED

    # 2. Start onboarding and create tasks
    onboarding_service.start_onboarding(employee.id, db=db_session)

    for i in range(3):
        onboarding_service.create_onboarding_task(
            employee_id=employee.id,
            title=f"Task {i+1}",
            category=TaskCategory.ORIENTATION,
            db=db_session
        )

    # 3. Complete all tasks
    tasks = onboarding_service.get_onboarding_tasks(employee.id, db=db_session)
    for task in tasks:
        onboarding_service.complete_task(task.id, test_manager.id, db=db_session)

    employee = onboarding_service.get_employee(employee.id, db_session)
    assert employee.onboarding_status == OnboardingStatus.COMPLETED

    # 4. Assign equipment
    onboarding_service.assign_equipment(
        employee_id=employee.id,
        equipment_type=EquipmentType.LAPTOP,
        name="MacBook Pro",
        company_id=test_company.id,
        db=db_session
    )

    # 5. Create document
    onboarding_service.create_document(
        employee_id=employee.id,
        document_type=DocumentType.CONTRACT,
        title="Employment Contract",
        requires_signature=True,
        db=db_session
    )

    # 6. Conduct review
    review = onboarding_service.create_review(
        employee_id=employee.id,
        reviewer_user_id=test_manager.id,
        review_type=ReviewType.PROBATION,
        db=db_session
    )

    onboarding_service.complete_review(
        review_id=review.id,
        overall_rating=4.0,
        manager_comments="Good work",
        strengths=["Reliable"],
        areas_for_improvement=["Speed"],
        db=db_session
    )

    # 7. Request and approve time off
    time_off = onboarding_service.request_time_off(
        employee_id=employee.id,
        time_off_type=TimeOffType.VACATION,
        start_date=today + timedelta(days=60),
        end_date=today + timedelta(days=62),
        db=db_session
    )

    onboarding_service.approve_time_off(time_off.id, test_manager.id, db=db_session)

    # 8. Terminate
    end_date = today + timedelta(days=365)
    terminated_employee = onboarding_service.terminate_employee(
        employee_id=employee.id,
        end_date=end_date,
        reason="Left for new opportunity",
        db=db_session
    )

    assert terminated_employee.employment_status == EmploymentStatus.TERMINATED
    assert terminated_employee.end_date == end_date
