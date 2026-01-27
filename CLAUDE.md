# CLAUDE.md - AI Assistant Guide for networking-ai

## Project Overview

**networking-ai** is an AI-native professional networking platform that connects people through intelligent agents and semantic discovery. The platform leverages AI/LLM technology to enable smarter professional connections and networking experiences.

## Repository Status

This repository is in its **initial setup phase**. The foundational scaffolding is in place, but implementation has not yet begun.

## Technology Stack

### Primary Language
- **Python 3.11+** (recommended)

### Package Management (choose one)
- **UV** (recommended for speed)
- Poetry
- PDM
- Pipenv

### Development Tools
| Tool | Purpose |
|------|---------|
| pytest | Unit and integration testing |
| mypy | Static type checking |
| Ruff | Linting and formatting |
| Sphinx | Documentation generation |

### Frameworks (anticipated)
- FastAPI or Flask for API endpoints
- Marimo for interactive notebooks/components
- LangChain or similar for AI agent orchestration

## Project Structure (Recommended)

```
networking-ai/
├── src/
│   └── networking_ai/
│       ├── __init__.py
│       ├── agents/          # AI agent implementations
│       ├── api/             # API endpoints
│       ├── core/            # Core business logic
│       ├── models/          # Data models
│       ├── services/        # External service integrations
│       └── utils/           # Utility functions
├── tests/
│   ├── unit/
│   ├── integration/
│   └── conftest.py
├── docs/
├── scripts/
├── pyproject.toml
├── README.md
├── CLAUDE.md
└── .gitignore
```

## Development Commands

```bash
# Install dependencies (using UV)
uv sync

# Run tests
pytest

# Run tests with coverage
pytest --cov=src/networking_ai --cov-report=html

# Type checking
mypy src/

# Linting and formatting
ruff check src/ tests/
ruff format src/ tests/

# Run the application (when implemented)
python -m networking_ai
```

## Code Conventions

### Python Style
- Follow PEP 8 style guidelines
- Use type hints for all function signatures
- Maximum line length: 88 characters (Black/Ruff default)
- Use double quotes for strings
- Prefer `pathlib.Path` over `os.path`

### Naming Conventions
- **Files/modules**: `snake_case.py`
- **Classes**: `PascalCase`
- **Functions/variables**: `snake_case`
- **Constants**: `UPPER_SNAKE_CASE`
- **Private members**: `_leading_underscore`

### Import Order
1. Standard library imports
2. Third-party imports
3. Local application imports

Use `ruff` for automatic import sorting.

### Documentation
- Use Google-style docstrings
- Document all public APIs
- Include type hints in function signatures

```python
def find_connections(user_id: str, limit: int = 10) -> list[Connection]:
    """Find potential professional connections for a user.

    Args:
        user_id: The unique identifier of the user.
        limit: Maximum number of connections to return.

    Returns:
        A list of Connection objects ordered by relevance.

    Raises:
        UserNotFoundError: If the user_id does not exist.
    """
```

## Testing Guidelines

### Test Structure
- Place tests in `tests/` directory mirroring source structure
- Use `test_` prefix for test files and functions
- Group related tests in classes with `Test` prefix

### Test Categories
- **Unit tests**: Test individual functions/classes in isolation
- **Integration tests**: Test component interactions
- **E2E tests**: Test full user workflows

### Fixtures
- Define shared fixtures in `conftest.py`
- Use factory fixtures for creating test data
- Mock external services in tests

```python
# Example test structure
def test_agent_finds_relevant_connections():
    """Agent should return connections based on semantic similarity."""
    agent = NetworkingAgent(embedding_model=mock_model)
    user = create_test_user(interests=["AI", "startups"])

    connections = agent.find_connections(user)

    assert len(connections) > 0
    assert all(c.relevance_score > 0.7 for c in connections)
```

## AI Agent Development

### Agent Architecture
When implementing AI agents:
- Use async/await for I/O operations
- Implement proper error handling and retries
- Log agent decisions for debugging
- Include rate limiting for external API calls

### Embedding & Semantic Search
- Use consistent embedding models across the application
- Cache embeddings when possible
- Implement similarity thresholds as configurable parameters

## Git Workflow

### Branch Naming
- Features: `feature/<description>`
- Bug fixes: `fix/<description>`
- AI assistant work: `claude/<session-id>`

### Commit Messages
Follow conventional commits:
```
type(scope): description

feat(agents): add semantic connection discovery
fix(api): handle rate limit errors gracefully
docs(readme): update installation instructions
test(agents): add unit tests for matching algorithm
```

### Pull Requests
- Keep PRs focused and reasonably sized
- Include tests for new functionality
- Update documentation as needed
- Ensure all CI checks pass

## Environment Variables

Expected environment variables (create `.env` file):
```bash
# API Keys
OPENAI_API_KEY=           # For embeddings/LLM
ANTHROPIC_API_KEY=        # Alternative LLM provider

# Database
DATABASE_URL=             # Connection string

# Application
DEBUG=false
LOG_LEVEL=INFO
```

## Common Tasks for AI Assistants

### When Adding a New Feature
1. Create/update tests first (TDD approach encouraged)
2. Implement the feature in the appropriate module
3. Add type hints and docstrings
4. Run linting and type checking
5. Ensure all tests pass
6. Update documentation if needed

### When Fixing a Bug
1. Write a failing test that reproduces the bug
2. Fix the bug
3. Verify the test passes
4. Check for similar issues elsewhere

### When Refactoring
1. Ensure comprehensive test coverage exists
2. Make incremental changes
3. Run tests after each change
4. Preserve external API contracts

## Dependencies

### Adding Dependencies
```bash
# Using UV
uv add <package>
uv add --dev <dev-package>
```

### Core Dependencies (anticipated)
- `fastapi` - API framework
- `pydantic` - Data validation
- `httpx` - HTTP client
- `openai` or `anthropic` - LLM integration
- `numpy` - Numerical operations
- `scikit-learn` - ML utilities

### Dev Dependencies
- `pytest` - Testing
- `pytest-cov` - Coverage
- `pytest-asyncio` - Async test support
- `mypy` - Type checking
- `ruff` - Linting/formatting

## Architecture Notes

### Key Design Principles
1. **Agent-first**: Design APIs around AI agent interactions
2. **Semantic-aware**: Use embeddings for content matching
3. **Privacy-conscious**: Handle user data responsibly
4. **Scalable**: Design for horizontal scaling

### Data Flow (anticipated)
```
User Input → API → Agent Orchestrator → Embedding Service
                         ↓
                   Vector Search → Matching Algorithm
                         ↓
                   Response Generation → User Output
```

## Troubleshooting

### Common Issues

**Import errors after adding new modules:**
- Ensure `__init__.py` exists in all package directories
- Check that the package is installed in editable mode

**Type checking failures:**
- Install type stubs: `uv add types-<package>`
- Use `# type: ignore` sparingly with explanation

**Test failures in CI but not locally:**
- Check for environment-specific code
- Ensure test isolation (no shared state)
- Verify all fixtures are properly scoped

## Resources

- [Python Best Practices](https://docs.python-guide.org/)
- [FastAPI Documentation](https://fastapi.tiangolo.com/)
- [Pytest Documentation](https://docs.pytest.org/)
- [Ruff Documentation](https://docs.astral.sh/ruff/)
