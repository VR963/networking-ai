"""Domain-specific exception classes for CV2.0 platform.

Using structured exceptions instead of generic Exception:
- Better error categorization in logs and metrics
- Cleaner error handling in route handlers
- Consistent error responses for API consumers
"""

from typing import Optional


class CV2Error(Exception):
    """Base exception for CV2.0 platform."""

    def __init__(self, message: str, code: str = "cv2_error", detail: Optional[dict] = None):
        super().__init__(message)
        self.code = code
        self.detail = detail or {}


class ProfileError(CV2Error):
    """Errors related to profile operations."""

    def __init__(self, message: str, user_id: str = "", detail: Optional[dict] = None):
        super().__init__(message, code="profile_error", detail=detail)
        self.user_id = user_id


class NegotiationError(CV2Error):
    """Errors during agent-to-agent negotiation."""

    def __init__(self, message: str, round_num: int = 0, detail: Optional[dict] = None):
        super().__init__(message, code="negotiation_error", detail=detail)
        self.round_num = round_num


class ActivationError(CV2Error):
    """Errors during agent activation."""

    def __init__(self, message: str, agent_id: str = "", detail: Optional[dict] = None):
        super().__init__(message, code="activation_error", detail=detail)
        self.agent_id = agent_id


class HallucinationViolation(CV2Error):
    """Detected hallucination or integrity violation."""

    def __init__(self, message: str, severity: str = "major", detail: Optional[dict] = None):
        super().__init__(message, code="hallucination_violation", detail=detail)
        self.severity = severity


class AIServiceError(CV2Error):
    """Errors from the Anthropic AI API."""

    def __init__(self, message: str, model: str = "", detail: Optional[dict] = None):
        super().__init__(message, code="ai_service_error", detail=detail)
        self.model = model


class DatabaseError(CV2Error):
    """Errors from Supabase/database operations."""

    def __init__(self, message: str, table: str = "", detail: Optional[dict] = None):
        super().__init__(message, code="database_error", detail=detail)
        self.table = table


class ValidationError(CV2Error):
    """Input validation errors."""

    def __init__(self, message: str, field: str = "", detail: Optional[dict] = None):
        super().__init__(message, code="validation_error", detail=detail)
        self.field = field
