"""
Memory System Models - Phase 10A Enhanced Memory.

Multi-tier memory system for AI agents with automatic decay and tier management.
"""

from datetime import datetime
from enum import Enum
from typing import Optional

from sqlalchemy import (
    Column,
    Integer,
    String,
    Text,
    Float,
    DateTime,
    Boolean,
    ForeignKey,
    Index,
    func,
    Enum as SQLEnum
)
from sqlalchemy.orm import relationship
from sqlalchemy.dialects.postgresql import JSONB

from ..database import Base


class MemoryTier(str, Enum):
    """Memory tier levels for multi-tier storage."""
    HOT = "hot"      # Redis - ultra-fast access (<1s)
    WARM = "warm"    # PostgreSQL - fast access (<5s)
    COLD = "cold"    # ChromaDB - vector search (<10s)


class MemoryType(str, Enum):
    """Type of memory content."""
    CONVERSATION = "conversation"    # Conversational memory
    DOCUMENT = "document"            # PDF/document ingestion
    KNOWLEDGE = "knowledge"          # Explicit knowledge
    EXPERIENCE = "experience"        # User experiences/events
    INSIGHT = "insight"              # AI-generated insights
    PREFERENCE = "preference"        # User preferences


class UserMemory(Base):
    """
    User memory storage with multi-tier support and automatic decay.

    This model stores all memories for users/agents in the warm tier (PostgreSQL).
    Hot tier (Redis) and cold tier (ChromaDB) are managed separately but reference
    this model for persistence and metadata.

    Features:
    - Full-text search on content (PostgreSQL GIN index)
    - Automatic decay scoring based on recency, frequency, and importance
    - Tier management (hot/warm/cold) with automatic promotion/demotion
    - JSONB metadata for flexible storage
    - Access tracking for intelligent caching
    """
    __tablename__ = "user_memories"
    __table_args__ = (
        # Full-text search index (PostgreSQL specific)
        Index(
            'idx_user_memories_content_fts',
            func.to_tsvector('english', 'content'),
            postgresql_using='gin'
        ),
        # Composite index for user + tier queries
        Index('idx_user_memories_user_tier', 'user_id', 'memory_tier'),
        # Index for decay-based queries
        Index('idx_user_memories_decay', 'user_id', 'decay_score'),
        # Index for time-based queries
        Index('idx_user_memories_accessed', 'user_id', 'last_accessed'),
        {'extend_existing': True}
    )

    # Primary Key
    id = Column(Integer, primary_key=True, index=True)

    # User relationship
    user_id = Column(Integer, ForeignKey('users.id'), nullable=False, index=True)

    # Memory content
    content = Column(Text, nullable=False)
    memory_type = Column(SQLEnum(MemoryType), default=MemoryType.CONVERSATION, nullable=False)

    # Metadata (flexible JSON storage)
    metadata = Column(JSONB, default={})
    """
    Metadata examples:
    - source: "conversation", "pdf_upload", "api_import"
    - tags: ["important", "project_x", "meeting"]
    - context: {"job_id": 123, "company": "Acme Corp"}
    - embedding_id: "chroma_collection_item_id"
    - chunk_index: 0 (for multi-chunk documents)
    - total_chunks: 5
    """

    # Importance and decay
    importance = Column(Float, default=0.5, nullable=False)
    """
    Importance score (0.0 to 1.0):
    - User-set importance (explicit)
    - AI-inferred importance (implicit)
    - Affects decay calculation
    """

    decay_score = Column(Float, default=1.0, nullable=False, index=True)
    """
    Decay score (0.0 to 1.0):
    - Calculated based on recency, frequency, importance
    - Updated hourly by background task
    - Determines tier placement:
      - > 0.8: Hot tier (Redis)
      - 0.3 - 0.8: Warm tier (PostgreSQL)
      - < 0.3: Cold tier (ChromaDB only)
    """

    # Access tracking
    access_count = Column(Integer, default=0, nullable=False)
    last_accessed = Column(DateTime, default=datetime.utcnow, index=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Tier management
    memory_tier = Column(SQLEnum(MemoryTier), default=MemoryTier.WARM, nullable=False, index=True)
    """
    Current tier placement:
    - HOT: In Redis cache (most accessed/recent)
    - WARM: In PostgreSQL only (moderate access)
    - COLD: Demoted to ChromaDB archive (rare access)
    """

    # Soft delete
    is_deleted = Column(Boolean, default=False, nullable=False)
    deleted_at = Column(DateTime, nullable=True)

    # Relationships
    user = relationship("User", backref="memories")

    def __repr__(self):
        return f"<UserMemory(id={self.id}, user_id={self.user_id}, tier={self.memory_tier}, score={self.decay_score:.2f})>"

    def to_dict(self) -> dict:
        """Convert memory to dictionary representation."""
        return {
            "id": self.id,
            "user_id": self.user_id,
            "content": self.content,
            "memory_type": self.memory_type.value if self.memory_type else None,
            "metadata": self.metadata or {},
            "importance": self.importance,
            "decay_score": self.decay_score,
            "access_count": self.access_count,
            "last_accessed": self.last_accessed.isoformat() if self.last_accessed else None,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
            "memory_tier": self.memory_tier.value if self.memory_tier else None,
            "is_deleted": self.is_deleted
        }

    def update_access(self):
        """Update access tracking when memory is accessed."""
        self.access_count += 1
        self.last_accessed = datetime.utcnow()

    def calculate_decay_score(
        self,
        recency_weight: float = 0.4,
        frequency_weight: float = 0.3,
        importance_weight: float = 0.3
    ) -> float:
        """
        Calculate decay score based on recency, frequency, and importance.

        Args:
            recency_weight: Weight for recency component (default 0.4)
            frequency_weight: Weight for frequency component (default 0.3)
            importance_weight: Weight for importance component (default 0.3)

        Returns:
            Decay score between 0.0 and 1.0
        """
        now = datetime.utcnow()

        # Recency score (exponential decay over 30 days)
        days_since_access = (now - self.last_accessed).total_seconds() / 86400
        recency_score = max(0.0, 1.0 - (days_since_access / 30.0))

        # Frequency score (normalized access count, max 100 accesses)
        frequency_score = min(1.0, self.access_count / 100.0)

        # Importance score (already 0-1)
        importance_score = self.importance

        # Combined decay score
        decay = (
            recency_weight * recency_score +
            frequency_weight * frequency_score +
            importance_weight * importance_score
        )

        return max(0.0, min(1.0, decay))

    def should_promote_to_hot(self) -> bool:
        """Check if memory should be promoted to hot tier."""
        return self.decay_score > 0.8 and self.memory_tier != MemoryTier.HOT

    def should_demote_to_cold(self) -> bool:
        """Check if memory should be demoted to cold tier."""
        return self.decay_score < 0.3 and self.memory_tier != MemoryTier.COLD


class MemoryAnalytics(Base):
    """
    Analytics tracking for memory system performance.

    Tracks cache hit rates, tier distribution, and access patterns
    to optimize memory system performance.
    """
    __tablename__ = "memory_analytics"
    __table_args__ = {'extend_existing': True}

    # Primary Key
    id = Column(Integer, primary_key=True, index=True)

    # Time bucket
    timestamp = Column(DateTime, default=datetime.utcnow, nullable=False, index=True)
    bucket_size = Column(String(20), default="hour", nullable=False)  # hour, day, week

    # User scope (null = system-wide)
    user_id = Column(Integer, ForeignKey('users.id'), nullable=True, index=True)

    # Cache performance
    hot_tier_hits = Column(Integer, default=0)
    warm_tier_hits = Column(Integer, default=0)
    cold_tier_hits = Column(Integer, default=0)
    cache_misses = Column(Integer, default=0)

    # Tier distribution
    hot_tier_count = Column(Integer, default=0)
    warm_tier_count = Column(Integer, default=0)
    cold_tier_count = Column(Integer, default=0)

    # Performance metrics
    avg_query_time_ms = Column(Float, nullable=True)
    total_queries = Column(Integer, default=0)

    # Memory usage
    total_memories = Column(Integer, default=0)
    total_size_kb = Column(Integer, default=0)

    # Relationships
    user = relationship("User", backref="memory_analytics")

    def __repr__(self):
        scope = f"user_id={self.user_id}" if self.user_id else "system"
        return f"<MemoryAnalytics({scope}, timestamp={self.timestamp})>"

    def cache_hit_rate(self) -> float:
        """Calculate overall cache hit rate (hot + warm / total)."""
        total = self.hot_tier_hits + self.warm_tier_hits + self.cold_tier_hits + self.cache_misses
        if total == 0:
            return 0.0
        hits = self.hot_tier_hits + self.warm_tier_hits
        return hits / total

    def hot_tier_hit_rate(self) -> float:
        """Calculate hot tier hit rate."""
        total = self.hot_tier_hits + self.warm_tier_hits + self.cold_tier_hits + self.cache_misses
        if total == 0:
            return 0.0
        return self.hot_tier_hits / total

    def to_dict(self) -> dict:
        """Convert analytics to dictionary."""
        return {
            "id": self.id,
            "timestamp": self.timestamp.isoformat() if self.timestamp else None,
            "bucket_size": self.bucket_size,
            "user_id": self.user_id,
            "cache_performance": {
                "hot_tier_hits": self.hot_tier_hits,
                "warm_tier_hits": self.warm_tier_hits,
                "cold_tier_hits": self.cold_tier_hits,
                "cache_misses": self.cache_misses,
                "cache_hit_rate": self.cache_hit_rate(),
                "hot_tier_hit_rate": self.hot_tier_hit_rate()
            },
            "tier_distribution": {
                "hot": self.hot_tier_count,
                "warm": self.warm_tier_count,
                "cold": self.cold_tier_count,
                "total": self.total_memories
            },
            "performance": {
                "avg_query_time_ms": self.avg_query_time_ms,
                "total_queries": self.total_queries
            },
            "storage": {
                "total_size_kb": self.total_size_kb
            }
        }
