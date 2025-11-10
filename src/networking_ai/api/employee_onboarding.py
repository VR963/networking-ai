"""
Employee Onboarding API Endpoints - Phase 9.

REST API for post-hire employee management including onboarding, training,
equipment, documents, time off, and performance reviews.
"""

from typing import Optional, List
from datetime import date, datetime
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from pydantic import BaseModel

from ..database import get_db
from ..models.onboarding import (
    Employee, OnboardingTask, EmployeeTraining, Equipment,
    EmployeeDocument, TimeOffRequest, EmployeeReview,
    EmploymentType, EmploymentStatus, OnboardingStatus, TaskStatus,
    TaskCategory, TrainingStatus, EquipmentType, EquipmentStatus,
    DocumentType, DocumentStatus, TimeOffType, TimeOffStatus,
    ReviewType, ReviewStatus
)
from ..services.onboarding_service import (
    OnboardingService,
    create_onboarding_service
)


# ==================== Request/Response Models ====================

class CreateEmployeeRequest(BaseModel):
    """Create employee request."""
    user_id: int
    company_id: int
    job_id: int
    application_id: int
    job_title: str
    employment_type: EmploymentType
    hire_date: date
    start_date: date
    base_salary: Optional[int] = None
    department: Optional[str] = None
    manager_user_id: Optional[int] = None
    work_email: Optional[str] = None


class EmployeeResponse(BaseModel):
    """Employee response."""
    id: int
    user_id: int
    company_id: int
    employee_id: str
    employment_type: EmploymentType
    employment_status: EmploymentStatus
    job_title: str
    department: Optional[str] = None
    hire_date: date
    start_date: date
    onboarding_status: OnboardingStatus
    onboarding_progress: float
    work_email: Optional[str] = None

    class Config:
        from_attributes = True


class CreateTaskRequest(BaseModel):
    """Create onboarding task request."""
    employee_id: int
    title: str
    category: TaskCategory
    description: Optional[str] = None
    due_date: Optional[date] = None
    assigned_to_user_id: Optional[int] = None
    priority: int = 0


class TaskResponse(BaseModel):
    """Onboarding task response."""
    id: int
    employee_id: int
    title: str
    category: TaskCategory
    status: TaskStatus
    due_date: Optional[date] = None
    completed_at: Optional[datetime] = None
    priority: int

    class Config:
        from_attributes = True


class CompleteTaskRequest(BaseModel):
    """Complete task request."""
    completed_by_user_id: int
    notes: Optional[str] = None


class EnrollTrainingRequest(BaseModel):
    """Enroll in training request."""
    employee_id: int
    program_id: int
    due_date: Optional[date] = None


class CompleteTrainingRequest(BaseModel):
    """Complete training request."""
    score: Optional[float] = None
    certificate_url: Optional[str] = None


class TrainingResponse(BaseModel):
    """Training enrollment response."""
    id: int
    employee_id: int
    program_id: int
    status: TrainingStatus
    progress: float
    enrolled_at: datetime
    completed_at: Optional[datetime] = None
    score: Optional[float] = None
    passed: Optional[bool] = None

    class Config:
        from_attributes = True


class AssignEquipmentRequest(BaseModel):
    """Assign equipment request."""
    employee_id: int
    equipment_type: EquipmentType
    name: str
    company_id: int
    serial_number: Optional[str] = None
    asset_tag: Optional[str] = None


class EquipmentResponse(BaseModel):
    """Equipment response."""
    id: int
    employee_id: Optional[int] = None
    equipment_type: EquipmentType
    name: str
    serial_number: Optional[str] = None
    status: EquipmentStatus
    assigned_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class CreateDocumentRequest(BaseModel):
    """Create document request."""
    employee_id: int
    document_type: DocumentType
    title: str
    file_url: Optional[str] = None
    requires_signature: bool = False
    due_date: Optional[date] = None


