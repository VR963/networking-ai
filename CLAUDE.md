# CLAUDE.md - AI Assistant Guide for networking-ai

## Project Overview

**networking-ai** is an AI-native professional networking platform designed to connect people through intelligent agents and semantic discovery. The platform leverages AI capabilities to facilitate meaningful professional connections.

**License:** MIT License (Copyright 2025 VR963)

## Technology Stack

### Core Technologies (Planned)
- **Language:** Python 3.x
- **Web Frameworks:** Django, Flask
- **AI/ML Integration:** Abstra (AI-powered process automation)
- **Interactive Development:** Marimo (notebooks/UI), Jupyter

### Development Tools
- **Linting/Formatting:** Ruff
- **Type Checking:** mypy
- **Testing:** pytest with coverage
- **Package Management:** pip, poetry, uv, or pdm (choose one)
- **Virtual Environments:** venv, pyenv, or similar

## Project Structure

### Current State
```
networking-ai/
├── .gitignore          # Python-focused ignore patterns
├── LICENSE             # MIT License
├── README.md           # Project description
└── CLAUDE.md           # This file - AI assistant guide
```

### Recommended Structure (To Be Implemented)
```
networking-ai/
├── src/
│   └── networking_ai/     # Main application package
│       ├── __init__.py
│       ├── agents/        # AI agent implementations
│       ├── api/           # API endpoints
│       ├── core/          # Core business logic
│       ├── models/        # Data models
│       └── utils/         # Utility functions
├── tests/
│   ├── unit/              # Unit tests
│   ├── integration/       # Integration tests
│   └── conftest.py        # pytest fixtures
├── docs/                  # Documentation
├── scripts/               # Utility scripts
├── .env.example           # Environment variable template
├── pyproject.toml         # Project metadata & dependencies
├── README.md
├── CLAUDE.md
└── LICENSE
```

## Development Workflows

### Environment Setup
```bash
# Create virtual environment
python -m venv .venv
source .venv/bin/activate  # Linux/macOS
# .venv\Scripts\activate   # Windows

# Install dependencies (once pyproject.toml exists)
pip install -e ".[dev]"
```

### Code Quality Commands
```bash
# Linting with Ruff
ruff check .
ruff check --fix .

# Formatting with Ruff
ruff format .

# Type checking
mypy src/

# Run tests
pytest
pytest --cov=src/networking_ai  # with coverage
```

### Git Workflow
- Main branch: `main` (or as specified)
- Feature branches: `feature/<description>`
- Bug fix branches: `fix/<description>`
- AI assistant branches: `claude/<session-id>`

## Coding Conventions

### Python Style
- Follow PEP 8 style guidelines
- Use Ruff for linting and formatting
- Add type hints to all function signatures
- Maximum line length: 88 characters (Ruff/Black default)

### Naming Conventions
- **Modules/Packages:** lowercase with underscores (`my_module.py`)
- **Classes:** PascalCase (`MyClass`)
- **Functions/Variables:** snake_case (`my_function`, `my_variable`)
- **Constants:** UPPER_SNAKE_CASE (`MAX_CONNECTIONS`)
- **Private:** prefix with underscore (`_private_method`)

### Import Order
1. Standard library imports
2. Third-party imports
3. Local application imports

Use Ruff's isort functionality to auto-sort imports.

### Documentation
- Use docstrings for all public modules, classes, and functions
- Follow Google-style docstrings:
```python
def function_name(param1: str, param2: int) -> bool:
    """Short description of function.

    Longer description if needed.

    Args:
        param1: Description of param1.
        param2: Description of param2.

    Returns:
        Description of return value.

    Raises:
        ValueError: When invalid input is provided.
    """
```

## Testing Practices

### Test File Structure
- Test files should mirror source structure in `tests/`
- Name test files with `test_` prefix: `test_module.py`
- Name test functions with `test_` prefix: `test_function_name()`

### Test Guidelines
- Write unit tests for all business logic
- Use pytest fixtures for common test setup
- Aim for high coverage on critical paths
- Mock external services and APIs in tests

### Running Tests
```bash
# All tests
pytest

# Specific test file
pytest tests/unit/test_agents.py

# With verbose output
pytest -v

# With coverage report
pytest --cov=src/networking_ai --cov-report=html
```

## Environment Variables

Create a `.env` file (never commit) based on `.env.example`:
```bash
# Application
APP_ENV=development
DEBUG=true

# Database (if applicable)
DATABASE_URL=postgresql://user:pass@localhost:5432/networking_ai

# AI/ML Services
OPENAI_API_KEY=your_key_here
ANTHROPIC_API_KEY=your_key_here

# Other services
SECRET_KEY=your_secret_key
```

## Key Considerations for AI Assistants

### Do's
- Read existing code before making modifications
- Follow established patterns in the codebase
- Write tests for new functionality
- Use type hints consistently
- Keep changes focused and minimal
- Commit with clear, descriptive messages
- Check for existing similar implementations before creating new ones

### Don'ts
- Don't commit sensitive data (API keys, credentials)
- Don't create unnecessary files or over-engineer solutions
- Don't ignore existing code style/patterns
- Don't make changes without understanding context
- Don't skip writing tests for new features
- Don't add dependencies without clear justification

### Before Making Changes
1. Explore relevant parts of the codebase
2. Understand existing patterns and conventions
3. Check for similar existing implementations
4. Consider impact on other parts of the system

### Code Quality Checklist
- [ ] Code follows project style guidelines
- [ ] Type hints are included
- [ ] Tests are written/updated
- [ ] No hardcoded secrets or credentials
- [ ] Changes are focused and minimal
- [ ] Documentation updated if needed

## Project-Specific Notes

### AI Agent Architecture
When implementing AI agents:
- Keep agent logic modular and testable
- Use clear interfaces between components
- Handle API rate limits and errors gracefully
- Log agent decisions for debugging
- Consider token usage and costs

### Semantic Discovery
For semantic search/discovery features:
- Use embeddings for semantic matching
- Consider caching strategies for performance
- Handle edge cases (empty results, no matches)
- Provide fallback to keyword search when appropriate

## Common Issues & Solutions

### Virtual Environment Issues
```bash
# If venv is corrupted, recreate it
rm -rf .venv
python -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
```

### Import Errors
- Ensure virtual environment is activated
- Verify package is installed in editable mode (`pip install -e .`)
- Check `__init__.py` files exist in all packages

### Test Discovery Issues
- Ensure test files start with `test_`
- Check pytest is installed in the virtual environment
- Verify conftest.py is properly configured

## Quick Reference

| Task | Command |
|------|---------|
| Run tests | `pytest` |
| Lint code | `ruff check .` |
| Format code | `ruff format .` |
| Type check | `mypy src/` |
| Install deps | `pip install -e ".[dev]"` |
| Activate venv | `source .venv/bin/activate` |

---

*Last updated: 2026-01-27*
*Project status: Initial setup - awaiting implementation*
