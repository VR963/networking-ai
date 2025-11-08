"""
Billing and Payment Models - Phase 6.

Stripe integration for subscription billing and payment processing.
"""

from datetime import datetime, timedelta
from enum import Enum
from typing import Optional, Dict, Any
from sqlalchemy import Column, Integer, String, Float, DateTime, ForeignKey, Boolean, Text, JSON, Enum as SQLEnum
from sqlalchemy.orm import relationship

from ..database import Base


class BillingCycle(str, Enum):
    """Billing cycle types."""
    MONTHLY = "monthly"
    QUARTERLY = "quarterly"
    ANNUALLY = "annually"


class PaymentStatus(str, Enum):
    """Payment status."""
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"
    REFUNDED = "refunded"
    CANCELED = "canceled"


class InvoiceStatus(str, Enum):
    """Invoice status."""
    DRAFT = "draft"
    OPEN = "open"
    PAID = "paid"
    VOID = "void"
    UNCOLLECTIBLE = "uncollectible"


class SubscriptionPlanType(str, Enum):
    """Subscription plan types."""
    FREE = "free"
    BASIC = "basic"
    PROFESSIONAL = "professional"
    ENTERPRISE = "enterprise"


class PaymentMethod(Base):
    """
    Payment method for billing.

    Stores Stripe payment method information for recurring charges.
    """
    __tablename__ = "payment_methods"

    # Primary Key
    id = Column(Integer, primary_key=True, index=True)

    # Foreign Keys
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    company_id = Column(Integer, ForeignKey("companies.id"), nullable=True, index=True)

    # Stripe Integration
    stripe_payment_method_id = Column(String(255), unique=True, index=True)
    stripe_customer_id = Column(String(255), index=True)

    # Payment Method Details
    payment_type = Column(String(50))  # card, bank_account, etc.
    card_brand = Column(String(50), nullable=True)  # visa, mastercard, amex, etc.
    card_last4 = Column(String(4), nullable=True)
    card_exp_month = Column(Integer, nullable=True)
    card_exp_year = Column(Integer, nullable=True)
    bank_name = Column(String(255), nullable=True)
    bank_last4 = Column(String(4), nullable=True)

    # Billing Address
    billing_name = Column(String(255), nullable=True)
    billing_email = Column(String(255), nullable=True)
    billing_address_line1 = Column(String(255), nullable=True)
    billing_address_line2 = Column(String(255), nullable=True)
    billing_city = Column(String(100), nullable=True)
    billing_state = Column(String(100), nullable=True)
    billing_postal_code = Column(String(20), nullable=True)
    billing_country = Column(String(2), nullable=True)  # ISO 3166-1 alpha-2

    # Status
    is_default = Column(Boolean, default=False)
    is_active = Column(Boolean, default=True)

    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow, index=True)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    deleted_at = Column(DateTime, nullable=True)

    # Relationships
    user = relationship("User", back_populates="payment_methods")
    company = relationship("Company", foreign_keys=[company_id])


class SubscriptionPlan(Base):
    """
    Subscription plan definition.

    Defines available subscription tiers and pricing.
    """
    __tablename__ = "subscription_plans"

    # Primary Key
    id = Column(Integer, primary_key=True, index=True)

    # Plan Details
    name = Column(String(100), nullable=False)
    plan_type = Column(SQLEnum(SubscriptionPlanType), nullable=False, index=True)
    description = Column(Text, nullable=True)

    # Pricing
    price_monthly = Column(Float, default=0.0)
    price_quarterly = Column(Float, default=0.0)
    price_annually = Column(Float, default=0.0)
    currency = Column(String(3), default="USD")

    # Stripe Integration
    stripe_price_id_monthly = Column(String(255), nullable=True)
    stripe_price_id_quarterly = Column(String(255), nullable=True)
    stripe_price_id_annually = Column(String(255), nullable=True)
    stripe_product_id = Column(String(255), nullable=True)

    # Features & Limits
    max_jobs_posted = Column(Integer, default=0)  # 0 = unlimited
    max_applications = Column(Integer, default=0)
    max_ai_matches_per_month = Column(Integer, default=0)
    max_interviews_per_month = Column(Integer, default=0)
    max_team_members = Column(Integer, default=1)

    # Feature Flags
    features = Column(JSON, default=dict)  # {"analytics": true, "api_access": true}

    # Status
    is_active = Column(Boolean, default=True)
    is_public = Column(Boolean, default=True)

    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    subscriptions = relationship("BillingSubscription", back_populates="plan")


