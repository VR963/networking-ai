"""
Tests for Recruiter Agent.

Tests AI interview agent, sub-agent activation, and knowledge extraction.
"""

import pytest
import os

from src.networking_ai.agents.recruiter_agent import RecruiterAgent, create_recruiter_agent


# Skip tests if no API key available
pytestmark = pytest.mark.skipif(
    not os.getenv("ANTHROPIC_API_KEY"),
    reason="ANTHROPIC_API_KEY not set"
)


@pytest.fixture
def recruiter_training():
    """Sample recruiter training data."""
    return """
# Finance Sector Recruiting Guide

## Key Competencies
- Technical: Python, Java, C++, real-time systems
- Domain: Trading systems, risk management
- Soft skills: Attention to detail, collaboration

## Interview Questions
- Tell me about your experience with mission-critical systems
- How do you ensure data security and compliance?
- Describe a challenging technical problem you solved

## Red Flags
- Frequent job changes
- No testing/quality mentions
- Poor communication skills
"""


@pytest.fixture
def sample_parsed_cv():
    """Sample parsed CV data."""
    return {
        "contact_info": {
            "name": "John Doe",
            "email": "john.doe@email.com"
        },
        "work_history": [
            {
                "company": "Goldman Sachs",
                "title": "Senior System Engineer",
                "start_date": "2018-06",
                "end_date": "present",
                "description": "Built low-latency trading systems"
            },
            {
                "company": "Morgan Stanley",
                "title": "System Engineer",
                "start_date": "2016-01",
                "end_date": "2018-05"
            }
        ],
        "skills": {
            "technical": ["Python", "Java", "C++", "SQL", "AWS"],
            "domain": ["Trading systems", "Real-time processing"]
        },
        "education": [
            {
                "degree": "BS Computer Science",
                "school": "MIT",
                "year": 2015
            }
        ]
    }


class TestRecruiterAgentInitialization:
    """Test recruiter agent initialization."""

    def test_create_recruiter_agent(self, recruiter_training):
        """Test creating recruiter agent."""
        agent = create_recruiter_agent(
            industry="finance",
            role="system_engineer",
            recruiter_training=recruiter_training
        )

        assert isinstance(agent, RecruiterAgent)
        assert agent.industry == "finance"
        assert agent.role == "system_engineer"
        assert agent.recruiter_training == recruiter_training

    def test_agent_has_tools(self, recruiter_training):
        """Test that agent has sub-agent tools."""
        agent = create_recruiter_agent(
            industry="finance",
            role="system_engineer",
            recruiter_training=recruiter_training
        )

        # Should have 5 sub-agent tools
        assert len(agent.tools) == 5

        tool_names = [tool.name for tool in agent.tools]
        assert "analyze_psychometric" in tool_names
        assert "detect_soft_skills" in tool_names
        assert "assess_technical_depth" in tool_names
        assert "understand_motivation" in tool_names
        assert "analyze_compensation_expectations" in tool_names

    def test_agent_has_memory(self, recruiter_training):
        """Test that agent has conversation memory."""
        agent = create_recruiter_agent(
            industry="finance",
            role="system_engineer",
            recruiter_training=recruiter_training
        )

        assert agent.memory is not None
        assert agent.memory.memory_key == "chat_history"


