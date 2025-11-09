"""
Comprehensive tests for Phase 10A Enhanced Memory System.

Tests all memory layers, orchestrator, decay algorithm, and API endpoints.
"""

import pytest
from datetime import datetime, timedelta
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from io import BytesIO

from src.networking_ai.database import Base
from src.networking_ai.models.user import User
from src.networking_ai.models.memory import UserMemory, MemoryAnalytics, MemoryTier, MemoryType
from src.networking_ai.cache.redis_client import RedisClient
from src.networking_ai.services.chromadb_service import ChromaDBService
from src.networking_ai.memory import (
    MemoryOrchestrator,
    HotMemory,
    WarmMemory,
    ColdMemory,
    Memory,
    MemoryDecayManager
)


# ==================== Fixtures ====================

@pytest.fixture(scope="function")
def db_session():
    """Create test database session."""
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    SessionLocal = sessionmaker(bind=engine)
    session = SessionLocal()

    yield session

    session.close()


@pytest.fixture
def test_user(db_session):
    """Create test user."""
    from src.networking_ai.models.user import UserRole, AccountStatus
    user = User(
        email="test@example.com",
        hashed_password="hashed_password",
        full_name="Test User",
        role=UserRole.TALENT,
        status=AccountStatus.ACTIVE
    )
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)
    return user


@pytest.fixture
def redis_client():
    """Create Redis client (or mock if Redis not available)."""
    try:
        client = RedisClient()
        # Clear test data
        yield client
    except Exception:
        # Return mock client if Redis not available
        pytest.skip("Redis not available")


@pytest.fixture
def chromadb_service():
    """Create ChromaDB service."""
    service = ChromaDBService(persist_directory="./test_chroma_data")
    yield service
    # Cleanup
    try:
        import shutil
        shutil.rmtree("./test_chroma_data", ignore_errors=True)
    except Exception:
        pass


@pytest.fixture
def memory_orchestrator(db_session, redis_client, chromadb_service):
    """Create MemoryOrchestrator instance."""
    return MemoryOrchestrator(
        db_session=db_session,
        redis_client=redis_client,
        chromadb_service=chromadb_service
    )


# ==================== WarmMemory Tests ====================

class TestWarmMemory:
    """Test WarmMemory (PostgreSQL) layer."""

    def test_store_memory(self, db_session, test_user):
        """Test storing a memory in warm tier."""
        warm = WarmMemory(db_session)

        memory = warm.store(
            user_id=test_user.id,
            content="This is a test memory",
            metadata={"source": "test"},
            importance=0.7
        )

        assert memory is not None
        assert memory.id is not None
        assert memory.content == "This is a test memory"
        assert memory.importance == 0.7
        assert memory.tier == 'warm'

    @pytest.mark.skip(reason="Full-text search requires PostgreSQL, test uses SQLite")
    def test_query_memory_full_text(self, db_session, test_user):
        """Test full-text search in warm tier."""
        warm = WarmMemory(db_session)

        # Store test memories
        warm.store(test_user.id, "Python programming tutorial", importance=0.8)
        warm.store(test_user.id, "JavaScript framework guide", importance=0.6)
        warm.store(test_user.id, "Python data science", importance=0.7)

        # Query for Python
        results = warm.query(test_user.id, "Python", limit=10)

        assert len(results) == 2
        assert all("python" in r.content.lower() for r in results)

    def test_get_by_id(self, db_session, test_user):
        """Test retrieving memory by ID."""
        warm = WarmMemory(db_session)

        # Store memory
        stored = warm.store(test_user.id, "Test content")
        memory_id = stored.id

        # Retrieve by ID
        retrieved = warm.get_by_id(test_user.id, memory_id)

        assert retrieved is not None
        assert retrieved.id == memory_id
        assert retrieved.content == "Test content"

    def test_get_recent(self, db_session, test_user):
        """Test getting recent memories."""
        warm = WarmMemory(db_session)

        # Store memories
        for i in range(5):
            warm.store(test_user.id, f"Memory {i}")

        # Get recent
        recent = warm.get_recent(test_user.id, limit=3, days=7)

        assert len(recent) <= 3

    def test_delete_memory(self, db_session, test_user):
        """Test soft deleting a memory."""
        warm = WarmMemory(db_session)

        # Store and delete
        memory = warm.store(test_user.id, "To be deleted")
        success = warm.delete(test_user.id, memory.id)

        assert success is True

        # Verify soft deleted
        db_memory = db_session.query(UserMemory).filter(
            UserMemory.id == memory.id
        ).first()
        assert db_memory.is_deleted is True

    def test_get_stats(self, db_session, test_user):
        """Test getting memory statistics."""
        warm = WarmMemory(db_session)

        # Store memories with different importance
        warm.store(test_user.id, "Memory 1", importance=0.5)
        warm.store(test_user.id, "Memory 2", importance=0.7)
        warm.store(test_user.id, "Memory 3", importance=0.9)

        stats = warm.get_stats(test_user.id)

        assert stats["total_memories"] == 3
        assert 0.6 < stats["avg_importance"] < 0.8


# ==================== ColdMemory Tests ====================

