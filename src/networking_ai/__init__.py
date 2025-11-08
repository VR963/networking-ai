"""
Networking AI - AI-native professional networking platform.

This package provides intelligent agents, RAG systems, privacy-first
knowledge management, and anti-hallucination controls for professional
networking connections.
"""

__version__ = "0.4.0"
__author__ = "Networking AI Team"

# Lazy imports to avoid cryptography dependency at import time
def __getattr__(name):
    """Lazy load modules to avoid import errors."""
    if name == "UserProfile":
        from .core import UserProfile
        return UserProfile
    elif name == "NetworkingAgent":
        from .core import NetworkingAgent
        return NetworkingAgent
    elif name == "SemanticMatcher":
        from .semantic import SemanticMatcher
        return SemanticMatcher
    elif name == "AnthropicAgent":
        from .ai_agent import AnthropicAgent
        return AnthropicAgent
    elif name == "ConnectionRecommender":
        from .recommender import ConnectionRecommender
        return ConnectionRecommender
    elif name == "create_recommender":
        from .recommender import create_recommender
        return create_recommender
    elif name == "DualRAGSystem":
        from .rag_system import DualRAGSystem
        return DualRAGSystem
    elif name == "PublicKnowledgeBase":
        from .rag_system import PublicKnowledgeBase
        return PublicKnowledgeBase
    elif name == "PrivateUserVault":
        from .rag_system import PrivateUserVault
        return PrivateUserVault
    elif name == "KnowledgeLearningSystem":
        from .knowledge_learning import KnowledgeLearningSystem
        return KnowledgeLearningSystem
    elif name == "create_learning_system":
        from .knowledge_learning import create_learning_system
        return create_learning_system
    elif name == "OrchestratorAgent":
        from .multi_agent_system import OrchestratorAgent
        return OrchestratorAgent
    elif name == "create_multi_agent_system":
        from .multi_agent_system import create_multi_agent_system
        return create_multi_agent_system
    elif name == "ResponseValidator":
        from .anti_hallucination import ResponseValidator
        return ResponseValidator
    elif name == "GroundingEngine":
        from .anti_hallucination import GroundingEngine
        return GroundingEngine
    elif name == "create_anti_hallucination_system":
        from .anti_hallucination import create_anti_hallucination_system
        return create_anti_hallucination_system
    elif name == "FactCheckerAgent":
        from .fact_checker_agent import FactCheckerAgent
        return FactCheckerAgent
    elif name == "create_fact_checker":
        from .fact_checker_agent import create_fact_checker
        return create_fact_checker
    elif name == "TrainingArena":
        from .training_arena import TrainingArena
        return TrainingArena
    elif name == "create_training_arena":
        from .training_arena import create_training_arena
        return create_training_arena
    elif name == "config":
        from .config import config
        return config
    raise AttributeError(f"module '{__name__}' has no attribute '{name}'")

__all__ = [
    "__version__",
    "__author__",
    "UserProfile",
    "NetworkingAgent",
    "SemanticMatcher",
    "AnthropicAgent",
    "ConnectionRecommender",
    "create_recommender",
    "DualRAGSystem",
    "PublicKnowledgeBase",
    "PrivateUserVault",
    "KnowledgeLearningSystem",
    "create_learning_system",
    "OrchestratorAgent",
    "create_multi_agent_system",
    "ResponseValidator",
    "GroundingEngine",
    "create_anti_hallucination_system",
    "FactCheckerAgent",
    "create_fact_checker",
    "TrainingArena",
    "create_training_arena",
    "config",
]
