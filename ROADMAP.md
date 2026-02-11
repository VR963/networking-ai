# CV2.0 Development Roadmap

> Full multi-session plan from current state to production readiness.

---

## Current State Assessment

### What Exists (22,300+ lines)
- Full FastAPI backend with 9 route modules, 20+ services
- Vanilla JS frontend: Landing, Talent App, HM App, Master AI Dashboard
- Supabase schema (21 tables, RLS, pgvector, triggers)
- 6-category interview pipeline (Talent + HM)
- 3-round AI negotiation protocol with hallucination guard
- Agent memory, reputation, collective intelligence
- Marketing AI, market intelligence, campaign manager
- Cost tracking, demo data fallback
- 5 test files (auth, database, embedding, middleware, tasks)

### Critical Gaps
| Gap | Impact | Priority |
|-----|--------|----------|
| Missing API endpoints (chat history, doc fetch, onboarding status) | Frontend broken | P0 |
| No startup config validation | Silent failures | P0 |
| RAG uses hash-based embeddings (not neural) | Poor semantic search | P1 |
| DSPy imported but not wired | No prompt optimization | P1 |
| No integration tests | Can't verify flows | P1 |
| Background tasks not persistent | Lost on restart | P2 |
| No database migrations | Schema drift risk | P2 |
| Single-instance LRU cache | Can't scale out | P2 |
| Training system not fully wired | Agents don't improve | P2 |
| No CI/CD pipeline | Manual deploys | P3 |

---

## Phase 1: Stabilization & Bootability (Session 2-3)

**Goal**: Make the app start, serve requests, and handle the happy path end-to-end.

### 1.1 Configuration & Startup
- [ ] Add startup validation in `main.py` — check all required env vars on boot
- [ ] Add `.env.example` with all required variables documented
- [ ] Fix `config.py` to raise clear errors for missing keys (not silent None)
- [ ] Add readiness probe that verifies DB connection + schema version

### 1.2 Fix Missing API Endpoints
Frontend calls these but they don't exist in the backend:
- [ ] `GET /chat/history/{user_id}` — fetch past conversations
- [ ] `GET /chat/onboarding-status/{user_id}` — onboarding topic progress
- [ ] `GET /user/documents/{user_id}` — list user documents
- [ ] `GET /calibration/status/{user_id}` — calibration progress
- [ ] Wire `interview_service.compute_interview_quality()` (referenced in auto_activation but missing)

### 1.3 Fix Import & Wiring Issues
- [ ] Audit all cross-service imports — ensure no circular dependencies
- [ ] Verify `industry_knowledge_modules.py` is properly imported in `a2a_engine.py`
- [ ] Wire `agent_training_center` to `ai_profile_service` for full retraining
- [ ] Connect `master_ai_control_center` to all department services (verify imports resolve)

### 1.4 End-to-End Smoke Test
- [ ] Manual walkthrough: signup → upload CV → chat interview → activation → matching
- [ ] Verify Supabase RPC functions exist (or add migration to create them)
- [ ] Test demo data fallback when Supabase unavailable
- [ ] Document all RPC functions needed in `schema.sql`

**Deliverable**: App boots cleanly, all routes respond, happy path works with demo data.

---

## Phase 2: Testing Foundation (Session 4-5)

**Goal**: Establish confidence through automated testing before adding features.

### 2.1 Unit Test Expansion
- [ ] `test_profile_analyzer.py` — CV analysis, job description parsing
- [ ] `test_interview_service.py` — question generation, answer analysis
- [ ] `test_negotiation_protocol.py` — 3-round negotiation, early exit, score weighting
- [ ] `test_hallucination_guard.py` — fabrication detection, profile cleaning
- [ ] `test_auto_activation.py` — readiness scoring, threshold logic
- [ ] `test_network_discovery.py` — compatibility scoring, industry adjacency
- [ ] `test_quality_analyzer.py` — conversation quality scoring
- [ ] `test_cost_tracker.py` — cost calculation, budget alerts

### 2.2 Integration Tests
- [ ] `test_onboarding_flow.py` — full talent onboarding: CV → interview → activation
- [ ] `test_hm_flow.py` — full HM onboarding: JD → interview → activation
- [ ] `test_matching_pipeline.py` — discovery → negotiation → consensus → match storage
- [ ] `test_feedback_loop.py` — match → accept/reject → reputation update → learning