class BillingSubscription(Base):
    """
    Active subscription for a company or user.

    Tracks current subscription status and billing cycle.
    """
    __tablename__ = "billing_subscriptions"

    # Primary Key
    id = Column(Integer, primary_key=True, index=True)

    # Foreign Keys
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    company_id = Column(Integer, ForeignKey("companies.id"), nullable=True, index=True)
    plan_id = Column(Integer, ForeignKey("subscription_plans.id"), nullable=False, index=True)
    payment_method_id = Column(Integer, ForeignKey("payment_methods.id"), nullable=True)

    # Stripe Integration
    stripe_subscription_id = Column(String(255), unique=True, index=True)
    stripe_customer_id = Column(String(255), index=True)

    # Subscription Details
    billing_cycle = Column(SQLEnum(BillingCycle), default=BillingCycle.MONTHLY)
    status = Column(String(50), default="active", index=True)  # active, canceled, past_due, etc.

    # Pricing
    current_price = Column(Float, nullable=False)
    currency = Column(String(3), default="USD")

    # Billing Dates
    trial_start_date = Column(DateTime, nullable=True)
    trial_end_date = Column(DateTime, nullable=True)
    current_period_start = Column(DateTime, nullable=False)
    current_period_end = Column(DateTime, nullable=False)
    cancel_at = Column(DateTime, nullable=True)
    canceled_at = Column(DateTime, nullable=True)
    ended_at = Column(DateTime, nullable=True)

    # Usage Tracking
    jobs_posted_this_period = Column(Integer, default=0)
    applications_this_period = Column(Integer, default=0)
    ai_matches_this_period = Column(Integer, default=0)
    interviews_this_period = Column(Integer, default=0)

    # Metadata
    metadata = Column(JSON, default=dict)

    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow, index=True)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    user = relationship("User", back_populates="billing_subscriptions")
    company = relationship("Company", foreign_keys=[company_id])
    plan = relationship("SubscriptionPlan", back_populates="subscriptions")
    payment_method = relationship("PaymentMethod")
    invoices = relationship("Invoice", back_populates="subscription")
    payments = relationship("Payment", back_populates="subscription")

    def is_trial(self) -> bool:
        """Check if subscription is in trial period."""
        if not self.trial_end_date:
            return False
        return datetime.utcnow() < self.trial_end_date

    def is_active(self) -> bool:
        """Check if subscription is currently active."""
        return self.status == "active" and datetime.utcnow() < self.current_period_end

    def days_until_renewal(self) -> int:
        """Calculate days until next renewal."""
        delta = self.current_period_end - datetime.utcnow()
        return max(0, delta.days)

    def reset_usage_tracking(self):
        """Reset usage counters for new billing period."""
        self.jobs_posted_this_period = 0
        self.applications_this_period = 0
        self.ai_matches_this_period = 0
        self.interviews_this_period = 0


