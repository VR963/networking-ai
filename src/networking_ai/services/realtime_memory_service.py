"""
Realtime Memory Service - Phase 11 WebSocket Integration

Broadcasts memory events to connected clients in real-time.

Features:
- Memory creation/update/deletion notifications
- Tier change alerts (promotion/demotion)
- Decay alerts (memories at risk)
- Cross-device synchronization
- Live statistics updates
"""

import logging
from typing import Optional, Dict, Any, List
from datetime import datetime

from ..websocket.connection_manager import ConnectionManager, get_connection_manager
from ..websocket.memory_events import (
    MemoryCreatedEvent,
    MemoryUpdatedEvent,
    MemoryDeletedEvent,
    MemoryTierChangedEvent,
    MemoryDecayAlertEvent,
    MemorySyncRequestEvent,
    MemorySyncResponseEvent,
    MemoryStatsEvent
)
from ..models.memory import UserMemory
from ..memory.hot_memory import Memory

logger = logging.getLogger(__name__)


class RealtimeMemoryService:
    """
    Service for broadcasting memory events to WebSocket clients.

    Integrates with Phase 10A Memory System to provide real-time updates.
    """

    def __init__(self, connection_manager: Optional[ConnectionManager] = None):
        """
        Initialize Realtime Memory Service.

        Args:
            connection_manager: WebSocket connection manager (default: global instance)
        """
        self.connection_manager = connection_manager or get_connection_manager()

    async def broadcast_memory_created(
        self,
        memory_id: int,
        user_id: int,
        content_preview: str,
        importance: float,
        tier: str,
        memory_type: str
    ):
        """
        Broadcast memory creation event to user.

        Args:
            memory_id: Memory ID
            user_id: User ID
            content_preview: First 100 characters of content
            importance: Importance score (0.0-1.0)
            tier: Memory tier (hot/warm/cold)
            memory_type: Type of memory
        """
        try:
            event = MemoryCreatedEvent.create(
                memory_id=memory_id,
                user_id=user_id,
                content_preview=content_preview,
                importance=importance,
                tier=tier,
                memory_type=memory_type
            )

            await self.connection_manager.send_to_user(
                user_id=user_id,
                message=event.dict()
            )

            logger.debug(f"Broadcasted memory.created event for memory {memory_id} to user {user_id}")

        except Exception as e:
            logger.error(f"Failed to broadcast memory created event: {str(e)}")

    async def broadcast_memory_updated(
        self,
        memory_id: int,
        user_id: int,
        changes: Dict[str, Any]
    ):
        """
        Broadcast memory update event to user.

        Args:
            memory_id: Memory ID
            user_id: User ID
            changes: Dictionary of changed fields
        """
        try:
            event = MemoryUpdatedEvent.create(
                memory_id=memory_id,
                user_id=user_id,
                changes=changes
            )

            await self.connection_manager.send_to_user(
                user_id=user_id,
                message=event.dict()
            )

            logger.debug(f"Broadcasted memory.updated event for memory {memory_id} to user {user_id}")

        except Exception as e:
            logger.error(f"Failed to broadcast memory updated event: {str(e)}")

    async def broadcast_memory_deleted(
        self,
        memory_id: int,
        user_id: int
    ):
        """
        Broadcast memory deletion event to user.

        Args:
            memory_id: Memory ID
            user_id: User ID
        """
        try:
            event = MemoryDeletedEvent.create(
                memory_id=memory_id,
                user_id=user_id
            )

            await self.connection_manager.send_to_user(
                user_id=user_id,
                message=event.dict()
            )

            logger.debug(f"Broadcasted memory.deleted event for memory {memory_id} to user {user_id}")

        except Exception as e:
            logger.error(f"Failed to broadcast memory deleted event: {str(e)}")

    async def broadcast_tier_changed(
        self,
        memory_id: int,
        user_id: int,
        old_tier: str,
        new_tier: str,
        decay_score: float,
        reason: str
    ):
        """
        Broadcast tier change event to user.

        Args:
            memory_id: Memory ID
            user_id: User ID
            old_tier: Old tier (hot/warm/cold)
            new_tier: New tier (hot/warm/cold)
            decay_score: Current decay score
            reason: Reason for change (promotion/demotion/manual)
        """
        try:
            event = MemoryTierChangedEvent.create(
                memory_id=memory_id,
                user_id=user_id,
                old_tier=old_tier,
                new_tier=new_tier,
                decay_score=decay_score,
                reason=reason
            )

            await self.connection_manager.send_to_user(
                user_id=user_id,
                message=event.dict()
            )

            logger.info(
                f"Broadcasted memory.tier_changed event for memory {memory_id} to user {user_id} "
                f"({old_tier} → {new_tier})"
            )

        except Exception as e:
            logger.error(f"Failed to broadcast tier changed event: {str(e)}")

    async def broadcast_decay_alert(
        self,
        memory_id: int,
        user_id: int,
        current_tier: str,
        decay_score: float,
        content_preview: str,
        days_until_demotion: int
    ):
        """
        Broadcast decay alert to user (memory at risk).

        Args:
            memory_id: Memory ID
            user_id: User ID
            current_tier: Current tier
            decay_score: Current decay score
            content_preview: Memory content preview
            days_until_demotion: Estimated days until demotion
        """
        try:
            event = MemoryDecayAlertEvent.create(
                memory_id=memory_id,
                user_id=user_id,
                current_tier=current_tier,
                decay_score=decay_score,
                content_preview=content_preview,
                days_until_demotion=days_until_demotion
            )

            await self.connection_manager.send_to_user(
                user_id=user_id,
                message=event.dict()
            )

            logger.info(
                f"Broadcasted memory.decay_alert for memory {memory_id} to user {user_id} "
                f"(tier={current_tier}, score={decay_score:.2f})"
            )

        except Exception as e:
            logger.error(f"Failed to broadcast decay alert: {str(e)}")

    async def handle_sync_request(
        self,
        user_id: int,
        last_sync_timestamp: Optional[str] = None,
        device_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Handle memory sync request from client.

        This would typically be called from a WebSocket handler when
        a client requests to sync memories.

        Args:
            user_id: User ID
            last_sync_timestamp: Last sync timestamp
            device_id: Device ID requesting sync

        Returns:
            Sync response data
        """
        try:
            # Log the sync request
            logger.info(
                f"Processing memory sync request for user {user_id} "
                f"(last_sync={last_sync_timestamp}, device={device_id})"
            )

            # TODO: Implement actual sync logic
            # This would:
            # 1. Query memories updated since last_sync_timestamp
            # 2. Return list of created/updated/deleted memories
            # 3. Handle conflict resolution

            # Placeholder response
            sync_response = {
                "memories_updated": 0,
                "memories_created": 0,
                "memories_deleted": 0,
                "sync_timestamp": datetime.utcnow().isoformat()
            }

            # Broadcast sync response
            event = MemorySyncResponseEvent.create(
                user_id=user_id,
                memories_updated=sync_response["memories_updated"],
                memories_created=sync_response["memories_created"],
                memories_deleted=sync_response["memories_deleted"],
                sync_timestamp=sync_response["sync_timestamp"]
            )

            await self.connection_manager.send_to_user(
                user_id=user_id,
                message=event.dict()
            )

            return sync_response

        except Exception as e:
            logger.error(f"Failed to handle sync request: {str(e)}")
            return {
                "error": str(e),
                "sync_timestamp": datetime.utcnow().isoformat()
            }

    async def broadcast_stats_update(
        self,
        user_id: int,
        total_memories: int,
        tier_distribution: Dict[str, int],
        cache_hit_rate: float,
        avg_importance: float
    ):
        """
        Broadcast statistics update to user.

        Args:
            user_id: User ID
            total_memories: Total number of memories
            tier_distribution: Count by tier
            cache_hit_rate: Cache hit rate
            avg_importance: Average importance score
        """
        try:
            event = MemoryStatsEvent.create(
                user_id=user_id,
                total_memories=total_memories,
                tier_distribution=tier_distribution,
                cache_hit_rate=cache_hit_rate,
                avg_importance=avg_importance
            )

            await self.connection_manager.send_to_user(
                user_id=user_id,
                message=event.dict()
            )

            logger.debug(f"Broadcasted memory.stats_updated to user {user_id}")

        except Exception as e:
            logger.error(f"Failed to broadcast stats update: {str(e)}")

    async def broadcast_batch_changes(
        self,
        user_id: int,
        created: List[int] = None,
        updated: List[int] = None,
        deleted: List[int] = None,
        tier_changed: List[int] = None
    ):
        """
        Broadcast multiple memory changes at once (efficient batch updates).

        Useful for decay task that updates many memories at once.

        Args:
            user_id: User ID
            created: List of created memory IDs
            updated: List of updated memory IDs
            deleted: List of deleted memory IDs
            tier_changed: List of tier-changed memory IDs
        """
        try:
            # Send single batch update event
            batch_event = {
                "event": "memory.batch_update",
                "timestamp": datetime.utcnow().isoformat(),
                "data": {
                    "user_id": user_id,
                    "created_count": len(created) if created else 0,
                    "updated_count": len(updated) if updated else 0,
                    "deleted_count": len(deleted) if deleted else 0,
                    "tier_changed_count": len(tier_changed) if tier_changed else 0,
                    "created_ids": created or [],
                    "updated_ids": updated or [],
                    "deleted_ids": deleted or [],
                    "tier_changed_ids": tier_changed or []
                }
            }

            await self.connection_manager.send_to_user(
                user_id=user_id,
                message=batch_event
            )

            logger.info(
                f"Broadcasted memory.batch_update to user {user_id} "
                f"(created={len(created or [])}, updated={len(updated or [])}, "
                f"deleted={len(deleted or [])}, tier_changed={len(tier_changed or [])})"
            )

        except Exception as e:
            logger.error(f"Failed to broadcast batch changes: {str(e)}")


# ==================== Integration Helpers ====================

def create_realtime_service() -> RealtimeMemoryService:
    """
    Create a realtime memory service instance.

    Returns:
        RealtimeMemoryService instance
    """
    return RealtimeMemoryService()


async def notify_memory_event(
    event_type: str,
    user_id: int,
    memory_data: Dict[str, Any],
    service: Optional[RealtimeMemoryService] = None
):
    """
    Helper function to notify memory events from memory system.

    Can be called from MemoryOrchestrator or other memory components.

    Args:
        event_type: Event type (created/updated/deleted/tier_changed)
        user_id: User ID
        memory_data: Memory data dictionary
        service: Optional service instance (creates new if None)

    Example:
        await notify_memory_event(
            event_type="created",
            user_id=1,
            memory_data={
                "memory_id": 123,
                "content": "Meeting notes...",
                "importance": 0.8,
                "tier": "hot",
                "memory_type": "conversation"
            }
        )
    """
    if service is None:
        service = create_realtime_service()

    try:
        if event_type == "created":
            await service.broadcast_memory_created(
                memory_id=memory_data["memory_id"],
                user_id=user_id,
                content_preview=memory_data.get("content", "")[:100],
                importance=memory_data.get("importance", 0.5),
                tier=memory_data.get("tier", "warm"),
                memory_type=memory_data.get("memory_type", "general")
            )

        elif event_type == "updated":
            await service.broadcast_memory_updated(
                memory_id=memory_data["memory_id"],
                user_id=user_id,
                changes=memory_data.get("changes", {})
            )

        elif event_type == "deleted":
            await service.broadcast_memory_deleted(
                memory_id=memory_data["memory_id"],
                user_id=user_id
            )

        elif event_type == "tier_changed":
            await service.broadcast_tier_changed(
                memory_id=memory_data["memory_id"],
                user_id=user_id,
                old_tier=memory_data["old_tier"],
                new_tier=memory_data["new_tier"],
                decay_score=memory_data.get("decay_score", 0.0),
                reason=memory_data.get("reason", "automatic")
            )

        elif event_type == "decay_alert":
            await service.broadcast_decay_alert(
                memory_id=memory_data["memory_id"],
                user_id=user_id,
                current_tier=memory_data["current_tier"],
                decay_score=memory_data["decay_score"],
                content_preview=memory_data.get("content", "")[:100],
                days_until_demotion=memory_data.get("days_until_demotion", 7)
            )

    except Exception as e:
        logger.error(f"Failed to notify memory event {event_type}: {str(e)}")


# ==================== Background Task Integration ====================

async def broadcast_periodic_stats(user_id: int, service: Optional[RealtimeMemoryService] = None):
    """
    Background task to broadcast periodic statistics updates.

    Can be called from a scheduler or background worker.

    Args:
        user_id: User ID
        service: Optional service instance
    """
    if service is None:
        service = create_realtime_service()

    try:
        # This would integrate with MemoryAnalyticsService
        # to get real stats

        # Placeholder stats
        stats = {
            "total_memories": 0,
            "tier_distribution": {"hot": 0, "warm": 0, "cold": 0},
            "cache_hit_rate": 0.0,
            "avg_importance": 0.0
        }

        # TODO: Get actual stats from analytics service
        # from ..services.memory_analytics_service import MemoryAnalyticsService
        # analytics = MemoryAnalyticsService(db)
        # stats = analytics.get_user_analytics(user_id, hours=1)

        await service.broadcast_stats_update(
            user_id=user_id,
            total_memories=stats["total_memories"],
            tier_distribution=stats["tier_distribution"],
            cache_hit_rate=stats["cache_hit_rate"],
            avg_importance=stats["avg_importance"]
        )

    except Exception as e:
        logger.error(f"Failed to broadcast periodic stats: {str(e)}")
