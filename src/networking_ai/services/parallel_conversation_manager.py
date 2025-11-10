"""
Parallel Conversation Manager with Async Support.

Handles 100+ simultaneous agent-to-agent conversations using async/await.
Coordinates question generation, validation, learning, and scoring.
"""

import asyncio
from typing import Dict, List, Optional, Any, Set
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from sqlalchemy.orm import Session
from langchain_anthropic import ChatAnthropic

from ..config import config
from ..models.agent_conversation import AgentConversation
from ..models.personal_ai_agent import PersonalAIAgent
from ..models.company_admin_agent import CompanyAdminAgent
from .intelligent_question_generator import (
    IntelligentQuestionGenerator,
    QuestionContext,
    ConversationPhase,
    Question
)
from .anti_hallucination_validator import AntiHallucinationValidator
from .shared_learning_engine import SharedLearningEngine
from .mutual_ranking_system import ConversationScorer


class ConversationState(str, Enum):
    """State of a conversation."""
    PENDING = "pending"
    ACTIVE = "active"
    SCREENING = "screening"  # Phase 1
    DEEP_DIVE = "deepdive"  # Phase 2
    VERIFICATION = "verification"  # Phase 3
    COMPLETED = "completed"
    FAILED = "failed"
    STUCK = "stuck"


@dataclass
class ConversationContext:
    """Context for a single conversation."""
    conversation_id: str
    talent_agent_id: int
    company_agent_id: int
    job_id: int

    # State
    state: ConversationState = ConversationState.PENDING
    phase: ConversationPhase = ConversationPhase.SCREENING
    turn_number: int = 0

    # Conversation history
    messages: List[Dict[str, str]] = field(default_factory=list)

    # Extracted insights
    insights: Dict[str, Any] = field(default_factory=dict)

    # Scoring data
    talent_perspective: Dict[str, Any] = field(default_factory=dict)
    company_perspective: Dict[str, Any] = field(default_factory=dict)

    # Metadata
    started_at: datetime = field(default_factory=datetime.now)
    last_message_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None

    # Progress tracking
    questions_asked: int = 0
    deal_breakers_found: List[str] = field(default_factory=list)
    positive_signals: List[str] = field(default_factory=list)


