"""
Unit Tests for Phase 2 Models.

Simple unit tests for model methods without API testing.
"""

import pytest
from datetime import datetime, timedelta
import sys
import os

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from networking_ai.models.company_v2 import Company
from networking_ai.models.subscription import Subscription, SubscriptionType, SubscriptionStatus
from networking_ai.models.company_admin_agent import CompanyAdminAgent, AdminAgentStatus


class TestCompanyModel:
    """Test Company model methods."""

    def test_company_initialization(self):
        """Test company can be initialized."""
        company = Company(
            name="Test Corp",
            hiring_manager_seats_allocated=10,
            hiring_manager_seats_used=0,
            talent_seats_allocated=20,
            talent_seats_used=0
        )

        assert company.name == "Test Corp"
        assert company.hiring_manager_seats_allocated == 10
        assert company.hiring_manager_seats_used == 0

    def test_has_available_hiring_manager_seats(self):
        """Test checking for available HM seats."""
        company = Company(
            name="Test Corp",
            hiring_manager_seats_allocated=10,
            hiring_manager_seats_used=5
        )

        assert company.has_available_hiring_manager_seats() is True

        # Use all seats
        company.hiring_manager_seats_used = 10
        assert company.has_available_hiring_manager_seats() is False

    def test_allocate_hiring_manager_seat(self):
        """Test allocating HM seat."""
        company = Company(
            name="Test Corp",
            hiring_manager_seats_allocated=10,
            hiring_manager_seats_used=0
        )

        result = company.allocate_hiring_manager_seat()
        assert result is True
        assert company.hiring_manager_seats_used == 1

        # Fill all seats
        company.hiring_manager_seats_used = 10
        result = company.allocate_hiring_manager_seat()
        assert result is False

    def test_release_hiring_manager_seat(self):
        """Test releasing HM seat."""
        company = Company(
            name="Test Corp",
            hiring_manager_seats_allocated=10,
            hiring_manager_seats_used=5
        )

        company.release_hiring_manager_seat()
        assert company.hiring_manager_seats_used == 4

        # Can't go below 0
        company.hiring_manager_seats_used = 0
        company.release_hiring_manager_seat()
        assert company.hiring_manager_seats_used == 0

    def test_has_available_talent_seats(self):
        """Test checking for available Talent seats."""
        company = Company(
            name="Test Corp",
            talent_seats_allocated=20,
            talent_seats_used=10
        )

        assert company.has_available_talent_seats() is True

        company.talent_seats_used = 20
        assert company.has_available_talent_seats() is False

    def test_is_subscription_active(self):
        """Test subscription active check."""
        company = Company(
            name="Test Corp",
            subscription_expires_at=datetime.utcnow() + timedelta(days=30)
        )

        assert company.is_subscription_active() is True

        company.subscription_expires_at = datetime.utcnow() - timedelta(days=1)
        assert company.is_subscription_active() is False


class TestSubscriptionModel:
    """Test Subscription model methods."""

    def test_subscription_initialization(self):
        """Test subscription can be initialized."""
        subscription = Subscription(
            user_id=1,
            subscription_type=SubscriptionType.TALENT_FREE,
            status=SubscriptionStatus.TRIAL,
            starts_at=datetime.utcnow(),
            expires_at=datetime.utcnow() + timedelta(days=365)
        )

        assert subscription.subscription_type == SubscriptionType.TALENT_FREE
        assert subscription.status == SubscriptionStatus.TRIAL

    def test_is_active(self):
        """Test subscription is_active check."""
        # Active subscription
        active = Subscription(
            subscription_type=SubscriptionType.TALENT_FREE,
            status=SubscriptionStatus.ACTIVE,
            expires_at=datetime.utcnow() + timedelta(days=30)
        )
        assert active.is_active() is True

        # Expired subscription
        expired = Subscription(
            subscription_type=SubscriptionType.TALENT_FREE,
            status=SubscriptionStatus.EXPIRED,
            expires_at=datetime.utcnow() - timedelta(days=1)
        )
        assert expired.is_active() is False

        # Trial subscription
        trial = Subscription(
            subscription_type=SubscriptionType.TALENT_FREE,
            status=SubscriptionStatus.TRIAL,
            expires_at=datetime.utcnow() + timedelta(days=30)
        )
        assert trial.is_active() is True

    def test_has_data_access_active(self):
        """Test data access for active subscription."""
        subscription = Subscription(
            subscription_type=SubscriptionType.TALENT_FREE,
            status=SubscriptionStatus.ACTIVE,
            expires_at=datetime.utcnow() + timedelta(days=30)
        )

        assert subscription.has_data_access() is True

    def test_has_data_access_grace_period(self):
        """Test data access during grace period."""
        subscription = Subscription(
            subscription_type=SubscriptionType.TALENT_FREE,
            status=SubscriptionStatus.EXPIRED,
            expires_at=datetime.utcnow() - timedelta(days=5),
            data_retention_expires_at=datetime.utcnow() + timedelta(days=25)
        )

        assert subscription.has_data_access() is True

    def test_has_data_access_expired(self):
        """Test NO PAYMENT = NO DATA: Expired subscription has no data access."""
        subscription = Subscription(
            subscription_type=SubscriptionType.TALENT_FREE,
            status=SubscriptionStatus.EXPIRED,
            expires_at=datetime.utcnow() - timedelta(days=35),
            data_retention_expires_at=datetime.utcnow() - timedelta(days=5)
        )

        # THE UNIVERSAL RULE
        assert subscription.has_data_access() is False
        print("\n🔒 UNIVERSAL RULE TESTED: No payment = No data!")

    def test_cancel(self):
        """Test subscription cancellation."""
        subscription = Subscription(
            subscription_type=SubscriptionType.TALENT_PAID,
            status=SubscriptionStatus.ACTIVE,
            auto_renew=True
        )

        subscription.cancel()

        assert subscription.status == SubscriptionStatus.CANCELLED
        assert subscription.auto_renew is False
        assert subscription.cancelled_at is not None


class TestCompanyAdminAgentModel:
    """Test CompanyAdminAgent model methods."""

    def test_admin_agent_initialization(self):
        """Test admin agent can be initialized."""
        agent = CompanyAdminAgent(
            company_id=1,
            company_rag_collection_id="company_1_master_rag",
            status=AdminAgentStatus.ACTIVE
        )

        assert agent.company_id == 1
        assert agent.status == AdminAgentStatus.ACTIVE

    def test_record_new_hiring_manager(self):
        """Test recording new hiring manager."""
        agent = CompanyAdminAgent(
            company_id=1,
            total_hiring_managers=0,
            active_hiring_managers=0
        )

        agent.record_new_hiring_manager()

        assert agent.total_hiring_managers == 1
        assert agent.active_hiring_managers == 1

    def test_record_conversation(self):
        """Test recording conversation."""
        agent = CompanyAdminAgent(
            company_id=1,
            total_conversations=10
        )

        agent.record_conversation()

        assert agent.total_conversations == 11

    def test_record_hire(self):
        """Test recording successful hire."""
        agent = CompanyAdminAgent(
            company_id=1,
            total_hires=5
        )

        agent.record_hire()

        assert agent.total_hires == 6


if __name__ == "__main__":
    # Run tests
    pytest.main([__file__, "-v", "--tb=short"])
