"""
Warm Memory Layer - PostgreSQL-based medium-term storage

Features:
- <5s query performance
- Full-text search (PostgreSQL GIN index)
- Thousands of memories per user
- 30-day default retention
- Access tracking and decay scoring
"""

import logging
from typing import List, Optional, Dict, Any
from datetime import datetime, timedelta

from sqlalchemy import func, and_, or_
from sqlalchemy.orm import Session

from ..models.memory import UserMemory, MemoryTier, MemoryType
from .hot_memory import Memory

logger = logging.getLogger(__name__)


class WarmMemory:
    """
    PostgreSQL-based warm memory layer for medium-term storage.

    Performance:
    - Query: <5s (full-text search)
    - Store: <100ms
    - Capacity: Thousands per user
    - Retention: 30 days (configurable)
    """

    def __init__(self, db_session: Session, retention_days: int = 30):
        """
        Initialize WarmMemory layer.

        Args:
            db_session: SQLAlchemy database session
            retention_days: Number of days to retain memories (default 30)
        """
        self.db = db_session
        self.retention_days = retention_days

    def query(
        self,
        user_id: int,
        query: str,
        limit: int = 10,
        min_importance: float = 0.0,
        memory_types: Optional[List[str]] = None
    ) -> List[Memory]:
        """
        Query warm memory using PostgreSQL full-text search.

        Args:
            user_id: User ID to search for
            query: Search query (full-text search)
            limit: Maximum number of results (default 10)
            min_importance: Minimum importance score (default 0.0)
            memory_types: Filter by memory types (optional)

        Returns:
            List of Memory objects with relevance scores
        """
        try:
            # Build full-text search query
            search_query = func.to_tsquery('english', self._prepare_query(query))

            # Build base query
            base_query = self.db.query(UserMemory).filter(
                and_(
                    UserMemory.user_id == user_id,
                    UserMemory.is_deleted == False,
                    UserMemory.memory_tier.in_([MemoryTier.WARM, MemoryTier.HOT]),
                    UserMemory.importance >= min_importance
                )
            )

            # Add memory type filter if specified
            if memory_types:
                base_query = base_query.filter(
                    UserMemory.memory_type.in_([MemoryType(t) for t in memory_types])
                )

            # Add full-text search with ranking
            results = base_query.filter(
                func.to_tsvector('english', UserMemory.content).op('@@')(search_query)
            ).order_by(
                # Order by relevance (ts_rank) and decay score
                func.ts_rank(
                    func.to_tsvector('english', UserMemory.content),
                    search_query
                ).desc(),
                UserMemory.decay_score.desc()
            ).limit(limit).all()

            # Convert to Memory objects with scores
            memories = []
            for result in results:
                # Calculate relevance score using ts_rank
                score = self.db.query(
                    func.ts_rank(
                        func.to_tsvector('english', result.content),
                        search_query
                    )
                ).scalar()

                memory = Memory(
                    id=result.id,
                    user_id=result.user_id,
                    content=result.content,
                    metadata=result.meta or {},
                    created_at=result.created_at,
                    last_accessed=result.last_accessed,
                    access_count=result.access_count,
                    importance=result.importance,
                    tier='warm',
                    score=float(score) if score else 0.0
                )
                memories.append(memory)

                # Update access tracking
                result.update_access()

            # Commit access updates
            self.db.commit()

            logger.info(f"WarmMemory query for user {user_id}: found {len(memories)} results")
            return memories

        except Exception as e:
            logger.error(f"WarmMemory query error: {str(e)}")
            self.db.rollback()
            return []

    def store(
        self,
        user_id: int,
        content: str,
        metadata: Optional[Dict[str, Any]] = None,
        importance: float = 0.5,
        memory_type: str = "conversation"
    ) -> Optional[Memory]:
        """
        Store a new memory in warm tier.

        Args:
            user_id: User ID
            content: Memory content
            metadata: Optional metadata
            importance: Importance score (0.0 to 1.0)
            memory_type: Type of memory (default "conversation")

        Returns:
            Memory object if successful, None otherwise
        """
        try:
            # Create UserMemory record
            user_memory = UserMemory(
                user_id=user_id,
                content=content,
                metadata=metadata or {},
                importance=importance,
                memory_type=MemoryType(memory_type),
                memory_tier=MemoryTier.WARM,
                created_at=datetime.utcnow(),
                last_accessed=datetime.utcnow(),
                access_count=0,
                decay_score=1.0  # New memories start with max score
            )

            self.db.add(user_memory)
            self.db.commit()
            self.db.refresh(user_memory)

            logger.info(f"WarmMemory stored memory {user_memory.id} for user {user_id}")

            # Convert to Memory object
            return Memory(
                id=user_memory.id,
                user_id=user_memory.user_id,
                content=user_memory.content,
                metadata=user_memory.meta,
                created_at=user_memory.created_at,
                last_accessed=user_memory.last_accessed,
                access_count=user_memory.access_count,
                importance=user_memory.importance,
                tier='warm',
                score=0.0
            )

        except Exception as e:
            logger.error(f"WarmMemory store error: {str(e)}")
            self.db.rollback()
            return None

    def get_by_id(self, user_id: int, memory_id: int) -> Optional[Memory]:
        """
        Retrieve a specific memory by ID.

        Args:
            user_id: User ID (for security)
            memory_id: Memory ID

        Returns:
            Memory object if found, None otherwise
        """
        try:
            result = self.db.query(UserMemory).filter(
                and_(
                    UserMemory.id == memory_id,
                    UserMemory.user_id == user_id,
                    UserMemory.is_deleted == False
                )
            ).first()

            if not result:
                return None

            # Update access tracking
            result.update_access()
            self.db.commit()

            return Memory(
                id=result.id,
                user_id=result.user_id,
                content=result.content,
                metadata=result.meta or {},
                created_at=result.created_at,
                last_accessed=result.last_accessed,
                access_count=result.access_count,
                importance=result.importance,
                tier='warm',
                score=0.0
            )

        except Exception as e:
            logger.error(f"WarmMemory get_by_id error: {str(e)}")
            self.db.rollback()
            return None

    def get_recent(
        self,
        user_id: int,
        limit: int = 20,
        days: int = 7
    ) -> List[Memory]:
        """
        Get recent memories for a user.

        Args:
            user_id: User ID
            limit: Maximum number of results
            days: Look back period in days (default 7)

        Returns:
            List of Memory objects sorted by recency
        """
        try:
            cutoff_date = datetime.utcnow() - timedelta(days=days)

            results = self.db.query(UserMemory).filter(
                and_(
                    UserMemory.user_id == user_id,
                    UserMemory.is_deleted == False,
                    UserMemory.last_accessed >= cutoff_date
                )
            ).order_by(
                UserMemory.last_accessed.desc()
            ).limit(limit).all()

            memories = []
            for result in results:
                memory = Memory(
                    id=result.id,
                    user_id=result.user_id,
                    content=result.content,
                    metadata=result.meta or {},
                    created_at=result.created_at,
                    last_accessed=result.last_accessed,
                    access_count=result.access_count,
                    importance=result.importance,
                    tier='warm',
                    score=result.decay_score
                )
                memories.append(memory)

            return memories

        except Exception as e:
            logger.error(f"WarmMemory get_recent error: {str(e)}")
            return []

    def update_tier(
        self,
        memory_id: int,
        new_tier: str
    ) -> bool:
        """
        Update memory tier (for promotion/demotion).

        Args:
            memory_id: Memory ID
            new_tier: New tier ('hot', 'warm', 'cold')

        Returns:
            True if successful, False otherwise
        """
        try:
            result = self.db.query(UserMemory).filter(
                UserMemory.id == memory_id
            ).first()

            if not result:
                return False

            result.memory_tier = MemoryTier(new_tier)
            self.db.commit()

            logger.info(f"WarmMemory updated tier for memory {memory_id} to {new_tier}")
            return True

        except Exception as e:
            logger.error(f"WarmMemory update_tier error: {str(e)}")
            self.db.rollback()
            return False

    def delete(self, user_id: int, memory_id: int) -> bool:
        """
        Soft delete a memory.

        Args:
            user_id: User ID (for security)
            memory_id: Memory ID

        Returns:
            True if successful, False otherwise
        """
        try:
            result = self.db.query(UserMemory).filter(
                and_(
                    UserMemory.id == memory_id,
                    UserMemory.user_id == user_id
                )
            ).first()

            if not result:
                return False

            result.is_deleted = True
            result.deleted_at = datetime.utcnow()
            self.db.commit()

            logger.info(f"WarmMemory deleted memory {memory_id} for user {user_id}")
            return True

        except Exception as e:
            logger.error(f"WarmMemory delete error: {str(e)}")
            self.db.rollback()
            return False

    def get_stats(self, user_id: int) -> Dict[str, Any]:
        """
        Get memory statistics for a user.

        Args:
            user_id: User ID

        Returns:
            Dictionary with statistics
        """
        try:
            total = self.db.query(func.count(UserMemory.id)).filter(
                and_(
                    UserMemory.user_id == user_id,
                    UserMemory.is_deleted == False
                )
            ).scalar()

            hot = self.db.query(func.count(UserMemory.id)).filter(
                and_(
                    UserMemory.user_id == user_id,
                    UserMemory.memory_tier == MemoryTier.HOT,
                    UserMemory.is_deleted == False
                )
            ).scalar()

            warm = self.db.query(func.count(UserMemory.id)).filter(
                and_(
                    UserMemory.user_id == user_id,
                    UserMemory.memory_tier == MemoryTier.WARM,
                    UserMemory.is_deleted == False
                )
            ).scalar()

            cold = self.db.query(func.count(UserMemory.id)).filter(
                and_(
                    UserMemory.user_id == user_id,
                    UserMemory.memory_tier == MemoryTier.COLD,
                    UserMemory.is_deleted == False
                )
            ).scalar()

            avg_importance = self.db.query(func.avg(UserMemory.importance)).filter(
                and_(
                    UserMemory.user_id == user_id,
                    UserMemory.is_deleted == False
                )
            ).scalar()

            return {
                "total_memories": total or 0,
                "tier_distribution": {
                    "hot": hot or 0,
                    "warm": warm or 0,
                    "cold": cold or 0
                },
                "avg_importance": float(avg_importance) if avg_importance else 0.0
            }

        except Exception as e:
            logger.error(f"WarmMemory get_stats error: {str(e)}")
            return {
                "total_memories": 0,
                "tier_distribution": {"hot": 0, "warm": 0, "cold": 0},
                "avg_importance": 0.0
            }

    def _prepare_query(self, query: str) -> str:
        """
        Prepare query string for PostgreSQL full-text search.

        Converts natural language query to tsquery format.

        Args:
            query: Natural language query

        Returns:
            Formatted tsquery string
        """
        # Split query into words
        words = query.strip().split()

        # Join with '&' for AND search (all words must match)
        # For OR search, use '|'
        # For phrase search, use '<->'
        prepared = ' & '.join(words)

        return prepared
