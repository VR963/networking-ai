"""
Mobile API dependencies and middleware.

Includes:
- Mobile authentication
- Rate limiting
- Request validation
- User agent detection
"""

from typing import Optional
from fastapi import Header, HTTPException, Depends, Request, status
from sqlalchemy.orm import Session
from datetime import datetime, timedelta
import jwt

from ...database import get_db
from ...models.user import User
from ...config import get_settings


settings = get_settings()


class MobileAuthRequired:
    """
    Dependency for mobile API authentication.

    Validates JWT access token from Authorization header.
    """

    async def __call__(
        self,
        authorization: Optional[str] = Header(None),
        db: Session = Depends(get_db)
    ) -> User:
        """
        Extract and validate JWT token, return authenticated user.

        Args:
            authorization: Authorization header (Bearer token)
            db: Database session

        Returns:
            Authenticated User object

        Raises:
            HTTPException: If token is invalid or user not found
        """
        if not authorization:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail={
                    "error": {
                        "code": "UNAUTHORIZED",
                        "message": "Authorization header required"
                    }
                }
            )

        # Extract token from "Bearer <token>"
        try:
            scheme, token = authorization.split()
            if scheme.lower() != "bearer":
                raise ValueError("Invalid scheme")
        except ValueError:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail={
                    "error": {
                        "code": "INVALID_TOKEN",
                        "message": "Invalid authorization header format. Use: Bearer <token>"
                    }
                }
            )

        # Decode and validate JWT
        try:
            payload = jwt.decode(
                token,
                settings.JWT_SECRET_KEY,
                algorithms=[settings.JWT_ALGORITHM]
            )

            user_id = payload.get("sub")
            if not user_id:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail={
                        "error": {
                            "code": "INVALID_TOKEN",
                            "message": "Token missing user ID"
                        }
                    }
                )

            # Check token expiration
            exp = payload.get("exp")
            if exp and datetime.utcfromtimestamp(exp) < datetime.utcnow():
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail={
                        "error": {
                            "code": "TOKEN_EXPIRED",
                            "message": "Access token has expired. Please refresh."
                        }
                    }
                )

        except jwt.ExpiredSignatureError:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail={
                    "error": {
                        "code": "TOKEN_EXPIRED",
                        "message": "Access token has expired. Please refresh."
                    }
                }
            )
        except jwt.InvalidTokenError as e:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail={
                    "error": {
                        "code": "INVALID_TOKEN",
                        "message": f"Invalid token: {str(e)}"
                    }
                }
            )

        # Get user from database
        user = db.query(User).filter(User.id == int(user_id)).first()
        if not user:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail={
                    "error": {
                        "code": "USER_NOT_FOUND",
                        "message": "User not found"
                    }
                }
            )

        if not user.is_active:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail={
                    "error": {
                        "code": "ACCOUNT_INACTIVE",
                        "message": "Account is inactive"
                    }
                }
            )

        # Update last login time
        user.last_login = datetime.utcnow()
        db.commit()

        return user


# Dependency instances
mobile_auth_required = MobileAuthRequired()


def get_device_info(
    user_agent: Optional[str] = Header(None, alias="User-Agent"),
    x_device_id: Optional[str] = Header(None, alias="X-Device-ID"),
    x_app_version: Optional[str] = Header(None, alias="X-App-Version"),
    x_platform: Optional[str] = Header(None, alias="X-Platform")
) -> dict:
    """
    Extract device information from headers.

    Expected headers:
        User-Agent: Standard HTTP user agent
        X-Device-ID: Unique device identifier
        X-App-Version: App version (e.g., "1.0.0")
        X-Platform: Platform (e.g., "ios", "android")

    Returns:
        Dictionary with device information
    """
    return {
        "user_agent": user_agent,
        "device_id": x_device_id,
        "app_version": x_app_version,
        "platform": x_platform
    }


def validate_pagination_params(
    cursor: Optional[str] = None,
    limit: int = 20
) -> dict:
    """
    Validate and normalize pagination parameters.

    Args:
        cursor: Base64 pagination cursor
        limit: Page size (default: 20, max: 50)

    Returns:
        Dictionary with validated pagination params

    Raises:
        HTTPException: If parameters are invalid
    """
    # Enforce max limit
    MAX_LIMIT = 50
    if limit < 1:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={
                "error": {
                    "code": "INVALID_INPUT",
                    "message": "Limit must be at least 1"
                }
            }
        )

    if limit > MAX_LIMIT:
        limit = MAX_LIMIT

    return {
        "cursor": cursor,
        "limit": limit
    }


class RateLimiter:
    """
    Simple in-memory rate limiter for mobile API.

    In production, use Redis for distributed rate limiting.
    """

    def __init__(self, max_requests: int = 100, window_seconds: int = 60):
        """
        Initialize rate limiter.

        Args:
            max_requests: Maximum requests allowed in time window
            window_seconds: Time window in seconds
        """
        self.max_requests = max_requests
        self.window_seconds = window_seconds
        self._requests: dict = {}  # {user_id: [(timestamp, count)]}

    def check_rate_limit(self, user_id: int) -> bool:
        """
        Check if user has exceeded rate limit.

        Args:
            user_id: User ID to check

        Returns:
            True if within limit, False if exceeded
        """
        now = datetime.utcnow()
        window_start = now - timedelta(seconds=self.window_seconds)

        # Clean old entries
        if user_id in self._requests:
            self._requests[user_id] = [
                (ts, count) for ts, count in self._requests[user_id]
                if ts > window_start
            ]
        else:
            self._requests[user_id] = []

        # Count requests in window
        total_requests = sum(count for _, count in self._requests[user_id])

        if total_requests >= self.max_requests:
            return False

        # Add current request
        self._requests[user_id].append((now, 1))
        return True


# Global rate limiter instance
mobile_rate_limiter = RateLimiter(max_requests=100, window_seconds=60)


def check_mobile_rate_limit(
    user: User = Depends(mobile_auth_required)
):
    """
    Dependency to check rate limiting for mobile API.

    Args:
        user: Authenticated user

    Raises:
        HTTPException: If rate limit exceeded
    """
    if not mobile_rate_limiter.check_rate_limit(user.id):
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail={
                "error": {
                    "code": "RATE_LIMIT_EXCEEDED",
                    "message": "Too many requests. Please try again later.",
                    "details": {
                        "limit": mobile_rate_limiter.max_requests,
                        "window_seconds": mobile_rate_limiter.window_seconds
                    }
                }
            }
        )
