# Testing Guide - Phase 1 Validation

## Overview

This guide provides instructions for validating Phase 1 of the AI Agent Marketplace. Tests are comprehensive (1,284 lines) and cover all critical functionality.

---

## Prerequisites

### 1. Environment Setup

```bash
# Create virtual environment (recommended)
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt
```

**Important**: Install ALL dependencies. Some packages (sentence-transformers, chromadb) are large but required.

### 2. Environment Variables

Create `.env` file in project root:

```bash
# Required
ANTHROPIC_API_KEY=your_anthropic_api_key_here

# Database (for testing)
DATABASE_URL=sqlite:///./data/test_database.db

# Optional
DEBUG=false
ENABLE_AI_ANALYSIS=true
```

### 3. Initialize Database

```bash
# Create database schema
python scripts/init_db.py
```

This creates all Phase 1 tables:
- users
- personal_ai_agents
- agent_conversations
- interview_sessions
- sub_agent_activations
- user_knowledge
- network_knowledge
- audit_logs

---

## Running Tests

### Quick Test (All Suites)

```bash
./scripts/run_tests.sh
```

This runs all 29 test cases across 3 test files.

### Individual Test Suites

```bash
# CV Parser tests (9 test cases)
./scripts/run_tests.sh test_cv_parser

# Recruiter Agent tests (15 test cases)
./scripts/run_tests.sh test_recruiter_agent

# E2E Onboarding tests (5 test cases)
./scripts/run_tests.sh test_e2e_onboarding
```

### Manual pytest

```bash
# Run all tests with verbose output
pytest tests/ -v

# Run specific test file
pytest tests/test_cv_parser.py -v

# Run specific test
pytest tests/test_cv_parser.py::TestCVParsing::test_parse_cv_with_ai -v

# Run with coverage
pytest tests/ --cov=src/networking_ai --cov-report=html
```

---

## Test Coverage

### 1. CV Parser Tests (`test_cv_parser.py`)

**Test Classes**:
- `TestCVTextExtraction`: Text extraction from PDF/DOCX/TXT
- `TestCVParsing`: AI-powered parsing with Claude
- `TestIndustryDetection`: Industry and role classification
- `TestUserSegmentation`: User segment ID generation
- `TestFullPipeline`: End-to-end CV processing
- `TestEdgeCases`: Edge cases and error handling

**What's Tested**:
- ✅ Text extraction from multiple formats
- ✅ Structured data extraction (contact, education, work history, skills)
- ✅ Industry detection (finance, tech, etc.)
- ✅ Role detection (engineer, manager, etc.)
- ✅ Experience level classification (junior, senior, expert)
- ✅ Confidence scoring
- ✅ User segmentation for cross-learning
- ✅ Gap detection in employment
- ✅ Minimal CV handling
- ✅ Missing data handling

**Expected Results**:
- Sample CV (John Doe) should classify as:
  - Industry: "finance" or "fintech"
  - Role: Contains "engineer"
  - Level: "senior"
  - Primary skills: Includes "Python"

### 2. Recruiter Agent Tests (`test_recruiter_agent.py`)

**Test Classes**:
- `TestRecruiterAgentInitialization`: Agent setup
- `TestInterviewFlow`: Conversation management
- `TestKnowledgeExtraction`: Learning from conversations
- `TestSubAgentActivation`: Specialized analyzer tools
- `TestCompletionTracking`: Progress monitoring
- `TestConversationHistory`: Memory persistence

**What's Tested**:
- ✅ Agent initialization with LangChain
- ✅ 5 sub-agent tools (psychometric, soft skills, technical, motivation, compensation)
- ✅ Interview conversation flow
- ✅ Opening message generation
- ✅ Follow-up question asking
- ✅ Conversation memory
- ✅ Knowledge extraction (technical skills, motivations, preferences, soft skills)
- ✅ Completion percentage calculation
- ✅ Sub-agent activation triggers
- ✅ Conversation history format

**Expected Results**:
- Agent should have 5 tools
- Conversation should maintain context
- Knowledge should be extracted into categories
- Completion should increase as topics are covered

### 3. E2E Onboarding Tests (`test_e2e_onboarding.py`)

**Test Classes**:
- `TestCompleteOnboardingFlow`: Full user journey
- `TestErrorHandling`: Error cases
- `TestConcurrentUsers`: Multi-user support

**What's Tested**:
- ✅ Complete user journey (CV upload → Parse → Interview → Completion)
- ✅ All 5 API endpoints:
  - POST /api/onboarding/cv-upload
  - POST /api/onboarding/start-interview
  - POST /api/onboarding/interview-message
  - GET /api/onboarding/interview-status/{id}
  - POST /api/onboarding/complete-interview/{id}
