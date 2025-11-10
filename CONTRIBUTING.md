# Contributing to Networking AI

Thank you for your interest in contributing to Networking AI! This document provides guidelines and instructions for contributing.

## Code of Conduct

By participating in this project, you agree to maintain a respectful and inclusive environment for all contributors.

## How to Contribute

### Reporting Bugs

Before creating bug reports, please check existing issues. When creating a bug report, include:

- Clear and descriptive title
- Steps to reproduce the issue
- Expected behavior
- Actual behavior
- Environment details (OS, Python version, etc.)

### Suggesting Enhancements

Enhancement suggestions are welcome! Please provide:

- Clear and descriptive title
- Detailed description of the proposed feature
- Use cases and benefits
- Any implementation considerations

### Pull Requests

1. **Fork the repository** and create your branch from `main`
2. **Make your changes** following our coding standards
3. **Add tests** for any new functionality
4. **Update documentation** as needed
5. **Ensure tests pass** (`pytest`)
6. **Lint your code** (`black`, `ruff`, `mypy`)
7. **Write clear commit messages**
8. **Submit the pull request**

## Development Setup

```bash
# Clone your fork
git clone https://github.com/yourusername/networking-ai.git
cd networking-ai

# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install development dependencies
pip install -r requirements-dev.txt

# Install pre-commit hooks
pre-commit install
```

## Coding Standards

### Python Style

- Follow PEP 8 guidelines
- Use type hints for function signatures
- Write docstrings for all public functions and classes
- Maximum line length: 88 characters (Black default)

### Code Formatting

We use automated tools for code formatting:

```bash
# Format code
black src/ tests/

# Check linting
ruff check src/ tests/

# Type checking
mypy src/
```

### Documentation

- Use Google-style docstrings
- Include examples in docstrings when helpful
- Update README.md for user-facing changes
- Add architecture notes to docs/ for significant features

Example docstring:

```python
def discover_connections(user_profile: dict) -> list:
    """
    Discover potential connections based on user profile.

    This function uses semantic analysis to find professionals
    with complementary skills and interests.

    Args:
        user_profile: Dictionary containing user information including
            'user_id', 'name', and 'skills' keys.

    Returns:
        List of potential connections, each represented as a dictionary
        with user information and match score.

    Example:
        >>> profile = {'user_id': '123', 'name': 'John', 'skills': ['Python']}
        >>> connections = discover_connections(profile)
        >>> len(connections) > 0
        True
    """
    # Implementation here
    pass
```

## Testing

### Writing Tests

- Place tests in the `tests/` directory
- Mirror the source structure
- Use descriptive test names
- Include unit tests for all new functions
- Add integration tests for new features

Example test structure:

```python
class TestUserProfile:
    """Test cases for UserProfile class."""

    def test_user_profile_creation(self):
        """Test creating a user profile with valid data."""
        profile = UserProfile(user_id="123", name="John")
        assert profile.user_id == "123"

    def test_user_profile_invalid_data(self):
        """Test that invalid data raises appropriate errors."""
        with pytest.raises(ValueError):
            UserProfile(user_id="", name="John")
```

### Running Tests

```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=networking_ai

# Run specific test file
pytest tests/test_core.py

# Run tests matching pattern
pytest -k "test_user"
```

## Commit Messages

Follow conventional commits format:

```
type(scope): subject

body

footer
```

Types:
- `feat`: New feature
- `fix`: Bug fix
- `docs`: Documentation changes
- `style`: Code style changes (formatting, etc.)
- `refactor`: Code refactoring
- `test`: Adding or updating tests
- `chore`: Maintenance tasks

Example:

```
feat(core): add semantic matching algorithm

Implement initial version of semantic profile matching using
sentence transformers for skill similarity comparison.

Closes #42
```

## Review Process

1. All submissions require review
2. Maintainers will review within 1 week
3. Address review feedback promptly
4. CI checks must pass before merging
5. At least one approval required for merge

## Getting Help

- Create an issue for questions
- Join our discussions
- Contact maintainers

## License

By contributing, you agree that your contributions will be licensed under the MIT License.
