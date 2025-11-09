"""
Cold Memory Layer - ChromaDB-based long-term archive

Features:
- <10s query performance (vector search)
- Unlimited capacity
- Semantic search with embeddings
- Per-user collections
- Permanent storage (no expiry)
"""

import logging
from typing import List, Optional, Dict, Any
from datetime import datetime
import uuid

from ..services.chromadb_service import ChromaDBService
from .hot_memory import Memory

logger = logging.getLogger(__name__)


class ColdMemory:
    """
    ChromaDB-based cold memory layer for long-term archive.

    Performance:
    - Query: <10s (vector search with semantic similarity)
    - Store: <500ms (embedding generation + storage)
    - Capacity: Unlimited
    - Retention: Permanent (no automatic deletion)
    """

    def __init__(self, chromadb_service: ChromaDBService):
        """
        Initialize ColdMemory layer.

        Args:
            chromadb_service: ChromaDB service instance
        """
        self.chromadb = chromadb_service

    def query(
        self,
        user_id: int,
        query: str,
        limit: int = 10,
        min_similarity: float = 0.5
    ) -> List[Memory]:
        """
        Query cold memory using semantic vector search.

        Args:
            user_id: User ID to search for
            query: Search query (semantic search)
            limit: Maximum number of results (default 10)
            min_similarity: Minimum similarity score (0.0 to 1.0, default 0.5)

        Returns:
            List of Memory objects with similarity scores
        """
        collection_name = self._get_collection_name(user_id)

        try:
            # Ensure collection exists
            self.chromadb.create_collection(
                collection_name=collection_name,
                metadata={"user_id": user_id, "type": "cold_memory"}
            )

            # Query ChromaDB with semantic search
            results = self.chromadb.query_collection(
                collection_name=collection_name,
                query_texts=[query],
                n_results=limit
            )

            # Convert ChromaDB results to Memory objects
            memories = []

            if results and results.get('documents') and len(results['documents']) > 0:
                documents = results['documents'][0]  # First query results
                metadatas = results.get('metadatas', [[]])[0]
                distances = results.get('distances', [[]])[0]
                ids = results.get('ids', [[]])[0]

                for i, document in enumerate(documents):
                    # ChromaDB returns distance (lower is better)
                    # Convert to similarity score (higher is better)
                    # distance = 0 => similarity = 1.0
                    # distance = 2 => similarity = 0.0
                    distance = distances[i] if i < len(distances) else 1.0
                    similarity = max(0.0, 1.0 - (distance / 2.0))

                    # Filter by minimum similarity
                    if similarity < min_similarity:
                        continue

                    metadata = metadatas[i] if i < len(metadatas) else {}

                    # Parse metadata
                    memory_id = metadata.get('memory_id', int(ids[i].split('_')[-1]) if '_' in ids[i] else 0)
                    created_at_str = metadata.get('created_at')
                    last_accessed_str = metadata.get('last_accessed')

                    # Parse datetime strings
                    created_at = (
                        datetime.fromisoformat(created_at_str)
                        if created_at_str
                        else datetime.utcnow()
                    )
                    last_accessed = (
                        datetime.fromisoformat(last_accessed_str)
                        if last_accessed_str
                        else datetime.utcnow()
                    )

                    memory = Memory(
                        id=memory_id,
                        user_id=user_id,
                        content=document,
                        metadata=metadata,
                        created_at=created_at,
                        last_accessed=last_accessed,
                        access_count=metadata.get('access_count', 0),
                        importance=metadata.get('importance', 0.5),
                        tier='cold',
                        score=similarity
                    )
                    memories.append(memory)

            logger.info(f"ColdMemory query for user {user_id}: found {len(memories)} results")
            return memories

        except Exception as e:
            logger.error(f"ColdMemory query error: {str(e)}")
            return []

    def store(
        self,
        user_id: int,
        memory_id: int,
        content: str,
        metadata: Optional[Dict[str, Any]] = None,
        created_at: Optional[datetime] = None,
        last_accessed: Optional[datetime] = None
    ) -> bool:
        """
        Store a memory in cold tier (archive).

        Args:
            user_id: User ID
            memory_id: Memory ID (from warm tier)
            content: Memory content
            metadata: Optional metadata
            created_at: Creation timestamp
            last_accessed: Last access timestamp

        Returns:
            True if successful, False otherwise
        """
        collection_name = self._get_collection_name(user_id)

        try:
            # Ensure collection exists
            self.chromadb.create_collection(
                collection_name=collection_name,
                metadata={"user_id": user_id, "type": "cold_memory"}
            )

            # Prepare metadata for ChromaDB
            chroma_metadata = metadata.copy() if metadata else {}
            chroma_metadata.update({
                "memory_id": memory_id,
                "user_id": user_id,
                "created_at": (created_at or datetime.utcnow()).isoformat(),
                "last_accessed": (last_accessed or datetime.utcnow()).isoformat(),
                "tier": "cold"
            })

            # Generate unique ID
            doc_id = f"user_{user_id}_memory_{memory_id}"

            # Add to ChromaDB
            self.chromadb.add_documents(
                collection_name=collection_name,
                documents=[content],
                metadatas=[chroma_metadata],
                ids=[doc_id]
            )

            logger.info(f"ColdMemory stored memory {memory_id} for user {user_id}")
            return True

        except Exception as e:
            logger.error(f"ColdMemory store error: {str(e)}")
            return False

    def delete(self, user_id: int, memory_id: int) -> bool:
        """
        Delete a memory from cold tier.

        Args:
            user_id: User ID
            memory_id: Memory ID

        Returns:
            True if successful, False otherwise
        """
        collection_name = self._get_collection_name(user_id)

        try:
            doc_id = f"user_{user_id}_memory_{memory_id}"

            self.chromadb.delete_documents(
                collection_name=collection_name,
                ids=[doc_id]
            )

            logger.info(f"ColdMemory deleted memory {memory_id} for user {user_id}")
            return True

        except Exception as e:
            logger.error(f"ColdMemory delete error: {str(e)}")
            return False

    def get_count(self, user_id: int) -> int:
        """
        Get count of memories in cold tier for a user.

        Args:
            user_id: User ID

        Returns:
            Number of memories
        """
        collection_name = self._get_collection_name(user_id)

        try:
            # Try to get collection
            collection = self.chromadb.client.get_collection(
                name=collection_name,
                embedding_function=self.chromadb.embedding_function
            )

            # Get count
            count = collection.count()
            return count

        except Exception as e:
            # Collection doesn't exist or error
            logger.debug(f"ColdMemory get_count: {str(e)}")
            return 0

    def clear_user_memories(self, user_id: int) -> bool:
        """
        Clear all memories for a user (delete collection).

        Args:
            user_id: User ID

        Returns:
            True if successful, False otherwise
        """
        collection_name = self._get_collection_name(user_id)

        try:
            self.chromadb.delete_collection(collection_name)
            logger.info(f"ColdMemory cleared all memories for user {user_id}")
            return True

        except Exception as e:
            logger.error(f"ColdMemory clear error: {str(e)}")
            return False

    def migrate_from_warm(
        self,
        user_id: int,
        memories: List[Memory]
    ) -> int:
        """
        Migrate multiple memories from warm to cold tier.

        Args:
            user_id: User ID
            memories: List of Memory objects to migrate

        Returns:
            Number of successfully migrated memories
        """
        collection_name = self._get_collection_name(user_id)
        success_count = 0

        try:
            # Ensure collection exists
            self.chromadb.create_collection(
                collection_name=collection_name,
                metadata={"user_id": user_id, "type": "cold_memory"}
            )

            # Batch prepare documents
            documents = []
            metadatas = []
            ids = []

            for memory in memories:
                # Prepare metadata
                chroma_metadata = memory.metadata.copy() if memory.metadata else {}
                chroma_metadata.update({
                    "memory_id": memory.id,
                    "user_id": user_id,
                    "created_at": memory.created_at.isoformat(),
                    "last_accessed": memory.last_accessed.isoformat(),
                    "access_count": memory.access_count,
                    "importance": memory.importance,
                    "tier": "cold"
                })

                documents.append(memory.content)
                metadatas.append(chroma_metadata)
                ids.append(f"user_{user_id}_memory_{memory.id}")

            # Batch add to ChromaDB
            if documents:
                self.chromadb.add_documents(
                    collection_name=collection_name,
                    documents=documents,
                    metadatas=metadatas,
                    ids=ids
                )
                success_count = len(documents)

            logger.info(f"ColdMemory migrated {success_count} memories for user {user_id}")
            return success_count

        except Exception as e:
            logger.error(f"ColdMemory migration error: {str(e)}")
            return success_count

    def _get_collection_name(self, user_id: int) -> str:
        """
        Get collection name for user's cold memories.

        Args:
            user_id: User ID

        Returns:
            Collection name
        """
        return f"user_{user_id}_cold_memory"
