"""
Main mobile API router.

Aggregates all mobile endpoint routers under /api/v1/mobile
"""

from fastapi import APIRouter, Depends

from .dependencies import check_mobile_rate_limit


# Main mobile router
mobile_router = APIRouter(
    prefix="/mobile",
    tags=["mobile"],
    responses={
        401: {"description": "Unauthorized - Invalid or expired token"},
        403: {"description": "Forbidden - Insufficient permissions"},
        429: {"description": "Too Many Requests - Rate limit exceeded"},
        500: {"description": "Internal Server Error"}
    }
)


@mobile_router.get("/health")
async def mobile_health_check():
    """
    Mobile API health check endpoint.

    Returns:
        Health status of mobile API
    """
    return {
        "data": {
            "status": "healthy",
            "version": "1.0",
            "endpoints": [
                "/mobile/auth",
                "/mobile/jobs",
                "/mobile/applications",
                "/mobile/profile",
                "/mobile/notifications",
                "/mobile/messages",
                "/mobile/devices"
            ]
        },
        "meta": {
            "version": "1.0"
        }
    }


# Import and include sub-routers (will be created next)
# from .auth import auth_router
# from .jobs import jobs_router
# from .applications import applications_router
# from .profile import profile_router
# from .notifications import notifications_router
# from .messages import messages_router
# from .devices import devices_router
#
# mobile_router.include_router(auth_router, prefix="/auth", tags=["mobile-auth"])
# mobile_router.include_router(jobs_router, prefix="/jobs", tags=["mobile-jobs"], dependencies=[Depends(check_mobile_rate_limit)])
# mobile_router.include_router(applications_router, prefix="/applications", tags=["mobile-applications"], dependencies=[Depends(check_mobile_rate_limit)])
# mobile_router.include_router(profile_router, prefix="/profile", tags=["mobile-profile"], dependencies=[Depends(check_mobile_rate_limit)])
# mobile_router.include_router(notifications_router, prefix="/notifications", tags=["mobile-notifications"], dependencies=[Depends(check_mobile_rate_limit)])
# mobile_router.include_router(messages_router, prefix="/messages", tags=["mobile-messages"], dependencies=[Depends(check_mobile_rate_limit)])
# mobile_router.include_router(devices_router, prefix="/devices", tags=["mobile-devices"], dependencies=[Depends(check_mobile_rate_limit)])