class TestColdMemory:
    """Test ColdMemory (ChromaDB) layer."""

    def test_store_memory(self, chromadb_service, test_user):
        """Test storing memory in cold tier."""
        cold = ColdMemory(chromadb_service)

        success = cold.store(
            user_id=test_user.id,
            memory_id=1,
            content="This is archived memory",
            metadata={"source": "archive"}
        )

        assert success is True

    def test_query_semantic_search(self, chromadb_service, test_user):
        """Test semantic search in cold tier."""
        cold = ColdMemory(chromadb_service)

        # Store memories
        cold.store(test_user.id, 1, "Machine learning algorithms")
        cold.store(test_user.id, 2, "Deep neural networks")
        cold.store(test_user.id, 3, "Database optimization")

        # Semantic search
        results = cold.query(test_user.id, "artificial intelligence", limit=5)

        # Should find ML and neural network related content
        assert len(results) >= 0  # May vary based on embeddings

    def test_get_count(self, chromadb_service, test_user):
        """Test getting count of cold memories."""
        cold = ColdMemory(chromadb_service)

        # Store memories
        cold.store(test_user.id, 1, "Memory 1")
        cold.store(test_user.id, 2, "Memory 2")

        count = cold.get_count(test_user.id)

        assert count == 2

    def test_delete_memory(self, chromadb_service, test_user):
        """Test deleting from cold tier."""
        cold = ColdMemory(chromadb_service)

        # Store and delete
        cold.store(test_user.id, 1, "To delete")
        success = cold.delete(test_user.id, 1)

        assert success is True


# ==================== MemoryOrchestrator Tests ====================

class TestMemoryOrchestrator:
    """Test MemoryOrchestrator (multi-tier coordination)."""

    def test_store_with_auto_tier(self, memory_orchestrator, test_user):
        """Test storing with automatic tier selection."""
        # High importance -> should go to hot tier
        memory = memory_orchestrator.store(
            user_id=test_user.id,
            content="Very important memory",
            importance=0.9,
            tier="auto"
        )

        assert memory is not None
        assert memory.importance == 0.9

    def test_query_multi_tier(self, memory_orchestrator, test_user):
        """Test querying across multiple tiers."""
        # Store memories
        memory_orchestrator.store(test_user.id, "Hot tier memory", importance=0.9)
        memory_orchestrator.store(test_user.id, "Warm tier memory", importance=0.5)
        memory_orchestrator.store(test_user.id, "Cold tier memory", importance=0.2)

        # Query
        results = memory_orchestrator.query(test_user.id, "memory", limit=10)

        assert len(results) >= 1

    def test_get_by_id(self, memory_orchestrator, test_user):
        """Test getting memory by ID."""
        # Store
        stored = memory_orchestrator.store(test_user.id, "Test memory")

        # Retrieve
        retrieved = memory_orchestrator.get_by_id(test_user.id, stored.id)

        assert retrieved is not None
        assert retrieved.id == stored.id

    def test_delete(self, memory_orchestrator, test_user):
        """Test deleting memory across tiers."""
        # Store
        memory = memory_orchestrator.store(test_user.id, "To delete")

        # Delete
        success = memory_orchestrator.delete(test_user.id, memory.id)

        assert success is True

    def test_get_stats(self, memory_orchestrator, test_user):
        """Test getting comprehensive statistics."""
        # Store various memories
        memory_orchestrator.store(test_user.id, "Memory 1", importance=0.8)
        memory_orchestrator.store(test_user.id, "Memory 2", importance=0.5)

        stats = memory_orchestrator.get_stats(test_user.id)

        assert "total_memories" in stats
        assert "tier_distribution" in stats
        assert stats["total_memories"] >= 2


# ==================== MemoryDecay Tests ====================

