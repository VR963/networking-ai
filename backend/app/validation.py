"""Input validation utilities for CV2.0 platform.

Validates and sanitizes user inputs at API boundaries.
Internal code trusts validated data — no redundant checks downstream.
"""

import re
from typing import Optional

from app.exceptions import ValidationError


# Limits
MAX_MESSAGE_LENGTH = 10_000  # Chat messages
MAX_CV_TEXT_LENGTH = 50_000  # CV/resume text
MAX_JD_TEXT_LENGTH = 30_000  # Job descriptions
MAX_FILENAME_LENGTH = 255
MAX_URL_LENGTH = 2048
MIN_ANSWER_LENGTH = 5  # Interview answers

# Patterns
UUID_PATTERN = re.compile(r"^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$", re.I)
EMAIL_PATTERN = re.compile(r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$")
SAFE_TEXT_PATTERN = re.compile(r"^[\w\s.,;:!?@#$%^&*()\-+=\[\]{}'\"/<>~`\n\r]+$", re.UNICODE)

# Allowed document types
ALLOWED_DOC_TYPES = {"cv", "certificate", "portfolio", "other"}
ALLOWED_INDUSTRIES = {
    "technology", "finance", "healthcare", "creative", "marketing",
    "engineering", "education", "legal", "consulting", "general",
}


def validate_user_id(user_id: str) -> str:
    """Validate user ID format."""
    if not user_id or not isinstance(user_id, str):
        raise ValidationError("user_id is required", field="user_id")
    user_id = user_id.strip()
    if len(user_id) > 128:
        raise ValidationError("user_id too long", field="user_id")
    return user_id


def validate_message(text: str) -> str:
    """Validate and sanitize a chat message."""
    if not text or not isinstance(text, str):
        raise ValidationError("Message cannot be empty", field="message")
    text = text.strip()
    if len(text) > MAX_MESSAGE_LENGTH:
        raise ValidationError(
            f"Message too long ({len(text)} chars, max {MAX_MESSAGE_LENGTH})",
            field="message",
        )
    if len(text) < 1:
        raise ValidationError("Message cannot be empty", field="message")
    return text


def validate_cv_text(text: str) -> str:
    """Validate CV/resume text content."""
    if not text or not isinstance(text, str):
        raise ValidationError("CV text is required", field="cv_text")
    text = text.strip()
    if len(text) > MAX_CV_TEXT_LENGTH:
        text = text[:MAX_CV_TEXT_LENGTH]
    if len(text) < 20:
        raise ValidationError("CV text too short to analyze", field="cv_text")
    return text


def validate_job_description(text: str) -> str:
    """Validate job description text."""
    if not text or not isinstance(text, str):
        raise ValidationError("Job description is required", field="description")
    text = text.strip()
    if len(text) > MAX_JD_TEXT_LENGTH:
        text = text[:MAX_JD_TEXT_LENGTH]
    if len(text) < 20:
        raise ValidationError("Job description too short", field="description")
    return text


def validate_filename(filename: str) -> str:
    """Validate uploaded filename."""
    if not filename or not isinstance(filename, str):
        raise ValidationError("Filename is required", field="filename")
    filename = filename.strip()
    if len(filename) > MAX_FILENAME_LENGTH:
        raise ValidationError("Filename too long", field="filename")
    # Block path traversal
    if ".." in filename or "/" in filename or "\\" in filename:
        raise ValidationError("Invalid filename", field="filename")
    return filename


def validate_doc_type(doc_type: str) -> str:
    """Validate document type."""
    if not doc_type or doc_type not in ALLOWED_DOC_TYPES:
        raise ValidationError(
            f"Invalid doc_type. Allowed: {', '.join(ALLOWED_DOC_TYPES)}",
            field="doc_type",
        )
    return doc_type


def validate_industry(industry: str) -> str:
    """Validate industry selection."""
    if not industry:
        return "general"
    industry = industry.lower().strip()
    if industry not in ALLOWED_INDUSTRIES:
        return "general"
    return industry


def validate_url(url: str) -> Optional[str]:
    """Validate and sanitize a URL."""
    if not url or not isinstance(url, str):
        return None
    url = url.strip()
    if len(url) > MAX_URL_LENGTH:
        raise ValidationError("URL too long", field="url")
    if not url.startswith(("http://", "https://")):
        raise ValidationError("URL must start with http:// or https://", field="url")
    return url


def validate_interview_answer(answer: str) -> str:
    """Validate an interview answer."""
    if not answer or not isinstance(answer, str):
        raise ValidationError("Answer is required", field="answer")
    answer = answer.strip()
    if len(answer) < MIN_ANSWER_LENGTH:
        raise ValidationError(
            f"Answer too short (min {MIN_ANSWER_LENGTH} chars)",
            field="answer",
        )
    if len(answer) > MAX_MESSAGE_LENGTH:
        answer = answer[:MAX_MESSAGE_LENGTH]
    return answer


def sanitize_for_prompt(text: str, max_length: int = 8000) -> str:
    """Sanitize text before including it in an AI prompt.

    Prevents prompt injection by limiting length and removing
    control sequences that could alter AI behavior.
    """
    if not text:
        return ""
    text = text[:max_length]
    # Remove common prompt injection patterns
    injection_markers = [
        "ignore previous instructions",
        "ignore all instructions",
        "disregard the above",
        "system:",
        "assistant:",
        "<|",
        "|>",
    ]
    text_lower = text.lower()
    for marker in injection_markers:
        if marker in text_lower:
            text = text.replace(marker, "[filtered]")
            text = text.replace(marker.upper(), "[filtered]")
    return text
