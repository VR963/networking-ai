"""
Master AI System.

Central intelligence that manages all personal agents, coordinates knowledge sharing,
and maintains the network knowledge base.
"""

from .rag_manager import MasterRAGManager, create_master_rag
# Phase 2:
# from .master_agent import MasterAgent
# from .knowledge_aggregator import KnowledgeAggregator

__all__ = [
    "MasterRAGManager",
    "create_master_rag",
    # "MasterAgent",  # Phase 2
    # "KnowledgeAggregator",  # Phase 2
]
