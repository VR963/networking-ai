"""
Multi-Agent System with LangChain.

Implements a hierarchical multi-agent architecture where each main agent
has specialized sub-agents for specific tasks.

Architecture:
- Main Orchestrator Agent: Coordinates all operations
  - Research Agent: Gathers information and trends
  - Matching Agent: Performs profile matching
  - Security Agent: Handles privacy and security
  - Knowledge Agent: Manages learning and retrieval
  - Note Taker Agent: Documents interactions and insights
"""

from typing import List, Dict, Optional, Any
from datetime import datetime
import json

from langchain.agents import AgentExecutor, create_structured_chat_agent
from langchain.tools import Tool, StructuredTool
from langchain.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain.memory import ConversationBufferMemory
from langchain_anthropic import ChatAnthropic
from langchain.schema import HumanMessage, SystemMessage

from .rag_system import DualRAGSystem
from .knowledge_learning import KnowledgeLearningSystem
from .semantic import SemanticMatcher
from .recommender import ConnectionRecommender
from .config import config


class AgentTools:
    """Collection of tools available to agents."""

    def __init__(
        self,
        rag_system: DualRAGSystem,
        learning_system: KnowledgeLearningSystem,
        matcher: SemanticMatcher,
        recommender: ConnectionRecommender,
    ):
        """Initialize agent tools."""
        self.rag_system = rag_system
        self.learning_system = learning_system
        self.matcher = matcher
        self.recommender = recommender

    def create_research_tools(self) -> List[Tool]:
        """Create tools for research agent."""
        return [
            Tool(
                name="query_public_knowledge",
                func=lambda query: json.dumps(self.rag_system.query_public(query, n_results=3)),
                description="Query the public knowledge base for information, patterns, and insights. Input should be a search query string.",
            ),
            Tool(
                name="get_knowledge_statistics",
                func=lambda _: json.dumps(self.rag_system.get_statistics()),
                description="Get statistics about the knowledge base. No input needed.",
            ),
        ]

    def create_matching_tools(self) -> List[Tool]:
        """Create tools for matching agent."""
        def calculate_profile_similarity(input_str: str) -> str:
            """Calculate similarity between two profiles."""
            try:
                data = json.loads(input_str)
                profile1 = data.get("profile1", {})
                profile2 = data.get("profile2", {})
                scores = self.matcher.match_profiles(profile1, profile2)
                return json.dumps(scores)
            except Exception as e:
                return json.dumps({"error": str(e)})

        return [
            Tool(
                name="calculate_similarity",
                func=calculate_profile_similarity,
                description="Calculate semantic similarity between two profiles. Input must be a JSON string with 'profile1' and 'profile2' keys.",
            ),
            Tool(
                name="find_skill_matches",
                func=lambda skills_json: json.dumps(
                    self.matcher.calculate_skill_similarity(
                        json.loads(skills_json).get("skills1", []),
                        json.loads(skills_json).get("skills2", []),
                    )
                ),
                description="Calculate skill similarity. Input must be JSON with 'skills1' and 'skills2' arrays.",
            ),
        ]

    def create_security_tools(self) -> List[Tool]:
        """Create tools for security agent."""
        def check_for_pii(text: str) -> str:
            """Check text for PII."""
            from .knowledge_learning import PIIDetector

            has_pii, pii_types = PIIDetector.contains_pii(text)
            return json.dumps({"has_pii": has_pii, "pii_types": pii_types})

        def anonymize_data(text: str) -> str:
            """Anonymize PII in text."""
            from .knowledge_learning import PIIDetector

            anonymized = PIIDetector.anonymize_text(text)
            return anonymized

        return [
            Tool(
                name="check_pii",
                func=check_for_pii,
                description="Check if text contains Personally Identifiable Information (PII). Input should be text to check.",
            ),
            Tool(
                name="anonymize_text",
                func=anonymize_data,
                description="Anonymize PII in text. Input should be text to anonymize.",
            ),
        ]

    def create_knowledge_tools(self) -> List[Tool]:
        """Create tools for knowledge agent."""
        def learn_from_interaction(input_json: str) -> str:
            """Learn from a conversation interaction."""
            try:
                data = json.loads(input_json)
                result = self.learning_system.process_interaction(
                    question=data.get("question", ""),
                    answer=data.get("answer", ""),
                    user_id=data.get("user_id"),
                    user_password=data.get("user_password"),
                    metadata=data.get("metadata", {}),
                )
                return json.dumps(result)
            except Exception as e:
                return json.dumps({"error": str(e)})

        return [
            Tool(
                name="learn_from_conversation",
                func=learn_from_interaction,
                description="Learn from a conversation interaction. Input must be JSON with 'question' and 'answer' keys.",
            ),
            Tool(
                name="get_learning_stats",
                func=lambda _: json.dumps(self.learning_system.stats),
                description="Get learning system statistics. No input needed.",
            ),
        ]

    def create_note_taker_tools(self) -> List[Tool]:
        """Create tools for note taker agent."""
        notes_storage = []

        def take_note(note: str) -> str:
            """Take a note about the current interaction."""
            notes_storage.append({"note": note, "timestamp": datetime.now().isoformat()})
            return f"Note recorded: {note}"

        def get_notes(_: str = "") -> str:
            """Get all recorded notes."""
            return json.dumps(notes_storage)

        return [
            Tool(name="take_note", func=take_note, description="Record a note or observation. Input should be the note text."),
            Tool(name="get_notes", func=get_notes, description="Retrieve all recorded notes. No input needed."),
        ]


