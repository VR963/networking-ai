"""
Test Configuration for Phase 2 Features.

Fixtures for testing multi-user architecture, subscriptions, and company management.
"""

import pytest
import os
from datetime import datetime, timedelta
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session

from src.networking_ai.api.main import app
from src.networking_ai.database import Base, get_db
from src.networking_ai.models.user import User, UserRole, AccountStatus
from src.networking_ai.models.profile import UserProfile
from src.networking_ai.models.company_v2 import Company
from src.networking_ai.models.company_admin_agent import CompanyAdminAgent, AdminAgentStatus
from src.networking_ai.models.hiring_manager_role import HiringManagerRole
from src.networking_ai.models.personal_ai_agent import PersonalAIAgent, AgentType, AgentStatus
from src.networking_ai.models.subscription import Subscription, SubscriptionType, SubscriptionStatus
from src.networking_ai.security import hash_password, create_access_token


# Test database setup
TEST_DATABASE_URL = "sqlite:///./test_phase2.db"


@pytest.fixture(scope="function")
def test_db_engine():
    """Create test database engine."""
    engine = create_engine(TEST_DATABASE_URL, connect_args={"check_same_thread": False})
    Base.metadata.create_all(bind=engine)
    yield engine
    Base.metadata.drop_all(bind=engine)
    if os.path.exists("./test_phase2.db"):
        os.remove("./test_phase2.db")


@pytest.fixture(scope="function")
def test_db(test_db_engine):
    """Create test database session."""
    TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=test_db_engine)
    yield TestingSessionLocal


@pytest.fixture(scope="function")
def db_session(test_db):
    """Create a database session for testing."""
    session = test_db()
    try:
        yield session
    finally:
        session.close()


@pytest.fixture(scope="function")
def client(test_db):
    """Create test client with test database."""
    def override_get_db():
        db = test_db()
        try:
            yield db
        finally:
            db.close()

    app.dependency_overrides[get_db] = override_get_db
    yield TestClient(app)
    app.dependency_overrides.clear()


# ============================================================================
# User Fixtures
# ============================================================================

@pytest.fixture
def talent_user(db_session: Session):
    """Create a Talent user with free trial subscription."""
    user = User(
        email="talent@test.com",
        hashed_password=hash_password("Password123!"),
        first_name="Sarah",
        last_name="Talent",
        full_name="Sarah Talent",
        role=UserRole.JOB_SEEKER,
        status=AccountStatus.ACTIVE,
        is_active=True,
        is_email_verified=True,
        created_at=datetime.utcnow()
    )
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)

    # Create profile
    profile = UserProfile(user_id=user.id)
    db_session.add(profile)

    # Create free trial subscription
    subscription = Subscription(
        user_id=user.id,
        subscription_type=SubscriptionType.TALENT_FREE,
        status=SubscriptionStatus.TRIAL,
        starts_at=datetime.utcnow(),
        expires_at=datetime.utcnow() + timedelta(days=365),
        data_retention_expires_at=datetime.utcnow() + timedelta(days=395),
        auto_renew=False
    )
    db_session.add(subscription)
    db_session.commit()

    return user


@pytest.fixture
def hiring_manager_user(db_session: Session, test_company):
    """Create a Hiring Manager user linked to company."""
    user = User(
        email="hm@test.com",
        hashed_password=hash_password("Password123!"),
        first_name="John",
        last_name="Manager",
        full_name="John Manager",
        role=UserRole.JOB_SEEKER,  # Base role
        status=AccountStatus.ACTIVE,
        is_active=True,
        is_email_verified=True,
        created_at=datetime.utcnow()
    )
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)

    # Create HM subscription
    subscription = Subscription(
        user_id=user.id,
        company_id=test_company.id,
        subscription_type=SubscriptionType.HIRING_MANAGER,
        status=SubscriptionStatus.ACTIVE,
        starts_at=datetime.utcnow(),
        expires_at=test_company.subscription_expires_at,
        data_retention_expires_at=test_company.subscription_expires_at + timedelta(days=30),
        auto_renew=False
    )
    db_session.add(subscription)
    db_session.commit()

    return user


