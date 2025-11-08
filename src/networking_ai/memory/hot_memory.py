"""
Hot Memory Layer - Redis-based ultra-fast cache

Features:
- <10ms query performance
- LRU eviction
- 24-hour TTL
- 100 items per user
- Keyword-based matching (faster than semantic)
"""

import json
import logging
from typing import List, Optional, Dict, Any
from datetime import datetime

from ..cache.redis_client import RedisClient

logger = logging.getLogger(__name__)


class Memory:
    """Memory object representation."""

    def __init__(
        self,
        id: int,
        user_id: int,
        content: str,
        metadata: dict,
        created_at: datetime,
        last_accessed: datetime,
        access_count: int = 0,
        importance: float = 0.5,
        tier: str = 'hot',
        score: float = 0.0
    ):
        self.id = id
        self.user_id = user_id
        self.content = content
        self.metadata = metadata
        self.created_at = created_at
        self.last_accessed = last_accessed
        self.access_count = access_count
        self.importance = importance
        self.tier = tier
        self.score = score  # Relevance score for query results

    def to_dict(self) -> dict:
        """Convert to dictionary."""
        return {
            "id": self.id,
            "user_id": self.user_id,
            "content": self.content,
            "metadata": self.metadata,
            "created_at": self.created_at.isoformat() if isinstance(self.created_at, datetime) else self.created_at,
            "last_accessed": self.last_accessed.isoformat() if isinstance(self.last_accessed, datetime) else self.last_accessed,
            "access_count": self.access_count,
            "importance": self.importance,
            "tier": self.tier,
            "score": self.score
        }

    @classmethod
    def from_dict(cls, data: dict) -> 'Memory':
        """Create from dictionary."""
        # Handle datetime strings
        created_at = data.get('created_at')
        if isinstance(created_at, str):
            created_at = datetime.fromisoformat(created_at)

        last_accessed = data.get('last_accessed')
        if isinstance(last_accessed, str):
            last_accessed = datetime.fromisoformat(last_accessed)

        return cls(
            id=data.get('id'),
            user_id=data.get('user_id'),
            content=data.get('content'),
            metadata=data.get('metadata', {}),
            created_at=created_at,
            last_accessed=last_accessed,
            access_count=data.get('access_count', 0),
            importance=data.get('importance', 0.5),
            tier=data.get('tier', 'hot'),
            score=data.get('score', 0.0)
        )


class HotMemory:
    """
    Redis-based hot memory layer for ultra-fast access.

    Performance:
    - Query: <10ms
    - Cache: <5ms
    - Capacity: 100 items per user
    - TTL: 24 hours
    """

    def __init__(self, redis_client: RedisClient):
        """
        Initialize hot memory layer.

        Args:
            redis_client: Redis client instance
        """
        self.redis = redis_client
        self.ttl = 86400  # 24 hours in seconds
        self.max_size = 100  # Max items per user

    def _get_key(self, user_id: int) -> str:
        """Get Redis key for user's hot memories."""
        return f"user:{user_id}:hot_memories"

    def query(
        self,
        user_id: int,
        query: str,
        limit: int = 10
    ) -> List[Memory]:
        """
        Query hot memory with keyword matching.

        Args:
            user_id: User ID
            query: Search query
            limit: Max results to return

        Returns:
            List of matching memories, sorted by relevance
        """
        key = self._get_key(user_id)

        # Get all hot memories for user
        memories_data = self.redis.hgetall(key)

        if not memories_data:
            logger.debug(f"No hot memories found for user {user_id}")
            return []

        # Simple keyword matching (faster than semantic search)
        query_keywords = set(query.lower().split())
        scored_memories = []

        for memory_key, memory_json in memories_data.items():
            try:
                memory_dict = json.loads(memory_json)
                content_keywords = set(memory_dict['content'].lower().split())

                # Calculate keyword overlap
                overlap = len(query_keywords & content_keywords)

                if overlap > 0:
                    # Calculate relevance score
                    score = overlap / len(query_keywords)
                    memory_dict['score'] = score
                    memory_dict['tier'] = 'hot'

                    # Create Memory object
                    memory = Memory.from_dict(memory_dict)
                    scored_memories.append(memory)

            except (json.JSONDecodeError, KeyError) as e:
                logger.error(f"Error parsing memory: {e}")
                continue

        # Sort by score (descending) and return top results
        scored_memories.sort(key=lambda x: x.score, reverse=True)

        return scored_memories[:limit]

    def cache(self, memories: List[Memory]) -> int:
        """
        Cache memories in hot layer with LRU eviction.

        Args:
            memories: List of memories to cache

        Returns:
            Number of memories successfully cached
        """
        if not memories:
            return 0

        cached_count = 0

        for memory in memories:
            key = self._get_key(memory.user_id)

            # Serialize memory
            memory_data = memory.to_dict()
            memory_json = json.dumps(memory_data)

            # Store in Redis hash
            success = self.redis.hset(key, f"memory:{memory.id}", memory_json)

            if success:
                cached_count += 1

                # Set TTL on first write
                self.redis.expire(key, self.ttl)

                # Check and maintain size limit
                size = self.redis.hlen(key)
                if size > self.max_size:
                    self._evict_oldest(key)

        logger.debug(f"Cached {cached_count}/{len(memories)} memories")
        return cached_count

    def _evict_oldest(self, key: str):
        """
        Evict oldest memory from hot cache (LRU).

        Args:
            key: Redis hash key
        """
        memories_data = self.redis.hgetall(key)

        if not memories_data:
            return

        # Find oldest memory by last_accessed timestamp
        oldest_key = None
        oldest_time = None

        for memory_key, memory_json in memories_data.items():
            try:
                memory_dict = json.loads(memory_json)
                last_accessed_str = memory_dict.get('last_accessed')

                if last_accessed_str:
                    last_accessed = datetime.fromisoformat(last_accessed_str)

                    if oldest_time is None or last_accessed < oldest_time:
                        oldest_time = last_accessed
                        oldest_key = memory_key

            except (json.JSONDecodeError, ValueError) as e:
                logger.error(f"Error parsing memory for eviction: {e}")
                continue

        # Evict oldest
        if oldest_key:
            self.redis.hdel(key, oldest_key)
            logger.debug(f"Evicted oldest memory: {oldest_key}")

    def evict(self, user_id: int, memory_id: int) -> bool:
        """
        Manually evict a specific memory from hot cache.

        Args:
            user_id: User ID
            memory_id: Memory ID to evict

        Returns:
            bool: True if evicted
        """
        key = self._get_key(user_id)
        result = self.redis.hdel(key, f"memory:{memory_id}")
        return result > 0

    def clear_user(self, user_id: int) -> bool:
        """
        Clear all hot memories for a user.

        Args:
            user_id: User ID

        Returns:
            bool: True if cleared
        """
        key = self._get_key(user_id)
        result = self.redis.delete(key)
        return result > 0

    def get_stats(self, user_id: int) -> Dict[str, Any]:
        """
        Get hot memory statistics for a user.

        Args:
            user_id: User ID

        Returns:
            dict: Statistics (count, size, etc.)
        """
        key = self._get_key(user_id)
        count = self.redis.hlen(key)

        return {
            "tier": "hot",
            "count": count,
            "max_size": self.max_size,
            "ttl_seconds": self.ttl,
            "usage_percent": (count / self.max_size * 100) if self.max_size > 0 else 0
        }
