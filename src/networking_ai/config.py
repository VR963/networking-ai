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
    ENABLE_AI_ANALYSIS: bool = os.getenv("ENABLE_AI_ANALYSIS", "true").lower() == "true"
    ENABLE_CACHING: bool = os.getenv("ENABLE_CACHING", "true").lower() == "true"

    # Sentence Transformer Model
    EMBEDDING_MODEL: str = os.getenv("EMBEDDING_MODEL", "all-MiniLM-L6-v2")

    @classmethod
    def validate(cls) -> bool:
        """
        Validate configuration.

        Returns:
            True if configuration is valid, False otherwise
        """
        if cls.ENABLE_AI_ANALYSIS and not cls.ANTHROPIC_API_KEY:
            print("Warning: ANTHROPIC_API_KEY not set. AI analysis will be disabled.")
            return False
        return True


# Global config instance
config = Config()
