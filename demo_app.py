#!/usr/bin/env python3
"""
Minimal FastAPI demo app to showcase the API documentation.
This version runs without heavy dependencies.
"""
from fastapi import FastAPI
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
import os

# Create FastAPI app
app = FastAPI(
    title="Networking AI Platform API",
    description="""
# AI Talent-Hiring Platform - Agent-to-Agent Conversations

## Overview
This is a REST API backend for an AI-powered talent hiring platform that uses autonomous
agent-to-agent conversations to find the best matches.

## Key Features
- **Agent-to-Agent Conversations**: Autonomous AI agents conduct intelligent conversations
- **100 → TOP 3 Matching**: Narrow down 100 candidates to the best 3 matches
- **Anti-Hallucination System**: 4-layer validation to ensure factual responses
- **Real-Time Learning**: Agents get smarter with each conversation
- **Mutual Ranking**: Both talent and company agents must agree on matches

## Architecture
- 8 core services (4,790 lines of production code)
- Agent orchestration with parallel execution
- Master AI monitoring and intervention
- Complete RAG system with ChromaDB

## Quick Start
1. **Register**: POST /api/registration/register
2. **Login**: POST /api/auth/login
3. **Onboarding**: Complete 7-phase interview via /api/onboarding
4. **Matching**: Find matches via /api/matching/find-matches

## Demo Mode
⚠️ This is a demo server running without database and AI dependencies.
The full application includes PostgreSQL, Redis, ChromaDB, and Anthropic Claude AI.

To run the full application with all features, set up the database and install all dependencies.
    """,
    version="0.5.0 (Demo)",
    docs_url="/api/docs",
    redoc_url="/api/redoc",
)

# Mount static files
if os.path.exists("static"):
    app.mount("/static", StaticFiles(directory="static"), name="static")

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/", tags=["Landing Page"])
async def landing_page():
    """Serve the landing page."""
    if os.path.exists("static/index.html"):
        return FileResponse("static/index.html")
    return {
        "message": "Networking AI Platform API",
        "version": "0.5.0 (Demo)",
        "status": "demo_mode",
        "docs": "/api/docs",
        "web_app": "/static/app.html",
        "note": "This is a demo server. Full app requires database setup."
    }


@app.get("/app", tags=["Web App"])
async def web_app():
    """Serve the web application."""
    if os.path.exists("static/app.html"):
        return FileResponse("static/app.html")
    return {"error": "Web app not found"}


@app.get("/api/health", tags=["Health"])
async def health_check():
    """Health check endpoint."""
    return {
        "status": "healthy",
        "mode": "demo",
        "version": "0.5.0",
        "message": "Demo server running without database dependencies",
        "swagger_ui": "/api/docs"
    }


# Demo Authentication endpoints
@app.post("/api/auth/login", tags=["Authentication"])
async def login_demo(email: str, password: str):
    """
    Demo login endpoint.

    In the full application, this validates credentials against the database
    and returns a JWT token for authentication.
    """
    return {
        "message": "Demo mode - Full app requires database",
        "demo_token": "demo_jwt_token_12345",
        "note": "This is a demo response. Real app validates against PostgreSQL."
    }


@app.post("/api/registration/register", tags=["Registration"])
async def register_demo(email: str, password: str, user_type: str):
    """
    Demo registration endpoint.

    In the full application, this creates a new user in the database
    and initiates the onboarding process.
    """
    return {
        "message": "Demo mode - Full app requires database",
        "user_id": "demo_user_123",
        "user_type": user_type,
        "note": "This is a demo response. Real app creates user in PostgreSQL."
    }


@app.get("/api/agents/me", tags=["AI Agents"])
async def get_agent_demo():
    """
    Demo endpoint to get user's AI agent.

    In the full application, this returns the user's personal AI agent
    with readiness score, knowledge base, and conversation history.
    """
    return {
        "message": "Demo mode - Full app requires database and AI",
        "agent": {
            "id": "demo_agent_456",
            "readiness_score": 85.5,
            "status": "active",
            "conversations_completed": 42,
            "knowledge_items": 127
        },
        "note": "Real agent uses Anthropic Claude AI and ChromaDB RAG system."
    }


@app.post("/api/matching/find-matches", tags=["Matching"])
async def find_matches_demo():
    """
    Demo matching endpoint.

    In the full application, this initiates agent-to-agent conversations
    to narrow down 100 candidates to the TOP 3 best matches.
    """
    return {
        "message": "Demo mode - Full app requires AI and database",
        "matches": [
            {
                "candidate_id": "demo_candidate_1",
                "match_score": 92.5,
                "compatibility_rank": 1,
                "conversation_summary": "Excellent technical fit and cultural alignment"
            },
            {
                "candidate_id": "demo_candidate_2",
                "match_score": 88.3,
                "compatibility_rank": 2,
                "conversation_summary": "Strong skills match with growth potential"
            },
            {
                "candidate_id": "demo_candidate_3",
                "match_score": 85.7,
                "compatibility_rank": 3,
                "conversation_summary": "Good experience alignment and motivation fit"
            }
        ],
        "note": "Real system conducts 100 AI agent conversations in ~3 minutes."
    }


@app.get("/api/conversations", tags=["Conversations"])
async def list_conversations_demo():
    """
    Demo conversations endpoint.

    In the full application, this returns all agent-to-agent conversations
    for the authenticated user.
    """
    return {
        "message": "Demo mode",
        "conversations": [
            {
                "id": "conv_123",
                "partner": "Talent Agent #456",
                "messages": 8,
                "status": "completed",
                "final_score": 92.5
            }
        ],
        "note": "Real app stores conversations in PostgreSQL with full message history."
    }


if __name__ == "__main__":
    import uvicorn
    print("""
╔════════════════════════════════════════════════════════════════╗
║                                                                ║
║    🤖 AI Talent-Hiring Platform - DEMO MODE                   ║
║                                                                ║
║    🌐 Landing Page:  http://localhost:8000                    ║
║    📚 Swagger UI:    http://localhost:8000/api/docs           ║
║    💚 Health Check:  http://localhost:8000/api/health         ║
║                                                                ║
║    ℹ️  This is a demo server without database/AI dependencies ║
║    ✅ Explore the API structure and documentation             ║
║    🔧 Full app requires PostgreSQL, Redis, ChromaDB setup     ║
║                                                                ║
╚════════════════════════════════════════════════════════════════╝
    """)
    uvicorn.run(app, host="0.0.0.0", port=8000)
