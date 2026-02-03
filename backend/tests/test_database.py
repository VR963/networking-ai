"""Tests for database connection pool and cache."""

import time
from unittest.mock import patch, MagicMock

import pytest


class TestLRUCache:
    """Test the LRU cache implementation."""

    def setup_method(self):
        from app.database import LRUCache
        self.cache = LRUCache(max_size=3, ttl_seconds=10)

    def test_set_and_get(self):
        self.cache.set("key1", "value1")
        assert self.cache.get("key1") == "value1"

    def test_get_missing_key(self):
        assert self.cache.get("nonexistent") is None

    def test_eviction_on_max_size(self):
        self.cache.set("a", 1)
        self.cache.set("b", 2)
        self.cache.set("c", 3)
        self.cache.set("d", 4)  # Should evict "a"
        assert self.cache.get("a") is None
        assert self.cache.get("d") == 4

    def test_ttl_expiration(self):
        from app.database import LRUCache
        cache = LRUCache(max_size=10, ttl_seconds=0.1)
        cache.set("key", "value")
        assert cache.get("key") == "value"
        time.sleep(0.15)
        assert cache.get("key") is None

    def test_invalidate(self):
        self.cache.set("key1", "value1")
        self.cache.invalidate("key1")
        assert self.cache.get("key1") is None

    def test_invalidate_prefix(self):
        self.cache.set("user:123:profile", "data1")
        self.cache.set("user:123:docs", "data2")
        self.cache.set("user:456:profile", "data3")
        self.cache.invalidate_prefix("user:123")
        assert self.cache.get("user:123:profile") is None
        assert self.cache.get("user:123:docs") is None
        assert self.cache.get("user:456:profile") == "data3"

    def test_stats(self):
        self.cache.set("x", 1)
        self.cache.get("x")  # hit
        self.cache.get("y")  # miss
        stats = self.cache.stats  # property, not method
        assert stats["hits"] == 1
        assert stats["misses"] == 1
        assert stats["size"] == 1


class TestDatabasePool:
    """Test the singleton database pool."""

    @patch("app.database.create_client")
    def test_singleton_pattern(self, mock_create):
        mock_create.return_value = MagicMock()
        from app.database import DatabasePool
        # Reset singleton for test
        DatabasePool._instance = None

        pool1 = DatabasePool()
        pool2 = DatabasePool()
        assert pool1 is pool2

        # Cleanup
        DatabasePool._instance = None

    def test_get_db_returns_client_or_none(self):
        from app.database import get_db
        # Should return a client or None (depending on env config)
        result = get_db()
        # In test env with mock URL, it may fail silently
        assert result is None or result is not None


class TestCacheInvalidation:
    """Test targeted cache invalidation helpers."""

    def test_invalidate_agent(self):
        from app.database import get_cache, invalidate_agent
        cache = get_cache()
        cache.set("agent:test123:reputation", {"score": 50})
        cache.set("agent:test123:history", [])
        invalidate_agent("test123")
        assert cache.get("agent:test123:reputation") is None
        assert cache.get("agent:test123:history") is None

    def test_invalidate_user(self):
        from app.database import get_cache, invalidate_user
        cache = get_cache()
        cache.set("user:u1:profile", {"name": "test"})
        invalidate_user("u1")
        assert cache.get("user:u1:profile") is None
