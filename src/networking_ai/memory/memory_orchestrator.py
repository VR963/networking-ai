"""
Memory Orchestrator - Intelligent multi-tier memory management

Features:
- Unified interface for all memory tiers (hot/warm/cold)
- Intelligent routing with fallback (hot → warm → cold)
- Automatic tier promotion/demotion
- Memory decay management
- Analytics tracking
"""

import logging
from typing import List, Optional, Dict, Any
from datetime import datetime
import asyncio

from sqlalchemy.orm import Session

from .hot_memory import HotMemory, Memory
from .warm_memory import WarmMemory
from .cold_memory import ColdMemory
from ..cache.redis_client import RedisClient
from ..services.chromadb_service import ChromaDBService
from ..models.memory import UserMemory, MemoryAnalytics, MemoryTier

logger = logging.getLogger(__name__)


class MemoryOrchestrator:
    """
    Intelligent orchestrator for multi-tier memory system.

    Manages:
    - Hot tier (Redis): <1s access, 100 items/user, 24h TTL
    - Warm tier (PostgreSQL): <5s access, thousands/user, 30d retention
    - Cold tier (ChromaDB): <10s access, unlimited, permanent

    Features:
    - Smart routing: Try hot → warm → cold with fallback
    - Auto-promotion: Frequently accessed memories move to hot tier
    - Auto-demotion: Rarely accessed memories move to cold tier
    - Analytics: Track hit rates and performance
    """

    def __init__(
        self,
        db_session: Session,
        redis_client: RedisClient,
        chromadb_service: ChromaDBService,
        realtime_service=None
    ):
        """
        Initialize MemoryOrchestrator.

        Args:
            db_session: SQLAlchemy database session
            redis_client: Redis client for hot tier
            chromadb_service: ChromaDB service for cold tier
            realtime_service: Optional realtime memory service for WebSocket broadcasts
        """
        self.db = db_session
        self.hot = HotMemory(redis_client)
        self.warm = WarmMemory(db_session)
        self.cold = ColdMemory(chromadb_service)
        self.realtime = realtime_service

        # Analytics tracking
        self.analytics = {
            "hot_hits": 0,
            "warm_hits": 0,
            "cold_hits": 0,
            "misses": 0
        }

    def query(
        self,
        user_id: int,
        query: str,
        limit: int = 10,
        tiers: Optional[List[str]] = None
    ) -> List[Memory]:
        """
        Query memory with intelligent tier routing.

        Strategy:
        1. Try hot tier first (fastest, <1s)
        2. If insufficient results, try warm tier (<5s)
        3. If still insufficient, try cold tier (<10s)
        4. Promote accessed memories to appropriate tier

        Args:
            user_id: User ID
            query: Search query
            limit: Maximum number of results (default 10)
            tiers: Specific tiers to search (default: all)

        Returns:
            List of Memory objects with relevance scores
        """
        results = []
        tiers_to_search = tiers or ['hot', 'warm', 'cold']

        try:
            # 1. Try HOT tier first (Redis - keyword search)
            if 'hot' in tiers_to_search:
                hot_results = self.hot.query(user_id, query, limit=limit)
                if hot_results:
                    results.extend(hot_results)
                    self.analytics["hot_hits"] += len(hot_results)
                    logger.info(f"MemoryOrchestrator: {len(hot_results)} hot tier hits")

            # 2. If we need more results, try WARM tier (PostgreSQL - full-text search)
            if len(results) < limit and 'warm' in tiers_to_search:
                remaining = limit - len(results)
                warm_results = self.warm.query(user_id, query, limit=remaining)
                if warm_results:
                    results.extend(warm_results)
                    self.analytics["warm_hits"] += len(warm_results)
                    logger.info(f"MemoryOrchestrator: {len(warm_results)} warm tier hits")

                    # Promote high-scoring warm memories to hot tier
                    self._promote_to_hot(warm_results)

            # 3. If still need more, try COLD tier (ChromaDB - vector search)
            if len(results) < limit and 'cold' in tiers_to_search:
                remaining = limit - len(results)
                cold_results = self.cold.query(user_id, query, limit=remaining)
                if cold_results:
                    results.extend(cold_results)
                    self.analytics["cold_hits"] += len(cold_results)
                    logger.info(f"MemoryOrchestrator: {len(cold_results)} cold tier hits")

                    # Promote high-scoring cold memories to warm tier
                    self._promote_to_warm(cold_results)

            # Sort by relevance score (descending)
            results.sort(key=lambda m: m.score, reverse=True)

            # Track misses
            if not results:
                self.analytics["misses"] += 1

            logger.info(
                f"MemoryOrchestrator query for user {user_id}: "
                f"{len(results)} total results from {len(tiers_to_search)} tiers"
            )

            return results[:limit]

        except Exception as e:
            logger.error(f"MemoryOrchestrator query error: {str(e)}")
            return []

    def store(
        self,
        user_id: int,
        content: str,
        metadata: Optional[Dict[str, Any]] = None,
        importance: float = 0.5,
        memory_type: str = "conversation",
        tier: str = "auto"
    ) -> Optional[Memory]:
        """
        Store a new memory with intelligent tier placement.

        Strategy:
        - High importance (>0.7): Start in hot tier
        - Medium importance (0.3-0.7): Start in warm tier
        - Low importance (<0.3): Start in cold tier
        - Auto: Determine based on importance

        Args:
            user_id: User ID
            content: Memory content
            metadata: Optional metadata
            importance: Importance score (0.0 to 1.0)
            memory_type: Type of memory
            tier: Target tier ('hot', 'warm', 'cold', 'auto')

        Returns:
            Memory object if successful, None otherwise
        """
        try:
            # Determine tier if auto
            if tier == "auto":
                if importance > 0.7:
                    tier = "hot"
                elif importance < 0.3:
                    tier = "cold"
                else:
                    tier = "warm"

            # Always store in warm tier (PostgreSQL) for persistence
            memory = self.warm.store(
                user_id=user_id,
                content=content,
                metadata=metadata,
                importance=importance,
                memory_type=memory_type
            )

            if not memory:
                return None

            # Additionally cache in hot tier if appropriate
            if tier == "hot" and memory:
                self.hot.cache([memory])

            # Additionally archive in cold tier if appropriate
            if tier == "cold" and memory:
                self.cold.store(
                    user_id=user_id,
                    memory_id=memory.id,
                    content=content,
                    metadata=metadata,
                    created_at=memory.created_at,
                    last_accessed=memory.last_accessed
                )

            logger.info(
                f"MemoryOrchestrator stored memory {memory.id} "
                f"for user {user_id} in tier '{tier}'"
            )

            # Broadcast memory created event
            if self.realtime:
                self._broadcast_event(
                    self.realtime.broadcast_memory_created(
                        memory_id=memory.id,
                        user_id=user_id,
                        content_preview=content[:100],
                        importance=importance,
                        tier=tier,
                        memory_type=memory_type
                    )
                )

            return memory

        except Exception as e:
            logger.error(f"MemoryOrchestrator store error: {str(e)}")
            return None

    def get_by_id(self, user_id: int, memory_id: int) -> Optional[Memory]:
        """
        Retrieve a specific memory by ID.

        Searches warm tier (source of truth) and updates hot tier cache.

        Args:
            user_id: User ID
            memory_id: Memory ID

        Returns:
            Memory object if found, None otherwise
        """
        try:
            # Get from warm tier (source of truth)
            memory = self.warm.get_by_id(user_id, memory_id)

            if memory:
                # Cache in hot tier for future access
                self.hot.cache([memory])
                self.analytics["warm_hits"] += 1
            else:
                self.analytics["misses"] += 1

            return memory

        except Exception as e:
            logger.error(f"MemoryOrchestrator get_by_id error: {str(e)}")
            return None

    def delete(self, user_id: int, memory_id: int) -> bool:
        """
        Delete a memory from all tiers.

        Args:
            user_id: User ID
            memory_id: Memory ID

        Returns:
            True if successful, False otherwise
        """
        try:
            # Delete from all tiers
            warm_deleted = self.warm.delete(user_id, memory_id)
            cold_deleted = self.cold.delete(user_id, memory_id)

            # Hot tier uses LRU eviction, so we don't need explicit delete
            # It will naturally expire

            logger.info(
                f"MemoryOrchestrator deleted memory {memory_id} "
                f"for user {user_id} (warm: {warm_deleted}, cold: {cold_deleted})"
            )

            # Broadcast memory deleted event
            if self.realtime and warm_deleted:
                self._broadcast_event(
                    self.realtime.broadcast_memory_deleted(
                        memory_id=memory_id,
                        user_id=user_id
                    )
                )

            return warm_deleted

        except Exception as e:
            logger.error(f"MemoryOrchestrator delete error: {str(e)}")
            return False

    def get_stats(self, user_id: int) -> Dict[str, Any]:
        """
        Get comprehensive memory statistics for a user.

        Args:
            user_id: User ID

        Returns:
            Dictionary with statistics across all tiers
        """
        try:
            # Get warm tier stats (includes hot/warm/cold counts)
            warm_stats = self.warm.get_stats(user_id)

            # Get cold tier count
            cold_count = self.cold.get_count(user_id)

            # Combine stats
            stats = {
                "total_memories": warm_stats["total_memories"],
                "tier_distribution": warm_stats["tier_distribution"],
                "avg_importance": warm_stats["avg_importance"],
                "cold_archive_count": cold_count,
                "cache_performance": {
                    "hot_hits": self.analytics["hot_hits"],
                    "warm_hits": self.analytics["warm_hits"],
                    "cold_hits": self.analytics["cold_hits"],
                    "misses": self.analytics["misses"],
                    "total_queries": (
                        self.analytics["hot_hits"] +
                        self.analytics["warm_hits"] +
                        self.analytics["cold_hits"] +
                        self.analytics["misses"]
                    )
                }
            }

            # Calculate hit rates
            total = stats["cache_performance"]["total_queries"]
            if total > 0:
                stats["cache_performance"]["hot_hit_rate"] = (
                    self.analytics["hot_hits"] / total
                )
                stats["cache_performance"]["overall_hit_rate"] = (
                    (self.analytics["hot_hits"] + self.analytics["warm_hits"]) / total
                )

            return stats

        except Exception as e:
            logger.error(f"MemoryOrchestrator get_stats error: {str(e)}")
            return {
                "total_memories": 0,
                "tier_distribution": {"hot": 0, "warm": 0, "cold": 0},
                "avg_importance": 0.0
            }

    def _promote_to_hot(self, memories: List[Memory]) -> int:
        """
        Promote high-scoring memories to hot tier.

        Args:
            memories: List of memories to consider

        Returns:
            Number of promoted memories
        """
        try:
            # Promote memories with high relevance scores (>0.7)
            high_scoring = [m for m in memories if m.score > 0.7]

            if high_scoring:
                count = self.hot.cache(high_scoring)
                logger.info(f"MemoryOrchestrator promoted {count} memories to hot tier")
                return count

            return 0

        except Exception as e:
            logger.error(f"MemoryOrchestrator promote_to_hot error: {str(e)}")
            return 0

    def _promote_to_warm(self, memories: List[Memory]) -> int:
        """
        Promote cold memories back to warm tier.

        Updates the tier in the database to mark them as warm.

        Args:
            memories: List of memories to promote

        Returns:
            Number of promoted memories
        """
        try:
            count = 0
            for memory in memories:
                # Only promote high-scoring results
                if memory.score > 0.6:
                    success = self.warm.update_tier(memory.id, 'warm')
                    if success:
                        count += 1

                        # Broadcast tier changed event
                        if self.realtime:
                            self._broadcast_event(
                                self.realtime.broadcast_tier_changed(
                                    memory_id=memory.id,
                                    user_id=memory.user_id,
                                    old_tier='cold',
                                    new_tier='warm',
                                    decay_score=memory.score,
                                    reason='promotion'
                                )
                            )

            if count > 0:
                logger.info(f"MemoryOrchestrator promoted {count} memories to warm tier")

            return count

        except Exception as e:
            logger.error(f"MemoryOrchestrator promote_to_warm error: {str(e)}")
            return 0

    def reset_analytics(self):
        """Reset analytics counters."""
        self.analytics = {
            "hot_hits": 0,
            "warm_hits": 0,
            "cold_hits": 0,
            "misses": 0
        }
        logger.info("MemoryOrchestrator analytics reset")

    def _broadcast_event(self, coro):
        """
        Helper to run async broadcast without blocking.

        Args:
            coro: Coroutine to run
        """
        if not self.realtime:
            return

        try:
            # Try to get running event loop
            loop = asyncio.get_event_loop()
            if loop.is_running():
                # If loop is running, schedule as task
                asyncio.create_task(coro)
            else:
                # If no loop, run synchronously
                loop.run_until_complete(coro)
        except RuntimeError:
            # No event loop, create new one
            try:
                asyncio.run(coro)
            except Exception as e:
                logger.warning(f"Failed to broadcast event: {str(e)}")
        except Exception as e:
            logger.warning(f"Failed to broadcast event: {str(e)}")
