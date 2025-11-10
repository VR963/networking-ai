"""
Job Offer API Endpoints - Phase 4.

REST API for managing job offers and negotiations.
"""

from typing import List, Optional
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from pydantic import BaseModel, Field

from ..database import get_db
from ..models.job_offer import (
    JobOffer,
    OfferNegotiation,
    OfferStatus,
    NegotiationType,
    NegotiationStatus
)
from ..services.offer_service import (
    OfferService,
    create_offer_service
)


# ==================== Request/Response Models ====================

class OfferCreate(BaseModel):
    """Create job offer request."""
    application_id: int
    job_id: int
    company_id: int
    candidate_user_id: int
    hiring_manager_id: int
    position_title: str
    base_salary: float
    salary_currency: str = "USD"
    employment_type: str = "full_time"
    bonus_amount: Optional[float] = None
    signing_bonus: Optional[float] = None
    equity_shares: Optional[int] = None
    equity_value: Optional[float] = None
    equity_vesting_years: Optional[int] = None
    department: Optional[str] = None
    start_date: Optional[datetime] = None
    benefits: Optional[List[str]] = None
    pto_days: Optional[int] = None
    remote_work_allowed: bool = False
    relocation_assistance: Optional[float] = None
    probation_period_months: Optional[int] = None
    special_conditions: Optional[str] = None
    notes: Optional[str] = None


class OfferSend(BaseModel):
    """Send offer request."""
    expires_in_days: int = 7
    offer_letter_url: Optional[str] = None


class OfferDecline(BaseModel):
    """Decline offer request."""
    reason: Optional[str] = None


class OfferWithdraw(BaseModel):
    """Withdraw offer request."""
    reason: Optional[str] = None


class OfferResponse(BaseModel):
    """Job offer response."""
    id: int
    application_id: int
    job_id: int
    company_id: int
    candidate_user_id: int
    position_title: str
    base_salary: float
    salary_currency: str
    bonus_amount: Optional[float] = None
    signing_bonus: Optional[float] = None
    equity_shares: Optional[int] = None
    employment_type: str
    status: OfferStatus
    sent_at: Optional[datetime] = None
    expires_at: Optional[datetime] = None
    response_deadline: Optional[datetime] = None
    accepted_at: Optional[datetime] = None
    declined_at: Optional[datetime] = None
    negotiation_rounds: int
    created_at: datetime

    class Config:
        from_attributes = True


class NegotiationCreate(BaseModel):
    """Create negotiation request."""
    negotiation_type: NegotiationType
    proposed_value: str
    original_value: Optional[str] = None
    message: Optional[str] = None


class NegotiationCounterOffer(BaseModel):
    """Counter offer request."""
    counter_value: str
    message: Optional[str] = None


class NegotiationReject(BaseModel):
    """Reject negotiation request."""
    message: Optional[str] = None


class NegotiationResponse(BaseModel):
    """Negotiation response."""
    id: int
    offer_id: int
    round_number: int
    negotiation_type: NegotiationType
    status: NegotiationStatus
    proposed_value: str
    counter_value: Optional[str] = None
    final_value: Optional[str] = None
    candidate_message: Optional[str] = None
    company_message: Optional[str] = None
    created_at: datetime
    resolved_at: Optional[datetime] = None

    class Config:
        from_attributes = True


# ==================== Router Setup ====================

router = APIRouter(prefix="/api/offers", tags=["offers"])


# ==================== Helper Functions ====================

def get_offer_service() -> OfferService:
    """Get offer service instance."""
    # In production, inject notification_service
    return create_offer_service()


# ==================== Offer CRUD ====================