class DocumentResponse(BaseModel):
    """Document response."""
    id: int
    employee_id: int
    document_type: DocumentType
    title: str
    status: DocumentStatus
    requires_signature: bool
    signed_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class TimeOffRequestCreate(BaseModel):
    """Time off request creation."""
    employee_id: int
    time_off_type: TimeOffType
    start_date: date
    end_date: date
    reason: Optional[str] = None


class TimeOffResponse(BaseModel):
    """Time off request response."""
    id: int
    employee_id: int
    time_off_type: TimeOffType
    start_date: date
    end_date: date
    total_days: float
    status: TimeOffStatus
    approved_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class CreateReviewRequest(BaseModel):
    """Create performance review request."""
    employee_id: int
    reviewer_user_id: int
    review_type: ReviewType
    scheduled_date: Optional[date] = None
    review_period_start: Optional[date] = None
    review_period_end: Optional[date] = None


class CompleteReviewRequest(BaseModel):
    """Complete review request."""
    overall_rating: float
    manager_comments: str
    strengths: List[str]
    areas_for_improvement: List[str]
    achievements: Optional[List[str]] = None
    goals: Optional[List[str]] = None
    performance_rating: Optional[float] = None
    communication_rating: Optional[float] = None
    teamwork_rating: Optional[float] = None
    promotion_recommended: bool = False
    raise_recommended: bool = False
    raise_amount: Optional[float] = None


class ReviewResponse(BaseModel):
    """Performance review response."""
    id: int
    employee_id: int
    reviewer_user_id: int
    review_type: ReviewType
    status: ReviewStatus
    overall_rating: Optional[float] = None
    scheduled_date: Optional[date] = None
    completed_at: Optional[datetime] = None

    class Config:
        from_attributes = True


# ==================== Router Setup ====================

router = APIRouter(prefix="/api/employee-onboarding", tags=["employee-onboarding"])


# ==================== Helper Functions ====================

def get_onboarding_service() -> OnboardingService:
    """Get onboarding service instance."""
    return create_onboarding_service()


# ==================== Employee Management ====================

@router.post("/employees", response_model=EmployeeResponse, status_code=status.HTTP_201_CREATED)
def create_employee(
    request: CreateEmployeeRequest,
    current_user_id: int,  # From auth
    db: Session = Depends(get_db),
    service: OnboardingService = Depends(get_onboarding_service)
):
    """
    Create employee record for a hired candidate.

    Converts a hired applicant into an active employee with onboarding tracking.
    """
    try:
        employee = service.create_employee(
            user_id=request.user_id,
            company_id=request.company_id,
            job_id=request.job_id,
            application_id=request.application_id,
            job_title=request.job_title,
            employment_type=request.employment_type,
            hire_date=request.hire_date,
            start_date=request.start_date,
            base_salary=request.base_salary,
            department=request.department,
            manager_user_id=request.manager_user_id,
            work_email=request.work_email,
            db=db
        )
        return employee
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create employee: {str(e)}"
        )


@router.get("/employees/{employee_id}", response_model=EmployeeResponse)
def get_employee(
    employee_id: int,
    current_user_id: int,  # From auth
    db: Session = Depends(get_db),
    service: OnboardingService = Depends(get_onboarding_service)
):
    """Get employee by ID."""
    employee = service.get_employee(employee_id, db)
    if not employee:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Employee not found"
        )
    return employee


@router.get("/employees/user/{user_id}", response_model=EmployeeResponse)
def get_employee_by_user(
    user_id: int,
    current_user_id: int,  # From auth
    db: Session = Depends(get_db),
    service: OnboardingService = Depends(get_onboarding_service)
):
    """Get employee record by user ID."""
    employee = service.get_employee_by_user(user_id, db)
    if not employee:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Employee not found"
        )
    return employee


