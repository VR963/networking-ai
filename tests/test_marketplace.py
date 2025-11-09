"""
Tests for AI Agent Marketplace (Phase 12).

Tests template creation, publishing, discovery, installation, and reviews.
"""

import pytest
import os
from decimal import Decimal
from datetime import datetime
from uuid import uuid4
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session

from src.networking_ai.api.main import app
from src.networking_ai.database import Base, get_db
from src.networking_ai.models.marketplace import (
    AgentTemplate, TemplatePurchase, TemplateReview, TemplateInstallation,
    TemplateCategory, TemplateStatus
)
from src.networking_ai.models.personal_ai_agent import PersonalAIAgent, AgentStatus
from src.networking_ai.models.user import User, UserRole, AccountStatus
from src.networking_ai.security import hash_password


# Test database setup
TEST_DATABASE_URL = "sqlite:///./test_marketplace.db"


@pytest.fixture(scope="function")
def test_db_engine():
    """Create test database engine."""
    engine = create_engine(TEST_DATABASE_URL, connect_args={"check_same_thread": False})
    Base.metadata.create_all(bind=engine)
    yield engine
    Base.metadata.drop_all(bind=engine)
    if os.path.exists("./test_marketplace.db"):
        os.remove("./test_marketplace.db")


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


@pytest.fixture
def talent_user(db_session: Session):
    """Create a talent user for testing."""
    user = User(
        email="talent@test.com",
        hashed_password=hash_password("Test123!"),
        full_name="Test Talent",
        role=UserRole.TALENT,
        status=AccountStatus.ACTIVE,
        is_active=True
    )
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)
    return user


# ============================================================================
# Template Creation Tests
# ============================================================================

def test_create_template(client, talent_user, db_session):
    """Test creating a new template."""
    # Login
    login_response = client.post("/api/auth/login", json={
        "email": talent_user.email,
        "password": "Test123!"
    })
    assert login_response.status_code == 200
    token = login_response.json()["access_token"]

    # Create template
    template_data = {
        "name": "Career Coach Pro",
        "description": "Professional career coaching agent with industry insights",
        "category": "career_coach",
        "tags": ["career", "coaching", "professional"],
        "price": 9.99,
        "configuration": {
            "model": "gpt-4",
            "temperature": 0.7
        },
        "prompt_template": "You are a professional career coach helping users advance their careers.",
        "knowledge_sources": {},
        "sub_agents": [],
        "version": "1.0.0"
    }

    response = client.post(
        "/api/v1/marketplace/templates",
        json=template_data,
        headers={"Authorization": f"Bearer {token}"}
    )

    assert response.status_code == 201
    data = response.json()
    assert data["name"] == "Career Coach Pro"
    assert data["status"] == "draft"
    assert Decimal(str(data["price"])) == Decimal("9.99")
    assert data["creator_id"] == talent_user.id


def test_create_template_invalid_data(client, talent_user):
    """Test creating template with invalid data."""
    # Login
    login_response = client.post("/api/auth/login", json={
        "email": talent_user.email,
        "password": "Test123!"
    })
    token = login_response.json()["access_token"]

    # Missing required fields
    response = client.post(
        "/api/v1/marketplace/templates",
        json={"name": "Test"},
        headers={"Authorization": f"Bearer {token}"}
    )

    assert response.status_code == 422  # Validation error


# ============================================================================
# Template Update Tests
# ============================================================================

def test_update_own_template(client, talent_user, db_session):
    """Test updating own template."""
    # Create template
    template = AgentTemplate(
        creator_id=talent_user.id,
        name="Test Template",
        description="Test description for the template",
        category=TemplateCategory.CAREER_COACH,
        price=Decimal("0.00"),
        configuration={"test": "config"},
        prompt_template="Test prompt",
        status=TemplateStatus.DRAFT
    )
    db_session.add(template)
    db_session.commit()

    # Login
    login_response = client.post("/api/auth/login", json={
        "email": talent_user.email,
        "password": "Test123!"
    })
    token = login_response.json()["access_token"]

    # Update template
    response = client.put(
        f"/api/v1/marketplace/templates/{template.id}",
        json={"name": "Updated Template", "price": 5.00},
        headers={"Authorization": f"Bearer {token}"}
    )

    assert response.status_code == 200
    data = response.json()
    assert data["name"] == "Updated Template"
    assert Decimal(str(data["price"])) == Decimal("5.00")