### 2.3 API Endpoint Tests
- [ ] Test all route handlers with FastAPI TestClient
- [ ] Test auth middleware (valid token, expired token, no token, admin)
- [ ] Test rate limiting (verify 429 responses)
- [ ] Test error responses (400, 404, 500 with proper error bodies)

### 2.4 Test Infrastructure
- [ ] Add factory fixtures for users, profiles, agents, jobs, matches
- [ ] Add mock Anthropic responses for deterministic AI testing
- [ ] Set up pytest markers: `@pytest.mark.unit`, `@pytest.mark.integration`, `@pytest.mark.slow`
- [ ] Add test coverage reporting (pytest-cov, target: 70%+)

**Deliverable**: 70%+ test coverage, CI-ready test suite, all tests pass.

---

## Phase 3: AI Pipeline Hardening (Session 6-7)

**Goal**: Replace placeholders with production-grade AI infrastructure.

### 3.1 Real Embedding System
- [ ] Replace hash-based embeddings with Voyage AI (or OpenAI) embedding API
- [ ] Update `embedding_store.py` — real 1024-dim vectors
- [ ] Add embedding batch processing (index multiple docs at once)
- [ ] Add semantic search endpoint: `GET /search?q=...&type=profile|job|pattern`
- [ ] Benchmark: cosine similarity accuracy before/after (hash vs neural)

### 3.2 DSPy Integration
- [ ] Wire DSPy signatures for interview question optimization
- [ ] Add prompt optimization loop: collect examples → optimize → deploy
- [ ] Track prompt versions with A/B performance metrics
- [ ] Add DSPy module for negotiation round prompts

### 3.3 Negotiation Protocol Improvements
- [ ] Add configurable round thresholds (not hardcoded 40/50/60)
- [ ] Add negotiation retry with different emphasis when score is borderline (55-64)
- [ ] Implement proper consensus — both agents generate independent recommendations
- [ ] Add negotiation audit trail (full prompt/response logging for debugging)

### 3.4 Hallucination Guard Hardening
- [ ] Add `_clean_profile()` implementation (referenced but missing)
- [ ] Add structured output validation (JSON schema for all AI responses)
- [ ] Add confidence scoring — flag low-confidence claims for human review
- [ ] Add periodic drift monitoring (compare agent behavior over time)

**Deliverable**: Neural embeddings, DSPy optimization, robust negotiation + integrity.

---

## Phase 4: Infrastructure & Reliability (Session 8-9)

**Goal**: Make the platform reliable, observable, and scalable.

### 4.1 Persistent Task Queue
- [ ] Replace in-memory task queue with Celery + Redis (or ARQ)
- [ ] Add retry logic with exponential backoff for failed tasks
- [ ] Add dead-letter queue for permanently failed tasks
- [ ] Add task status API: `GET /tasks/{task_id}` with progress updates
- [ ] Migrate background operations: governance cycle, training, matching

### 4.2 Caching Layer
- [ ] Add Redis for distributed caching (replace single-instance LRU)
- [ ] Cache agent profiles (invalidate on update)
- [ ] Cache industry patterns (TTL: 1 hour)
- [ ] Cache embedding search results (TTL: 5 minutes)
- [ ] Add cache hit/miss metrics to `/health` endpoint

### 4.3 Database Migrations
- [ ] Add Alembic for schema migrations
- [ ] Create initial migration from current `schema.sql`
- [ ] Add migration for any schema changes going forward
- [ ] Add migration verification in startup health check

### 4.4 Observability
- [ ] Add structured logging (JSON format) with correlation IDs
- [ ] Add request tracing (OpenTelemetry or similar)
- [ ] Add Anthropic API latency tracking (P50, P95, P99)
- [ ] Add real-time cost alerting (Slack/email when budget threshold hit)
- [ ] Add `/metrics` endpoint (Prometheus-compatible)

### 4.5 Error Handling
- [ ] Replace silent try/except with proper error propagation
- [ ] Add domain-specific exception classes (MatchingError, ProfileError, etc.)
- [ ] Add error reporting to external service (Sentry or similar)
- [ ] Ensure no internal details leak in production error responses

**Deliverable**: Persistent tasks, distributed cache, migrations, full observability.

---