- ✅ Authentication and authorization
- ✅ Database state validation
- ✅ Error handling (invalid files, unauthorized access)
- ✅ Knowledge extraction over multiple turns
- ✅ Completion tracking
- ✅ Audit logging

**Expected Results**:
- Full flow should complete in 5-10 conversation turns
- Database should have all records (session, conversation, knowledge)
- Completion percentage should reach 80%+
- All knowledge categories should be populated

---

## Expected Test Results

### Success Criteria

When all tests pass, you should see:

```
====================================== test session starts ======================================
collected 29 items

tests/test_cv_parser.py::TestCVTextExtraction::test_extract_text_from_txt PASSED          [  3%]
tests/test_cv_parser.py::TestCVParsing::test_parse_cv_with_ai PASSED                      [  6%]
tests/test_cv_parser.py::TestCVParsing::test_parse_cv_includes_gaps PASSED                [  10%]
tests/test_cv_parser.py::TestIndustryDetection::test_detect_industry_and_role PASSED      [  13%]
tests/test_cv_parser.py::TestIndustryDetection::test_detect_with_confidence_scores PASSED [  17%]
tests/test_cv_parser.py::TestUserSegmentation::test_generate_user_segment_id PASSED       [  20%]
tests/test_cv_parser.py::TestUserSegmentation::test_segment_ids_consistent PASSED         [  24%]
tests/test_cv_parser.py::TestFullPipeline::test_parse_cv_file_full_pipeline PASSED        [  27%]
tests/test_cv_parser.py::TestEdgeCases::test_parse_minimal_cv PASSED                      [  31%]
tests/test_cv_parser.py::TestEdgeCases::test_parse_cv_missing_dates PASSED                [  34%]

tests/test_recruiter_agent.py::TestRecruiterAgentInitialization::test_create_recruiter_agent PASSED [  37%]
tests/test_recruiter_agent.py::TestRecruiterAgentInitialization::test_agent_has_tools PASSED        [  41%]
tests/test_recruiter_agent.py::TestRecruiterAgentInitialization::test_agent_has_memory PASSED       [  44%]
tests/test_recruiter_agent.py::TestInterviewFlow::test_start_interview PASSED                       [  48%]
tests/test_recruiter_agent.py::TestInterviewFlow::test_ask_question_continues_conversation PASSED   [  51%]
tests/test_recruiter_agent.py::TestInterviewFlow::test_conversation_memory_persists PASSED          [  55%]
tests/test_recruiter_agent.py::TestKnowledgeExtraction::test_extract_technical_knowledge PASSED     [  58%]
tests/test_recruiter_agent.py::TestKnowledgeExtraction::test_extract_motivation_knowledge PASSED    [  62%]
tests/test_recruiter_agent.py::TestKnowledgeExtraction::test_knowledge_structure PASSED             [  65%]
tests/test_recruiter_agent.py::TestSubAgentActivation::test_psychometric_analysis_tool PASSED       [  68%]
tests/test_recruiter_agent.py::TestSubAgentActivation::test_soft_skills_detection_tool PASSED       [  72%]
tests/test_recruiter_agent.py::TestSubAgentActivation::test_technical_assessment_tool PASSED        [  75%]
tests/test_recruiter_agent.py::TestSubAgentActivation::test_motivation_analysis_tool PASSED         [  79%]
tests/test_recruiter_agent.py::TestCompletionTracking::test_calculate_completion_initial PASSED     [  82%]
tests/test_recruiter_agent.py::TestCompletionTracking::test_calculate_completion_progresses PASSED  [  86%]
tests/test_recruiter_agent.py::TestCompletionTracking::test_completion_based_on_knowledge_categories PASSED [  89%]
tests/test_recruiter_agent.py::TestConversationHistory::test_get_conversation_history_format PASSED [  93%]

tests/test_e2e_onboarding.py::TestCompleteOnboardingFlow::test_full_onboarding_journey PASSED       [  96%]
tests/test_e2e_onboarding.py::TestErrorHandling::test_upload_invalid_file_type PASSED               [100%]

====================================== 29 passed in 45.23s =======================================
```

### Test Timing

- **CV Parser tests**: ~10-15 seconds (calls Claude API)
- **Recruiter Agent tests**: ~20-30 seconds (multiple API calls)
- **E2E tests**: ~30-60 seconds (full flow with 5+ turns)

**Total**: ~60-120 seconds for full suite

### Cost Estimation

