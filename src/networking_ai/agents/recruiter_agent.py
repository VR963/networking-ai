"""
Recruiter Agent.

AI agent that interviews users to learn about them beyond their CV.
Uses industry-specific training from Master RAG.
"""

import os
from typing import Dict, List, Optional
from langchain.agents import AgentExecutor, create_tool_calling_agent
from langchain_anthropic import ChatAnthropic
from langchain.memory import ConversationBufferMemory
from langchain.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain.tools import Tool


class RecruiterAgent:
    """
    Recruiter Agent for conducting user interviews.

    Learns about users through natural conversation, activates sub-agents
    as needed, and builds a comprehensive understanding of the candidate.
    """

    def __init__(
        self,
        industry: str,
        role: str,
        recruiter_training: str,
        anthropic_api_key: Optional[str] = None
    ):
        """
        Initialize Recruiter Agent.

        Args:
            industry: Detected industry (e.g., "finance", "tech")
            role: Detected role (e.g., "system_engineer")
            recruiter_training: Training guide from Master RAG
            anthropic_api_key: Anthropic API key
        """
        self.industry = industry
        self.role = role
        self.recruiter_training = recruiter_training

        api_key = anthropic_api_key or os.getenv("ANTHROPIC_API_KEY")

        if not api_key:
            raise ValueError("Anthropic API key required")

        # Initialize Claude
        self.llm = ChatAnthropic(
            model="claude-3-5-sonnet-20241022",
            api_key=api_key,
            temperature=0.7  # Slightly creative for natural conversation
        )

        # Conversation memory
        self.memory = ConversationBufferMemory(
            memory_key="chat_history",
            return_messages=True
        )

        # Tools (sub-agents will be added as tools)
        self.tools = self._create_tools()

        # Create agent
        self.agent = self._create_agent()

        # Knowledge extracted during conversation
        self.extracted_knowledge = {
            "technical_skills": {},
            "motivations": {},
            "preferences": {},
            "soft_skills": {},
            "work_history_details": []
        }

        # Topics covered
        self.topics_covered = []

    def _create_tools(self) -> List[Tool]:
        """
        Create tools for the recruiter agent.

        These represent sub-agent capabilities that can be invoked.
        """
        return [
            Tool(
                name="analyze_psychometric",
                func=self._psychometric_analysis,
                description="""Analyze candidate's personality traits, communication style, and life stage.
                Use when candidate discusses personal life, values, or communication preferences.
                Input: Relevant conversation context."""
            ),
            Tool(
                name="detect_soft_skills",
                func=self._soft_skills_detection,
                description="""Detect soft skills like collaboration, leadership, and communication.
                Use when candidate describes team experiences or interpersonal situations.
                Input: Description of team/interpersonal experience."""
            ),
            Tool(
                name="assess_technical_depth",
                func=self._technical_assessment,
                description="""Assess technical depth and problem-solving ability.
                Use when candidate discusses complex technical challenges.
                Input: Technical discussion context."""
            ),
            Tool(
                name="understand_motivation",
                func=self._motivation_analysis,
                description="""Understand candidate's motivations and career goals.
                Use when candidate discusses what they want in their next role.
                Input: Motivation-related conversation."""
            ),
            Tool(
                name="analyze_compensation_expectations",
                func=self._compensation_analysis,
                description="""Analyze compensation expectations and priorities.
                Use when candidate mentions salary, benefits, or compensation.
                Input: Compensation discussion context."""
            )
        ]

    def _psychometric_analysis(self, context: str) -> str:
        """Sub-agent: Psychometric analysis."""
        # Store activation
        self.extracted_knowledge["soft_skills"]["communication_style"] = "analyzing..."

        return f"Psychometric analysis: Candidate shows {context}. Note: life stage and personality traits recorded."

    def _soft_skills_detection(self, context: str) -> str:
        """Sub-agent: Soft skills detection."""
        # Store activation
        if "team" in context.lower():
            self.extracted_knowledge["soft_skills"]["collaboration"] = "strong"

        return f"Soft skills detected: {context}. Collaboration and teamwork abilities noted."

    def _technical_assessment(self, context: str) -> str:
        """Sub-agent: Technical assessment."""
        # Store activation
        self.extracted_knowledge["technical_skills"]["depth"] = "experienced"

        return f"Technical assessment: {context}. Technical depth and problem-solving capability recorded."

    def _motivation_analysis(self, context: str) -> str:
        """Sub-agent: Motivation analysis."""
        # Extract motivations
        if "balance" in context.lower():
            self.extracted_knowledge["motivations"]["primary"] = "work_life_balance"
        elif "growth" in context.lower():
            self.extracted_knowledge["motivations"]["primary"] = "career_growth"

        return f"Motivation analysis: {context}. Career goals and motivations documented."

    def _compensation_analysis(self, context: str) -> str:
        """Sub-agent: Compensation analysis."""
        # Store compensation data
        self.extracted_knowledge["preferences"]["compensation_priority"] = "high"

        return f"Compensation analysis: {context}. Salary expectations and benefits priorities noted."

    def _create_agent(self) -> AgentExecutor:
        """Create the LangChain agent."""

        # System prompt
        system_prompt = f"""You are an expert recruiter conducting an interview with a candidate.

**Your Goal**: Learn about the candidate beyond their CV through natural, conversational questions.

**Industry**: {self.industry}
**Role**: {self.role}

**Recruiter Training**:
{self.recruiter_training[:2000]}  # First 2000 chars

**Interview Strategy**:
1. Start with open-ended questions about their experience
2. Probe deeper based on their answers
3. Use the tools (sub-agents) to analyze specific aspects:
   - Use `analyze_psychometric` when they discuss personal life or communication style
   - Use `detect_soft_skills` when they describe team experiences
   - Use `assess_technical_depth` for complex technical discussions
   - Use `understand_motivation` when they talk about career goals
   - Use `analyze_compensation_expectations` for salary discussions

4. Ask follow-up questions to clarify and deepen understanding
5. Be conversational, not interrogative
6. Show genuine interest in their responses
7. Don't ask yes/no questions - ask open-ended questions

**Topics to Cover** (naturally, not a checklist):
- Technical skills and depth
- Past projects and challenges
- Team collaboration and soft skills
- Career motivations and goals
- Work-life balance preferences
- Compensation expectations
- Company stage/culture preferences

**Style**: Professional but friendly. Make the candidate comfortable.

**Important**: You're building a comprehensive understanding of who they are, not just what's on their CV."""

        prompt = ChatPromptTemplate.from_messages([
            ("system", system_prompt),
            MessagesPlaceholder(variable_name="chat_history"),
            ("human", "{input}"),
            MessagesPlaceholder(variable_name="agent_scratchpad"),
        ])

        # Create agent
        agent = create_tool_calling_agent(self.llm, self.tools, prompt)

        # Create executor
        agent_executor = AgentExecutor(
            agent=agent,
            tools=self.tools,
            memory=self.memory,
            verbose=True,
            max_iterations=3,  # Limit tool use per turn
            handle_parsing_errors=True
        )

        return agent_executor

    def start_interview(self, parsed_cv: Dict) -> str:
        """
        Start the interview with opening message.

        Args:
            parsed_cv: Parsed CV data

        Returns:
            Opening message from recruiter
        """
        # Extract key info from CV for context
        name = parsed_cv.get('contact_info', {}).get('name', 'there')
        recent_job = parsed_cv.get('work_history', [{}])[0]
        company = recent_job.get('company', 'your previous company')
        title = recent_job.get('title', 'your role')

        opening_context = f"""The candidate's name is {name}. They most recently worked as {title} at {company}.

Their CV shows {len(parsed_cv.get('work_history', []))} jobs and skills including {', '.join(parsed_cv.get('skills', {}).get('technical', [])[:5])}.

Start the interview by greeting them and asking an open-ended question about their recent experience."""

        response = self.agent.invoke({"input": opening_context})

        return response.get("output", "Hi! Let's chat about your background.")

    def ask_question(self, user_response: str) -> str:
        """
        Continue the interview conversation.

        Args:
            user_response: User's answer to previous question

        Returns:
            Next question from recruiter
        """
        response = self.agent.invoke({"input": user_response})

        return response.get("output", "Tell me more about that.")

    def get_knowledge_extracted(self) -> Dict:
        """Get all knowledge extracted during interview."""
        return self.extracted_knowledge

    def get_conversation_history(self) -> List[Dict]:
        """Get conversation history."""
        messages = self.memory.chat_memory.messages

        history = []
        for msg in messages:
            history.append({
                "role": "assistant" if msg.type == "ai" else "user",
                "content": msg.content
            })

        return history

    def calculate_completion(self) -> int:
        """
        Calculate interview completion percentage.

        Returns:
            Completion percentage (0-100)
        """
        required_topics = [
            "technical_skills",
            "motivations",
            "preferences",
            "soft_skills"
        ]

        covered = sum(1 for topic in required_topics if self.extracted_knowledge.get(topic))

        return int((covered / len(required_topics)) * 100)


# Factory function
def create_recruiter_agent(
    industry: str,
    role: str,
    recruiter_training: str,
    anthropic_api_key: Optional[str] = None
) -> RecruiterAgent:
    """
    Create Recruiter Agent instance.

    Args:
        industry: Detected industry
        role: Detected role
        recruiter_training: Training from Master RAG
        anthropic_api_key: Optional API key

    Returns:
        RecruiterAgent instance
    """
    return RecruiterAgent(
        industry=industry,
        role=role,
        recruiter_training=recruiter_training,
        anthropic_api_key=anthropic_api_key
    )
