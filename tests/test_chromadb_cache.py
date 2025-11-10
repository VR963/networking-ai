"""
Tests for ChromaDB Cache Service - Phase 2 Week 3.

Comprehensive tests for query caching optimization:
- Cache entry lifecycle
- LRU eviction
- TTL expiration
- Cache statistics
- Cache warming
- Performance improvements
"""

import sys
import os
import time
from datetime import datetime, timedelta

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

# Import directly from file to avoid cryptography issues
import importlib.util

cache_service_path = os.path.join(os.path.dirname(__file__), '..', 'src', 'networking_ai', 'services', 'chromadb_cache_service.py')
spec = importlib.util.spec_from_file_location("chromadb_cache_service", cache_service_path)
cache_service_module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(cache_service_module)

CacheEntry = cache_service_module.CacheEntry
ChromaDBCacheService = cache_service_module.ChromaDBCacheService
CachedChromaDBService = cache_service_module.CachedChromaDBService


# ==================== Test CacheEntry ====================

def test_cache_entry_creation():
    """Test creating a cache entry."""
    entry = CacheEntry(
        key="test_key",
        value={"result": "data"},
        ttl_seconds=3600
    )

    assert entry.key == "test_key"
    assert entry.value == {"result": "data"}
    assert entry.ttl_seconds == 3600
    assert entry.access_count == 0
    assert not entry.is_expired()

    print("✓ Cache entry created successfully")


def test_cache_entry_expiration():
    """Test cache entry expiration."""
    # Entry with very short TTL
    entry = CacheEntry(
        key="test_key",
        value="data",
        ttl_seconds=1  # 1 second
    )

    # Initially not expired
    assert not entry.is_expired()

    # Wait for expiration
    time.sleep(1.1)

    # Now expired
    assert entry.is_expired()

    print("✓ Cache entry expiration works correctly")


def test_cache_entry_access():
    """Test cache entry access tracking."""
    entry = CacheEntry(key="test", value="data", ttl_seconds=3600)

    assert entry.access_count == 0

    # Access multiple times
    entry.access()
    assert entry.access_count == 1

    entry.access()
    assert entry.access_count == 2

    entry.access()
    assert entry.access_count == 3

    print("✓ Cache entry access tracking works correctly")


def test_cache_entry_age():
    """Test cache entry age calculation."""
    entry = CacheEntry(key="test", value="data", ttl_seconds=3600)

    # Initially age should be ~0
    age = entry.age_seconds()
    assert age >= 0 and age < 1

    # Wait a bit
    time.sleep(0.5)

    # Age should be ~0.5
    age = entry.age_seconds()
    assert age >= 0.4 and age < 1

    print("✓ Cache entry age calculation works correctly")


# ==================== Test ChromaDBCacheService ====================

def test_cache_service_creation():
    """Test creating cache service."""
    cache = ChromaDBCacheService(
        max_cache_size=100,
        default_ttl=1800,
        enable_stats=True
    )

    assert cache.max_cache_size == 100
    assert cache.default_ttl == 1800
    assert cache.enable_stats == True

    stats = cache.get_stats()
    assert stats["hits"] == 0
    assert stats["misses"] == 0
    assert stats["current_size"] == 0

    print("✓ Cache service created successfully")


def test_cache_key_generation():
    """Test cache key generation."""
    cache = ChromaDBCacheService()

    # Same query should produce same key
    key1 = cache._generate_cache_key("talent_agent_1", "skills", 5)
    key2 = cache._generate_cache_key("talent_agent_1", "skills", 5)
    assert key1 == key2

    # Different query should produce different key
    key3 = cache._generate_cache_key("talent_agent_1", "experience", 5)
    assert key1 != key3

    # Different collection should produce different key
    key4 = cache._generate_cache_key("talent_agent_2", "skills", 5)
    assert key1 != key4

    # Different n_results should produce different key
    key5 = cache._generate_cache_key("talent_agent_1", "skills", 10)
    assert key1 != key5

    print("✓ Cache key generation works correctly")


def test_cache_set_and_get():
    """Test setting and getting cache entries."""
    cache = ChromaDBCacheService(default_ttl=3600)

    # Set entry
    cache.set(
        collection_name="talent_agent_1",
        query_text="skills",
        result={"documents": [["Python", "JavaScript", "SQL"]]},
        n_results=5
    )

    # Get entry (should hit)
    result = cache.get("talent_agent_1", "skills", 5)
    assert result is not None
    assert result["documents"][0] == ["Python", "JavaScript", "SQL"]

    # Check stats
    stats = cache.get_stats()
    assert stats["hits"] == 1
    assert stats["misses"] == 0
    assert stats["total_queries"] == 1
    assert stats["hit_rate"] == 1.0

    print("✓ Cache set and get work correctly")


def test_cache_miss():
    """Test cache miss."""
    cache = ChromaDBCacheService()

    # Try to get non-existent entry
    result = cache.get("talent_agent_1", "nonexistent", 5)
    assert result is None

    # Check stats
    stats = cache.get_stats()
    assert stats["misses"] == 1
    assert stats["total_queries"] == 1
    assert stats["hit_rate"] == 0.0

    print("✓ Cache miss works correctly")


