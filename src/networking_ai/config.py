"""Configuration management for Networking AI."""

import os
from typing import Optional
from dotenv import load_dotenv

# Load environment variables
load_dotenv()


class Config:
    """Application configuration."""

    # Anthropic API Configuration
    ANTHROPIC_API_KEY: Optional[str] = os.getenv("ANTHROPIC_API_KEY")
    DEFAULT_MODEL: str = os.getenv("DEFAULT_MODEL", "claude-3-5-sonnet-20241022")
    MAX_TOKENS: int = int(os.getenv("MAX_TOKENS", "4096"))
    TEMPERATURE: float = float(os.getenv("TEMPERATURE", "0.7"))

    # Similarity Thresholds
    MIN_SIMILARITY_SCORE: float = float(os.getenv("MIN_SIMILARITY_SCORE", "0.6"))
    TOP_N_RECOMMENDATIONS: int = int(os.getenv("TOP_N_RECOMMENDATIONS", "10"))

    # Feature Flags
    DEBUG: bool = os.getenv("DEBUG", "false").lower() == "true"
    ENABLE_AI_ANALYSIS: bool = os.getenv("ENABLE_AI_ANALYSIS", "true").lower() == "true"
    ENABLE_CACHING: bool = os.getenv("ENABLE_CACHING", "true").lower() == "true"

    # Sentence Transformer Model
    EMBEDDING_MODEL: str = os.getenv("EMBEDDING_MODEL", "all-MiniLM-L6-v2")

    # RAG Configuration
    CHROMADB_PATH: str = os.getenv("CHROMADB_PATH", "./data/chromadb")
    PUBLIC_KNOWLEDGE_COLLECTION: str = os.getenv("PUBLIC_KNOWLEDGE_COLLECTION", "public_knowledge")
    PRIVATE_VAULT_COLLECTION: str = os.getenv("PRIVATE_VAULT_COLLECTION", "private_vault")

    # Security & Encryption
    ENCRYPTION_KEY: Optional[str] = os.getenv("ENCRYPTION_KEY")
    MASTER_SALT: Optional[str] = os.getenv("MASTER_SALT")

    # Knowledge Learning
    ENABLE_KNOWLEDGE_LEARNING: bool = os.getenv("ENABLE_KNOWLEDGE_LEARNING", "true").lower() == "true"
    DEDUPLICATION_THRESHOLD: float = float(os.getenv("DEDUPLICATION_THRESHOLD", "0.95"))
    MIN_INTERACTION_QUALITY_SCORE: float = float(os.getenv("MIN_INTERACTION_QUALITY_SCORE", "0.7"))

    # Account Lifecycle
    ACCOUNT_SLEEP_DAYS: int = int(os.getenv("ACCOUNT_SLEEP_DAYS", "365"))
    ACCOUNT_DELETE_DAYS: int = int(os.getenv("ACCOUNT_DELETE_DAYS", "730"))

    # Agent Configuration
    ENABLE_MULTI_AGENT: bool = os.getenv("ENABLE_MULTI_AGENT", "true").lower() == "true"
    MAX_AGENT_ITERATIONS: int = int(os.getenv("MAX_AGENT_ITERATIONS", "10"))
    AGENT_VERBOSE: bool = os.getenv("AGENT_VERBOSE", "false").lower() == "true"

    # Redis Configuration (optional)
    REDIS_URL: str = os.getenv("REDIS_URL", "redis://localhost:6379")
    REDIS_TTL: int = int(os.getenv("REDIS_TTL", "3600"))

    @classmethod
    def validate(cls) -> bool:
        """
        Validate configuration.

        Returns:
            True if configuration is valid, False otherwise
        """
        warnings = []

        if cls.ENABLE_AI_ANALYSIS and not cls.ANTHROPIC_API_KEY:
            warnings.append("ANTHROPIC_API_KEY not set. AI analysis will be disabled.")

        if cls.ENABLE_MULTI_AGENT and not cls.ANTHROPIC_API_KEY:
            warnings.append("ANTHROPIC_API_KEY not set. Multi-agent system will be limited.")

        if not cls.ENCRYPTION_KEY:
            warnings.append("ENCRYPTION_KEY not set. Using generated key (not persistent).")

        for warning in warnings:
            print(f"Warning: {warning}")

        return len(warnings) == 0


# Global config instance
config = Config()
