"""
AI Agents Package.

Specialized AI agents for the marketplace.
"""

# Optional imports - gracefully handle if LangChain not available
try:
    from .recruiter_agent import RecruiterAgent, create_recruiter_agent
    __all__ = [
        "RecruiterAgent",
        "create_recruiter_agent",
    ]
except ImportError as e:
    print(f"Warning: Recruiter agent not available: {e}")
    __all__ = []