@pytest.fixture
def recruiter_user(db_session: Session):
    """Create a Recruiter user."""
    user = User(
        email="recruiter@test.com",
        hashed_password=hash_password("Password123!"),
        first_name="Alice",
        last_name="Recruiter",
        full_name="Alice Recruiter",
        role=UserRole.JOB_SEEKER,  # Base role
        status=AccountStatus.ACTIVE,
        is_active=True,
        is_email_verified=True,
        created_at=datetime.utcnow()
    )
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)

    # Create Recruiter subscription
    subscription = Subscription(
        user_id=user.id,
        subscription_type=SubscriptionType.RECRUITER,
        status=SubscriptionStatus.ACTIVE,
        starts_at=datetime.utcnow(),
        expires_at=datetime.utcnow() + timedelta(days=365),
        data_retention_expires_at=datetime.utcnow() + timedelta(days=395),
        billing_amount=1199.88,
        billing_currency="USD",
        billing_interval="annually",
        auto_renew=True
    )
    db_session.add(subscription)
    db_session.commit()

    return user


# ============================================================================
# Company Fixtures
# ============================================================================

@pytest.fixture
def test_company(db_session: Session):
    """Create a test company with seat allocation."""
    company = Company(
        name="TechCorp Test",
        description="A test technology company",
        industry="Technology",
        size="50-200",
        website="https://techcorp.test",
        hiring_manager_seats_allocated=10,
        hiring_manager_seats_used=0,
        talent_seats_allocated=20,
        talent_seats_used=0,
        subscription_expires_at=datetime.utcnow() + timedelta(days=365),
        created_at=datetime.utcnow(),
        updated_at=datetime.utcnow()
    )
    db_session.add(company)
    db_session.commit()
    db_session.refresh(company)

    return company


@pytest.fixture
def company_admin_agent(db_session: Session, test_company):
    """Create a Company Admin Agent."""
    admin_agent = CompanyAdminAgent(
        company_id=test_company.id,
        company_rag_collection_id=f"company_{test_company.id}_master_rag",
        status=AdminAgentStatus.ACTIVE,
        total_hiring_managers=0,
        active_hiring_managers=0,
        total_conversations=0,
        total_hires=0,
        created_at=datetime.utcnow(),
        updated_at=datetime.utcnow()
    )
    db_session.add(admin_agent)
    db_session.commit()
    db_session.refresh(admin_agent)

    return admin_agent


@pytest.fixture
def hiring_manager_role(db_session: Session, hiring_manager_user, test_company, company_admin_agent):
    """Create a Hiring Manager Role linking user to company."""
    # First create HM agent
    hm_agent = PersonalAIAgent(
        user_id=hiring_manager_user.id,
        agent_type=AgentType.HIRING_MANAGER,
        personal_rag_collection_id=f"user_{hiring_manager_user.id}_hm_rag",
        status=AgentStatus.ACTIVE,
        industry="Technology",
        role="Engineering Manager",
        user_segment_id="engineering_manager_tech_5yrs",
        created_at=datetime.utcnow(),
        activated_at=datetime.utcnow()
    )
    db_session.add(hm_agent)
    db_session.commit()
    db_session.refresh(hm_agent)

    # Create role linking
    hm_role = HiringManagerRole(
        user_id=hiring_manager_user.id,
        company_id=test_company.id,
        hiring_manager_agent_id=hm_agent.id,
        company_admin_agent_id=company_admin_agent.id,
        is_active=True,
        joined_at=datetime.utcnow()
    )
    db_session.add(hm_role)

    # Update company seats
    test_company.hiring_manager_seats_used = 1

    db_session.commit()
    db_session.refresh(hm_role)

    return hm_role


# ============================================================================
# Personal AI Agent Fixtures
# ============================================================================

