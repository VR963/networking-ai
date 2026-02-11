# CV2.0 — AI-Native Professional Networking Platform

## Project Overview

CV2.0 is an AI-native recruitment platform where both candidates (talent) and hiring managers
get personalized AI agents that negotiate matches on their behalf. The platform uses deep
6-category behavioral interviews, multi-round AI-to-AI negotiations, hallucination guards,
and collective network learning.

## Tech Stack

| Layer | Technology |
|-------|------------|
| Backend | Python 3.10+, FastAPI, Uvicorn |
| Database | Supabase (PostgreSQL + pgvector + RLS) |
| AI | Anthropic Claude API (Sonnet 4 primary) |
| Frontend | Vanilla JS, Tailwind CSS (CDN), Supabase Auth |
| Testing | pytest, pytest-asyncio |
| PWA | Service worker, manifest.json, offline support |

## Directory Structure

```
networking-ai/
├── backend/
│   ├── app/
│   │   ├── main.py              # FastAPI entry point
│   │   ├── config.py            # Environment configuration
│   │   ├── database.py          # Supabase connection pool + LRU cache
│   │   ├── auth.py              # JWT + Supabase auth (get_current_user, require_admin)
│   │   ├── middleware.py        # Rate limiting, security headers, logging
│   │   ├── tasks.py             # Background task queue (async, semaphore-based)
│   │   ├── schema.sql           # Full database schema (21 tables)
│   │   ├── api/                 # Route handlers
│   │   │   ├── profile_chat.py  # Talent chat (6-category onboarding)
│   │   │   ├── hm_chat.py       # Hiring manager chat
│   │   │   ├── onboarding.py    # Structured interview flow
│   │   │   ├── user_routes.py   # Profile + document management
│   │   │   ├── job_routes.py    # Job creation/listing
│   │   │   ├── network_routes.py # Marketplace operations
│   │   │   ├── a2a_routes.py    # Agent-to-agent matching
│   │   │   └── calibration.py   # Profile verification
│   │   ├── routes/
│   │   │   └── master_ai_routes.py  # Admin governance dashboard
│   │   └── services/            # Business logic (20+ modules)
│   │       ├── ai_profile_service.py
│   │       ├── profile_analyzer.py
│   │       ├── interview_service.py
│   │       ├── auto_activation.py
│   │       ├── a2a_engine.py
│   │       ├── negotiation_protocol.py
│   │       ├── network_discovery.py
│   │       ├── hallucination_guard.py
│   │       ├── agent_memory.py
│   │       ├── dspy_learning.py
│   │       ├── collective_intelligence.py
│   │       ├── quality_analyzer.py
│   │       ├── embedding_store.py
│   │       ├── master_ai_control_center.py
│   │       ├── master_ai_governance.py
│   │       ├── ai_council.py
│   │       ├── agent_training_center.py
│   │       ├── cost_tracker.py
│   │       ├── market_intelligence.py
│   │       ├── marketing_ai_agent.py
│   │       ├── campaign_manager.py
│   │       └── ... (more)
│   ├── tests/
│   │   ├── conftest.py          # Mock Supabase + Anthropic fixtures
│   │   └── test_*.py            # Unit tests
│   └── requirements.txt
├── frontend/
│   ├── index.html               # Landing page
│   ├── auth.html                # Login/signup
│   ├── talent-app.html          # Candidate SPA (chat, profile, matches)
│   ├── hm-app.html              # Hiring manager SPA
│   ├── talent-onboarding.html   # Talent structured interview
│   ├── hm-onboarding.html       # HM structured interview
│   ├── calibration.html         # Profile verification
│   ├── master-control-center.html  # Admin dashboard
│   ├── js/app.js                # Auth + API helpers
│   ├── js/config.js             # Supabase credentials
│   ├── css/design.css           # Swiss/Revolut design system
│   ├── manifest.json            # PWA manifest
│   └── sw.js                    # Service worker
└── ROADMAP.md                   # Development roadmap
```

## Key Concepts

- **6-Category Methodology**: Career Motivations, Achievements, Work Style, Leadership, Next Role, Values & Culture
- **3-Round Negotiation**: Surface match → Values alignment → Deep fit (with early exit to save tokens)
- **Hallucination Guard**: Zero-tolerance integrity system embedded at profile generation, verification, and negotiation
- **Collective Intelligence**: Agents learn from each other within the same industry
- **Auto-Activation**: Readiness score = (document_quality × 0.7) + (interview_quality × 0.3), threshold 60/100
- **Consensus Model**: Both agents must independently agree before presenting a match to users

## Running Locally

```bash
# Backend
cd backend
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000

# Required environment variables
export ANTHROPIC_API_KEY=...
export SUPABASE_URL=...
export SUPABASE_SERVICE_KEY=...

# Tests
cd backend && pytest
```

## Development Guidelines

- All services use `async/await`
- Supabase client is a singleton (see `database.py`)
- Use `cost_tracker.record_api_call()` after every Claude API call
- Run hallucination guard on all AI-generated profiles and negotiation outputs
- Mark all Claude calls with the appropriate operation category for cost attribution
- Prefer graceful degradation (demo data fallback) over hard failures
