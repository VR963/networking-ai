"""
Conversation Orchestrator - Main entry point for agent-to-agent conversations.

Coordinates the entire process:
1. Find matching candidates/jobs (100+)
2. Execute conversations in parallel (100 → 20 → 10 → 3)
3. Apply learning across conversations
4. Rank and select TOP 3 matches
5. Present to user for meeting scheduling
"""

import asyncio
from typing import Dict, List, Optional, Any
from dataclasses import dataclass
from datetime import datetime
from sqlalchemy.orm import Session

from ..models.personal_ai_agent import PersonalAIAgent
from ..models.company_admin_agent import CompanyAdminAgent
from ..models.job import Job
from ..models.match import Match
from .parallel_conversation_manager import ParallelConversationManager, ConversationContext
from .mutual_ranking_system import MutualRankingSystem, MutualMatch
from .agent_matching_service import AgentMatchingService


@dataclass
class OrchestrationResult:
    """Result of full orchestration process."""
    initiating_agent_id: int
    agent_type: str  # "talent" or "company"

    # Execution metrics
    total_matches_found: int
    conversations_started: int
    conversations_completed: int
    conversations_failed: int
    execution_time_seconds: float

    # Results
    top_3_matches: List[MutualMatch]
    all_ranked_matches: List[MutualMatch]

    # Learning insights
    patterns_detected: List[str]
    recommendations: List[str]

    # Timestamp
    completed_at: datetime