@pytest.fixture
def talent_agent(db_session: Session, talent_user):
    """Create a Talent Personal AI Agent."""
    agent = PersonalAIAgent(
        user_id=talent_user.id,
        agent_type=AgentType.JOBSEEKER,
        personal_rag_collection_id=f"user_{talent_user.id}_personal_rag",
        status=AgentStatus.ACTIVE,
        industry="Technology",
        role="Software Engineer",
        user_segment_id="software_engineer_tech_3yrs_python",
        total_conversations=5,
        successful_matches=2,
        learning_score=0.65,
        created_at=datetime.utcnow(),
        activated_at=datetime.utcnow()
    )
    db_session.add(agent)
    db_session.commit()
    db_session.refresh(agent)

    return agent


@pytest.fixture
def recruiter_agent(db_session: Session, recruiter_user):
    """Create a Recruiter Personal AI Agent."""
    agent = PersonalAIAgent(
        user_id=recruiter_user.id,
        agent_type=AgentType.RECRUITER,
        personal_rag_collection_id=f"user_{recruiter_user.id}_recruiter_rag",
        status=AgentStatus.ACTIVE,
        industry="Recruitment",
        role="Tech Recruiter",
        recruitment_company_name="Elite Tech Recruiters",
        recruitment_company_description="Specialized tech recruitment agency",
        user_segment_id="tech_recruiter_5yrs",
        created_at=datetime.utcnow(),
        activated_at=datetime.utcnow()
    )
    db_session.add(agent)
    db_session.commit()
    db_session.refresh(agent)

    return agent


# ============================================================================
# Authentication Fixtures
# ============================================================================

@pytest.fixture
def talent_auth_token(talent_user):
    """Create auth token for talent user."""
    return create_access_token(data={"sub": talent_user.id})


@pytest.fixture
def talent_auth_headers(talent_auth_token):
    """Create auth headers for talent user."""
    return {"Authorization": f"Bearer {talent_auth_token}"}


@pytest.fixture
def hm_auth_token(hiring_manager_user):
    """Create auth token for hiring manager user."""
    return create_access_token(data={"sub": hiring_manager_user.id})


@pytest.fixture
def hm_auth_headers(hm_auth_token):
    """Create auth headers for hiring manager user."""
    return {"Authorization": f"Bearer {hm_auth_token}"}


@pytest.fixture
def recruiter_auth_token(recruiter_user):
    """Create auth token for recruiter user."""
    return create_access_token(data={"sub": recruiter_user.id})


@pytest.fixture
def recruiter_auth_headers(recruiter_auth_token):
    """Create auth headers for recruiter user."""
    return {"Authorization": f"Bearer {recruiter_auth_token}"}


# ============================================================================
# Subscription Fixtures
# ============================================================================

@pytest.fixture
def expired_subscription(db_session: Session, talent_user):
    """Create an expired subscription."""
    subscription = Subscription(
        user_id=talent_user.id,
        subscription_type=SubscriptionType.TALENT_FREE,
        status=SubscriptionStatus.EXPIRED,
        starts_at=datetime.utcnow() - timedelta(days=400),
        expires_at=datetime.utcnow() - timedelta(days=35),  # Expired 35 days ago
        data_retention_expires_at=datetime.utcnow() - timedelta(days=5),  # Grace period also expired
        auto_renew=False
    )
    db_session.add(subscription)
    db_session.commit()
    db_session.refresh(subscription)

    return subscription


@pytest.fixture
def grace_period_subscription(db_session: Session):
    """Create a subscription in grace period."""
    user = User(
        email="grace@test.com",
        hashed_password=hash_password("Password123!"),
        first_name="Grace",
        last_name="Period",
        full_name="Grace Period",
        role=UserRole.JOB_SEEKER,
        status=AccountStatus.ACTIVE,
        is_active=True,
        created_at=datetime.utcnow()
    )
    db_session.add(user)
    db_session.commit()

    subscription = Subscription(
        user_id=user.id,
        subscription_type=SubscriptionType.TALENT_FREE,
        status=SubscriptionStatus.EXPIRED,
        starts_at=datetime.utcnow() - timedelta(days=400),
        expires_at=datetime.utcnow() - timedelta(days=5),  # Expired 5 days ago
        data_retention_expires_at=datetime.utcnow() + timedelta(days=25),  # Still in grace period
        auto_renew=False
    )
    db_session.add(subscription)
    db_session.commit()
    db_session.refresh(subscription)

    return subscription
