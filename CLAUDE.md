# CLAUDE.md

## Project Overview

**networking-ai** is an AI-native professional networking platform that connects people through intelligent agents and semantic discovery. The project is licensed under MIT (Copyright 2025 VR963).

This repository is in its **early bootstrap phase** — foundational code and infrastructure are being built.

## Repository Structure

```
networking-ai/
├── .gitignore        # Python-focused ignore rules
├── LICENSE           # MIT License
├── README.md         # Project description
└── CLAUDE.md         # This file
```

## Technology Stack

**Language:** Python (inferred from .gitignore configuration)

**Intended tooling** (based on .gitignore entries):

| Category | Tools |
|---|---|
| Package management | pip, Poetry, PDM, UV, or Pipenv |
| Testing | pytest, tox, nox |
| Linting/Formatting | Ruff |
| Type checking | mypy, Pyre, or pytype |
| Documentation | Sphinx or MkDocs |
| Notebooks | Jupyter |

## Development Setup

No build configuration exists yet. When setup files are added, update this section. Expected setup:

```bash
# Create virtual environment
python -m venv .venv
source .venv/bin/activate

# Install dependencies (once pyproject.toml or requirements.txt exists)
pip install -e ".[dev]"
```

## Common Commands

These will be populated as the project matures:

```bash
# Testing (expected)
pytest

# Linting (expected)
ruff check .

# Formatting (expected)
ruff format .

# Type checking (expected)
mypy .
```

## Git Workflow

- **Default branch:** `master`
- **Branch naming:** Feature branches use descriptive names
- Write clear, concise commit messages describing the "why" not just the "what"

## Architecture Notes

The project aims to include:
- **Intelligent agents** for professional networking interactions
- **Semantic discovery** for connecting users based on meaning, not just keywords
- Likely involves embeddings, vector search, and LLM integration

## Conventions for AI Assistants

### General

- Read existing files before proposing changes
- Prefer editing existing files over creating new ones
- Keep changes minimal and focused on the task at hand
- Do not over-engineer; build only what is needed now

### Python Style (when code is added)

- Follow PEP 8 conventions
- Use type hints for function signatures
- Use Ruff for linting and formatting
- Prefer `pyproject.toml` for project configuration over `setup.py`/`setup.cfg`

### Testing

- Place tests in a `tests/` directory mirroring the source structure
- Use pytest conventions (functions prefixed with `test_`, fixtures, parametrize)
- Run the full test suite before committing changes

### Security

- Never commit secrets, API keys, or credentials
- Use environment variables (`.env` files are gitignored) for sensitive configuration
- Validate all external input at system boundaries

### Dependencies

- Pin dependency versions for reproducibility
- Keep lock files (poetry.lock, uv.lock, etc.) in version control for applications
- Separate dev dependencies from production dependencies
