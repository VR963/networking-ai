"""
ChromaDB Cache Service - Phase 2 Week 3.

Implements intelligent caching for ChromaDB queries to improve performance.

Key Features:
- Query result caching with TTL
- LRU (Least Recently Used) eviction
- Cache statistics and monitoring
- Cache warming for common queries
- Batch query optimization
"""

from typing import List, Dict, Optional, Any
from datetime import datetime, timedelta
from collections import OrderedDict
import hashlib
import json


class CacheEntry:
    """Represents a single cache entry."""

    def __init__(self, key: str, value: Any, ttl_seconds: int = 3600):
        """
        Initialize cache entry.

        Args:
            key: Cache key
            value: Cached value
            ttl_seconds: Time to live in seconds
        """
        self.key = key
        self.value = value
        self.created_at = datetime.utcnow()
        self.last_accessed = datetime.utcnow()
        self.ttl_seconds = ttl_seconds
        self.access_count = 0

    def is_expired(self) -> bool:
        """Check if this entry has expired."""
        expiry_time = self.created_at + timedelta(seconds=self.ttl_seconds)
        return datetime.utcnow() > expiry_time

    def access(self):
        """Mark this entry as accessed."""
        self.last_accessed = datetime.utcnow()
        self.access_count += 1

    def age_seconds(self) -> float:
        """Get age of this entry in seconds."""
        return (datetime.utcnow() - self.created_at).total_seconds()


