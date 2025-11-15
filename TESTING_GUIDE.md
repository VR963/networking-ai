# Comprehensive Testing Guide

This guide explains how to test the Networking AI platform after rebuild, including registration flow and agent-to-agent interactions.

## Overview

The test suite includes:
1. **Registration Flow Tests** - User registration, login, and profile setup
2. **Agent Interaction Tests** - AI agent communication and collaboration
3. **Master AI Analysis** - Coordination and orchestration capabilities
4. **Comprehensive Report** - Overall system health and performance

## Prerequisites

1. **System Running**: Ensure the application is running via Docker
2. **Python 3.11+**: Required for test scripts
3. **Dependencies**: `requests` library

### Install Test Dependencies

```bash
pip install requests
```

## Quick Start - Run All Tests

After rebuilding the system with `docker-compose up --build`:

```bash
# Wait for all services to be healthy (about 30-60 seconds)

# Run the comprehensive test suite
python run_comprehensive_tests.py

# Or with custom URL
python run_comprehensive_tests.py --url http://localhost:8000
```

This will:
- Run all registration tests
- Run all agent interaction tests
- Generate comprehensive reports
- Analyze Master AI performance
- Provide recommendations

## Individual Test Suites

### 1. Registration Flow Tests

Tests user registration and onboarding:

```bash
python test_registration_flow.py
```

**What it tests:**
- ✅ API health check
- ✅ Job seeker registration
- ✅ Hiring manager registration
- ✅ User login
- ✅ Personal AI agent creation
- ✅ Agent conversation
- ✅ Onboarding flow

## How Registration Works

Based on the test results, here's how the registration flow works:

### Job Seeker Registration

```
User submits registration form → POST /api/auth/register
System creates:
    - User account in database
    - User profile
    - Personal AI agent
    - Email verification token
Returns access token and agent ID
```

### Hiring Manager Registration

```
User submits registration form → POST /api/auth/register
System creates:
    - User account
    - Company record
    - Company admin user
    - Company AI agent
    - Subscription
Returns access token, company ID, and agent ID
```

## How Agent-to-Agent Interactions Work

### Architecture Overview

```
Master AI (coordinates all communications)
    ↓
Personal Agent ←→ Company Agent
    ↓                   ↓
User Profile      Job Postings
```

For complete documentation, see the full testing guide.
