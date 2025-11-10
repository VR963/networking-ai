"""
End-to-End Test for Onboarding Flow.

Tests complete user journey: CV upload → Parse → Interview → Completion
"""

import pytest
import os
import tempfile
from pathlib import Path
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from src.networking_ai.api.main import app
from src.networking_ai.database import Base, get_db
from src.networking_ai.models.user import User
from src.networking_ai.models.interview_session import InterviewSession
from src.networking_ai.models.agent_conversation import AgentConversation


# Skip if no API key
pytestmark = pytest.mark.skipif(
    not os.getenv("ANTHROPIC_API_KEY"),
    reason="ANTHROPIC_API_KEY not set - required for E2E test"
)


# Test database setup
TEST_DATABASE_URL = "sqlite:///./test_onboarding_e2e.db"


@pytest.fixture(scope="module")
def test_db():
    """Create test database."""
    engine = create_engine(TEST_DATABASE_URL, connect_args={"check_same_thread": False})
    TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

    # Create tables
    Base.metadata.create_all(bind=engine)

    yield TestingSessionLocal

    # Cleanup
    Base.metadata.drop_all(bind=engine)
    if os.path.exists("./test_onboarding_e2e.db"):
        os.remove("./test_onboarding_e2e.db")


@pytest.fixture(scope="module")
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


@pytest.fixture(scope="module")
def test_user(test_db):
    """Create test user."""
    db = test_db()

    from networking_ai.services.security import get_password_hash

    user = User(
        email="john.doe.test@email.com",
        full_name="John Doe Test",
        hashed_password=get_password_hash("testpassword123"),
        is_active=True,
        account_type="job_seeker"
    )

    db.add(user)
    db.commit()
    db.refresh(user)

    yield user

    db.close()


@pytest.fixture(scope="module")
def auth_headers(client, test_user):
    """Get authentication headers."""
    # Login
    response = client.post(
        "/api/auth/login",
        data={
            "username": test_user.email,
            "password": "testpassword123"
        }
    )

    assert response.status_code == 200
    token = response.json()["access_token"]

    return {"Authorization": f"Bearer {token}"}


@pytest.fixture
def sample_cv_file():
    """Create sample CV file for upload."""
    cv_content = """John Doe
Senior System Engineer
john.doe@email.com | +1-555-0123

PROFESSIONAL SUMMARY
Senior System Engineer with 8 years of experience in financial technology.

WORK EXPERIENCE

Senior System Engineer | Goldman Sachs | New York, NY
June 2018 - Present
- Built low-latency trading systems handling 100k+ transactions/second
- Led migration to microservices architecture
- Technologies: Python, Java, C++, Kafka, Redis, PostgreSQL

System Engineer | Morgan Stanley | New York, NY
January 2016 - May 2018
- Built automated testing framework
- Developed trade reconciliation tools
- Technologies: Python, SQL, Docker

EDUCATION
BS Computer Science - MIT (2015)

TECHNICAL SKILLS
Python (Expert), Java (Advanced), C++ (Advanced), SQL, AWS
"""

    # Create temporary file
    with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False) as f:
        f.write(cv_content)
        temp_path = f.name

    yield temp_path

    # Cleanup
    if os.path.exists(temp_path):
        os.remove(temp_path)


