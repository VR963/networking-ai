#!/usr/bin/env python3
"""
Minimal FastAPI demo app to showcase the API documentation.
This version runs without heavy dependencies.
"""
from fastapi import FastAPI
from fastapi.responses import FileResponse, HTMLResponse
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


@app.get("/app", tags=["Web App"], response_class=HTMLResponse)
async def web_app():
    """Serve the embedded web application."""
    return """<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>AI Talent-Hiring Platform</title>
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body {
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            min-height: 100vh;
            color: #333;
        }
        .page { display: none; min-height: 100vh; }
        .page.active { display: block; }
        .hero {
            text-align: center;
            padding: 100px 20px;
            color: white;
        }
        .hero h1 {
            font-size: 3rem;
            margin-bottom: 1rem;
            text-shadow: 2px 2px 4px rgba(0,0,0,0.3);
        }
        .hero p {
            font-size: 1.3rem;
            margin-bottom: 2rem;
            opacity: 0.95;
        }
        .btn {
            padding: 15px 40px;
            border: none;
            border-radius: 30px;
            font-size: 1.1rem;
            font-weight: 600;
            cursor: pointer;
            margin: 10px;
            transition: transform 0.3s;
        }
        .btn:hover { transform: translateY(-3px); }
        .btn-primary {
            background: white;
            color: #667eea;
        }
        .btn-secondary {
            background: rgba(255,255,255,0.2);
            color: white;
            border: 2px solid white;
        }
        .auth-box {
            max-width: 450px;
            margin: 80px auto;
            background: white;
            padding: 40px;
            border-radius: 20px;
            box-shadow: 0 20px 60px rgba(0,0,0,0.3);
        }
        .auth-box h2 {
            color: #667eea;
            margin-bottom: 30px;
            text-align: center;
        }
        .form-group {
            margin-bottom: 20px;
        }
        .form-group input, .form-group select {
            width: 100%;
            padding: 12px;
            border: 2px solid #e0e0e0;
            border-radius: 10px;
            font-size: 1rem;
        }
        .form-group input:focus {
            outline: none;
            border-color: #667eea;
        }
        .btn-block { width: 100%; }
        .container {
            max-width: 1200px;
            margin: 0 auto;
            padding: 40px 20px;
        }
        .dashboard {
            background: white;
            border-radius: 20px;
            padding: 40px;
            margin-top: 20px;
        }
        .dashboard h1 {
            color: #667eea;
            margin-bottom: 30px;
        }
        .cards {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(250px, 1fr));
            gap: 20px;
            margin-bottom: 40px;
        }
        .card {
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            padding: 30px;
            border-radius: 15px;
            text-align: center;
        }
        .card h3 { font-size: 2.5rem; margin-bottom: 10px; }
        .nav {
            background: white;
            padding: 20px;
            box-shadow: 0 2px 10px rgba(0,0,0,0.1);
            margin-bottom: 20px;
            border-radius: 15px;
        }
        .nav button {
            margin-right: 10px;
        }
        .toast {
            position: fixed;
            bottom: 20px;
            right: 20px;
            background: #4ade80;
            color: white;
            padding: 15px 30px;
            border-radius: 10px;
            display: none;
            z-index: 1000;
        }
        .toast.show { display: block; }
    </style>
</head>
<body>
    <!-- Landing Page -->
    <div id="landing" class="page active">
        <div class="hero">
            <h1>🤖 AI Talent-Hiring Platform</h1>
            <p>Agent-to-Agent Conversations for Perfect Matches</p>
            <p style="max-width: 600px; margin: 0 auto 40px;">
                Our AI agents conduct intelligent conversations to find your TOP 3 matches from 100 candidates in ~3 minutes
            </p>
            <button class="btn btn-primary" onclick="showPage('signup')">Get Started</button>
            <button class="btn btn-secondary" onclick="showPage('login')">Sign In</button>
            <div style="display: flex; gap: 30px; justify-content: center; margin-top: 60px; flex-wrap: wrap;">
                <div style="background: rgba(255,255,255,0.1); padding: 30px; border-radius: 15px; min-width: 150px;">
                    <h3 style="font-size: 2.5rem; margin-bottom: 10px;">100→3</h3>
                    <p>Smart Filtering</p>
                </div>
                <div style="background: rgba(255,255,255,0.1); padding: 30px; border-radius: 15px; min-width: 150px;">
                    <h3 style="font-size: 2.5rem; margin-bottom: 10px;">~3min</h3>
                    <p>Process Time</p>
                </div>
                <div style="background: rgba(255,255,255,0.1); padding: 30px; border-radius: 15px; min-width: 150px;">
                    <h3 style="font-size: 2.5rem; margin-bottom: 10px;">85%+</h3>
                    <p>Match Success</p>
                </div>
            </div>
        </div>
    </div>

    <!-- Signup Page -->
    <div id="signup" class="page">
        <div class="auth-box">
            <h2>Create Your Account</h2>
            <form onsubmit="handleSignup(event)">
                <div class="form-group">
                    <select id="userType" required>
                        <option value="talent">Job Seeker (Talent)</option>
                        <option value="company">Employer (Company)</option>
                    </select>
                </div>
                <div class="form-group">
                    <input type="email" id="signupEmail" placeholder="Email" required>
                </div>
                <div class="form-group">
                    <input type="password" id="signupPassword" placeholder="Password (min 8 chars)" required minlength="8">
                </div>
                <div class="form-group">
                    <input type="text" id="signupName" placeholder="Full Name" required>
                </div>
                <button type="submit" class="btn btn-primary btn-block">Create Account</button>
                <p style="text-align: center; margin-top: 20px;">
                    <a href="#" onclick="showPage('login')" style="color: #667eea;">Already have an account? Sign In</a>
                </p>
            </form>
        </div>
    </div>

    <!-- Login Page -->
    <div id="login" class="page">
        <div class="auth-box">
            <h2>Welcome Back</h2>
            <form onsubmit="handleLogin(event)">
                <div class="form-group">
                    <input type="email" id="loginEmail" placeholder="Email" required>
                </div>
                <div class="form-group">
                    <input type="password" id="loginPassword" placeholder="Password" required>
                </div>
                <button type="submit" class="btn btn-primary btn-block">Sign In</button>
                <p style="text-align: center; margin-top: 20px;">
                    <a href="#" onclick="showPage('signup')" style="color: #667eea;">Don't have an account? Sign Up</a>
                </p>
            </form>
        </div>
    </div>

    <!-- Dashboard Page -->
    <div id="dashboard" class="page">
        <div class="container">
            <div class="nav">
                <button class="btn btn-primary" onclick="showPage('dashboard')">Dashboard</button>
                <button class="btn btn-secondary" onclick="showPage('jobs')">Jobs</button>
                <button class="btn btn-secondary" onclick="showPage('matches')">Matches</button>
                <button class="btn btn-secondary" onclick="handleLogout()">Logout</button>
            </div>
            <div class="dashboard">
                <h1>Welcome, <span id="userName">User</span>!</h1>
                <div class="cards">
                    <div class="card">
                        <h3>45%</h3>
                        <p>Agent Readiness</p>
                        <p style="margin-top: 10px; font-size: 0.9rem;">Complete onboarding to reach 80%</p>
                    </div>
                    <div class="card">
                        <h3>3</h3>
                        <p>Active Matches</p>
                        <button class="btn btn-secondary" style="margin-top: 10px;" onclick="showPage('matches')">View</button>
                    </div>
                    <div class="card">
                        <h3>12</h3>
                        <p>Conversations</p>
                    </div>
                </div>
                <h2 style="color: #667eea; margin-bottom: 20px;">Recent Activity</h2>
                <div style="background: #f7f7f7; padding: 20px; border-radius: 10px;">
                    <div style="margin-bottom: 15px; padding: 15px; background: white; border-radius: 8px;">
                        <strong>New match found!</strong> - Software Engineer at TechCorp
                        <div style="color: #666; font-size: 0.9rem; margin-top: 5px;">2 hours ago</div>
                    </div>
                </div>
            </div>
        </div>
    </div>

    <!-- Jobs Page -->
    <div id="jobs" class="page">
        <div class="container">
            <div class="nav">
                <button class="btn btn-secondary" onclick="showPage('dashboard')">Dashboard</button>
                <button class="btn btn-primary" onclick="showPage('jobs')">Jobs</button>
                <button class="btn btn-secondary" onclick="showPage('matches')">Matches</button>
            </div>
            <div class="dashboard">
                <h1>Browse Jobs</h1>
                <div class="cards">
                    <div style="background: white; padding: 25px; border-radius: 15px;">
                        <h3 style="color: #667eea;">Senior Software Engineer</h3>
                        <p><strong>TechCorp</strong></p>
                        <p style="color: #666; margin: 10px 0;">📍 San Francisco • 💰 $150k-$200k</p>
                        <button class="btn btn-primary" onclick="showToast('Application submitted!')">Apply</button>
                    </div>
                    <div style="background: white; padding: 25px; border-radius: 15px;">
                        <h3 style="color: #667eea;">Product Manager</h3>
                        <p><strong>InnovateCo</strong></p>
                        <p style="color: #666; margin: 10px 0;">📍 Remote • 💰 $130k-$180k</p>
                        <button class="btn btn-primary" onclick="showToast('Application submitted!')">Apply</button>
                    </div>
                </div>
            </div>
        </div>
    </div>

    <!-- Matches Page -->
    <div id="matches" class="page">
        <div class="container">
            <div class="nav">
                <button class="btn btn-secondary" onclick="showPage('dashboard')">Dashboard</button>
                <button class="btn btn-secondary" onclick="showPage('jobs')">Jobs</button>
                <button class="btn btn-primary" onclick="showPage('matches')">Matches</button>
            </div>
            <div class="dashboard">
                <h1>Your TOP 3 Matches</h1>
                <div class="cards">
                    <div style="background: white; padding: 30px; border-radius: 15px;">
                        <div style="display: flex; justify-content: space-between; margin-bottom: 15px;">
                            <h3 style="color: #667eea;">Senior Engineer</h3>
                            <div style="background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); color: white; padding: 8px 16px; border-radius: 20px; font-weight: bold;">92.5%</div>
                        </div>
                        <p><strong>TechCorp</strong></p>
                        <p style="color: #666; margin: 15px 0;">Excellent technical and cultural fit</p>
                        <button class="btn btn-primary" onclick="showToast('Interview scheduled!')">Schedule Interview</button>
                    </div>
                </div>
            </div>
        </div>
    </div>

    <div id="toast" class="toast"></div>

    <script>
        let currentUser = null;
        function showPage(pageName) {
            document.querySelectorAll('.page').forEach(p => p.classList.remove('active'));
            document.getElementById(pageName).classList.add('active');
        }
        function handleSignup(e) {
            e.preventDefault();
            currentUser = {
                email: document.getElementById('signupEmail').value,
                name: document.getElementById('signupName').value
            };
            localStorage.setItem('currentUser', JSON.stringify(currentUser));
            showToast('Account created! Please sign in.');
            setTimeout(() => showPage('login'), 1500);
        }
        function handleLogin(e) {
            e.preventDefault();
            currentUser = JSON.parse(localStorage.getItem('currentUser')) || {name: 'User'};
            document.getElementById('userName').textContent = currentUser.name;
            showToast('Login successful!');
            setTimeout(() => showPage('dashboard'), 1000);
        }
        function handleLogout() {
            showToast('Logged out');
            setTimeout(() => showPage('landing'), 1000);
        }
        function showToast(message) {
            const toast = document.getElementById('toast');
            toast.textContent = message;
            toast.classList.add('show');
            setTimeout(() => toast.classList.remove('show'), 3000);
        }
    </script>
</body>
</html>"""


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