def test_cache_expiration():
    """Test cache entry expiration."""
    cache = ChromaDBCacheService(default_ttl=1)  # 1 second TTL

    # Set entry
    cache.set("collection", "query", {"result": "data"}, ttl=1)

    # Should hit immediately
    result = cache.get("collection", "query")
    assert result is not None

    # Wait for expiration
    time.sleep(1.1)

    # Should miss after expiration
    result = cache.get("collection", "query")
    assert result is None

    # Check stats
    stats = cache.get_stats()
    assert stats["expirations"] == 1

    print("✓ Cache expiration works correctly")


def test_cache_lru_eviction():
    """Test LRU (Least Recently Used) eviction."""
    cache = ChromaDBCacheService(max_cache_size=3, default_ttl=3600)

    # Add 3 entries (fills cache)
    cache.set("col1", "query1", "result1")
    cache.set("col2", "query2", "result2")
    cache.set("col3", "query3", "result3")

    # All should be present
    assert cache.get("col1", "query1") is not None
    assert cache.get("col2", "query2") is not None
    assert cache.get("col3", "query3") is not None

    # Add 4th entry (should evict oldest)
    cache.set("col4", "query4", "result4")

    # col1 should be evicted (oldest, not accessed)
    assert cache.get("col1", "query1") is None

    # Others should still be present
    assert cache.get("col2", "query2") is not None
    assert cache.get("col3", "query3") is not None
    assert cache.get("col4", "query4") is not None

    # Check stats
    stats = cache.get_stats()
    assert stats["evictions"] == 1

    print("✓ LRU eviction works correctly")


def test_cache_invalidation():
    """Test cache invalidation."""
    cache = ChromaDBCacheService(default_ttl=3600)

    # Add entries for two collections
    cache.set("talent_agent_1", "skills", "result1")
    cache.set("talent_agent_1", "experience", "result2")
    cache.set("talent_agent_2", "skills", "result3")

    # Verify all present
    assert cache.get("talent_agent_1", "skills") is not None
    assert cache.get("talent_agent_1", "experience") is not None
    assert cache.get("talent_agent_2", "skills") is not None

    # Invalidate specific query
    cache.invalidate("talent_agent_1", "skills")
    assert cache.get("talent_agent_1", "skills") is None
    assert cache.get("talent_agent_1", "experience") is not None

    # Invalidate entire collection
    cache.invalidate("talent_agent_1")
    assert cache.get("talent_agent_1", "experience") is None
    assert cache.get("talent_agent_2", "skills") is not None  # Different collection

    # Invalidate all
    cache.invalidate()
    assert cache.get("talent_agent_2", "skills") is None

    print("✓ Cache invalidation works correctly")


def test_cache_cleanup_expired():
    """Test cleanup of expired entries."""
    cache = ChromaDBCacheService(default_ttl=1)

    # Add multiple entries with short TTL
    cache.set("col1", "query1", "result1", ttl=1)
    cache.set("col2", "query2", "result2", ttl=1)
    cache.set("col3", "query3", "result3", ttl=10)  # Long TTL

    # Wait for expiration
    time.sleep(1.1)

    # Clean up
    removed = cache.cleanup_expired()

    # Should have removed 2 expired entries
    assert removed == 2

    # Only long TTL entry should remain
    assert cache.get("col3", "query3") is not None

    print("✓ Cache cleanup works correctly")


def test_cache_statistics():
    """Test cache statistics tracking."""
    cache = ChromaDBCacheService(max_cache_size=10, default_ttl=3600)

    # Perform various operations
    cache.set("col1", "query1", "result1")
    cache.set("col2", "query2", "result2")

    # Hit
    cache.get("col1", "query1")

    # Miss
    cache.get("col3", "query3")

    # Another hit
    cache.get("col2", "query2")

    # Get stats
    stats = cache.get_stats()

    assert stats["hits"] == 2
    assert stats["misses"] == 1
    assert stats["total_queries"] == 3
    assert abs(stats["hit_rate"] - 0.667) < 0.01  # Approximate comparison
    assert stats["current_size"] == 2
    assert stats["max_size"] == 10
    assert stats["fill_percentage"] == 20.0

    print("✓ Cache statistics work correctly")


def test_cache_info():
    """Test cache info retrieval."""
    cache = ChromaDBCacheService(default_ttl=3600)

    # Add entries
    cache.set("col1", "query1", "result1")
    cache.set("col2", "query2", "result2")

    # Access first entry multiple times
    cache.get("col1", "query1")
    cache.get("col1", "query1")

    # Get cache info
    info = cache.get_cache_info(limit=10)

    assert len(info) == 2

    # Check that we have one entry with 2 accesses and one with 0
    access_counts = [entry["access_count"] for entry in info]
    assert 2 in access_counts  # One entry accessed twice
    assert 0 in access_counts  # One entry not accessed

    print("✓ Cache info retrieval works correctly")


# ==================== Test CachedChromaDBService ====================

