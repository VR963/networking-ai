"""
Tests for Phase 2 Registration API.

Tests multi-user type registration:
- Talent registration (free trial)
- Add Hiring Manager function
- Add Recruiter function
- User functions status
"""

import pytest
from datetime import datetime
from sqlalchemy.orm import Session

from networking_ai.models.user import User, UserRole
from networking_ai.models.subscription import Subscription, SubscriptionType, SubscriptionStatus
from networking_ai.models.company_v2 import Company
from networking_ai.models.hiring_manager_role import HiringManagerRole
from networking_ai.models.personal_ai_agent import PersonalAIAgent, AgentType

# Import fixtures
pytest_plugins = ["tests.conftest_phase2"]


class TestTalentRegistration:
    """Test Talent user registration."""

    def test_register_talent_success(self, client, db_session):
        """Test successful talent registration."""
        response = client.post(
            "/api/registration/register/talent",
            json={
                "email": "newuser@test.com",
                "password": "SecurePass123!",
                "first_name": "John",
                "last_name": "Doe"
            }
        )

        assert response.status_code == 201
        data = response.json()

        assert data["email"] == "newuser@test.com"
        assert data["full_name"] == "John Doe"
        assert data["subscription_type"] == "talent_free"
        assert "subscription_expires_at" in data
        assert "Complete CV upload" in data["message"]

        # Verify user created in database
        user = db_session.query(User).filter(User.email == "newuser@test.com").first()
        assert user is not None
        assert user.first_name == "John"
        assert user.last_name == "Doe"
        assert user.full_name == "John Doe"

        # Verify subscription created
        subscription = db_session.query(Subscription).filter(
            Subscription.user_id == user.id
        ).first()
        assert subscription is not None
        assert subscription.subscription_type == SubscriptionType.TALENT_FREE
        assert subscription.status == SubscriptionStatus.TRIAL

    def test_register_talent_duplicate_email(self, client, talent_user):
        """Test registration with duplicate email fails."""
        response = client.post(
            "/api/registration/register/talent",
            json={
                "email": "talent@test.com",  # Already exists
                "password": "SecurePass123!",
                "first_name": "Another",
                "last_name": "User"
            }
        )

        assert response.status_code == 400
        assert "already registered" in response.json()["detail"].lower()

    def test_register_talent_invalid_email(self, client):
        """Test registration with invalid email fails."""
        response = client.post(
            "/api/registration/register/talent",
            json={
                "email": "not-an-email",
                "password": "SecurePass123!",
                "first_name": "John",
                "last_name": "Doe"
            }
        )

        assert response.status_code == 422  # Validation error

    def test_register_talent_weak_password(self, client):
        """Test registration with weak password fails."""
        response = client.post(
            "/api/registration/register/talent",
            json={
                "email": "test@example.com",
                "password": "weak",  # Too short
                "first_name": "John",
                "last_name": "Doe"
            }
        )

        assert response.status_code == 422  # Validation error


