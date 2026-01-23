import os
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware

from app.api.a2a_routes import router as a2a_router
from app.api.profile_chat import router as profile_chat_router
from app.api.calibration import router as calibration_router
from app.routes.master_ai_routes import router as master_ai_router

app = FastAPI(title="CV 2.0 Platform", version="2.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# API routes
app.include_router(a2a_router, prefix="/a2a", tags=["A2A Matching"])
app.include_router(profile_chat_router, prefix="/chat", tags=["Profile Chat"])
app.include_router(calibration_router, prefix="/calibration", tags=["Calibration"])
app.include_router(master_ai_router, prefix="/master-ai", tags=["Master AI"])

# Serve frontend static files
frontend_path = os.path.join(os.path.dirname(__file__), "..", "..", "frontend")
if os.path.exists(frontend_path):
    app.mount("/", StaticFiles(directory=frontend_path, html=True), name="frontend")


@app.get("/health")
async def health_check():
    return {"status": "healthy", "version": "2.0.0"}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
