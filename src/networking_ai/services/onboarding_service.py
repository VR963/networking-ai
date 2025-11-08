"""
Onboarding Service - Phase 9.

Business logic for post-hire employee management including onboarding, training,
equipment, documents, time off, and performance reviews.
"""

from datetime import datetime, date, timedelta
from typing import List, Optional, Dict, Any
from sqlalchemy.orm import Session
from sqlalchemy import and_, or_

from ..models.onboarding import (
    Employee, OnboardingChecklist, OnboardingTask, TrainingProgram,
    EmployeeTraining, Equipment, EmployeeDocument, TimeOffRequest,
    EmployeeReview,
    EmploymentType, EmploymentStatus, OnboardingStatus, TaskStatus,
    TaskCategory, TrainingStatus, TrainingType, EquipmentStatus,
    EquipmentType, DocumentType, DocumentStatus, TimeOffType,
    TimeOffStatus, ReviewType, ReviewStatus
)
from ..models.user import User
from ..models.company import Company
from ..models.job import Job
from ..models.application import Application


class OnboardingService:
    """Service for managing employee onboarding and lifecycle."""

    # ==================== Employee Management ====================

    def create_employee(
        self,
        user_id: int,
        company_id: int,
        job_id: int,
        application_id: int,
        job_title: str,
        employment_type: EmploymentType,
        hire_date: date,
        start_date: date,
        base_salary: Optional[int] = None,
        department: Optional[str] = None,
        manager_user_id: Optional[int] = None,
        work_email: Optional[str] = None,
        db: Session = None
    ) -> Employee:
        """
        Create employee record for a hired candidate.

        Args:
            user_id: User ID of the hired candidate
            company_id: Company ID
            job_id: Job they were hired for
            application_id: Application that led to hire
            job_title: Job title
            employment_type: Type of employment
            hire_date: Date offer was accepted
            start_date: First day of work
            base_salary: Annual/hourly salary
            department: Department
            manager_user_id: Manager's user ID
            work_email: Work email address
            db: Database session

        Returns:
            Created Employee record
        """
        # Generate employee ID
        count = db.query(Employee).filter(Employee.company_id == company_id).count()
        employee_id = f"EMP{company_id:04d}{count + 1:05d}"

        # Calculate probation end (typically 90 days)
        probation_end = start_date + timedelta(days=90)

        employee = Employee(
            user_id=user_id,
            company_id=company_id,
            job_id=job_id,
            application_id=application_id,
            employee_id=employee_id,
            employment_type=employment_type,
            employment_status=EmploymentStatus.ACTIVE,
            hire_date=hire_date,
            start_date=start_date,
            probation_end_date=probation_end,
            job_title=job_title,
            department=department,
            manager_user_id=manager_user_id,
            base_salary=base_salary,
            work_email=work_email,
            onboarding_status=OnboardingStatus.NOT_STARTED,
            onboarding_progress=0.0
        )

        db.add(employee)
        db.commit()
        db.refresh(employee)

        return employee

    def update_employee(
        self,
        employee_id: int,
        updates: Dict[str, Any],
        db: Session
    ) -> Employee:
        """
        Update employee record.

        Args:
            employee_id: Employee ID
            updates: Dictionary of fields to update
            db: Database session

        Returns:
            Updated Employee
        """
        employee = db.query(Employee).get(employee_id)
        if not employee:
            raise ValueError(f"Employee {employee_id} not found")

        for key, value in updates.items():
            if hasattr(employee, key):
                setattr(employee, key, value)

        db.commit()
        db.refresh(employee)

        return employee

    def get_employee(
        self,
        employee_id: int,
        db: Session
    ) -> Optional[Employee]:
        """Get employee by ID."""
        return db.query(Employee).get(employee_id)

    def get_employee_by_user(
        self,
        user_id: int,
        db: Session
    ) -> Optional[Employee]:
        """Get employee record by user ID."""
        return db.query(Employee).filter(Employee.user_id == user_id).first()

    def terminate_employee(
        self,
        employee_id: int,
        end_date: date,
        reason: Optional[str] = None,
        db: Session = None
    ) -> Employee:
        """
        Terminate employee.

        Args:
            employee_id: Employee ID
            end_date: Last day of employment
            reason: Termination reason
            db: Database session

        Returns:
            Updated Employee
        """
        employee = self.get_employee(employee_id, db)
        if not employee:
            raise ValueError(f"Employee {employee_id} not found")

        employee.employment_status = EmploymentStatus.TERMINATED
        employee.end_date = end_date

        if reason:
            if not employee.notes:
                employee.notes = ""
            employee.notes += f"\nTermination reason: {reason}"

        db.commit()
        db.refresh(employee)

        return employee

    # ==================== Onboarding Management ====================

    def start_onboarding(
        self,
        employee_id: int,
        checklist_id: Optional[int] = None,
        db: Session = None
    ) -> Employee:
        """
        Start onboarding process for an employee.

        Creates onboarding tasks from checklist template.

        Args:
            employee_id: Employee ID
            checklist_id: Onboarding checklist to use (optional)
            db: Database session

        Returns:
            Updated Employee with tasks created
        """
        employee = self.get_employee(employee_id, db)
        if not employee:
            raise ValueError(f"Employee {employee_id} not found")

        # Update status
        employee.onboarding_status = OnboardingStatus.IN_PROGRESS

        # Find appropriate checklist if not specified
        if not checklist_id:
            checklist = db.query(OnboardingChecklist).filter(
                OnboardingChecklist.company_id == employee.company_id,
                OnboardingChecklist.active == True,
                or_(
                    OnboardingChecklist.department == employee.department,
                    OnboardingChecklist.job_title == employee.job_title,
                    OnboardingChecklist.employment_type == employee.employment_type,
                    OnboardingChecklist.is_default == True
                )
            ).first()
            if checklist:
                checklist_id = checklist.id

        # Create tasks from checklist
        if checklist_id:
            checklist = db.query(OnboardingChecklist).get(checklist_id)
            if checklist and checklist.tasks:
                for task_data in checklist.tasks:
                    # Calculate due date based on start date + due_days
                    due_days = task_data.get('due_days', 7)
                    due_date = employee.start_date + timedelta(days=due_days)

                    task = OnboardingTask(
                        employee_id=employee_id,
                        checklist_id=checklist_id,
                        title=task_data['title'],
                        description=task_data.get('description'),
                        category=TaskCategory(task_data.get('category', 'custom')),
                        due_date=due_date,
                        priority=task_data.get('priority', 0),
                        status=TaskStatus.PENDING
                    )
                    db.add(task)

        db.commit()
        db.refresh(employee)

        # Update progress
        self._update_onboarding_progress(employee_id, db)

        return employee

    def create_onboarding_task(
        self,
        employee_id: int,
        title: str,
        category: TaskCategory,
        description: Optional[str] = None,
        due_date: Optional[date] = None,
        assigned_to_user_id: Optional[int] = None,
        priority: int = 0,
        db: Session = None
    ) -> OnboardingTask:
        """
        Create an onboarding task.

        Args:
            employee_id: Employee ID
            title: Task title
            category: Task category
            description: Task description
            due_date: Due date
            assigned_to_user_id: User assigned to complete task
            priority: Priority (higher = more important)
            db: Database session

        Returns:
            Created OnboardingTask
        """
        task = OnboardingTask(
            employee_id=employee_id,
            title=title,
            description=description,
            category=category,
            due_date=due_date,
            assigned_to_user_id=assigned_to_user_id,
            priority=priority,
            status=TaskStatus.PENDING
        )

        db.add(task)
        db.commit()
        db.refresh(task)

        # Update onboarding progress
        self._update_onboarding_progress(employee_id, db)

        return task

    def complete_task(
        self,
        task_id: int,
        completed_by_user_id: int,
        notes: Optional[str] = None,
        db: Session = None
    ) -> OnboardingTask:
        """
        Mark an onboarding task as completed.

        Args:
            task_id: Task ID
            completed_by_user_id: User who completed the task
            notes: Completion notes
            db: Database session

        Returns:
            Updated OnboardingTask
        """
        task = db.query(OnboardingTask).get(task_id)
        if not task:
            raise ValueError(f"Task {task_id} not found")

        task.status = TaskStatus.COMPLETED
        task.completed_at = datetime.utcnow()
        task.completed_by_user_id = completed_by_user_id

        if notes:
            task.notes = notes

        db.commit()
        db.refresh(task)

        # Update onboarding progress
        self._update_onboarding_progress(task.employee_id, db)

        return task

    def get_onboarding_tasks(
        self,
        employee_id: int,
        status: Optional[TaskStatus] = None,
        db: Session = None
    ) -> List[OnboardingTask]:
        """
        Get onboarding tasks for an employee.

        Args:
            employee_id: Employee ID
            status: Filter by status (optional)
            db: Database session

        Returns:
            List of OnboardingTask
        """
        query = db.query(OnboardingTask).filter(
            OnboardingTask.employee_id == employee_id
        )

        if status:
            query = query.filter(OnboardingTask.status == status)

        return query.order_by(OnboardingTask.priority.desc(), OnboardingTask.due_date).all()

    def _update_onboarding_progress(
        self,
        employee_id: int,
        db: Session
    ) -> None:
        """Update employee onboarding progress percentage."""
        employee = self.get_employee(employee_id, db)
        if not employee:
            return

        tasks = self.get_onboarding_tasks(employee_id, db=db)
        if not tasks:
            return

        completed = sum(1 for t in tasks if t.status == TaskStatus.COMPLETED)
        total = len(tasks)
        progress = (completed / total * 100) if total > 0 else 0

        employee.onboarding_progress = round(progress, 2)

        # Mark onboarding complete if 100%
        if progress >= 100 and employee.onboarding_status != OnboardingStatus.COMPLETED:
            employee.onboarding_status = OnboardingStatus.COMPLETED
            employee.onboarding_completed_at = datetime.utcnow()

        db.commit()

    # ==================== Training Management ====================

    def enroll_in_training(
        self,
        employee_id: int,
        program_id: int,
        due_date: Optional[date] = None,
        db: Session = None
    ) -> EmployeeTraining:
        """
        Enroll employee in training program.

        Args:
            employee_id: Employee ID
            program_id: Training program ID
            due_date: Due date for completion
            db: Database session

        Returns:
            Created EmployeeTraining
        """
        # Check if already enrolled
        existing = db.query(EmployeeTraining).filter(
            EmployeeTraining.employee_id == employee_id,
            EmployeeTraining.program_id == program_id
        ).first()

        if existing:
            return existing

        program = db.query(TrainingProgram).get(program_id)
        if not program:
            raise ValueError(f"Training program {program_id} not found")

        # Calculate expiry if applicable
        expires_at = None
        if program.expires_after_days:
            expires_at = datetime.utcnow() + timedelta(days=program.expires_after_days)

        training = EmployeeTraining(
            employee_id=employee_id,
            program_id=program_id,
            status=TrainingStatus.NOT_STARTED,
            due_date=due_date,
            expires_at=expires_at
        )

        db.add(training)
        db.commit()
        db.refresh(training)

        return training

    def start_training(
        self,
        training_id: int,
        db: Session
    ) -> EmployeeTraining:
        """Mark training as started."""
        training = db.query(EmployeeTraining).get(training_id)
        if not training:
            raise ValueError(f"Training {training_id} not found")

        if training.status == TrainingStatus.NOT_STARTED:
            training.status = TrainingStatus.IN_PROGRESS
            training.started_at = datetime.utcnow()
            db.commit()
            db.refresh(training)

        return training

    def complete_training(
        self,
        training_id: int,
        score: Optional[float] = None,
        certificate_url: Optional[str] = None,
        db: Session = None
    ) -> EmployeeTraining:
        """
        Mark training as completed.

        Args:
            training_id: Training enrollment ID
            score: Assessment score (if applicable)
            certificate_url: URL to certificate
            db: Database session

        Returns:
            Updated EmployeeTraining
        """
        training = db.query(EmployeeTraining).get(training_id)
        if not training:
            raise ValueError(f"Training {training_id} not found")

        program = training.program

        # Check if passed (if has passing score requirement)
        passed = True
        if program.passing_score and score:
            passed = score >= program.passing_score

        training.status = TrainingStatus.COMPLETED if passed else TrainingStatus.FAILED
        training.completed_at = datetime.utcnow()
        training.progress = 100.0
        training.score = score
        training.passed = passed
        training.attempts += 1

        if certificate_url:
            training.certificate_url = certificate_url
            training.certificate_issued_at = datetime.utcnow()

        db.commit()
        db.refresh(training)

        return training

    def get_employee_trainings(
        self,
        employee_id: int,
        status: Optional[TrainingStatus] = None,
        db: Session = None
    ) -> List[EmployeeTraining]:
        """Get training enrollments for employee."""
        query = db.query(EmployeeTraining).filter(
            EmployeeTraining.employee_id == employee_id
        )

        if status:
            query = query.filter(EmployeeTraining.status == status)

        return query.all()

    # ==================== Equipment Management ====================

    def assign_equipment(
        self,
        employee_id: int,
        equipment_type: EquipmentType,
        name: str,
        company_id: int,
        serial_number: Optional[str] = None,
        asset_tag: Optional[str] = None,
        db: Session = None
    ) -> Equipment:
        """
        Assign equipment to employee.

        Args:
            employee_id: Employee ID
            equipment_type: Type of equipment
            name: Equipment name/model
            company_id: Company ID
            serial_number: Serial number
            asset_tag: Asset tag
            db: Database session

        Returns:
            Created/updated Equipment
        """
        equipment = Equipment(
            company_id=company_id,
            employee_id=employee_id,
            equipment_type=equipment_type,
            name=name,
            serial_number=serial_number,
            asset_tag=asset_tag,
            status=EquipmentStatus.ASSIGNED,
            assigned_at=datetime.utcnow()
        )

        db.add(equipment)
        db.commit()
        db.refresh(equipment)

        return equipment

    def return_equipment(
        self,
        equipment_id: int,
        condition: Optional[str] = None,
        notes: Optional[str] = None,
        db: Session = None
    ) -> Equipment:
        """
        Mark equipment as returned.

        Args:
            equipment_id: Equipment ID
            condition: Condition upon return
            notes: Return notes
            db: Database session

        Returns:
            Updated Equipment
        """
        equipment = db.query(Equipment).get(equipment_id)
        if not equipment:
            raise ValueError(f"Equipment {equipment_id} not found")

        equipment.status = EquipmentStatus.RETURNED
        equipment.returned_at = datetime.utcnow()

        if condition:
            equipment.condition = condition
        if notes:
            equipment.notes = notes

        db.commit()
        db.refresh(equipment)

        return equipment

    def get_employee_equipment(
        self,
        employee_id: int,
        active_only: bool = True,
        db: Session = None
    ) -> List[Equipment]:
        """Get equipment assigned to employee."""
        query = db.query(Equipment).filter(
            Equipment.employee_id == employee_id
        )

        if active_only:
            query = query.filter(
                Equipment.status.in_([EquipmentStatus.ASSIGNED, EquipmentStatus.IN_USE])
            )

        return query.all()

    # ==================== Document Management ====================

    def create_document(
        self,
        employee_id: int,
        document_type: DocumentType,
        title: str,
        file_url: Optional[str] = None,
        requires_signature: bool = False,
        due_date: Optional[date] = None,
        db: Session = None
    ) -> EmployeeDocument:
        """
        Create employee document.

        Args:
            employee_id: Employee ID
            document_type: Type of document
            title: Document title
            file_url: URL to document file
            requires_signature: Whether signature is required
            due_date: Due date for signature
            db: Database session

        Returns:
            Created EmployeeDocument
        """
        document = EmployeeDocument(
            employee_id=employee_id,
            document_type=document_type,
            title=title,
            file_url=file_url,
            requires_signature=requires_signature,
            due_date=due_date,
            status=DocumentStatus.PENDING
        )

        db.add(document)
        db.commit()
        db.refresh(document)

        return document

    def sign_document(
        self,
        document_id: int,
        signature_url: Optional[str] = None,
        db: Session = None
    ) -> EmployeeDocument:
        """
        Mark document as signed.

        Args:
            document_id: Document ID
            signature_url: URL to signature
            db: Database session

        Returns:
            Updated EmployeeDocument
        """
        document = db.query(EmployeeDocument).get(document_id)
        if not document:
            raise ValueError(f"Document {document_id} not found")

        document.status = DocumentStatus.SIGNED
        document.signed_at = datetime.utcnow()
        document.signature_url = signature_url

        db.commit()
        db.refresh(document)

        return document

    def get_employee_documents(
        self,
        employee_id: int,
        document_type: Optional[DocumentType] = None,
        db: Session = None
    ) -> List[EmployeeDocument]:
        """Get documents for employee."""
        query = db.query(EmployeeDocument).filter(
            EmployeeDocument.employee_id == employee_id
        )

        if document_type:
            query = query.filter(EmployeeDocument.document_type == document_type)

        return query.all()

    # ==================== Time Off Management ====================

    def request_time_off(
        self,
        employee_id: int,
        time_off_type: TimeOffType,
        start_date: date,
        end_date: date,
        reason: Optional[str] = None,
        db: Session = None
    ) -> TimeOffRequest:
        """
        Create time off request.

        Args:
            employee_id: Employee ID
            time_off_type: Type of time off
            start_date: Start date
            end_date: End date
            reason: Reason for request
            db: Database session

        Returns:
            Created TimeOffRequest
        """
        # Calculate total days (business days)
        total_days = (end_date - start_date).days + 1

        request = TimeOffRequest(
            employee_id=employee_id,
            time_off_type=time_off_type,
            start_date=start_date,
            end_date=end_date,
            total_days=total_days,
            reason=reason,
            status=TimeOffStatus.PENDING
        )

        db.add(request)
        db.commit()
        db.refresh(request)

        return request

    def approve_time_off(
        self,
        request_id: int,
        approved_by_user_id: int,
        db: Session = None
    ) -> TimeOffRequest:
        """
        Approve time off request.

        Args:
            request_id: Request ID
            approved_by_user_id: User approving the request
            db: Database session

        Returns:
            Updated TimeOffRequest
        """
        request = db.query(TimeOffRequest).get(request_id)
        if not request:
            raise ValueError(f"Time off request {request_id} not found")

        request.status = TimeOffStatus.APPROVED
        request.approved_by_user_id = approved_by_user_id
        request.approved_at = datetime.utcnow()

        db.commit()
        db.refresh(request)

        return request

    def reject_time_off(
        self,
        request_id: int,
        approved_by_user_id: int,
        rejection_reason: str,
        db: Session = None
    ) -> TimeOffRequest:
        """
        Reject time off request.

        Args:
            request_id: Request ID
            approved_by_user_id: User rejecting the request
            rejection_reason: Reason for rejection
            db: Database session

        Returns:
            Updated TimeOffRequest
        """
        request = db.query(TimeOffRequest).get(request_id)
        if not request:
            raise ValueError(f"Time off request {request_id} not found")

        request.status = TimeOffStatus.REJECTED
        request.approved_by_user_id = approved_by_user_id
        request.approved_at = datetime.utcnow()
        request.rejection_reason = rejection_reason

        db.commit()
        db.refresh(request)

        return request

    # ==================== Performance Reviews ====================

    def create_review(
        self,
        employee_id: int,
        reviewer_user_id: int,
        review_type: ReviewType,
        scheduled_date: Optional[date] = None,
        review_period_start: Optional[date] = None,
        review_period_end: Optional[date] = None,
        db: Session = None
    ) -> EmployeeReview:
        """
        Create performance review.

        Args:
            employee_id: Employee ID
            reviewer_user_id: Reviewer user ID
            review_type: Type of review
            scheduled_date: Scheduled review date
            review_period_start: Start of review period
            review_period_end: End of review period
            db: Database session

        Returns:
            Created EmployeeReview
        """
        review = EmployeeReview(
            employee_id=employee_id,
            reviewer_user_id=reviewer_user_id,
            review_type=review_type,
            scheduled_date=scheduled_date,
            review_period_start=review_period_start,
            review_period_end=review_period_end,
            status=ReviewStatus.SCHEDULED
        )

        db.add(review)
        db.commit()
        db.refresh(review)

        return review

    def complete_review(
        self,
        review_id: int,
        overall_rating: float,
        manager_comments: str,
        strengths: List[str],
        areas_for_improvement: List[str],
        achievements: Optional[List[str]] = None,
        goals: Optional[List[str]] = None,
        performance_rating: Optional[float] = None,
        communication_rating: Optional[float] = None,
        teamwork_rating: Optional[float] = None,
        promotion_recommended: bool = False,
        raise_recommended: bool = False,
        raise_amount: Optional[float] = None,
        db: Session = None
    ) -> EmployeeReview:
        """
        Complete performance review.

        Args:
            review_id: Review ID
            overall_rating: Overall rating (1-5)
            manager_comments: Manager's comments
            strengths: List of strengths
            areas_for_improvement: Areas for improvement
            achievements: List of achievements
            goals: List of goals for next period
            performance_rating: Performance rating
            communication_rating: Communication rating
            teamwork_rating: Teamwork rating
            promotion_recommended: Recommend for promotion
            raise_recommended: Recommend raise
            raise_amount: Recommended raise amount
            db: Database session

        Returns:
            Updated EmployeeReview
        """
        review = db.query(EmployeeReview).get(review_id)
        if not review:
            raise ValueError(f"Review {review_id} not found")

        review.status = ReviewStatus.COMPLETED
        review.completed_at = datetime.utcnow()
        review.overall_rating = overall_rating
        review.manager_comments = manager_comments
        review.strengths = strengths
        review.areas_for_improvement = areas_for_improvement

        if achievements:
            review.achievements = achievements
        if goals:
            review.goals = goals
        if performance_rating:
            review.performance_rating = performance_rating
        if communication_rating:
            review.communication_rating = communication_rating
        if teamwork_rating:
            review.teamwork_rating = teamwork_rating

        review.promotion_recommended = promotion_recommended
        review.raise_recommended = raise_recommended
        review.raise_amount = raise_amount

        db.commit()
        db.refresh(review)

        return review

    def get_employee_reviews(
        self,
        employee_id: int,
        db: Session = None
    ) -> List[EmployeeReview]:
        """Get all reviews for employee."""
        return db.query(EmployeeReview).filter(
            EmployeeReview.employee_id == employee_id
        ).order_by(EmployeeReview.scheduled_date.desc()).all()


def create_onboarding_service() -> OnboardingService:
    """Factory function to create OnboardingService instance."""
    return OnboardingService()
