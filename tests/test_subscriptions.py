"""
Tests for Subscription Management.

Tests the "No payment = No data" rule, grace periods, and subscription lifecycle.
"""

import pytest
from datetime import datetime, timedelta
from sqlalchemy.orm import Session

from networking_ai.models.subscription import Subscription, SubscriptionType, SubscriptionStatus
from networking_ai.services.subscription_manager import SubscriptionManager

# Import fixtures
pytest_plugins = ["tests.conftest_phase2"]


class TestSubscriptionCreation:
    """Test subscription creation."""

    def test_create_talent_free_trial(self, client, talent_auth_headers):
        """Test creating talent free trial subscription."""
        response = client.post(
            "/api/companies/subscriptions",
            headers=talent_auth_headers,
            json={
                "subscription_type": "talent_free"
            }
        )

        assert response.status_code == 201
        data = response.json()

        assert data["subscription_type"] == "talent_free"
        assert data["status"] == "trial"
        assert data["auto_renew"] is False
        assert data["has_data_access"] is True

    def test_upgrade_talent_to_paid(self, client, talent_user, talent_auth_headers, db_session):
        """Test upgrading from free trial to paid subscription."""
        response = client.post(
            "/api/companies/subscriptions",
            headers=talent_auth_headers,
            json={
                "subscription_type": "talent_paid",
                "duration_months": 12
            }
        )

        assert response.status_code == 201
        data = response.json()

        assert data["subscription_type"] == "talent_paid"
        assert data["status"] == "active"
        assert data["auto_renew"] is True
        assert data["billing_amount"] is not None

    def test_create_recruiter_subscription(self, client, talent_auth_headers):
        """Test creating recruiter subscription."""
        response = client.post(
            "/api/companies/subscriptions",
            headers=talent_auth_headers,
            json={
                "subscription_type": "recruiter",
                "duration_months": 12
            }
        )

        assert response.status_code == 201
        data = response.json()

        assert data["subscription_type"] == "recruiter"
        assert data["status"] == "active"
        assert data["billing_amount"] > 0


class TestDataAccessRules:
    """Test the 'No payment = No data access' rule."""

    def test_active_subscription_has_data_access(self, db_session):
        """Test active subscription has data access."""
        subscription_manager = SubscriptionManager()

        # Create active subscription
        from networking_ai.models.user import User, UserRole
        from networking_ai.security import hash_password

        user = User(
            email="active@test.com",
            hashed_password=hash_password("pass123"),
            full_name="Active User",
            role=UserRole.JOB_SEEKER
        )
        db_session.add(user)
        db_session.commit()

        subscription = subscription_manager.create_talent_free_trial(
            user_id=user.id,
            db=db_session
        )

        # Check data access
        access_status = subscription_manager.check_data_access(
            user_id=user.id,
            db=db_session
        )

        assert access_status["has_access"] is True
        assert access_status["subscription_type"] == "talent_free"

    def test_expired_subscription_in_grace_period_has_access(self, grace_period_subscription, db_session):
        """Test expired subscription in grace period still has data access."""
        subscription_manager = SubscriptionManager()

        access_status = subscription_manager.check_data_access(
            user_id=grace_period_subscription.user_id,
            db=db_session
        )

        assert access_status["has_access"] is True
        assert access_status.get("in_grace_period") is True
        assert "days_until_data_loss" in access_status

    def test_expired_subscription_past_grace_period_no_access(self, expired_subscription, db_session):
        """Test NO PAYMENT = NO DATA: Expired subscription past grace period has no data access."""
        subscription_manager = SubscriptionManager()

        access_status = subscription_manager.check_data_access(
            user_id=expired_subscription.user_id,
            db=db_session
        )

        # THE UNIVERSAL RULE: No payment = No data (like iCloud)
        assert access_status["has_access"] is False
        assert "expired" in access_status["reason"].lower()

        print("\n🔒 UNIVERSAL RULE ENFORCED: No payment = No data access (like iCloud)!")

    def test_has_data_access_method(self, db_session):
        """Test Subscription.has_data_access() method."""
        from networking_ai.models.user import User, UserRole
        from networking_ai.security import hash_password

        user = User(
            email="datatest@test.com",
            hashed_password=hash_password("pass123"),
            full_name="Data Test",
            role=UserRole.JOB_SEEKER
        )
        db_session.add(user)
        db_session.commit()

        # Active subscription
        active_sub = Subscription(
            user_id=user.id,
            subscription_type=SubscriptionType.TALENT_FREE,
            status=SubscriptionStatus.ACTIVE,
            starts_at=datetime.utcnow(),
            expires_at=datetime.utcnow() + timedelta(days=30)
        )
        assert active_sub.has_data_access() is True

        # Expired but in grace period
        grace_sub = Subscription(
            user_id=user.id,
            subscription_type=SubscriptionType.TALENT_FREE,
            status=SubscriptionStatus.EXPIRED,
            starts_at=datetime.utcnow() - timedelta(days=400),
            expires_at=datetime.utcnow() - timedelta(days=5),
            data_retention_expires_at=datetime.utcnow() + timedelta(days=25)
        )
        assert grace_sub.has_data_access() is True

        # Fully expired
        expired_sub = Subscription(
            user_id=user.id,
            subscription_type=SubscriptionType.TALENT_FREE,
            status=SubscriptionStatus.EXPIRED,
            starts_at=datetime.utcnow() - timedelta(days=400),
            expires_at=datetime.utcnow() - timedelta(days=35),
            data_retention_expires_at=datetime.utcnow() - timedelta(days=5)
        )
        assert expired_sub.has_data_access() is False


