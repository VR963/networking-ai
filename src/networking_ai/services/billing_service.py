"""
Billing Service - Phase 6.

Handles Stripe integration, subscription management, and payment processing.
"""

from datetime import datetime, timedelta
from typing import Optional, List, Dict, Any
from sqlalchemy.orm import Session
import logging

from ..models.billing import (
    PaymentMethod,
    SubscriptionPlan,
    BillingSubscription,
    Invoice,
    Payment,
    UsageRecord,
    BillingEvent,
    BillingCycle,
    PaymentStatus,
    InvoiceStatus,
    SubscriptionPlanType
)
from ..models.user import User
from ..models.company import CompanyLegacy as Company

logger = logging.getLogger(__name__)


class BillingService:
    """
    Service for managing billing, subscriptions, and payments.

    Integrates with Stripe for payment processing.
    """

    def __init__(self, stripe_api_key: Optional[str] = None, notification_service=None):
        """Initialize billing service."""
        self.stripe_api_key = stripe_api_key
        self.notification_service = notification_service

        # Initialize Stripe if API key provided
        if stripe_api_key:
            try:
                import stripe
                stripe.api_key = stripe_api_key
                self.stripe = stripe
            except ImportError:
                logger.warning("Stripe library not installed. Payment processing will be disabled.")
                self.stripe = None
        else:
            self.stripe = None

    # ==================== Payment Methods ====================

    def create_payment_method(
        self,
        user_id: int,
        stripe_payment_method_id: str,
        company_id: Optional[int] = None,
        is_default: bool = False,
        db: Session = None
    ) -> PaymentMethod:
        """
        Add a payment method for a user/company.

        Args:
            user_id: User ID
            stripe_payment_method_id: Stripe payment method ID
            company_id: Optional company ID
            is_default: Set as default payment method
            db: Database session

        Returns:
            Created PaymentMethod
        """
        # Get payment method details from Stripe
        pm_details = {}
        if self.stripe:
            try:
                stripe_pm = self.stripe.PaymentMethod.retrieve(stripe_payment_method_id)
                pm_details = {
                    "payment_type": stripe_pm.type,
                    "card_brand": stripe_pm.card.brand if stripe_pm.type == "card" else None,
                    "card_last4": stripe_pm.card.last4 if stripe_pm.type == "card" else None,
                    "card_exp_month": stripe_pm.card.exp_month if stripe_pm.type == "card" else None,
                    "card_exp_year": stripe_pm.card.exp_year if stripe_pm.type == "card" else None,
                }
            except Exception as e:
                logger.error(f"Failed to retrieve Stripe payment method: {e}")

        # If setting as default, unset other defaults
        if is_default:
            existing_defaults = db.query(PaymentMethod).filter(
                PaymentMethod.user_id == user_id,
                PaymentMethod.is_default == True
            ).all()
            for pm in existing_defaults:
                pm.is_default = False

        # Create payment method
        payment_method = PaymentMethod(
            user_id=user_id,
            company_id=company_id,
            stripe_payment_method_id=stripe_payment_method_id,
            is_default=is_default,
            **pm_details
        )

        db.add(payment_method)
        db.commit()
        db.refresh(payment_method)

        logger.info(f"Created payment method {payment_method.id} for user {user_id}")
        return payment_method

    def get_payment_methods(
        self,
        user_id: int,
        company_id: Optional[int] = None,
        active_only: bool = True,
        db: Session = None
    ) -> List[PaymentMethod]:
        """
        Get payment methods for a user/company.

        Args:
            user_id: User ID
            company_id: Optional company ID
            active_only: Only return active payment methods
            db: Database session

        Returns:
            List of PaymentMethod objects
        """
        query = db.query(PaymentMethod).filter(PaymentMethod.user_id == user_id)

        if company_id:
            query = query.filter(PaymentMethod.company_id == company_id)

        if active_only:
            query = query.filter(PaymentMethod.is_active == True)

        return query.order_by(PaymentMethod.is_default.desc(), PaymentMethod.created_at.desc()).all()

    def delete_payment_method(
        self,
        payment_method_id: int,
        user_id: int,
        db: Session = None
    ) -> bool:
        """
        Delete a payment method.

        Args:
            payment_method_id: Payment method ID
            user_id: User ID (for authorization)
            db: Database session

        Returns:
            True if deleted successfully
        """
        payment_method = db.query(PaymentMethod).filter(
            PaymentMethod.id == payment_method_id,
            PaymentMethod.user_id == user_id
        ).first()

        if not payment_method:
            raise ValueError("Payment method not found")

        # Soft delete
        payment_method.is_active = False
        payment_method.deleted_at = datetime.utcnow()
        db.commit()

        # Also delete from Stripe
        if self.stripe and payment_method.stripe_payment_method_id:
            try:
                self.stripe.PaymentMethod.detach(payment_method.stripe_payment_method_id)
            except Exception as e:
                logger.error(f"Failed to detach Stripe payment method: {e}")

        logger.info(f"Deleted payment method {payment_method_id} for user {user_id}")
        return True

    # ==================== Subscription Plans ====================

    def create_subscription_plan(
        self,
        name: str,
        plan_type: SubscriptionPlanType,
        price_monthly: float,
        price_quarterly: float = None,
        price_annually: float = None,
        max_jobs_posted: int = 0,
        max_applications: int = 0,
        features: Dict[str, Any] = None,
        db: Session = None
    ) -> SubscriptionPlan:
        """
        Create a subscription plan.

        Args:
            name: Plan name
            plan_type: Plan type
            price_monthly: Monthly price
            price_quarterly: Quarterly price
            price_annually: Annual price
            max_jobs_posted: Max jobs that can be posted
            max_applications: Max applications
            features: Feature flags dictionary
            db: Database session

        Returns:
            Created SubscriptionPlan
        """
        plan = SubscriptionPlan(
            name=name,
            plan_type=plan_type,
            price_monthly=price_monthly,
            price_quarterly=price_quarterly or (price_monthly * 3 * 0.9),  # 10% discount
            price_annually=price_annually or (price_monthly * 12 * 0.8),  # 20% discount
            max_jobs_posted=max_jobs_posted,
            max_applications=max_applications,
            features=features or {}
        )

        db.add(plan)
        db.commit()
        db.refresh(plan)

        logger.info(f"Created subscription plan {plan.id}: {name}")
        return plan

    def get_subscription_plans(
        self,
        active_only: bool = True,
        public_only: bool = True,
        db: Session = None
    ) -> List[SubscriptionPlan]:
        """
        Get available subscription plans.

        Args:
            active_only: Only return active plans
            public_only: Only return public plans
            db: Database session

        Returns:
            List of SubscriptionPlan objects
        """
        query = db.query(SubscriptionPlan)

        if active_only:
            query = query.filter(SubscriptionPlan.is_active == True)

        if public_only:
            query = query.filter(SubscriptionPlan.is_public == True)

        return query.order_by(SubscriptionPlan.price_monthly).all()

    # ==================== Subscriptions ====================

    def create_subscription(
        self,
        user_id: int,
        plan_id: int,
        billing_cycle: BillingCycle = BillingCycle.MONTHLY,
        payment_method_id: Optional[int] = None,
        company_id: Optional[int] = None,
        trial_days: int = 0,
        db: Session = None
    ) -> BillingSubscription:
        """
        Create a new subscription.

        Args:
            user_id: User ID
            plan_id: Subscription plan ID
            billing_cycle: Billing cycle
            payment_method_id: Payment method ID
            company_id: Optional company ID
            trial_days: Number of trial days
            db: Database session

        Returns:
            Created BillingSubscription
        """
        # Get plan
        plan = db.query(SubscriptionPlan).filter(SubscriptionPlan.id == plan_id).first()
        if not plan:
            raise ValueError("Subscription plan not found")

        # Calculate price based on billing cycle
        if billing_cycle == BillingCycle.MONTHLY:
            price = plan.price_monthly
        elif billing_cycle == BillingCycle.QUARTERLY:
            price = plan.price_quarterly
        else:
            price = plan.price_annually

        # Calculate billing periods
        now = datetime.utcnow()
        trial_start = now if trial_days > 0 else None
        trial_end = now + timedelta(days=trial_days) if trial_days > 0 else None
        current_period_start = trial_end or now

        if billing_cycle == BillingCycle.MONTHLY:
            current_period_end = current_period_start + timedelta(days=30)
        elif billing_cycle == BillingCycle.QUARTERLY:
            current_period_end = current_period_start + timedelta(days=90)
        else:
            current_period_end = current_period_start + timedelta(days=365)

        # Create subscription
        subscription = BillingSubscription(
            user_id=user_id,
            company_id=company_id,
            plan_id=plan_id,
            payment_method_id=payment_method_id,
            billing_cycle=billing_cycle,
            status="active",
            current_price=price,
            trial_start_date=trial_start,
            trial_end_date=trial_end,
            current_period_start=current_period_start,
            current_period_end=current_period_end
        )

        db.add(subscription)
        db.commit()
        db.refresh(subscription)

        # Create Stripe subscription if configured
        if self.stripe and payment_method_id:
            try:
                payment_method = db.query(PaymentMethod).get(payment_method_id)
                if payment_method and payment_method.stripe_payment_method_id:
                    stripe_subscription = self._create_stripe_subscription(
                        subscription, payment_method, plan, trial_days
                    )
                    subscription.stripe_subscription_id = stripe_subscription.id
                    db.commit()
            except Exception as e:
                logger.error(f"Failed to create Stripe subscription: {e}")

        # Log event
        self._log_billing_event(
            event_type="subscription_created",
            user_id=user_id,
            company_id=company_id,
            subscription_id=subscription.id,
            db=db
        )

        # Send notification
        if self.notification_service:
            self.notification_service.send_subscription_created(subscription, db=db)

        logger.info(f"Created subscription {subscription.id} for user {user_id}")
        return subscription

    def cancel_subscription(
        self,
        subscription_id: int,
        user_id: int,
        immediate: bool = False,
        reason: Optional[str] = None,
        db: Session = None
    ) -> BillingSubscription:
        """
        Cancel a subscription.

        Args:
            subscription_id: Subscription ID
            user_id: User ID (for authorization)
            immediate: Cancel immediately vs at period end
            reason: Cancellation reason
            db: Database session

        Returns:
            Updated BillingSubscription
        """
        subscription = db.query(BillingSubscription).filter(
            BillingSubscription.id == subscription_id,
            BillingSubscription.user_id == user_id
        ).first()

        if not subscription:
            raise ValueError("Subscription not found")

        if immediate:
            subscription.status = "canceled"
            subscription.ended_at = datetime.utcnow()
        else:
            subscription.cancel_at = subscription.current_period_end

        subscription.canceled_at = datetime.utcnow()

        db.commit()
        db.refresh(subscription)

        # Cancel Stripe subscription
        if self.stripe and subscription.stripe_subscription_id:
            try:
                self.stripe.Subscription.modify(
                    subscription.stripe_subscription_id,
                    cancel_at_period_end=not immediate
                )
            except Exception as e:
                logger.error(f"Failed to cancel Stripe subscription: {e}")

        # Log event
        self._log_billing_event(
            event_type="subscription_canceled",
            user_id=user_id,
            subscription_id=subscription_id,
            event_data={"reason": reason, "immediate": immediate},
            db=db
        )

        logger.info(f"Canceled subscription {subscription_id}")
        return subscription

    def get_active_subscription(
        self,
        user_id: int,
        company_id: Optional[int] = None,
        db: Session = None
    ) -> Optional[BillingSubscription]:
        """
        Get active subscription for a user/company.

        Args:
            user_id: User ID
            company_id: Optional company ID
            db: Database session

        Returns:
            Active BillingSubscription or None
        """
        query = db.query(BillingSubscription).filter(
            BillingSubscription.user_id == user_id,
            BillingSubscription.status == "active"
        )

        if company_id:
            query = query.filter(BillingSubscription.company_id == company_id)

        return query.order_by(BillingSubscription.created_at.desc()).first()

    # ==================== Invoices ====================

    def create_invoice(
        self,
        user_id: int,
        subscription_id: int,
        amount: int,  # in cents
        due_date: datetime,
        line_items: List[Dict[str, Any]] = None,
        company_id: Optional[int] = None,
        db: Session = None
    ) -> Invoice:
        """
        Create an invoice.

        Args:
            user_id: User ID
            subscription_id: Subscription ID
            amount: Total amount in cents
            due_date: Due date
            line_items: List of line items
            company_id: Optional company ID
            db: Database session

        Returns:
            Created Invoice
        """
        # Generate invoice number
        invoice_count = db.query(Invoice).count()
        invoice_number = f"INV-{datetime.utcnow().year}-{invoice_count + 1:06d}"

        invoice = Invoice(
            subscription_id=subscription_id,
            user_id=user_id,
            company_id=company_id,
            invoice_number=invoice_number,
            status=InvoiceStatus.OPEN,
            subtotal=amount,
            total_amount=amount,
            amount_due=amount,
            due_date=due_date,
            line_items=line_items or []
        )

        db.add(invoice)
        db.commit()
        db.refresh(invoice)

        logger.info(f"Created invoice {invoice.id}: {invoice_number}")
        return invoice

    def get_invoices(
        self,
        user_id: int,
        company_id: Optional[int] = None,
        status: Optional[InvoiceStatus] = None,
        db: Session = None
    ) -> List[Invoice]:
        """
        Get invoices for a user/company.

        Args:
            user_id: User ID
            company_id: Optional company ID
            status: Filter by invoice status
            db: Database session

        Returns:
            List of Invoice objects
        """
        query = db.query(Invoice).filter(Invoice.user_id == user_id)

        if company_id:
            query = query.filter(Invoice.company_id == company_id)

        if status:
            query = query.filter(Invoice.status == status)

        return query.order_by(Invoice.invoice_date.desc()).all()

    # ==================== Payments ====================

    def process_payment(
        self,
        user_id: int,
        amount: int,  # in cents
        payment_method_id: int,
        invoice_id: Optional[int] = None,
        subscription_id: Optional[int] = None,
        description: Optional[str] = None,
        db: Session = None
    ) -> Payment:
        """
        Process a payment.

        Args:
            user_id: User ID
            amount: Amount in cents
            payment_method_id: Payment method ID
            invoice_id: Optional invoice ID
            subscription_id: Optional subscription ID
            description: Payment description
            db: Database session

        Returns:
            Created Payment
        """
        payment_method = db.query(PaymentMethod).get(payment_method_id)
        if not payment_method:
            raise ValueError("Payment method not found")

        # Create payment record
        payment = Payment(
            user_id=user_id,
            payment_method_id=payment_method_id,
            invoice_id=invoice_id,
            subscription_id=subscription_id,
            amount=amount,
            status=PaymentStatus.PROCESSING,
            description=description,
            payment_type=payment_method.payment_type,
            card_brand=payment_method.card_brand,
            card_last4=payment_method.card_last4
        )

        db.add(payment)
        db.commit()
        db.refresh(payment)

        # Process with Stripe
        if self.stripe and payment_method.stripe_payment_method_id:
            try:
                intent = self.stripe.PaymentIntent.create(
                    amount=amount,
                    currency="usd",
                    payment_method=payment_method.stripe_payment_method_id,
                    confirm=True,
                    description=description
                )

                payment.stripe_payment_intent_id = intent.id
                payment.status = PaymentStatus.COMPLETED
                payment.completed_at = datetime.utcnow()
                payment.receipt_url = intent.charges.data[0].receipt_url if intent.charges.data else None

                # Update invoice if provided
                if invoice_id:
                    invoice = db.query(Invoice).get(invoice_id)
                    if invoice:
                        invoice.amount_paid += amount
                        invoice.amount_due = max(0, invoice.total_amount - invoice.amount_paid)
                        if invoice.amount_due == 0:
                            invoice.status = InvoiceStatus.PAID
                            invoice.paid_at = datetime.utcnow()

                db.commit()
                logger.info(f"Payment {payment.id} completed successfully")

            except Exception as e:
                payment.status = PaymentStatus.FAILED
                payment.failure_message = str(e)
                db.commit()
                logger.error(f"Payment {payment.id} failed: {e}")
                raise ValueError(f"Payment processing failed: {e}")

        return payment

    # ==================== Usage Tracking ====================

    def record_usage(
        self,
        subscription_id: int,
        user_id: int,
        usage_type: str,
        quantity: int = 1,
        resource_id: Optional[int] = None,
        resource_type: Optional[str] = None,
        metadata: Dict[str, Any] = None,
        db: Session = None
    ):
        """
        Record usage for metered billing.

        Args:
            subscription_id: Subscription ID
            user_id: User ID
            usage_type: Type of usage (api_call, ai_match, etc.)
            quantity: Quantity used
            resource_id: Optional resource ID
            resource_type: Optional resource type
            metadata: Additional metadata
            db: Database session
        """
        usage = UsageRecord(
            subscription_id=subscription_id,
            user_id=user_id,
            usage_type=usage_type,
            quantity=quantity,
            resource_id=resource_id,
            resource_type=resource_type,
            metadata=metadata or {}
        )

        db.add(usage)

        # Update subscription usage counters
        subscription = db.query(BillingSubscription).get(subscription_id)
        if subscription:
            if usage_type == "job_posted":
                subscription.jobs_posted_this_period += quantity
            elif usage_type == "application":
                subscription.applications_this_period += quantity
            elif usage_type == "ai_match":
                subscription.ai_matches_this_period += quantity
            elif usage_type == "interview":
                subscription.interviews_this_period += quantity

        db.commit()

    # ==================== Helper Methods ====================

    def _create_stripe_subscription(
        self,
        subscription: BillingSubscription,
        payment_method: PaymentMethod,
        plan: SubscriptionPlan,
        trial_days: int
    ):
        """Create Stripe subscription."""
        # This would integrate with actual Stripe API
        # Implementation depends on Stripe price IDs configured in plan
        pass

    def _log_billing_event(
        self,
        event_type: str,
        user_id: Optional[int] = None,
        company_id: Optional[int] = None,
        subscription_id: Optional[int] = None,
        event_data: Dict[str, Any] = None,
        db: Session = None
    ):
        """Log a billing event."""
        event = BillingEvent(
            event_type=event_type,
            user_id=user_id,
            company_id=company_id,
            subscription_id=subscription_id,
            event_data=event_data or {},
            event_source="system"
        )

        db.add(event)
        db.commit()


def create_billing_service(
    stripe_api_key: Optional[str] = None,
    notification_service=None
) -> BillingService:
    """
    Factory function to create BillingService.

    Args:
        stripe_api_key: Optional Stripe API key
        notification_service: Optional notification service

    Returns:
        BillingService instance
    """
    return BillingService(
        stripe_api_key=stripe_api_key,
        notification_service=notification_service
    )
