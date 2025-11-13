"""
Job Offer Models - Phase 4.

Handles job offers, negotiations, and offer lifecycle management.
"""

from datetime import datetime, timedelta
from enum import Enum
from typing import Dict, Optional, List
from sqlalchemy import Column, Integer, String, Text, DateTime, ForeignKey, Boolean, JSON, Enum as SQLEnum, Float
from sqlalchemy.orm import relationship

from ..database import Base


class OfferStatus(str, Enum):
    """Job offer status."""
    DRAFT = "draft"  # Being prepared, not sent yet
    PENDING = "pending"  # Sent to candidate, awaiting response
    UNDER_NEGOTIATION = "under_negotiation"  # Candidate is negotiating
    ACCEPTED = "accepted"  # Candidate accepted
    DECLINED = "declined"  # Candidate declined
    WITHDRAWN = "withdrawn"  # Company withdrew offer
    EXPIRED = "expired"  # Offer expired


class NegotiationType(str, Enum):
    """Type of negotiation."""
    SALARY = "salary"
    EQUITY = "equity"
    BENEFITS = "benefits"
    START_DATE = "start_date"
    REMOTE_WORK = "remote_work"
    RELOCATION = "relocation"
    SIGNING_BONUS = "signing_bonus"
    OTHER = "other"


class NegotiationStatus(str, Enum):
    """Negotiation status."""
    OPEN = "open"  # Candidate proposed change
    COMPANY_REVIEWING = "company_reviewing"  # Company is reviewing
    COUNTER_OFFERED = "counter_offered"  # Company made counter offer
    ACCEPTED = "accepted"  # Negotiation accepted
    REJECTED = "rejected"  # Negotiation rejected


