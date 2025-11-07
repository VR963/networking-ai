"""
Main FastAPI Application.

This is the entry point for the REST API.
Provides access to all platform features via HTTP endpoints.
"""

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
import time

from ..database import engine, Base
from .auth import router as auth_router
# Import other routers as they're created
# from .users import router as users_router
# from .jobs import router as jobs_router
# from .matches import router as matches_router


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
    """Initialize database on startup."""
    # Create tables (in production, use Alembic migrations instead)
    Base.metadata.create_all(bind=engine)
    print("[API] Database tables created")
    print("[API] FastAPI application started")


# Shutdown event
@app.on_event("shutdown")
async def shutdown_event():
    """Cleanup on shutdown."""
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
    }


# Include routers
app.include_router(auth_router, prefix="/api/auth", tags=["Authentication"])
# app.include_router(users_router, prefix="/api/users", tags=["Users"])
# app.include_router(jobs_router, prefix="/api/jobs", tags=["Jobs"])
# app.include_router(matches_router, prefix="/api/matches", tags=["Matches"])


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "networking_ai.api.main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,  # Development only
    )