# ============================================================================
# Template Publishing Tests
# ============================================================================

def test_publish_free_template(client, talent_user, db_session):
    """Test publishing a free template."""
    # Create template
    template = AgentTemplate(
        creator_id=talent_user.id,
        name="Free Template",
        description="This is a free template for testing",
        category=TemplateCategory.CAREER_COACH,
        price=Decimal("0.00"),
        configuration={"test": "config"},
        prompt_template="You are a helpful career coach",
        status=TemplateStatus.DRAFT
    )
    db_session.add(template)
    db_session.commit()

    # Login
    login_response = client.post("/api/auth/login", json={
        "email": talent_user.email,
        "password": "Test123!"
    })
    token = login_response.json()["access_token"]

    # Publish template
    response = client.put(
        f"/api/v1/marketplace/templates/{template.id}/publish",
        json={"submit_for_review": False},
        headers={"Authorization": f"Bearer {token}"}
    )

    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "published"
    assert data["published_at"] is not None


def test_publish_paid_template_requires_review(client, talent_user, db_session):
    """Test publishing a paid template requires admin review."""
    # Create paid template
    template = AgentTemplate(
        creator_id=talent_user.id,
        name="Premium Template",
        description="This is a premium paid template",
        category=TemplateCategory.CAREER_COACH,
        price=Decimal("19.99"),
        configuration={"test": "config"},
        prompt_template="You are a premium career coach",
        status=TemplateStatus.DRAFT
    )
    db_session.add(template)
    db_session.commit()

    # Login
    login_response = client.post("/api/auth/login", json={
        "email": talent_user.email,
        "password": "Test123!"
    })
    token = login_response.json()["access_token"]

    # Publish template
    response = client.put(
        f"/api/v1/marketplace/templates/{template.id}/publish",
        json={"submit_for_review": True},
        headers={"Authorization": f"Bearer {token}"}
    )

    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "pending_review"


# ============================================================================
# Template Discovery Tests
# ============================================================================

def test_browse_templates(client, db_session):
    """Test browsing published templates."""
    # Create multiple published templates
    for i in range(5):
        template = AgentTemplate(
            creator_id=1,  # Assume user exists
            name=f"Template {i}",
            description=f"Description for template {i}",
            category=TemplateCategory.CAREER_COACH,
            price=Decimal("0.00"),
            configuration={},
            prompt_template="Test prompt",
            status=TemplateStatus.PUBLISHED,
            published_at=datetime.utcnow()
        )
        db_session.add(template)
    db_session.commit()

    # Browse templates
    response = client.get("/api/v1/marketplace/templates")

    assert response.status_code == 200
    data = response.json()
    assert data["total"] >= 5
    assert len(data["templates"]) >= 5
    assert data["page"] == 1


def test_search_templates_by_query(client, db_session, talent_user):
    """Test searching templates by keyword."""
    # Create templates
    template1 = AgentTemplate(
        creator_id=talent_user.id,
        name="Interview Coach",
        description="Helps with interview preparation",
        category=TemplateCategory.INTERVIEW_PREP,
        price=Decimal("0.00"),
        configuration={},
        prompt_template="Test",
        status=TemplateStatus.PUBLISHED,
        published_at=datetime.utcnow()
    )
    template2 = AgentTemplate(
        creator_id=talent_user.id,
        name="Resume Builder",
        description="Creates professional resumes",
        category=TemplateCategory.RESUME_BUILDER,
        price=Decimal("0.00"),
        configuration={},
        prompt_template="Test",
        status=TemplateStatus.PUBLISHED,
        published_at=datetime.utcnow()
    )
    db_session.add_all([template1, template2])
    db_session.commit()

    # Search for "interview"
    response = client.get("/api/v1/marketplace/templates?query=interview")

    assert response.status_code == 200
    data = response.json()
    assert any("Interview" in t["name"] for t in data["templates"])


