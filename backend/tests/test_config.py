"""Tests for configuration validation."""

import pytest
from unittest.mock import patch


class TestValidateConfig:
    """Test startup config validation."""

    def test_all_set(self):
        with patch.dict("os.environ", {
            "ANTHROPIC_API_KEY": "sk-test",
            "SUPABASE_URL": "https://test.supabase.co",
            "SUPABASE_SERVICE_KEY": "test-key",
            "MASTER_API_KEY": "admin-key",
            "APP_ENV": "development",
        }):
            # Re-import to pick up patched env
            import importlib
            import app.config
            importlib.reload(app.config)
            result = app.config.validate_config()
            assert result["valid"] is True
            assert result["capabilities"]["ai"] is True
            assert result["capabilities"]["database"] is True
            assert result["capabilities"]["admin"] is True
            assert len(result["issues"]) == 0

    def test_missing_anthropic_key(self):
        from app.config import validate_config
        with patch("app.config.ANTHROPIC_API_KEY", ""):
            result = validate_config()
            assert result["valid"] is False
            assert result["capabilities"]["ai"] is False

    def test_missing_supabase(self):
        from app.config import validate_config
        with patch("app.config.SUPABASE_URL", ""):
            with patch("app.config.SUPABASE_SERVICE_KEY", ""):
                result = validate_config()
                assert result["capabilities"]["database"] is False

    def test_invalid_supabase_url(self):
        from app.config import validate_config
        with patch("app.config.SUPABASE_URL", "not-a-url"):
            with patch("app.config.SUPABASE_SERVICE_KEY", "key"):
                result = validate_config()
                assert any("invalid" in i.lower() for i in result["issues"])

    def test_invalid_app_env(self):
        from app.config import validate_config
        with patch("app.config.APP_ENV", "banana"):
            result = validate_config()
            assert any("APP_ENV" in w for w in result["warnings"])

    def test_production_without_api_key_raises(self):
        from app.config import validate_config
        with patch("app.config.APP_ENV", "production"):
            with patch("app.config.ANTHROPIC_API_KEY", ""):
                with pytest.raises(RuntimeError, match="ANTHROPIC_API_KEY"):
                    validate_config()

    def test_missing_master_key_warns(self):
        from app.config import validate_config
        with patch("app.config.MASTER_API_KEY", ""):
            result = validate_config()
            assert any("MASTER_API_KEY" in w for w in result["warnings"])