class JobOffer(Base):
    """
    Job offer entity for hiring pipeline.

    Represents a formal job offer made to a candidate.
    """
    __tablename__ = "job_offers"
    __table_args__ = {'extend_existing': True}

    # Primary Key
    id = Column(Integer, primary_key=True, index=True)

    # Related Entities
    application_id = Column(Integer, ForeignKey("applications.id"), nullable=False, index=True)
    job_id = Column(Integer, ForeignKey("jobs.id"), nullable=False, index=True)
    company_id = Column(Integer, ForeignKey("companies.id"), nullable=False)
    candidate_user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    hiring_manager_id = Column(Integer, ForeignKey("users.id"), nullable=False)

    # Offer Details
    position_title = Column(String(255), nullable=False)
    department = Column(String(255), nullable=True)
    start_date = Column(DateTime, nullable=True)  # Proposed start date
    offer_letter_url = Column(String(500), nullable=True)  # Link to formal offer letter

    # Compensation
    base_salary = Column(Float, nullable=False)  # Annual base salary
    salary_currency = Column(String(10), default="USD")
    bonus_amount = Column(Float, nullable=True)  # Annual bonus target
    signing_bonus = Column(Float, nullable=True)  # One-time signing bonus
    equity_shares = Column(Integer, nullable=True)  # Number of shares/options
    equity_value = Column(Float, nullable=True)  # Estimated value
    equity_vesting_years = Column(Integer, nullable=True)  # Vesting period

    # Benefits & Perks
    benefits = Column(JSON, nullable=True)  # ["health", "dental", "401k", "pto"]
    pto_days = Column(Integer, nullable=True)  # Paid time off days
    remote_work_allowed = Column(Boolean, default=False)
    relocation_assistance = Column(Float, nullable=True)  # Relocation package amount

    # Other Terms
    employment_type = Column(String(50), nullable=False)  # full_time, part_time, contract
    probation_period_months = Column(Integer, nullable=True)
    special_conditions = Column(Text, nullable=True)  # Any special terms

    # Status & Timeline
    status = Column(SQLEnum(OfferStatus), default=OfferStatus.DRAFT, index=True, nullable=False)
    sent_at = Column(DateTime, nullable=True)
    expires_at = Column(DateTime, nullable=True)  # Offer expiration
    response_deadline = Column(DateTime, nullable=True)  # When candidate must respond

    # Candidate Response
    responded_at = Column(DateTime, nullable=True)
    accepted_at = Column(DateTime, nullable=True)
    declined_at = Column(DateTime, nullable=True)
    decline_reason = Column(Text, nullable=True)

    # Withdrawal
    withdrawn_at = Column(DateTime, nullable=True)
    withdrawn_by_user_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    withdrawal_reason = Column(Text, nullable=True)

    # Negotiation Tracking
    negotiation_rounds = Column(Integer, default=0)  # Number of negotiation rounds
    final_accepted_terms = Column(JSON, nullable=True)  # Final agreed terms

    # Metadata
    created_by_user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    notes = Column(Text, nullable=True)  # Internal notes

    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False, index=True)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    # Relationships
    application = relationship("Application", foreign_keys=[application_id])
    job = relationship("Job", foreign_keys=[job_id])
    company = relationship("CompanyLegacy", foreign_keys=[company_id])
    candidate = relationship("User", foreign_keys=[candidate_user_id])
    hiring_manager = relationship("User", foreign_keys=[hiring_manager_id])
    negotiations = relationship("OfferNegotiation", back_populates="offer", cascade="all, delete-orphan")

    def __repr__(self):
        return f"<JobOffer {self.id}: {self.position_title} - {self.status.value}>"

    # Helper Methods

    def send_offer(self, expires_in_days: int = 7):
        """Send offer to candidate."""
        self.status = OfferStatus.PENDING
        self.sent_at = datetime.utcnow()
        self.expires_at = datetime.utcnow() + timedelta(days=expires_in_days)
        self.response_deadline = self.expires_at

    def accept_offer(self):
        """Mark offer as accepted."""
        self.status = OfferStatus.ACCEPTED
        self.accepted_at = datetime.utcnow()
        self.responded_at = datetime.utcnow()

    def decline_offer(self, reason: Optional[str] = None):
        """Mark offer as declined."""
        self.status = OfferStatus.DECLINED
        self.declined_at = datetime.utcnow()
        self.responded_at = datetime.utcnow()
        self.decline_reason = reason

    def withdraw_offer(self, user_id: int, reason: Optional[str] = None):
        """Withdraw offer."""
        self.status = OfferStatus.WITHDRAWN
        self.withdrawn_at = datetime.utcnow()
        self.withdrawn_by_user_id = user_id
        self.withdrawal_reason = reason

    def start_negotiation(self):
        """Mark offer as under negotiation."""
        if self.status == OfferStatus.PENDING:
            self.status = OfferStatus.UNDER_NEGOTIATION
            self.negotiation_rounds += 1

    def is_expired(self) -> bool:
        """Check if offer has expired."""
        if not self.expires_at:
            return False
        return datetime.utcnow() > self.expires_at

    def is_pending_response(self) -> bool:
        """Check if offer is awaiting candidate response."""
        return self.status in [OfferStatus.PENDING, OfferStatus.UNDER_NEGOTIATION]

    def get_total_compensation(self) -> float:
        """Calculate total first-year compensation."""
        total = self.base_salary

        if self.bonus_amount:
            total += self.bonus_amount

        if self.signing_bonus:
            total += self.signing_bonus

        # Don't include equity in first year total (vesting)

        return total

    def to_dict(self) -> Dict:
        """Convert to dictionary."""
        return {
            "id": self.id,
            "application_id": self.application_id,
            "job_id": self.job_id,
            "company_id": self.company_id,
            "candidate_user_id": self.candidate_user_id,
            "position_title": self.position_title,
            "department": self.department,
            "start_date": self.start_date.isoformat() if self.start_date else None,
            "base_salary": float(self.base_salary),
            "salary_currency": self.salary_currency,
            "bonus_amount": float(self.bonus_amount) if self.bonus_amount else None,
            "signing_bonus": float(self.signing_bonus) if self.signing_bonus else None,
            "equity_shares": self.equity_shares,
            "equity_value": float(self.equity_value) if self.equity_value else None,
            "benefits": self.benefits,
            "pto_days": self.pto_days,
            "remote_work_allowed": self.remote_work_allowed,
            "relocation_assistance": float(self.relocation_assistance) if self.relocation_assistance else None,
            "employment_type": self.employment_type,
            "status": self.status.value,
            "sent_at": self.sent_at.isoformat() if self.sent_at else None,
            "expires_at": self.expires_at.isoformat() if self.expires_at else None,
            "response_deadline": self.response_deadline.isoformat() if self.response_deadline else None,
            "accepted_at": self.accepted_at.isoformat() if self.accepted_at else None,
            "declined_at": self.declined_at.isoformat() if self.declined_at else None,
            "negotiation_rounds": self.negotiation_rounds,
            "total_compensation": self.get_total_compensation(),
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
        }


