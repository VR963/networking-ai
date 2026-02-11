"""Tests for domain-specific exceptions."""

import pytest

from app.exceptions import (
    CV2Error,
    ProfileError,
    NegotiationError,
    ActivationError,
    HallucinationViolation,
    AIServiceError,
    DatabaseError,
    ValidationError,
)


class TestCV2Error:
    def test_base_error(self):
        err = CV2Error("something went wrong")
        assert str(err) == "something went wrong"
        assert err.code == "cv2_error"
        assert err.detail == {}

    def test_with_code_and_detail(self):
        err = CV2Error("bad thing", code="custom_code", detail={"key": "value"})
        assert err.code == "custom_code"
        assert err.detail["key"] == "value"


class TestProfileError:
    def test_profile_error(self):
        err = ProfileError("Profile not found", user_id="user-123")
        assert err.code == "profile_error"
        assert err.user_id == "user-123"

    def test_is_cv2_error(self):
        assert issubclass(ProfileError, CV2Error)


class TestNegotiationError:
    def test_negotiation_error(self):
        err = NegotiationError("Round failed", round_num=2)
        assert err.code == "negotiation_error"
        assert err.round_num == 2


class TestHallucinationViolation:
    def test_violation(self):
        err = HallucinationViolation("Fabricated skill", severity="critical")
        assert err.severity == "critical"
        assert err.code == "hallucination_violation"


class TestValidationError:
    def test_validation_error(self):
        err = ValidationError("Too long", field="message")
        assert err.code == "validation_error"
        assert err.field == "message"

    def test_is_cv2_error(self):
        assert issubclass(ValidationError, CV2Error)


class TestInheritance:
    """Verify all exceptions inherit from CV2Error for unified handling."""

    def test_all_inherit_from_cv2error(self):
        exceptions = [
            ProfileError, NegotiationError, ActivationError,
            HallucinationViolation, AIServiceError, DatabaseError,
            ValidationError,
        ]
        for exc_class in exceptions:
            assert issubclass(exc_class, CV2Error), f"{exc_class.__name__} should inherit CV2Error"

    def test_can_catch_with_base_class(self):
        try:
            raise ProfileError("test")
        except CV2Error as e:
            assert e.code == "profile_error"
