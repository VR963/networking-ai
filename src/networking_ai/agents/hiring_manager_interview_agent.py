"""
Hiring Manager Interview Agent.

AI agent that interviews hiring managers to learn about their:
- Hiring style and preferences
- Team composition and needs
- Technical requirements
- Cultural values
- Decision-making process

Populates BOTH:
- Personal HM Agent RAG (portable)
- Company Admin Agent RAG (persistent)
"""

import os
from typing import Dict, List, Optional
from langchain.agents import AgentExecutor, create_openai_tools_agent
from langchain_anthropic import ChatAnthropic
from langchain.memory import ConversationBufferMemory
from langchain.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain.tools import Tool


class HiringManagerInterviewAgent:
    """
    Interview agent for hiring managers.

    Learns about hiring managers' style, preferences, and team needs through
    natural conversation. Builds knowledge for both personal and company RAG.
    """

    def __init__(
        self,
        company_name: str,
        industry: str,
        anthropic_api_key: Optional[str] = None
    ):
        """
        Initialize Hiring Manager Interview Agent.

        Args:
            company_name: Company name
            industry: Industry (e.g., "technology", "finance")
            anthropic_api_key: Anthropic API key
        """
        self.company_name = company_name
        self.industry = industry

        api_key = anthropic_api_key or os.getenv("ANTHROPIC_API_KEY")

        if not api_key:
            raise ValueError("Anthropic API key required")

        # Initialize Claude
        self.llm = ChatAnthropic(
            model="claude-3-5-sonnet-20241022",
            api_key=api_key,
            temperature=0.7
        )

        # Conversation memory
        self.memory = ConversationBufferMemory(
            memory_key="chat_history",
            return_messages=True
        )

        # Tools
        self.tools = self._create_tools()

        # Create agent
        self.agent = self._create_agent()

        # Knowledge extracted during conversation
        self.extracted_knowledge = {
            "profile": {},
            "hiring_preferences": {},
            "hiring_style": {},
            "team_info": {},
            "technical_requirements": {},
            "cultural_values": {},
            "decision_criteria": {}
        }

        # Topics covered
        self.topics_covered = []

        # Completion percentage
        self.completion_percentage = 0

    def _create_tools(self) -> List[Tool]:
        """Create tools for the HM interview agent."""
        return [
            Tool(
                name="analyze_hiring_style",
                func=self._analyze_hiring_style,
                description="""Analyze hiring manager's interviewing and decision-making style.
                Use when they describe their interview process or how they evaluate candidates.
                Input: Description of their hiring approach."""
            ),
            Tool(
                name="extract_team_needs",
                func=self._extract_team_needs,
                description="""Extract information about team composition and hiring needs.
                Use when they discuss current team, gaps, or future growth plans.
                Input: Team description or hiring needs."""
            ),
            Tool(
                name="identify_technical_requirements",
                func=self._identify_technical_requirements,
                description="""Identify technical skills and experience requirements.
                Use when they mention specific technologies, tools, or technical expertise needed.
                Input: Technical requirements description."""
            ),
            Tool(
                name="capture_cultural_values",
                func=self._capture_cultural_values,
                description="""Capture company culture and values important for hiring.
                Use when they discuss team culture, work environment, or desired candidate traits.
                Input: Cultural values or team environment description."""
            )
        ]

    def _analyze_hiring_style(self, context: str) -> str:
        """Analyze hiring style from conversation context."""
        # Extract hiring style information
        prompt = f"""Analyze this hiring manager's style from the following context:

{context}

Extract:
1. Interview approach (structured, conversational, technical deep-dive, etc.)
2. Decision-making process (collaborative, individual, data-driven, gut feeling, etc.)
3. Communication style with candidates
4. Time to decision (fast, thorough, etc.)

Return in JSON format."""

        response = self.llm.invoke(prompt)

        # Update knowledge
        self.extracted_knowledge["hiring_style"].update({
            "raw_context": context,
            "analysis": response.content
        })

        if "hiring_style" not in self.topics_covered:
            self.topics_covered.append("hiring_style")
            self._update_completion()

        return "Hiring style analyzed and recorded."

    def _extract_team_needs(self, context: str) -> str:
        """Extract team composition and needs."""
        prompt = f"""Extract team information from this context:

{context}

Extract:
1. Current team size
2. Team structure (roles, seniority levels)
3. Current gaps or needs
4. Growth plans
5. Team dynamics

Return in JSON format."""

        response = self.llm.invoke(prompt)

        self.extracted_knowledge["team_info"].update({
            "raw_context": context,
            "analysis": response.content
        })

        if "team_info" not in self.topics_covered:
            self.topics_covered.append("team_info")
            self._update_completion()

        return "Team needs extracted and recorded."

    def _identify_technical_requirements(self, context: str) -> str:
        """Identify technical requirements."""
        prompt = f"""Extract technical requirements from this context:

{context}

Extract:
1. Required technologies/tools
2. Required experience level
3. Must-have skills
4. Nice-to-have skills
5. Domain knowledge needed

Return in JSON format."""

        response = self.llm.invoke(prompt)

        self.extracted_knowledge["technical_requirements"].update({
            "raw_context": context,
            "analysis": response.content
        })

        if "technical_requirements" not in self.topics_covered:
            self.topics_covered.append("technical_requirements")
            self._update_completion()

        return "Technical requirements identified and recorded."

    def _capture_cultural_values(self, context: str) -> str:
        """Capture cultural values and team culture."""
        prompt = f"""Extract cultural values from this context:

{context}

Extract:
1. Company values
2. Team culture
3. Work environment (remote, hybrid, office)
4. Desired candidate traits (beyond technical)
5. Red flags or deal-breakers

Return in JSON format."""

        response = self.llm.invoke(prompt)

        self.extracted_knowledge["cultural_values"].update({
            "raw_context": context,
            "analysis": response.content
        })

        if "cultural_values" not in self.topics_covered:
            self.topics_covered.append("cultural_values")
            self._update_completion()

        return "Cultural values captured and recorded."

    def _update_completion(self):
        """Update completion percentage based on topics covered."""
        required_topics = [
            "hiring_style",
            "team_info",
            "technical_requirements",
            "cultural_values",
            "profile"
        ]

        covered_count = len([t for t in required_topics if t in self.topics_covered])
        self.completion_percentage = int((covered_count / len(required_topics)) * 100)

    def _create_agent(self) -> AgentExecutor:
        """Create the interview agent."""

        prompt = ChatPromptTemplate.from_messages([
            ("system", """You are an experienced talent acquisition specialist conducting an interview with a hiring manager.

Your goal is to understand:
1. Their hiring style and preferences
2. Team composition and needs
3. Technical requirements for roles
4. Cultural values and team fit criteria
5. Decision-making process

Company: {company_name}
Industry: {industry}

Guidelines:
- Ask open-ended questions
- Listen actively and dig deeper based on responses
- Be conversational and friendly
- Cover all key topics naturally
- Use the tools to extract and record information

Start by introducing yourself and asking about their role and team."""),
            MessagesPlaceholder(variable_name="chat_history"),
            ("user", "{input}"),
            MessagesPlaceholder(variable_name="agent_scratchpad"),
        ])

        agent = create_openai_tools_agent(
            llm=self.llm,
            tools=self.tools,
            prompt=prompt
        )

        return AgentExecutor(
            agent=agent,
            tools=self.tools,
            memory=self.memory,
            verbose=True,
            max_iterations=5,
            handle_parsing_errors=True
        )

    def start_interview(self) -> str:
        """Start the interview with opening message."""
        opening_message = self.agent.invoke({
            "input": "Hello! I'm ready to start the interview.",
            "company_name": self.company_name,
            "industry": self.industry
        })

        return opening_message["output"]

    def send_message(self, message: str) -> Dict:
        """
        Send a message and get response.

        Args:
            message: User's message

        Returns:
            Dict with response and progress info
        """
        response = self.agent.invoke({
            "input": message,
            "company_name": self.company_name,
            "industry": self.industry
        })

        return {
            "message": response["output"],
            "completion_percentage": self.completion_percentage,
            "topics_covered": self.topics_covered,
            "is_complete": self.completion_percentage >= 80
        }

    def get_extracted_knowledge(self) -> Dict:
        """Get all extracted knowledge."""
        return self.extracted_knowledge

    def is_interview_complete(self) -> bool:
        """Check if interview is complete (80%+ topics covered)."""
        return self.completion_percentage >= 80


def create_hiring_manager_interview_agent(
    company_name: str,
    industry: str,
    anthropic_api_key: Optional[str] = None
) -> HiringManagerInterviewAgent:
    """
    Factory function to create a HM interview agent.

    Args:
        company_name: Company name
        industry: Industry
        anthropic_api_key: Anthropic API key

    Returns:
        HiringManagerInterviewAgent instance
    """
    return HiringManagerInterviewAgent(
        company_name=company_name,
        industry=industry,
        anthropic_api_key=anthropic_api_key
    )