## Phase 5: Security & Hardening (Session 10)

**Goal**: Production-grade security posture.

### 5.1 Authentication
- [ ] Add token refresh flow (currently no refresh handling)
- [ ] Add session management (max concurrent sessions, device tracking)
- [ ] Rate limit auth endpoints (prevent brute force)
- [ ] Add email verification requirement before activation

### 5.2 Data Protection
- [ ] Audit all Supabase RLS policies (ensure no data leaks between users)
- [ ] Add input sanitization on all user-facing endpoints
- [ ] Add file upload validation (size limits, type checks, malware scanning)
- [ ] Encrypt sensitive profile data at rest (Supabase vault or column encryption)
- [ ] Remove hardcoded credentials from frontend `config.js`

### 5.3 API Security
- [ ] Add API versioning (`/api/v1/...`)
- [ ] Add request signing for admin endpoints
- [ ] Tighten CORS (remove wildcard in production)
- [ ] Add CSP nonce for inline scripts
- [ ] Security audit of all middleware (verify header values)

### 5.4 AI Safety
- [ ] Add prompt injection detection on user inputs
- [ ] Add output filtering (PII redaction in logs)
- [ ] Add rate limiting per user for AI-heavy endpoints
- [ ] Add content moderation layer before chat responses
- [ ] Audit all system prompts for jailbreak resistance

**Deliverable**: Hardened auth, data protection, API security, AI safety layer.

---

## Phase 6: Frontend Modernization (Session 11-13)

**Goal**: Production-quality user experience.

### 6.1 Architecture Decision
- [ ] Evaluate: stay vanilla JS vs migrate to React/Next.js/Svelte
- [ ] If staying vanilla: add proper module bundling (Vite)
- [ ] If migrating: scaffold new project, migrate views incrementally

### 6.2 Core UX Improvements
- [ ] Add real-time updates (WebSocket or SSE for match notifications)
- [ ] Add proper error states and retry UI for all API calls
- [ ] Add loading skeletons (not just spinners)
- [ ] Add offline-first with IndexedDB message caching
- [ ] Add pagination for conversations, matches, documents

### 6.3 Mobile Experience
- [ ] Audit all pages on mobile (320px - 428px)
- [ ] Fix any overflow, z-index, or touch target issues
- [ ] Add pull-to-refresh on key views
- [ ] Improve PWA: add install banner, proper offline page
- [ ] Test on iOS Safari, Android Chrome

### 6.4 Accessibility
- [ ] Add ARIA labels to all interactive elements
- [ ] Ensure keyboard navigation works throughout
- [ ] Add screen reader support for chat messages
- [ ] Verify color contrast ratios (WCAG AA minimum)

**Deliverable**: Modern, responsive, accessible frontend with real-time updates.

---

## Phase 7: Advanced Features (Session 14-16)

**Goal**: Differentiation features that make CV2.0 unique.

### 7.1 Agent Transparency Dashboard
- [ ] Show users exactly what their agent "knows" about them
- [ ] Let users correct/override agent conclusions
- [ ] Show negotiation replay (what happened in each round)
- [ ] Show why a match was scored the way it was (explainability)

### 7.2 Multi-Agent Council
- [ ] Complete AI Council implementation (multi-perspective evaluation)
- [ ] Add council sessions for borderline matches
- [ ] Add council review for agent certification decisions
- [ ] Log council reasoning for audit trail

### 7.3 Network Intelligence
- [ ] Real-time industry heatmaps (supply/demand by skill)
- [ ] Salary intelligence (anonymized aggregation from profiles)
- [ ] Career path prediction (based on collective patterns)
- [ ] Alert users when market shifts affect their search

### 7.4 Hiring Campaign System
- [ ] Complete campaign lifecycle (create → approve → execute → measure)
- [ ] Add automated A/B testing for campaign content
- [ ] Add attribution tracking (campaign → signup → activation → match)
- [ ] Add ROI reporting for hiring managers

### 7.5 Advanced Matching
- [ ] Add team-level matching (match against team profile, not just role)
- [ ] Add cultural DNA fingerprinting (cluster agents by values similarity)
- [ ] Add "anti-match" detection (identify incompatible pairs early)
- [ ] Add match confidence intervals (not just point scores)

**Deliverable**: Transparent agents, council system, network intelligence, advanced matching.

