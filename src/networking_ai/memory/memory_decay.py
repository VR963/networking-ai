"""
Memory Decay Algorithm - Automatic tier management

Features:
- Calculate decay scores based on recency, frequency, importance
- Automatic tier migration (hot ↔ warm ↔ cold)
- Background task for periodic updates
- Configurable weights and thresholds
"""

import logging
from typing import List, Optional, Dict, Any
from datetime import datetime, timedelta

from sqlalchemy.orm import Session
from sqlalchemy import and_, func

from ..models.memory import UserMemory, MemoryTier, MemoryAnalytics
from .cold_memory import ColdMemory
from .hot_memory import HotMemory, Memory

logger = logging.getLogger(__name__)


class MemoryDecayManager:
    """
    Manager for memory decay calculations and tier migrations.

    Decay Score Formula:
    score = recency_weight × recency + frequency_weight × frequency + importance_weight × importance

    Where:
    - recency: 1.0 if accessed today, decays exponentially to 0.0 over 30 days
    - frequency: normalized access count (0.0 to 1.0, max at 100 accesses)
    - importance: user/AI set importance (0.0 to 1.0)

    Default Weights:
    - recency_weight: 0.4 (40%)
    - frequency_weight: 0.3 (30%)
    - importance_weight: 0.3 (30%)

    Tier Thresholds:
    - > 0.8: Hot tier (Redis)
    - 0.3 - 0.8: Warm tier (PostgreSQL)
    - < 0.3: Cold tier (ChromaDB)
    """

    def __init__(
        self,
        db_session: Session,
        recency_weight: float = 0.4,
        frequency_weight: float = 0.3,
        importance_weight: float = 0.3,
        hot_threshold: float = 0.8,
        cold_threshold: float = 0.3
    ):
        """
        Initialize MemoryDecayManager.

        Args:
            db_session: SQLAlchemy database session
            recency_weight: Weight for recency component (default 0.4)
            frequency_weight: Weight for frequency component (default 0.3)
            importance_weight: Weight for importance component (default 0.3)
            hot_threshold: Minimum score for hot tier (default 0.8)
            cold_threshold: Maximum score for cold tier (default 0.3)
        """
        self.db = db_session
        self.recency_weight = recency_weight
        self.frequency_weight = frequency_weight
        self.importance_weight = importance_weight
        self.hot_threshold = hot_threshold
        self.cold_threshold = cold_threshold

    def calculate_decay_score(self, memory: UserMemory) -> float:
        """
        Calculate decay score for a memory.

        Args:
            memory: UserMemory object

        Returns:
            Decay score (0.0 to 1.0)
        """
        now = datetime.utcnow()

        # 1. Recency score (exponential decay over 30 days)
        days_since_access = (now - memory.last_accessed).total_seconds() / 86400
        recency_score = max(0.0, 1.0 - (days_since_access / 30.0))

        # 2. Frequency score (normalized access count, max 100 accesses)
        frequency_score = min(1.0, memory.access_count / 100.0)

        # 3. Importance score (already 0-1)
        importance_score = memory.importance

        # 4. Combined decay score
        decay = (
            self.recency_weight * recency_score +
            self.frequency_weight * frequency_score +
            self.importance_weight * importance_score
        )

        return max(0.0, min(1.0, decay))

    def update_all_decay_scores(
        self,
        user_id: Optional[int] = None,
        batch_size: int = 1000
    ) -> Dict[str, int]:
        """
        Update decay scores for all memories (or specific user).

        Args:
            user_id: Optional user ID to filter (None = all users)
            batch_size: Number of memories to process per batch

        Returns:
            Dictionary with update statistics
        """
        stats = {
            "processed": 0,
            "updated": 0,
            "promoted_to_hot": 0,
            "demoted_to_cold": 0,
            "errors": 0
        }

        try:
            # Build query
            query = self.db.query(UserMemory).filter(
                UserMemory.is_deleted == False
            )

            if user_id:
                query = query.filter(UserMemory.user_id == user_id)

            # Process in batches
            offset = 0
            while True:
                batch = query.offset(offset).limit(batch_size).all()
                if not batch:
                    break

                for memory in batch:
                    try:
                        # Calculate new decay score
                        old_score = memory.decay_score
                        new_score = self.calculate_decay_score(memory)
                        memory.decay_score = new_score

                        stats["processed"] += 1

                        # Check if tier should change
                        if new_score != old_score:
                            stats["updated"] += 1

                        # Promote to hot tier
                        if new_score > self.hot_threshold and memory.memory_tier != MemoryTier.HOT:
                            memory.memory_tier = MemoryTier.HOT
                            stats["promoted_to_hot"] += 1
                            logger.debug(
                                f"Memory {memory.id} promoted to hot tier "
                                f"(score: {old_score:.2f} → {new_score:.2f})"
                            )

                        # Demote to cold tier
                        elif new_score < self.cold_threshold and memory.memory_tier != MemoryTier.COLD:
                            memory.memory_tier = MemoryTier.COLD
                            stats["demoted_to_cold"] += 1
                            logger.debug(
                                f"Memory {memory.id} demoted to cold tier "
                                f"(score: {old_score:.2f} → {new_score:.2f})"
                            )

                        # Keep in warm tier
                        elif (
                            self.cold_threshold <= new_score <= self.hot_threshold
                            and memory.memory_tier not in [MemoryTier.WARM, MemoryTier.HOT]
                        ):
                            memory.memory_tier = MemoryTier.WARM

                    except Exception as e:
                        logger.error(f"Error processing memory {memory.id}: {str(e)}")
                        stats["errors"] += 1

                # Commit batch
                self.db.commit()

                offset += batch_size

            logger.info(
                f"Memory decay update complete: "
                f"processed={stats['processed']}, updated={stats['updated']}, "
                f"promoted={stats['promoted_to_hot']}, demoted={stats['demoted_to_cold']}, "
                f"errors={stats['errors']}"
            )

            return stats

        except Exception as e:
            logger.error(f"Memory decay update error: {str(e)}")
            self.db.rollback()
            return stats

    def migrate_cold_memories(
        self,
        user_id: int,
        cold_memory: ColdMemory,
        limit: int = 100
    ) -> int:
        """
        Migrate memories to cold tier (ChromaDB archive).

        Args:
            user_id: User ID
            cold_memory: ColdMemory instance
            limit: Maximum memories to migrate

        Returns:
            Number of migrated memories
        """
        try:
            # Find memories marked as cold tier but not yet in ChromaDB
            cold_tier_memories = self.db.query(UserMemory).filter(
                and_(
                    UserMemory.user_id == user_id,
                    UserMemory.memory_tier == MemoryTier.COLD,
                    UserMemory.is_deleted == False
                )
            ).order_by(
                UserMemory.decay_score.asc()  # Migrate lowest scores first
            ).limit(limit).all()

            if not cold_tier_memories:
                return 0

            # Convert to Memory objects
            memories = []
            for mem in cold_tier_memories:
                memory = Memory(
                    id=mem.id,
                    user_id=mem.user_id,
                    content=mem.content,
                    metadata=mem.meta or {},
                    created_at=mem.created_at,
                    last_accessed=mem.last_accessed,
                    access_count=mem.access_count,
                    importance=mem.importance,
                    tier='cold',
                    score=mem.decay_score
                )
                memories.append(memory)

            # Batch migrate to ChromaDB
            migrated = cold_memory.migrate_from_warm(user_id, memories)

            logger.info(f"Migrated {migrated} memories to cold tier for user {user_id}")
            return migrated

        except Exception as e:
            logger.error(f"Cold memory migration error: {str(e)}")
            return 0

    def cleanup_old_memories(
        self,
        days_threshold: int = 90,
        min_importance: float = 0.1
    ) -> int:
        """
        Soft delete very old, low-importance memories.

        Args:
            days_threshold: Delete memories older than this (default 90 days)
            min_importance: Only delete if importance below this (default 0.1)

        Returns:
            Number of deleted memories
        """
        try:
            cutoff_date = datetime.utcnow() - timedelta(days=days_threshold)

            # Find candidates for deletion
            to_delete = self.db.query(UserMemory).filter(
                and_(
                    UserMemory.is_deleted == False,
                    UserMemory.last_accessed < cutoff_date,
                    UserMemory.importance < min_importance,
                    UserMemory.decay_score < 0.1
                )
            ).all()

            count = 0
            for memory in to_delete:
                memory.is_deleted = True
                memory.deleted_at = datetime.utcnow()
                count += 1

            self.db.commit()

            logger.info(f"Cleaned up {count} old memories (>{days_threshold} days, importance<{min_importance})")
            return count

        except Exception as e:
            logger.error(f"Memory cleanup error: {str(e)}")
            self.db.rollback()
            return 0

    def get_tier_statistics(self) -> Dict[str, Any]:
        """
        Get overall tier distribution statistics.

        Returns:
            Dictionary with tier statistics
        """
        try:
            stats = {
                "total": self.db.query(func.count(UserMemory.id)).filter(
                    UserMemory.is_deleted == False
                ).scalar() or 0,
                "hot": self.db.query(func.count(UserMemory.id)).filter(
                    and_(
                        UserMemory.memory_tier == MemoryTier.HOT,
                        UserMemory.is_deleted == False
                    )
                ).scalar() or 0,
                "warm": self.db.query(func.count(UserMemory.id)).filter(
                    and_(
                        UserMemory.memory_tier == MemoryTier.WARM,
                        UserMemory.is_deleted == False
                    )
                ).scalar() or 0,
                "cold": self.db.query(func.count(UserMemory.id)).filter(
                    and_(
                        UserMemory.memory_tier == MemoryTier.COLD,
                        UserMemory.is_deleted == False
                    )
                ).scalar() or 0,
                "deleted": self.db.query(func.count(UserMemory.id)).filter(
                    UserMemory.is_deleted == True
                ).scalar() or 0
            }

            # Calculate percentages
            if stats["total"] > 0:
                stats["hot_percent"] = (stats["hot"] / stats["total"]) * 100
                stats["warm_percent"] = (stats["warm"] / stats["total"]) * 100
                stats["cold_percent"] = (stats["cold"] / stats["total"]) * 100
            else:
                stats["hot_percent"] = 0
                stats["warm_percent"] = 0
                stats["cold_percent"] = 0

            return stats

        except Exception as e:
            logger.error(f"Tier statistics error: {str(e)}")
            return {
                "total": 0,
                "hot": 0,
                "warm": 0,
                "cold": 0,
                "deleted": 0
            }


