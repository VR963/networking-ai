"""Tests for RAG embedding store."""

import pytest
from unittest.mock import patch, MagicMock


class TestEmbeddingStore:
    """Test the embedding and similarity search system."""

    def setup_method(self):
        from app.services.embedding_store import EmbeddingStore
        self.store = EmbeddingStore()

    def test_text_to_features_deterministic(self):
        vec1 = self.store._text_to_features("hello world")
        vec2 = self.store._text_to_features("hello world")
        assert vec1 == vec2

    def test_text_to_features_different_inputs(self):
        vec1 = self.store._text_to_features("software engineer")
        vec2 = self.store._text_to_features("marketing manager")
        assert vec1 != vec2

    def test_text_to_features_dimension(self):
        vec = self.store._text_to_features("test content")
        assert len(vec) == 128

    def test_text_to_features_normalized(self):
        vec = self.store._text_to_features("some sample text here")
        magnitude = sum(v * v for v in vec) ** 0.5
        assert abs(magnitude - 1.0) < 0.01  # Should be unit vector

    def test_cosine_similarity_identical(self):
        vec = [1.0, 0.0, 1.0, 0.0]
        sim = self.store._cosine_similarity(vec, vec)
        assert abs(sim - 1.0) < 0.001

    def test_cosine_similarity_orthogonal(self):
        vec1 = [1.0, 0.0, 0.0, 0.0]
        vec2 = [0.0, 1.0, 0.0, 0.0]
        sim = self.store._cosine_similarity(vec1, vec2)
        assert abs(sim) < 0.001

    def test_cosine_similarity_opposite(self):
        vec1 = [1.0, 1.0]
        vec2 = [-1.0, -1.0]
        sim = self.store._cosine_similarity(vec1, vec2)
        assert sim < 0

    def test_similar_content_high_similarity(self):
        vec1 = self.store._text_to_features("senior python developer backend")
        vec2 = self.store._text_to_features("python backend developer senior")
        sim = self.store._cosine_similarity(vec1, vec2)
        assert sim > 0.5  # Similar content should have high similarity

    def test_dissimilar_content_low_similarity(self):
        vec1 = self.store._text_to_features("quantum physics research paper university")
        vec2 = self.store._text_to_features("chocolate cake baking recipe kitchen")
        sim = self.store._cosine_similarity(vec1, vec2)
        assert sim < 0.5  # Dissimilar content should have low similarity

    @patch("app.services.embedding_store.get_db")
    def test_index_content(self, mock_get_db):
        mock_client = MagicMock()
        mock_table = MagicMock()
        mock_table.upsert.return_value = mock_table
        mock_table.insert.return_value = mock_table
        mock_table.execute.return_value = MagicMock(data=[{"id": "test-id"}])
        mock_client.table.return_value = mock_table
        mock_get_db.return_value = mock_client

        import asyncio
        result = asyncio.run(self.store.index_content(
            content_type="test",
            content_id="123",
            text_content="sample text for indexing",
            user_id="user1",
        ))

        mock_client.table.assert_called_with("cv2_embeddings")

    @patch("app.services.embedding_store.get_db")
    def test_query_similar(self, mock_get_db):
        mock_client = MagicMock()
        mock_table = MagicMock()
        mock_table.select.return_value = mock_table
        mock_table.eq.return_value = mock_table
        mock_table.limit.return_value = mock_table
        mock_table.execute.return_value = MagicMock(data=[
            {
                "content_id": "doc1",
                "content_type": "conversation",
                "text_content": "python developer looking for work",
                "embedding": self.store._text_to_features("python developer"),
                "metadata": {},
                "user_id": "u1",
            }
        ])
        mock_client.table.return_value = mock_table
        mock_get_db.return_value = mock_client

        import asyncio
        results = asyncio.run(self.store.query_similar(
            query_text="python engineer",
            content_type="conversation",
            limit=5,
        ))
        assert isinstance(results, list)

    def test_empty_text_returns_none(self):
        import asyncio
        result = asyncio.run(self.store._generate_embedding(""))
        assert result is None
