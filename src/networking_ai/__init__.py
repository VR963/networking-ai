"""
Networking AI - AI-native professional networking platform.

This package provides intelligent agents and semantic discovery for
professional networking connections.
"""

__version__ = "0.2.0"
__author__ = "Networking AI Team"

from .core import UserProfile, NetworkingAgent
from .semantic import SemanticMatcher
from .ai_agent import AnthropicAgent
from .recommender import ConnectionRecommender, create_recommender
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
    "config",
]