class MockChromaDBService:
    """Mock ChromaDB service for testing."""

    def __init__(self):
        self.query_count = 0

    def query_collection(self, collection_name, query_texts, n_results):
        self.query_count += 1
        return {
            "documents": [[f"result_{i}" for i in range(n_results)]],
            "metadatas": [[{} for _ in range(n_results)]],
            "distances": [[0.1 * i for i in range(n_results)]]
        }

    def query_talent_profile(self, collection_name, query, n_results):
        self.query_count += 1
        return {"skills": ["Python", "SQL"], "experience": "5 years"}


def test_cached_service_with_cache():
    """Test cached service with caching enabled."""
    mock_service = MockChromaDBService()
    cached_service = CachedChromaDBService(
        chromadb_service=mock_service,
        enable_cache=True
    )

    # First query (miss, should hit DB)
    result1 = cached_service.query_collection("col1", ["query1"], 5)
    assert mock_service.query_count == 1

    # Second identical query (hit, should NOT hit DB)
    result2 = cached_service.query_collection("col1", ["query1"], 5)
    assert mock_service.query_count == 1  # Still 1!

    # Results should be identical
    assert result1 == result2

    # Check cache stats
    stats = cached_service.get_cache_stats()
    assert stats["hits"] == 1
    assert stats["misses"] == 1

    print("✓ Cached service with caching works correctly")


def test_cached_service_without_cache():
    """Test cached service with caching disabled."""
    mock_service = MockChromaDBService()
    cached_service = CachedChromaDBService(
        chromadb_service=mock_service,
        enable_cache=False
    )

    # Both queries should hit DB
    result1 = cached_service.query_collection("col1", ["query1"], 5)
    assert mock_service.query_count == 1

    result2 = cached_service.query_collection("col1", ["query1"], 5)
    assert mock_service.query_count == 2  # Hit DB again

    print("✓ Cached service without caching works correctly")


def test_cached_service_cache_bypass():
    """Test bypassing cache with use_cache=False."""
    mock_service = MockChromaDBService()
    cached_service = CachedChromaDBService(
        chromadb_service=mock_service,
        enable_cache=True
    )

    # Query with cache
    result1 = cached_service.query_collection("col1", ["query1"], 5, use_cache=True)
    assert mock_service.query_count == 1

    # Same query but bypass cache
    result2 = cached_service.query_collection("col1", ["query1"], 5, use_cache=False)
    assert mock_service.query_count == 2  # Hit DB again

    print("✓ Cache bypass works correctly")


def test_cached_service_invalidation():
    """Test cache invalidation in cached service."""
    mock_service = MockChromaDBService()
    cached_service = CachedChromaDBService(
        chromadb_service=mock_service,
        enable_cache=True
    )

    # Cache query
    cached_service.query_collection("col1", ["query1"], 5)
    assert mock_service.query_count == 1

    # Query again (should hit cache)
    cached_service.query_collection("col1", ["query1"], 5)
    assert mock_service.query_count == 1

    # Invalidate
    cached_service.invalidate_collection("col1")

    # Query again (should hit DB)
    cached_service.query_collection("col1", ["query1"], 5)
    assert mock_service.query_count == 2

    print("✓ Cache invalidation in cached service works correctly")


# ==================== Performance Tests ====================

def test_cache_performance_improvement():
    """Test that caching improves performance."""
    mock_service = MockChromaDBService()
    cached_service = CachedChromaDBService(
        chromadb_service=mock_service,
        enable_cache=True
    )

    # Warm up cache
    cached_service.query_collection("col1", ["query1"], 5)

    # Measure cache hit performance
    start = time.time()
    for _ in range(100):
        cached_service.query_collection("col1", ["query1"], 5)
    cached_time = time.time() - start

    # Only 1 DB query should have been made
    assert mock_service.query_count == 1

    # Cache hits should be fast
    assert cached_time < 0.1  # Should complete in < 100ms

    print(f"✓ Cache performance: 100 queries in {cached_time*1000:.2f}ms")
    print(f"✓ Cache saved {99} database queries")


# ==================== Run All Tests ====================

if __name__ == "__main__":
    print("\n" + "="*70)
    print("ChromaDB Cache Service Tests")
    print("="*70 + "\n")

    # CacheEntry tests
    print("1. Testing CacheEntry...")
    test_cache_entry_creation()
    test_cache_entry_expiration()
    test_cache_entry_access()
    test_cache_entry_age()

    # ChromaDBCacheService tests
    print("\n2. Testing ChromaDBCacheService...")
    test_cache_service_creation()
    test_cache_key_generation()
    test_cache_set_and_get()
    test_cache_miss()
    test_cache_expiration()
    test_cache_lru_eviction()
    test_cache_invalidation()
    test_cache_cleanup_expired()
    test_cache_statistics()
    test_cache_info()

    # CachedChromaDBService tests
    print("\n3. Testing CachedChromaDBService...")
    test_cached_service_with_cache()
    test_cached_service_without_cache()
    test_cached_service_cache_bypass()
    test_cached_service_invalidation()

    # Performance tests
    print("\n4. Testing Performance...")
    test_cache_performance_improvement()

    print("\n" + "="*70)
    print("✅ All Cache Tests Passed! (19 tests)")
    print("="*70 + "\n")
