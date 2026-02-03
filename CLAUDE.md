# CLAUDE.md

This file provides context and instructions for Claude Code when working on this project.

## Project Overview

**CV 2.0** is an AI-native professional networking platform that uses intelligent agents to represent candidates and hiring managers. The system enables:
- AI agents that understand users deeply through structured interviews
- Agent-to-agent (A2A) negotiation for quality job matching
- Multi-round AI negotiations with human-in-the-loop validation
- Collective intelligence learning across the network
- Master AI governance to ensure match quality and network health

## Work Status

### Saved Work Location
All CV 2.0 backend work is saved on branch: `origin/claude/setup-cv2-backend-LTv40`

**Stats:** 78 files, 22,303+ lines of code

To checkout and continue work:
```bash
git fetch origin
git checkout -b cv2-backend origin/claude/setup-cv2-backend-LTv40
```

## Architecture Overview

### Directory Structure
```
networking-ai/
├── backend/                    # FastAPI Python backend
│   ├── app/
│   │   ├── api/               # API route handlers (8 modules)
│   │   ├── routes/            # Master AI routes
│   │   ├── services/          # Core business logic (30+ services)
│   │   ├── main.py            # FastAPI application entry point
│   │   ├── config.py          # Configuration & environment variables
│   │   ├── database.py        # Supabase connection pool + LRU cache
│   │   ├── auth.py            # JWT authentication via Supabase
│   │   ├── middleware.py      # Rate limiting, security, logging
│   │   └── schema.sql         # PostgreSQL schema (Supabase)
│   └── tests/                 # Pytest test suite
│
├── frontend/                  # Vanilla HTML/CSS/JS frontend
│   ├── index.html            # Landing page
│   ├── talent-*.html         # Talent agent interfaces
│   ├── hm-*.html             # Hiring manager interfaces
│   ├── master-*.html         # Master AI admin dashboards
│   └── js/app.js             # Shared app module
```

### Tech Stack
- **Backend:** FastAPI, Python 3.11+, Supabase (PostgreSQL + pgvector)
- **AI:** Anthropic Claude API, DSPy for prompt optimization
- **Frontend:** Vanilla HTML/CSS/JS, Tailwind CSS, PWA-ready
- **Auth:** Supabase JWT tokens

### Key Services
| Service | Purpose |
|---------|---------|
| `master_ai_governance.py` | Quality gates, network health, agent suspension |
| `a2a_engine.py` | Agent-to-agent negotiation and matching |
| `dspy_learning.py` | ML-based prompt optimization |
| `collective_intelligence.py` | Network-wide pattern learning |
| `interview_service.py` | 6-category structured interviews |

### API Routes
- `/user/*` - Profile management
- `/onboarding/*` - Talent/HM structured interviews
- `/chat/*` - Profile refinement chat
- `/a2a/*` - Agent-to-agent matching
- `/master-ai/*` - Governance and admin

## Picking Up Work from Claude Code

### How to Resume Previous Work

1. **Use the `/resume` command** - In Claude Code CLI, type `/resume` to see recent sessions

2. **Check git branches** - Previous work is on feature branches:
   ```bash
   git fetch --all
   git branch -r  # List all remote branches
   ```

3. **Key branches:**
   - `origin/claude/setup-cv2-backend-LTv40` - Main CV 2.0 backend work
   - `origin/main` - Initial commit only (clean slate)

### Session Continuity Tips

- Commit frequently with descriptive messages
- Use TODO comments: `// TODO:` or `# TODO:`
- Update this file with in-progress work notes

### Useful Claude Code Commands

| Command | Description |
|---------|-------------|
| `/resume` | Resume a previous session |
| `/status` | Show current session status |
| `/clear` | Clear conversation history |
| `/help` | Show all available commands |
| `/compact` | Summarize conversation to reduce context |

## Development Guidelines

### Running the Backend
```bash
cd backend
pip install -r requirements.txt
python -m app.main  # Runs on http://0.0.0.0:8000
```

### Environment Variables
```
SUPABASE_URL               # PostgreSQL database
SUPABASE_SERVICE_KEY       # Backend-only API key
ANTHROPIC_API_KEY          # Claude AI access
APP_ENV                    # development/staging/production
```

### Running Tests
```bash
cd backend
pytest
```

### Code Patterns
- Async/await throughout the backend
- Singleton database connection pool
- LRU caching for frequently accessed data
- Background task queue for AI operations
- Row-level security (RLS) in Supabase

## In-Progress Work / TODOs

Add notes about current work here:
- [ ] Merge CV2 backend to main branch
- [ ] Set up production environment
- [ ] Complete calibration test flow
- [ ] Add more industry knowledge modules
