"""
Master AI RAG Manager.

Manages ChromaDB collections for:
- Recruiter training guides
- Behavioral patterns
- Conversation templates
- Network knowledge
"""

import os
from typing import List, Dict, Optional
import chromadb
from chromadb.config import Settings


class MasterRAGManager:
    """
    Manages Master AI's RAG (Retrieval-Augmented Generation) database.

    Uses ChromaDB to store and retrieve:
    - Industry-specific recruiter training
    - Behavioral patterns across users
    - Conversation templates
    - Network knowledge for cross-learning
    """

    def __init__(self, persist_directory: str = "./data/master_rag"):
        """
        Initialize Master RAG Manager.

        Args:
            persist_directory: Directory to persist ChromaDB data
        """
        self.persist_directory = persist_directory

        # Ensure directory exists
        os.makedirs(persist_directory, exist_ok=True)

        # Initialize ChromaDB client
        self.client = chromadb.Client(Settings(
            chroma_db_impl="duckdb+parquet",
            persist_directory=persist_directory
        ))

        # Initialize collections
        self._init_collections()

    def _init_collections(self):
        """Initialize all Master AI collections."""
        # Recruiter Training: Industry-specific guides
        self.recruiter_training = self.client.get_or_create_collection(
            name="recruiter_training",
            metadata={"description": "Industry-specific recruiter training guides"}
        )

        # Behavioral Patterns: Aggregated user behaviors
        self.behavioral_patterns = self.client.get_or_create_collection(
            name="behavioral_patterns",
            metadata={"description": "Behavioral patterns across user segments"}
        )

        # Conversation Templates: Interview and conversation templates
        self.conversation_templates = self.client.get_or_create_collection(
            name="conversation_templates",
            metadata={"description": "Conversation templates by industry and role"}
        )

        # Network Knowledge: Cross-learning data
        self.network_knowledge = self.client.get_or_create_collection(
            name="network_knowledge",
            metadata={"description": "Network knowledge for cross-learning"}
        )

        print(f"[MASTER RAG] Initialized 4 collections in {self.persist_directory}")

    # ========================================================================
    # Recruiter Training
    # ========================================================================

    def add_recruiter_training(
        self,
        industry: str,
        content: str,
        metadata: Dict = None
    ) -> str:
        """
        Add recruiter training guide for an industry.

        Args:
            industry: Industry name (e.g., "finance", "tech")
            content: Training content (markdown format)
            metadata: Additional metadata

        Returns:
            Document ID
        """
        doc_id = f"recruiter_{industry}"

        if metadata is None:
            metadata = {}

        metadata.update({
            "industry": industry,
            "type": "recruiter_guide"
        })

        self.recruiter_training.add(
            documents=[content],
            metadatas=[metadata],
            ids=[doc_id]
        )

        print(f"[MASTER RAG] Added recruiter training for {industry}")

        return doc_id

    def get_recruiter_training(self, industry: str) -> Optional[str]:
        """
        Get recruiter training for an industry.

        Args:
            industry: Industry name

        Returns:
            Training content or None
        """
        doc_id = f"recruiter_{industry}"

        results = self.recruiter_training.get(
            ids=[doc_id]
        )

        if results and results["documents"]:
            return results["documents"][0]

        return None

    def query_recruiter_training(
        self,
        query: str,
        industry: str = None,
        n_results: int = 3
    ) -> List[Dict]:
        """
        Query recruiter training guides.

        Args:
            query: Search query
            industry: Optional industry filter
            n_results: Number of results

        Returns:
            List of matching documents with metadata
        """
        where = {"industry": industry} if industry else None

        results = self.recruiter_training.query(
            query_texts=[query],
            n_results=n_results,
            where=where
        )

        return [
            {
                "content": doc,
                "metadata": meta,
                "distance": dist
            }
            for doc, meta, dist in zip(
                results["documents"][0],
                results["metadatas"][0],
                results["distances"][0]
            )
        ]

    # ========================================================================
    # Behavioral Patterns
    # ========================================================================

    def add_behavioral_pattern(
        self,
        user_segment: str,
        pattern_type: str,
        pattern_data: Dict,
        confidence: float = 0.5
    ) -> str:
        """
        Add behavioral pattern for a user segment.

        Args:
            user_segment: Segment ID (e.g., "system_engineer_finance_5yrs_python")
            pattern_type: Type of pattern
            pattern_data: Pattern data
            confidence: Confidence score (0-1)

        Returns:
            Document ID
        """
        doc_id = f"{user_segment}_{pattern_type}"

        # Convert pattern data to text for embedding
        content = f"Segment: {user_segment}\nPattern: {pattern_type}\nData: {pattern_data}"

        metadata = {
            "user_segment": user_segment,
            "pattern_type": pattern_type,
            "confidence": confidence,
            "pattern_data": str(pattern_data)
        }

        self.behavioral_patterns.add(
            documents=[content],
            metadatas=[metadata],
            ids=[doc_id]
        )

        print(f"[MASTER RAG] Added behavioral pattern: {pattern_type} for {user_segment}")

        return doc_id

    def get_behavioral_patterns(
        self,
        user_segment: str
    ) -> List[Dict]:
        """
        Get all behavioral patterns for a user segment.

        Args:
            user_segment: Segment ID

        Returns:
            List of patterns
        """
        results = self.behavioral_patterns.get(
            where={"user_segment": user_segment}
        )

        if not results or not results["documents"]:
            return []

        return [
            {
                "content": doc,
                "metadata": meta
            }
            for doc, meta in zip(results["documents"], results["metadatas"])
        ]

    # ========================================================================
    # Conversation Templates
    # ========================================================================

    def add_conversation_template(
        self,
        template_id: str,
        industry: str,
        role: str,
        content: str,
        metadata: Dict = None
    ) -> str:
        """
        Add conversation template.

        Args:
            template_id: Unique template ID
            industry: Industry
            role: Role type
            content: Template content
            metadata: Additional metadata

        Returns:
            Document ID
        """
        if metadata is None:
            metadata = {}

        metadata.update({
            "template_id": template_id,
            "industry": industry,
            "role": role,
            "type": "conversation_template"
        })

        self.conversation_templates.add(
            documents=[content],
            metadatas=[metadata],
            ids=[template_id]
        )

        print(f"[MASTER RAG] Added conversation template: {template_id}")

        return template_id

    def get_conversation_template(
        self,
        industry: str,
        role: str
    ) -> Optional[str]:
        """
        Get conversation template for industry and role.

        Args:
            industry: Industry name
            role: Role type

        Returns:
            Template content or None
        """
        results = self.conversation_templates.get(
            where={"industry": industry, "role": role}
        )

        if results and results["documents"]:
            return results["documents"][0]

        return None

    # ========================================================================
    # Network Knowledge
    # ========================================================================

    def add_network_knowledge(
        self,
        knowledge_id: str,
        user_segment: str,
        knowledge_type: str,
        content: str,
        metadata: Dict = None
    ) -> str:
        """
        Add network knowledge for cross-learning.

        Args:
            knowledge_id: Unique knowledge ID
            user_segment: User segment
            knowledge_type: Type of knowledge
            content: Knowledge content
            metadata: Additional metadata

        Returns:
            Document ID
        """
        if metadata is None:
            metadata = {}

        metadata.update({
            "knowledge_id": knowledge_id,
            "user_segment": user_segment,
            "knowledge_type": knowledge_type
        })

        self.network_knowledge.add(
            documents=[content],
            metadatas=[metadata],
            ids=[knowledge_id]
        )

        print(f"[MASTER RAG] Added network knowledge: {knowledge_id}")

        return knowledge_id

    def query_network_knowledge(
        self,
        query: str,
        user_segment: str = None,
        n_results: int = 5
    ) -> List[Dict]:
        """
        Query network knowledge.

        Args:
            query: Search query
            user_segment: Optional segment filter
            n_results: Number of results

        Returns:
            List of matching knowledge
        """
        where = {"user_segment": user_segment} if user_segment else None

        results = self.network_knowledge.query(
            query_texts=[query],
            n_results=n_results,
            where=where
        )

        return [
            {
                "content": doc,
                "metadata": meta,
                "distance": dist
            }
            for doc, meta, dist in zip(
                results["documents"][0],
                results["metadatas"][0],
                results["distances"][0]
            )
        ]

    # ========================================================================
    # Utility Methods
    # ========================================================================

    def persist(self):
        """Persist all collections to disk."""
        self.client.persist()
        print(f"[MASTER RAG] Persisted all collections to {self.persist_directory}")

    def get_stats(self) -> Dict:
        """Get statistics about all collections."""
        return {
            "recruiter_training": self.recruiter_training.count(),
            "behavioral_patterns": self.behavioral_patterns.count(),
            "conversation_templates": self.conversation_templates.count(),
            "network_knowledge": self.network_knowledge.count()
        }


# Factory function
def create_master_rag(persist_directory: str = "./data/master_rag") -> MasterRAGManager:
    """
    Create Master RAG Manager instance.

    Args:
        persist_directory: Directory to persist data

    Returns:
        MasterRAGManager instance
    """
    return MasterRAGManager(persist_directory=persist_directory)
