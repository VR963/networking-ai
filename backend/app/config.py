import os
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
