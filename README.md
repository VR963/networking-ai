# Networking AI

[![Python Version](https://img.shields.io/badge/python-3.9+-blue.svg)](https://www.python.org/downloads/)
[![License](https://img.shields.io/badge/license-MIT-green.svg)](LICENSE)
[![Code style: black](https://img.shields.io/badge/code%20style-black-000000.svg)](https://github.com/psf/black)

AI-native professional networking platform – connecting people through intelligent agents and semantic discovery.

## Overview

Networking AI is a modern platform that leverages artificial intelligence to revolutionize professional networking. Instead of manual searches and cold outreach, our intelligent agents analyze user profiles, skills, and goals to facilitate meaningful connections through semantic understanding.

### Key Features

- **Intelligent Agents**: AI-powered agents that understand context and facilitate connections
- **Semantic Discovery**: Find professionals based on meaning, not just keywords
- **Profile Analysis**: Deep understanding of skills, interests, and professional goals
- **Smart Matching**: Context-aware connection recommendations
- **Automated Outreach**: AI-assisted conversation starters and introductions

## Installation

### Prerequisites

- Python 3.9 or higher
- pip or uv package manager

### Basic Installation

```bash
# Clone the repository
git clone https://github.com/yourusername/networking-ai.git
cd networking-ai

# Create a virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# For development
pip install -r requirements-dev.txt

# Or install as a package
pip install -e .
```

### Using pyproject.toml

```bash
# Install with optional AI dependencies
pip install -e ".[ai]"

# Install with development dependencies
pip install -e ".[dev]"

# Install everything
pip install -e ".[dev,ai]"
```

## Quick Start

### Basic Setup

```bash
# Set your Anthropic API key (optional, for AI features)
export ANTHROPIC_API_KEY=your_api_key_here
```

### Example Usage

```python
from networking_ai import (
    UserProfile,
    NetworkingAgent,
    ConnectionRecommender,
)

# Create user profiles
alice = UserProfile(
    user_id="alice123",
    name="Alice Johnson",
    skills=["Python", "Machine Learning", "Data Science"],
    interests=["AI Research", "Deep Learning"],
    bio="ML Engineer passionate about AI",
    goals="Build innovative AI products"
)

bob = UserProfile(
    user_id="bob456",
    name="Bob Smith",
    skills=["Python", "AI", "Neural Networks"],
    interests=["Computer Vision", "NLP"],
)

# Use NetworkingAgent for discovery
agent = NetworkingAgent(name="ConnectorBot")
candidates = [bob]

connections = agent.discover_connections(
    alice.to_dict(),
    [c.to_dict() for c in candidates],
    top_n=5
)

# Use ConnectionRecommender for advanced matching
recommender = ConnectionRecommender()
recommendations = recommender.recommend_connections(
    alice,
    candidates,
    include_explanations=True,  # Requires API key
    include_introductions=True
)

for rec in recommendations:
    print(f"{rec['name']} - {rec['match_strength']} match")
    print(f"Score: {rec['match_scores']['weighted_score']:.2f}")
    if 'explanation' in rec:
        print(f"Why: {rec['explanation']}")
```

See [examples/basic_usage.py](examples/basic_usage.py) for a complete example.

## Project Structure

```
networking-ai/
├── src/
│   └── networking_ai/          # Main package
│       ├── __init__.py         # Package exports
│       ├── core.py             # Core classes (UserProfile, NetworkingAgent)
│       ├── semantic.py         # Semantic matching & embeddings
│       ├── ai_agent.py         # Anthropic Claude integration
│       ├── recommender.py      # Connection recommendation engine
│       └── config.py           # Configuration management
├── tests/                      # Test suite
│   ├── __init__.py
│   ├── conftest.py            # Pytest fixtures
│   ├── test_core.py           # Core functionality tests
│   ├── test_semantic.py       # Semantic matching tests
│   ├── test_config.py         # Configuration tests
│   └── test_recommender.py    # Recommender tests
├── examples/                   # Usage examples
│   └── basic_usage.py         # Complete usage example
├── docs/                       # Documentation
│   └── architecture.md        # Architecture overview
├── .github/
│   └── workflows/             # CI/CD pipelines
│       ├── ci.yml             # Continuous integration
│       ├── release.yml        # Release automation
│       └── codeql.yml         # Security scanning
├── pyproject.toml             # Project configuration
├── requirements.txt           # Production dependencies
├── requirements-dev.txt       # Development dependencies
├── pytest.ini                 # Pytest configuration
├── .env.example               # Environment variables template
└── README.md                  # This file
```

## Development

### Running Tests

```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=networking_ai

# Run specific test file
pytest tests/test_core.py

# Run specific test
pytest tests/test_core.py::TestUserProfile::test_user_profile_creation
```

### Code Quality

```bash
# Format code with black
black src/ tests/

# Lint with ruff
ruff check src/ tests/

# Type checking with mypy
mypy src/

# Run all checks
black src/ tests/ && ruff check src/ tests/ && mypy src/ && pytest
```

### Pre-commit Hooks

Install pre-commit hooks to automatically check code quality:

```bash
pre-commit install
```

## Architecture

The platform is built with modularity and scalability in mind:

- **Core Module**: Fundamental classes for users, profiles, and agents
- **AI Agents**: Specialized agents for different networking tasks
- **Discovery Engine**: Semantic search and matching algorithms
- **API Layer**: RESTful API built with FastAPI (coming soon)
- **Database**: SQLAlchemy ORM for data persistence (coming soon)

See [docs/architecture.md](docs/architecture.md) for detailed architecture documentation.

## Roadmap

### Phase 1: Foundation (Completed ✓)
- [x] Project structure
- [x] Core classes (UserProfile, NetworkingAgent)
- [x] Testing infrastructure
- [x] Development tooling

### Phase 2: Core Features (Completed ✓)
- [x] Semantic profile matching algorithm with sentence transformers
- [x] Integration with Anthropic Claude for AI-powered analysis
- [x] Profile similarity scoring (skill-based and semantic)
- [x] Connection recommendation engine with batch processing
- [x] AI-generated introductions and explanations
- [x] Comprehensive test suite

### Phase 3: API & Database (Current)
- [ ] RESTful API with FastAPI
- [ ] Database models and migrations
- [ ] User authentication
- [ ] API documentation

### Phase 4: Advanced Features
- [ ] Real-time messaging
- [ ] AI conversation assistance
- [ ] Analytics dashboard
- [ ] Integration with LinkedIn/other platforms
- [ ] Conversation starter suggestions
- [ ] Profile enrichment with external data

## Contributing

Contributions are welcome! Please follow these guidelines:

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Make your changes
4. Run tests and ensure they pass (`pytest`)
5. Format code (`black src/ tests/`)
6. Commit your changes (`git commit -m 'Add amazing feature'`)
7. Push to the branch (`git push origin feature/amazing-feature`)
8. Open a Pull Request

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## Contact

Project Link: [https://github.com/yourusername/networking-ai](https://github.com/yourusername/networking-ai)

## Acknowledgments

- Built with modern Python best practices
- Powered by AI/ML technologies
- Inspired by the future of professional networking