class TestSubscriptionRetrieval:
    """Test subscription retrieval."""

    def test_get_my_subscription(self, client, talent_auth_headers):
        """Test getting current user's subscription."""
        response = client.get(
            "/api/companies/subscriptions/me",
            headers=talent_auth_headers
        )

        assert response.status_code == 200
        data = response.json()

        assert "subscription_type" in data
        assert "status" in data
        assert "has_data_access" in data
        assert "expires_at" in data


class TestSubscriptionCancellation:
    """Test subscription cancellation."""

    def test_cancel_subscription_success(self, client, talent_user, talent_auth_headers, db_session):
        """Test successful subscription cancellation."""
        # Get subscription ID
        subscription = db_session.query(Subscription).filter(
            Subscription.user_id == talent_user.id
        ).first()

        response = client.post(
            f"/api/companies/subscriptions/{subscription.id}/cancel",
            headers=talent_auth_headers
        )

        assert response.status_code == 200

        # Verify subscription cancelled
        db_session.refresh(subscription)
        assert subscription.status == SubscriptionStatus.CANCELLED
        assert subscription.auto_renew is False

    def test_cancel_subscription_wrong_user(self, client, hm_auth_headers, talent_user, db_session):
        """Test cancelling someone else's subscription fails."""
        subscription = db_session.query(Subscription).filter(
            Subscription.user_id == talent_user.id
        ).first()

        response = client.post(
            f"/api/companies/subscriptions/{subscription.id}/cancel",
            headers=hm_auth_headers  # Different user
        )

        assert response.status_code == 404  # Not found (filtered by user_id)


class TestSubscriptionManager:
    """Test SubscriptionManager service methods."""

    def test_create_talent_free_trial(self, db_session):
        """Test creating talent free trial."""
        from networking_ai.models.user import User, UserRole
        from networking_ai.security import hash_password

        user = User(
            email="trial@test.com",
            hashed_password=hash_password("pass123"),
            full_name="Trial User",
            role=UserRole.JOB_SEEKER
        )
        db_session.add(user)
        db_session.commit()

        subscription_manager = SubscriptionManager()
        subscription = subscription_manager.create_talent_free_trial(
            user_id=user.id,
            db=db_session
        )

        assert subscription.subscription_type == SubscriptionType.TALENT_FREE
        assert subscription.status == SubscriptionStatus.TRIAL
        assert subscription.auto_renew is False

        # Check duration (12 months)
        duration = (subscription.expires_at - subscription.starts_at).days
        assert 360 <= duration <= 370  # Approximately 12 months

    def test_create_company_subscription(self, db_session, test_company):
        """Test creating company subscription with seats."""
        subscription_manager = SubscriptionManager()

        subscription = subscription_manager.create_company_subscription(
            company_id=test_company.id,
            hiring_manager_seats=10,
            talent_seats=20,
            duration_months=12,
            db=db_session
        )

        assert subscription.subscription_type == SubscriptionType.COMPANY_SEATS
        assert subscription.company_id == test_company.id
        assert subscription.status == SubscriptionStatus.ACTIVE
        assert subscription.auto_renew is True
        assert subscription.billing_amount > 0

        # Verify seats allocated
        db_session.refresh(test_company)
        assert test_company.hiring_manager_seats_allocated == 10
        assert test_company.talent_seats_allocated == 20

    def test_renew_subscription(self, expired_subscription, db_session):
        """Test renewing expired subscription."""
        subscription_manager = SubscriptionManager()

        renewed = subscription_manager.renew_subscription(
            subscription_id=expired_subscription.id,
            duration_months=12,
            db=db_session
        )

        assert renewed.status == SubscriptionStatus.ACTIVE
        assert renewed.expires_at > datetime.utcnow()
        assert renewed.data_retention_expires_at > renewed.expires_at

    def test_get_expiring_subscriptions(self, db_session):
        """Test getting subscriptions expiring soon."""
        from networking_ai.models.user import User, UserRole
        from networking_ai.security import hash_password

        # Create user with expiring subscription
        user = User(
            email="expiring@test.com",
            hashed_password=hash_password("pass123"),
            full_name="Expiring User",
            role=UserRole.JOB_SEEKER
        )
        db_session.add(user)
        db_session.commit()

        # Expires in 15 days
        expiring_sub = Subscription(
            user_id=user.id,
            subscription_type=SubscriptionType.TALENT_PAID,
            status=SubscriptionStatus.ACTIVE,
            starts_at=datetime.utcnow() - timedelta(days=350),
            expires_at=datetime.utcnow() + timedelta(days=15)
        )
        db_session.add(expiring_sub)
        db_session.commit()

        subscription_manager = SubscriptionManager()
        expiring = subscription_manager.get_expiring_subscriptions(
            days_threshold=30,
            db=db_session
        )

        subscription_ids = [sub.id for sub in expiring]
        assert expiring_sub.id in subscription_ids