class TestInterviewFlow:
    """Test interview conversation flow."""

    def test_start_interview(self, recruiter_training, sample_parsed_cv):
        """Test starting interview."""
        agent = create_recruiter_agent(
            industry="finance",
            role="system_engineer",
            recruiter_training=recruiter_training
        )

        opening_message = agent.start_interview(sample_parsed_cv)

        # Should return a greeting and question
        assert len(opening_message) > 20
        assert isinstance(opening_message, str)

        # Should be conversational (might mention name or company)
        # Note: AI output varies, so we just check it's not empty
        print(f"\n[TEST] Opening message: {opening_message}")

    def test_ask_question_continues_conversation(self, recruiter_training, sample_parsed_cv):
        """Test continuing interview conversation."""
        agent = create_recruiter_agent(
            industry="finance",
            role="system_engineer",
            recruiter_training=recruiter_training
        )

        # Start interview
        opening = agent.start_interview(sample_parsed_cv)
        print(f"\n[TEST] Opening: {opening}")

        # User responds
        user_response = """
        I've been working at Goldman Sachs for about 5 years now.
        My main focus has been on building low-latency trading systems.
        It's been challenging but rewarding work.
        """

        # Agent asks follow-up
        next_question = agent.ask_question(user_response)

        assert len(next_question) > 20
        assert isinstance(next_question, str)

        print(f"\n[TEST] Next question: {next_question}")

    def test_conversation_memory_persists(self, recruiter_training, sample_parsed_cv):
        """Test that conversation history is maintained."""
        agent = create_recruiter_agent(
            industry="finance",
            role="system_engineer",
            recruiter_training=recruiter_training
        )

        # Start and have a short conversation
        agent.start_interview(sample_parsed_cv)
        agent.ask_question("I work on trading systems at Goldman Sachs")
        agent.ask_question("I've been there for 5 years")

        # Check conversation history
        history = agent.get_conversation_history()

        # Should have at least 4 messages (2 from agent, 2 from user)
        assert len(history) >= 4

        # Check format
        for msg in history:
            assert "role" in msg
            assert "content" in msg
            assert msg["role"] in ["assistant", "user"]


class TestKnowledgeExtraction:
    """Test knowledge extraction from conversations."""

    def test_extract_technical_knowledge(self, recruiter_training, sample_parsed_cv):
        """Test extracting technical skills knowledge."""
        agent = create_recruiter_agent(
            industry="finance",
            role="system_engineer",
            recruiter_training=recruiter_training
        )

        agent.start_interview(sample_parsed_cv)

        # User talks about technical work
        agent.ask_question("""
        I specialize in Python and C++ for building trading systems.
        I've worked extensively with low-latency architectures and real-time data processing.
        We handle over 100,000 transactions per second.
        """)

        # Check extracted knowledge
        knowledge = agent.get_knowledge_extracted()

        # Should have technical_skills category
        assert "technical_skills" in knowledge

    def test_extract_motivation_knowledge(self, recruiter_training, sample_parsed_cv):
        """Test extracting motivation and goals."""
        agent = create_recruiter_agent(
            industry="finance",
            role="system_engineer",
            recruiter_training=recruiter_training
        )

        agent.start_interview(sample_parsed_cv)

        # User talks about career goals
        agent.ask_question("""
        I'm looking for my next role because I want more work-life balance.
        At my current job, I'm often on-call and working long hours.
        I'd love to find a company with better balance while still doing interesting technical work.
        """)

        # Check extracted knowledge
        knowledge = agent.get_knowledge_extracted()

        # Should have motivations category
        assert "motivations" in knowledge

        # Should detect work-life balance motivation
        motivations = knowledge["motivations"]
        if motivations:  # AI might store it differently
            assert "balance" in str(motivations).lower() or "work_life_balance" in str(motivations).lower()

    def test_knowledge_structure(self, recruiter_training, sample_parsed_cv):
        """Test knowledge extraction structure."""
        agent = create_recruiter_agent(
            industry="finance",
            role="system_engineer",
            recruiter_training=recruiter_training
        )

        knowledge = agent.get_knowledge_extracted()

        # Should have predefined categories
        assert "technical_skills" in knowledge
        assert "motivations" in knowledge
        assert "preferences" in knowledge
        assert "soft_skills" in knowledge
        assert "work_history_details" in knowledge