class OfferNegotiation(Base):
    """
    Offer negotiation tracking.

    Records back-and-forth negotiations between candidate and company.
    """
    __tablename__ = "offer_negotiations"
    __table_args__ = {'extend_existing': True}

    # Primary Key
    id = Column(Integer, primary_key=True, index=True)

    # Related Entities
    offer_id = Column(Integer, ForeignKey("job_offers.id"), nullable=False, index=True)
    round_number = Column(Integer, nullable=False)  # Which negotiation round

    # Negotiation Details
    initiated_by_user_id = Column(Integer, ForeignKey("users.id"), nullable=False)  # Who made this proposal
    negotiation_type = Column(SQLEnum(NegotiationType), nullable=False)
    status = Column(SQLEnum(NegotiationStatus), default=NegotiationStatus.OPEN, nullable=False)

    # What was proposed
    original_value = Column(String(500), nullable=True)  # Original offer value
    proposed_value = Column(String(500), nullable=False)  # Candidate's proposal
    counter_value = Column(String(500), nullable=True)  # Company's counter offer
    final_value = Column(String(500), nullable=True)  # Agreed value (if accepted)

    # Messages/Justification
    candidate_message = Column(Text, nullable=True)  # Candidate's explanation
    company_message = Column(Text, nullable=True)  # Company's response

    # Resolution
    resolved_at = Column(DateTime, nullable=True)
    resolved_by_user_id = Column(Integer, ForeignKey("users.id"), nullable=True)

    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    # Relationships
    offer = relationship("JobOffer", back_populates="negotiations")
    initiated_by = relationship("User", foreign_keys=[initiated_by_user_id])
    resolved_by = relationship("User", foreign_keys=[resolved_by_user_id])

    def __repr__(self):
        return f"<OfferNegotiation {self.id}: {self.negotiation_type.value} - {self.status.value}>"

    # Helper Methods

    def counter_offer(self, counter_value: str, message: Optional[str] = None):
        """Company makes counter offer."""
        self.status = NegotiationStatus.COUNTER_OFFERED
        self.counter_value = counter_value
        self.company_message = message

    def accept_proposal(self, user_id: int):
        """Accept the proposed change."""
        self.status = NegotiationStatus.ACCEPTED
        self.resolved_at = datetime.utcnow()
        self.resolved_by_user_id = user_id
        self.final_value = self.proposed_value

    def reject_proposal(self, user_id: int, message: Optional[str] = None):
        """Reject the proposed change."""
        self.status = NegotiationStatus.REJECTED
        self.resolved_at = datetime.utcnow()
        self.resolved_by_user_id = user_id
        self.company_message = message

    def to_dict(self) -> Dict:
        """Convert to dictionary."""
        return {
            "id": self.id,
            "offer_id": self.offer_id,
            "round_number": self.round_number,
            "negotiation_type": self.negotiation_type.value,
            "status": self.status.value,
            "original_value": self.original_value,
            "proposed_value": self.proposed_value,
            "counter_value": self.counter_value,
            "final_value": self.final_value,
            "candidate_message": self.candidate_message,
            "company_message": self.company_message,
            "created_at": self.created_at.isoformat(),
            "resolved_at": self.resolved_at.isoformat() if self.resolved_at else None,
        }
