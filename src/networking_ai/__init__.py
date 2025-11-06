"""
Networking AI - AI-native professional networking platform.

This package provides intelligent agents, RAG systems, and privacy-first
knowledge management for professional networking connections.
"""

__version__ = "0.3.0"
__author__ = "Networking AI Team"

from .core import UserProfile, NetworkingAgent
from .semantic import SemanticMatcher
from .ai_agent import AnthropicAgent
from .recommender import ConnectionRecommender, create_recommender
from .rag_system import DualRAGSystem, PublicKnowledgeBase, PrivateUserVault
from .knowledge_learning import KnowledgeLearningSystem, create_learning_system
from .multi_agent_system import OrchestratorAgent, create_multi_agent_system
from .config import config

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
    "config",
]