class TestAddHiringManagerFunction:
    """Test adding Hiring Manager function to account."""

    def test_add_hm_function_new_company(self, client, talent_user, talent_auth_headers, db_session):
        """Test adding HM function with new company creation."""
        response = client.post(
            "/api/registration/add-function/hiring-manager",
            headers=talent_auth_headers,
            json={
                "company_name": "NewTech Corp",
                "company_description": "Innovative tech company",
                "company_industry": "Technology"
            }
        )

        assert response.status_code == 200
        data = response.json()

        assert "hiring_manager_role_id" in data
        assert data["company_name"] == "NewTech Corp"
        assert "Complete HM interview" in data["message"]

        # Verify company created
        company = db_session.query(Company).filter(
            Company.name == "NewTech Corp"
        ).first()
        assert company is not None
        assert company.description == "Innovative tech company"
        assert company.industry == "Technology"

        # Verify HM role created
        hm_role = db_session.query(HiringManagerRole).filter(
            HiringManagerRole.user_id == talent_user.id
        ).first()
        assert hm_role is not None
        assert hm_role.company_id == company.id
        assert hm_role.is_active is True

        # Verify HM subscription created
        hm_sub = db_session.query(Subscription).filter(
            Subscription.user_id == talent_user.id,
            Subscription.subscription_type == SubscriptionType.HIRING_MANAGER
        ).first()
        assert hm_sub is not None
        assert hm_sub.company_id == company.id

    def test_add_hm_function_existing_company(
        self, client, talent_user, talent_auth_headers, test_company, company_admin_agent, db_session
    ):
        """Test adding HM function with existing company."""
        response = client.post(
            "/api/registration/add-function/hiring-manager",
            headers=talent_auth_headers,
            json={
                "company_id": test_company.id
            }
        )

        assert response.status_code == 200
        data = response.json()

        assert data["company_id"] == test_company.id
        assert data["company_name"] == test_company.name

        # Verify HM role created
        hm_role = db_session.query(HiringManagerRole).filter(
            HiringManagerRole.user_id == talent_user.id,
            HiringManagerRole.company_id == test_company.id
        ).first()
        assert hm_role is not None

    def test_add_hm_function_already_has_hm(
        self, client, hiring_manager_user, hm_auth_headers, hiring_manager_role
    ):
        """Test adding HM function when user already has HM function fails."""
        response = client.post(
            "/api/registration/add-function/hiring-manager",
            headers=hm_auth_headers,
            json={
                "company_name": "Another Company"
            }
        )

        assert response.status_code == 400
        assert "already has an active Hiring Manager" in response.json()["detail"]

    def test_add_hm_function_no_company_name(self, client, talent_auth_headers):
        """Test adding HM function without company name fails."""
        response = client.post(
            "/api/registration/add-function/hiring-manager",
            headers=talent_auth_headers,
            json={}  # No company_id or company_name
        )

        assert response.status_code == 400
        assert "company_name required" in response.json()["detail"]

    def test_add_hm_function_no_available_seats(
        self, client, talent_user, talent_auth_headers, test_company, company_admin_agent, db_session
    ):
        """Test adding HM function when company has no available seats fails."""
        # Use up all seats
        test_company.hiring_manager_seats_used = test_company.hiring_manager_seats_allocated
        db_session.commit()

        response = client.post(
            "/api/registration/add-function/hiring-manager",
            headers=talent_auth_headers,
            json={
                "company_id": test_company.id
            }
        )

        assert response.status_code == 400
        assert "No available Hiring Manager seats" in response.json()["detail"]


class TestAddRecruiterFunction:
    """Test adding Recruiter function to account."""

    def test_add_recruiter_function_success(self, client, talent_user, talent_auth_headers, db_session):
        """Test successful recruiter function addition."""
        response = client.post(
            "/api/registration/add-function/recruiter",
            headers=talent_auth_headers,
            json={
                "recruitment_company_name": "Elite Recruiters",
                "recruitment_company_description": "Tech recruitment specialists"
            }
        )

        assert response.status_code == 200
        data = response.json()

        assert "recruiter_agent_id" in data
        assert "subscription_id" in data
        assert "Complete Recruiter interview" in data["message"]

        # Verify recruiter agent created
        agent = db_session.query(PersonalAIAgent).filter(
            PersonalAIAgent.user_id == talent_user.id,
            PersonalAIAgent.agent_type == AgentType.RECRUITER
        ).first()
        assert agent is not None
        assert agent.recruitment_company_name == "Elite Recruiters"
        assert agent.status == "pending"  # Not activated yet

        # Verify recruiter subscription created
        subscription = db_session.query(Subscription).filter(
            Subscription.user_id == talent_user.id,
            Subscription.subscription_type == SubscriptionType.RECRUITER
        ).first()
        assert subscription is not None
        assert subscription.status == SubscriptionStatus.ACTIVE

    def test_add_recruiter_function_already_has_recruiter(
        self, client, recruiter_user, recruiter_auth_headers, recruiter_agent
    ):
        """Test adding recruiter function when user already has recruiter fails."""
        response = client.post(
            "/api/registration/add-function/recruiter",
            headers=recruiter_auth_headers,
            json={
                "recruitment_company_name": "Another Agency"
            }
        )

        assert response.status_code == 400
        assert "already has a Recruiter function" in response.json()["detail"]


