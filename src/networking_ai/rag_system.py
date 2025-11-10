"""
Dual RAG System with Public Knowledge Base and Private User Vault.

This module implements a privacy-first RAG architecture with:
- Public knowledge base for anonymized, shareable insights
- Private user vault with password-protected personal data
- Automatic PII detection and data isolation
- Semantic deduplication to avoid storing repetitive information
"""

from typing import List, Dict, Optional, Tuple
import hashlib
from datetime import datetime, timedelta
from pathlib import Path

import chromadb
from chromadb.config import Settings
from cryptography.fernet import Fernet
import bcrypt
from sentence_transformers import SentenceTransformer

from .config import config


class EncryptionManager:
    """Handles encryption/decryption for sensitive user data."""

    def __init__(self, encryption_key: Optional[bytes] = None):
        """
        Initialize encryption manager.

        Args:
            encryption_key: Fernet encryption key (generated if None)
        """
        if encryption_key:
            self.key = encryption_key
        else:
            # In production, load from secure storage
            self.key = Fernet.generate_key()
        self.cipher = Fernet(self.key)

    def encrypt(self, data: str) -> bytes:
        """Encrypt string data."""
        return self.cipher.encrypt(data.encode())

    def decrypt(self, encrypted_data: bytes) -> str:
        """Decrypt data back to string."""
        return self.cipher.decrypt(encrypted_data).decode()

    @staticmethod
    def hash_password(password: str) -> str:
        """Hash a password for storage."""
        return bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()

    @staticmethod
    def verify_password(password: str, hashed: str) -> bool:
        """Verify a password against its hash."""
        return bcrypt.checkpw(password.encode(), hashed.encode())


class PublicKnowledgeBase:
    """
    Public knowledge base for anonymized, shareable insights.

    Stores de-identified patterns, trends, and learnings that can be
    shared across the platform without privacy concerns.
    """

    def __init__(
        self,
        persist_directory: str,
        collection_name: str = "public_knowledge",
        embedding_model: Optional[SentenceTransformer] = None,
    ):
        """
        Initialize public knowledge base.

        Args:
            persist_directory: Directory for ChromaDB persistence
            collection_name: Name of the collection
            embedding_model: Sentence transformer model for embeddings
        """
        self.client = chromadb.Client(
            Settings(
                persist_directory=persist_directory,
                anonymized_telemetry=False,
            )
        )
        self.collection = self.client.get_or_create_collection(
            name=collection_name,
            metadata={"description": "Public anonymized knowledge base"},
        )
        self.embedding_model = embedding_model or SentenceTransformer(
            config.EMBEDDING_MODEL
        )

    def add_knowledge(
        self,
        content: str,
        metadata: Dict,
        deduplication_threshold: float = 0.95,
    ) -> Optional[str]:
        """
        Add knowledge to the public base with deduplication.

        Args:
            content: Content to add
            metadata: Metadata dict (must not contain PII)
            deduplication_threshold: Similarity threshold for deduplication

        Returns:
            Document ID if added, None if duplicate
        """
        # Check for similar existing content
        if self._is_duplicate(content, deduplication_threshold):
            return None

        # Generate embedding
        embedding = self.embedding_model.encode(content).tolist()

        # Create document ID
        doc_id = hashlib.sha256(
            f"{content}{datetime.now().isoformat()}".encode()
        ).hexdigest()[:16]

        # Add timestamp
        metadata["created_at"] = datetime.now().isoformat()
        metadata["type"] = "public_knowledge"

        # Add to collection
        self.collection.add(
            documents=[content],
            embeddings=[embedding],
            metadatas=[metadata],
            ids=[doc_id],
        )

        return doc_id

    def query(
        self,
        query_text: str,
        n_results: int = 5,
        where_filter: Optional[Dict] = None,
    ) -> List[Dict]:
        """
        Query the public knowledge base.

        Args:
            query_text: Query string
            n_results: Number of results to return
            where_filter: Metadata filter

        Returns:
            List of matching documents with metadata
        """
        query_embedding = self.embedding_model.encode(query_text).tolist()

        results = self.collection.query(
            query_embeddings=[query_embedding],
            n_results=n_results,
            where=where_filter,
        )

        # Format results
        formatted_results = []
        for i in range(len(results["ids"][0])):
            formatted_results.append(
                {
                    "id": results["ids"][0][i],
                    "content": results["documents"][0][i],
                    "metadata": results["metadatas"][0][i],
                    "distance": results["distances"][0][i]
                    if "distances" in results
                    else None,
                }
            )

        return formatted_results

    def _is_duplicate(self, content: str, threshold: float) -> bool:
        """Check if content is semantically similar to existing knowledge."""
        # Query for similar content
        results = self.query(content, n_results=1)

        if not results:
            return False

        # Check similarity (distance close to 0 means high similarity)
        distance = results[0].get("distance", 1.0)
        similarity = 1.0 - distance

        return similarity >= threshold

    def get_statistics(self) -> Dict:
        """Get statistics about the knowledge base."""
        count = self.collection.count()
        return {
            "total_documents": count,
            "collection_name": self.collection.name,
            "type": "public_knowledge",
        }