class SubAgent:
    """Base class for specialized sub-agents."""

    def __init__(
        self,
        name: str,
        role: str,
        tools: List[Tool],
        llm: Optional[ChatAnthropic] = None,
    ):
        """
        Initialize sub-agent.

        Args:
            name: Agent name
            role: Agent role/responsibility
            tools: List of tools for this agent
            llm: Language model (uses Claude if None)
        """
        self.name = name
        self.role = role
        self.tools = tools
        self.llm = llm or ChatAnthropic(model=config.DEFAULT_MODEL, temperature=config.TEMPERATURE)

    def execute(self, task: str, context: Optional[Dict] = None) -> str:
        """
        Execute a task with this agent.

        Args:
            task: Task description
            context: Optional context information

        Returns:
            Agent's response
        """
        system_prompt = f"""You are {self.name}, a specialized AI agent.
Your role: {self.role}

You have access to specific tools to accomplish your tasks.
Always use the appropriate tools when needed.
Be concise and focused in your responses."""

        messages = [
            SystemMessage(content=system_prompt),
            HumanMessage(content=task),
        ]

        if context:
            messages.insert(1, HumanMessage(content=f"Context: {json.dumps(context)}"))

        try:
            response = self.llm.invoke(messages)
            return response.content
        except Exception as e:
            return f"Error executing task: {str(e)}"


class ResearchAgent(SubAgent):
    """Agent specialized in research and information gathering."""

    def __init__(self, tools: List[Tool]):
        super().__init__(
            name="Research Agent",
            role="Gather information, analyze trends, and provide insights from the knowledge base",
            tools=tools,
        )


class MatchingAgent(SubAgent):
    """Agent specialized in profile matching and similarity analysis."""

    def __init__(self, tools: List[Tool]):
        super().__init__(
            name="Matching Agent",
            role="Analyze profile similarities, calculate match scores, and provide matching recommendations",
            tools=tools,
        )


class SecurityAgent(SubAgent):
    """Agent specialized in security and privacy protection."""

    def __init__(self, tools: List[Tool]):
        super().__init__(
            name="Security Agent",
            role="Protect user privacy, detect PII, ensure data security, and enforce access controls",
            tools=tools,
        )


class KnowledgeAgent(SubAgent):
    """Agent specialized in knowledge management and learning."""

    def __init__(self, tools: List[Tool]):
        super().__init__(
            name="Knowledge Agent",
            role="Manage knowledge base, learn from interactions, and retrieve relevant information",
            tools=tools,
        )


class NoteTakerAgent(SubAgent):
    """Agent specialized in documenting interactions and insights."""

    def __init__(self, tools: List[Tool]):
        super().__init__(
            name="Note Taker Agent",
            role="Document interactions, record insights, and maintain conversation logs",
            tools=tools,
        )


