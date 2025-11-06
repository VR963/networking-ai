"""
Basic usage example for Networking AI.

This example demonstrates:
1. Creating user profiles
2. Using semantic matching
3. Finding connection recommendations
4. AI-powered profile analysis (requires API key)
"""

from networking_ai import (
    UserProfile,
    NetworkingAgent,
    ConnectionRecommender,
    create_recommender,
)


def main():
    """Run basic usage example."""
    print("=== Networking AI - Basic Usage Example ===\n")

    # Step 1: Create user profiles
    print("1. Creating user profiles...")

    alice = UserProfile(
        user_id="alice123",
        name="Alice Johnson",
        skills=["Python", "Machine Learning", "Data Science"],
        interests=["AI Research", "Deep Learning"],
        bio="ML Engineer passionate about AI applications",
        goals="Build innovative AI products that impact millions",
    )

    bob = UserProfile(
        user_id="bob456",
        name="Bob Smith",
        skills=["Python", "AI", "Neural Networks"],
        interests=["Computer Vision", "NLP"],
        bio="AI Researcher working on cutting-edge models",
        goals="Advance the field of artificial intelligence",
    )

    charlie = UserProfile(
        user_id="charlie789",
        name="Charlie Brown",
        skills=["JavaScript", "React", "Node.js"],
        interests=["Web Development", "Frontend"],
        bio="Full-stack developer focused on user experiences",
        goals="Create beautiful and functional web applications",
    )

    david = UserProfile(
        user_id="david101",
        name="David Lee",
        skills=["Python", "Data Engineering", "SQL"],
        interests=["Big Data", "Analytics"],
        bio="Data Engineer building scalable pipelines",
        goals="Enable data-driven decision making at scale",
    )

    print(f"✓ Created profiles for {alice.name}, {bob.name}, {charlie.name}, {david.name}\n")

    # Step 2: Use Networking Agent for discovery
    print("2. Using Networking Agent for connection discovery...")

    agent = NetworkingAgent(name="DiscoveryBot")
    candidates = [bob, charlie, david]

    connections = agent.discover_connections(
        alice.to_dict(),
        [c.to_dict() for c in candidates],
        top_n=3,
    )

    print(f"✓ Found {len(connections)} potential connections for Alice:\n")

    for i, conn in enumerate(connections, 1):
        profile = conn["profile"]
        scores = conn["scores"]
        print(f"   {i}. {profile['name']}")
        print(f"      Match Score: {scores['weighted_score']:.2f}")
        print(f"      Skills Match: {scores['skill_score']:.2f}")
        if "explanation" in conn:
            print(f"      Explanation: {conn['explanation']}")
        print()

    # Step 3: Use Connection Recommender
    print("3. Using Connection Recommender for advanced recommendations...")

    recommender = create_recommender()

    recommendations = recommender.recommend_connections(
        alice,
        candidates,
        top_n=2,
        include_explanations=False,  # Set to True if you have ANTHROPIC_API_KEY
        include_introductions=False,
    )

    print(f"✓ Generated {len(recommendations)} recommendations:\n")

    for rec in recommendations:
        print(f"   • {rec['name']} - {rec['match_strength'].upper()} match")
        print(f"     Score: {rec['match_scores']['weighted_score']:.2f}")
        if "explanation" in rec:
            print(f"     {rec['explanation']}")
        if "introduction" in rec:
            print(f"     Introduction: {rec['introduction']}")
        print()

    # Step 4: Skill-based matching
    print("4. Finding skill-specific matches...")

    skill_matches = recommender.find_skill_matches(
        alice,
        candidates,
        required_skills=["Python", "Data Science"],
        top_n=3,
    )

    print(f"✓ Found {len(skill_matches)} matches with Python & Data Science skills:\n")

    for match in skill_matches:
        print(f"   • {match['name']}")
        print(f"     Skill Match Score: {match['skill_score']:.2f}")
        print()

    # Step 5: Batch recommendations
    print("5. Generating batch recommendations...")

    all_users = [alice, bob]
    batch_results = recommender.batch_recommend(
        all_users,
        [charlie, david],
        top_n_per_user=2,
    )

    print("✓ Batch recommendations generated:\n")
    for user_id, recs in batch_results.items():
        user = next(u for u in all_users if u.user_id == user_id)
        print(f"   {user.name}:")
        for rec in recs:
            print(f"     → {rec['name']} ({rec['match_strength']})")
        print()

    print("=== Example Complete ===")


if __name__ == "__main__":
    # Note: To use AI features, set ANTHROPIC_API_KEY environment variable
    # export ANTHROPIC_API_KEY=your_api_key_here

    main()
