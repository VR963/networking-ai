#!/bin/bash
#
# Test Runner Script for Phase 1 Onboarding Tests
#
# Usage:
#   ./scripts/run_tests.sh [test_file]
#
# Examples:
#   ./scripts/run_tests.sh                     # Run all tests
#   ./scripts/run_tests.sh test_cv_parser      # Run CV parser tests only
#   ./scripts/run_tests.sh test_e2e_onboarding # Run E2E tests only
#

set -e  # Exit on error

echo "========================================="
echo "Phase 1 Onboarding Test Suite"
echo "========================================="
echo ""

# Check if ANTHROPIC_API_KEY is set
if [ -z "$ANTHROPIC_API_KEY" ]; then
    echo "❌ ERROR: ANTHROPIC_API_KEY environment variable not set"
    echo ""
    echo "Please set your Anthropic API key:"
    echo "  export ANTHROPIC_API_KEY='your-key-here'"
    echo ""
    exit 1
fi

echo "✓ ANTHROPIC_API_KEY is set"
echo ""

# Change to project root
cd "$(dirname "$0")/.."

# Activate virtual environment if it exists
if [ -d "venv" ]; then
    echo "✓ Activating virtual environment..."
    source venv/bin/activate
fi

# Install test dependencies if needed
echo "✓ Checking dependencies..."
pip install -q pytest pytest-asyncio httpx fastapi[all] 2>/dev/null || true

echo ""
echo "========================================="
echo "Running Tests"
echo "========================================="
echo ""

# Run tests
if [ -z "$1" ]; then
    # Run all Phase 1 tests
    echo "Running ALL Phase 1 tests..."
    pytest tests/test_cv_parser.py \
           tests/test_recruiter_agent.py \
           tests/test_e2e_onboarding.py \
           -v \
           --tb=short \
           --color=yes
else
    # Run specific test file
    echo "Running tests: $1..."
    pytest "tests/${1}.py" -v --tb=short --color=yes
fi

echo ""
echo "========================================="
echo "Test Summary"
echo "========================================="
echo ""

if [ $? -eq 0 ]; then
    echo "✅ All tests passed!"
    echo ""
    echo "Phase 1 onboarding system is working correctly:"
    echo "  - CV parsing and industry detection ✓"
    echo "  - Recruiter agent interviews ✓"
    echo "  - API endpoints and database ✓"
    echo "  - End-to-end user flow ✓"
else
    echo "❌ Some tests failed"
    echo ""
    echo "Please review the output above for details."
    exit 1
fi

echo ""
echo "To run individual test suites:"
echo "  ./scripts/run_tests.sh test_cv_parser"
echo "  ./scripts/run_tests.sh test_recruiter_agent"
echo "  ./scripts/run_tests.sh test_e2e_onboarding"
echo ""