@router.post("/employees/{employee_id}/start-onboarding")
def start_onboarding(
    employee_id: int,
    checklist_id: Optional[int] = None,
    current_user_id: int = 0,  # From auth
    db: Session = Depends(get_db),
    service: OnboardingService = Depends(get_onboarding_service)
):
    """
    Start onboarding process for an employee.

    Creates onboarding tasks from checklist template.
    """
    try:
        employee = service.start_onboarding(employee_id, checklist_id, db)
        return {
            "message": "Onboarding started",
            "employee_id": employee.id,
            "status": employee.onboarding_status,
            "progress": employee.onboarding_progress
        }
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e)
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to start onboarding: {str(e)}"
        )


@router.post("/employees/{employee_id}/terminate")
def terminate_employee(
    employee_id: int,
    end_date: date,
    reason: Optional[str] = None,
    current_user_id: int = 0,  # From auth
    db: Session = Depends(get_db),
    service: OnboardingService = Depends(get_onboarding_service)
):
    """Terminate employee."""
    try:
        employee = service.terminate_employee(employee_id, end_date, reason, db)
        return {
            "message": "Employee terminated",
            "employee_id": employee.id,
            "status": employee.employment_status,
            "end_date": employee.end_date
        }
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e)
        )


# ==================== Onboarding Tasks ====================

@router.post("/tasks", response_model=TaskResponse, status_code=status.HTTP_201_CREATED)
def create_task(
    request: CreateTaskRequest,
    current_user_id: int,  # From auth
    db: Session = Depends(get_db),
    service: OnboardingService = Depends(get_onboarding_service)
):
    """Create an onboarding task."""
    try:
        task = service.create_onboarding_task(
            employee_id=request.employee_id,
            title=request.title,
            category=request.category,
            description=request.description,
            due_date=request.due_date,
            assigned_to_user_id=request.assigned_to_user_id,
            priority=request.priority,
            db=db
        )
        return task
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create task: {str(e)}"
        )


@router.get("/tasks/employee/{employee_id}", response_model=List[TaskResponse])
def get_employee_tasks(
    employee_id: int,
    status_filter: Optional[TaskStatus] = None,
    current_user_id: int = 0,  # From auth
    db: Session = Depends(get_db),
    service: OnboardingService = Depends(get_onboarding_service)
):
    """Get onboarding tasks for an employee."""
    tasks = service.get_onboarding_tasks(employee_id, status_filter, db)
    return tasks


@router.post("/tasks/{task_id}/complete", response_model=TaskResponse)
def complete_task(
    task_id: int,
    request: CompleteTaskRequest,
    db: Session = Depends(get_db),
    service: OnboardingService = Depends(get_onboarding_service)
):
    """Mark an onboarding task as completed."""
    try:
        task = service.complete_task(
            task_id=task_id,
            completed_by_user_id=request.completed_by_user_id,
            notes=request.notes,
            db=db
        )
        return task
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e)
        )


# ==================== Training ====================

@router.post("/training/enroll", response_model=TrainingResponse, status_code=status.HTTP_201_CREATED)
def enroll_training(
    request: EnrollTrainingRequest,
    current_user_id: int,  # From auth
    db: Session = Depends(get_db),
    service: OnboardingService = Depends(get_onboarding_service)
):
    """Enroll employee in training program."""
    try:
        training = service.enroll_in_training(
            employee_id=request.employee_id,
            program_id=request.program_id,
            due_date=request.due_date,
            db=db
        )
        return training
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e)
        )


@router.post("/training/{training_id}/start", response_model=TrainingResponse)
def start_training(
    training_id: int,
    current_user_id: int,  # From auth
    db: Session = Depends(get_db),
    service: OnboardingService = Depends(get_onboarding_service)
):
    """Mark training as started."""
    try:
        training = service.start_training(training_id, db)
        return training
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e)
        )


