import os
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware

from app.api.a2a_routes import router as a2a_router
from app.api.profile_chat import router as profile_chat_router
from app.api.calibration import router as calibration_router
from app.api.user_routes import router as user_router
from app.api.job_routes import router as job_router
from app.api.onboarding import router as onboarding_router
from app.routes.master_ai_routes import router as master_ai_router

app = FastAPI(title="CV 2.0 Platform", version="2.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.exception_handler(RuntimeError)
async def runtime_error_handler(request: Request, exc: RuntimeError):
    return JSONResponse(status_code=503, content={"detail": str(exc)})


@app.exception_handler(Exception)
async def general_exception_handler(request: Request, exc: Exception):
    error_type = type(exc).__name__
    if "supabase" in error_type.lower() or "supabase_url" in str(exc).lower():
        return JSONResponse(
            status_code=503,
            content={"detail": "Database not configured. Set SUPABASE_URL and SUPABASE_SERVICE_KEY."},
        )
    if "api_key" in str(exc).lower() or "auth_token" in str(exc).lower():
        return JSONResponse(
            status_code=503,
            content={"detail": "API credentials not configured. Set ANTHROPIC_API_KEY."},
        )
    return JSONResponse(status_code=500, content={"detail": f"Internal error: {error_type}"})


# API routes
app.include_router(a2a_router, prefix="/a2a", tags=["A2A Matching"])
app.include_router(profile_chat_router, prefix="/chat", tags=["Profile Chat"])
app.include_router(calibration_router, prefix="/calibration", tags=["Calibration"])
app.include_router(user_router, prefix="/user", tags=["User Management"])
app.include_router(job_router, prefix="/jobs", tags=["Job Management"])
app.include_router(onboarding_router, prefix="/onboarding", tags=["Onboarding"])
app.include_router(master_ai_router, prefix="/master-ai", tags=["Master AI"])


@app.get("/health")
async def health_check():
    return {"status": "healthy", "version": "2.0.0"}


# Serve frontend static files (must be after API routes)
frontend_path = os.path.join(os.path.dirname(__file__), "..", "..", "frontend")
if os.path.exists(frontend_path):
    app.mount("/", StaticFiles(directory=frontend_path, html=True), name="frontend")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