Running the full test suite costs approximately:
- CV parsing: ~$0.02 per test × 9 tests = $0.18
- Agent interviews: ~$0.05 per test × 15 tests = $0.75
- E2E flow: ~$0.15 per test × 2 tests = $0.30

**Total**: ~$1.25 per full test run

---

## Troubleshooting

### Issue: "ANTHROPIC_API_KEY not set"

```bash
# Set in terminal
export ANTHROPIC_API_KEY='your-key-here'

# Or add to .env file
echo "ANTHROPIC_API_KEY=your-key-here" >> .env
```

### Issue: "Module not found"

```bash
# Reinstall dependencies
pip install -r requirements.txt

# Check specific package
pip list | grep anthropic
pip list | grep langchain
```

### Issue: "Database locked" (SQLite)

```bash
# Remove test database and recreate
rm data/test_database.db
python scripts/init_db.py
```

### Issue: "Tests are slow"

This is expected. Tests make real API calls to Claude which takes time.

To speed up:
- Run specific test suites instead of all
- Use pytest-xdist for parallel execution (experimental)

### Issue: "Numpy compatibility error"

```bash
# Ensure compatible numpy version
pip install "numpy>=1.24.0,<2.0"
```

### Issue: "ChromaDB errors"

```bash
# Reinstall chromadb
pip uninstall chromadb
pip install chromadb==0.4.22
```

---

## Manual API Testing (Optional)

### 1. Start the API Server

```bash
uvicorn src.networking_ai.api.main:app --reload
```

### 2. Test Endpoints with curl

```bash
# Register user
curl -X POST http://localhost:8000/api/auth/register \
  -H "Content-Type: application/json" \
  -d '{"email":"test@example.com","password":"testpass123","full_name":"Test User"}'

# Login
curl -X POST http://localhost:8000/api/auth/login \
  -d "username=test@example.com&password=testpass123"

# Upload CV (save token from login)
curl -X POST http://localhost:8000/api/onboarding/cv-upload \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -F "file=@path/to/cv.pdf"

# Start interview
curl -X POST http://localhost:8000/api/onboarding/start-interview \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"session_id":1}'

# Send message
curl -X POST http://localhost:8000/api/onboarding/interview-message \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"conversation_id":1,"message":"I work in finance..."}'
```

### 3. Test with Postman/Insomnia

Import the API collection (create one based on endpoints above).

---

## Database Inspection

### View Created Tables

```bash
# SQLite
sqlite3 data/test_database.db ".tables"

# PostgreSQL
psql -d networking_ai -c "\dt"
```

### Check Data

```bash
# SQLite
sqlite3 data/test_database.db "SELECT * FROM interview_sessions;"
sqlite3 data/test_database.db "SELECT * FROM agent_conversations LIMIT 1;"

# PostgreSQL
psql -d networking_ai -c "SELECT * FROM interview_sessions;"
```

---

## What to Validate

### ✅ Phase 1 Critical Functionality

1. **CV Upload & Parsing**
   - PDFs are extracted correctly
   - CVs are parsed into structured data
   - Industry is detected (finance/tech/etc)
   - Role is detected (engineer/manager/etc)

2. **Recruiter Agent**
   - Interview starts with greeting
   - Questions are relevant and natural
   - Conversation maintains context
   - Knowledge is extracted
   - Sub-agents activate appropriately

3. **API Endpoints**
   - All 5 endpoints respond correctly
   - Authentication works
   - Errors are handled gracefully
   - Database is updated properly

4. **Database**
   - All 8 Phase 1 tables exist
   - Relationships are correct
   - Data is stored properly
   - Audit logs are created

5. **Knowledge Extraction**
   - Technical skills captured
   - Motivations identified
   - Preferences understood
   - Soft skills detected
   - Completion percentage accurate

---

## Continuous Integration (Future)

### GitHub Actions (Recommended)

```yaml
name: Phase 1 Tests

on: [push, pull_request]

jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v2
      - uses: actions/setup-python@v2
        with:
          python-version: '3.11'
      - run: pip install -r requirements.txt
      - run: pytest tests/
    env:
      ANTHROPIC_API_KEY: ${{ secrets.ANTHROPIC_API_KEY }}
```

---

## Summary

**Phase 1 is production-ready** once these tests pass in your environment.

**Next Steps**:
1. Run tests locally
2. Verify all pass
3. Document any issues found
4. Move to Phase 2 development

**Questions?** Check:
- `PHASE_1_COMPLETE.md` - Completion report
- `AGENT_ARCHITECTURE.md` - Full architecture
- `API_COMPLETE.md` - API documentation

---

*Testing Guide v1.0 - Phase 1 Validation*