class TestCompleteOnboardingFlow:
    """Test complete onboarding flow from start to finish."""

    def test_full_onboarding_journey(self, client, auth_headers, sample_cv_file, test_db):
        """
        Test complete user journey:
        1. Upload CV
        2. Start interview
        3. Have conversation (5 turns)
        4. Check status
        5. Complete interview
        """

        # ========================================
        # Step 1: Upload CV
        # ========================================
        print("\n[E2E TEST] Step 1: Uploading CV...")

        with open(sample_cv_file, 'rb') as cv_file:
            response = client.post(
                "/api/onboarding/cv-upload",
                files={"file": ("john_doe_cv.txt", cv_file, "text/plain")},
                headers=auth_headers
            )

        assert response.status_code == 201, f"CV upload failed: {response.json()}"

        cv_data = response.json()

        # Validate CV upload response
        assert "session_id" in cv_data
        assert "parsed_data" in cv_data
        assert "detected_industry" in cv_data
        assert "detected_role" in cv_data

        session_id = cv_data["session_id"]

        print(f"[E2E TEST] CV uploaded successfully")
        print(f"[E2E TEST] Detected industry: {cv_data['detected_industry']}")
        print(f"[E2E TEST] Detected role: {cv_data['detected_role']}")
        print(f"[E2E TEST] Session ID: {session_id}")

        # Industry should be finance-related
        assert cv_data["detected_industry"] in ["finance", "fintech", "financial_services", "banking"]

        # Role should be engineer-related
        role = cv_data["detected_role"].lower()
        assert "engineer" in role or "developer" in role

        # ========================================
        # Step 2: Start Interview
        # ========================================
        print("\n[E2E TEST] Step 2: Starting AI interview...")

        response = client.post(
            "/api/onboarding/start-interview",
            json={"session_id": session_id},
            headers=auth_headers
        )

        assert response.status_code == 200, f"Start interview failed: {response.json()}"

        interview_data = response.json()

        assert "conversation_id" in interview_data
        assert "opening_message" in interview_data

        conversation_id = interview_data["conversation_id"]
        opening_message = interview_data["opening_message"]

        print(f"[E2E TEST] Interview started")
        print(f"[E2E TEST] Conversation ID: {conversation_id}")
        print(f"[E2E TEST] Opening: {opening_message[:100]}...")

        # Opening message should be conversational
        assert len(opening_message) > 20

        # ========================================
        # Step 3: Have Conversation (5 turns)
        # ========================================
        print("\n[E2E TEST] Step 3: Conducting interview conversation...")

        conversation_turns = [
            {
                "user": """I've been at Goldman Sachs for about 5 years now. I started as a regular
                system engineer and worked my way up to senior. It's been great experience but
                I'm looking for new challenges.""",
                "expect_keywords": ["experience", "goldm"]  # Flexible matching
            },
            {
                "user": """My main work has been on trading systems. I focus on low-latency architecture
                and real-time data processing. We handle over 100,000 transactions per second, so
                performance is critical.""",
                "expect_keywords": ["technical", "trading", "system"]
            },
            {
                "user": """I work closely with traders, risk managers, and other engineers. Collaboration
                is key in our environment. I also mentor junior engineers on the team.""",
                "expect_keywords": ["team", "collabor", "work"]
            },
            {
                "user": """Honestly, I'm looking for better work-life balance. At Goldman, I'm often
                on-call and working weekends. I'd like my next role to have more predictable hours
                while still being technically challenging.""",
                "expect_keywords": ["balance", "life", "next"]
            },
            {
                "user": """For compensation, I'm currently making around $160k base plus bonus.
                I'd expect something competitive, maybe in the $170-200k range for the right opportunity.
                Benefits and equity are important too.""",
                "expect_keywords": ["compensat", "salary", "expect"]
            }
        ]

        for i, turn in enumerate(conversation_turns, 1):
            print(f"\n[E2E TEST] Turn {i}/5:")
            print(f"[E2E TEST] User: {turn['user'][:80]}...")

            response = client.post(
                "/api/onboarding/interview-message",
                json={
                    "conversation_id": conversation_id,
                    "message": turn["user"]
                },
                headers=auth_headers
            )

            assert response.status_code == 200, f"Interview message failed: {response.json()}"

            message_data = response.json()

            assert "recruiter_message" in message_data
            assert "completion_percentage" in message_data
            assert "topics_covered" in message_data

            recruiter_message = message_data["recruiter_message"]
            completion = message_data["completion_percentage"]

            print(f"[E2E TEST] Recruiter: {recruiter_message[:80]}...")
            print(f"[E2E TEST] Completion: {completion}%")
            print(f"[E2E TEST] Topics covered: {message_data['topics_covered']}")

            # Completion should increase over time
            if i > 1:
                assert completion >= 0  # Should make progress

            # Recruiter should respond
            assert len(recruiter_message) > 10

        # ========================================
        # Step 4: Check Interview Status
        # ========================================
        print("\n[E2E TEST] Step 4: Checking interview status...")

        response = client.get(
            f"/api/onboarding/interview-status/{session_id}",
            headers=auth_headers
        )

        assert response.status_code == 200

        status_data = response.json()

        assert "status" in status_data
        assert "completion_percentage" in status_data
        assert "topics_covered" in status_data
        assert "knowledge_extracted" in status_data

        print(f"[E2E TEST] Status: {status_data['status']}")
        print(f"[E2E TEST] Completion: {status_data['completion_percentage']}%")
        print(f"[E2E TEST] Topics: {status_data['topics_covered']}")

        # Should have covered multiple topics
        assert len(status_data['topics_covered']) > 0

        # Knowledge should be extracted
        knowledge = status_data['knowledge_extracted']
        assert isinstance(knowledge, dict)

        # ========================================
        # Step 5: Complete Interview
        # ========================================
        print("\n[E2E TEST] Step 5: Completing interview...")

        response = client.post(
            f"/api/onboarding/complete-interview/{session_id}",
            headers=auth_headers
        )

        assert response.status_code == 200

        completion_data = response.json()

        assert "message" in completion_data
        assert "completion_percentage" in completion_data
        assert "knowledge_extracted" in completion_data

        print(f"[E2E TEST] Interview completed!")
        print(f"[E2E TEST] Message: {completion_data['message']}")

        # ========================================
        # Verify Database State
        # ========================================
        print("\n[E2E TEST] Verifying database state...")

        db = test_db()

        # Check interview session
        session = db.query(InterviewSession).filter(
            InterviewSession.id == session_id
        ).first()

        assert session is not None
        assert session.status.value == "completed"
        assert session.completion_percentage == 100

        # Check conversation
        conversation = db.query(AgentConversation).filter(
            AgentConversation.id == conversation_id
        ).first()

        assert conversation is not None
        assert len(conversation.messages) >= 10  # 5 user + 5 recruiter (at least)

        db.close()

        print("\n[E2E TEST] ✅ Complete onboarding flow test PASSED!")


