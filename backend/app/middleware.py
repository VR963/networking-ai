"""Middleware Stack - Rate limiting, security, logging, and concurrency control.

PROBLEMS SOLVED:
1. No rate limiting → DDoS/abuse vulnerability → Fixed with sliding window limiter
2. No structured logging → Can't debug production → Fixed with request logging
3. No concurrency control → AI calls overwhelm API → Fixed with semaphore
4. No security headers → XSS/clickjacking risk → Fixed with security headers
5. No request size limits → Memory exhaustion → Fixed with body size check
"""

import time
import asyncio
import logging
import threading
from collections import defaultdict
from typing import Callable

from fastapi import Request, Response
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware

from app.config import (
    RATE_LIMIT_PER_MINUTE,
    RATE_LIMIT_AI_PER_MINUTE,
    MAX_CONCURRENT_AI_CALLS,
    MASTER_API_KEY,
    API_KEY_HEADER,
    APP_ENV,
)


logger = logging.getLogger("cv2.middleware")


# --- Rate Limiter (Sliding Window) ---

class RateLimiter:
    """Thread-safe sliding window rate limiter.

    Tracks requests per client IP with a 60-second sliding window.
    Different limits for general vs AI-heavy endpoints.
    """

    def __init__(self):
        self._requests: dict[str, list[float]] = defaultdict(list)
        self._lock = threading.Lock()

    def is_allowed(self, client_id: str, limit: int = RATE_LIMIT_PER_MINUTE) -> bool:
        now = time.time()
        window_start = now - 60.0

        with self._lock:
            # Remove expired entries
            self._requests[client_id] = [
                t for t in self._requests[client_id] if t > window_start
            ]
            if len(self._requests[client_id]) >= limit:
                return False
            self._requests[client_id].append(now)
            return True

    def get_remaining(self, client_id: str, limit: int = RATE_LIMIT_PER_MINUTE) -> int:
        now = time.time()
        window_start = now - 60.0
        with self._lock:
            active = [t for t in self._requests.get(client_id, []) if t > window_start]
            return max(0, limit - len(active))

    def cleanup(self) -> None:
        """Remove stale entries (call periodically)."""
        now = time.time()
        window_start = now - 60.0
        with self._lock:
            stale_keys = []
            for key, times in self._requests.items():
                self._requests[key] = [t for t in times if t > window_start]
                if not self._requests[key]:
                    stale_keys.append(key)
            for key in stale_keys:
                del self._requests[key]


_rate_limiter = RateLimiter()

# AI call semaphore - prevents overwhelming Anthropic API
_ai_semaphore = asyncio.Semaphore(MAX_CONCURRENT_AI_CALLS)


async def acquire_ai_slot() -> bool:
    """Acquire a slot for an AI API call. Use as context manager or check return."""
    return await asyncio.wait_for(_ai_semaphore.acquire(), timeout=30.0)


def release_ai_slot() -> None:
    """Release an AI API call slot."""
    _ai_semaphore.release()


# --- AI paths that need stricter rate limiting ---
AI_HEAVY_PATHS = {
    "/master-ai/control-center/cycle",
    "/master-ai/council/convene",
    "/master-ai/council/consult",
    "/master-ai/training/run",
    "/master-ai/training/cycle",
    "/master-ai/marketing/propose",
    "/master-ai/marketing/review",
    "/master-ai/marketing/content",
    "/master-ai/marketing/landing-page",
    "/master-ai/marketing/justify",
    "/master-ai/market/strategic-brief",
    "/network/negotiate",
    "/onboarding/talent/start",
    "/onboarding/hm/start",
    "/chat/message",
}

# Master-AI admin paths requiring API key
PROTECTED_PATHS = {
    "/master-ai/control-center/cycle",
    "/master-ai/training/run",
    "/master-ai/training/cycle",
    "/master-ai/marketing/approve",
    "/master-ai/marketing/reject",
    "/master-ai/marketing/terminate",
    "/master-ai/marketing/activate",
}


# --- Middleware Classes ---

class RateLimitMiddleware(BaseHTTPMiddleware):
    """Rate limiting per client IP with different tiers."""

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        client_ip = request.client.host if request.client else "unknown"
        path = request.url.path

        # Determine rate limit tier
        is_ai_path = any(path.startswith(p) for p in AI_HEAVY_PATHS)
        limit = RATE_LIMIT_AI_PER_MINUTE if is_ai_path else RATE_LIMIT_PER_MINUTE

        if not _rate_limiter.is_allowed(client_ip, limit):
            remaining = _rate_limiter.get_remaining(client_ip, limit)
            return JSONResponse(
                status_code=429,
                content={"detail": "Rate limit exceeded. Try again later."},
                headers={
                    "X-RateLimit-Limit": str(limit),
                    "X-RateLimit-Remaining": str(remaining),
                    "Retry-After": "60",
                },
            )

        response = await call_next(request)
        remaining = _rate_limiter.get_remaining(client_ip, limit)
        response.headers["X-RateLimit-Limit"] = str(limit)
        response.headers["X-RateLimit-Remaining"] = str(remaining)
        return response


class SecurityMiddleware(BaseHTTPMiddleware):
    """Security headers, API key validation for admin routes, body size limits."""

    MAX_BODY_SIZE = 10 * 1024 * 1024  # 10MB max request body

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        path = request.url.path

        # Body size check (only for POST/PUT)
        if request.method in ("POST", "PUT"):
            content_length = request.headers.get("content-length")
            if content_length and int(content_length) > self.MAX_BODY_SIZE:
                return JSONResponse(
                    status_code=413,
                    content={"detail": "Request body too large. Maximum 10MB."},
                )

        # API key check for protected admin endpoints
        if any(path.startswith(p) for p in PROTECTED_PATHS):
            if MASTER_API_KEY:  # Only enforce if key is configured
                provided_key = request.headers.get(API_KEY_HEADER, "")
                if provided_key != MASTER_API_KEY:
                    return JSONResponse(
                        status_code=403,
                        content={"detail": "Admin API key required for this endpoint."},
                    )

        response = await call_next(request)

        # Security headers
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["X-XSS-Protection"] = "1; mode=block"
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        if APP_ENV == "production":
            response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"

        # Cache control for static files - prevent stale JavaScript in development
        if APP_ENV != "production" and path.endswith((".html", ".js", ".css")):
            response.headers["Cache-Control"] = "no-cache, must-revalidate"

        return response


class RequestLoggingMiddleware(BaseHTTPMiddleware):
    """Structured request logging for debugging and monitoring."""

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        start_time = time.time()
        client_ip = request.client.host if request.client else "unknown"

        # Process request
        try:
            response = await call_next(request)
        except Exception as exc:
            duration_ms = (time.time() - start_time) * 1000
            logger.error(
                "request_error",
                extra={
                    "method": request.method,
                    "path": request.url.path,
                    "client_ip": client_ip,
                    "error": type(exc).__name__,
                    "duration_ms": round(duration_ms, 1),
                },
            )
            raise

        duration_ms = (time.time() - start_time) * 1000

        # Log slow requests (>2s) at WARNING level
        log_level = logging.WARNING if duration_ms > 2000 else logging.INFO
        # Only log non-static requests
        if not request.url.path.startswith(("/static", "/favicon")):
            logger.log(
                log_level,
                "%s %s %d %.0fms",
                request.method,
                request.url.path,
                response.status_code,
                duration_ms,
            )

        response.headers["X-Response-Time"] = f"{duration_ms:.0f}ms"
        return response
