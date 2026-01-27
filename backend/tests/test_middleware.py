"""Tests for middleware components."""

import time
import asyncio

import pytest


class TestRateLimiter:
    """Test sliding window rate limiter."""

    def test_allows_under_limit(self):
        from app.middleware import RateLimiter
        limiter = RateLimiter()
        for _ in range(5):
            assert limiter.is_allowed("client1", limit=5) is True

    def test_blocks_over_limit(self):
        from app.middleware import RateLimiter
        limiter = RateLimiter()
        for _ in range(3):
            limiter.is_allowed("client1", limit=3)
        assert limiter.is_allowed("client1", limit=3) is False

    def test_separate_clients(self):
        from app.middleware import RateLimiter
        limiter = RateLimiter()
        limiter.is_allowed("client1", limit=2)
        limiter.is_allowed("client1", limit=2)
        # client1 is at limit
        assert limiter.is_allowed("client1", limit=2) is False
        # client2 is fresh
        assert limiter.is_allowed("client2", limit=2) is True

    def test_get_remaining(self):
        from app.middleware import RateLimiter
        limiter = RateLimiter()
        limiter.is_allowed("client1", limit=10)
        limiter.is_allowed("client1", limit=10)
        assert limiter.get_remaining("client1", limit=10) == 8

    def test_cleanup(self):
        from app.middleware import RateLimiter
        limiter = RateLimiter()
        limiter.is_allowed("old_client", limit=100)
        limiter.cleanup()  # Should not error


class TestAISemaphore:
    """Test AI concurrency control."""

    def test_acquire_release(self):
        from app.middleware import acquire_ai_slot, release_ai_slot

        async def _test():
            acquired = await acquire_ai_slot()
            assert acquired is True
            release_ai_slot()

        asyncio.run(_test())
