# CLAUDE.md

This file provides guidance for AI assistants working with the CV2.0 codebase.

## Project Overview

**CV 2.0** is an AI-native professional networking platform that connects talent with hiring managers through autonomous AI agents, semantic matching, and intelligent discovery.

- **Version**: 2.0.0
- **License**: MIT
- **Stack**: Python (FastAPI) + Vanilla JavaScript + Supabase (PostgreSQL)
- **AI Provider**: Anthropic Claude

## Repository Structure

```
CV2.0/
├── backend/
│   ├── app/
│   │   ├── api/              # API route handlers
│   │   │   ├── a2a_routes.py       # Agent-to-Agent matching
│   │   │   ├── calibration.py      # User calibration flows
│   │   │   ├── job_routes.py       # Job management
│   │   │   ├── network_routes.py   # AI network endpoints
│   │   │   ├── onboarding.py       # User onboarding
│   │   │   ├── profile_chat.py     # Profile conversation
│   │   │   └── user_routes.py      # User management
│   │   ├── routes/
│   │   │   └── master_ai_routes.py # Master AI control center
│   │   ├── services/         # Business logic & AI agents
│   │   │   ├── a2a_engine.py           # Agent-to-Agent matching engine
│   │   │   ├── agent_memory.py         # Agent memory persistence
│   │   │   ├── agent_training_center.py # Agent training system
│   │   │   ├── ai_analytics.py         # Analytics & metrics
│   │   │   ├── ai_council.py           # Multi-agent governance
│   │   │   ├── ai_profile_service.py   # Profile AI operations
│   │   │   ├── auto_activation.py      # Agent activation system
│   │   │   ├── campaign_manager.py     # Marketing campaigns
│   │   │   ├── cost_tracker.py         # AI cost monitoring
│   │   │   ├── dspy_learning.py        # DSPy prompt optimization
│   │   │   ├── embedding_store.py      # Vector embeddings (RAG)
│   │   │   ├── hallucination_guard.py  # AI safety guardrails
│   │   │   ├── interview_service.py    # Interview orchestration
│   │   │   ├── market_intelligence.py  # Market insights
│   │   │   ├── marketing_ai_agent.py   # Marketing AI department
│   │   │   ├── master_ai_control_center.py # Central AI control
│   │   │   ├── master_ai_governance.py # AI governance policies
│   │   │   ├── negotiation_protocol.py # Agent negotiation
│   │   │   ├── network_discovery.py    # Network graph discovery
│   │   │   ├── network_events.py       # Event handling
│   │   │   ├── network_learning.py     # Collective learning
│   │   │   └── profile_analyzer.py     # Profile analysis
│   │   ├── auth.py           # Authentication (Supabase)
│   │   ├── config.py         # App configuration
│   │   ├── database.py       # Database connection pool
│   │   ├── main.py           # FastAPI application entry
│   │   ├── middleware.py     # Rate limiting, security, logging
│   │   ├── schema.sql        # PostgreSQL schema (with RLS)
│   │   └── tasks.py          # Background task queue
│   ├── tests/                # Pytest test suite
│   ├── requirements.txt      # Python dependencies
│   └── pytest.ini            # Pytest configuration
├── frontend/
│   ├── js/
│   │   └── app.js            # Shared app module (auth, API, nav)
│   ├── css/
│   │   └── styles.css        # Global styles
│   ├── icons/                # PWA icons
│   ├── index.html            # Landing page
│   ├── auth.html             # Authentication page
│   ├── dashboard.html        # User dashboard
│   ├── talent-app.html       # Talent application
│   ├── talent-onboarding.html # Talent onboarding flow
│   ├── hm-onboarding.html    # Hiring manager onboarding
│   ├── job-command-center.html # Job matching interface
│   ├── calibration.html      # User calibration
│   ├── chat.html             # AI chat interface
│   ├── network-dashboard.html # AI network visualization
│   ├── master-ai-dashboard.html # Master AI dashboard
│   ├── master-control-center.html # Full control center
│   ├── manifest.json         # PWA manifest
│   └── sw.js                 # Service worker (offline + push)
├── .gitignore
├── LICENSE
├── README.md
└── CLAUDE.md
```

## Architecture

### Backend (FastAPI)

**Entry Point**: `backend/app/main.py`

**Middleware Stack** (applied outermost to innermost):
1. `RequestLoggingMiddleware` - Timing and audit trail
2. `SecurityMiddleware` - Headers, body size, API key validation
3. `RateLimitMiddleware` - Per-IP sliding window rate limiting
4. `CORSMiddleware` - Cross-origin access control

**Key Services**:
- **Master AI Control Center** - Central orchestration for all AI agents
- **A2A Engine** - Agent-to-Agent matching and negotiation
- **Hallucination Guard** - Multi-layer AI safety validation
- **Embedding Store** - Vector search for semantic matching (RAG)
- **Cost Tracker** - Monitor and control AI API costs

### Frontend (Vanilla JS + Tailwind)

**Core Module**: `frontend/js/app.js` - Handles auth, API calls, navigation

**Design System**: Swiss minimalist + Revolut-inspired UI with Tailwind CSS

**Features**:
- PWA with offline support (service worker)
- Push notifications
- Responsive mobile design
- Supabase authentication with demo fallback

### Database (Supabase/PostgreSQL)

**Schema**: `backend/app/schema.sql`

**Key Tables**:
- `cv2_users` - User accounts
- `cv2_profiles` - AI-enriched user profiles
- `cv2_interviews` - Onboarding interview state
- `cv2_agents` - AI agent instances
- `cv2_agent_negotiations` - A2A negotiation records
- `cv2_job_requisitions` - Job postings
- `cv2_matches` - Talent-job matches

**Row Level Security (RLS)**: All tables have RLS policies for user data isolation.