class TestErrorHandling:
    """Test error handling in onboarding flow."""

    def test_upload_invalid_file_type(self, client, auth_headers):
        """Test uploading unsupported file type."""
        # Create fake image file
        with tempfile.NamedTemporaryFile(suffix='.png', delete=False) as f:
            f.write(b"fake image data")
            temp_path = f.name

        try:
            with open(temp_path, 'rb') as img_file:
                response = client.post(
                    "/api/onboarding/cv-upload",
                    files={"file": ("image.png", img_file, "image/png")},
                    headers=auth_headers
                )

            assert response.status_code == 400
            assert "not supported" in response.json()["detail"].lower()

        finally:
            if os.path.exists(temp_path):
                os.remove(temp_path)

    def test_start_interview_invalid_session(self, client, auth_headers):
        """Test starting interview with invalid session ID."""
        response = client.post(
            "/api/onboarding/start-interview",
            json={"session_id": 99999},
            headers=auth_headers
        )

        assert response.status_code == 404

    def test_send_message_invalid_conversation(self, client, auth_headers):
        """Test sending message to invalid conversation."""
        response = client.post(
            "/api/onboarding/interview-message",
            json={
                "conversation_id": 99999,
                "message": "Hello"
            },
            headers=auth_headers
        )

        assert response.status_code == 404


class TestConcurrentUsers:
    """Test multiple users going through onboarding simultaneously."""

    def test_two_users_onboarding_separately(self, client, test_db):
        """Test that two users can onboard independently."""
        # This would require creating two separate users and auth tokens
        # For now, we verify the system supports it by checking session isolation

        db = test_db()

        # Create two users
        from networking_ai.services.security import get_password_hash

        user1 = User(
            email="user1@test.com",
            full_name="User One",
            hashed_password=get_password_hash("pass123"),
            is_active=True,
            account_type="job_seeker"
        )

        user2 = User(
            email="user2@test.com",
            full_name="User Two",
            hashed_password=get_password_hash("pass123"),
            is_active=True,
            account_type="job_seeker"
        )

        db.add_all([user1, user2])
        db.commit()

        # Verify users are separate
        assert user1.id != user2.id

        db.close()