def run_decay_task(
    db_session: Session,
    cold_memory: Optional[ColdMemory] = None,
    user_id: Optional[int] = None
):
    """
    Background task to run memory decay updates.

    Should be scheduled to run hourly.

    Args:
        db_session: Database session
        cold_memory: ColdMemory instance for migrations (optional)
        user_id: Optional user ID (None = all users)
    """
    logger.info("Starting memory decay background task")

    try:
        manager = MemoryDecayManager(db_session)

        # 1. Update decay scores
        stats = manager.update_all_decay_scores(user_id=user_id)

        # 2. Migrate to cold tier if ColdMemory available
        if cold_memory and user_id:
            migrated = manager.migrate_cold_memories(user_id, cold_memory)
            stats["migrated_to_cold"] = migrated

        # 3. Cleanup old memories (once per day)
        # TODO: Add daily check to avoid running cleanup every hour
        # cleanup_count = manager.cleanup_old_memories()
        # stats["cleaned_up"] = cleanup_count

        # 4. Log statistics
        tier_stats = manager.get_tier_statistics()

        logger.info(
            f"Memory decay task complete - "
            f"Stats: {stats}, Tier distribution: {tier_stats}"
        )

    except Exception as e:
        logger.error(f"Memory decay task error: {str(e)}")


# APScheduler job definition (for integration)
def schedule_decay_task(scheduler, db_session_factory, cold_memory=None):
    """
    Schedule memory decay task with APScheduler.

    Example:
        from apscheduler.schedulers.background import BackgroundScheduler
        scheduler = BackgroundScheduler()
        schedule_decay_task(scheduler, SessionLocal)
        scheduler.start()

    Args:
        scheduler: APScheduler instance
        db_session_factory: Database session factory (e.g., SessionLocal)
        cold_memory: ColdMemory instance (optional)
    """
    def decay_job():
        db = db_session_factory()
        try:
            run_decay_task(db, cold_memory=cold_memory)
        finally:
            db.close()

    # Run every hour
    scheduler.add_job(
        decay_job,
        'interval',
        hours=1,
        id='memory_decay_task',
        replace_existing=True
    )

    logger.info("Memory decay task scheduled (runs every hour)")