@router.post("/training/{training_id}/complete", response_model=TrainingResponse)
def complete_training(
    training_id: int,
    request: CompleteTrainingRequest,
    current_user_id: int,  # From auth
    db: Session = Depends(get_db),
    service: OnboardingService = Depends(get_onboarding_service)
):
    """Mark training as completed."""
    try:
        training = service.complete_training(
            training_id=training_id,
            score=request.score,
            certificate_url=request.certificate_url,
            db=db
        )
        return training
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e)
        )


@router.get("/training/employee/{employee_id}", response_model=List[TrainingResponse])
def get_employee_trainings(
    employee_id: int,
    status_filter: Optional[TrainingStatus] = None,
    current_user_id: int = 0,  # From auth
    db: Session = Depends(get_db),
    service: OnboardingService = Depends(get_onboarding_service)
):
    """Get training enrollments for employee."""
    trainings = service.get_employee_trainings(employee_id, status_filter, db)
    return trainings


# ==================== Equipment ====================

@router.post("/equipment", response_model=EquipmentResponse, status_code=status.HTTP_201_CREATED)
def assign_equipment(
    request: AssignEquipmentRequest,
    current_user_id: int,  # From auth
    db: Session = Depends(get_db),
    service: OnboardingService = Depends(get_onboarding_service)
):
    """Assign equipment to employee."""
    try:
        equipment = service.assign_equipment(
            employee_id=request.employee_id,
            equipment_type=request.equipment_type,
            name=request.name,
            company_id=request.company_id,
            serial_number=request.serial_number,
            asset_tag=request.asset_tag,
            db=db
        )
        return equipment
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to assign equipment: {str(e)}"
        )


@router.post("/equipment/{equipment_id}/return")
def return_equipment(
    equipment_id: int,
    condition: Optional[str] = None,
    notes: Optional[str] = None,
    current_user_id: int = 0,  # From auth
    db: Session = Depends(get_db),
    service: OnboardingService = Depends(get_onboarding_service)
):
    """Mark equipment as returned."""
    try:
        equipment = service.return_equipment(equipment_id, condition, notes, db)
        return {
            "message": "Equipment returned",
            "equipment_id": equipment.id,
            "status": equipment.status
        }
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e)
        )


@router.get("/equipment/employee/{employee_id}", response_model=List[EquipmentResponse])
def get_employee_equipment(
    employee_id: int,
    active_only: bool = True,
    current_user_id: int = 0,  # From auth
    db: Session = Depends(get_db),
    service: OnboardingService = Depends(get_onboarding_service)
):
    """Get equipment assigned to employee."""
    equipment = service.get_employee_equipment(employee_id, active_only, db)
    return equipment


# ==================== Documents ====================

@router.post("/documents", response_model=DocumentResponse, status_code=status.HTTP_201_CREATED)
def create_document(
    request: CreateDocumentRequest,
    current_user_id: int,  # From auth
    db: Session = Depends(get_db),
    service: OnboardingService = Depends(get_onboarding_service)
):
    """Create employee document."""
    try:
        document = service.create_document(
            employee_id=request.employee_id,
            document_type=request.document_type,
            title=request.title,
            file_url=request.file_url,
            requires_signature=request.requires_signature,
            due_date=request.due_date,
            db=db
        )
        return document
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create document: {str(e)}"
        )


@router.post("/documents/{document_id}/sign")
def sign_document(
    document_id: int,
    signature_url: Optional[str] = None,
    current_user_id: int = 0,  # From auth
    db: Session = Depends(get_db),
    service: OnboardingService = Depends(get_onboarding_service)
):
    """Mark document as signed."""
    try:
        document = service.sign_document(document_id, signature_url, db)
        return {
            "message": "Document signed",
            "document_id": document.id,
            "status": document.status,
            "signed_at": document.signed_at
        }
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e)
        )


@router.get("/documents/employee/{employee_id}", response_model=List[DocumentResponse])
def get_employee_documents(
    employee_id: int,
    document_type: Optional[DocumentType] = None,
    current_user_id: int = 0,  # From auth
    db: Session = Depends(get_db),
    service: OnboardingService = Depends(get_onboarding_service)
):
    """Get documents for employee."""
    documents = service.get_employee_documents(employee_id, document_type, db)
    return documents


