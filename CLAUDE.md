# CLAUDE.md

This file provides guidance for AI assistants working on the networking-ai codebase.

## Project Overview

**networking-ai** is an AI-native professional networking platform that connects people through intelligent agents and semantic discovery.

- **Language**: Python
- **License**: MIT (Copyright 2025 VR963)
- **Status**: Early-stage development

## Repository Structure

```
networking-ai/
├── .gitignore          # Python/Abstra-focused ignore rules
├── LICENSE             # MIT License
├── README.md           # Project description
└── CLAUDE.md           # This file
```

## Technology Stack

### Core Technologies
- **Python** - Primary programming language
- **Abstra** - AI-powered process automation framework (https://abstra.io/docs)

### Anticipated Frameworks (based on .gitignore)
- Flask or Django for web framework
- Jupyter Notebooks for experimentation
- Celery for task queues (optional)

### Development Tools
- **Ruff** - Python linter and formatter
- **mypy** - Static type checking
- **pytest** - Testing framework
- **uv/poetry/pip** - Package management

## Development Guidelines

### Code Style
- Follow PEP 8 conventions
- Use type hints for function signatures
- Run `ruff check` before committing
- Run `mypy` for type checking

### Testing
- Write tests using pytest
- Place tests in a `tests/` directory
- Name test files with `test_` prefix
- Aim for meaningful test coverage

### Environment Setup
```bash
# Create virtual environment
python -m venv .venv
source .venv/bin/activate  # Linux/macOS
# or
.venv\Scripts\activate     # Windows

# Install dependencies (when requirements exist)
pip install -r requirements.txt
# or with uv
uv pip install -r requirements.txt
```

### Common Commands
```bash
# Linting
ruff check .
ruff format .

# Type checking
mypy .

# Testing
pytest

# Run development server (when implemented)
python -m flask run  # if Flask
python manage.py runserver  # if Django
```

## File Conventions

### Python Files
- Use snake_case for modules and functions
- Use PascalCase for classes
- Group imports: stdlib, third-party, local

### Configuration Files to Create
When setting up the project, create:
- `pyproject.toml` - Project metadata and tool configuration
- `requirements.txt` or use pyproject.toml dependencies
- `.env.example` - Environment variable template (never commit `.env`)

## AI/ML Considerations

This project focuses on:
- **Intelligent agents** - Autonomous AI components for networking
- **Semantic discovery** - Meaning-based search and matching

When implementing AI features:
- Document model dependencies clearly
- Consider inference latency for user-facing features
- Implement proper error handling for AI service calls
- Store model configurations in version control

## Git Workflow

### Branch Naming
- Feature branches: `feature/<description>`
- Bug fixes: `fix/<description>`
- AI assistant branches: `claude/<session-id>`

### Commit Messages
- Use clear, descriptive messages
- Start with verb: "Add", "Fix", "Update", "Remove"
- Reference issues when applicable

### Files to Never Commit
- `.env` files with secrets
- API keys or credentials
- Large model files (use Git LFS or external storage)
- `__pycache__/` directories
- Virtual environment directories

## Security Notes

- Never hardcode API keys or secrets
- Use environment variables for configuration
- Validate all user inputs
- Sanitize data before database operations
- Review dependencies for vulnerabilities

## Future Architecture (Anticipated)

```
networking-ai/
├── src/
│   ├── agents/          # AI agent implementations
│   ├── api/             # REST/GraphQL endpoints
│   ├── core/            # Core business logic
│   ├── models/          # Data models
│   └── utils/           # Shared utilities
├── tests/
│   ├── unit/
│   └── integration/
├── docs/                # Documentation
├── scripts/             # Utility scripts
└── config/              # Configuration files
```

## Quick Reference

| Task | Command |
|------|---------|
| Lint code | `ruff check .` |
| Format code | `ruff format .` |
| Type check | `mypy .` |
| Run tests | `pytest` |
| Install deps | `pip install -r requirements.txt` |

## Resources

- [Abstra Documentation](https://abstra.io/docs)
- [Python PEP 8](https://peps.python.org/pep-0008/)
- [Ruff Documentation](https://docs.astral.sh/ruff/)
- [mypy Documentation](https://mypy.readthedocs.io/)
