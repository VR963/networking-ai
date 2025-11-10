"""
Memory Events - Phase 11 Real-time Memory Sync

WebSocket event types for real-time memory system updates.
Integrates with Phase 10A Enhanced Memory System.
"""

from datetime import datetime
from typing import Optional, Dict, Any
from pydantic import BaseModel, Field


class MemoryEvent(BaseModel):
    """Base class for all memory events."""
    event: str
    timestamp: str = Field(default_factory=lambda: datetime.utcnow().isoformat())
    data: Dict[str, Any]

    class Config:
        json_schema_extra = {
            "example": {
                "event": "memory.created",
                "timestamp": "2025-11-09T12:00:00",
                "data": {}
            }
        }


class MemoryCreatedEvent(BaseModel):
    """Event fired when a new memory is created."""
    event: str = "memory.created"
    timestamp: str = Field(default_factory=lambda: datetime.utcnow().isoformat())
    data: Dict[str, Any]

    @classmethod
    def create(
        cls,
        memory_id: int,
        user_id: int,
        content_preview: str,
        importance: float,
        tier: str,
        memory_type: str
    ) -> "MemoryCreatedEvent":
        """
        Create a MemoryCreatedEvent.

        Args:
            memory_id: Memory ID
            user_id: User ID
            content_preview: First 100 characters of content
            importance: Importance score (0.0-1.0)
            tier: Memory tier (hot/warm/cold)
            memory_type: Type of memory

        Returns:
            MemoryCreatedEvent instance
        """
        return cls(
            data={
                "memory_id": memory_id,
                "user_id": user_id,
                "content_preview": content_preview[:100],
                "importance": importance,
                "tier": tier,
                "memory_type": memory_type
            }
        )

    class Config:
        json_schema_extra = {
            "example": {
                "event": "memory.created",
                "timestamp": "2025-11-09T12:00:00",
                "data": {
                    "memory_id": 123,
                    "user_id": 1,
                    "content_preview": "Important meeting notes about...",
                    "importance": 0.8,
                    "tier": "hot",
                    "memory_type": "conversation"
                }
            }
        }


class MemoryUpdatedEvent(BaseModel):
    """Event fired when a memory is updated."""
    event: str = "memory.updated"
    timestamp: str = Field(default_factory=lambda: datetime.utcnow().isoformat())
    data: Dict[str, Any]

    @classmethod
    def create(
        cls,
        memory_id: int,
        user_id: int,
        changes: Dict[str, Any]
    ) -> "MemoryUpdatedEvent":
        """
        Create a MemoryUpdatedEvent.

        Args:
            memory_id: Memory ID
            user_id: User ID
            changes: Dictionary of changed fields

        Returns:
            MemoryUpdatedEvent instance
        """
        return cls(
            data={
                "memory_id": memory_id,
                "user_id": user_id,
                "changes": changes
            }
        )


class MemoryDeletedEvent(BaseModel):
    """Event fired when a memory is deleted."""
    event: str = "memory.deleted"
    timestamp: str = Field(default_factory=lambda: datetime.utcnow().isoformat())
    data: Dict[str, Any]

    @classmethod
    def create(
        cls,
        memory_id: int,
        user_id: int
    ) -> "MemoryDeletedEvent":
        """
        Create a MemoryDeletedEvent.

        Args:
            memory_id: Memory ID
            user_id: User ID

        Returns:
            MemoryDeletedEvent instance
        """
        return cls(
            data={
                "memory_id": memory_id,
                "user_id": user_id,
                "deleted_at": datetime.utcnow().isoformat()
            }
        )


class MemoryTierChangedEvent(BaseModel):
    """Event fired when a memory's tier changes (promotion/demotion)."""
    event: str = "memory.tier_changed"
    timestamp: str = Field(default_factory=lambda: datetime.utcnow().isoformat())
    data: Dict[str, Any]

    @classmethod
    def create(
        cls,
        memory_id: int,
        user_id: int,
        old_tier: str,
        new_tier: str,
        decay_score: float,
        reason: str
    ) -> "MemoryTierChangedEvent":
        """
        Create a MemoryTierChangedEvent.

        Args:
            memory_id: Memory ID
            user_id: User ID
            old_tier: Old tier (hot/warm/cold)
            new_tier: New tier (hot/warm/cold)
            decay_score: Current decay score
            reason: Reason for tier change

        Returns:
            MemoryTierChangedEvent instance
        """
        return cls(
            data={
                "memory_id": memory_id,
                "user_id": user_id,
                "old_tier": old_tier,
                "new_tier": new_tier,
                "decay_score": decay_score,
                "reason": reason,  # "promotion", "demotion", "manual"
                "is_promotion": _is_promotion(old_tier, new_tier)
            }
        )

    class Config:
        json_schema_extra = {
            "example": {
                "event": "memory.tier_changed",
                "timestamp": "2025-11-09T12:00:00",
                "data": {
                    "memory_id": 123,
                    "user_id": 1,
                    "old_tier": "warm",
                    "new_tier": "hot",
                    "decay_score": 0.85,
                    "reason": "promotion",
                    "is_promotion": True
                }
            }
        }


