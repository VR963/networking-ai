# CLAUDE.md

This file provides guidance for AI assistants working with the networking-ai codebase.

## Project Overview

**networking-ai** is an AI-native professional networking platform that connects people through intelligent agents and semantic discovery.

- **License**: MIT
- **Language**: Python
- **Status**: Early development / Initial setup

## Repository Structure

```
networking-ai/
├── .gitignore          # Python-focused gitignore
├── LICENSE             # MIT License
├── README.md           # Project description
└── CLAUDE.md           # This file - AI assistant guidance
```

## Development Environment

### Python Setup

This project uses Python. The `.gitignore` supports multiple Python environment tools:
- **venv/virtualenv**: Standard Python virtual environments
- **pipenv**: Pipfile-based dependency management
- **poetry**: Modern dependency management with pyproject.toml
- **uv**: Fast Python package installer
- **pdm**: Modern Python package manager
- **pixi**: Conda-compatible package manager

When setting up the project, look for:
1. `pyproject.toml` - Modern Python project configuration
2. `requirements.txt` - Pip requirements file
3. `Pipfile` - Pipenv configuration
4. `setup.py` / `setup.cfg` - Legacy packaging

### Environment Variables

- Never commit `.env` files (they are gitignored)
- Use `.env.example` or similar for documenting required environment variables
- Sensitive credentials should never be hardcoded

## Code Conventions

### Python Style

- Follow PEP 8 style guidelines
- Use type hints for function signatures
- Prefer descriptive variable and function names
- Keep functions focused and single-purpose

### File Organization (Anticipated)

As this is an AI-focused networking platform, expect future structure like:
```
networking-ai/
├── src/                    # Source code
│   ├── agents/             # AI agent implementations
│   ├── api/                # API endpoints
│   ├── models/             # Data models
│   └── services/           # Business logic
├── tests/                  # Test files
├── docs/                   # Documentation
└── scripts/                # Utility scripts
```

## AI Assistant Guidelines

### When Making Changes

1. **Read before modifying**: Always read files before suggesting changes
2. **Preserve existing patterns**: Match the coding style already in use
3. **Keep changes minimal**: Only modify what's necessary for the task
4. **Don't over-engineer**: Avoid adding unnecessary abstractions or features

### Security Considerations

- Never commit secrets, API keys, or credentials
- Validate user input at system boundaries
- Be cautious with external API integrations
- Review dependencies for known vulnerabilities

### Testing

- Write tests for new functionality
- Run existing tests before committing
- Look for `pytest`, `unittest`, or test configuration in `pyproject.toml`

### Documentation

- Update docstrings for public functions/classes
- Keep README.md current with setup instructions
- Document non-obvious design decisions in code comments

## Common Commands

Commands will vary based on the package manager chosen. Common patterns:

```bash
# Virtual environment (venv)
python -m venv .venv
source .venv/bin/activate  # Linux/macOS
.venv\Scripts\activate     # Windows

# Install dependencies
pip install -r requirements.txt
pip install -e .           # Editable install

# Run tests
pytest
python -m pytest

# Type checking (if configured)
mypy .
pyright

# Linting/Formatting (if configured)
ruff check .
ruff format .
black .
```

## Git Workflow

- Use descriptive commit messages
- Keep commits focused on single changes
- Branch names should be descriptive of the feature/fix
- Current main branch: check with `git branch -a`

## Notes for AI Assistants

1. **Project is new**: Limited existing code to reference
2. **Python-focused**: All tooling assumes Python development
3. **AI/ML likely**: Given the "AI-native" description, expect ML dependencies
4. **Networking domain**: Professional networking context for features

When the codebase grows, update this file with:
- Specific architecture patterns in use
- Build and deployment procedures
- API documentation references
- Testing conventions and coverage requirements
