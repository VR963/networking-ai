# CLAUDE.md - AI Assistant Guidelines

## Project Overview

**networking-ai** is an AI-native professional networking platform that connects people through intelligent agents and semantic discovery. The platform aims to revolutionize professional networking by leveraging AI for intelligent matchmaking, relationship building, and knowledge sharing.

### Project Vision
- AI-first architecture with intelligent agents at the core
- Semantic discovery for meaningful professional connections
- Modern, scalable Python-based backend

## Project Status

This is an **early-stage project** currently in the initialization phase. Core implementation has not yet begun.

## Technology Stack

### Primary Language
- **Python 3.10+** (recommended)

### Expected Frameworks & Tools
Based on project configuration, the following tools are anticipated:

| Category | Tools |
|----------|-------|
| Web Framework | Django or Flask (TBD) |
| Testing | pytest, coverage, tox |
| Type Checking | mypy, pytype |
| Linting/Formatting | Ruff, black, isort |
| Documentation | Sphinx, mkdocs |
| Package Management | pip, poetry, or uv |
| Notebooks | Jupyter (for prototyping/research) |

## Repository Structure

```
networking-ai/
├── .gitignore          # Python-focused ignore rules
├── LICENSE             # MIT License (VR963, 2025)
├── README.md           # Project description
├── CLAUDE.md           # This file - AI assistant guidelines
└── (source code TBD)
```

### Planned Directory Structure (Recommended)
```
networking-ai/
├── src/                # Main source code
│   └── networking_ai/  # Primary package
│       ├── __init__.py
│       ├── agents/     # AI agent implementations
│       ├── api/        # API endpoints
│       ├── models/     # Data models
│       ├── services/   # Business logic
│       └── utils/      # Utility functions
├── tests/              # Test suite
│   ├── unit/
│   └── integration/
├── docs/               # Documentation
├── scripts/            # Utility scripts
├── pyproject.toml      # Project configuration
└── README.md
```

## Development Guidelines

### Code Style

1. **Follow PEP 8** with these specifics:
   - Max line length: 88 characters (Black default)
   - Use double quotes for strings
   - Use trailing commas in multi-line structures

2. **Type Hints**: Use type hints for all function signatures
   ```python
   def find_connections(user_id: str, limit: int = 10) -> list[Connection]:
       ...
   ```

3. **Docstrings**: Use Google-style docstrings for public APIs
   ```python
   def semantic_search(query: str, filters: dict | None = None) -> list[Result]:
       """Search for professionals using semantic matching.

       Args:
           query: Natural language search query.
           filters: Optional filters for industry, location, etc.

       Returns:
           List of matching professional profiles.
       """
   ```

4. **Imports**: Order imports as:
   - Standard library
   - Third-party packages
   - Local application imports
   - Use absolute imports

### Naming Conventions

| Type | Convention | Example |
|------|------------|---------|
| Modules | snake_case | `user_profile.py` |
| Classes | PascalCase | `ConnectionAgent` |
| Functions | snake_case | `get_recommendations()` |
| Constants | UPPER_SNAKE | `MAX_CONNECTIONS` |
| Private | Leading underscore | `_internal_method()` |

### AI Agent Development

When implementing AI agents for this platform:

1. **Agent Interface**: All agents should implement a common interface
2. **Stateless Design**: Prefer stateless agent operations where possible
3. **Error Handling**: Agents must gracefully handle API failures and edge cases
4. **Logging**: Include structured logging for agent decisions and actions
5. **Testing**: Write comprehensive tests for agent behavior

### Testing

1. **Test Location**: Tests mirror the source structure in `tests/`
2. **Naming**: Test files should be named `test_<module>.py`
3. **Coverage**: Aim for >80% code coverage
4. **Markers**: Use pytest markers for slow/integration tests

```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=src/networking_ai

# Run specific markers
pytest -m "not slow"
```

## Common Commands

```bash
# Install dependencies (when pyproject.toml exists)
pip install -e ".[dev]"

# Run linting
ruff check .

# Run type checking
mypy src/

# Format code
ruff format .

# Run tests
pytest

# Build documentation
mkdocs build  # or sphinx-build docs/ docs/_build/
```

## Git Workflow

### Branch Naming
- Feature branches: `feature/<description>`
- Bug fixes: `fix/<description>`
- AI assistant branches: `claude/<session-id>`

### Commit Messages
Use conventional commits:
```
feat: add semantic search endpoint
fix: resolve connection timeout issue
docs: update API documentation
test: add agent integration tests
refactor: simplify recommendation engine
```

### Pre-commit Checks
Before committing, ensure:
1. All tests pass
2. Linting passes (ruff)
3. Type checking passes (mypy)
4. Code is formatted

## Environment Setup

### Environment Variables
Create a `.env` file (never commit):
```bash
# API Keys
OPENAI_API_KEY=your_key_here
ANTHROPIC_API_KEY=your_key_here

# Database
DATABASE_URL=postgresql://user:pass@localhost/networking_ai

# Application
DEBUG=true
LOG_LEVEL=INFO
```

### Virtual Environment
```bash
python -m venv .venv
source .venv/bin/activate  # Linux/macOS
# or
.venv\Scripts\activate     # Windows
```

## AI Assistant Notes

### When Working on This Codebase

1. **Read before modifying**: Always read relevant files before making changes
2. **Keep changes focused**: Make minimal, targeted changes
3. **Maintain consistency**: Follow existing patterns in the codebase
4. **Test thoroughly**: Run tests after making changes
5. **Document decisions**: Add comments for non-obvious logic

### Key Considerations

- This is an AI-native platform; AI integration is core, not an add-on
- Semantic understanding and discovery are primary features
- Professional networking context requires privacy and data security awareness
- Scalability should be considered in architectural decisions

### Areas Needing Implementation

Since this is early-stage, major components to implement include:
- [ ] Project setup with pyproject.toml
- [ ] Core data models (User, Connection, Profile)
- [ ] AI agent framework
- [ ] Semantic search infrastructure
- [ ] API layer
- [ ] Authentication/authorization
- [ ] Database migrations
- [ ] Test infrastructure

## License

MIT License - See [LICENSE](LICENSE) for details.

---

*Last updated: 2026-01-27*
