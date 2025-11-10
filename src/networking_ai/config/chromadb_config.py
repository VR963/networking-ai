"""
ChromaDB Production Configuration.

Handles ChromaDB setup for different environments:
- Development: Local persistence
- Staging: Cloud deployment with authentication
- Production: Optimized cloud deployment with monitoring
"""

import os
from enum import Enum
from typing import Optional, Dict
from dataclasses import dataclass


class Environment(str, Enum):
    """Deployment environment."""
    DEVELOPMENT = "development"
    STAGING = "staging"
    PRODUCTION = "production"


@dataclass
class ChromaDBConfig:
    """ChromaDB configuration."""

    # Environment
    environment: Environment

    # Persistence
    persist_directory: str

    # Cloud settings (for staging/production)
    cloud_host: Optional[str] = None
    cloud_port: Optional[int] = None
    cloud_api_key: Optional[str] = None

    # Performance settings
    batch_size: int = 100
    max_batch_size: int = 1000

    # Collection settings
    collection_metadata: Dict = None
    embedding_function: str = "default"  # "default", "openai", "cohere"

    # Caching
    enable_cache: bool = True
    cache_ttl_seconds: int = 3600  # 1 hour

    # Monitoring
    enable_telemetry: bool = False
    log_queries: bool = True

    # Security
    require_auth: bool = False
    allowed_origins: list = None


def get_chromadb_config(environment: Optional[str] = None) -> ChromaDBConfig:
    """
    Get ChromaDB configuration for the current environment.

    Args:
        environment: Override environment (development, staging, production)

    Returns:
        ChromaDBConfig instance
    """
    env = environment or os.getenv("ENVIRONMENT", "development")
    env = Environment(env.lower())

    if env == Environment.DEVELOPMENT:
        return ChromaDBConfig(
            environment=env,
            persist_directory=os.getenv("CHROMA_PERSIST_DIR", "./chroma_data"),
            batch_size=50,
            enable_cache=True,
            cache_ttl_seconds=1800,  # 30 minutes
            enable_telemetry=False,
            log_queries=True,
            require_auth=False
        )

    elif env == Environment.STAGING:
        return ChromaDBConfig(
            environment=env,
            persist_directory=os.getenv("CHROMA_PERSIST_DIR", "/data/chroma_staging"),
            cloud_host=os.getenv("CHROMA_CLOUD_HOST"),
            cloud_port=int(os.getenv("CHROMA_CLOUD_PORT", "8000")),
            cloud_api_key=os.getenv("CHROMA_API_KEY"),
            batch_size=100,
            max_batch_size=1000,
            enable_cache=True,
            cache_ttl_seconds=3600,  # 1 hour
            enable_telemetry=True,
            log_queries=True,
            require_auth=True,
            allowed_origins=["https://staging.networking-ai.com"]
        )

    else:  # Production
        return ChromaDBConfig(
            environment=env,
            persist_directory=os.getenv("CHROMA_PERSIST_DIR", "/data/chroma_production"),
            cloud_host=os.getenv("CHROMA_CLOUD_HOST"),
            cloud_port=int(os.getenv("CHROMA_CLOUD_PORT", "8000")),
            cloud_api_key=os.getenv("CHROMA_API_KEY"),
            batch_size=100,
            max_batch_size=1000,
            enable_cache=True,
            cache_ttl_seconds=7200,  # 2 hours
            enable_telemetry=True,
            log_queries=True,
            require_auth=True,
            allowed_origins=["https://networking-ai.com", "https://app.networking-ai.com"]
        )


def get_collection_config(collection_type: str) -> Dict:
    """
    Get collection-specific configuration.

    Args:
        collection_type: Type of collection (talent_rag, hm_rag, job_rag, company_rag)

    Returns:
        Collection metadata configuration
    """
    base_config = {
        "hnsw:space": "cosine",  # Cosine similarity for embeddings
        "hnsw:construction_ef": 200,  # Construction time parameter
        "hnsw:search_ef": 100,  # Search time parameter
        "hnsw:M": 16  # Number of bi-directional links
    }

    if collection_type == "talent_rag":
        return {
            **base_config,
            "description": "Talent Personal Agent RAG - Skills, preferences, career goals",
            "portable": True,
            "owner_type": "talent_user",
            "retention_policy": "delete_with_user"
        }

    elif collection_type == "hm_rag":
        return {
            **base_config,
            "description": "HM Personal Agent RAG - Hiring preferences and style",
            "portable": True,
            "owner_type": "hm_user",
            "retention_policy": "delete_with_user"
        }

    elif collection_type == "job_rag":
        return {
            **base_config,
            "description": "Job RAG - Requirements with dual access (HM + Company)",
            "portable": False,
            "owner_type": "company",
            "retention_policy": "delete_with_job",
            "dual_access": True
        }

    elif collection_type == "company_admin_rag":
        return {
            **base_config,
            "description": "Company Admin Agent RAG - Culture, values, knowledge base",
            "portable": False,
            "owner_type": "company",
            "retention_policy": "persist_with_company"
        }

    else:
        return base_config


# Environment detection
def is_production() -> bool:
    """Check if running in production."""
    return os.getenv("ENVIRONMENT", "development").lower() == "production"


def is_staging() -> bool:
    """Check if running in staging."""
    return os.getenv("ENVIRONMENT", "development").lower() == "staging"


def is_development() -> bool:
    """Check if running in development."""
    return os.getenv("ENVIRONMENT", "development").lower() == "development"


# ChromaDB health check
def check_chromadb_health(config: ChromaDBConfig) -> Dict:
    """
    Check ChromaDB health and connectivity.

    Args:
        config: ChromaDB configuration

    Returns:
        Health status dict
    """
    try:
        import chromadb

        if config.cloud_host:
            # Cloud deployment - check connectivity
            client = chromadb.HttpClient(
                host=config.cloud_host,
                port=config.cloud_port,
                headers={"Authorization": f"Bearer {config.cloud_api_key}"} if config.cloud_api_key else {}
            )
        else:
            # Local deployment
            client = chromadb.PersistentClient(path=config.persist_directory)

        # Try to list collections
        collections = client.list_collections()

        return {
            "status": "healthy",
            "environment": config.environment.value,
            "collections_count": len(collections),
            "persist_directory": config.persist_directory,
            "cloud_enabled": config.cloud_host is not None
        }

    except ImportError:
        return {
            "status": "unavailable",
            "error": "ChromaDB not installed",
            "environment": config.environment.value
        }

    except Exception as e:
        return {
            "status": "unhealthy",
            "error": str(e),
            "environment": config.environment.value
        }