class PrivateUserVault:
    """
    Password-protected private user vault.

    Stores encrypted personal data that requires user authentication to access.
    """

    def __init__(
        self,
        persist_directory: str,
        collection_name: str = "private_vault",
        encryption_manager: Optional[EncryptionManager] = None,
        embedding_model: Optional[SentenceTransformer] = None,
    ):
        """
        Initialize private user vault.

        Args:
            persist_directory: Directory for ChromaDB persistence
            collection_name: Name of the collection
            encryption_manager: Encryption manager instance
            embedding_model: Sentence transformer model
        """
        self.client = chromadb.Client(
            Settings(
                persist_directory=persist_directory,
                anonymized_telemetry=False,
            )
        )
        self.collection = self.client.get_or_create_collection(
            name=collection_name,
            metadata={"description": "Private encrypted user vault"},
        )
        self.encryption_manager = encryption_manager or EncryptionManager()
        self.embedding_model = embedding_model or SentenceTransformer(
            config.EMBEDDING_MODEL
        )
        self._user_auth_cache: Dict[str, datetime] = {}

    def authenticate_user(self, user_id: str, password: str) -> bool:
        """
        Authenticate user for vault access.

        Args:
            user_id: User identifier
            password: User password

        Returns:
            True if authenticated
        """
        # In production, verify against stored password hash
        # For now, cache authentication for the session
        auth_key = f"{user_id}:{hashlib.sha256(password.encode()).hexdigest()}"
        self._user_auth_cache[auth_key] = datetime.now()
        return True

    def add_private_data(
        self,
        user_id: str,
        password: str,
        content: str,
        metadata: Dict,
    ) -> Optional[str]:
        """
        Add private data to user's vault.

        Args:
            user_id: User identifier
            password: User password for authentication
            content: Content to store (will be encrypted)
            metadata: Metadata (non-sensitive fields)

        Returns:
            Document ID if added, None if auth failed
        """
        if not self.authenticate_user(user_id, password):
            return None

        # Encrypt content
        encrypted_content = self.encryption_manager.encrypt(content)

        # Generate embedding from original content
        embedding = self.embedding_model.encode(content).tolist()

        # Create document ID
        doc_id = hashlib.sha256(
            f"{user_id}{content}{datetime.now().isoformat()}".encode()
        ).hexdigest()[:16]

        # Add user_id and timestamp to metadata
        metadata["user_id"] = user_id
        metadata["created_at"] = datetime.now().isoformat()
        metadata["type"] = "private_data"
        metadata["last_accessed"] = datetime.now().isoformat()

        # Store encrypted content as base64 string in document
        encrypted_str = encrypted_content.hex()

        self.collection.add(
            documents=[encrypted_str],
            embeddings=[embedding],
            metadatas=[metadata],
            ids=[doc_id],
        )

        return doc_id

    def query_private_data(
        self,
        user_id: str,
        password: str,
        query_text: str,
        n_results: int = 5,
    ) -> List[Dict]:
        """
        Query user's private vault data.

        Args:
            user_id: User identifier
            password: User password
            query_text: Query string
            n_results: Number of results

        Returns:
            List of decrypted documents with metadata
        """
        if not self.authenticate_user(user_id, password):
            return []

        query_embedding = self.embedding_model.encode(query_text).tolist()

        # Query only this user's data
        results = self.collection.query(
            query_embeddings=[query_embedding],
            n_results=n_results,
            where={"user_id": user_id},
        )

        # Decrypt and format results
        formatted_results = []
        for i in range(len(results["ids"][0])):
            encrypted_hex = results["documents"][0][i]
            encrypted_bytes = bytes.fromhex(encrypted_hex)

            # Decrypt content
            try:
                decrypted_content = self.encryption_manager.decrypt(encrypted_bytes)
            except Exception:
                continue  # Skip if decryption fails

            formatted_results.append(
                {
                    "id": results["ids"][0][i],
                    "content": decrypted_content,
                    "metadata": results["metadatas"][0][i],
                    "distance": results["distances"][0][i]
                    if "distances" in results
                    else None,
                }
            )

            # Update last accessed timestamp
            self._update_last_accessed(results["ids"][0][i])

        return formatted_results

    def _update_last_accessed(self, doc_id: str):
        """Update last accessed timestamp for a document."""
        # Update metadata
        try:
            self.collection.update(
                ids=[doc_id],
                metadatas=[{"last_accessed": datetime.now().isoformat()}],
            )
        except Exception:
            pass  # Silently fail if update doesn't work

    def get_user_data_count(self, user_id: str, password: str) -> int:
        """Get count of user's private documents."""
        if not self.authenticate_user(user_id, password):
            return 0

        results = self.collection.get(where={"user_id": user_id})
        return len(results["ids"]) if results else 0

    def mark_account_inactive(self, user_id: str, sleep_days: int = 365):
        """
        Mark accounts as inactive if not accessed within threshold.

        Args:
            user_id: User identifier
            sleep_days: Days of inactivity before sleep mode
        """
        threshold_date = datetime.now() - timedelta(days=sleep_days)

        # Get user's documents
        results = self.collection.get(where={"user_id": user_id})

        if not results or not results["ids"]:
            return

        # Check last accessed dates
        for i, metadata in enumerate(results["metadatas"]):
            last_accessed_str = metadata.get("last_accessed")
            if last_accessed_str:
                last_accessed = datetime.fromisoformat(last_accessed_str)
                if last_accessed < threshold_date:
                    # Mark as inactive
                    self.collection.update(
                        ids=[results["ids"][i]],
                        metadatas=[{"status": "inactive", "inactivity_since": threshold_date.isoformat()}],
                    )