@router.post("", response_model=OfferResponse, status_code=status.HTTP_201_CREATED)
def create_offer(
    offer: OfferCreate,
    created_by_user_id: int,  # Should come from auth
    db: Session = Depends(get_db),
    service: OfferService = Depends(get_offer_service)
):
    """
    Create a new job offer (draft status).

    Creates an offer in draft status. Use the send endpoint to send it to the candidate.
    """
    created = service.create_offer(
        application_id=offer.application_id,
        job_id=offer.job_id,
        company_id=offer.company_id,
        candidate_user_id=offer.candidate_user_id,
        hiring_manager_id=offer.hiring_manager_id,
        created_by_user_id=created_by_user_id,
        position_title=offer.position_title,
        base_salary=offer.base_salary,
        salary_currency=offer.salary_currency,
        employment_type=offer.employment_type,
        bonus_amount=offer.bonus_amount,
        signing_bonus=offer.signing_bonus,
        equity_shares=offer.equity_shares,
        equity_value=offer.equity_value,
        equity_vesting_years=offer.equity_vesting_years,
        department=offer.department,
        start_date=offer.start_date,
        benefits=offer.benefits,
        pto_days=offer.pto_days,
        remote_work_allowed=offer.remote_work_allowed,
        relocation_assistance=offer.relocation_assistance,
        probation_period_months=offer.probation_period_months,
        special_conditions=offer.special_conditions,
        notes=offer.notes,
        db=db
    )
    return created


@router.get("/{offer_id}", response_model=OfferResponse)
def get_offer(
    offer_id: int,
    db: Session = Depends(get_db),
    service: OfferService = Depends(get_offer_service)
):
    """Get offer by ID."""
    offer = service.get_offer(offer_id=offer_id, db=db)
    if not offer:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Offer not found"
        )
    return offer


@router.get("", response_model=List[OfferResponse])
def list_offers(
    candidate_user_id: Optional[int] = None,
    company_id: Optional[int] = None,
    application_id: Optional[int] = None,
    pending_only: bool = False,
    offer_status: Optional[OfferStatus] = None,
    db: Session = Depends(get_db),
    service: OfferService = Depends(get_offer_service)
):
    """
    List offers with filters.

    Can filter by candidate, company, application, or status.
    """
    if candidate_user_id:
        offers = service.get_offers_for_candidate(
            candidate_user_id=candidate_user_id,
            db=db,
            pending_only=pending_only
        )
    elif company_id:
        offers = service.get_offers_for_company(
            company_id=company_id,
            db=db,
            status=offer_status
        )
    elif application_id:
        offers = service.get_offers_for_application(
            application_id=application_id,
            db=db
        )
    else:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Must provide candidate_user_id, company_id, or application_id"
        )

    return offers


# ==================== Offer Actions ====================

@router.post("/{offer_id}/send", response_model=OfferResponse)
def send_offer(
    offer_id: int,
    send_params: OfferSend,
    db: Session = Depends(get_db),
    service: OfferService = Depends(get_offer_service)
):
    """
    Send offer to candidate.

    Changes status from DRAFT to PENDING and sends notification to candidate.
    Sets expiration date based on expires_in_days parameter.
    """
    try:
        offer = service.send_offer(
            offer_id=offer_id,
            expires_in_days=send_params.expires_in_days,
            offer_letter_url=send_params.offer_letter_url,
            db=db
        )
        return offer
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )


@router.post("/{offer_id}/accept", response_model=OfferResponse)
def accept_offer(
    offer_id: int,
    db: Session = Depends(get_db),
    service: OfferService = Depends(get_offer_service)
):
    """
    Candidate accepts the offer.

    Updates status to ACCEPTED and sends notification to hiring manager.
    """
    try:
        offer = service.accept_offer(offer_id=offer_id, db=db)
        return offer
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )


@router.post("/{offer_id}/decline", response_model=OfferResponse)
def decline_offer(
    offer_id: int,
    decline_params: OfferDecline,
    db: Session = Depends(get_db),
    service: OfferService = Depends(get_offer_service)
):
    """
    Candidate declines the offer.

    Updates status to DECLINED and sends notification to hiring manager.
    """
    try:
        offer = service.decline_offer(
            offer_id=offer_id,
            reason=decline_params.reason,
            db=db
        )
        return offer
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )


