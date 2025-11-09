"""
Redis client wrapper for hot memory caching and general application caching.

Provides connection pooling, health checks, and convenient async/sync interfaces.
"""

import json
import logging
from typing import Optional, Any, Dict
from datetime import timedelta

try:
    import redis
    from redis.connection import ConnectionPool
    REDIS_AVAILABLE = True
except ImportError:
    REDIS_AVAILABLE = False
    redis = None
    ConnectionPool = None

from ..config import config

logger = logging.getLogger(__name__)


class RedisClient:
    """
    Redis client wrapper with connection pooling and health checks.

    Features:
    - Connection pooling (configurable size)
    - Automatic reconnection
    - Health checks
    - JSON serialization helpers
    - TTL management
    - Graceful degradation if Redis unavailable
    """

    def __init__(
        self,
        host: str = 'localhost',
        port: int = 6379,
        db: int = 0,
        password: Optional[str] = None,
        max_connections: int = 50,
        socket_timeout: int = 5,
        socket_connect_timeout: int = 5,
        decode_responses: bool = True
    ):
        """
        Initialize Redis client with connection pool.

        Args:
            host: Redis server host
            port: Redis server port
            db: Redis database number (0-15)
            password: Redis password (if required)
            max_connections: Maximum connections in pool
            socket_timeout: Socket timeout in seconds
            socket_connect_timeout: Connection timeout in seconds
            decode_responses: Decode byte responses to strings
        """
        self.available = REDIS_AVAILABLE

        if not self.available:
            logger.warning("Redis not available - falling back to in-memory cache")
            self._in_memory_cache: Dict[str, Any] = {}
            self.client = None
            self.pool = None
            return

        try:
            # Create connection pool
            self.pool = ConnectionPool(
                host=host,
                port=port,
                db=db,
                password=password,
                max_connections=max_connections,
                socket_timeout=socket_timeout,
                socket_connect_timeout=socket_connect_timeout,
                decode_responses=decode_responses
            )

            # Create Redis client
            self.client = redis.Redis(connection_pool=self.pool)

            # Test connection
            self.client.ping()
            logger.info(f"Redis connected successfully: {host}:{port}/{db}")

        except Exception as e:
            logger.error(f"Failed to connect to Redis: {e}")
            logger.warning("Falling back to in-memory cache")
            self.available = False
            self._in_memory_cache: Dict[str, Any] = {}
            self.client = None
            self.pool = None

    def health_check(self) -> bool:
        """
        Check if Redis is healthy.

        Returns:
            bool: True if Redis is responding, False otherwise
        """
        if not self.available or not self.client:
            return False

        try:
            return self.client.ping()
        except Exception as e:
            logger.error(f"Redis health check failed: {e}")
            return False

    # ==================== Basic Operations ====================

    def get(self, key: str) -> Optional[str]:
        """
        Get value by key.

        Args:
            key: Redis key

        Returns:
            Value as string, or None if key doesn't exist
        """
        if not self.available or not self.client:
            return self._in_memory_cache.get(key)

        try:
            return self.client.get(key)
        except Exception as e:
            logger.error(f"Redis GET error for key '{key}': {e}")
            return None

    def set(
        self,
        key: str,
        value: str,
        ex: Optional[int] = None,
        px: Optional[int] = None,
        nx: bool = False,
        xx: bool = False
    ) -> bool:
        """
        Set key to value.

        Args:
            key: Redis key
            value: Value to store
            ex: Expiration in seconds
            px: Expiration in milliseconds
            nx: Only set if key doesn't exist
            xx: Only set if key exists

        Returns:
            bool: True if successful
        """
        if not self.available or not self.client:
            self._in_memory_cache[key] = value
            return True

        try:
            return bool(self.client.set(key, value, ex=ex, px=px, nx=nx, xx=xx))
        except Exception as e:
            logger.error(f"Redis SET error for key '{key}': {e}")
            return False

    def delete(self, *keys: str) -> int:
        """
        Delete one or more keys.

        Args:
            keys: Keys to delete

        Returns:
            Number of keys deleted
        """
        if not self.available or not self.client:
            count = 0
            for key in keys:
                if key in self._in_memory_cache:
                    del self._in_memory_cache[key]
                    count += 1
            return count

        try:
            return self.client.delete(*keys)
        except Exception as e:
            logger.error(f"Redis DELETE error: {e}")
            return 0

    def exists(self, *keys: str) -> int:
        """
        Check if keys exist.

        Args:
            keys: Keys to check

        Returns:
            Number of existing keys
        """
        if not self.available or not self.client:
            return sum(1 for key in keys if key in self._in_memory_cache)

        try:
            return self.client.exists(*keys)
        except Exception as e:
            logger.error(f"Redis EXISTS error: {e}")
            return 0

    def expire(self, key: str, seconds: int) -> bool:
        """
        Set key expiration.

        Args:
            key: Redis key
            seconds: Expiration in seconds

        Returns:
            bool: True if successful
        """
        if not self.available or not self.client:
            return True  # In-memory cache doesn't support expiration

        try:
            return bool(self.client.expire(key, seconds))
        except Exception as e:
            logger.error(f"Redis EXPIRE error for key '{key}': {e}")
            return False

    # ==================== Hash Operations ====================

    def hget(self, name: str, key: str) -> Optional[str]:
        """Get value from hash."""
        if not self.available or not self.client:
            hash_dict = self._in_memory_cache.get(name, {})
            return hash_dict.get(key) if isinstance(hash_dict, dict) else None

        try:
            return self.client.hget(name, key)
        except Exception as e:
            logger.error(f"Redis HGET error: {e}")
            return None

    def hset(self, name: str, key: str, value: str) -> int:
        """Set value in hash."""
        if not self.available or not self.client:
            if name not in self._in_memory_cache:
                self._in_memory_cache[name] = {}
            if isinstance(self._in_memory_cache[name], dict):
                self._in_memory_cache[name][key] = value
            return 1

        try:
            return self.client.hset(name, key, value)
        except Exception as e:
            logger.error(f"Redis HSET error: {e}")
            return 0

    def hgetall(self, name: str) -> dict:
        """Get all fields and values from hash."""
        if not self.available or not self.client:
            value = self._in_memory_cache.get(name, {})
            return value if isinstance(value, dict) else {}

        try:
            return self.client.hgetall(name)
        except Exception as e:
            logger.error(f"Redis HGETALL error: {e}")
            return {}

    def hdel(self, name: str, *keys: str) -> int:
        """Delete fields from hash."""
        if not self.available or not self.client:
            hash_dict = self._in_memory_cache.get(name, {})
            if isinstance(hash_dict, dict):
                count = sum(1 for key in keys if hash_dict.pop(key, None) is not None)
                return count
            return 0

        try:
            return self.client.hdel(name, *keys)
        except Exception as e:
            logger.error(f"Redis HDEL error: {e}")
            return 0

    def hlen(self, name: str) -> int:
        """Get number of fields in hash."""
        if not self.available or not self.client:
            hash_dict = self._in_memory_cache.get(name, {})
            return len(hash_dict) if isinstance(hash_dict, dict) else 0

        try:
            return self.client.hlen(name)
        except Exception as e:
            logger.error(f"Redis HLEN error: {e}")
            return 0

    # ==================== JSON Helpers ====================

    def get_json(self, key: str) -> Optional[Any]:
        """
        Get and deserialize JSON value.

        Args:
            key: Redis key

        Returns:
            Deserialized Python object, or None
        """
        value = self.get(key)
        if value is None:
            return None

        try:
            return json.loads(value)
        except json.JSONDecodeError as e:
            logger.error(f"Failed to decode JSON for key '{key}': {e}")
            return None

    def set_json(
        self,
        key: str,
        value: Any,
        ex: Optional[int] = None
    ) -> bool:
        """
        Serialize and set JSON value.

        Args:
            key: Redis key
            value: Python object to serialize
            ex: Expiration in seconds

        Returns:
            bool: True if successful
        """
        try:
            json_value = json.dumps(value)
            return self.set(key, json_value, ex=ex)
        except (TypeError, ValueError) as e:
            logger.error(f"Failed to serialize value for key '{key}': {e}")
            return False

    # ==================== Increment/Decrement ====================

    def incr(self, key: str, amount: int = 1) -> int:
        """
        Increment value.

        Args:
            key: Redis key
            amount: Amount to increment by

        Returns:
            New value
        """
        if not self.available or not self.client:
            current = int(self._in_memory_cache.get(key, 0))
            new_value = current + amount
            self._in_memory_cache[key] = str(new_value)
            return new_value

        try:
            return self.client.incrby(key, amount)
        except Exception as e:
            logger.error(f"Redis INCR error: {e}")
            return 0

    def decr(self, key: str, amount: int = 1) -> int:
        """
        Decrement value.

        Args:
            key: Redis key
            amount: Amount to decrement by

        Returns:
            New value
        """
        if not self.available or not self.client:
            current = int(self._in_memory_cache.get(key, 0))
            new_value = current - amount
            self._in_memory_cache[key] = str(new_value)
            return new_value

        try:
            return self.client.decrby(key, amount)
        except Exception as e:
            logger.error(f"Redis DECR error: {e}")
            return 0

    # ==================== Set Operations ====================

    def sadd(self, name: str, *values: str) -> int:
        """Add members to set."""
        if not self.available or not self.client:
            if name not in self._in_memory_cache:
                self._in_memory_cache[name] = set()
            if isinstance(self._in_memory_cache[name], set):
                before = len(self._in_memory_cache[name])
                self._in_memory_cache[name].update(values)
                return len(self._in_memory_cache[name]) - before
            return 0

        try:
            return self.client.sadd(name, *values)
        except Exception as e:
            logger.error(f"Redis SADD error: {e}")
            return 0

    def smembers(self, name: str) -> set:
        """Get all members of set."""
        if not self.available or not self.client:
            value = self._in_memory_cache.get(name, set())
            return value if isinstance(value, set) else set()

        try:
            return self.client.smembers(name)
        except Exception as e:
            logger.error(f"Redis SMEMBERS error: {e}")
            return set()

    # ==================== Cleanup ====================

    def close(self):
        """Close Redis connection pool."""
        if self.pool:
            try:
                self.pool.disconnect()
                logger.info("Redis connection pool closed")
            except Exception as e:
                logger.error(f"Error closing Redis pool: {e}")


# ==================== Global Instance ====================

_redis_client: Optional[RedisClient] = None


def get_redis_client() -> RedisClient:
    """
    Get global Redis client instance.

    Returns:
        RedisClient: Singleton Redis client
    """
    global _redis_client

    if _redis_client is None:
        # Initialize from settings (add to config later)
        _redis_client = RedisClient(
            host=getattr(settings, 'REDIS_HOST', 'localhost'),
            port=getattr(settings, 'REDIS_PORT', 6379),
            db=getattr(settings, 'REDIS_DB', 0),
            password=getattr(settings, 'REDIS_PASSWORD', None),
            max_connections=50
        )

    return _redis_client


# ==================== Health Check ====================

def redis_health_check() -> Dict[str, Any]:
    """
    Redis health check for monitoring.

    Returns:
        dict: Health check status
    """
    client = get_redis_client()

    return {
        "available": client.available,
        "healthy": client.health_check() if client.available else False,
        "fallback": not client.available
    }
