"""
Subscription Model.

Tracks payments and data retention for all user types.
Critical rule: No payment = No data access (like iCloud).
"""

from datetime import datetime, timedelta
from sqlalchemy import Column, Integer, String, Float, DateTime, Boolean, ForeignKey, Enum as SQLEnum
from sqlalchemy.orm import relationship
from enum import Enum

from ..database import Base


class SubscriptionType(str, Enum):
    """Type of subscription."""
    TALENT_FREE = "talent_free"              # Free trial (12 months)
    TALENT_PAID = "talent_paid"              # Paid talent (keep data)
    HIRING_MANAGER = "hiring_manager"        # Individual HM
    RECRUITER = "recruiter"                  # Recruiter
    COMPANY_ADMIN = "company_admin"          # Company Admin Agent
    COMPANY_SEATS = "company_seats"          # Bulk seat purchase


class SubscriptionStatus(str, Enum):
    """Subscription status."""
    TRIAL = "trial"              # Free trial period
    ACTIVE = "active"            # Paid and active
    EXPIRED = "expired"          # Expired - lose data access
    CANCELLED = "cancelled"      # User cancelled
    SUSPENDED = "suspended"      # Payment failed


class Subscription(Base):
    """
    Subscription model.

    Manages payments and data retention.

    Rules:
    - Talent: Free for 12 months, then pay or lose data
    - Hiring Manager: Pay or lose access
    - Company: Pay or lose all company knowledge
    - Recruiter: Pay or lose access

    Like iCloud: Stop paying = Lose access
    """
    __tablename__ = "subscriptions"
    __table_args__ = {'extend_existing': True}

    # Primary key
    id = Column(Integer, primary_key=True, index=True)

    # Ownership (one of these is set)
    user_id = Column(Integer, ForeignKey("users.id"), index=True)  # For individual subscriptions
    company_id = Column(Integer, ForeignKey("companies.id"), index=True)  # For company subscriptions

    # Subscription details
    subscription_type = Column(SQLEnum(SubscriptionType), nullable=False)
    status = Column(SQLEnum(SubscriptionStatus), default=SubscriptionStatus.TRIAL, nullable=False)

    # Pricing
    price_per_month = Column(Float)  # USD
    billing_cycle = Column(String(50))  # monthly, annual
    seats_included = Column(Integer, default=1)  # For bulk purchases

    # Seat allocation (for company subscriptions)
    hiring_manager_seats = Column(Integer, default=0)
    talent_seats = Column(Integer, default=0)

    # Payment
    payment_method = Column(String(100))  # stripe, paypal, etc.
    payment_id = Column(String(255))  # External payment system ID
    last_payment_at = Column(DateTime)
    next_payment_due = Column(DateTime)

    # Trial and expiration
    trial_started_at = Column(DateTime)
    trial_ends_at = Column(DateTime)
    started_at = Column(DateTime, default=datetime.utcnow)
    expires_at = Column(DateTime)

    # Data retention
    data_retention_expires_at = Column(DateTime)
    """
    Critical: When subscription expires, user has grace period.
    After data_retention_expires_at, all data is deleted.
    """

    # Cancellation
    cancelled_at = Column(DateTime)
    cancellation_reason = Column(String(500))

    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    user = relationship("User")
    company = relationship("CompanyLegacy")

    def __repr__(self):
        return f"<Subscription(id={self.id}, type={self.subscription_type}, status={self.status})>"

    def is_active(self) -> bool:
        """Check if subscription is currently active."""
        if self.status not in [SubscriptionStatus.TRIAL, SubscriptionStatus.ACTIVE]:
            return False

        if self.status == SubscriptionStatus.TRIAL:
            return datetime.utcnow() < self.trial_ends_at

        if self.expires_at:
            return datetime.utcnow() < self.expires_at

        return True

    def has_data_access(self) -> bool:
        """
        Check if user has access to their data.

        Critical rule: No payment = No data (like iCloud)
        """
        if self.is_active():
            return True

        # Grace period: Expired but within data retention period
        if self.data_retention_expires_at:
            return datetime.utcnow() < self.data_retention_expires_at

        return False

    def start_trial(self, duration_months: int = 12):
        """Start free trial (for Talent)."""
        self.status = SubscriptionStatus.TRIAL
        self.trial_started_at = datetime.utcnow()
        self.trial_ends_at = datetime.utcnow() + timedelta(days=duration_months * 30)

    def activate_paid_subscription(self):
        """Activate paid subscription."""
        self.status = SubscriptionStatus.ACTIVE
        self.started_at = datetime.utcnow()

        # Set expiration based on billing cycle
        if self.billing_cycle == "monthly":
            self.expires_at = datetime.utcnow() + timedelta(days=30)
            self.next_payment_due = self.expires_at
        elif self.billing_cycle == "annual":
            self.expires_at = datetime.utcnow() + timedelta(days=365)
            self.next_payment_due = self.expires_at

    def renew(self):
        """Renew subscription (payment received)."""
        self.status = SubscriptionStatus.ACTIVE
        self.last_payment_at = datetime.utcnow()

        # Extend expiration
        if self.billing_cycle == "monthly":
            self.expires_at = datetime.utcnow() + timedelta(days=30)
            self.next_payment_due = self.expires_at
        elif self.billing_cycle == "annual":
            self.expires_at = datetime.utcnow() + timedelta(days=365)
            self.next_payment_due = self.expires_at

        # Reset data retention (they paid, so data is safe)
        self.data_retention_expires_at = None

    def expire(self, grace_period_days: int = 30):
        """
        Expire subscription.

        Sets data retention grace period.
        After grace period, data is deleted.
        """
        self.status = SubscriptionStatus.EXPIRED
        self.data_retention_expires_at = datetime.utcnow() + timedelta(days=grace_period_days)

    def cancel(self, reason: str = None):
        """Cancel subscription (user requested)."""
        self.status = SubscriptionStatus.CANCELLED
        self.cancelled_at = datetime.utcnow()
        if reason:
            self.cancellation_reason = reason

        # Set data retention grace period
        self.data_retention_expires_at = datetime.utcnow() + timedelta(days=30)

    def suspend(self):
        """Suspend subscription (payment failed)."""
        self.status = SubscriptionStatus.SUSPENDED

    def get_status_summary(self) -> dict:
        """Get subscription status summary."""
        return {
            "type": self.subscription_type.value,
            "status": self.status.value,
            "is_active": self.is_active(),
            "has_data_access": self.has_data_access(),
            "expires_at": self.expires_at.isoformat() if self.expires_at else None,
            "data_retention_expires_at": self.data_retention_expires_at.isoformat() if self.data_retention_expires_at else None,
            "next_payment_due": self.next_payment_due.isoformat() if self.next_payment_due else None,
            "price_per_month": self.price_per_month
        }
