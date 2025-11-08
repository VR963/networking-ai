"""
Onboarding Models - Phase 9.

Post-hire employee management including onboarding, training, equipment, and reviews.
"""

from datetime import datetime, date
from typing import Optional
import enum

from sqlalchemy import (
    Column, Integer, String, Text, Boolean, DateTime, Date, Float,
    ForeignKey, Enum as SQLEnum, JSON
)
from sqlalchemy.orm import relationship

from ..database import Base


# ==================== Enums ====================

class EmploymentType(str, enum.Enum):
    """Employment type."""
    FULL_TIME = "full_time"
    PART_TIME = "part_time"
    CONTRACT = "contract"
    INTERN = "intern"
    TEMPORARY = "temporary"


class EmploymentStatus(str, enum.Enum):
    """Employment status."""
    ACTIVE = "active"
    ON_LEAVE = "on_leave"
    TERMINATED = "terminated"
    RESIGNED = "resigned"
    RETIRED = "retired"


class OnboardingStatus(str, enum.Enum):
    """Onboarding progress status."""
    NOT_STARTED = "not_started"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    OVERDUE = "overdue"


class TaskStatus(str, enum.Enum):
    """Task completion status."""
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    SKIPPED = "skipped"
    BLOCKED = "blocked"


class TaskCategory(str, enum.Enum):
    """Onboarding task category."""
    PAPERWORK = "paperwork"
    IT_SETUP = "it_setup"
    TRAINING = "training"
    ORIENTATION = "orientation"
    TEAM_INTRO = "team_intro"
    EQUIPMENT = "equipment"
    POLICIES = "policies"
    BENEFITS = "benefits"
    CUSTOM = "custom"


class TrainingStatus(str, enum.Enum):
    """Training completion status."""
    NOT_STARTED = "not_started"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"
    EXPIRED = "expired"


class TrainingType(str, enum.Enum):
    """Training type."""
    ORIENTATION = "orientation"
    TECHNICAL = "technical"
    COMPLIANCE = "compliance"
    SAFETY = "safety"
    SOFT_SKILLS = "soft_skills"
    PRODUCT = "product"
    CUSTOM = "custom"


class EquipmentStatus(str, enum.Enum):
    """Equipment status."""
    ASSIGNED = "assigned"
    IN_USE = "in_use"
    RETURNED = "returned"
    DAMAGED = "damaged"
    LOST = "lost"


class EquipmentType(str, enum.Enum):
    """Equipment type."""
    LAPTOP = "laptop"
    MONITOR = "monitor"
    PHONE = "phone"
    KEYBOARD = "keyboard"
    MOUSE = "mouse"
    HEADSET = "headset"
    DESK = "desk"
    CHAIR = "chair"
    ACCESS_CARD = "access_card"
    OTHER = "other"


class DocumentType(str, enum.Enum):
    """Document type."""
    CONTRACT = "contract"
    NDA = "nda"
    OFFER_LETTER = "offer_letter"
    HANDBOOK = "handbook"
    POLICY = "policy"
    TAX_FORM = "tax_form"
    BENEFITS = "benefits"
    CERTIFICATION = "certification"
    OTHER = "other"


class DocumentStatus(str, enum.Enum):
    """Document status."""
    PENDING = "pending"
    SENT = "sent"
    SIGNED = "signed"
    EXPIRED = "expired"
    REJECTED = "rejected"


class TimeOffType(str, enum.Enum):
    """Time off type."""
    VACATION = "vacation"
    SICK_LEAVE = "sick_leave"
    PERSONAL = "personal"
    PARENTAL = "parental"
    BEREAVEMENT = "bereavement"
    UNPAID = "unpaid"
    OTHER = "other"


class TimeOffStatus(str, enum.Enum):
    """Time off request status."""
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"
    CANCELLED = "cancelled"