class ChromaDBCacheService:
    """
    Caching layer for ChromaDB queries.

    Implements LRU cache with TTL for vector database query results.
    """

    def __init__(
        self,
        max_cache_size: int = 1000,
        default_ttl: int = 3600,  # 1 hour
        enable_stats: bool = True
    ):
        """
        Initialize cache service.

        Args:
            max_cache_size: Maximum number of entries in cache
            default_ttl: Default TTL in seconds
            enable_stats: Enable statistics tracking
        """
        self.max_cache_size = max_cache_size
        self.default_ttl = default_ttl
        self.enable_stats = enable_stats

        # LRU cache using OrderedDict
        self._cache: OrderedDict[str, CacheEntry] = OrderedDict()

        # Statistics
        self._stats = {
            "hits": 0,
            "misses": 0,
            "evictions": 0,
            "expirations": 0,
            "total_queries": 0
        }

    def _generate_cache_key(
        self,
        collection_name: str,
        query_text: str,
        n_results: int = 5,
        additional_params: Optional[Dict] = None
    ) -> str:
        """
        Generate a unique cache key for a query.

        Args:
            collection_name: ChromaDB collection name
            query_text: Query text
            n_results: Number of results requested
            additional_params: Additional query parameters

        Returns:
            Cache key string
        """
        # Build key components
        key_data = {
            "collection": collection_name,
            "query": query_text,
            "n_results": n_results
        }

        if additional_params:
            key_data["params"] = additional_params

        # Create hash
        key_json = json.dumps(key_data, sort_keys=True)
        key_hash = hashlib.sha256(key_json.encode()).hexdigest()[:16]

        return f"chroma:{collection_name}:{key_hash}"

    def get(
        self,
        collection_name: str,
        query_text: str,
        n_results: int = 5,
        additional_params: Optional[Dict] = None
    ) -> Optional[Any]:
        """
        Get cached query result.

        Args:
            collection_name: ChromaDB collection name
            query_text: Query text
            n_results: Number of results requested
            additional_params: Additional query parameters

        Returns:
            Cached result if found and valid, None otherwise
        """
        if self.enable_stats:
            self._stats["total_queries"] += 1

        cache_key = self._generate_cache_key(collection_name, query_text, n_results, additional_params)

        # Check if key exists
        if cache_key not in self._cache:
            if self.enable_stats:
                self._stats["misses"] += 1
            return None

        entry = self._cache[cache_key]

        # Check if expired
        if entry.is_expired():
            del self._cache[cache_key]
            if self.enable_stats:
                self._stats["misses"] += 1
                self._stats["expirations"] += 1
            return None

        # Cache hit!
        entry.access()
        if self.enable_stats:
            self._stats["hits"] += 1

        # Move to end (most recently used)
        self._cache.move_to_end(cache_key)

        return entry.value

    def set(
        self,
        collection_name: str,
        query_text: str,
        result: Any,
        n_results: int = 5,
        ttl: Optional[int] = None,
        additional_params: Optional[Dict] = None
    ):
        """
        Cache a query result.

        Args:
            collection_name: ChromaDB collection name
            query_text: Query text
            result: Query result to cache
            n_results: Number of results requested
            ttl: TTL in seconds (uses default if None)
            additional_params: Additional query parameters
        """
        cache_key = self._generate_cache_key(collection_name, query_text, n_results, additional_params)
        ttl = ttl or self.default_ttl

        # Create entry
        entry = CacheEntry(key=cache_key, value=result, ttl_seconds=ttl)

        # Add to cache
        self._cache[cache_key] = entry
        self._cache.move_to_end(cache_key)

        # Check size limit
        if len(self._cache) > self.max_cache_size:
            self._evict_oldest()

    def _evict_oldest(self):
        """Evict the oldest (least recently used) entry."""
        if self._cache:
            oldest_key = next(iter(self._cache))
            del self._cache[oldest_key]
            if self.enable_stats:
                self._stats["evictions"] += 1

    def invalidate(
        self,
        collection_name: Optional[str] = None,
        query_text: Optional[str] = None
    ):
        """
        Invalidate cache entries.

        Args:
            collection_name: Invalidate all entries for this collection (None = all)
            query_text: Invalidate specific query (requires collection_name)
        """
        if collection_name is None:
            # Clear entire cache
            self._cache.clear()
            return

        if query_text:
            # Invalidate specific query
            cache_key = self._generate_cache_key(collection_name, query_text)
            if cache_key in self._cache:
                del self._cache[cache_key]
        else:
            # Invalidate all queries for collection
            keys_to_delete = [
                key for key in self._cache.keys()
                if key.startswith(f"chroma:{collection_name}:")
            ]
            for key in keys_to_delete:
                del self._cache[key]

    def clear(self):
        """Clear all cache entries."""
        self._cache.clear()
        if self.enable_stats:
            self._stats["evictions"] += len(self._cache)

    def cleanup_expired(self) -> int:
        """
        Remove all expired entries from cache.

        Returns:
            Number of entries removed
        """
        expired_keys = [
            key for key, entry in self._cache.items()
            if entry.is_expired()
        ]

        for key in expired_keys:
            del self._cache[key]

        if self.enable_stats:
            self._stats["expirations"] += len(expired_keys)

        return len(expired_keys)

    def get_stats(self) -> Dict:
        """
        Get cache statistics.

        Returns:
            Statistics dictionary
        """
        hit_rate = 0.0
        if self._stats["total_queries"] > 0:
            hit_rate = self._stats["hits"] / self._stats["total_queries"]

        return {
            **self._stats,
            "hit_rate": round(hit_rate, 3),
            "current_size": len(self._cache),
            "max_size": self.max_cache_size,
            "fill_percentage": round((len(self._cache) / self.max_cache_size) * 100, 1)
        }

    def get_cache_info(self, limit: int = 10) -> List[Dict]:
        """
        Get information about cached entries.

        Args:
            limit: Maximum number of entries to return

        Returns:
            List of cache entry info
        """
        info = []
        for key, entry in list(self._cache.items())[:limit]:
            info.append({
                "key": entry.key,
                "created_at": entry.created_at.isoformat(),
                "last_accessed": entry.last_accessed.isoformat(),
                "access_count": entry.access_count,
                "age_seconds": round(entry.age_seconds(), 1),
                "ttl_seconds": entry.ttl_seconds,
                "is_expired": entry.is_expired()
            })

        return info

    def reset_stats(self):
        """Reset statistics counters."""
        self._stats = {
            "hits": 0,
            "misses": 0,
            "evictions": 0,
            "expirations": 0,
            "total_queries": 0
        }

    def warm_cache(
        self,
        common_queries: List[Dict],
        chromadb_service
    ):
        """
        Pre-populate cache with common queries.

        Args:
            common_queries: List of query dicts with 'collection_name', 'query_text', 'n_results'
            chromadb_service: ChromaDB service to execute queries
        """
        for query_spec in common_queries:
            collection_name = query_spec["collection_name"]
            query_text = query_spec["query_text"]
            n_results = query_spec.get("n_results", 5)

            try:
                # Execute query
                result = chromadb_service.query_collection(
                    collection_name=collection_name,
                    query_texts=[query_text],
                    n_results=n_results
                )

                # Cache result
                self.set(
                    collection_name=collection_name,
                    query_text=query_text,
                    result=result,
                    n_results=n_results,
                    ttl=query_spec.get("ttl", self.default_ttl)
                )

                print(f"[Cache] Warmed: {collection_name} - {query_text[:50]}...")

            except Exception as e:
                print(f"[Cache] Failed to warm query: {e}")


