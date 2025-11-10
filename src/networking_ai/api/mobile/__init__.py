"""
Mobile API Module - Phase 10

Provides mobile-optimized endpoints for iOS and Android applications.

Features:
- Cursor-based pagination
- Compact response payloads
- Device registration
- Push notifications
- Offline support considerations
"""

from .router import mobile_router

__all__ = ["mobile_router"]