class ReviewType(str, enum.Enum):
    """Performance review type."""
    PROBATION = "probation"
    QUARTERLY = "quarterly"
    ANNUAL = "annual"
    PROMOTION = "promotion"
    PIP = "pip"  # Performance Improvement Plan
    EXIT = "exit"


class ReviewStatus(str, enum.Enum):
    """Review status."""
    SCHEDULED = "scheduled"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    CANCELLED = "cancelled"


# ==================== Models ====================

class Employee(Base):
    """
    Employee record for hired candidates.

    Extended profile with employment details, compensation, and department info.
    """
    __tablename__ = "employees"
    __table_args__ = {'extend_existing': True}

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey('users.id'), nullable=False, unique=True)
    company_id = Column(Integer, ForeignKey('companies.id'), nullable=False)
    job_id = Column(Integer, ForeignKey('jobs.id'), nullable=True)  # Original job hired for
    application_id = Column(Integer, ForeignKey('applications.id'), nullable=True)

    # Employment Details
    employee_id = Column(String(100), unique=True, nullable=False)  # Company employee ID
    employment_type = Column(SQLEnum(EmploymentType), nullable=False)
    employment_status = Column(SQLEnum(EmploymentStatus), default=EmploymentStatus.ACTIVE)

    # Dates
    hire_date = Column(Date, nullable=False)
    start_date = Column(Date, nullable=False)
    end_date = Column(Date, nullable=True)
    probation_end_date = Column(Date, nullable=True)

    # Position
    job_title = Column(String(200), nullable=False)
    department = Column(String(100), nullable=True)
    team = Column(String(100), nullable=True)
    level = Column(String(50), nullable=True)  # Junior, Mid, Senior, Staff, Principal, etc.

    # Reporting
    manager_user_id = Column(Integer, ForeignKey('users.id'), nullable=True)
    reports_to_employee_id = Column(Integer, ForeignKey('employees.id'), nullable=True)

    # Compensation
    base_salary = Column(Integer, nullable=True)
    currency = Column(String(3), default="USD")
    salary_frequency = Column(String(20), default="annual")  # annual, monthly, hourly
    bonus_eligible = Column(Boolean, default=False)
    equity_shares = Column(Integer, nullable=True)

    # Location
    work_location = Column(String(200), nullable=True)
    office_location = Column(String(200), nullable=True)
    remote = Column(Boolean, default=False)

    # Onboarding
    onboarding_status = Column(SQLEnum(OnboardingStatus), default=OnboardingStatus.NOT_STARTED)
    onboarding_progress = Column(Float, default=0.0)  # 0-100
    onboarding_completed_at = Column(DateTime, nullable=True)

    # Contact (work)
    work_email = Column(String(255), nullable=True)
    work_phone = Column(String(50), nullable=True)
    slack_id = Column(String(100), nullable=True)

    # Additional Info
    emergency_contact_name = Column(String(200), nullable=True)
    emergency_contact_phone = Column(String(50), nullable=True)
    emergency_contact_relationship = Column(String(100), nullable=True)

    notes = Column(Text, nullable=True)
    extra_data = Column(JSON, default=dict)

    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    # Relationships
    user = relationship("User", foreign_keys=[user_id], backref="employee_record")
    company = relationship("Company", backref="employees")
    job = relationship("Job", backref="hired_employees")
    application = relationship("Application", backref="hired_employee_record")
    manager = relationship("User", foreign_keys=[manager_user_id], backref="managed_employees")
    reports_to = relationship("Employee", remote_side=[id], backref="direct_reports")

    onboarding_tasks = relationship("OnboardingTask", back_populates="employee", cascade="all, delete-orphan")
    trainings = relationship("EmployeeTraining", back_populates="employee", cascade="all, delete-orphan")
    equipment = relationship("Equipment", back_populates="employee", cascade="all, delete-orphan")
    documents = relationship("EmployeeDocument", back_populates="employee", cascade="all, delete-orphan")
    time_off_requests = relationship("TimeOffRequest", back_populates="employee", cascade="all, delete-orphan")
    reviews = relationship("EmployeeReview", back_populates="employee", cascade="all, delete-orphan")


