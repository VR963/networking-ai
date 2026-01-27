# CLAUDE.md - AI Assistant Guide for networking-ai

> AI-native professional networking platform – connecting people through intelligent agents and semantic discovery.

## Project Overview

This is an early-stage Python project building an AI-powered professional networking platform. The platform aims to use intelligent agents and semantic discovery to connect people in meaningful ways.

**Project Stage:** Initial skeleton - active development starting

## Technology Stack

Based on project configuration, this is a **Python** project with the following tooling:

| Category | Tool | Purpose |
|----------|------|---------|
| Language | Python 3.x | Primary development language |
| Linting | Ruff | Fast Python linter and formatter |
| Type Checking | mypy | Static type analysis |
| Testing | pytest | Test framework |
| Notebooks | Marimo | Interactive Python notebooks |
| Automation | Abstra | AI-powered process automation framework |

## Directory Structure

```
networking-ai/
├── CLAUDE.md          # This file - AI assistant guidelines
├── README.md          # Project overview
├── LICENSE            # MIT License
├── .gitignore         # Python-focused ignore rules
└── (source code to be added)
```

### Planned Structure (to be created as development progresses)

```
networking-ai/
├── src/               # Main source code
│   ├── __init__.py
│   ├── agents/        # AI agent implementations
│   ├── discovery/     # Semantic discovery modules
│   ├── networking/    # Connection and matching logic
│   └── api/           # API endpoints
├── tests/             # Test files
│   ├── __init__.py
│   ├── unit/
│   └── integration/
├── docs/              # Documentation
├── scripts/           # Utility scripts
├── pyproject.toml     # Project configuration
└── requirements.txt   # Dependencies (or use pyproject.toml)
```

## Development Commands

Once the project is set up, these are the expected commands:

```bash
# Install dependencies (after pyproject.toml is created)
pip install -e ".[dev]"
# or with uv:
uv pip install -e ".[dev]"

# Run linter
ruff check .
ruff format .

# Run type checker
mypy src/

# Run tests
pytest
pytest --cov=src  # with coverage

# Run specific test file
pytest tests/unit/test_example.py -v
```

## Code Style & Conventions

### Python Standards

- **Python Version:** Target Python 3.10+ for modern features
- **Type Hints:** Use type hints for all function signatures
- **Docstrings:** Use Google-style docstrings for modules, classes, and functions
- **Imports:** Use absolute imports; organize with `isort` (configured via Ruff)

### Naming Conventions

| Element | Convention | Example |
|---------|------------|---------|
| Modules | snake_case | `semantic_search.py` |
| Classes | PascalCase | `AgentManager` |
| Functions | snake_case | `find_connections()` |
| Constants | UPPER_SNAKE | `MAX_CONNECTIONS` |
| Private | Leading underscore | `_internal_method()` |

### File Organization

- Keep files focused and under 500 lines when possible
- One class per file for major components
- Group related utilities in shared modules
- Tests mirror source structure (`src/agents/` → `tests/unit/agents/`)

## AI Assistant Guidelines

### When Working on This Codebase

1. **Read before modifying:** Always read existing files before proposing changes
2. **Maintain type safety:** Add type hints to all new code
3. **Write tests:** New features should include tests
4. **Keep it simple:** Avoid over-engineering; prefer minimal solutions
5. **Document intent:** Add docstrings for non-obvious logic

### Common Tasks

#### Adding a New Feature

1. Create the module in appropriate `src/` subdirectory
2. Add corresponding test file in `tests/`
3. Update any relevant documentation
4. Run linter and type checker before committing

#### Fixing a Bug

1. Write a failing test that reproduces the bug
2. Fix the bug in the minimal way possible
3. Verify the test passes
4. Check for similar issues elsewhere in codebase

#### Adding Dependencies

- Add to `pyproject.toml` under `[project.dependencies]`
- Dev-only dependencies go under `[project.optional-dependencies.dev]`
- Pin versions for reproducibility in production code

### Things to Avoid

- Don't add features beyond what's requested
- Don't refactor unrelated code while fixing bugs
- Don't add comments to unchanged code
- Don't create abstractions for one-time operations
- Don't commit files containing secrets or credentials

## Environment Setup

### Required Environment Variables

Create a `.env` file (not committed to git) for local development:

```bash
# Example .env structure (to be defined as project develops)
# DATABASE_URL=postgresql://localhost/networking_ai
# OPENAI_API_KEY=sk-...
# LOG_LEVEL=DEBUG
```

### Virtual Environment

```bash
# Create virtual environment
python -m venv .venv

# Activate
source .venv/bin/activate  # Linux/macOS
.venv\Scripts\activate     # Windows

# Install dependencies
pip install -e ".[dev]"
```

## Git Workflow

### Branch Naming

- Feature branches: `feature/<description>`
- Bug fixes: `fix/<description>`
- AI assistant branches: `claude/<session-id>`

### Commit Messages

Use conventional commit format:

```
type(scope): description

[optional body]

[optional footer]
```

Types: `feat`, `fix`, `docs`, `style`, `refactor`, `test`, `chore`

Example:
```
feat(agents): add semantic matching algorithm

Implements cosine similarity matching for user profiles
using sentence embeddings.
```

## Testing Strategy

### Test Categories

- **Unit tests:** Test individual functions/classes in isolation
- **Integration tests:** Test component interactions
- **End-to-end tests:** Test complete user workflows

### Running Tests

```bash
# All tests
pytest

# With coverage report
pytest --cov=src --cov-report=html

# Specific marker
pytest -m "not slow"

# Verbose output
pytest -v
```

## Architecture Notes

### Core Concepts (Planned)

1. **Intelligent Agents:** AI agents that represent users and facilitate connections
2. **Semantic Discovery:** Vector-based similarity search for finding relevant connections
3. **Profile Matching:** Multi-dimensional compatibility scoring

### Design Principles

- **Privacy First:** User data protection is paramount
- **Explainable AI:** Users should understand why connections are suggested
- **Scalability:** Design for horizontal scaling from the start
- **API-First:** Build clean APIs for all functionality

## Troubleshooting

### Common Issues

| Issue | Solution |
|-------|----------|
| Import errors | Ensure package is installed: `pip install -e .` |
| Type errors | Run `mypy src/` and fix reported issues |
| Test failures | Check test database state, run with `-v` for details |
| Linting errors | Run `ruff check --fix .` for auto-fixes |

## Resources

- [Python Type Hints](https://docs.python.org/3/library/typing.html)
- [Ruff Documentation](https://docs.astral.sh/ruff/)
- [pytest Documentation](https://docs.pytest.org/)
- [Marimo Documentation](https://docs.marimo.io/)
- [Abstra Documentation](https://abstra.io/docs)

---

*This document should be updated as the project evolves. Last updated: 2026-01-27*