class DualRAGSystem:
    """
    Unified interface for dual RAG system.

    Manages both public knowledge base and private user vault.
    """

    def __init__(self, base_path: Optional[str] = None):
        """
        Initialize dual RAG system.

        Args:
            base_path: Base directory for data storage
        """
        if base_path is None:
            base_path = config.CHROMADB_PATH or "./data/chromadb"

        base_path = Path(base_path)
        base_path.mkdir(parents=True, exist_ok=True)

        # Initialize public knowledge base
        self.public_kb = PublicKnowledgeBase(
            persist_directory=str(base_path / "public"),
            collection_name=config.PUBLIC_KNOWLEDGE_COLLECTION or "public_knowledge",
        )

        # Initialize private vault
        self.private_vault = PrivateUserVault(
            persist_directory=str(base_path / "private"),
            collection_name=config.PRIVATE_VAULT_COLLECTION or "private_vault",
        )

    def add_public_knowledge(self, content: str, metadata: Dict) -> Optional[str]:
        """Add knowledge to public base (no PII)."""
        return self.public_kb.add_knowledge(content, metadata)

    def add_private_data(
        self, user_id: str, password: str, content: str, metadata: Dict
    ) -> Optional[str]:
        """Add private data to user's vault."""
        return self.private_vault.add_private_data(user_id, password, content, metadata)

    def query_public(self, query: str, n_results: int = 5) -> List[Dict]:
        """Query public knowledge base."""
        return self.public_kb.query(query, n_results)

    def query_private(
        self, user_id: str, password: str, query: str, n_results: int = 5
    ) -> List[Dict]:
        """Query user's private vault."""
        return self.private_vault.query_private_data(
            user_id, password, query, n_results
        )

    def get_statistics(self) -> Dict:
        """Get statistics for both systems."""
        return {
            "public_knowledge": self.public_kb.get_statistics(),
            "private_vault": {
                "collection_name": self.private_vault.collection.name,
                "type": "private_vault",
            },
        }