class TestUserFunctionsStatus:
    """Test viewing user functions status."""

    def test_get_functions_talent_only(self, client, talent_user, talent_auth_headers, talent_agent):
        """Test getting functions for talent-only user."""
        response = client.get(
            "/api/registration/me/functions",
            headers=talent_auth_headers
        )

        assert response.status_code == 200
        data = response.json()

        assert data["user_id"] == talent_user.id
        assert data["email"] == talent_user.email
        assert data["has_talent_function"] is True
        assert data["has_hiring_manager_function"] is False
        assert data["has_recruiter_function"] is False
        assert data["talent_subscription_active"] is True

    def test_get_functions_talent_and_hm(
        self, client, hiring_manager_user, hm_auth_headers, hiring_manager_role, test_company, db_session
    ):
        """Test getting functions for user with both Talent and HM functions."""
        # Add talent subscription
        talent_sub = Subscription(
            user_id=hiring_manager_user.id,
            subscription_type=SubscriptionType.TALENT_FREE,
            status=SubscriptionStatus.TRIAL,
            starts_at=datetime.utcnow(),
            expires_at=datetime.utcnow(),
            auto_renew=False
        )
        db_session.add(talent_sub)
        db_session.commit()

        response = client.get(
            "/api/registration/me/functions",
            headers=hm_auth_headers
        )

        assert response.status_code == 200
        data = response.json()

        assert data["has_talent_function"] is True
        assert data["has_hiring_manager_function"] is True
        assert data["has_recruiter_function"] is False
        assert data["hiring_manager_company"] == test_company.name

    def test_get_functions_all_types(
        self, client, talent_user, talent_auth_headers, test_company, company_admin_agent, db_session
    ):
        """Test getting functions for user with all function types."""
        # Add HM function
        hm_agent = PersonalAIAgent(
            user_id=talent_user.id,
            agent_type=AgentType.HIRING_MANAGER,
            personal_rag_collection_id=f"user_{talent_user.id}_hm_rag",
            status=AgentStatus.ACTIVE
        )
        db_session.add(hm_agent)
        db_session.commit()

        hm_role = HiringManagerRole(
            user_id=talent_user.id,
            company_id=test_company.id,
            hiring_manager_agent_id=hm_agent.id,
            company_admin_agent_id=company_admin_agent.id,
            is_active=True,
            joined_at=datetime.utcnow()
        )
        db_session.add(hm_role)

        # Add Recruiter function
        recruiter_agent = PersonalAIAgent(
            user_id=talent_user.id,
            agent_type=AgentType.RECRUITER,
            personal_rag_collection_id=f"user_{talent_user.id}_rec_rag",
            recruitment_company_name="Test Recruiters",
            status=AgentStatus.ACTIVE
        )
        db_session.add(recruiter_agent)
        db_session.commit()

        response = client.get(
            "/api/registration/me/functions",
            headers=talent_auth_headers
        )

        assert response.status_code == 200
        data = response.json()

        assert data["has_talent_function"] is True
        assert data["has_hiring_manager_function"] is True
        assert data["has_recruiter_function"] is True
        assert data["hiring_manager_company"] == test_company.name
        assert data["recruiter_company"] == "Test Recruiters"


class TestSimultaneousFunctions:
    """Test the unique feature: simultaneous multi-function accounts."""

    def test_user_can_be_both_talent_and_hm(
        self, client, talent_user, talent_auth_headers, test_company, company_admin_agent, db_session
    ):
        """
        Test THE UNIQUE FEATURE: User can have BOTH Talent and HM functions active.

        This is what makes the platform revolutionary!
        Example: Sarah is job seeking (Talent) AND hiring for her team (HM) simultaneously.
        """
        # User starts as Talent (already has talent subscription via fixture)

        # Add HM function
        response = client.post(
            "/api/registration/add-function/hiring-manager",
            headers=talent_auth_headers,
            json={
                "company_id": test_company.id
            }
        )
        assert response.status_code == 200

        # Verify user has BOTH subscriptions
        subscriptions = db_session.query(Subscription).filter(
            Subscription.user_id == talent_user.id
        ).all()

        subscription_types = [sub.subscription_type for sub in subscriptions]
        assert SubscriptionType.TALENT_FREE in subscription_types
        assert SubscriptionType.HIRING_MANAGER in subscription_types

        # Verify functions status shows both
        response = client.get(
            "/api/registration/me/functions",
            headers=talent_auth_headers
        )
        data = response.json()

        assert data["has_talent_function"] is True
        assert data["has_hiring_manager_function"] is True

        # This is the revolutionary feature!
        print("\n🎉 UNIQUE FEATURE WORKING: User has both Talent AND Hiring Manager functions!")