def test_filter_templates_by_category(client, db_session, talent_user):
    """Test filtering templates by category."""
    # Create templates in different categories
    template1 = AgentTemplate(
        creator_id=talent_user.id,
        name="Career Coach",
        description="Career coaching",
        category=TemplateCategory.CAREER_COACH,
        price=Decimal("0.00"),
        configuration={},
        prompt_template="Test",
        status=TemplateStatus.PUBLISHED,
        published_at=datetime.utcnow()
    )
    template2 = AgentTemplate(
        creator_id=talent_user.id,
        name="Interview Prep",
        description="Interview preparation",
        category=TemplateCategory.INTERVIEW_PREP,
        price=Decimal("0.00"),
        configuration={},
        prompt_template="Test",
        status=TemplateStatus.PUBLISHED,
        published_at=datetime.utcnow()
    )
    db_session.add_all([template1, template2])
    db_session.commit()

    # Filter by career_coach category
    response = client.get("/api/v1/marketplace/templates?category=career_coach")

    assert response.status_code == 200
    data = response.json()
    assert all(t["category"] == "career_coach" for t in data["templates"])


def test_filter_free_templates_only(client, db_session, talent_user):
    """Test filtering for free templates only."""
    # Create free and paid templates
    free_template = AgentTemplate(
        creator_id=talent_user.id,
        name="Free Template",
        description="Free template",
        category=TemplateCategory.CAREER_COACH,
        price=Decimal("0.00"),
        configuration={},
        prompt_template="Test",
        status=TemplateStatus.PUBLISHED,
        published_at=datetime.utcnow()
    )
    paid_template = AgentTemplate(
        creator_id=talent_user.id,
        name="Paid Template",
        description="Paid template",
        category=TemplateCategory.CAREER_COACH,
        price=Decimal("9.99"),
        configuration={},
        prompt_template="Test",
        status=TemplateStatus.PUBLISHED,
        published_at=datetime.utcnow()
    )
    db_session.add_all([free_template, paid_template])
    db_session.commit()

    # Filter for free only
    response = client.get("/api/v1/marketplace/templates?free_only=true")

    assert response.status_code == 200
    data = response.json()
    assert all(Decimal(str(t["price"])) == Decimal("0.00") for t in data["templates"])


# ============================================================================
# Template Installation Tests
# ============================================================================

def test_install_free_template(client, talent_user, db_session):
    """Test installing a free template."""
    # Create free template
    template = AgentTemplate(
        creator_id=talent_user.id,
        name="Free Career Coach",
        description="Free career coaching template",
        category=TemplateCategory.CAREER_COACH,
        price=Decimal("0.00"),
        configuration={"model": "gpt-4"},
        prompt_template="You are a career coach",
        status=TemplateStatus.PUBLISHED,
        published_at=datetime.utcnow()
    )
    db_session.add(template)
    db_session.commit()

    # Login
    login_response = client.post("/api/auth/login", json={
        "email": talent_user.email,
        "password": "Test123!"
    })
    token = login_response.json()["access_token"]

    # Install template
    response = client.post(
        f"/api/v1/marketplace/templates/{template.id}/install",
        json={"agent_name": "My Career Coach"},
        headers={"Authorization": f"Bearer {token}"}
    )

    assert response.status_code == 201
    data = response.json()
    assert data["installation_successful"] == True
    assert data["agent_id"] is not None

    # Verify agent was created
    agent = db_session.query(PersonalAIAgent).filter(
        PersonalAIAgent.id == data["agent_id"]
    ).first()
    assert agent is not None
    assert agent.name == "My Career Coach"


