"""Authentication & Authorization Module.

Provides JWT verification using Supabase Auth tokens.
All user-facing endpoints should use `get_current_user` as a dependency.
Admin endpoints use `require_admin` for API key + role verification.
"""

import time
import logging
from typing import Optional

from fastapi import Depends, HTTPException, Request, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials

from app.config import SUPABASE_URL, SUPABASE_SERVICE_KEY, MASTER_API_KEY
from app.database import get_db

logger = logging.getLogger(__name__)

security = HTTPBearer(auto_error=False)


class AuthUser:
    """Authenticated user context passed to endpoints."""

    def __init__(self, user_id: str, email: str = "", role: str = "user"):
        self.user_id = user_id
        self.email = email
        self.role = role

    @property
    def is_admin(self) -> bool:
        return self.role in ("admin", "service_role")


# Simple token cache to avoid re-verifying on every request
_token_cache: dict[str, tuple[AuthUser, float]] = {}
_CACHE_TTL = 300  # 5 minutes


def _verify_supabase_token(token: str) -> Optional[AuthUser]:
    """Verify a Supabase JWT token and return the user.

    Uses Supabase's auth.getUser() which validates the JWT server-side.
    This is more secure than local JWT verification because Supabase
    checks token revocation and session validity.
    """
    # Check cache first
    cached = _token_cache.get(token)
    if cached:
        user, expires = cached
        if time.time() < expires:
            return user
        else:
            del _token_cache[token]

    client = get_db()
    if not client:
        return None

    try:
        # Supabase SDK validates the token server-side
        response = client.auth.get_user(token)
        if response and response.user:
            user = AuthUser(
                user_id=response.user.id,
                email=response.user.email or "",
                role=response.user.role or "user",
            )
            # Cache the result
            if len(_token_cache) > 1000:
                # Evict expired entries
                now = time.time()
                _token_cache.clear()
            _token_cache[token] = (user, time.time() + _CACHE_TTL)
            return user
    except Exception as e:
        logger.debug(f"Token verification failed: {e}")

    return None


async def get_current_user(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security),
) -> AuthUser:
    """FastAPI dependency that extracts and verifies the authenticated user.

    Usage:
        @router.get("/me")
        async def get_me(user: AuthUser = Depends(get_current_user)):
            return {"user_id": user.user_id}
    """
    if not credentials:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required. Provide Bearer token.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    user = _verify_supabase_token(credentials.credentials)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    return user


async def get_optional_user(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security),
) -> Optional[AuthUser]:
    """Like get_current_user but returns None instead of raising 401.

    Use for endpoints that work with or without auth (e.g., public pages
    with personalization for logged-in users).
    """
    if not credentials:
        return None

    return _verify_supabase_token(credentials.credentials)


async def require_admin(
    request: Request,
    user: AuthUser = Depends(get_current_user),
) -> AuthUser:
    """Dependency that requires admin role or master API key.

    Usage:
        @router.post("/admin/action")
        async def admin_action(admin: AuthUser = Depends(require_admin)):
            ...
    """
    # Check API key header as alternative
    api_key = request.headers.get("X-API-Key", "")
    if MASTER_API_KEY and api_key == MASTER_API_KEY:
        return AuthUser(user_id="system", email="system@internal", role="admin")

    if not user.is_admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin access required.",
        )

    return user


def clear_auth_cache():
    """Clear the token verification cache. Called on shutdown."""
    _token_cache.clear()