# ==================== Time Off ====================

@router.post("/time-off", response_model=TimeOffResponse, status_code=status.HTTP_201_CREATED)
def request_time_off(
    request: TimeOffRequestCreate,
    current_user_id: int,  # From auth
    db: Session = Depends(get_db),
    service: OnboardingService = Depends(get_onboarding_service)
):
    """Create time off request."""
    try:
        time_off = service.request_time_off(
            employee_id=request.employee_id,
            time_off_type=request.time_off_type,
            start_date=request.start_date,
            end_date=request.end_date,
            reason=request.reason,
            db=db
        )
        return time_off
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create time off request: {str(e)}"
        )


@router.post("/time-off/{request_id}/approve")
def approve_time_off(
    request_id: int,
    approved_by_user_id: int,
    db: Session = Depends(get_db),
    service: OnboardingService = Depends(get_onboarding_service)
):
    """Approve time off request."""
    try:
        time_off = service.approve_time_off(request_id, approved_by_user_id, db)
        return {
            "message": "Time off approved",
            "request_id": time_off.id,
            "status": time_off.status
        }
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e)
        )


@router.post("/time-off/{request_id}/reject")
def reject_time_off(
    request_id: int,
    approved_by_user_id: int,
    rejection_reason: str,
    db: Session = Depends(get_db),
    service: OnboardingService = Depends(get_onboarding_service)
):
    """Reject time off request."""
    try:
        time_off = service.reject_time_off(request_id, approved_by_user_id, rejection_reason, db)
        return {
            "message": "Time off rejected",
            "request_id": time_off.id,
            "status": time_off.status,
            "rejection_reason": time_off.rejection_reason
        }
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e)
        )


# ==================== Performance Reviews ====================

@router.post("/reviews", response_model=ReviewResponse, status_code=status.HTTP_201_CREATED)
def create_review(
    request: CreateReviewRequest,
    current_user_id: int,  # From auth
    db: Session = Depends(get_db),
    service: OnboardingService = Depends(get_onboarding_service)
):
    """Create performance review."""
    try:
        review = service.create_review(
            employee_id=request.employee_id,
            reviewer_user_id=request.reviewer_user_id,
            review_type=request.review_type,
            scheduled_date=request.scheduled_date,
            review_period_start=request.review_period_start,
            review_period_end=request.review_period_end,
            db=db
        )
        return review
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create review: {str(e)}"
        )


@router.post("/reviews/{review_id}/complete", response_model=ReviewResponse)
def complete_review(
    review_id: int,
    request: CompleteReviewRequest,
    current_user_id: int,  # From auth
    db: Session = Depends(get_db),
    service: OnboardingService = Depends(get_onboarding_service)
):
    """Complete performance review."""
    try:
        review = service.complete_review(
            review_id=review_id,
            overall_rating=request.overall_rating,
            manager_comments=request.manager_comments,
            strengths=request.strengths,
            areas_for_improvement=request.areas_for_improvement,
            achievements=request.achievements,
            goals=request.goals,
            performance_rating=request.performance_rating,
            communication_rating=request.communication_rating,
            teamwork_rating=request.teamwork_rating,
            promotion_recommended=request.promotion_recommended,
            raise_recommended=request.raise_recommended,
            raise_amount=request.raise_amount,
            db=db
        )
        return review
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e)
        )


@router.get("/reviews/employee/{employee_id}", response_model=List[ReviewResponse])
def get_employee_reviews(
    employee_id: int,
    current_user_id: int,  # From auth
    db: Session = Depends(get_db),
    service: OnboardingService = Depends(get_onboarding_service)
):
    """Get all reviews for employee."""
    reviews = service.get_employee_reviews(employee_id, db)
    return reviews