## Development Environment

### Prerequisites

- Python 3.11+
- Node.js (optional, for tooling)
- Supabase account (or local Supabase)

### Setup

```bash
# Create virtual environment
cd backend
python -m venv .venv
source .venv/bin/activate  # Linux/macOS
# .venv\Scripts\activate   # Windows

# Install dependencies
pip install -r requirements.txt

# Configure environment
cp .env.example .env  # Create if needed
# Edit .env with your credentials:
#   SUPABASE_URL=your-supabase-url
#   SUPABASE_SERVICE_KEY=your-service-key
#   ANTHROPIC_API_KEY=your-anthropic-key

# Run database migrations
# Copy schema.sql contents to Supabase SQL editor

# Start development server
uvicorn app.main:app --reload --port 8000
```

### Environment Variables

| Variable | Description | Required |
|----------|-------------|----------|
| `SUPABASE_URL` | Supabase project URL | Yes |
| `SUPABASE_SERVICE_KEY` | Supabase service role key | Yes |
| `SUPABASE_ANON_KEY` | Supabase anonymous key | Yes |
| `ANTHROPIC_API_KEY` | Anthropic Claude API key | Yes |
| `APP_ENV` | Environment (`development`/`production`) | No |
| `WORKERS` | Number of Uvicorn workers | No |

## Common Commands

```bash
# Backend
cd backend
uvicorn app.main:app --reload          # Dev server
pytest                                  # Run tests
pytest -v --tb=short                   # Verbose tests
mypy app/                              # Type checking (if configured)

# Frontend
# Just serve the frontend directory with any HTTP server
python -m http.server 8080 -d frontend

# Full stack (backend serves frontend)
uvicorn app.main:app --reload --port 8000
# Access at http://localhost:8000
```

## API Endpoints

### Health & System
- `GET /health` - Comprehensive health check
- `GET /health/ready` - Readiness probe
- `GET /system/tasks` - Background task status
- `GET /system/cache` - Cache statistics

### User & Auth
- `POST /user/register` - User registration
- `POST /user/login` - Authentication
- `GET /user/profile` - Get user profile
- `PUT /user/profile` - Update profile
- `POST /user/push-subscribe` - Push notification subscription

### Onboarding
- `POST /onboarding/talent/start` - Start talent onboarding
- `POST /onboarding/talent/respond` - Submit onboarding response
- `POST /onboarding/hm/start` - Start hiring manager onboarding

### Jobs & Matching
- `POST /jobs/create` - Create job requisition
- `GET /jobs/list` - List jobs
- `POST /a2a/match` - Trigger A2A matching

### AI Network
- `GET /network/agents` - List active agents
- `POST /network/negotiate` - Agent negotiation
- `GET /network/analytics` - Network analytics

### Master AI
- `GET /master-ai/dashboard` - Control center data
- `POST /master-ai/command` - Execute AI command
- `GET /master-ai/governance` - Governance policies

## AI Agent Architecture

### Agent Types
1. **Talent Agent** - Represents job seekers
2. **Hiring Manager Agent** - Represents employers
3. **Marketing Agent** - Autonomous marketing campaigns
4. **Master AI** - Orchestrates all agents

### Safety Features
- **Hallucination Guard** - Multi-layer fact validation
- **Cost Tracker** - Budget enforcement per agent
- **AI Council** - Multi-agent decision governance
- **Negotiation Protocol** - Structured agent communication

## Testing

```bash
cd backend
pytest                          # All tests
pytest tests/test_auth.py       # Specific file
pytest -k "test_login"          # By name pattern
pytest --cov=app               # With coverage
```

**Test Files**:
- `test_auth.py` - Authentication tests
- `test_database.py` - Database operations
- `test_embedding_store.py` - Vector store tests
- `test_middleware.py` - Middleware tests
- `test_tasks.py` - Background task tests

## Code Conventions

### Python Style
- Follow PEP 8
- Use type hints for function signatures
- Async/await for all I/O operations
- Descriptive variable names

### File Organization
- One service class per file in `services/`
- Route handlers grouped by domain in `api/`
- Shared utilities in root `app/` directory

### Error Handling
- Use FastAPI's HTTPException for API errors
- Log errors with context using Python logging
- Don't expose internal errors in production

## AI Assistant Guidelines

### When Making Changes

1. **Read existing code first** - Understand patterns before modifying
2. **Follow async patterns** - All database and AI calls must be async
3. **Preserve hallucination guards** - Never bypass AI safety checks
4. **Track costs** - Use cost_tracker for all AI API calls
5. **Update tests** - Add tests for new functionality

### Security Considerations

- Never commit `.env` files or API keys
- All user data access must respect RLS policies
- Validate all user input at API boundaries
- Use parameterized queries (handled by Supabase client)

### Common Patterns

**Adding a new API endpoint**:
1. Create route handler in `app/api/`
2. Add service logic in `app/services/`
3. Register router in `main.py`
4. Add tests in `tests/`

**Adding a new AI agent capability**:
1. Implement in relevant service file
2. Add hallucination guard check
3. Track costs with cost_tracker
4. Log with conversation_logger if user-facing

## Troubleshooting

| Issue | Solution |
|-------|----------|
| DB connection fails | Check `SUPABASE_URL` and keys in `.env` |
| AI calls fail | Verify `ANTHROPIC_API_KEY` is valid |
| CORS errors | Check `ALLOWED_ORIGINS` in config |
| Rate limited | Adjust `RateLimitMiddleware` settings |
| Push notifications fail | Check VAPID keys and service worker |

## Future Development

Areas marked for enhancement:
- DSPy prompt optimization (`dspy_learning.py`)
- Enhanced market intelligence
- Multi-tenant deployment
- Real-time agent collaboration
- Advanced analytics dashboard