@router.post("/{offer_id}/withdraw", response_model=OfferResponse)
def withdraw_offer(
    offer_id: int,
    withdraw_params: OfferWithdraw,
    user_id: int,  # Should come from auth
    db: Session = Depends(get_db),
    service: OfferService = Depends(get_offer_service)
):
    """
    Company withdraws the offer.

    Updates status to WITHDRAWN and sends notification to candidate.
    """
    try:
        offer = service.withdraw_offer(
            offer_id=offer_id,
            user_id=user_id,
            reason=withdraw_params.reason,
            db=db
        )
        return offer
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )


# ==================== Negotiation Endpoints ====================

@router.post("/{offer_id}/negotiations", response_model=NegotiationResponse, status_code=status.HTTP_201_CREATED)
def start_negotiation(
    offer_id: int,
    negotiation: NegotiationCreate,
    initiated_by_user_id: int,  # Should come from auth
    db: Session = Depends(get_db),
    service: OfferService = Depends(get_offer_service)
):
    """
    Start a negotiation on an offer.

    Candidate proposes changes to the offer terms (salary, benefits, etc.).
    """
    try:
        created = service.start_negotiation(
            offer_id=offer_id,
            initiated_by_user_id=initiated_by_user_id,
            negotiation_type=negotiation.negotiation_type,
            proposed_value=negotiation.proposed_value,
            original_value=negotiation.original_value,
            message=negotiation.message,
            db=db
        )
        return created
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )


@router.get("/{offer_id}/negotiations", response_model=List[NegotiationResponse])
def get_negotiations(
    offer_id: int,
    db: Session = Depends(get_db),
    service: OfferService = Depends(get_offer_service)
):
    """
    Get all negotiations for an offer.

    Returns the negotiation history for the offer.
    """
    negotiations = service.get_negotiations_for_offer(offer_id=offer_id, db=db)
    return negotiations


@router.post("/negotiations/{negotiation_id}/counter", response_model=NegotiationResponse)
def counter_offer_negotiation(
    negotiation_id: int,
    counter: NegotiationCounterOffer,
    db: Session = Depends(get_db),
    service: OfferService = Depends(get_offer_service)
):
    """
    Company makes counter offer to negotiation.

    Responds to candidate's negotiation with a counter proposal.
    """
    try:
        negotiation = service.counter_offer_negotiation(
            negotiation_id=negotiation_id,
            counter_value=counter.counter_value,
            message=counter.message,
            db=db
        )
        return negotiation
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )


@router.post("/negotiations/{negotiation_id}/accept", response_model=NegotiationResponse)
def accept_negotiation(
    negotiation_id: int,
    user_id: int,  # Should come from auth
    db: Session = Depends(get_db),
    service: OfferService = Depends(get_offer_service)
):
    """
    Accept a negotiation proposal.

    Either party accepts the proposed changes.
    """
    try:
        negotiation = service.accept_negotiation(
            negotiation_id=negotiation_id,
            user_id=user_id,
            db=db
        )
        return negotiation
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )


@router.post("/negotiations/{negotiation_id}/reject", response_model=NegotiationResponse)
def reject_negotiation(
    negotiation_id: int,
    reject_params: NegotiationReject,
    user_id: int,  # Should come from auth
    db: Session = Depends(get_db),
    service: OfferService = Depends(get_offer_service)
):
    """
    Reject a negotiation proposal.

    Either party rejects the proposed changes.
    """
    try:
        negotiation = service.reject_negotiation(
            negotiation_id=negotiation_id,
            user_id=user_id,
            message=reject_params.message,
            db=db
        )
        return negotiation
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )


# ==================== Utility Endpoints ====================

@router.post("/check-expired")
def check_expired_offers(
    db: Session = Depends(get_db),
    service: OfferService = Depends(get_offer_service)
):
    """
    Check for expired offers (cron job endpoint).

    Updates status of offers that have passed their expiration date.
    Should be called by a scheduled task.
    """
    results = service.check_expired_offers(db=db)
    return {
        "message": "Expired offers checked",
        "expired_count": results["expired_offers"]
    }