class OrchestratorAgent:
    """
    Main orchestrator agent that coordinates all sub-agents.

    This agent receives user requests and delegates tasks to appropriate
    sub-agents based on the nature of the request.
    """

    def __init__(
        self,
        rag_system: Optional[DualRAGSystem] = None,
        learning_system: Optional[KnowledgeLearningSystem] = None,
    ):
        """Initialize orchestrator agent with all sub-agents."""
        self.rag_system = rag_system or DualRAGSystem()
        self.learning_system = learning_system or KnowledgeLearningSystem(self.rag_system)

        # Initialize shared resources
        self.matcher = SemanticMatcher()
        self.recommender = ConnectionRecommender()

        # Create tools
        self.tools = AgentTools(self.rag_system, self.learning_system, self.matcher, self.recommender)

        # Initialize sub-agents
        self.research_agent = ResearchAgent(self.tools.create_research_tools())
        self.matching_agent = MatchingAgent(self.tools.create_matching_tools())
        self.security_agent = SecurityAgent(self.tools.create_security_tools())
        self.knowledge_agent = KnowledgeAgent(self.tools.create_knowledge_tools())
        self.note_taker_agent = NoteTakerAgent(self.tools.create_note_taker_tools())

        self.llm = ChatAnthropic(model=config.DEFAULT_MODEL, temperature=config.TEMPERATURE)

        self.interaction_history: List[Dict] = []

    def process_request(self, request: str, context: Optional[Dict] = None) -> Dict:
        """
        Process a user request by coordinating sub-agents.

        Args:
            request: User's request
            context: Optional context (user_id, profiles, etc.)

        Returns:
            Response dict with results from relevant agents
        """
        # Record interaction start
        interaction = {"request": request, "timestamp": datetime.now().isoformat(), "context": context}

        # Note taker records the request
        self.note_taker_agent.execute(f"User request: {request}")

        # Analyze request to determine which agents to engage
        agent_plan = self._plan_agent_coordination(request, context)

        results = {"plan": agent_plan, "agent_responses": {}}

        # Execute plan
        for step in agent_plan:
            agent_name = step["agent"]
            task = step["task"]

            if agent_name == "research":
                response = self.research_agent.execute(task, context)
                results["agent_responses"]["research"] = response
            elif agent_name == "matching":
                response = self.matching_agent.execute(task, context)
                results["agent_responses"]["matching"] = response
            elif agent_name == "security":
                response = self.security_agent.execute(task, context)
                results["agent_responses"]["security"] = response
            elif agent_name == "knowledge":
                response = self.knowledge_agent.execute(task, context)
                results["agent_responses"]["knowledge"] = response

        # Synthesize final response
        final_response = self._synthesize_response(request, results)
        results["final_response"] = final_response

        # Record interaction
        interaction["results"] = results
        self.interaction_history.append(interaction)

        # Note taker records completion
        self.note_taker_agent.execute(f"Request completed: {request[:50]}...")

        return results

    def _plan_agent_coordination(self, request: str, context: Optional[Dict]) -> List[Dict]:
        """
        Plan which agents to use and in what order.

        Args:
            request: User's request
            context: Request context

        Returns:
            List of agent coordination steps
        """
        request_lower = request.lower()
        plan = []

        # Security check for all requests with user data
        if context and context.get("user_data"):
            plan.append({"agent": "security", "task": "Check request for PII and security concerns"})

        # Research requests
        if any(word in request_lower for word in ["research", "find", "search", "information", "trends"]):
            plan.append({"agent": "research", "task": f"Research: {request}"})

        # Matching requests
        if any(word in request_lower for word in ["match", "similar", "recommend", "connection", "profile"]):
            plan.append({"agent": "matching", "task": f"Analyze matching for: {request}"})

        # Knowledge/learning requests
        if any(word in request_lower for word in ["learn", "remember", "store", "knowledge"]):
            plan.append({"agent": "knowledge", "task": f"Process knowledge: {request}"})

        # Default to research if no specific agent identified
        if not plan:
            plan.append({"agent": "research", "task": f"General inquiry: {request}"})

        return plan

    def _synthesize_response(self, request: str, results: Dict) -> str:
        """
        Synthesize final response from multiple agent outputs.

        Args:
            request: Original request
            results: Results from all agents

        Returns:
            Synthesized response
        """
        system_prompt = """You are an AI orchestrator. Synthesize the responses from specialized agents into a coherent, helpful answer.
Be concise and focus on the most relevant information."""

        agent_outputs = "\n\n".join(
            [f"{agent.upper()}:\n{response}" for agent, response in results.get("agent_responses", {}).items()]
        )

        messages = [
            SystemMessage(content=system_prompt),
            HumanMessage(content=f"Original Request: {request}\n\nAgent Outputs:\n{agent_outputs}\n\nProvide a synthesized response:"),
        ]

        try:
            response = self.llm.invoke(messages)
            return response.content
        except Exception as e:
            return f"Error synthesizing response: {str(e)}"

    def get_interaction_history(self) -> List[Dict]:
        """Get history of all interactions."""
        return self.interaction_history

    def clear_history(self):
        """Clear interaction history."""
        self.interaction_history.clear()


def create_multi_agent_system(
    rag_system: Optional[DualRAGSystem] = None,
    learning_system: Optional[KnowledgeLearningSystem] = None,
) -> OrchestratorAgent:
    """
    Factory function to create multi-agent system.

    Args:
        rag_system: Optional RAG system instance
        learning_system: Optional learning system instance

    Returns:
        Configured OrchestratorAgent
    """
    return OrchestratorAgent(rag_system=rag_system, learning_system=learning_system)