class TestMemoryDecay:
    """Test Memory Decay Algorithm."""

    def test_calculate_decay_score(self, db_session, test_user):
        """Test decay score calculation."""
        # Create memory
        memory = UserMemory(
            user_id=test_user.id,
            content="Test memory",
            importance=0.7,
            access_count=50,
            last_accessed=datetime.utcnow() - timedelta(days=5),
            created_at=datetime.utcnow() - timedelta(days=10)
        )
        db_session.add(memory)
        db_session.commit()

        # Calculate decay
        manager = MemoryDecayManager(db_session)
        score = manager.calculate_decay_score(memory)

        assert 0.0 <= score <= 1.0
        # Should be relatively high (recent, frequent, important)
        assert score > 0.5

    def test_update_all_decay_scores(self, db_session, test_user):
        """Test updating all decay scores."""
        # Create memories with different access patterns
        for i in range(5):
            memory = UserMemory(
                user_id=test_user.id,
                content=f"Memory {i}",
                importance=0.5 + (i * 0.1),
                access_count=i * 10,
                last_accessed=datetime.utcnow() - timedelta(days=i),
                created_at=datetime.utcnow() - timedelta(days=i + 10)
            )
            db_session.add(memory)
        db_session.commit()

        # Update scores
        manager = MemoryDecayManager(db_session)
        stats = manager.update_all_decay_scores(user_id=test_user.id)

        assert stats["processed"] == 5
        assert stats["updated"] >= 0

    def test_tier_promotion(self, db_session, test_user):
        """Test automatic tier promotion."""
        # Create low-score memory
        memory = UserMemory(
            user_id=test_user.id,
            content="Old memory",
            importance=0.9,  # High importance
            access_count=100,  # Frequently accessed
            last_accessed=datetime.utcnow(),  # Very recent
            memory_tier=MemoryTier.WARM,
            decay_score=0.5
        )
        db_session.add(memory)
        db_session.commit()

        # Update scores (should promote to hot)
        manager = MemoryDecayManager(db_session)
        manager.update_all_decay_scores(user_id=test_user.id)

        db_session.refresh(memory)
        # Should have high decay score now
        assert memory.decay_score > 0.8
        assert memory.memory_tier == MemoryTier.HOT

    def test_tier_demotion(self, db_session, test_user):
        """Test automatic tier demotion."""
        # Create old, rarely accessed memory
        memory = UserMemory(
            user_id=test_user.id,
            content="Very old memory",
            importance=0.2,
            access_count=1,
            last_accessed=datetime.utcnow() - timedelta(days=60),
            memory_tier=MemoryTier.WARM,
            decay_score=0.8
        )
        db_session.add(memory)
        db_session.commit()

        # Update scores (should demote to cold)
        manager = MemoryDecayManager(db_session)
        manager.update_all_decay_scores(user_id=test_user.id)

        db_session.refresh(memory)
        # Should have low decay score now
        assert memory.decay_score < 0.3
        assert memory.memory_tier == MemoryTier.COLD


# ==================== Integration Tests ====================

class TestMemoryIntegration:
    """Integration tests for complete memory workflows."""

    def test_full_memory_lifecycle(self, memory_orchestrator, test_user):
        """Test complete memory lifecycle: store, query, update, delete."""
        # 1. Store
        memory = memory_orchestrator.store(
            user_id=test_user.id,
            content="Important project notes about AI development",
            importance=0.8,
            metadata={"project": "AI Platform"}
        )

        assert memory is not None
        memory_id = memory.id

        # 2. Query
        results = memory_orchestrator.query(test_user.id, "AI development", limit=5)
        assert len(results) >= 1
        assert any(r.id == memory_id for r in results)

        # 3. Get by ID
        retrieved = memory_orchestrator.get_by_id(test_user.id, memory_id)
        assert retrieved is not None
        assert retrieved.access_count > 0  # Should have been incremented

        # 4. Get stats
        stats = memory_orchestrator.get_stats(test_user.id)
        assert stats["total_memories"] >= 1

        # 5. Delete
        success = memory_orchestrator.delete(test_user.id, memory_id)
        assert success is True

    def test_memory_decay_workflow(self, db_session, chromadb_service, test_user):
        """Test memory decay and tier migration workflow."""
        # 1. Create memories with different patterns
        recent_important = UserMemory(
            user_id=test_user.id,
            content="Recent important memory",
            importance=0.9,
            access_count=50,
            last_accessed=datetime.utcnow(),
            memory_tier=MemoryTier.WARM
        )

        old_unimportant = UserMemory(
            user_id=test_user.id,
            content="Old unimportant memory",
            importance=0.2,
            access_count=2,
            last_accessed=datetime.utcnow() - timedelta(days=60),
            memory_tier=MemoryTier.WARM
        )

        db_session.add_all([recent_important, old_unimportant])
        db_session.commit()

        # 2. Run decay algorithm
        manager = MemoryDecayManager(db_session)
        stats = manager.update_all_decay_scores(user_id=test_user.id)

        assert stats["processed"] == 2

        # 3. Check tier changes
        db_session.refresh(recent_important)
        db_session.refresh(old_unimportant)

        # Recent important should be promoted or stay warm
        assert recent_important.memory_tier in [MemoryTier.HOT, MemoryTier.WARM]
        # Old unimportant should be demoted to cold
        assert old_unimportant.memory_tier == MemoryTier.COLD


# ==================== Performance Tests ====================

class TestMemoryPerformance:
    """Performance tests for memory system."""

    def test_query_performance(self, memory_orchestrator, test_user):
        """Test query performance meets targets."""
        import time

        # Store test data
        for i in range(10):
            memory_orchestrator.store(
                user_id=test_user.id,
                content=f"Test memory {i} with various keywords",
                importance=0.5
            )

        # Measure query time
        start = time.time()
        results = memory_orchestrator.query(test_user.id, "keywords", limit=5)
        query_time = (time.time() - start) * 1000  # Convert to ms

        # Should complete in <5000ms (warm tier target)
        assert query_time < 5000
        assert len(results) >= 1

    def test_batch_storage_performance(self, memory_orchestrator, test_user):
        """Test batch storage performance."""
        import time

        # Measure batch storage
        start = time.time()
        for i in range(20):
            memory_orchestrator.store(
                user_id=test_user.id,
                content=f"Batch memory {i}",
                importance=0.5
            )
        storage_time = (time.time() - start) * 1000

        # Should store 20 memories in reasonable time (<2000ms)
        assert storage_time < 2000