class OnboardingChecklist(Base):
    """
    Onboarding checklist template.

    Defines standard onboarding tasks for a role or department.
    """
    __tablename__ = "onboarding_checklists"
    __table_args__ = {'extend_existing': True}

    id = Column(Integer, primary_key=True, autoincrement=True)
    company_id = Column(Integer, ForeignKey('companies.id'), nullable=False)

    name = Column(String(200), nullable=False)
    description = Column(Text, nullable=True)

    # Applies to
    department = Column(String(100), nullable=True)
    job_title = Column(String(200), nullable=True)
    employment_type = Column(SQLEnum(EmploymentType), nullable=True)
    is_default = Column(Boolean, default=False)

    # Tasks (JSON array)
    tasks = Column(JSON, default=list)  # [{ title, description, category, due_days, assigned_to }]

    active = Column(Boolean, default=True)

    created_by = Column(Integer, ForeignKey('users.id'), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    # Relationships
    company = relationship("Company", backref="onboarding_checklists")
    creator = relationship("User", backref="created_checklists")


class OnboardingTask(Base):
    """
    Individual onboarding task for an employee.

    Tracks completion of paperwork, setup, training, and orientation activities.
    """
    __tablename__ = "onboarding_tasks"
    __table_args__ = {'extend_existing': True}

    id = Column(Integer, primary_key=True, autoincrement=True)
    employee_id = Column(Integer, ForeignKey('employees.id'), nullable=False)
    checklist_id = Column(Integer, ForeignKey('onboarding_checklists.id'), nullable=True)

    title = Column(String(200), nullable=False)
    description = Column(Text, nullable=True)
    category = Column(SQLEnum(TaskCategory), nullable=False)

    # Status
    status = Column(SQLEnum(TaskStatus), default=TaskStatus.PENDING)
    priority = Column(Integer, default=0)  # Higher = more important

    # Scheduling
    due_date = Column(Date, nullable=True)
    completed_at = Column(DateTime, nullable=True)

    # Assignment
    assigned_to_user_id = Column(Integer, ForeignKey('users.id'), nullable=True)  # Who should complete it
    completed_by_user_id = Column(Integer, ForeignKey('users.id'), nullable=True)

    # Dependencies
    depends_on_task_id = Column(Integer, ForeignKey('onboarding_tasks.id'), nullable=True)
    blocking = Column(Boolean, default=False)  # Blocks other tasks

    # Additional
    notes = Column(Text, nullable=True)
    attachments = Column(JSON, default=list)  # URLs or file paths

    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    # Relationships
    employee = relationship("Employee", back_populates="onboarding_tasks")
    checklist = relationship("OnboardingChecklist", backref="task_instances")
    assigned_to = relationship("User", foreign_keys=[assigned_to_user_id], backref="assigned_tasks")
    completed_by = relationship("User", foreign_keys=[completed_by_user_id], backref="completed_tasks")
    depends_on = relationship("OnboardingTask", remote_side=[id], backref="dependent_tasks")


class TrainingProgram(Base):
    """
    Training program or course.

    Defines training content, requirements, and scheduling.
    """
    __tablename__ = "training_programs"
    __table_args__ = {'extend_existing': True}

    id = Column(Integer, primary_key=True, autoincrement=True)
    company_id = Column(Integer, ForeignKey('companies.id'), nullable=False)

    title = Column(String(200), nullable=False)
    description = Column(Text, nullable=True)
    training_type = Column(SQLEnum(TrainingType), nullable=False)

    # Content
    content_url = Column(String(500), nullable=True)  # LMS link, video, etc.
    materials = Column(JSON, default=list)  # Additional resources

    # Requirements
    required = Column(Boolean, default=False)
    duration_hours = Column(Float, nullable=True)
    passing_score = Column(Float, nullable=True)  # If has assessment

    # Scheduling
    available_from = Column(Date, nullable=True)
    expires_after_days = Column(Integer, nullable=True)  # Training expires after X days

    # Target audience
    departments = Column(JSON, default=list)
    job_titles = Column(JSON, default=list)

    active = Column(Boolean, default=True)

    created_by = Column(Integer, ForeignKey('users.id'), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    # Relationships
    company = relationship("Company", backref="training_programs")
    creator = relationship("User", backref="created_training_programs")
    enrollments = relationship("EmployeeTraining", back_populates="program", cascade="all, delete-orphan")


class EmployeeTraining(Base):
    """
    Employee training enrollment and completion.

    Tracks individual progress through training programs.
    """
    __tablename__ = "employee_trainings"
    __table_args__ = {'extend_existing': True}

    id = Column(Integer, primary_key=True, autoincrement=True)
    employee_id = Column(Integer, ForeignKey('employees.id'), nullable=False)
    program_id = Column(Integer, ForeignKey('training_programs.id'), nullable=False)

    # Status
    status = Column(SQLEnum(TrainingStatus), default=TrainingStatus.NOT_STARTED)
    progress = Column(Float, default=0.0)  # 0-100

    # Dates
    enrolled_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    started_at = Column(DateTime, nullable=True)
    completed_at = Column(DateTime, nullable=True)
    due_date = Column(Date, nullable=True)
    expires_at = Column(DateTime, nullable=True)

    # Results
    score = Column(Float, nullable=True)  # If has assessment
    passed = Column(Boolean, nullable=True)
    attempts = Column(Integer, default=0)

    # Certification
    certificate_url = Column(String(500), nullable=True)
    certificate_issued_at = Column(DateTime, nullable=True)

    notes = Column(Text, nullable=True)

    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    # Relationships
    employee = relationship("Employee", back_populates="trainings")
    program = relationship("TrainingProgram", back_populates="enrollments")


class Equipment(Base):
    """
    Company equipment assigned to employees.

    Tracks laptops, phones, monitors, and other assets.
    """
    __tablename__ = "equipment"
    __table_args__ = {'extend_existing': True}

    id = Column(Integer, primary_key=True, autoincrement=True)
    company_id = Column(Integer, ForeignKey('companies.id'), nullable=False)
    employee_id = Column(Integer, ForeignKey('employees.id'), nullable=True)  # Null if unassigned

    # Equipment Info
    equipment_type = Column(SQLEnum(EquipmentType), nullable=False)
    name = Column(String(200), nullable=False)  # e.g., "MacBook Pro 16-inch"
    description = Column(Text, nullable=True)

    # Identification
    serial_number = Column(String(200), nullable=True)
    asset_tag = Column(String(100), nullable=True)

    # Status
    status = Column(SQLEnum(EquipmentStatus), default=EquipmentStatus.ASSIGNED)
    condition = Column(String(50), nullable=True)  # New, Good, Fair, Poor

    # Dates
    assigned_at = Column(DateTime, nullable=True)
    return_date = Column(Date, nullable=True)
    returned_at = Column(DateTime, nullable=True)

    # Value
    purchase_price = Column(Float, nullable=True)
    purchase_date = Column(Date, nullable=True)
    warranty_expires = Column(Date, nullable=True)

    # Location
    location = Column(String(200), nullable=True)

    notes = Column(Text, nullable=True)

    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    # Relationships
    company = relationship("Company", backref="equipment")
    employee = relationship("Employee", back_populates="equipment")


class EmployeeDocument(Base):
    """
    Employment documents.

    Contracts, NDAs, policies, tax forms, and other employee documents.
    """
    __tablename__ = "employee_documents"
    __table_args__ = {'extend_existing': True}

    id = Column(Integer, primary_key=True, autoincrement=True)
    employee_id = Column(Integer, ForeignKey('employees.id'), nullable=False)

    document_type = Column(SQLEnum(DocumentType), nullable=False)
    title = Column(String(200), nullable=False)
    description = Column(Text, nullable=True)

    # File
    file_url = Column(String(500), nullable=True)
    file_name = Column(String(255), nullable=True)
    file_size = Column(Integer, nullable=True)  # bytes

    # Status
    status = Column(SQLEnum(DocumentStatus), default=DocumentStatus.PENDING)

    # Signature
    requires_signature = Column(Boolean, default=False)
    signed_at = Column(DateTime, nullable=True)
    signature_url = Column(String(500), nullable=True)

    # Dates
    sent_at = Column(DateTime, nullable=True)
    due_date = Column(Date, nullable=True)
    expires_at = Column(Date, nullable=True)

    # Uploaded by
    uploaded_by_user_id = Column(Integer, ForeignKey('users.id'), nullable=True)

    notes = Column(Text, nullable=True)

    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    # Relationships
    employee = relationship("Employee", back_populates="documents")
    uploaded_by = relationship("User", backref="uploaded_documents")


class TimeOffRequest(Base):
    """
    Employee time off request.

    PTO, sick leave, vacation, and other leave requests.
    """
    __tablename__ = "time_off_requests"
    __table_args__ = {'extend_existing': True}

    id = Column(Integer, primary_key=True, autoincrement=True)
    employee_id = Column(Integer, ForeignKey('employees.id'), nullable=False)

    time_off_type = Column(SQLEnum(TimeOffType), nullable=False)
    status = Column(SQLEnum(TimeOffStatus), default=TimeOffStatus.PENDING)

    # Dates
    start_date = Column(Date, nullable=False)
    end_date = Column(Date, nullable=False)
    total_days = Column(Float, nullable=False)  # Can be partial days

    # Request details
    reason = Column(Text, nullable=True)
    notes = Column(Text, nullable=True)

    # Approval
    approved_by_user_id = Column(Integer, ForeignKey('users.id'), nullable=True)
    approved_at = Column(DateTime, nullable=True)
    rejection_reason = Column(Text, nullable=True)

    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    # Relationships
    employee = relationship("Employee", back_populates="time_off_requests")
    approved_by = relationship("User", backref="approved_time_off_requests")


class EmployeeReview(Base):
    """
    Performance review.

    Tracks employee performance reviews, feedback, and goals.
    """
    __tablename__ = "employee_reviews"
    __table_args__ = {'extend_existing': True}

    id = Column(Integer, primary_key=True, autoincrement=True)
    employee_id = Column(Integer, ForeignKey('employees.id'), nullable=False)
    reviewer_user_id = Column(Integer, ForeignKey('users.id'), nullable=False)

    review_type = Column(SQLEnum(ReviewType), nullable=False)
    status = Column(SQLEnum(ReviewStatus), default=ReviewStatus.SCHEDULED)

    # Period
    review_period_start = Column(Date, nullable=True)
    review_period_end = Column(Date, nullable=True)
    scheduled_date = Column(Date, nullable=True)
    completed_at = Column(DateTime, nullable=True)

    # Ratings (1-5 scale)
    overall_rating = Column(Float, nullable=True)
    performance_rating = Column(Float, nullable=True)
    communication_rating = Column(Float, nullable=True)
    teamwork_rating = Column(Float, nullable=True)
    leadership_rating = Column(Float, nullable=True)

    # Feedback
    strengths = Column(JSON, default=list)
    areas_for_improvement = Column(JSON, default=list)
    achievements = Column(JSON, default=list)
    goals = Column(JSON, default=list)

    # Comments
    manager_comments = Column(Text, nullable=True)
    employee_comments = Column(Text, nullable=True)

    # Outcomes
    promotion_recommended = Column(Boolean, default=False)
    raise_recommended = Column(Boolean, default=False)
    raise_amount = Column(Float, nullable=True)

    # Documents
    attachments = Column(JSON, default=list)

    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    # Relationships
    employee = relationship("Employee", back_populates="reviews")
    reviewer = relationship("User", backref="conducted_reviews")