class CachedChromaDBService:
    """
    Wrapper for ChromaDBService with caching.

    Transparently adds caching to ChromaDB queries.
    """

    def __init__(
        self,
        chromadb_service,
        cache_service: Optional[ChromaDBCacheService] = None,
        enable_cache: bool = True
    ):
        """
        Initialize cached service.

        Args:
            chromadb_service: Base ChromaDB service
            cache_service: Cache service (creates new if None)
            enable_cache: Enable caching
        """
        self.chromadb = chromadb_service
        self.cache = cache_service or ChromaDBCacheService()
        self.enable_cache = enable_cache

    def query_collection(
        self,
        collection_name: str,
        query_texts: List[str],
        n_results: int = 5,
        use_cache: bool = True
    ) -> Dict:
        """
        Query collection with caching.

        Args:
            collection_name: Collection name
            query_texts: Query texts
            n_results: Number of results
            use_cache: Use cache for this query

        Returns:
            Query results
        """
        # Only cache single-query requests for now
        if not self.enable_cache or not use_cache or len(query_texts) != 1:
            return self.chromadb.query_collection(collection_name, query_texts, n_results)

        query_text = query_texts[0]

        # Check cache
        cached_result = self.cache.get(
            collection_name=collection_name,
            query_text=query_text,
            n_results=n_results
        )

        if cached_result is not None:
            return cached_result

        # Execute query
        result = self.chromadb.query_collection(collection_name, query_texts, n_results)

        # Cache result
        self.cache.set(
            collection_name=collection_name,
            query_text=query_text,
            result=result,
            n_results=n_results
        )

        return result

    def query_talent_profile(
        self,
        collection_name: str,
        query: str,
        n_results: int = 10,
        use_cache: bool = True
    ) -> Dict:
        """Query talent profile with caching."""
        if not self.enable_cache or not use_cache:
            return self.chromadb.query_talent_profile(collection_name, query, n_results)

        # Check cache
        cached_result = self.cache.get(collection_name, query, n_results)
        if cached_result:
            return cached_result

        # Execute
        result = self.chromadb.query_talent_profile(collection_name, query, n_results)

        # Cache
        self.cache.set(collection_name, query, result, n_results)

        return result

    def invalidate_collection(self, collection_name: str):
        """Invalidate all cache entries for a collection."""
        self.cache.invalidate(collection_name=collection_name)

    def get_cache_stats(self) -> Dict:
        """Get cache statistics."""
        return self.cache.get_stats()

    def cleanup_cache(self) -> int:
        """Clean up expired cache entries."""
        return self.cache.cleanup_expired()


def create_cached_chromadb_service(
    chromadb_service,
    max_cache_size: int = 1000,
    default_ttl: int = 3600,
    enable_cache: bool = True
) -> CachedChromaDBService:
    """
    Factory function to create cached ChromaDB service.

    Args:
        chromadb_service: Base ChromaDB service
        max_cache_size: Maximum cache entries
        default_ttl: Default TTL in seconds
        enable_cache: Enable caching

    Returns:
        CachedChromaDBService instance
    """
    cache_service = ChromaDBCacheService(
        max_cache_size=max_cache_size,
        default_ttl=default_ttl,
        enable_stats=True
    )

    return CachedChromaDBService(
        chromadb_service=chromadb_service,
        cache_service=cache_service,
        enable_cache=enable_cache
    )