class ParallelConversationManager:
    """
    Manages multiple agent-to-agent conversations in parallel.

    Uses async/await to handle 100+ simultaneous conversations efficiently.
    """

    def __init__(
        self,
        db: Session,
        chromadb_service,
        initiating_agent: PersonalAIAgent,
        agent_type: str = "talent"
    ):
        """
        Initialize parallel conversation manager.

        Args:
            db: Database session
            chromadb_service: ChromaDB service
            initiating_agent: Agent initiating conversations (talent or company)
            agent_type: "talent" or "company"
        """
        self.db = db
        self.chromadb_service = chromadb_service
        self.initiating_agent = initiating_agent
        self.agent_type = agent_type

        # Services
        self.question_generator = IntelligentQuestionGenerator()
        self.validator = AntiHallucinationValidator(chromadb_service)
        self.learning_engine = SharedLearningEngine()
        self.scorer = ConversationScorer()

        # LLM for responses
        self.llm = ChatAnthropic(
            model="claude-3-5-sonnet-20241022",
            api_key=config.anthropic_api_key,
            temperature=0.7
        )

        # Active conversations
        self.active_conversations: Dict[str, ConversationContext] = {}

        # Conversation queue
        self.conversation_queue: asyncio.Queue = asyncio.Queue()

        # Results
        self.completed_conversations: List[ConversationContext] = []
        self.failed_conversations: List[ConversationContext] = []

    async def start_conversations(
        self,
        matches: List[Dict[str, Any]],
        max_concurrent: int = 20
    ) -> List[ConversationContext]:
        """
        Start conversations with all matches in parallel waves.

        Args:
            matches: List of match dicts (agent_id, job_id, score, etc.)
            max_concurrent: Max concurrent conversations (default 20)

        Returns:
            List of completed conversation contexts
        """
        print(f"\n🚀 Starting {len(matches)} conversations in parallel...")

        # Wave 1: Top 20 (or all if < 20)
        wave1_size = min(20, len(matches))
        wave1_matches = matches[:wave1_size]

        print(f"📊 Wave 1: Starting {wave1_size} conversations...")
        wave1_results = await self._execute_wave(
            wave1_matches,
            phase=ConversationPhase.SCREENING,
            max_concurrent=max_concurrent
        )

        # Filter Wave 1 results: Keep conversations that passed screening
        passed_screening = [
            ctx for ctx in wave1_results
            if ctx.state == ConversationState.COMPLETED
            and not ctx.deal_breakers_found
        ]

        print(f"✅ Wave 1 Complete: {len(passed_screening)}/{wave1_size} passed screening")

        # If we have >= 10 strong candidates, proceed to deep dive
        if len(passed_screening) >= 10:
            top_10 = passed_screening[:10]
        else:
            # Start Wave 2 to get more candidates
            wave2_size = min(30, len(matches) - wave1_size)
            if wave2_size > 0:
                print(f"📊 Wave 2: Starting {wave2_size} additional conversations...")
                wave2_matches = matches[wave1_size:wave1_size + wave2_size]
                wave2_results = await self._execute_wave(
                    wave2_matches,
                    phase=ConversationPhase.SCREENING,
                    max_concurrent=max_concurrent
                )

                passed_screening.extend([
                    ctx for ctx in wave2_results
                    if ctx.state == ConversationState.COMPLETED
                    and not ctx.deal_breakers_found
                ])

                print(f"✅ Wave 2 Complete: {len(passed_screening)} total passed screening")

            top_10 = passed_screening[:10]

        # Phase 2: Deep Dive with top 10
        print(f"\n🔍 Phase 2: Deep dive with top {len(top_10)} candidates...")
        deepdive_results = await self._continue_conversations(
            top_10,
            phase=ConversationPhase.DEEP_DIVE,
            max_concurrent=max_concurrent
        )

        # Filter: Keep strong matches
        strong_matches = [
            ctx for ctx in deepdive_results
            if ctx.state == ConversationState.COMPLETED
        ]

        print(f"✅ Phase 2 Complete: {len(strong_matches)} strong matches")

        # Phase 3: Verification with top 5
        top_5 = strong_matches[:5]
        if top_5:
            print(f"\n✔️  Phase 3: Final verification with top {len(top_5)} candidates...")
            verification_results = await self._continue_conversations(
                top_5,
                phase=ConversationPhase.VERIFICATION,
                max_concurrent=max_concurrent
            )

            final_candidates = [
                ctx for ctx in verification_results
                if ctx.state == ConversationState.COMPLETED
            ]

            print(f"✅ Phase 3 Complete: {len(final_candidates)} final candidates")

            return final_candidates

        return strong_matches

    async def _execute_wave(
        self,
        matches: List[Dict[str, Any]],
        phase: ConversationPhase,
        max_concurrent: int
    ) -> List[ConversationContext]:
        """
        Execute a wave of conversations in parallel.

        Args:
            matches: List of matches to converse with
            phase: Conversation phase
            max_concurrent: Max concurrent conversations

        Returns:
            List of conversation contexts
        """
        # Create conversation contexts
        contexts = []
        for match in matches:
            ctx = ConversationContext(
                conversation_id=f"conv_{match['agent_id']}_{match['job_id']}_{int(datetime.now().timestamp())}",
                talent_agent_id=match.get('talent_agent_id', self.initiating_agent.id),
                company_agent_id=match.get('company_agent_id', match['agent_id']),
                job_id=match['job_id'],
                state=ConversationState.SCREENING,
                phase=phase
            )
            contexts.append(ctx)
            self.active_conversations[ctx.conversation_id] = ctx

        # Execute conversations with concurrency limit
        semaphore = asyncio.Semaphore(max_concurrent)

        async def run_with_semaphore(ctx):
            async with semaphore:
                return await self._run_conversation_phase(ctx)

        # Run all conversations
        results = await asyncio.gather(
            *[run_with_semaphore(ctx) for ctx in contexts],
            return_exceptions=True
        )

        # Filter exceptions
        completed = []
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                print(f"❌ Conversation {contexts[i].conversation_id} failed: {result}")
                contexts[i].state = ConversationState.FAILED
                self.failed_conversations.append(contexts[i])
            else:
                completed.append(result)

        return completed

    async def _continue_conversations(
        self,
        contexts: List[ConversationContext],
        phase: ConversationPhase,
        max_concurrent: int
    ) -> List[ConversationContext]:
        """
        Continue existing conversations in a new phase.

        Args:
            contexts: Existing conversation contexts
            phase: New phase to enter
            max_concurrent: Max concurrent conversations

        Returns:
            Updated conversation contexts
        """
        # Update phase for all contexts
        for ctx in contexts:
            ctx.phase = phase
            ctx.state = ConversationState.ACTIVE

        # Execute phase
        semaphore = asyncio.Semaphore(max_concurrent)

        async def run_with_semaphore(ctx):
            async with semaphore:
                return await self._run_conversation_phase(ctx)

        results = await asyncio.gather(
            *[run_with_semaphore(ctx) for ctx in contexts],
            return_exceptions=True
        )

        # Filter exceptions
        completed = []
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                print(f"❌ Conversation {contexts[i].conversation_id} failed: {result}")
                contexts[i].state = ConversationState.FAILED
            else:
                completed.append(result)

        return completed

    async def _run_conversation_phase(
        self,
        ctx: ConversationContext
    ) -> ConversationContext:
        """
        Run one phase of a conversation (2-7 turns).

        Args:
            ctx: Conversation context

        Returns:
            Updated conversation context
        """
        # Determine turns for this phase
        max_turns = {
            ConversationPhase.SCREENING: 3,
            ConversationPhase.DEEP_DIVE: 7,
            ConversationPhase.VERIFICATION: 4
        }

        phase_max_turns = max_turns.get(ctx.phase, 3)

        # Get current learnings
        learnings = self.learning_engine.get_learnings()

        # Run conversation turns
        for turn in range(phase_max_turns):
            # Generate question
            question = await self._generate_next_question(ctx, learnings)

            if not question:
                # No more questions to ask
                break

            # Send question and get response
            response = await self._send_question_get_response(ctx, question)

            if not response:
                # No response or error
                ctx.state = ConversationState.FAILED
                break

            # Add to conversation history
            ctx.messages.append({
                "role": self.agent_type,
                "content": question.text,
                "turn": ctx.turn_number
            })
            ctx.messages.append({
                "role": "other",
                "content": response,
                "turn": ctx.turn_number
            })

            ctx.turn_number += 1
            ctx.questions_asked += 1
            ctx.last_message_at = datetime.now()

            # Extract insights
            await self._extract_insights(ctx, question, response)

            # Share learning
            self.learning_engine.add_conversation_turn(
                conversation_id=ctx.conversation_id,
                turn_number=ctx.turn_number,
                question=question.text,
                response=response,
                question_purpose=question.purpose
            )

            # Check for deal breakers
            if self._check_deal_breaker(response, question):
                ctx.deal_breakers_found.append(question.purpose)
                if ctx.phase == ConversationPhase.SCREENING:
                    # Early exit in screening phase
                    ctx.state = ConversationState.COMPLETED
                    break

            # Check for positive signals
            if self._check_positive_signal(response, question):
                ctx.positive_signals.append(question.purpose)

            # Small delay to avoid rate limits
            await asyncio.sleep(0.1)

        # Mark as completed if not already failed
        if ctx.state != ConversationState.FAILED:
            ctx.state = ConversationState.COMPLETED
            ctx.completed_at = datetime.now()
            self.completed_conversations.append(ctx)

        return ctx

    async def _generate_next_question(
        self,
        ctx: ConversationContext,
        learnings: Dict[str, Any]
    ) -> Optional[Question]:
        """
        Generate next question for conversation.

        Args:
            ctx: Conversation context
            learnings: Current learnings from all conversations

        Returns:
            Question object or None
        """
        # Build question context
        question_context = QuestionContext(
            agent_type=self.agent_type,
            phase=ctx.phase,
            profile=self._get_profile_for_context(ctx),
            conversation_history=ctx.messages,
            learnings=learnings,
            insights_so_far=ctx.insights
        )

        # Generate questions
        questions = self.question_generator.generate_questions(
            context=question_context,
            num_questions=1
        )

        return questions[0] if questions else None

    async def _send_question_get_response(
        self,
        ctx: ConversationContext,
        question: Question
    ) -> Optional[str]:
        """
        Send question to other agent and get response.

        Args:
            ctx: Conversation context
            question: Question to ask

        Returns:
            Response string or None
        """
        # Get other agent's RAG
        if self.agent_type == "talent":
            other_agent = self.db.query(CompanyAdminAgent).filter(
                CompanyAdminAgent.id == ctx.company_agent_id
            ).first()
            other_rag_id = other_agent.company_rag_collection_id if other_agent else None
        else:
            other_agent = self.db.query(PersonalAIAgent).filter(
                PersonalAIAgent.id == ctx.talent_agent_id
            ).first()
            other_rag_id = other_agent.personal_rag_collection_id if other_agent else None

        if not other_rag_id:
            return None

        # Build prompt for response
        prompt = self._build_response_prompt(ctx, question, other_rag_id)

        # Generate response
        response = self.llm.invoke(prompt)
        response_text = response.content

        # Validate response against RAG (prevent hallucinations)
        other_agent_type = "company" if self.agent_type == "talent" else "talent"
        validation = self.validator.validate_message(
            message=response_text,
            agent_type=other_agent_type,
            rag_collection_id=other_rag_id,
            auto_correct=True
        )

        # Use corrected message if needed
        if not validation.is_valid and validation.corrected_message:
            response_text = validation.corrected_message

        return response_text

    def _build_response_prompt(
        self,
        ctx: ConversationContext,
        question: Question,
        rag_collection_id: str
    ) -> str:
        """Build prompt for generating response from other agent."""
        # Query RAG for relevant information
        rag_results = self.chromadb_service.query_collection(
            collection_name=rag_collection_id,
            query_texts=[question.text],
            n_results=3
        )

        rag_context = ""
        if rag_results and rag_results.get('documents'):
            rag_context = "\n".join(rag_results['documents'][0][:2])

        conversation_history = "\n".join([
            f"{msg['role']}: {msg['content']}"
            for msg in ctx.messages[-4:]  # Last 4 messages
        ])

        other_agent_type = "company" if self.agent_type == "talent" else "talent"

        prompt = f"""
You are a {other_agent_type} AI agent in a professional networking platform.

Your Knowledge Base:
{rag_context}

Previous conversation:
{conversation_history}

Question from {self.agent_type} agent:
{question.text}

Respond naturally and honestly based ONLY on your knowledge base.
- Answer the question directly
- Be conversational but professional
- If you don't have information, say so
- DO NOT make up information
- Keep response to 100-300 words

Response:
"""

        return prompt

    async def _extract_insights(
        self,
        ctx: ConversationContext,
        question: Question,
        response: str
    ):
        """Extract insights from response and update context."""
        # Simple keyword-based extraction (can be enhanced with LLM)
        insight_key = question.purpose

        ctx.insights[insight_key] = {
            "value": response[:200],  # First 200 chars
            "confidence": 0.7,
            "evidence": response,
            "question": question.text
        }

    def _check_deal_breaker(
        self,
        response: str,
        question: Question
    ) -> bool:
        """Check if response indicates a deal breaker."""
        response_lower = response.lower()

        # Check against question's disqualifying responses
        if question.disqualifying_responses:
            for disqualifying in question.disqualifying_responses:
                if disqualifying.lower() in response_lower:
                    return True

        return False

    def _check_positive_signal(
        self,
        response: str,
        question: Question
    ) -> bool:
        """Check if response contains positive signals."""
        response_lower = response.lower()

        # Check against question's expected signals
        if question.expected_signals:
            for signal in question.expected_signals:
                if signal.lower() in response_lower:
                    return True

        return False

    def _get_profile_for_context(
        self,
        ctx: ConversationContext
    ) -> Dict[str, Any]:
        """Get profile information for question generation context."""
        # This would query the actual agent profiles
        # For now, return placeholder
        return {
            "conversation_id": ctx.conversation_id,
            "phase": ctx.phase.value,
            "turn_number": ctx.turn_number
        }

    def get_statistics(self) -> Dict[str, Any]:
        """Get statistics about conversation execution."""
        return {
            "active_conversations": len(self.active_conversations),
            "completed_conversations": len(self.completed_conversations),
            "failed_conversations": len(self.failed_conversations),
            "learning_stats": self.learning_engine.get_stats()
        }