class Invoice(Base):
    """
    Invoice for subscription or one-time charges.

    Tracks billing invoices sent to customers.
    """
    __tablename__ = "invoices"

    # Primary Key
    id = Column(Integer, primary_key=True, index=True)

    # Foreign Keys
    subscription_id = Column(Integer, ForeignKey("billing_subscriptions.id"), nullable=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    company_id = Column(Integer, ForeignKey("companies.id"), nullable=True, index=True)

    # Stripe Integration
    stripe_invoice_id = Column(String(255), unique=True, index=True)
    stripe_customer_id = Column(String(255), index=True)

    # Invoice Details
    invoice_number = Column(String(100), unique=True, index=True)
    status = Column(SQLEnum(InvoiceStatus), default=InvoiceStatus.DRAFT, index=True)

    # Amounts (in cents to avoid floating point issues)
    subtotal = Column(Integer, nullable=False)  # In cents
    tax_amount = Column(Integer, default=0)
    discount_amount = Column(Integer, default=0)
    total_amount = Column(Integer, nullable=False)
    amount_paid = Column(Integer, default=0)
    amount_due = Column(Integer, default=0)
    currency = Column(String(3), default="USD")

    # Line Items
    line_items = Column(JSON, default=list)  # List of invoice line items

    # Billing Period
    billing_period_start = Column(DateTime, nullable=True)
    billing_period_end = Column(DateTime, nullable=True)

    # Dates
    invoice_date = Column(DateTime, default=datetime.utcnow, index=True)
    due_date = Column(DateTime, nullable=False)
    paid_at = Column(DateTime, nullable=True)
    voided_at = Column(DateTime, nullable=True)

    # URLs
    invoice_pdf_url = Column(String(500), nullable=True)
    hosted_invoice_url = Column(String(500), nullable=True)

    # Notes
    description = Column(Text, nullable=True)
    notes = Column(Text, nullable=True)

    # Metadata
    metadata = Column(JSON, default=dict)

    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow, index=True)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    subscription = relationship("BillingSubscription", back_populates="invoices")
    user = relationship("User")
    company = relationship("Company", foreign_keys=[company_id])
    payments = relationship("Payment", back_populates="invoice")

    def to_dict(self) -> Dict[str, Any]:
        """Convert invoice to dictionary."""
        return {
            "id": self.id,
            "invoice_number": self.invoice_number,
            "status": self.status.value if self.status else None,
            "subtotal": self.subtotal / 100,  # Convert cents to dollars
            "tax_amount": self.tax_amount / 100,
            "total_amount": self.total_amount / 100,
            "amount_paid": self.amount_paid / 100,
            "amount_due": self.amount_due / 100,
            "currency": self.currency,
            "invoice_date": self.invoice_date.isoformat() if self.invoice_date else None,
            "due_date": self.due_date.isoformat() if self.due_date else None,
            "paid_at": self.paid_at.isoformat() if self.paid_at else None,
            "invoice_pdf_url": self.invoice_pdf_url,
            "hosted_invoice_url": self.hosted_invoice_url,
        }


