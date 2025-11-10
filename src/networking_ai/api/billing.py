"""
Billing API Endpoints - Phase 6.

REST API for subscription management, payments, and invoices.
"""

from typing import List, Optional
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from pydantic import BaseModel, Field

from ..database import get_db
from ..models.billing import (
    PaymentMethod,
    SubscriptionPlan,
    BillingSubscription,
    Invoice,
    Payment,
    BillingCycle,
    PaymentStatus,
    InvoiceStatus,
    SubscriptionPlanType
)
from ..services.billing_service import (
    BillingService,
    create_billing_service
)


# ==================== Request/Response Models ====================

class PaymentMethodCreate(BaseModel):
    """Create payment method request."""
    stripe_payment_method_id: str
    company_id: Optional[int] = None
    is_default: bool = False


class PaymentMethodResponse(BaseModel):
    """Payment method response."""
    id: int
    payment_type: str
    card_brand: Optional[str] = None
    card_last4: Optional[str] = None
    card_exp_month: Optional[int] = None
    card_exp_year: Optional[int] = None
    is_default: bool
    is_active: bool
    created_at: datetime

    class Config:
        from_attributes = True


class SubscriptionPlanCreate(BaseModel):
    """Create subscription plan request."""
    name: str
    plan_type: SubscriptionPlanType
    description: Optional[str] = None
    price_monthly: float
    price_quarterly: Optional[float] = None
    price_annually: Optional[float] = None
    max_jobs_posted: int = 0
    max_applications: int = 0
    max_ai_matches_per_month: int = 0
    max_interviews_per_month: int = 0
    max_team_members: int = 1
    features: Optional[dict] = {}


class SubscriptionPlanResponse(BaseModel):
    """Subscription plan response."""
    id: int
    name: str
    plan_type: SubscriptionPlanType
    description: Optional[str] = None
    price_monthly: float
    price_quarterly: float
    price_annually: float
    max_jobs_posted: int
    max_applications: int
    max_ai_matches_per_month: int
    max_interviews_per_month: int
    features: dict
    is_active: bool
    created_at: datetime

    class Config:
        from_attributes = True


class SubscriptionCreate(BaseModel):
    """Create subscription request."""
    plan_id: int
    billing_cycle: BillingCycle = BillingCycle.MONTHLY
    payment_method_id: Optional[int] = None
    company_id: Optional[int] = None
    trial_days: int = 0


class SubscriptionResponse(BaseModel):
    """Subscription response."""
    id: int
    plan_id: int
    billing_cycle: BillingCycle
    status: str
    current_price: float
    currency: str
    current_period_start: datetime
    current_period_end: datetime
    trial_end_date: Optional[datetime] = None
    cancel_at: Optional[datetime] = None
    canceled_at: Optional[datetime] = None
    created_at: datetime

    class Config:
        from_attributes = True


class SubscriptionCancel(BaseModel):
    """Cancel subscription request."""
    immediate: bool = False
    reason: Optional[str] = None


class InvoiceResponse(BaseModel):
    """Invoice response."""
    id: int
    invoice_number: str
    status: InvoiceStatus
    subtotal: int
    tax_amount: int
    total_amount: int
    amount_paid: int
    amount_due: int
    currency: str
    invoice_date: datetime
    due_date: datetime
    paid_at: Optional[datetime] = None
    invoice_pdf_url: Optional[str] = None
    hosted_invoice_url: Optional[str] = None

    class Config:
        from_attributes = True


class PaymentCreate(BaseModel):
    """Create payment request."""
    amount: float  # in dollars
    payment_method_id: int
    invoice_id: Optional[int] = None
    description: Optional[str] = None


class PaymentResponse(BaseModel):
    """Payment response."""
    id: int
    amount: int
    currency: str
    status: PaymentStatus
    payment_type: str
    card_brand: Optional[str] = None
    card_last4: Optional[str] = None
    description: Optional[str] = None
    receipt_url: Optional[str] = None
    failure_message: Optional[str] = None
    refunded: bool
    created_at: datetime
    completed_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class UsageRecordCreate(BaseModel):
    """Create usage record request."""
    usage_type: str
    quantity: int = 1
    resource_id: Optional[int] = None
    resource_type: Optional[str] = None
    metadata: Optional[dict] = {}


# ==================== Router Setup ====================

router = APIRouter(prefix="/api/billing", tags=["billing"])


# ==================== Helper Functions ====================

def get_billing_service() -> BillingService:
    """Get billing service instance."""
    # In production, pass Stripe API key from config
    return create_billing_service()


# ==================== Payment Methods ====================

@router.post("/payment-methods", response_model=PaymentMethodResponse, status_code=status.HTTP_201_CREATED)
def create_payment_method(
    payment_method: PaymentMethodCreate,
    user_id: int,  # Should come from auth
    db: Session = Depends(get_db),
    service: BillingService = Depends(get_billing_service)
):
    """
    Add a payment method.

    Creates a new payment method for the user using Stripe.
    """
    try:
        created = service.create_payment_method(
            user_id=user_id,
            stripe_payment_method_id=payment_method.stripe_payment_method_id,
            company_id=payment_method.company_id,
            is_default=payment_method.is_default,
            db=db
        )
        return created
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )


@router.get("/payment-methods", response_model=List[PaymentMethodResponse])
def list_payment_methods(
    user_id: int,  # Should come from auth
    company_id: Optional[int] = None,
    db: Session = Depends(get_db),
    service: BillingService = Depends(get_billing_service)
):
    """
    List payment methods.

    Returns all payment methods for the user.
    """
    methods = service.get_payment_methods(
        user_id=user_id,
        company_id=company_id,
        db=db
    )
    return methods


@router.delete("/payment-methods/{payment_method_id}")
def delete_payment_method(
    payment_method_id: int,
    user_id: int,  # Should come from auth
    db: Session = Depends(get_db),
    service: BillingService = Depends(get_billing_service)
):
    """
    Delete a payment method.

    Removes the payment method from the user's account.
    """
    try:
        service.delete_payment_method(
            payment_method_id=payment_method_id,
            user_id=user_id,
            db=db
        )
        return {"message": "Payment method deleted successfully"}
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e)
        )


# ==================== Subscription Plans ====================

@router.post("/plans", response_model=SubscriptionPlanResponse, status_code=status.HTTP_201_CREATED)
def create_subscription_plan(
    plan: SubscriptionPlanCreate,
    admin_user_id: int,  # Should come from auth, must be admin
    db: Session = Depends(get_db),
    service: BillingService = Depends(get_billing_service)
):
    """
    Create a subscription plan (Admin only).

    Creates a new subscription plan with pricing and features.
    """
    created = service.create_subscription_plan(
        name=plan.name,
        plan_type=plan.plan_type,
        price_monthly=plan.price_monthly,
        price_quarterly=plan.price_quarterly,
        price_annually=plan.price_annually,
        max_jobs_posted=plan.max_jobs_posted,
        max_applications=plan.max_applications,
        features=plan.features,
        db=db
    )
    return created


@router.get("/plans", response_model=List[SubscriptionPlanResponse])
def list_subscription_plans(
    active_only: bool = True,
    db: Session = Depends(get_db),
    service: BillingService = Depends(get_billing_service)
):
    """
    List subscription plans.

    Returns all available subscription plans.
    """
    plans = service.get_subscription_plans(
        active_only=active_only,
        db=db
    )
    return plans


@router.get("/plans/{plan_id}", response_model=SubscriptionPlanResponse)
def get_subscription_plan(
    plan_id: int,
    db: Session = Depends(get_db)
):
    """
    Get subscription plan details.

    Returns details for a specific subscription plan.
    """
    plan = db.query(SubscriptionPlan).filter(SubscriptionPlan.id == plan_id).first()
    if not plan:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Subscription plan not found"
        )
    return plan


# ==================== Subscriptions ====================

@router.post("/subscriptions", response_model=SubscriptionResponse, status_code=status.HTTP_201_CREATED)
def create_subscription(
    subscription: SubscriptionCreate,
    user_id: int,  # Should come from auth
    db: Session = Depends(get_db),
    service: BillingService = Depends(get_billing_service)
):
    """
    Create a subscription.

    Subscribes the user to a plan and starts billing.
    """
    try:
        created = service.create_subscription(
            user_id=user_id,
            plan_id=subscription.plan_id,
            billing_cycle=subscription.billing_cycle,
            payment_method_id=subscription.payment_method_id,
            company_id=subscription.company_id,
            trial_days=subscription.trial_days,
            db=db
        )
        return created
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )


@router.get("/subscriptions/active", response_model=SubscriptionResponse)
def get_active_subscription(
    user_id: int,  # Should come from auth
    company_id: Optional[int] = None,
    db: Session = Depends(get_db),
    service: BillingService = Depends(get_billing_service)
):
    """
    Get active subscription.

    Returns the user's currently active subscription.
    """
    subscription = service.get_active_subscription(
        user_id=user_id,
        company_id=company_id,
        db=db
    )

    if not subscription:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No active subscription found"
        )

    return subscription


@router.get("/subscriptions/{subscription_id}", response_model=SubscriptionResponse)
def get_subscription(
    subscription_id: int,
    user_id: int,  # Should come from auth
    db: Session = Depends(get_db)
):
    """
    Get subscription details.

    Returns details for a specific subscription.
    """
    subscription = db.query(BillingSubscription).filter(
        BillingSubscription.id == subscription_id,
        BillingSubscription.user_id == user_id
    ).first()

    if not subscription:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Subscription not found"
        )

    return subscription


@router.post("/subscriptions/{subscription_id}/cancel", response_model=SubscriptionResponse)
def cancel_subscription(
    subscription_id: int,
    cancel_params: SubscriptionCancel,
    user_id: int,  # Should come from auth
    db: Session = Depends(get_db),
    service: BillingService = Depends(get_billing_service)
):
    """
    Cancel a subscription.

    Cancels the subscription either immediately or at period end.
    """
    try:
        subscription = service.cancel_subscription(
            subscription_id=subscription_id,
            user_id=user_id,
            immediate=cancel_params.immediate,
            reason=cancel_params.reason,
            db=db
        )
        return subscription
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e)
        )