def test_cannot_install_paid_template_without_purchase(client, talent_user, db_session):
    """Test that paid templates require purchase before installation."""
    # Create another user as template creator
    creator = User(
        email="creator@test.com",
        hashed_password="hashed",
        full_name="Creator",
        role=UserRole.TALENT
    )
    db_session.add(creator)
    db_session.flush()

    # Create paid template
    template = AgentTemplate(
        creator_id=creator.id,
        name="Premium Template",
        description="Premium paid template",
        category=TemplateCategory.CAREER_COACH,
        price=Decimal("19.99"),
        configuration={"model": "gpt-4"},
        prompt_template="You are a premium coach",
        status=TemplateStatus.PUBLISHED,
        published_at=datetime.utcnow()
    )
    db_session.add(template)
    db_session.commit()

    # Login as talent user
    login_response = client.post("/api/auth/login", json={
        "email": talent_user.email,
        "password": "Test123!"
    })
    token = login_response.json()["access_token"]

    # Try to install without purchase
    response = client.post(
        f"/api/v1/marketplace/templates/{template.id}/install",
        json={},
        headers={"Authorization": f"Bearer {token}"}
    )

    assert response.status_code == 402  # Payment Required


# ============================================================================
# Review Tests
# ============================================================================

def test_create_review_after_installation(client, talent_user, db_session):
    """Test creating a review after installing a template."""
    # Create template
    template = AgentTemplate(
        creator_id=talent_user.id,
        name="Test Template",
        description="Test template",
        category=TemplateCategory.CAREER_COACH,
        price=Decimal("0.00"),
        configuration={},
        prompt_template="Test",
        status=TemplateStatus.PUBLISHED,
        published_at=datetime.utcnow()
    )
    db_session.add(template)
    db_session.flush()

    # Create agent
    agent = PersonalAIAgent(
        user_id=talent_user.id,
        name="Test Agent",
        status=AgentStatus.ACTIVE,
        system_prompt="Test"
    )
    db_session.add(agent)
    db_session.flush()

    # Create installation
    installation = TemplateInstallation(
        template_id=template.id,
        user_id=talent_user.id,
        agent_id=agent.id,
        installation_successful=True
    )
    db_session.add(installation)
    db_session.commit()

    # Login
    login_response = client.post("/api/auth/login", json={
        "email": talent_user.email,
        "password": "Test123!"
    })
    token = login_response.json()["access_token"]

    # Create review
    response = client.post(
        f"/api/v1/marketplace/templates/{template.id}/reviews",
        json={
            "rating": 5,
            "title": "Excellent template!",
            "review_text": "This template helped me a lot with my career."
        },
        headers={"Authorization": f"Bearer {token}"}
    )

    assert response.status_code == 201
    data = response.json()
    assert data["rating"] == 5
    assert data["title"] == "Excellent template!"


def test_cannot_review_without_installation(client, talent_user, db_session):
    """Test that reviews require prior installation."""
    # Create template
    template = AgentTemplate(
        creator_id=talent_user.id,
        name="Test Template",
        description="Test template",
        category=TemplateCategory.CAREER_COACH,
        price=Decimal("0.00"),
        configuration={},
        prompt_template="Test",
        status=TemplateStatus.PUBLISHED,
        published_at=datetime.utcnow()
    )
    db_session.add(template)
    db_session.commit()

    # Login
    login_response = client.post("/api/auth/login", json={
        "email": talent_user.email,
        "password": "Test123!"
    })
    token = login_response.json()["access_token"]

    # Try to review without installation
    response = client.post(
        f"/api/v1/marketplace/templates/{template.id}/reviews",
        json={
            "rating": 5,
            "review_text": "Great template!"
        },
        headers={"Authorization": f"Bearer {token}"}
    )

    assert response.status_code == 403  # Forbidden


