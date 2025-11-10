"""
Cache module for hot memory and general caching.
"""

from .redis_client import RedisClient, get_redis_client

__all__ = ['RedisClient', 'get_redis_client']