class TestGracePeriod:
    """Test grace period functionality."""

    def test_grace_period_duration(self):
        """Test grace period is 30 days after expiration."""
        subscription_manager = SubscriptionManager()
        assert subscription_manager.DATA_RETENTION_GRACE_PERIOD_DAYS == 30

    def test_subscription_in_grace_period_still_accessible(self, grace_period_subscription):
        """Test subscription in grace period still allows data access."""
        assert grace_period_subscription.status == SubscriptionStatus.EXPIRED
        assert grace_period_subscription.has_data_access() is True

        # But is marked as expired
        assert not grace_period_subscription.is_active()

    def test_subscription_past_grace_period_no_access(self, expired_subscription):
        """Test subscription past grace period has no data access."""
        assert expired_subscription.status == SubscriptionStatus.EXPIRED
        assert expired_subscription.has_data_access() is False

        print("\n⏰ GRACE PERIOD WORKING: 30-day grace period, then data locked!")


class TestSubscriptionLifecycle:
    """Test complete subscription lifecycle."""

    def test_complete_lifecycle(self, db_session):
        """
        Test complete subscription lifecycle:
        TRIAL → ACTIVE → EXPIRED (grace period) → EXPIRED (no access)
        """
        from networking_ai.models.user import User, UserRole
        from networking_ai.security import hash_password

        user = User(
            email="lifecycle@test.com",
            hashed_password=hash_password("pass123"),
            full_name="Lifecycle User",
            role=UserRole.JOB_SEEKER
        )
        db_session.add(user)
        db_session.commit()

        subscription_manager = SubscriptionManager()

        # 1. TRIAL (12-month free trial)
        subscription = subscription_manager.create_talent_free_trial(
            user_id=user.id,
            db=db_session
        )
        assert subscription.status == SubscriptionStatus.TRIAL
        assert subscription.has_data_access() is True

        # 2. UPGRADE TO PAID
        upgraded = subscription_manager.upgrade_talent_to_paid(
            user_id=user.id,
            duration_months=12,
            db=db_session
        )
        assert upgraded.status == SubscriptionStatus.ACTIVE
        assert upgraded.subscription_type == SubscriptionType.TALENT_PAID
        assert upgraded.has_data_access() is True

        # 3. EXPIRES (but still in grace period)
        upgraded.status = SubscriptionStatus.EXPIRED
        upgraded.expires_at = datetime.utcnow() - timedelta(days=5)
        upgraded.data_retention_expires_at = datetime.utcnow() + timedelta(days=25)
        db_session.commit()

        assert upgraded.has_data_access() is True  # Still in grace period

        # 4. PAST GRACE PERIOD (data locked)
        upgraded.data_retention_expires_at = datetime.utcnow() - timedelta(days=5)
        db_session.commit()

        assert upgraded.has_data_access() is False  # No payment = No data!

        # 5. RENEW (data accessible again)
        renewed = subscription_manager.renew_subscription(
            subscription_id=upgraded.id,
            duration_months=12,
            db=db_session
        )
        assert renewed.has_data_access() is True

        print("\n✅ COMPLETE LIFECYCLE WORKING: TRIAL → PAID → EXPIRED → GRACE → LOCKED → RENEWED!")
