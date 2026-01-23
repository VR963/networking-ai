"""CV 2.0 Platform - Main Application Entry Point.

Architecture:
- FastAPI async web framework
- Supabase (PostgreSQL) via singleton connection pool
- Anthropic Claude for AI operations
- Background task queue for expensive AI calls
- LRU cache for hot data
- Rate limiting + security middleware stack

Middleware order (outermost first):
1. RequestLogging - timing and audit trail
2. Security - headers, body size, API key validation
3. RateLimit - per-IP sliding window
4. CORS - cross-origin access control
"""

import os
import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware

from app.config import ALLOWED_ORIGINS, APP_ENV, WORKERS
from app.database import get_db, get_pool_stats
from app.middleware import (
    RateLimitMiddleware,
    SecurityMiddleware,
    RequestLoggingMiddleware,
)
from app.tasks import task_queue

from app.api.a2a_routes import router as a2a_router
from app.api.profile_chat import router as profile_chat_router
from app.api.calibration import router as calibration_router
from app.api.user_routes import router as user_router
from app.api.job_routes import router as job_router
from app.api.onboarding import router as onboarding_router
from app.api.network_routes import router as network_router
from app.routes.master_ai_routes import router as master_ai_router


# --- Logging Configuration ---
logging.basicConfig(
    level=logging.INFO if APP_ENV == "production" else logging.DEBUG,
    format="%(asctime)s [%(name)s] %(levelname)s: %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger("cv2.main")


# --- Application Lifecycle ---

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup and shutdown hooks."""
    # Startup
    logger.info("CV 2.0 Platform starting (env=%s, workers=%d)", APP_ENV, WORKERS)

    # Validate database connection
    db = get_db()
    if db:
        logger.info("Database connection established")
    else:
        logger.warning("Database not configured - running in limited mode")

    yield

    # Shutdown
    logger.info("CV 2.0 Platform shutting down")
    # Flush any pending cost records
    try:
        from app.services.cost_tracker import cost_tracker
        cost_tracker.flush()
    except Exception:
        pass


# --- App Initialization ---

app = FastAPI(
    title="CV 2.0 Platform",
    version="2.0.0",
    lifespan=lifespan,
    docs_url="/docs" if APP_ENV != "production" else None,
    redoc_url="/redoc" if APP_ENV != "production" else None,
)


# --- Middleware Stack (applied in reverse order) ---

# 1. CORS (innermost - applied last)
app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS if APP_ENV == "production" else ["*"],
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
    allow_headers=["*"],
)

# 2. Rate limiting
app.add_middleware(RateLimitMiddleware)

# 3. Security headers and API key validation
app.add_middleware(SecurityMiddleware)

# 4. Request logging (outermost - applied first)
app.add_middleware(RequestLoggingMiddleware)


# --- Exception Handlers ---

@app.exception_handler(RuntimeError)
async def runtime_error_handler(request: Request, exc: RuntimeError):
    logger.error("RuntimeError on %s: %s", request.url.path, str(exc)[:200])
    return JSONResponse(status_code=503, content={"detail": "Service temporarily unavailable."})


@app.exception_handler(Exception)
async def general_exception_handler(request: Request, exc: Exception):
    error_type = type(exc).__name__
    logger.error("Unhandled %s on %s: %s", error_type, request.url.path, str(exc)[:200])

    if "supabase" in error_type.lower() or "supabase" in str(exc).lower():
        return JSONResponse(
            status_code=503,
            content={"detail": "Database service unavailable."},
        )
    if "api_key" in str(exc).lower() or "auth" in str(exc).lower():
        return JSONResponse(
            status_code=503,
            content={"detail": "AI service not configured."},
        )
    # Don't leak implementation details in production
    detail = f"Internal error: {error_type}" if APP_ENV != "production" else "Internal server error."
    return JSONResponse(status_code=500, content={"detail": detail})


# --- API Routes ---

app.include_router(a2a_router, prefix="/a2a", tags=["A2A Matching"])
app.include_router(profile_chat_router, prefix="/chat", tags=["Profile Chat"])
app.include_router(calibration_router, prefix="/calibration", tags=["Calibration"])
app.include_router(user_router, prefix="/user", tags=["User Management"])
app.include_router(job_router, prefix="/jobs", tags=["Job Management"])
app.include_router(onboarding_router, prefix="/onboarding", tags=["Onboarding"])
app.include_router(network_router, prefix="/network", tags=["AI Network"])
app.include_router(master_ai_router, prefix="/master-ai", tags=["Master AI"])


# --- System Endpoints ---

@app.get("/health")
async def health_check():
    """Comprehensive health check including dependencies."""
    pool_stats = get_pool_stats()
    tasks = task_queue.get_queue_stats()

    status = "healthy"
    if not pool_stats["db_available"]:
        status = "degraded"

    return {
        "status": status,
        "version": "2.0.0",
        "environment": APP_ENV,
        "database": pool_stats,
        "tasks": tasks,
    }


@app.get("/health/ready")
async def readiness_check():
    """Readiness probe - is the app ready to serve traffic?"""
    db = get_db()
    if not db:
        return JSONResponse(
            status_code=503,
            content={"ready": False, "reason": "Database not available"},
        )
    return {"ready": True}


@app.get("/system/tasks")
async def get_task_status():
    """Get background task queue status."""
    return {
        "queue": task_queue.get_queue_stats(),
        "active": task_queue.get_active_tasks(),
    }


@app.get("/system/cache")
async def get_cache_stats():
    """Get cache performance statistics."""
    return get_pool_stats()


# --- Static Files (must be last) ---

frontend_path = os.path.join(os.path.dirname(__file__), "..", "..", "frontend")
if os.path.exists(frontend_path):
    app.mount("/", StaticFiles(directory=frontend_path, html=True), name="frontend")


# --- Entry Point ---

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=8000,
        workers=WORKERS,
        log_level="info",
        access_log=True,
    )