class Payment(Base):
    """
    Payment transaction record.

    Tracks all payment attempts and completions.
    """
    __tablename__ = "payments"

    # Primary Key
    id = Column(Integer, primary_key=True, index=True)

    # Foreign Keys
    subscription_id = Column(Integer, ForeignKey("billing_subscriptions.id"), nullable=True, index=True)
    invoice_id = Column(Integer, ForeignKey("invoices.id"), nullable=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    company_id = Column(Integer, ForeignKey("companies.id"), nullable=True, index=True)
    payment_method_id = Column(Integer, ForeignKey("payment_methods.id"), nullable=True)

    # Stripe Integration
    stripe_payment_intent_id = Column(String(255), unique=True, index=True)
    stripe_charge_id = Column(String(255), unique=True, index=True)
    stripe_customer_id = Column(String(255), index=True)

    # Payment Details
    amount = Column(Integer, nullable=False)  # In cents
    currency = Column(String(3), default="USD")
    status = Column(SQLEnum(PaymentStatus), default=PaymentStatus.PENDING, index=True)

    # Payment Method Used
    payment_type = Column(String(50))  # card, bank_account, etc.
    card_brand = Column(String(50), nullable=True)
    card_last4 = Column(String(4), nullable=True)

    # Transaction Details
    description = Column(Text, nullable=True)
    receipt_url = Column(String(500), nullable=True)
    failure_code = Column(String(100), nullable=True)
    failure_message = Column(Text, nullable=True)

    # Refund Information
    refunded = Column(Boolean, default=False)
    refund_amount = Column(Integer, default=0)
    refunded_at = Column(DateTime, nullable=True)

    # Metadata
    metadata = Column(JSON, default=dict)

    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow, index=True)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    completed_at = Column(DateTime, nullable=True)

    # Relationships
    subscription = relationship("BillingSubscription", back_populates="payments")
    invoice = relationship("Invoice", back_populates="payments")
    user = relationship("User")
    company = relationship("Company", foreign_keys=[company_id])
    payment_method = relationship("PaymentMethod")

    def to_dict(self) -> Dict[str, Any]:
        """Convert payment to dictionary."""
        return {
            "id": self.id,
            "amount": self.amount / 100,  # Convert cents to dollars
            "currency": self.currency,
            "status": self.status.value if self.status else None,
            "payment_type": self.payment_type,
            "card_brand": self.card_brand,
            "card_last4": self.card_last4,
            "description": self.description,
            "receipt_url": self.receipt_url,
            "refunded": self.refunded,
            "refund_amount": self.refund_amount / 100 if self.refund_amount else 0,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
        }


class UsageRecord(Base):
    """
    Usage tracking for metered billing.

    Tracks API calls, AI matches, and other metered features.
    """
    __tablename__ = "usage_records"

    # Primary Key
    id = Column(Integer, primary_key=True, index=True)

    # Foreign Keys
    subscription_id = Column(Integer, ForeignKey("billing_subscriptions.id"), nullable=False, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    company_id = Column(Integer, ForeignKey("companies.id"), nullable=True, index=True)

    # Usage Details
    usage_type = Column(String(100), nullable=False, index=True)  # api_call, ai_match, interview, etc.
    quantity = Column(Integer, default=1)
    unit_price = Column(Integer, default=0)  # In cents
    total_amount = Column(Integer, default=0)  # In cents

    # Metadata
    resource_id = Column(Integer, nullable=True)  # ID of the resource (job_id, application_id, etc.)
    resource_type = Column(String(100), nullable=True)  # job, application, match, etc.
    metadata = Column(JSON, default=dict)

    # Timestamps
    timestamp = Column(DateTime, default=datetime.utcnow, index=True)
    recorded_at = Column(DateTime, default=datetime.utcnow)

    # Relationships
    subscription = relationship("BillingSubscription")
    user = relationship("User")
    company = relationship("Company", foreign_keys=[company_id])


class BillingEvent(Base):
    """
    Billing event log.

    Tracks all billing-related events for audit purposes.
    """
    __tablename__ = "billing_events"

    # Primary Key
    id = Column(Integer, primary_key=True, index=True)

    # Foreign Keys
    user_id = Column(Integer, ForeignKey("users.id"), nullable=True, index=True)
    company_id = Column(Integer, ForeignKey("companies.id"), nullable=True, index=True)
    subscription_id = Column(Integer, ForeignKey("billing_subscriptions.id"), nullable=True, index=True)

    # Event Details
    event_type = Column(String(100), nullable=False, index=True)  # subscription_created, payment_succeeded, etc.
    event_source = Column(String(50), default="system")  # system, stripe, manual

    # Stripe Integration
    stripe_event_id = Column(String(255), unique=True, index=True, nullable=True)

    # Event Data
    event_data = Column(JSON, default=dict)
    description = Column(Text, nullable=True)

    # Status
    processed = Column(Boolean, default=False)
    processed_at = Column(DateTime, nullable=True)

    # Timestamps
    event_timestamp = Column(DateTime, default=datetime.utcnow, index=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    # Relationships
    user = relationship("User")
    company = relationship("Company", foreign_keys=[company_id])
    subscription = relationship("BillingSubscription")
