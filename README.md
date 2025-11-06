# Networking AI

[![Python Version](https://img.shields.io/badge/python-3.9+-blue.svg)](https://www.python.org/downloads/)
[![License](https://img.shields.io/badge/license-MIT-green.svg)](LICENSE)
[![Code style: black](https://img.shields.io/badge/code%20style-black-000000.svg)](https://github.com/psf/black)

AI-native professional networking platform with autonomous Master Agent system, multi-agent orchestration, privacy-first RAG, and anti-hallucination controls.

## Overview

Networking AI is a revolutionary platform that leverages cutting-edge artificial intelligence to create a fully autonomous professional networking ecosystem. At its core is a **Master Agent** (AI CEO) that monitors platform health, identifies opportunities, manages specialized sub-agents, and autonomously brings new users to the platform through AI-driven marketing campaigns.

### Key Features

#### Core Networking
- **Intelligent Agents**: AI-powered agents with specialized sub-agents (research, knowledge, security, testing, note taker)
- **Semantic Discovery**: Find professionals based on meaning using sentence transformers
- **Smart Matching**: Context-aware connection recommendations with AI explanations
- **Profile Analysis**: Deep understanding of skills, interests, and professional goals

#### Advanced AI System (Phase 3-5)
- **Master Agent (AI CEO)**: Supreme orchestrator that monitors, rewards, and manages the entire AI ecosystem
- **Autonomous Marketing**: AI Marketing Agent creates campaigns and brings new users autonomously
- **Master's Sub-Agents**:
  - Traffic Analyzer: Monitors platform traffic and predicts load
  - Audit Agent: Ensures compliance and tracks violations
  - Security Agent: Detects threats and prevents attacks
  - Performance Optimizer: Identifies bottlenecks and optimizes caching
  - R&D Agent: Researches innovations and competitive analysis
- **Multi-Agent System**: LangChain-powered orchestration with specialized agents
- **Dual RAG System**: Public knowledge base + password-protected private vaults
- **Knowledge Learning**: Learns from all interactions with deduplication (95% threshold)
- **Privacy-First**: Separate storage for personal data with encryption (Fernet)
- **Anti-Hallucination Controls**:
  - Grounding engine verifying claims against RAG
  - Hallucination detection with pattern matching
  - Response validation before user delivery
  - Fact-checker agent validating all outputs
  - Training arena for testing and teaching agents
- **Agent Governance**: Performance tracking, rewards, assistance for underperformers
- **Demand Analysis**: Identifies platform gaps and creates marketing campaigns
- **Admin Oversight**: Human administrator approves budgets and major decisions

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
│   └── networking_ai/              # Main package
│       ├── __init__.py             # Package exports
│       ├── config.py               # Configuration management
│       # Core Networking (Phase 1-2)
│       ├── core.py                 # Core classes (UserProfile, NetworkingAgent)
│       ├── semantic.py             # Semantic matching & embeddings
│       ├── ai_agent.py             # Anthropic Claude integration
│       ├── recommender.py          # Connection recommendation engine
│       # Multi-Agent System (Phase 3)
│       ├── rag_system.py           # Dual RAG (Public KB + Private Vault)
│       ├── knowledge_learning.py   # Knowledge learning with deduplication
│       ├── multi_agent_system.py   # LangChain orchestrator + sub-agents
│       # Anti-Hallucination (Phase 4)
│       ├── anti_hallucination.py   # Grounding engine & response validator
│       ├── fact_checker_agent.py   # Fact-checking agent for all outputs
│       ├── training_arena.py       # Training & testing environment
│       # Master Agent System (Phase 5)
│       ├── master_agent.py         # Master Agent (AI CEO) + governance
│       ├── marketing_agent.py      # Autonomous marketing campaigns
│       ├── master_sub_agents.py    # Traffic, Audit, Security, Perf, R&D
│       └── admin_interface.py      # Human admin control panel
├── tests/                          # Test suite (100+ tests)
│   ├── conftest.py                # Pytest fixtures
│   ├── test_core.py               # Core functionality tests
│   ├── test_semantic.py           # Semantic matching tests
│   ├── test_config.py             # Configuration tests
│   ├── test_recommender.py        # Recommender tests
│   ├── test_rag_system.py         # RAG system tests
│   ├── test_knowledge_learning.py # Knowledge learning tests
│   ├── test_multi_agent.py        # Multi-agent orchestration tests
│   ├── test_anti_hallucination.py # Anti-hallucination tests
│   └── test_training_arena.py     # Training arena tests
├── examples/                       # Usage examples
│   ├── basic_usage.py             # Basic networking example
│   ├── multi_agent_usage.py       # Multi-agent system demo
│   ├── anti_hallucination_demo.py # Anti-hallucination demo
│   └── master_agent_demo.py       # Complete Master Agent system demo
├── docs/                           # Documentation
│   └── architecture.md            # Architecture overview
├── data/                           # Data directory
│   └── chromadb/                  # ChromaDB vector storage
├── .github/
│   └── workflows/                 # CI/CD pipelines
│       ├── ci.yml                 # Continuous integration
│       ├── release.yml            # Release automation
│       └── codeql.yml             # Security scanning
├── pyproject.toml                 # Project configuration
├── requirements.txt               # Production dependencies
├── requirements-dev.txt           # Development dependencies
├── pytest.ini                     # Pytest configuration
├── .env.example                   # Environment variables template
└── README.md                      # This file
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

### Phase 1: Foundation (Completed ✅)
- [x] Project structure with proper packaging
- [x] Core classes (UserProfile, NetworkingAgent)
- [x] Testing infrastructure with pytest
- [x] CI/CD pipelines with GitHub Actions
- [x] Development tooling (black, ruff, mypy)

### Phase 2: Core AI Features (Completed ✅)
- [x] Semantic profile matching with sentence transformers (all-MiniLM-L6-v2)
- [x] Integration with Anthropic Claude (claude-3-5-sonnet-20241022)
- [x] Profile similarity scoring (skill-based and semantic)
- [x] Connection recommendation engine with batch processing
- [x] AI-generated introductions and explanations
- [x] Comprehensive test suite with 60+ tests

### Phase 3: Multi-Agent System & RAG (Completed ✅)
- [x] **Dual RAG System**: Public knowledge base + private encrypted vaults
- [x] **ChromaDB Integration**: Vector database for semantic search
- [x] **Knowledge Learning**: Learns from interactions with 95% deduplication
- [x] **Privacy-First Architecture**: Separate storage with password protection
- [x] **Multi-Agent Orchestration**: LangChain-powered agent coordination
- [x] **Specialized Sub-Agents**: Research, Matching, Security, Knowledge, Note Taker
- [x] **PII Detection**: Automatic detection and anonymization
- [x] **Account Lifecycle**: 12-month sleep mode, 24-month deletion

### Phase 4: Anti-Hallucination System (Completed ✅)
- [x] **Grounding Engine**: Verifies all claims against RAG (0.7 similarity threshold)
- [x] **Hallucination Detector**: Pattern matching for exaggerations and unsupported claims
- [x] **Response Validator**: Gatekeeper validating before user delivery
- [x] **Fact-Checker Agent**: Claude-powered validation of all agent outputs
- [x] **Confidence Scoring**: 5-level confidence system (Verified, High, Medium, Low, Uncertain)
- [x] **Training Arena**: Sandbox for testing and teaching agents
- [x] **Behavioral Constraints**: Ensures realistic, grounded conversations
- [x] **Source Attribution**: Requires evidence for factual claims

### Phase 5: Master Agent System (Completed ✅)
- [x] **Master Agent (AI CEO)**: Supreme orchestrator managing entire platform
- [x] **Agent Governance**: Performance tracking, warnings, suspensions
- [x] **Reward System**: Performance-based rewards for high-performing agents
- [x] **Demand Analyzer**: Identifies platform gaps and missing user types
- [x] **Marketing Agent**: Autonomous campaign creation and execution
- [x] **Multi-Channel Marketing**: LinkedIn, GitHub, Reddit, Twitter, Google Ads, etc.
- [x] **Campaign Management**: Design, launch, track, optimize, report
- [x] **Master's Sub-Agents**:
  - [x] Traffic Analyzer: Monitors traffic patterns and predicts load
  - [x] Audit Agent: Ensures compliance and tracks violations
  - [x] Security Agent: Detects threats and prevents attacks
  - [x] Performance Optimizer: Identifies bottlenecks and optimizes systems
  - [x] R&D Agent: Researches innovations and competitive analysis
- [x] **Admin Interface**: Human oversight for budgets and major decisions
- [x] **Budget Management**: Master requests funds with ROI justification
- [x] **Full Autonomy**: System operates independently with admin approval points

### Phase 6: API & Production (Next)
- [ ] RESTful API with FastAPI
- [ ] Database models with SQLAlchemy
- [ ] User authentication (JWT)
- [ ] API documentation with OpenAPI/Swagger
- [ ] Production deployment (Docker, Kubernetes)
- [ ] Monitoring and observability

### Phase 7: Advanced Features (Future)
- [ ] Real-time messaging with WebSockets
- [ ] Analytics dashboard for insights
- [ ] Mobile applications (iOS, Android)
- [ ] Integration with LinkedIn/GitHub APIs
- [ ] Video networking capabilities
- [ ] Advanced recommendation algorithms

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