def test_get_template_reviews(client, talent_user, db_session):
    """Test getting reviews for a template."""
    # Create template
    template = AgentTemplate(
        creator_id=talent_user.id,
        name="Test Template",
        description="Test template",
        category=TemplateCategory.CAREER_COACH,
        price=Decimal("0.00"),
        configuration={},
        prompt_template="Test",
        status=TemplateStatus.PUBLISHED,
        published_at=datetime.utcnow(),
        average_rating=Decimal("4.5"),
        review_count=2
    )
    db_session.add(template)
    db_session.flush()

    # Create reviews
    review1 = TemplateReview(
        template_id=template.id,
        user_id=talent_user.id,
        rating=5,
        review_text="Excellent!",
        is_verified_purchase=True
    )
    review2 = TemplateReview(
        template_id=template.id,
        user_id=talent_user.id,
        rating=4,
        review_text="Very good",
        is_verified_purchase=False
    )
    db_session.add_all([review1, review2])
    db_session.commit()

    # Get reviews
    response = client.get(f"/api/v1/marketplace/templates/{template.id}/reviews")

    assert response.status_code == 200
    data = response.json()
    assert data["total"] == 2
    assert len(data["reviews"]) == 2
    assert Decimal(str(data["average_rating"])) == Decimal("4.5")


# ============================================================================
# Creator Dashboard Tests
# ============================================================================

def test_creator_dashboard(client, talent_user, db_session):
    """Test creator dashboard endpoint."""
    # Create templates
    template1 = AgentTemplate(
        creator_id=talent_user.id,
        name="Template 1",
        description="First template",
        category=TemplateCategory.CAREER_COACH,
        price=Decimal("0.00"),
        configuration={},
        prompt_template="Test",
        status=TemplateStatus.PUBLISHED,
        downloads_count=10,
        installations_count=8,
        revenue_total=Decimal("0.00"),
        average_rating=Decimal("4.5"),
        review_count=5
    )
    template2 = AgentTemplate(
        creator_id=talent_user.id,
        name="Template 2",
        description="Second template",
        category=TemplateCategory.INTERVIEW_PREP,
        price=Decimal("9.99"),
        configuration={},
        prompt_template="Test",
        status=TemplateStatus.PUBLISHED,
        downloads_count=5,
        installations_count=4,
        revenue_total=Decimal("39.96"),
        average_rating=Decimal("5.0"),
        review_count=2
    )
    db_session.add_all([template1, template2])
    db_session.commit()

    # Login
    login_response = client.post("/api/auth/login", json={
        "email": talent_user.email,
        "password": "Test123!"
    })
    token = login_response.json()["access_token"]

    # Get dashboard
    response = client.get(
        "/api/v1/marketplace/creator/dashboard",
        headers={"Authorization": f"Bearer {token}"}
    )

    assert response.status_code == 200
    data = response.json()
    assert data["stats"]["total_templates"] == 2
    assert data["stats"]["published_templates"] == 2
    assert data["stats"]["total_downloads"] == 15
    assert data["stats"]["total_installations"] == 12
    assert Decimal(str(data["stats"]["total_revenue"])) == Decimal("39.96")


def test_creator_earnings(client, talent_user, db_session):
    """Test creator earnings endpoint."""
    # Create template with revenue
    template = AgentTemplate(
        creator_id=talent_user.id,
        name="Premium Template",
        description="Premium template",
        category=TemplateCategory.CAREER_COACH,
        price=Decimal("19.99"),
        configuration={},
        prompt_template="Test",
        status=TemplateStatus.PUBLISHED,
        revenue_total=Decimal("199.90")  # 10 purchases
    )
    db_session.add(template)
    db_session.commit()

    # Login
    login_response = client.post("/api/auth/login", json={
        "email": talent_user.email,
        "password": "Test123!"
    })
    token = login_response.json()["access_token"]

    # Get earnings
    response = client.get(
        "/api/v1/marketplace/creator/earnings",
        headers={"Authorization": f"Bearer {token}"}
    )

    assert response.status_code == 200
    data = response.json()
    assert Decimal(str(data["total_revenue"])) == Decimal("199.90")
    assert Decimal(str(data["platform_commission"])) == Decimal("39.98")  # 20%
    assert Decimal(str(data["net_earnings"])) == Decimal("159.92")  # 80%
    assert len(data["earnings_by_template"]) == 1
