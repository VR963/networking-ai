"""
Complete example of Multi-Agent System with RAG and Knowledge Learning.

This example demonstrates:
1. Dual RAG system (public knowledge + private vault)
2. Knowledge learning with deduplication
3. Multi-agent coordination
4. Privacy-preserving data handling
"""

from networking_ai import (
    DualRAGSystem,
    KnowledgeLearningSystem,
    OrchestratorAgent,
    create_multi_agent_system,
)


def main():
    """Run comprehensive multi-agent system example."""
    print("="*70)
    print("Networking AI - Multi-Agent System with RAG Example")
    print("="*70)
    print()

    # =================================================================
    # PART 1: Initialize the Dual RAG System
    # =================================================================
    print("1. Initializing Dual RAG System...")
    print("-" * 70)

    rag_system = DualRAGSystem(base_path="./example_data")

    # Add some public knowledge (no PII)
    print("\n   Adding public knowledge...")
    rag_system.add_public_knowledge(
        content="Python and Machine Learning skills are highly sought after in AI roles",
        metadata={"topic": "skills", "domain": "AI"}
    )

    rag_system.add_public_knowledge(
        content="Networking in tech industry often happens through conferences and online communities",
        metadata={"topic": "networking", "domain": "tech"}
    )

    # Add private user data (password-protected)
    print("   Adding private user data...")
    user_id = "alice_123"
    password = "secure_password"

    rag_system.add_private_data(
        user_id=user_id,
        password=password,
        content="Alice's personal goal: transition from data analyst to ML engineer within 2 years",
        metadata={"type": "goal", "privacy": "high"}
    )

    print("   ✓ RAG system initialized with public and private data")

    # Query public knowledge
    print("\n   Querying public knowledge...")
    results = rag_system.query_public("Python skills", n_results=2)
    for i, result in enumerate(results, 1):
        print(f"      {i}. {result['content'][:60]}...")

    # Query private data
    print("\n   Querying private data (requires authentication)...")
    private_results = rag_system.query_private(
        user_id, password, "career goals", n_results=2
    )
    for i, result in enumerate(private_results, 1):
        print(f"      {i}. {result['content'][:60]}...")

    print()

    # =================================================================
    # PART 2: Knowledge Learning with Deduplication
    # =================================================================
    print("\n2. Knowledge Learning System")
    print("-" * 70)

    learning_system = KnowledgeLearningSystem(rag_system=rag_system)

    # Simulate user interactions
    interactions = [
        {
            "question": "What skills are important for AI roles?",
            "answer": "Python, machine learning, and data science skills are crucial for AI positions.",
        },
        {
            "question": "What programming language is best for AI?",
            "answer": "Python is the most popular language for AI due to its extensive libraries.",
        },
        {
            "question": "What skills do I need for AI?",  # Similar to first - should deduplicate
            "answer": "You need Python and ML skills for AI work.",
        },
        {
            "question": "Tell me about my email address alice@example.com",  # Contains PII
            "answer": "I can help you with your profile.",
        },
    ]

    print("\n   Processing interactions...")
    for i, interaction in enumerate(interactions, 1):
        result = learning_system.process_interaction(
            question=interaction["question"],
            answer=interaction["answer"],
            user_id=user_id if "email" in interaction["question"] else None,
            user_password=password if "email" in interaction["question"] else None,
        )
        print(f"\n      Interaction {i}: {result['status']}")
        if result["status"] == "duplicate":
            print(f"         (Skipped - too similar to existing knowledge)")
        elif result["status"] == "pii_detected":
            print(f"         (Contains PII: {result.get('pii_detected', [])})")

    # Show statistics
    stats = learning_system.stats
    print(f"\n   Learning Statistics:")
    print(f"      Total interactions: {stats['total_interactions']}")
    print(f"      Learned: {stats['learned']}")
    print(f"      Duplicates skipped: {stats['duplicates_skipped']}")
    print(f"      Low quality skipped: {stats['low_quality_skipped']}")
    print(f"      PII detected: {stats['pii_detected']}")

    print()

    # =================================================================
    # PART 3: Multi-Agent System
    # =================================================================
    print("\n3. Multi-Agent Orchestrator")
    print("-" * 70)

    # Create orchestrator with all sub-agents
    print("\n   Initializing multi-agent system...")
    orchestrator = create_multi_agent_system(
        rag_system=rag_system,
        learning_system=learning_system
    )

    print("   ✓ Orchestrator initialized with sub-agents:")
    print("      - Research Agent")
    print("      - Matching Agent")
    print("      - Security Agent")
    print("      - Knowledge Agent")
    print("      - Note Taker Agent")

    # Example requests
    print("\n   Processing requests through orchestrator...")

    # Request 1: Research query
    print("\n   Request 1: Research about AI skills")
    print("   " + "-" * 66)
    result1 = orchestrator.process_request(
        "What skills are most valuable for AI professionals?",
        context={"domain": "AI"}
    )
    print(f"   Agents engaged: {', '.join(result1['agent_responses'].keys())}")
    print(f"   Response: {result1['final_response'][:100]}...")

    # Request 2: Profile matching
    print("\n   Request 2: Profile matching")
    print("   " + "-" * 66)
    result2 = orchestrator.process_request(
        "Find matches for a Python ML engineer",
        context={
            "user_profile": {
                "skills": ["Python", "Machine Learning"],
                "interests": ["AI", "Data Science"]
            }
        }
    )
    print(f"   Agents engaged: {', '.join(result2['agent_responses'].keys())}")
    print(f"   Response: {result2['final_response'][:100]}...")

    # Request 3: Security check
    print("\n   Request 3: Security/Privacy check")
    print("   " + "-" * 66)
    result3 = orchestrator.process_request(
        "Check this data for PII: My email is test@example.com",
        context={"user_data": True}
    )
    print(f"   Agents engaged: {', '.join(result3['agent_responses'].keys())}")
    print(f"   Response: {result3['final_response'][:100]}...")

    print()

    # =================================================================
    # PART 4: System Statistics
    # =================================================================
    print("\n4. System Statistics")
    print("-" * 70)

    rag_stats = rag_system.get_statistics()
    print(f"\n   Public Knowledge Base:")
    print(f"      Documents: {rag_stats['public_knowledge']['total_documents']}")

    print(f"\n   Private Vault:")
    print(f"      Collection: {rag_stats['private_vault']['collection_name']}")

    print(f"\n   Orchestrator:")
    print(f"      Total interactions: {len(orchestrator.get_interaction_history())}")

    print()
    print("="*70)
    print("Example Complete!")
    print("="*70)
    print()
    print("Key Features Demonstrated:")
    print("  ✓ Dual RAG system (public + private)")
    print("  ✓ Password-protected private data")
    print("  ✓ Semantic deduplication")
    print("  ✓ PII detection and handling")
    print("  ✓ Multi-agent coordination")
    print("  ✓ Sub-agent specialization")
    print("  ✓ Knowledge learning from interactions")
    print()
    print("Privacy Features:")
    print("  ✓ Encrypted storage for sensitive data")
    print("  ✓ User authentication required for private data")
    print("  ✓ Automatic PII detection")
    print("  ✓ Anonymization of public knowledge")
    print("  ✓ No sharing of personal data between users")
    print()


if __name__ == "__main__":
    # Note: Set ANTHROPIC_API_KEY environment variable to enable AI features
    # export ANTHROPIC_API_KEY=your_api_key_here

    try:
        main()
    except KeyboardInterrupt:
        print("\n\nExample interrupted by user.")
    except Exception as e:
        print(f"\n\nError: {e}")
        print("Make sure you have set ANTHROPIC_API_KEY environment variable.")