class TestSubAgentActivation:
    """Test sub-agent tool activation."""

    def test_psychometric_analysis_tool(self, recruiter_training):
        """Test psychometric analysis sub-agent."""
        agent = create_recruiter_agent(
            industry="finance",
            role="system_engineer",
            recruiter_training=recruiter_training
        )

        # Manually trigger tool (for testing)
        result = agent._psychometric_analysis("Candidate discusses work-life balance and family priorities")

        assert len(result) > 0
        assert "Psychometric analysis" in result

    def test_soft_skills_detection_tool(self, recruiter_training):
        """Test soft skills detection sub-agent."""
        agent = create_recruiter_agent(
            industry="finance",
            role="system_engineer",
            recruiter_training=recruiter_training
        )

        # Manually trigger tool
        result = agent._soft_skills_detection("Led a team of 5 engineers, collaborated with cross-functional teams")

        assert len(result) > 0
        assert "Soft skills detected" in result

        # Should update extracted knowledge
        knowledge = agent.get_knowledge_extracted()
        assert "soft_skills" in knowledge

    def test_technical_assessment_tool(self, recruiter_training):
        """Test technical assessment sub-agent."""
        agent = create_recruiter_agent(
            industry="finance",
            role="system_engineer",
            recruiter_training=recruiter_training
        )

        # Manually trigger tool
        result = agent._technical_assessment("Built distributed system handling 1M requests/sec with 99.99% uptime")

        assert len(result) > 0
        assert "Technical assessment" in result

    def test_motivation_analysis_tool(self, recruiter_training):
        """Test motivation analysis sub-agent."""
        agent = create_recruiter_agent(
            industry="finance",
            role="system_engineer",
            recruiter_training=recruiter_training
        )

        # Test work-life balance motivation
        result1 = agent._motivation_analysis("Looking for better work-life balance")
        assert "Motivation analysis" in result1

        knowledge = agent.get_knowledge_extracted()
        if knowledge["motivations"]:
            assert knowledge["motivations"].get("primary") == "work_life_balance"

        # Test career growth motivation
        result2 = agent._motivation_analysis("Want to grow my skills and take on more responsibility")
        assert "Motivation analysis" in result2


class TestCompletionTracking:
    """Test interview completion tracking."""

    def test_calculate_completion_initial(self, recruiter_training):
        """Test initial completion is 0%."""
        agent = create_recruiter_agent(
            industry="finance",
            role="system_engineer",
            recruiter_training=recruiter_training
        )

        completion = agent.calculate_completion()
        assert completion == 0

    def test_calculate_completion_progresses(self, recruiter_training):
        """Test completion increases as topics are covered."""
        agent = create_recruiter_agent(
            industry="finance",
            role="system_engineer",
            recruiter_training=recruiter_training
        )

        # Trigger some sub-agents to populate knowledge
        agent._technical_assessment("Python expert")
        agent._motivation_analysis("Want growth")

        completion = agent.calculate_completion()

        # Should be > 0 now that we've covered some topics
        assert completion > 0
        assert completion <= 100

    def test_completion_based_on_knowledge_categories(self, recruiter_training):
        """Test that completion is based on knowledge categories."""
        agent = create_recruiter_agent(
            industry="finance",
            role="system_engineer",
            recruiter_training=recruiter_training
        )

        # Cover all required topics
        agent._technical_assessment("Technical depth")
        agent._motivation_analysis("Career growth")
        agent._soft_skills_detection("Team collaboration")
        agent._compensation_analysis("Salary expectations")

        completion = agent.calculate_completion()

        # Should be high since we covered multiple topics
        # Note: May not be 100% if there are other required topics
        assert completion >= 50


class TestConversationHistory:
    """Test conversation history retrieval."""

    def test_get_conversation_history_format(self, recruiter_training, sample_parsed_cv):
        """Test conversation history format."""
        agent = create_recruiter_agent(
            industry="finance",
            role="system_engineer",
            recruiter_training=recruiter_training
        )

        agent.start_interview(sample_parsed_cv)
        agent.ask_question("I work on trading systems")

        history = agent.get_conversation_history()

        # Check format
        assert isinstance(history, list)
        assert len(history) > 0

        for msg in history:
            assert isinstance(msg, dict)
            assert "role" in msg
            assert "content" in msg
            assert msg["role"] in ["assistant", "user"]
            assert isinstance(msg["content"], str)
