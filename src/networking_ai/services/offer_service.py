"""
Offer Service - Phase 4.

Handles job offer creation, sending, negotiation, and lifecycle management.
"""

from datetime import datetime, timedelta
from typing import Optional, List, Dict
from sqlalchemy.orm import Session
from sqlalchemy import and_, or_

from ..models.job_offer import (
    JobOffer,
    OfferNegotiation,
    OfferStatus,
    NegotiationType,
    NegotiationStatus
)
from ..models.application import Application, ApplicationStatus
from ..models.job import Job
from ..models.user import User
from ..models.notification import NotificationType, NotificationPriority


class OfferService:
    """
    Service for managing job offers and negotiations.

    Handles the complete offer lifecycle from creation to acceptance/decline.
    """

    def __init__(
        self,
        notification_service=None,
        enable_notifications: bool = True
    ):
        """
        Initialize the offer service.

        Args:
            notification_service: Optional notification service for sending alerts
            enable_notifications: Whether to send notifications (default True)
        """
        self.notification_service = notification_service
        self.enable_notifications = enable_notifications

    # ==================== Offer Creation ====================

    def create_offer(
        self,
        application_id: int,
        job_id: int,
        company_id: int,
        candidate_user_id: int,
        hiring_manager_id: int,
        created_by_user_id: int,
        position_title: str,
        base_salary: float,
        salary_currency: str = "USD",
        employment_type: str = "full_time",
        bonus_amount: Optional[float] = None,
        signing_bonus: Optional[float] = None,
        equity_shares: Optional[int] = None,
        equity_value: Optional[float] = None,
        equity_vesting_years: Optional[int] = None,
        department: Optional[str] = None,
        start_date: Optional[datetime] = None,
        benefits: Optional[List[str]] = None,
        pto_days: Optional[int] = None,
        remote_work_allowed: bool = False,
        relocation_assistance: Optional[float] = None,
        probation_period_months: Optional[int] = None,
        special_conditions: Optional[str] = None,
        notes: Optional[str] = None,
        db: Session = None
    ) -> JobOffer:
        """
        Create a new job offer (draft status).

        Args:
            application_id: Related application ID
            job_id: Related job ID
            company_id: Company ID
            candidate_user_id: Candidate's user ID
            hiring_manager_id: Hiring manager's user ID
            created_by_user_id: User creating the offer
            position_title: Job title
            base_salary: Annual base salary
            salary_currency: Currency code (default USD)
            employment_type: full_time, part_time, contract
            (other compensation and benefits params...)
            db: Database session

        Returns:
            Created JobOffer object
        """
        offer = JobOffer(
            application_id=application_id,
            job_id=job_id,
            company_id=company_id,
            candidate_user_id=candidate_user_id,
            hiring_manager_id=hiring_manager_id,
            created_by_user_id=created_by_user_id,
            position_title=position_title,
            department=department,
            start_date=start_date,
            base_salary=base_salary,
            salary_currency=salary_currency,
            bonus_amount=bonus_amount,
            signing_bonus=signing_bonus,
            equity_shares=equity_shares,
            equity_value=equity_value,
            equity_vesting_years=equity_vesting_years,
            benefits=benefits,
            pto_days=pto_days,
            remote_work_allowed=remote_work_allowed,
            relocation_assistance=relocation_assistance,
            employment_type=employment_type,
            probation_period_months=probation_period_months,
            special_conditions=special_conditions,
            notes=notes,
            status=OfferStatus.DRAFT
        )

        db.add(offer)
        db.commit()
        db.refresh(offer)

        return offer

    # ==================== Offer Sending ====================

    def send_offer(
        self,
        offer_id: int,
        expires_in_days: int = 7,
        offer_letter_url: Optional[str] = None,
        db: Session = None
    ) -> JobOffer:
        """
        Send offer to candidate.

        Updates status to PENDING, sets expiration, and sends notifications.

        Args:
            offer_id: Offer ID to send
            expires_in_days: How many days until offer expires
            offer_letter_url: URL to formal offer letter document
            db: Database session

        Returns:
            Updated JobOffer object
        """
        offer = db.query(JobOffer).filter(JobOffer.id == offer_id).first()

        if not offer:
            raise ValueError("Offer not found")

        if offer.status != OfferStatus.DRAFT:
            raise ValueError("Only draft offers can be sent")

        # Send the offer
        offer.send_offer(expires_in_days=expires_in_days)

        if offer_letter_url:
            offer.offer_letter_url = offer_letter_url

        # Update application status
        application = db.query(Application).filter(
            Application.id == offer.application_id
        ).first()
        if application:
            application.status = ApplicationStatus.OFFER_EXTENDED

        db.commit()
        db.refresh(offer)

        # Send notification
        if self.enable_notifications and self.notification_service:
            self._send_offer_notification(offer, db)

        return offer

    # ==================== Offer Response ====================

    def accept_offer(
        self,
        offer_id: int,
        db: Session
    ) -> JobOffer:
        """
        Candidate accepts the offer.

        Args:
            offer_id: Offer ID
            db: Database session

        Returns:
            Updated JobOffer object
        """
        offer = db.query(JobOffer).filter(JobOffer.id == offer_id).first()

        if not offer:
            raise ValueError("Offer not found")

        if not offer.is_pending_response():
            raise ValueError("Offer is not pending response")

        if offer.is_expired():
            offer.status = OfferStatus.EXPIRED
            db.commit()
            raise ValueError("Offer has expired")

        offer.accept_offer()

        # Update application status
        application = db.query(Application).filter(
            Application.id == offer.application_id
        ).first()
        if application:
            application.status = ApplicationStatus.OFFER_ACCEPTED

        db.commit()
        db.refresh(offer)

        # Send notification
        if self.enable_notifications and self.notification_service:
            self._send_offer_accepted_notification(offer, db)

        return offer

    def decline_offer(
        self,
        offer_id: int,
        reason: Optional[str] = None,
        db: Session = None
    ) -> JobOffer:
        """
        Candidate declines the offer.

        Args:
            offer_id: Offer ID
            reason: Optional reason for declining
            db: Database session

        Returns:
            Updated JobOffer object
        """
        offer = db.query(JobOffer).filter(JobOffer.id == offer_id).first()

        if not offer:
            raise ValueError("Offer not found")

        if not offer.is_pending_response():
            raise ValueError("Offer is not pending response")

        offer.decline_offer(reason=reason)

        # Update application status
        application = db.query(Application).filter(
            Application.id == offer.application_id
        ).first()
        if application:
            application.status = ApplicationStatus.OFFER_DECLINED

        db.commit()
        db.refresh(offer)

        # Send notification
        if self.enable_notifications and self.notification_service:
            self._send_offer_declined_notification(offer, db)

        return offer

    def withdraw_offer(
        self,
        offer_id: int,
        user_id: int,
        reason: Optional[str] = None,
        db: Session = None
    ) -> JobOffer:
        """
        Company withdraws the offer.

        Args:
            offer_id: Offer ID
            user_id: User withdrawing the offer
            reason: Reason for withdrawal
            db: Database session

        Returns:
            Updated JobOffer object
        """
        offer = db.query(JobOffer).filter(JobOffer.id == offer_id).first()

        if not offer:
            raise ValueError("Offer not found")

        if offer.status in [OfferStatus.ACCEPTED, OfferStatus.DECLINED]:
            raise ValueError("Cannot withdraw an offer that has been accepted or declined")

        offer.withdraw_offer(user_id=user_id, reason=reason)
        db.commit()
        db.refresh(offer)

        # Send notification
        if self.enable_notifications and self.notification_service:
            self._send_offer_withdrawn_notification(offer, db)

        return offer

    # ==================== Negotiation ====================

    def start_negotiation(
        self,
        offer_id: int,
        initiated_by_user_id: int,
        negotiation_type: NegotiationType,
        proposed_value: str,
        original_value: Optional[str] = None,
        message: Optional[str] = None,
        db: Session = None
    ) -> OfferNegotiation:
        """
        Start a negotiation on an offer.

        Args:
            offer_id: Offer ID
            initiated_by_user_id: User initiating negotiation (usually candidate)
            negotiation_type: Type of negotiation (salary, benefits, etc.)
            proposed_value: Proposed new value
            original_value: Original offer value
            message: Candidate's message/justification
            db: Database session

        Returns:
            Created OfferNegotiation object
        """
        offer = db.query(JobOffer).filter(JobOffer.id == offer_id).first()

        if not offer:
            raise ValueError("Offer not found")

        if offer.status not in [OfferStatus.PENDING, OfferStatus.UNDER_NEGOTIATION]:
            raise ValueError("Can only negotiate pending offers")

        # Update offer status
        offer.start_negotiation()

        # Create negotiation record
        negotiation = OfferNegotiation(
            offer_id=offer_id,
            round_number=offer.negotiation_rounds,
            initiated_by_user_id=initiated_by_user_id,
            negotiation_type=negotiation_type,
            original_value=original_value,
            proposed_value=proposed_value,
            candidate_message=message,
            status=NegotiationStatus.OPEN
        )

        db.add(negotiation)
        db.commit()
        db.refresh(negotiation)

        # Send notification
        if self.enable_notifications and self.notification_service:
            self._send_negotiation_started_notification(offer, negotiation, db)

        return negotiation

    def counter_offer_negotiation(
        self,
        negotiation_id: int,
        counter_value: str,
        message: Optional[str] = None,
        db: Session = None
    ) -> OfferNegotiation:
        """
        Company makes counter offer to negotiation.

        Args:
            negotiation_id: Negotiation ID
            counter_value: Company's counter offer value
            message: Company's message
            db: Database session

        Returns:
            Updated OfferNegotiation object
        """
        negotiation = db.query(OfferNegotiation).filter(
            OfferNegotiation.id == negotiation_id
        ).first()

        if not negotiation:
            raise ValueError("Negotiation not found")

        if negotiation.status != NegotiationStatus.OPEN:
            raise ValueError("Can only counter open negotiations")

        negotiation.counter_offer(counter_value=counter_value, message=message)
        db.commit()
        db.refresh(negotiation)

        # Send notification
        if self.enable_notifications and self.notification_service:
            self._send_counter_offer_notification(negotiation, db)

        return negotiation

    def accept_negotiation(
        self,
        negotiation_id: int,
        user_id: int,
        db: Session = None
    ) -> OfferNegotiation:
        """
        Accept a negotiation proposal.

        Args:
            negotiation_id: Negotiation ID
            user_id: User accepting
            db: Database session

        Returns:
            Updated OfferNegotiation object
        """
        negotiation = db.query(OfferNegotiation).filter(
            OfferNegotiation.id == negotiation_id
        ).first()

        if not negotiation:
            raise ValueError("Negotiation not found")

        negotiation.accept_proposal(user_id=user_id)
        db.commit()
        db.refresh(negotiation)

        # Send notification
        if self.enable_notifications and self.notification_service:
            self._send_negotiation_accepted_notification(negotiation, db)

        return negotiation

    def reject_negotiation(
        self,
        negotiation_id: int,
        user_id: int,
        message: Optional[str] = None,
        db: Session = None
    ) -> OfferNegotiation:
        """
        Reject a negotiation proposal.

        Args:
            negotiation_id: Negotiation ID
            user_id: User rejecting
            message: Rejection message
            db: Database session

        Returns:
            Updated OfferNegotiation object
        """
        negotiation = db.query(OfferNegotiation).filter(
            OfferNegotiation.id == negotiation_id
        ).first()

        if not negotiation:
            raise ValueError("Negotiation not found")

        negotiation.reject_proposal(user_id=user_id, message=message)
        db.commit()
        db.refresh(negotiation)

        # Send notification
        if self.enable_notifications and self.notification_service:
            self._send_negotiation_rejected_notification(negotiation, db)

        return negotiation

    # ==================== Query Methods ====================

    def get_offer(
        self,
        offer_id: int,
        db: Session
    ) -> Optional[JobOffer]:
        """Get offer by ID."""
        return db.query(JobOffer).filter(JobOffer.id == offer_id).first()

    def get_offers_for_candidate(
        self,
        candidate_user_id: int,
        db: Session,
        pending_only: bool = False
    ) -> List[JobOffer]:
        """Get all offers for a candidate."""
        query = db.query(JobOffer).filter(
            JobOffer.candidate_user_id == candidate_user_id
        )

        if pending_only:
            query = query.filter(
                JobOffer.status.in_([OfferStatus.PENDING, OfferStatus.UNDER_NEGOTIATION])
            )

        return query.order_by(JobOffer.created_at.desc()).all()

    def get_offers_for_application(
        self,
        application_id: int,
        db: Session
    ) -> List[JobOffer]:
        """Get all offers for an application."""
        return db.query(JobOffer).filter(
            JobOffer.application_id == application_id
        ).order_by(JobOffer.created_at.desc()).all()

    def get_offers_for_company(
        self,
        company_id: int,
        db: Session,
        status: Optional[OfferStatus] = None
    ) -> List[JobOffer]:
        """Get all offers for a company."""
        query = db.query(JobOffer).filter(JobOffer.company_id == company_id)

        if status:
            query = query.filter(JobOffer.status == status)

        return query.order_by(JobOffer.created_at.desc()).all()

    def get_negotiations_for_offer(
        self,
        offer_id: int,
        db: Session
    ) -> List[OfferNegotiation]:
        """Get all negotiations for an offer."""
        return db.query(OfferNegotiation).filter(
            OfferNegotiation.offer_id == offer_id
        ).order_by(OfferNegotiation.created_at).all()

    # ==================== Expiration Check ====================

    def check_expired_offers(
        self,
        db: Session
    ) -> Dict[str, int]:
        """
        Check for expired offers and update their status.

        Should be called by a scheduled task.

        Args:
            db: Database session

        Returns:
            Dict with count of expired offers
        """
        now = datetime.utcnow()

        # Find offers that have expired
        expired_offers = db.query(JobOffer).filter(
            and_(
                JobOffer.status.in_([OfferStatus.PENDING, OfferStatus.UNDER_NEGOTIATION]),
                JobOffer.expires_at <= now
            )
        ).all()

        for offer in expired_offers:
            offer.status = OfferStatus.EXPIRED

        db.commit()

        return {"expired_offers": len(expired_offers)}

    # ==================== Private Helper Methods ====================

    def _send_offer_notification(self, offer: JobOffer, db: Session):
        """Send notification when offer is sent."""
        if not self.notification_service:
            return

        job = db.query(Job).filter(Job.id == offer.job_id).first()

        self.notification_service.create_notification(
            user_id=offer.candidate_user_id,
            notification_type=NotificationType.OFFER_RECEIVED,
            title=f"Job Offer: {offer.position_title}",
            message=f"Congratulations! You've received a job offer for {offer.position_title}. Base salary: ${offer.base_salary:,.0f}/year. Respond by {offer.response_deadline.strftime('%B %d, %Y')}.",
            channels=["in_app", "email"],
            priority=NotificationPriority.URGENT,
            action_url=f"/offers/{offer.id}",
            action_text="View Offer",
            extra_data={
                "offer_id": offer.id,
                "job_id": offer.job_id,
                "base_salary": offer.base_salary,
                "expires_at": offer.expires_at.isoformat() if offer.expires_at else None
            },
            db=db
        )

    def _send_offer_accepted_notification(self, offer: JobOffer, db: Session):
        """Send notification when offer is accepted."""
        if not self.notification_service:
            return

        self.notification_service.create_notification(
            user_id=offer.hiring_manager_id,
            notification_type=NotificationType.APPLICATION_STATUS_CHANGE,
            title="Offer Accepted",
            message=f"Candidate accepted the job offer for {offer.position_title}!",
            channels=["in_app", "email"],
            priority=NotificationPriority.HIGH,
            action_url=f"/offers/{offer.id}",
            action_text="View Details",
            db=db
        )

    def _send_offer_declined_notification(self, offer: JobOffer, db: Session):
        """Send notification when offer is declined."""
        if not self.notification_service:
            return

        self.notification_service.create_notification(
            user_id=offer.hiring_manager_id,
            notification_type=NotificationType.APPLICATION_STATUS_CHANGE,
            title="Offer Declined",
            message=f"Candidate declined the job offer for {offer.position_title}.",
            channels=["in_app", "email"],
            priority=NotificationPriority.HIGH,
            action_url=f"/offers/{offer.id}",
            action_text="View Details",
            db=db
        )

    def _send_offer_withdrawn_notification(self, offer: JobOffer, db: Session):
        """Send notification when offer is withdrawn."""
        if not self.notification_service:
            return

        self.notification_service.create_notification(
            user_id=offer.candidate_user_id,
            notification_type=NotificationType.APPLICATION_STATUS_CHANGE,
            title="Offer Withdrawn",
            message=f"The job offer for {offer.position_title} has been withdrawn.",
            channels=["in_app", "email"],
            priority=NotificationPriority.HIGH,
            action_url=f"/applications/{offer.application_id}",
            action_text="View Application",
            db=db
        )

    def _send_negotiation_started_notification(
        self,
        offer: JobOffer,
        negotiation: OfferNegotiation,
        db: Session
    ):
        """Send notification when negotiation starts."""
        if not self.notification_service:
            return

        self.notification_service.create_notification(
            user_id=offer.hiring_manager_id,
            notification_type=NotificationType.APPLICATION_STATUS_CHANGE,
            title="Offer Negotiation Started",
            message=f"Candidate has started negotiating the offer for {offer.position_title} - {negotiation.negotiation_type.value}",
            channels=["in_app", "email"],
            priority=NotificationPriority.HIGH,
            action_url=f"/offers/{offer.id}/negotiations",
            action_text="Review Negotiation",
            db=db
        )

    def _send_counter_offer_notification(self, negotiation: OfferNegotiation, db: Session):
        """Send notification when company makes counter offer."""
        if not self.notification_service:
            return

        offer = negotiation.offer

        self.notification_service.create_notification(
            user_id=offer.candidate_user_id,
            notification_type=NotificationType.APPLICATION_STATUS_CHANGE,
            title="Counter Offer Received",
            message=f"The company has made a counter offer on your {negotiation.negotiation_type.value} negotiation.",
            channels=["in_app", "email"],
            priority=NotificationPriority.HIGH,
            action_url=f"/offers/{offer.id}/negotiations",
            action_text="View Counter Offer",
            db=db
        )

    def _send_negotiation_accepted_notification(self, negotiation: OfferNegotiation, db: Session):
        """Send notification when negotiation is accepted."""
        if not self.notification_service:
            return

        offer = negotiation.offer

        # Notify the other party
        recipient_id = (
            offer.hiring_manager_id
            if negotiation.initiated_by_user_id == offer.candidate_user_id
            else offer.candidate_user_id
        )

        self.notification_service.create_notification(
            user_id=recipient_id,
            notification_type=NotificationType.APPLICATION_STATUS_CHANGE,
            title="Negotiation Accepted",
            message=f"Your {negotiation.negotiation_type.value} proposal has been accepted!",
            channels=["in_app", "email"],
            priority=NotificationPriority.HIGH,
            action_url=f"/offers/{offer.id}",
            action_text="View Offer",
            db=db
        )

    def _send_negotiation_rejected_notification(self, negotiation: OfferNegotiation, db: Session):
        """Send notification when negotiation is rejected."""
        if not self.notification_service:
            return

        offer = negotiation.offer

        # Notify the other party
        recipient_id = (
            offer.hiring_manager_id
            if negotiation.initiated_by_user_id == offer.candidate_user_id
            else offer.candidate_user_id
        )

        self.notification_service.create_notification(
            user_id=recipient_id,
            notification_type=NotificationType.APPLICATION_STATUS_CHANGE,
            title="Negotiation Declined",
            message=f"Your {negotiation.negotiation_type.value} proposal was declined.",
            channels=["in_app", "email"],
            priority=NotificationPriority.NORMAL,
            action_url=f"/offers/{offer.id}",
            action_text="View Offer",
            db=db
        )


# ==================== Factory Function ====================

def create_offer_service(
    notification_service=None,
    enable_notifications: bool = True
) -> OfferService:
    """
    Factory function to create OfferService.

    Args:
        notification_service: Optional notification service
        enable_notifications: Whether to send notifications

    Returns:
        OfferService instance
    """
    return OfferService(
        notification_service=notification_service,
        enable_notifications=enable_notifications
    )
