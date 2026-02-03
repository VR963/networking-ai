"""Database Connection Pool - Singleton Supabase client with connection reuse.

PROBLEM SOLVED:
Before this, every service call created a NEW Supabase client:
  def _get_supabase():
      return create_client(SUPABASE_URL, SUPABASE_SERVICE_KEY)  # NEW connection every time

With 1000 concurrent users making 5 service calls each = 5000 connections.
Supabase connection limits: Free=60, Pro=300, Enterprise=1000+.

SOLUTION:
- Single shared client instance (thread-safe, connection-pooled)
- LRU cache for frequently queried data (agent profiles, patterns)
- Async-safe design compatible with FastAPI's async event loop
- Graceful degradation when DB is unavailable
"""

import time
import threading
from typing import Optional, Any
from collections import OrderedDict

from supabase import create_client, Client

from app.config import (
    SUPABASE_URL,
    SUPABASE_SERVICE_KEY,
    CACHE_TTL_SECONDS,
    CACHE_MAX_SIZE,
)


class LRUCache:
    """Thread-safe LRU cache with TTL expiration.

    Used for:
    - Agent profiles (fetched 10+ times per governance cycle)
    - User patterns (fetched during negotiations)
    - Config/settings that rarely change
    """

    def __init__(self, max_size: int = 1000, ttl_seconds: int = 300):
        self._cache: OrderedDict[str, tuple[float, Any]] = OrderedDict()
        self._max_size = max_size
        self._ttl = ttl_seconds
        self._lock = threading.Lock()
        self._hits = 0
        self._misses = 0

    def get(self, key: str) -> Optional[Any]:
        with self._lock:
            if key in self._cache:
                timestamp, value = self._cache[key]
                if time.time() - timestamp < self._ttl:
                    self._cache.move_to_end(key)
                    self._hits += 1
                    return value
                else:
                    del self._cache[key]
            self._misses += 1
            return None

    def set(self, key: str, value: Any) -> None:
        with self._lock:
            if key in self._cache:
                del self._cache[key]
            elif len(self._cache) >= self._max_size:
                self._cache.popitem(last=False)
            self._cache[key] = (time.time(), value)

    def invalidate(self, key: str) -> None:
        with self._lock:
            self._cache.pop(key, None)

    def invalidate_prefix(self, prefix: str) -> None:
        """Invalidate all keys starting with prefix."""
        with self._lock:
            keys_to_remove = [k for k in self._cache if k.startswith(prefix)]
            for k in keys_to_remove:
                del self._cache[k]

    def clear(self) -> None:
        with self._lock:
            self._cache.clear()

    @property
    def stats(self) -> dict:
        total = self._hits + self._misses
        return {
            "size": len(self._cache),
            "max_size": self._max_size,
            "hits": self._hits,
            "misses": self._misses,
            "hit_rate": round(self._hits / max(total, 1) * 100, 1),
        }


class DatabasePool:
    """Singleton database connection pool.

    Provides:
    - Single shared Supabase client (connection reuse)
    - Built-in LRU caching for hot data
    - Cache invalidation on writes
    - Graceful None returns when DB unavailable
    """

    _instance: Optional["DatabasePool"] = None
    _lock = threading.Lock()

    def __new__(cls) -> "DatabasePool":
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
                    cls._instance._initialized = False
        return cls._instance

    def __init__(self):
        if self._initialized:
            return
        self._client: Optional[Client] = None
        self._cache = LRUCache(max_size=CACHE_MAX_SIZE, ttl_seconds=CACHE_TTL_SECONDS)
        self._initialized = True

    @property
    def client(self) -> Optional[Client]:
        """Get the shared Supabase client. Creates on first access."""
        if self._client is None:
            if not SUPABASE_URL or not SUPABASE_SERVICE_KEY:
                return None
            self._client = create_client(SUPABASE_URL, SUPABASE_SERVICE_KEY)
        return self._client

    @property
    def cache(self) -> LRUCache:
        return self._cache

    def get_client(self) -> Optional[Client]:
        """Explicit method to get the client (same as .client property)."""
        return self.client

    def is_available(self) -> bool:
        """Check if database is configured and reachable."""
        return self.client is not None

    def reset(self) -> None:
        """Reset the connection (for testing or reconnection)."""
        self._client = None
        self._cache.clear()


# Module-level singleton access
_pool = DatabasePool()


def get_db() -> Optional[Client]:
    """Get the shared database client.

    Usage (replaces _get_supabase() in all services):
        from app.database import get_db
        client = get_db()
        if not client:
            return fallback_value
    """
    return _pool.client


def get_cache() -> LRUCache:
    """Get the shared cache instance.

    Usage:
        from app.database import get_cache
        cache = get_cache()

        # Read-through pattern:
        cached = cache.get(f"agent:{agent_id}")
        if cached:
            return cached
        data = fetch_from_db(agent_id)
        cache.set(f"agent:{agent_id}", data)
        return data
    """
    return _pool.cache


def invalidate_agent(agent_id: str) -> None:
    """Invalidate all cached data for an agent."""
    _pool.cache.invalidate_prefix(f"agent:{agent_id}")


def invalidate_user(user_id: str) -> None:
    """Invalidate all cached data for a user."""
    _pool.cache.invalidate_prefix(f"user:{user_id}")


def get_pool_stats() -> dict:
    """Get connection pool and cache statistics."""
    return {
        "db_available": _pool.is_available(),
        "cache": _pool.cache.stats,
    }