class MemoryDecayAlertEvent(BaseModel):
    """Event fired when a memory is at risk of being demoted."""
    event: str = "memory.decay_alert"
    timestamp: str = Field(default_factory=lambda: datetime.utcnow().isoformat())
    data: Dict[str, Any]

    @classmethod
    def create(
        cls,
        memory_id: int,
        user_id: int,
        current_tier: str,
        decay_score: float,
        content_preview: str,
        days_until_demotion: int
    ) -> "MemoryDecayAlertEvent":
        """
        Create a MemoryDecayAlertEvent.

        Args:
            memory_id: Memory ID
            user_id: User ID
            current_tier: Current tier
            decay_score: Current decay score
            content_preview: Memory content preview
            days_until_demotion: Estimated days until demotion

        Returns:
            MemoryDecayAlertEvent instance
        """
        return cls(
            data={
                "memory_id": memory_id,
                "user_id": user_id,
                "current_tier": current_tier,
                "decay_score": decay_score,
                "content_preview": content_preview[:100],
                "days_until_demotion": days_until_demotion,
                "action": "access_to_preserve"
            }
        )


class MemorySyncRequestEvent(BaseModel):
    """Client request to sync memories across devices."""
    event: str = "memory.sync_request"
    timestamp: str = Field(default_factory=lambda: datetime.utcnow().isoformat())
    data: Dict[str, Any]

    @classmethod
    def create(
        cls,
        user_id: int,
        last_sync_timestamp: Optional[str] = None,
        device_id: Optional[str] = None
    ) -> "MemorySyncRequestEvent":
        """
        Create a MemorySyncRequestEvent.

        Args:
            user_id: User ID
            last_sync_timestamp: Last sync timestamp
            device_id: Device ID requesting sync

        Returns:
            MemorySyncRequestEvent instance
        """
        return cls(
            data={
                "user_id": user_id,
                "last_sync_timestamp": last_sync_timestamp,
                "device_id": device_id
            }
        )


class MemorySyncResponseEvent(BaseModel):
    """Server response with synced memories."""
    event: str = "memory.sync_response"
    timestamp: str = Field(default_factory=lambda: datetime.utcnow().isoformat())
    data: Dict[str, Any]

    @classmethod
    def create(
        cls,
        user_id: int,
        memories_updated: int,
        memories_created: int,
        memories_deleted: int,
        sync_timestamp: str
    ) -> "MemorySyncResponseEvent":
        """
        Create a MemorySyncResponseEvent.

        Args:
            user_id: User ID
            memories_updated: Number of updated memories
            memories_created: Number of new memories
            memories_deleted: Number of deleted memories
            sync_timestamp: Sync completion timestamp

        Returns:
            MemorySyncResponseEvent instance
        """
        return cls(
            data={
                "user_id": user_id,
                "memories_updated": memories_updated,
                "memories_created": memories_created,
                "memories_deleted": memories_deleted,
                "sync_timestamp": sync_timestamp,
                "total_changes": memories_updated + memories_created + memories_deleted
            }
        )


class MemoryStatsEvent(BaseModel):
    """Event with memory statistics update."""
    event: str = "memory.stats_updated"
    timestamp: str = Field(default_factory=lambda: datetime.utcnow().isoformat())
    data: Dict[str, Any]

    @classmethod
    def create(
        cls,
        user_id: int,
        total_memories: int,
        tier_distribution: Dict[str, int],
        cache_hit_rate: float,
        avg_importance: float
    ) -> "MemoryStatsEvent":
        """
        Create a MemoryStatsEvent.

        Args:
            user_id: User ID
            total_memories: Total number of memories
            tier_distribution: Count by tier
            cache_hit_rate: Cache hit rate
            avg_importance: Average importance score

        Returns:
            MemoryStatsEvent instance
        """
        return cls(
            data={
                "user_id": user_id,
                "total_memories": total_memories,
                "tier_distribution": tier_distribution,
                "cache_hit_rate": cache_hit_rate,
                "avg_importance": avg_importance
            }
        )


# ==================== Helper Functions ====================

def _is_promotion(old_tier: str, new_tier: str) -> bool:
    """
    Determine if tier change is a promotion.

    Args:
        old_tier: Old tier
        new_tier: New tier

    Returns:
        True if promotion, False if demotion
    """
    tier_rank = {"cold": 0, "warm": 1, "hot": 2}
    return tier_rank.get(new_tier, 0) > tier_rank.get(old_tier, 0)


# ==================== Event Type Registry ====================

MEMORY_EVENT_TYPES = {
    "memory.created": MemoryCreatedEvent,
    "memory.updated": MemoryUpdatedEvent,
    "memory.deleted": MemoryDeletedEvent,
    "memory.tier_changed": MemoryTierChangedEvent,
    "memory.decay_alert": MemoryDecayAlertEvent,
    "memory.sync_request": MemorySyncRequestEvent,
    "memory.sync_response": MemorySyncResponseEvent,
    "memory.stats_updated": MemoryStatsEvent,
}
