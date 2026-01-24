"""Tests for authentication system."""

import pytest
from unittest.mock import patch, MagicMock, AsyncMock

from app.auth import AuthUser, _verify_supabase_token, clear_auth_cache


class TestAuthUser:
    """Test AuthUser model."""

    def test_basic_user(self):
        user = AuthUser(user_id="123", email="test@example.com")
        assert user.user_id == "123"
        assert user.email == "test@example.com"
        assert user.role == "user"
        assert user.is_admin is False

    def test_admin_user(self):
        user = AuthUser(user_id="admin1", role="admin")
        assert user.is_admin is True

    def test_service_role(self):
        user = AuthUser(user_id="svc", role="service_role")
        assert user.is_admin is True


class TestTokenVerification:
    """Test Supabase token verification."""

    def setup_method(self):
        clear_auth_cache()

    @patch("app.auth.get_db")
    def test_valid_token(self, mock_get_db):
        mock_client = MagicMock()
        mock_user = MagicMock()
        mock_user.id = "user-uuid-123"
        mock_user.email = "test@test.com"
        mock_user.role = "authenticated"
        mock_response = MagicMock()
        mock_response.user = mock_user
        mock_client.auth.get_user.return_value = mock_response
        mock_get_db.return_value = mock_client

        result = _verify_supabase_token("valid-token-123")
        assert result is not None
        assert result.user_id == "user-uuid-123"
        assert result.email == "test@test.com"

    @patch("app.auth.get_db")
    def test_invalid_token(self, mock_get_db):
        mock_client = MagicMock()
        mock_client.auth.get_user.side_effect = Exception("Invalid token")
        mock_get_db.return_value = mock_client

        result = _verify_supabase_token("bad-token")
        assert result is None

    @patch("app.auth.get_db")
    def test_cached_token(self, mock_get_db):
        mock_client = MagicMock()
        mock_user = MagicMock()
        mock_user.id = "cached-user"
        mock_user.email = "cached@test.com"
        mock_user.role = "user"
        mock_response = MagicMock()
        mock_response.user = mock_user
        mock_client.auth.get_user.return_value = mock_response
        mock_get_db.return_value = mock_client

        # First call - hits Supabase
        result1 = _verify_supabase_token("cache-test-token")
        # Second call - should hit cache
        result2 = _verify_supabase_token("cache-test-token")

        assert result1.user_id == result2.user_id
        # Supabase should only be called once
        assert mock_client.auth.get_user.call_count == 1

    def test_no_db_returns_none(self):
        with patch("app.auth.get_db", return_value=None):
            result = _verify_supabase_token("any-token")
            assert result is None
