"""
Subscription Manager.

Manages subscriptions, payments, and data retention.
Implements "No payment = No data access" rule.
"""

from typing import Optional, Dict
from datetime import datetime, timedelta
from sqlalchemy.orm import Session

from ..models.subscription import (
    Subscription,
    SubscriptionType,
    SubscriptionStatus
)
from ..models.user import User
from ..models.company_v2 import Company


class SubscriptionManager:
    """
    Manages user and company subscriptions.

    Key Rules:
    - Talent: Free for 12 months, then pay or lose data access
    - Hiring Manager: Part of company subscription
    - Recruiter: Individual subscription
    - Company: Seat-based subscription
    - Universal: No payment = No data access (like iCloud)
    """

    # Subscription durations
    TALENT_FREE_TRIAL_MONTHS = 12
    DATA_RETENTION_GRACE_PERIOD_DAYS = 30

    def __init__(self):
        """Initialize Subscription Manager."""
        pass

    def create_talent_free_trial(
        self,
        user_id: int,
        db: Session
    ) -> Subscription:
        """
        Create free trial subscription for talent users.

        Args:
            user_id: User ID
            db: Database session

        Returns:
            Subscription instance
        """
        # Calculate expiration (12 months from now)
        expires_at = datetime.utcnow() + timedelta(days=self.TALENT_FREE_TRIAL_MONTHS * 30)
        data_retention_expires = expires_at + timedelta(days=self.DATA_RETENTION_GRACE_PERIOD_DAYS)

        subscription = Subscription(
            user_id=user_id,
            subscription_type=SubscriptionType.TALENT_FREE,
            status=SubscriptionStatus.TRIAL,
            starts_at=datetime.utcnow(),
            expires_at=expires_at,
            data_retention_expires_at=data_retention_expires,
            auto_renew=False
        )

        db.add(subscription)
        db.commit()
        db.refresh(subscription)

        print(f"[SUBSCRIPTION] Created free trial for user {user_id} (expires: {expires_at.date()})")
        return subscription

    def create_company_subscription(
        self,
        company_id: int,
        hiring_manager_seats: int,
        talent_seats: int,
        duration_months: int = 12,
        db: Session = None
    ) -> Subscription:
        """
        Create company subscription with seat allocation.

        Args:
            company_id: Company ID
            hiring_manager_seats: Number of HM seats
            talent_seats: Number of Talent seats
            duration_months: Subscription duration in months
            db: Database session

        Returns:
            Subscription instance
        """
        company = db.query(Company).filter(Company.id == company_id).first()
        if not company:
            raise ValueError(f"Company {company_id} not found")

        # Calculate expiration
        expires_at = datetime.utcnow() + timedelta(days=duration_months * 30)
        data_retention_expires = expires_at + timedelta(days=self.DATA_RETENTION_GRACE_PERIOD_DAYS)

        # Calculate monthly cost (example pricing)
        monthly_cost = (hiring_manager_seats * 49.99) + (talent_seats * 9.99)
        total_amount = monthly_cost * duration_months

        subscription = Subscription(
            company_id=company_id,
            subscription_type=SubscriptionType.COMPANY_SEATS,
            status=SubscriptionStatus.ACTIVE,
            starts_at=datetime.utcnow(),
            expires_at=expires_at,
            data_retention_expires_at=data_retention_expires,
            auto_renew=True,
            billing_amount=total_amount,
            billing_currency="USD",
            billing_interval="annually"
        )

        db.add(subscription)

        # Update company seat allocation
        company.hiring_manager_seats_allocated = hiring_manager_seats
        company.talent_seats_allocated = talent_seats
        company.subscription_expires_at = expires_at

        db.commit()
        db.refresh(subscription)

        print(f"[SUBSCRIPTION] Created company subscription: {hiring_manager_seats} HM seats + {talent_seats} Talent seats")
        return subscription

    def create_hiring_manager_subscription(
        self,
        user_id: int,
        company_id: int,
        db: Session
    ) -> Subscription:
        """
        Create hiring manager subscription (linked to company).

        Args:
            user_id: User ID
            company_id: Company ID
            db: Database session

        Returns:
            Subscription instance
        """
        company = db.query(Company).filter(Company.id == company_id).first()
        if not company:
            raise ValueError(f"Company {company_id} not found")

        # Check if company has available seats
        if not company.has_available_hiring_manager_seats():
            raise ValueError("No available hiring manager seats in company subscription")

        # Allocate seat
        company.allocate_hiring_manager_seat()

        # Create subscription (expires with company subscription)
        subscription = Subscription(
            user_id=user_id,
            company_id=company_id,
            subscription_type=SubscriptionType.HIRING_MANAGER,
            status=SubscriptionStatus.ACTIVE,
            starts_at=datetime.utcnow(),
            expires_at=company.subscription_expires_at,
            data_retention_expires_at=company.subscription_expires_at + timedelta(
                days=self.DATA_RETENTION_GRACE_PERIOD_DAYS
            ),
            auto_renew=False  # Managed by company subscription
        )

        db.add(subscription)
        db.commit()
        db.refresh(subscription)

        print(f"[SUBSCRIPTION] Created HM subscription for user {user_id} (company: {company.name})")
        return subscription

    def create_recruiter_subscription(
        self,
        user_id: int,
        duration_months: int = 12,
        db: Session = None
    ) -> Subscription:
        """
        Create recruiter subscription.

        Args:
            user_id: User ID
            duration_months: Subscription duration
            db: Database session

        Returns:
            Subscription instance
        """
        expires_at = datetime.utcnow() + timedelta(days=duration_months * 30)
        data_retention_expires = expires_at + timedelta(days=self.DATA_RETENTION_GRACE_PERIOD_DAYS)

        # Recruiter pricing (example)
        monthly_cost = 99.99
        total_amount = monthly_cost * duration_months

        subscription = Subscription(
            user_id=user_id,
            subscription_type=SubscriptionType.RECRUITER,
            status=SubscriptionStatus.ACTIVE,
            starts_at=datetime.utcnow(),
            expires_at=expires_at,
            data_retention_expires_at=data_retention_expires,
            auto_renew=True,
            billing_amount=total_amount,
            billing_currency="USD",
            billing_interval="annually"
        )

        db.add(subscription)
        db.commit()
        db.refresh(subscription)

        print(f"[SUBSCRIPTION] Created recruiter subscription for user {user_id}")
        return subscription

    def upgrade_talent_to_paid(
        self,
        user_id: int,
        duration_months: int = 12,
        db: Session = None
    ) -> Subscription:
        """
        Upgrade talent from free trial to paid subscription.

        Args:
            user_id: User ID
            duration_months: Subscription duration
            db: Database session

        Returns:
            Updated subscription instance
        """
        # Get existing subscription
        subscription = db.query(Subscription).filter(
            Subscription.user_id == user_id,
            Subscription.subscription_type == SubscriptionType.TALENT_FREE
        ).first()

        if not subscription:
            raise ValueError(f"No free trial subscription found for user {user_id}")

        # Update to paid
        expires_at = datetime.utcnow() + timedelta(days=duration_months * 30)
        monthly_cost = 9.99
        total_amount = monthly_cost * duration_months

        subscription.subscription_type = SubscriptionType.TALENT_PAID
        subscription.status = SubscriptionStatus.ACTIVE
        subscription.expires_at = expires_at
        subscription.data_retention_expires_at = expires_at + timedelta(
            days=self.DATA_RETENTION_GRACE_PERIOD_DAYS
        )
        subscription.auto_renew = True
        subscription.billing_amount = total_amount
        subscription.billing_currency = "USD"
        subscription.billing_interval = "annually"
        subscription.updated_at = datetime.utcnow()

        db.commit()
        db.refresh(subscription)

        print(f"[SUBSCRIPTION] Upgraded user {user_id} to paid Talent subscription")
        return subscription

    def check_data_access(
        self,
        user_id: int,
        db: Session
    ) -> Dict:
        """
        Check if user has data access.

        Universal rule: No payment = No data access (like iCloud)

        Args:
            user_id: User ID
            db: Database session

        Returns:
            Dictionary with access status and details
        """
        subscription = db.query(Subscription).filter(
            Subscription.user_id == user_id
        ).order_by(Subscription.created_at.desc()).first()

        if not subscription:
            return {
                "has_access": False,
                "reason": "No subscription found",
                "action_required": "Create subscription"
            }

        has_access = subscription.has_data_access()
        is_active = subscription.is_active()

        if has_access and is_active:
            return {
                "has_access": True,
                "subscription_type": subscription.subscription_type.value,
                "status": subscription.status.value,
                "expires_at": subscription.expires_at.isoformat() if subscription.expires_at else None
            }
        elif has_access and not is_active:
            # In grace period
            days_left = (subscription.data_retention_expires_at - datetime.utcnow()).days
            return {
                "has_access": True,
                "in_grace_period": True,
                "days_until_data_loss": days_left,
                "action_required": "Renew subscription to retain data",
                "expires_at": subscription.expires_at.isoformat() if subscription.expires_at else None
            }
        else:
            return {
                "has_access": False,
                "reason": "Subscription expired and grace period ended",
                "action_required": "Renew subscription (data may be lost)",
                "expired_at": subscription.expires_at.isoformat() if subscription.expires_at else None
            }

    def renew_subscription(
        self,
        subscription_id: int,
        duration_months: int = 12,
        db: Session = None
    ) -> Subscription:
        """
        Renew an expired subscription.

        Args:
            subscription_id: Subscription ID
            duration_months: Renewal duration
            db: Database session

        Returns:
            Updated subscription instance
        """
        subscription = db.query(Subscription).filter(
            Subscription.id == subscription_id
        ).first()

        if not subscription:
            raise ValueError(f"Subscription {subscription_id} not found")

        # Calculate new expiration
        new_expires_at = datetime.utcnow() + timedelta(days=duration_months * 30)

        # Update subscription
        subscription.status = SubscriptionStatus.ACTIVE
        subscription.expires_at = new_expires_at
        subscription.data_retention_expires_at = new_expires_at + timedelta(
            days=self.DATA_RETENTION_GRACE_PERIOD_DAYS
        )
        subscription.updated_at = datetime.utcnow()

        db.commit()
        db.refresh(subscription)

        print(f"[SUBSCRIPTION] Renewed subscription {subscription_id}")
        return subscription

    def cancel_subscription(
        self,
        subscription_id: int,
        db: Session
    ) -> Subscription:
        """
        Cancel a subscription.

        Data access continues until data_retention_expires_at.

        Args:
            subscription_id: Subscription ID
            db: Database session

        Returns:
            Updated subscription instance
        """
        subscription = db.query(Subscription).filter(
            Subscription.id == subscription_id
        ).first()

        if not subscription:
            raise ValueError(f"Subscription {subscription_id} not found")

        subscription.cancel()
        db.commit()
        db.refresh(subscription)

        print(f"[SUBSCRIPTION] Cancelled subscription {subscription_id}")
        return subscription

    def get_expiring_subscriptions(
        self,
        days_threshold: int = 30,
        db: Session = None
    ) -> list:
        """
        Get subscriptions expiring within threshold.

        Args:
            days_threshold: Number of days to look ahead
            db: Database session

        Returns:
            List of expiring subscriptions
        """
        threshold_date = datetime.utcnow() + timedelta(days=days_threshold)

        expiring = db.query(Subscription).filter(
            Subscription.status.in_([SubscriptionStatus.ACTIVE, SubscriptionStatus.TRIAL]),
            Subscription.expires_at <= threshold_date,
            Subscription.expires_at > datetime.utcnow()
        ).all()

        return expiring