---

## Phase 8: Deployment & Operations (Session 17-18)

**Goal**: Production deployment with operational excellence.

### 8.1 Containerization
- [ ] Add Dockerfile for backend (multi-stage build)
- [ ] Add Dockerfile for frontend (nginx static serving)
- [ ] Add docker-compose for local development (backend + Redis + worker)
- [ ] Add health check commands in containers

### 8.2 CI/CD Pipeline
- [ ] GitHub Actions: lint → test → build → deploy
- [ ] Add pre-commit hooks (ruff, mypy, black)
- [ ] Add branch protection rules (require tests pass, require review)
- [ ] Add automated dependency updates (Dependabot/Renovate)

### 8.3 Deployment
- [ ] Choose hosting: Railway / Fly.io / AWS ECS / GCP Cloud Run
- [ ] Set up staging environment
- [ ] Set up production environment
- [ ] Add blue-green or canary deployment strategy
- [ ] Add rollback procedure

### 8.4 Monitoring & Alerting
- [ ] Set up uptime monitoring
- [ ] Set up error rate alerting
- [ ] Set up API latency dashboards
- [ ] Set up Anthropic API cost dashboards
- [ ] Set up on-call runbook for common incidents

**Deliverable**: Containerized, CI/CD pipeline, staging + production environments.

---

## Session Priority Matrix

| Session | Phase | Focus | Est. Effort |
|---------|-------|-------|-------------|
| 2-3 | Phase 1 | Stabilization & bootability | Medium |
| 4-5 | Phase 2 | Testing foundation | Medium |
| 6-7 | Phase 3 | AI pipeline hardening | High |
| 8-9 | Phase 4 | Infrastructure & reliability | High |
| 10 | Phase 5 | Security & hardening | Medium |
| 11-13 | Phase 6 | Frontend modernization | High |
| 14-16 | Phase 7 | Advanced features | Very High |
| 17-18 | Phase 8 | Deployment & operations | Medium |

---

## Quick Wins (Can Do in Any Session)

These are low-effort, high-impact improvements you can slot into any session:

1. Add `.env.example` with all required env vars
2. Add `compute_interview_quality()` to interview_service
3. Add `_clean_profile()` to hallucination guard
4. Add missing `GET` endpoints for frontend
5. Add structured error responses (consistent JSON format)
6. Add request correlation IDs (UUID per request in logs)
7. Add `__version__` to main.py (API version tracking)
8. Fix hardcoded model names — use config constants
9. Add database connection retry on startup
10. Add graceful shutdown handler (drain tasks, close connections)

---

## Architecture Evolution

```
CURRENT STATE (v0.1 - Alpha)
┌─────────────────────────────────────────────────┐
│ FastAPI (monolith) + Vanilla JS + Supabase      │
│ - In-memory task queue                          │
│ - Hash-based embeddings                         │
│ - LRU cache (single instance)                   │
│ - Manual deploys                                │
└─────────────────────────────────────────────────┘
          │
          ▼  Phase 1-3
STABILIZED STATE (v0.5 - Beta)
┌─────────────────────────────────────────────────┐
│ FastAPI + Tests + Real Embeddings + DSPy        │
│ - All endpoints working                         │
│ - 70%+ test coverage                            │
│ - Neural embeddings (Voyage AI)                 │
│ - Prompt optimization pipeline                  │
└─────────────────────────────────────────────────┘
          │
          ▼  Phase 4-5
RELIABLE STATE (v1.0 - Production MVP)
┌─────────────────────────────────────────────────┐
│ FastAPI + Redis + Celery + Alembic              │
│ - Persistent task queue                         │
│ - Distributed caching                           │
│ - Database migrations                           │
│ - Observability + security hardened             │
└─────────────────────────────────────────────────┘
          │
          ▼  Phase 6-8
PRODUCTION STATE (v2.0 - Scale)
┌─────────────────────────────────────────────────┐
│ Containerized + CI/CD + Modern Frontend         │
│ - Real-time updates (WebSocket)                 │
│ - Agent transparency                            │
│ - Multi-agent council                           │
│ - Network intelligence                          │
│ - Blue-green deploys, monitoring, alerting      │
└─────────────────────────────────────────────────┘
```

---

*This roadmap is a living document. Update it as priorities shift.*
