"""
Main FastAPI Application.

This is the entry point for the REST API.
Provides access to all platform features via HTTP endpoints.
"""

from fastapi import FastAPI, Request, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
import time

from ..database import engine, Base
from .auth import router as auth_router
from .registration import router as registration_router
from .users import router as users_router
from .jobs import router as jobs_router
from .matches import router as matches_router  # Phase 1 (legacy)
from .matching import router as matching_router  # Phase 2 (new)
from .messages import router as messages_router
from .onboarding import router as onboarding_router
from .agents import router as agents_router
from .companies import router as companies_router
from .hiring_manager_onboarding import router as hm_onboarding_router
from .job_postings import router as job_postings_router
from .mobile import mobile_router
from .memory import router as memory_router
from .marketplace import router as marketplace_router
from ..services.background_tasks import task_manager


# Create FastAPI app
app = FastAPI(
    title="Networking AI Platform API",
    description="AI-native professional networking platform with intelligent matching",
    version="0.5.0",
    docs_url="/api/docs",  # Swagger UI
    redoc_url="/api/redoc",  # ReDoc
)


# CORS Configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",  # React development
        "http://localhost:3001",
        "http://localhost:8080",
        # Add production domains here
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Request timing middleware
@app.middleware("http")
async def add_process_time_header(request: Request, call_next):
    """Add X-Process-Time header to all responses."""
    start_time = time.time()
    response = await call_next(request)
    process_time = time.time() - start_time
    response.headers["X-Process-Time"] = str(process_time)
    return response


# Exception handlers
@app.exception_handler(404)
async def not_found_handler(request: Request, exc):
    """Handle 404 errors."""
    return JSONResponse(
        status_code=404,
        content={"detail": "Resource not found"},
    )


@app.exception_handler(500)
async def internal_error_handler(request: Request, exc):
    """Handle 500 errors."""
    return JSONResponse(
        status_code=500,
        content={"detail": "Internal server error"},
    )


# Startup event
@app.on_event("startup")
async def startup_event():
    """Initialize database and background services on startup."""
    # Create tables (in production, use Alembic migrations instead)
    Base.metadata.create_all(bind=engine)
    print("[API] Database tables created")

    # Start background task manager
    task_manager.start()
    print("[API] Background task manager started")

    print("[API] FastAPI application started")


# Shutdown event
@app.on_event("shutdown")
async def shutdown_event():
    """Cleanup on shutdown."""
    # Stop background task manager
    task_manager.stop()
    print("[API] Background task manager stopped")
    print("[API] FastAPI application shutting down")


# Health check endpoint
@app.get("/", tags=["Health"])
async def root():
    """Root endpoint / health check."""
    return {
        "message": "Networking AI Platform API",
        "version": "0.5.0",
        "status": "healthy",
        "docs": "/api/docs",
    }


@app.get("/api/health", tags=["Health"])
async def health_check():
    """Detailed health check."""
    return {
        "status": "healthy",
        "timestamp": time.time(),
        "database": "connected",
        "ai_system": "ready",
        "background_tasks": "running" if task_manager.running else "stopped",
    }


@app.get("/api/tasks/{task_id}", tags=["Background Tasks"])
async def get_task_status(task_id: str):
    """Get status of a background task."""
    task_status = task_manager.get_task_status(task_id)

    if not task_status:
        raise HTTPException(
            status_code=404,
            detail=f"Task {task_id} not found"
        )

    return task_status


@app.get("/api/tasks", tags=["Background Tasks"])
async def list_all_tasks():
    """List all background tasks (admin endpoint)."""
    return task_manager.get_all_tasks()


# Include routers
app.include_router(auth_router, prefix="/api/auth", tags=["Authentication"])
app.include_router(registration_router, prefix="/api/registration", tags=["Registration & User Types"])
app.include_router(onboarding_router, prefix="/api/onboarding", tags=["Onboarding & Interview"])
app.include_router(hm_onboarding_router, prefix="/api/hiring-manager", tags=["Hiring Manager Onboarding"])
app.include_router(agents_router, prefix="/api/agents", tags=["Personal AI Agents"])
app.include_router(companies_router, prefix="/api/companies", tags=["Companies & Subscriptions"])
app.include_router(job_postings_router, prefix="/api/job-postings", tags=["Job Postings (Company AI Agents)"])
app.include_router(matching_router, prefix="/api/matching", tags=["AI Matching (Phase 2)"])
app.include_router(users_router, prefix="/api/users", tags=["Users & Profiles"])
app.include_router(jobs_router, prefix="/api/jobs", tags=["Jobs & Applications (Legacy)"])
app.include_router(matches_router, prefix="/api/matches", tags=["AI Matches (Legacy)"])
app.include_router(messages_router, prefix="/api/conversations", tags=["Messaging"])
app.include_router(mobile_router, prefix="/api/v1", tags=["Mobile API (Phase 10)"])
app.include_router(memory_router, tags=["Enhanced Memory System (Phase 10A)"])
app.include_router(marketplace_router, prefix="/api/v1/marketplace", tags=["AI Agent Marketplace (Phase 12)"])


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "networking_ai.api.main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,  # Development only
    )