# ==================== Invoices ====================

@router.get("/invoices", response_model=List[InvoiceResponse])
def list_invoices(
    user_id: int,  # Should come from auth
    company_id: Optional[int] = None,
    invoice_status: Optional[InvoiceStatus] = None,
    db: Session = Depends(get_db),
    service: BillingService = Depends(get_billing_service)
):
    """
    List invoices.

    Returns all invoices for the user.
    """
    invoices = service.get_invoices(
        user_id=user_id,
        company_id=company_id,
        status=invoice_status,
        db=db
    )
    return invoices


@router.get("/invoices/{invoice_id}", response_model=InvoiceResponse)
def get_invoice(
    invoice_id: int,
    user_id: int,  # Should come from auth
    db: Session = Depends(get_db)
):
    """
    Get invoice details.

    Returns details for a specific invoice.
    """
    invoice = db.query(Invoice).filter(
        Invoice.id == invoice_id,
        Invoice.user_id == user_id
    ).first()

    if not invoice:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Invoice not found"
        )

    return invoice


# ==================== Payments ====================

@router.post("/payments", response_model=PaymentResponse, status_code=status.HTTP_201_CREATED)
def process_payment(
    payment: PaymentCreate,
    user_id: int,  # Should come from auth
    subscription_id: Optional[int] = None,
    db: Session = Depends(get_db),
    service: BillingService = Depends(get_billing_service)
):
    """
    Process a payment.

    Creates and processes a payment for an invoice or subscription.
    """
    try:
        # Convert dollars to cents
        amount_cents = int(payment.amount * 100)

        processed = service.process_payment(
            user_id=user_id,
            amount=amount_cents,
            payment_method_id=payment.payment_method_id,
            invoice_id=payment.invoice_id,
            subscription_id=subscription_id,
            description=payment.description,
            db=db
        )
        return processed
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )


@router.get("/payments", response_model=List[PaymentResponse])
def list_payments(
    user_id: int,  # Should come from auth
    company_id: Optional[int] = None,
    db: Session = Depends(get_db)
):
    """
    List payments.

    Returns all payments for the user.
    """
    query = db.query(Payment).filter(Payment.user_id == user_id)

    if company_id:
        query = query.filter(Payment.company_id == company_id)

    payments = query.order_by(Payment.created_at.desc()).all()
    return payments


@router.get("/payments/{payment_id}", response_model=PaymentResponse)
def get_payment(
    payment_id: int,
    user_id: int,  # Should come from auth
    db: Session = Depends(get_db)
):
    """
    Get payment details.

    Returns details for a specific payment.
    """
    payment = db.query(Payment).filter(
        Payment.id == payment_id,
        Payment.user_id == user_id
    ).first()

    if not payment:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Payment not found"
        )

    return payment


# ==================== Usage Tracking ====================

@router.post("/usage")
def record_usage(
    usage: UsageRecordCreate,
    user_id: int,  # Should come from auth
    subscription_id: int,
    db: Session = Depends(get_db),
    service: BillingService = Depends(get_billing_service)
):
    """
    Record usage (Internal endpoint).

    Records usage for metered billing features.
    """
    service.record_usage(
        subscription_id=subscription_id,
        user_id=user_id,
        usage_type=usage.usage_type,
        quantity=usage.quantity,
        resource_id=usage.resource_id,
        resource_type=usage.resource_type,
        metadata=usage.metadata,
        db=db
    )

    return {"message": "Usage recorded successfully"}


# ==================== Utility Endpoints ====================

@router.get("/subscription-status")
def check_subscription_status(
    user_id: int,  # Should come from auth
    company_id: Optional[int] = None,
    db: Session = Depends(get_db),
    service: BillingService = Depends(get_billing_service)
):
    """
    Check subscription status.

    Returns current subscription status and usage limits.
    """
    subscription = service.get_active_subscription(
        user_id=user_id,
        company_id=company_id,
        db=db
    )

    if not subscription:
        return {
            "has_active_subscription": False,
            "plan_type": "free",
            "status": "none"
        }

    # Get plan details
    plan = db.query(SubscriptionPlan).get(subscription.plan_id)

    return {
        "has_active_subscription": True,
        "subscription_id": subscription.id,
        "plan_type": plan.plan_type.value if plan else None,
        "plan_name": plan.name if plan else None,
        "status": subscription.status,
        "is_trial": subscription.is_trial(),
        "days_until_renewal": subscription.days_until_renewal(),
        "current_period_end": subscription.current_period_end,
        "usage": {
            "jobs_posted": subscription.jobs_posted_this_period,
            "applications": subscription.applications_this_period,
            "ai_matches": subscription.ai_matches_this_period,
            "interviews": subscription.interviews_this_period,
        },
        "limits": {
            "max_jobs_posted": plan.max_jobs_posted if plan else 0,
            "max_applications": plan.max_applications if plan else 0,
            "max_ai_matches_per_month": plan.max_ai_matches_per_month if plan else 0,
            "max_interviews_per_month": plan.max_interviews_per_month if plan else 0,
        }
    }
