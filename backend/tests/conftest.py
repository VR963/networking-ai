"""Test configuration and shared fixtures."""

import sys
import os
from unittest.mock import MagicMock, AsyncMock, patch

import pytest

# Ensure app module is importable
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

# Mock environment variables before any app imports
os.environ.setdefault("SUPABASE_URL", "http://test-supabase.local")
os.environ.setdefault("SUPABASE_SERVICE_KEY", "test-service-key")
os.environ.setdefault("ANTHROPIC_API_KEY", "test-anthropic-key")
os.environ.setdefault("MASTER_API_KEY", "test-master-key")


@pytest.fixture
def mock_supabase():
    """Mock Supabase client that returns configurable responses."""
    client = MagicMock()

    # Default: table().select().execute() returns empty
    table_mock = MagicMock()
    table_mock.select.return_value = table_mock
    table_mock.insert.return_value = table_mock
    table_mock.update.return_value = table_mock
    table_mock.upsert.return_value = table_mock
    table_mock.delete.return_value = table_mock
    table_mock.eq.return_value = table_mock
    table_mock.neq.return_value = table_mock
    table_mock.order.return_value = table_mock
    table_mock.limit.return_value = table_mock
    table_mock.execute.return_value = MagicMock(data=[], count=0)

    client.table.return_value = table_mock
    return client


@pytest.fixture
def mock_db(mock_supabase):
    """Patch get_db to return mock supabase client."""
    with patch("app.database.get_db", return_value=mock_supabase):
        yield mock_supabase


@pytest.fixture
def mock_anthropic():
    """Mock Anthropic API client."""
    with patch("anthropic.Anthropic") as mock_cls:
        client = MagicMock()
        response = MagicMock()
        response.content = [MagicMock(text="Test AI response")]
        response.usage = MagicMock(input_tokens=100, output_tokens=50)
        client.messages.create.return_value = response
        mock_cls.return_value = client
        yield client
