"""
Standard response wrappers for mobile API.

All mobile API responses follow a consistent structure:
- Success responses: { data, meta, links }
- Error responses: { error, meta }
"""

from datetime import datetime
from typing import Optional, Any, Dict, Generic, TypeVar
from pydantic import BaseModel, ConfigDict

T = TypeVar('T')


class ResponseMeta(BaseModel):
    """Metadata included in all responses."""
    model_config = ConfigDict(from_attributes=True)

    version: str = "1.0"
    timestamp: datetime = datetime.utcnow()
    request_id: Optional[str] = None


class ResponseLinks(BaseModel):
    """HATEOAS links for navigation."""
    model_config = ConfigDict(from_attributes=True)

    self: str
    related: Optional[Dict[str, str]] = None


class MobileResponse(BaseModel, Generic[T]):
    """
    Standard mobile API success response.

    Example:
        {
            "data": { ... },
            "meta": {
                "version": "1.0",
                "timestamp": "2025-11-08T12:00:00Z"
            },
            "links": {
                "self": "/api/v1/mobile/jobs/123"
            }
        }
    """
    model_config = ConfigDict(from_attributes=True)

    data: T
    meta: ResponseMeta = ResponseMeta()
    links: Optional[ResponseLinks] = None


class ErrorDetail(BaseModel):
    """Detailed error information."""
    model_config = ConfigDict(from_attributes=True)

    field: Optional[str] = None
    message: str
    constraint: Optional[str] = None


class ErrorResponse(BaseModel):
    """
    Standard mobile API error response.

    Example:
        {
            "error": {
                "code": "VALIDATION_ERROR",
                "message": "Invalid email format",
                "details": {
                    "field": "email",
                    "message": "Email must be valid",
                    "constraint": "format"
                }
            },
            "meta": {
                "version": "1.0",
                "timestamp": "2025-11-08T12:00:00Z",
                "request_id": "req_abc123"
            }
        }
    """
    model_config = ConfigDict(from_attributes=True)

    error: Dict[str, Any]
    meta: ResponseMeta = ResponseMeta()


# Common error codes
class ErrorCode:
    """Standard error codes for mobile API."""

    # Authentication errors (401)
    UNAUTHORIZED = "UNAUTHORIZED"
    INVALID_TOKEN = "INVALID_TOKEN"
    TOKEN_EXPIRED = "TOKEN_EXPIRED"

    # Authorization errors (403)
    FORBIDDEN = "FORBIDDEN"
    INSUFFICIENT_PERMISSIONS = "INSUFFICIENT_PERMISSIONS"

    # Validation errors (400)
    VALIDATION_ERROR = "VALIDATION_ERROR"
    INVALID_INPUT = "INVALID_INPUT"
    MISSING_FIELD = "MISSING_FIELD"

    # Resource errors (404, 409)
    NOT_FOUND = "NOT_FOUND"
    ALREADY_EXISTS = "ALREADY_EXISTS"
    CONFLICT = "CONFLICT"

    # Rate limiting (429)
    RATE_LIMIT_EXCEEDED = "RATE_LIMIT_EXCEEDED"

    # Server errors (500)
    INTERNAL_ERROR = "INTERNAL_ERROR"
    SERVICE_UNAVAILABLE = "SERVICE_UNAVAILABLE"


def create_success_response(
    data: Any,
    self_link: str,
    related_links: Optional[Dict[str, str]] = None,
    request_id: Optional[str] = None
) -> Dict[str, Any]:
    """
    Create a standard success response.

    Args:
        data: Response data
        self_link: URL of current resource
        related_links: Optional related resource links
        request_id: Optional request ID for tracking

    Returns:
        Formatted response dictionary
    """
    return {
        "data": data,
        "meta": {
            "version": "1.0",
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "request_id": request_id
        },
        "links": {
            "self": self_link,
            "related": related_links
        } if related_links else {"self": self_link}
    }


def create_error_response(
    code: str,
    message: str,
    details: Optional[Dict[str, Any]] = None,
    request_id: Optional[str] = None
) -> Dict[str, Any]:
    """
    Create a standard error response.

    Args:
        code: Error code (use ErrorCode constants)
        message: Human-readable error message
        details: Optional additional error details
        request_id: Optional request ID for tracking

    Returns:
        Formatted error response dictionary
    """
    error_data = {
        "code": code,
        "message": message
    }

    if details:
        error_data["details"] = details

    return {
        "error": error_data,
        "meta": {
            "version": "1.0",
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "request_id": request_id
        }
    }
