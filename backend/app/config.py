import os
import logging
from pathlib import Path

# Load .env file if python-dotenv is available
try:
    from dotenv import load_dotenv
    env_path = Path(__file__).resolve().parent.parent / ".env"
    load_dotenv(env_path)
except ImportError:
    pass


# --- Core Credentials ---
SUPABASE_URL = os.environ.get("SUPABASE_URL", "")
SUPABASE_SERVICE_KEY = os.environ.get("SUPABASE_SERVICE_KEY", "") or os.environ.get("SUPABASE_KEY", "")
ANTHROPIC_API_KEY = os.environ.get("ANTHROPIC_API_KEY", "")

# --- Application Settings ---
QUALITY_THRESHOLD = 7.0
MAX_NEGOTIATION_TOKENS = 4000
APP_ENV = os.environ.get("APP_ENV", "development")  # development, staging, production

# --- Rate Limiting ---
RATE_LIMIT_PER_MINUTE = int(os.environ.get("RATE_LIMIT_PER_MINUTE", "60"))
RATE_LIMIT_AI_PER_MINUTE = int(os.environ.get("RATE_LIMIT_AI_PER_MINUTE", "20"))

# --- Cache Settings ---
CACHE_TTL_SECONDS = int(os.environ.get("CACHE_TTL_SECONDS", "300"))  # 5 min default
CACHE_MAX_SIZE = int(os.environ.get("CACHE_MAX_SIZE", "1000"))

# --- API Security ---
API_KEY_HEADER = "X-API-Key"
MASTER_API_KEY = os.environ.get("MASTER_API_KEY", "")  # For admin endpoints
ALLOWED_ORIGINS = os.environ.get(
    "ALLOWED_ORIGINS", "http://localhost:8000,http://localhost:3000"
).split(",")

# --- Worker Configuration ---
WORKERS = int(os.environ.get("WORKERS", "4"))
MAX_CONCURRENT_AI_CALLS = int(os.environ.get("MAX_CONCURRENT_AI_CALLS", "10"))

# --- Embedding / RAG Settings ---
EMBEDDING_DIMENSION = 1024  # Voyage AI / compatible dimension
SIMILARITY_THRESHOLD = 0.75

logger = logging.getLogger("cv2.config")


def validate_config() -> dict:
    """Validate configuration on startup. Returns a status dict.

    Raises on fatal misconfigurations in production.
    Logs warnings for degraded capabilities in development.
    """
    issues: list[str] = []
    warnings: list[str] = []

    if not ANTHROPIC_API_KEY:
        issues.append("ANTHROPIC_API_KEY not set — AI features disabled")

    if not SUPABASE_URL:
        warnings.append("SUPABASE_URL not set — running in demo/limited mode")
    elif not SUPABASE_URL.startswith("http"):
        issues.append(f"SUPABASE_URL looks invalid: {SUPABASE_URL[:30]}...")

    if not SUPABASE_SERVICE_KEY:
        warnings.append("SUPABASE_SERVICE_KEY not set — database unavailable")

    if not MASTER_API_KEY:
        warnings.append("MASTER_API_KEY not set — admin endpoints unprotected")

    if APP_ENV not in ("development", "staging", "production"):
        warnings.append(f"APP_ENV='{APP_ENV}' — expected development|staging|production")

    for w in warnings:
        logger.warning("CONFIG: %s", w)
    for i in issues:
        logger.error("CONFIG: %s", i)

    if APP_ENV == "production" and not ANTHROPIC_API_KEY:
        raise RuntimeError("ANTHROPIC_API_KEY is required in production")

    return {
        "valid": len(issues) == 0,
        "issues": issues,
        "warnings": warnings,
        "capabilities": {
            "ai": bool(ANTHROPIC_API_KEY),
            "database": bool(SUPABASE_URL and SUPABASE_SERVICE_KEY),
            "admin": bool(MASTER_API_KEY),
        },
    }