class ConversationOrchestrator:
    """
    Main orchestrator for agent-to-agent conversations.

    Entry point for the entire matching process:
    - Talent agent searches for jobs
    - Company agent searches for candidates
    - Conducts parallel conversations
    - Learns and optimizes in real-time
    - Returns TOP 3 mutual matches
    """

    def __init__(
        self,
        db: Session,
        chromadb_service,
        matching_service: Optional[AgentMatchingService] = None
    ):
        """
        Initialize conversation orchestrator.

        Args:
            db: Database session
            chromadb_service: ChromaDB service
            matching_service: Optional matching service for finding candidates
        """
        self.db = db
        self.chromadb_service = chromadb_service
        self.matching_service = matching_service or AgentMatchingService(db, chromadb_service)
        self.ranking_system = MutualRankingSystem()

    async def find_top_3_matches_for_talent(
        self,
        talent_agent: PersonalAIAgent,
        max_conversations: int = 100,
        max_concurrent: int = 20
    ) -> OrchestrationResult:
        """
        Find TOP 3 jobs for a talent agent.

        Process:
        1. Search for relevant jobs (semantic + filters)
        2. Find up to 100 matching jobs
        3. Conduct parallel conversations with company agents
        4. Learn and optimize during process
        5. Rank all conversations
        6. Select TOP 3 mutual matches

        Args:
            talent_agent: Talent agent searching for jobs
            max_conversations: Max conversations to conduct (default 100)
            max_concurrent: Max concurrent conversations (default 20)

        Returns:
            OrchestrationResult with TOP 3 matches
        """
        start_time = datetime.now()

        print(f"\n{'='*60}")
        print(f"🎯 TALENT AGENT SEARCH")
        print(f"{'='*60}")
        print(f"Agent ID: {talent_agent.id}")
        print(f"User ID: {talent_agent.user_id}")
        print(f"Industry: {talent_agent.industry}")
        print(f"Role: {talent_agent.role}")
        print(f"{'='*60}\n")

        # Step 1: Find matching jobs
        print("🔍 Step 1: Finding matching jobs...")
        matching_jobs = await self._find_matching_jobs(
            talent_agent,
            limit=max_conversations
        )

        print(f"✅ Found {len(matching_jobs)} matching jobs")

        if not matching_jobs:
            return self._create_empty_result(
                talent_agent.id,
                "talent",
                start_time,
                "No matching jobs found"
            )

        # Step 2: Prepare conversation targets
        conversation_targets = []
        for job_match in matching_jobs:
            conversation_targets.append({
                "talent_agent_id": talent_agent.id,
                "agent_id": job_match["company_agent_id"],
                "company_agent_id": job_match["company_agent_id"],
                "job_id": job_match["job_id"],
                "match_score": job_match["match_score"],
                "job_title": job_match.get("job_title", ""),
                "company_name": job_match.get("company_name", "")
            })

        # Step 3: Execute parallel conversations
        print(f"\n💬 Step 2: Conducting conversations...")
        conversation_manager = ParallelConversationManager(
            db=self.db,
            chromadb_service=self.chromadb_service,
            initiating_agent=talent_agent,
            agent_type="talent"
        )

        completed_conversations = await conversation_manager.start_conversations(
            matches=conversation_targets,
            max_concurrent=max_concurrent
        )

        print(f"\n✅ Conversations complete!")
        print(f"   Completed: {len(completed_conversations)}")
        print(f"   Failed: {len(conversation_manager.failed_conversations)}")

        # Step 4: Rank conversations
        print(f"\n📊 Step 3: Ranking conversations...")
        ranked_matches = await self._rank_conversations(
            completed_conversations,
            conversation_targets
        )

        print(f"✅ Ranked {len(ranked_matches)} conversations")

        # Step 5: Select TOP 3
        top_3 = self.ranking_system.select_top_3(ranked_matches)

        print(f"\n🎯 TOP 3 MATCHES:")
        for i, match in enumerate(top_3, 1):
            print(f"   {i}. {match.mutual_score:.1f}/100 - "
                  f"Job ID {match.job_id}")

        # Step 6: Get learning insights
        learning_stats = conversation_manager.learning_engine.get_stats()
        learnings = conversation_manager.learning_engine.get_learnings()

        # Calculate execution time
        execution_time = (datetime.now() - start_time).total_seconds()

        # Create result
        result = OrchestrationResult(
            initiating_agent_id=talent_agent.id,
            agent_type="talent",
            total_matches_found=len(matching_jobs),
            conversations_started=len(conversation_targets),
            conversations_completed=len(completed_conversations),
            conversations_failed=len(conversation_manager.failed_conversations),
            execution_time_seconds=execution_time,
            top_3_matches=top_3,
            all_ranked_matches=ranked_matches,
            patterns_detected=learnings.get("recommendations", []),
            recommendations=learnings.get("recommendations", []),
            completed_at=datetime.now()
        )

        print(f"\n{'='*60}")
        print(f"✅ ORCHESTRATION COMPLETE")
        print(f"{'='*60}")
        print(f"Execution Time: {execution_time:.1f}s")
        print(f"TOP 3 Selected: {len(top_3)}")
        print(f"{'='*60}\n")

        return result

    async def find_top_3_candidates_for_company(
        self,
        company_agent: CompanyAdminAgent,
        job_id: int,
        max_conversations: int = 100,
        max_concurrent: int = 20
    ) -> OrchestrationResult:
        """
        Find TOP 3 candidates for a company's job posting.

        Process:
        1. Search for relevant candidates (semantic + filters)
        2. Find up to 100 matching candidates
        3. Conduct parallel conversations with talent agents
        4. Learn and optimize during process
        5. Rank all conversations
        6. Select TOP 3 mutual matches

        Args:
            company_agent: Company agent searching for candidates
            job_id: Job posting ID
            max_conversations: Max conversations to conduct (default 100)
            max_concurrent: Max concurrent conversations (default 20)

        Returns:
            OrchestrationResult with TOP 3 candidates
        """
        start_time = datetime.now()

        print(f"\n{'='*60}")
        print(f"🎯 COMPANY AGENT SEARCH")
        print(f"{'='*60}")
        print(f"Agent ID: {company_agent.id}")
        print(f"Company ID: {company_agent.company_id}")
        print(f"Job ID: {job_id}")
        print(f"{'='*60}\n")

        # Step 1: Find matching candidates
        print("🔍 Step 1: Finding matching candidates...")
        matching_candidates = await self._find_matching_candidates(
            company_agent,
            job_id,
            limit=max_conversations
        )

        print(f"✅ Found {len(matching_candidates)} matching candidates")

        if not matching_candidates:
            return self._create_empty_result(
                company_agent.id,
                "company",
                start_time,
                "No matching candidates found"
            )

        # Step 2: Prepare conversation targets
        conversation_targets = []
        for candidate_match in matching_candidates:
            conversation_targets.append({
                "company_agent_id": company_agent.id,
                "agent_id": candidate_match["talent_agent_id"],
                "talent_agent_id": candidate_match["talent_agent_id"],
                "job_id": job_id,
                "match_score": candidate_match["match_score"]
            })

        # Step 3: Execute parallel conversations
        print(f"\n💬 Step 2: Conducting conversations...")
        conversation_manager = ParallelConversationManager(
            db=self.db,
            chromadb_service=self.chromadb_service,
            initiating_agent=company_agent,
            agent_type="company"
        )

        completed_conversations = await conversation_manager.start_conversations(
            matches=conversation_targets,
            max_concurrent=max_concurrent
        )

        print(f"\n✅ Conversations complete!")
        print(f"   Completed: {len(completed_conversations)}")
        print(f"   Failed: {len(conversation_manager.failed_conversations)}")

        # Step 4: Rank conversations
        print(f"\n📊 Step 3: Ranking conversations...")
        ranked_matches = await self._rank_conversations(
            completed_conversations,
            conversation_targets
        )

        print(f"✅ Ranked {len(ranked_matches)} conversations")

        # Step 5: Select TOP 3
        top_3 = self.ranking_system.select_top_3(ranked_matches)

        print(f"\n🎯 TOP 3 CANDIDATES:")
        for i, match in enumerate(top_3, 1):
            print(f"   {i}. {match.mutual_score:.1f}/100 - "
                  f"Talent Agent ID {match.talent_agent_id}")

        # Step 6: Get learning insights
        learning_stats = conversation_manager.learning_engine.get_stats()
        learnings = conversation_manager.learning_engine.get_learnings()

        # Calculate execution time
        execution_time = (datetime.now() - start_time).total_seconds()

        # Create result
        result = OrchestrationResult(
            initiating_agent_id=company_agent.id,
            agent_type="company",
            total_matches_found=len(matching_candidates),
            conversations_started=len(conversation_targets),
            conversations_completed=len(completed_conversations),
            conversations_failed=len(conversation_manager.failed_conversations),
            execution_time_seconds=execution_time,
            top_3_matches=top_3,
            all_ranked_matches=ranked_matches,
            patterns_detected=learnings.get("recommendations", []),
            recommendations=learnings.get("recommendations", []),
            completed_at=datetime.now()
        )

        print(f"\n{'='*60}")
        print(f"✅ ORCHESTRATION COMPLETE")
        print(f"{'='*60}")
        print(f"Execution Time: {execution_time:.1f}s")
        print(f"TOP 3 Selected: {len(top_3)}")
        print(f"{'='*60}\n")

        return result

    async def _find_matching_jobs(
        self,
        talent_agent: PersonalAIAgent,
        limit: int
    ) -> List[Dict[str, Any]]:
        """
        Find matching jobs for talent agent.

        Uses semantic search + filters.

        Args:
            talent_agent: Talent agent
            limit: Max number of jobs to return

        Returns:
            List of matching job dicts
        """
        # Get agent's preferences from RAG
        preferences_query = "What kind of jobs and companies is this user looking for?"
        rag_results = self.chromadb_service.query_collection(
            collection_name=talent_agent.personal_rag_collection_id,
            query_texts=[preferences_query],
            n_results=5
        )

        # Extract preferences (simplified)
        # In production, this would be more sophisticated
        search_query = f"{talent_agent.role} in {talent_agent.industry}"

        # Query active jobs
        jobs = self.db.query(Job).filter(
            Job.status == "active"
        ).limit(limit * 2).all()  # Get 2x to account for filtering

        # Score and rank jobs
        matching_jobs = []
        for job in jobs[:limit]:
            # Get company agent
            company_agent = self.db.query(CompanyAdminAgent).filter(
                CompanyAdminAgent.company_id == job.company_id
            ).first()

            if company_agent:
                matching_jobs.append({
                    "job_id": job.id,
                    "company_agent_id": company_agent.id,
                    "match_score": 0.85,  # Placeholder - would calculate actual score
                    "job_title": job.title,
                    "company_name": job.company.company_name if job.company else "Unknown"
                })

        return matching_jobs[:limit]

    async def _find_matching_candidates(
        self,
        company_agent: CompanyAdminAgent,
        job_id: int,
        limit: int
    ) -> List[Dict[str, Any]]:
        """
        Find matching candidates for job.

        Uses semantic search + filters.

        Args:
            company_agent: Company agent
            job_id: Job ID
            limit: Max number of candidates to return

        Returns:
            List of matching candidate dicts
        """
        # Get job details
        job = self.db.query(Job).filter(Job.id == job_id).first()

        if not job:
            return []

        # Query active talent agents
        talent_agents = self.db.query(PersonalAIAgent).filter(
            PersonalAIAgent.status == "active"
        ).limit(limit * 2).all()

        # Score and rank candidates
        matching_candidates = []
        for agent in talent_agents[:limit]:
            matching_candidates.append({
                "talent_agent_id": agent.id,
                "match_score": 0.85,  # Placeholder - would calculate actual score
                "user_id": agent.user_id
            })

        return matching_candidates[:limit]

    async def _rank_conversations(
        self,
        conversations: List[ConversationContext],
        targets: List[Dict[str, Any]]
    ) -> List[MutualMatch]:
        """
        Rank all conversations using mutual ranking system.

        Args:
            conversations: Completed conversation contexts
            targets: Original conversation targets with metadata

        Returns:
            Sorted list of MutualMatch objects
        """
        # Convert conversations to format expected by ranking system
        conversations_for_ranking = []

        for ctx in conversations:
            # Find matching target
            target = next(
                (t for t in targets
                 if t["talent_agent_id"] == ctx.talent_agent_id
                 and t["company_agent_id"] == ctx.company_agent_id
                 and t["job_id"] == ctx.job_id),
                None
            )

            if target:
                conversations_for_ranking.append({
                    "conversation_id": ctx.conversation_id,
                    "talent_agent_id": ctx.talent_agent_id,
                    "company_agent_id": ctx.company_agent_id,
                    "job_id": ctx.job_id,
                    "job_title": target.get("job_title", ""),
                    "company_name": target.get("company_name", ""),
                    "talent_perspective": self._build_perspective_data(ctx, "talent"),
                    "company_perspective": self._build_perspective_data(ctx, "company")
                })

        # Rank using mutual ranking system
        ranked_matches = self.ranking_system.rank_conversations(
            conversations_for_ranking
        )

        return ranked_matches

    def _build_perspective_data(
        self,
        ctx: ConversationContext,
        perspective: str
    ) -> Dict[str, Any]:
        """Build perspective data for scoring."""
        return {
            "turns": ctx.turn_number,
            "technical_insights": ctx.insights,
            "cultural_insights": {},
            "motivation_insights": {},
            "responses": [m["content"] for m in ctx.messages if m["role"] == perspective],
            "interest_indicators": {
                "asked_questions": any("?" in m["content"] for m in ctx.messages if m["role"] == perspective),
                "positive_language": bool(ctx.positive_signals)
            },
            "deal_breakers": ctx.deal_breakers_found,
            "positive_signals": ctx.positive_signals,
            "concerns": []
        }

    def _create_empty_result(
        self,
        agent_id: int,
        agent_type: str,
        start_time: datetime,
        reason: str
    ) -> OrchestrationResult:
        """Create empty result when no matches found."""
        execution_time = (datetime.now() - start_time).total_seconds()

        return OrchestrationResult(
            initiating_agent_id=agent_id,
            agent_type=agent_type,
            total_matches_found=0,
            conversations_started=0,
            conversations_completed=0,
            conversations_failed=0,
            execution_time_seconds=execution_time,
            top_3_matches=[],
            all_ranked_matches=[],
            patterns_detected=[],
            recommendations=[f"No matches found: {reason}"],
            completed_at=datetime.now()
        )
