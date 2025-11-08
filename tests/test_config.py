"""Tests for configuration module."""

import pytest
from src.networking_ai.config import Config


class TestConfig:
    """Test cases for Config class."""

    def test_config_defaults(self):
        """Test default configuration values."""
        assert Config.DEFAULT_MODEL is not None
        assert Config.MAX_TOKENS > 0
        assert Config.TEMPERATURE >= 0
        assert Config.MIN_SIMILARITY_SCORE >= 0
        assert Config.TOP_N_RECOMMENDATIONS > 0

    def test_config_validation(self):
        """Test configuration validation."""
        # Should not raise an error
        result = Config.validate()
        assert isinstance(result, bool)

    def test_embedding_model(self):
        """Test embedding model configuration."""
        assert Config.EMBEDDING_MODEL is not None
        assert len(Config.EMBEDDING_MODEL) > 0
