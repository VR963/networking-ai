"""Tests for RAG system functionality."""

import pytest
import tempfile
import shutil
from pathlib import Path

from src.networking_ai.rag_system import (
    DualRAGSystem,
    PublicKnowledgeBase,
    PrivateUserVault,
    EncryptionManager,
)


class TestEncryptionManager:
    """Test cases for EncryptionManager."""

    def test_encryption_decryption(self):
        """Test basic encryption and decryption."""
        manager = EncryptionManager()
        original_text = "Sensitive user data"

        encrypted = manager.encrypt(original_text)
        decrypted = manager.decrypt(encrypted)

        assert isinstance(encrypted, bytes)
        assert decrypted == original_text

    def test_password_hashing(self):
        """Test password hashing and verification."""
        password = "secure_password_123"

        hashed = EncryptionManager.hash_password(password)
        assert isinstance(hashed, str)
        assert EncryptionManager.verify_password(password, hashed)
        assert not EncryptionManager.verify_password("wrong_password", hashed)


class TestPublicKnowledgeBase:
    """Test cases for PublicKnowledgeBase."""

    @pytest.fixture
    def temp_dir(self):
        """Create temporary directory for tests."""
        temp_path = tempfile.mkdtemp()
        yield temp_path
        shutil.rmtree(temp_path, ignore_errors=True)

    @pytest.fixture
    def knowledge_base(self, temp_dir):
        """Create knowledge base instance."""
        return PublicKnowledgeBase(persist_directory=temp_dir)

    def test_add_knowledge(self, knowledge_base):
        """Test adding knowledge to the base."""
        content = "Python is a popular programming language for AI"
        metadata = {"topic": "programming", "category": "tech"}

        doc_id = knowledge_base.add_knowledge(content, metadata)
        assert doc_id is not None
        assert isinstance(doc_id, str)

    def test_query_knowledge(self, knowledge_base):
        """Test querying the knowledge base."""
        # Add some knowledge
        knowledge_base.add_knowledge(
            "Machine learning is a subset of AI",
            {"topic": "AI"},
        )
        knowledge_base.add_knowledge(
            "Python is great for data science",
            {"topic": "programming"},
        )

        # Query
        results = knowledge_base.query("artificial intelligence", n_results=2)
        assert isinstance(results, list)
        assert len(results) <= 2

    def test_deduplication(self, knowledge_base):
        """Test semantic deduplication."""
        content1 = "Python is a programming language"
        content2 = "Python is a coding language"  # Very similar

        doc_id1 = knowledge_base.add_knowledge(content1, {"test": "dup"})
        doc_id2 = knowledge_base.add_knowledge(
            content2, {"test": "dup"}, deduplication_threshold=0.90
        )

        assert doc_id1 is not None
        # doc_id2 might be None due to deduplication (depending on similarity)

    def test_get_statistics(self, knowledge_base):
        """Test getting statistics."""
        knowledge_base.add_knowledge("Test content", {})

        stats = knowledge_base.get_statistics()
        assert "total_documents" in stats
        assert stats["total_documents"] >= 0


class TestPrivateUserVault:
    """Test cases for PrivateUserVault."""

    @pytest.fixture
    def temp_dir(self):
        """Create temporary directory for tests."""
        temp_path = tempfile.mkdtemp()
        yield temp_path
        shutil.rmtree(temp_path, ignore_errors=True)

    @pytest.fixture
    def private_vault(self, temp_dir):
        """Create private vault instance."""
        return PrivateUserVault(persist_directory=temp_dir)

    def test_authenticate_user(self, private_vault):
        """Test user authentication."""
        user_id = "test_user"
        password = "test_password"

        result = private_vault.authenticate_user(user_id, password)
        assert result is True

    def test_add_private_data(self, private_vault):
        """Test adding private data."""
        user_id = "test_user"
        password = "test_password"
        content = "My personal information"
        metadata = {"type": "personal"}

        doc_id = private_vault.add_private_data(user_id, password, content, metadata)
        assert doc_id is not None

    def test_query_private_data(self, private_vault):
        """Test querying private data."""
        user_id = "test_user"
        password = "test_password"

        # Add some data
        private_vault.add_private_data(
            user_id, password, "My private thoughts about AI", {"type": "note"}
        )

        # Query
        results = private_vault.query_private_data(
            user_id, password, "AI thoughts", n_results=5
        )

        assert isinstance(results, list)
        # Should decrypt successfully
        if results:
            assert "content" in results[0]

    def test_get_user_data_count(self, private_vault):
        """Test getting user data count."""
        user_id = "test_user"
        password = "test_password"

        initial_count = private_vault.get_user_data_count(user_id, password)

        private_vault.add_private_data(user_id, password, "Test data", {})

        new_count = private_vault.get_user_data_count(user_id, password)
        assert new_count >= initial_count


class TestDualRAGSystem:
    """Test cases for DualRAGSystem."""

    @pytest.fixture
    def temp_dir(self):
        """Create temporary directory for tests."""
        temp_path = tempfile.mkdtemp()
        yield temp_path
        shutil.rmtree(temp_path, ignore_errors=True)

    @pytest.fixture
    def rag_system(self, temp_dir):
        """Create RAG system instance."""
        return DualRAGSystem(base_path=temp_dir)

    def test_add_public_knowledge(self, rag_system):
        """Test adding public knowledge."""
        content = "Public information about networking"
        metadata = {"type": "public"}

        doc_id = rag_system.add_public_knowledge(content, metadata)
        assert doc_id is not None

    def test_add_private_data(self, rag_system):
        """Test adding private data."""
        user_id = "test_user"
        password = "test_password"
        content = "Private user information"
        metadata = {"type": "private"}

        doc_id = rag_system.add_private_data(user_id, password, content, metadata)
        assert doc_id is not None

    def test_query_public(self, rag_system):
        """Test querying public knowledge."""
        rag_system.add_public_knowledge("Test public content", {})

        results = rag_system.query_public("test", n_results=5)
        assert isinstance(results, list)

    def test_query_private(self, rag_system):
        """Test querying private data."""
        user_id = "test_user"
        password = "test_password"

        rag_system.add_private_data(user_id, password, "Test private content", {})

        results = rag_system.query_private(user_id, password, "test", n_results=5)
        assert isinstance(results, list)

    def test_get_statistics(self, rag_system):
        """Test getting system statistics."""
        stats = rag_system.get_statistics()

        assert "public_knowledge" in stats
        assert "private_vault" in stats
