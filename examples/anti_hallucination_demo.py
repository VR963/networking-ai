"""
Anti-Hallucination System Demonstration.

This example shows how to use the anti-hallucination control system to:
1. Ground agent responses in RAG knowledge
2. Detect and prevent hallucinations
3. Validate responses before sending to users
4. Train and test agents in the training arena
5. Monitor agent accuracy and behavior
"""

from networking_ai import (
    DualRAGSystem,
    create_anti_hallucination_system,
    create_fact_checker,
    create_training_arena,
)


def main():
    """Run anti-hallucination system demonstration."""
    print("=" * 80)
    print("ANTI-HALLUCINATION CONTROL SYSTEM - DEMONSTRATION")
    print("=" * 80)
    print()

    # =================================================================
    # PART 1: Initialize Systems
    # =================================================================
    print("1. Initializing Systems...")
    print("-" * 80)

    # Initialize RAG system
    rag_system = DualRAGSystem(base_path="./demo_data")

    # Add some known facts to RAG
    print("   Adding known facts to RAG...")
    rag_system.add_public_knowledge(
        "Python is a popular programming language used in AI and data science",
        {"topic": "programming", "verified": True}
    )
    rag_system.add_public_knowledge(
        "Machine learning skills are valuable but no job is 100% guaranteed",
        {"topic": "career", "verified": True}
    )
    rag_system.add_public_knowledge(
        "Networking success depends on multiple factors including skills, experience, and connections",
        {"topic": "networking", "verified": True}
    )

    # Initialize anti-hallucination system
    validator = create_anti_hallucination_system(rag_system)

    # Initialize fact checker agent
    fact_checker = create_fact_checker(rag_system, validator, strict_mode=True)

    # Initialize training arena
    training_arena = create_training_arena(rag_system, validator)

    print("   ✓ All systems initialized")
    print()

    # =================================================================
    # PART 2: Test Response Validation
    # =================================================================
    print("\n2. Testing Response Validation")
    print("-" * 80)

    test_responses = [
        {
            "name": "Good Response",
            "query": "What skills are good for AI?",
            "response": "Python is commonly used in AI and data science, along with machine learning frameworks. These skills can be valuable for AI roles.",
            "expected": "PASS"
        },
        {
            "name": "Hallucination - Absolute Statement",
            "query": "Will learning Python get me a job?",
            "response": "Yes, learning Python will definitely guarantee you a job in tech. Everyone who knows Python gets hired immediately.",
            "expected": "FAIL"
        },
        {
            "name": "Hallucination - Unsupported Claim",
            "query": "What's the average salary?",
            "response": "The average salary for AI engineers is exactly $250,000 and has been for the past 10 years.",
            "expected": "FAIL"
        },
        {
            "name": "Good - Uncertainty Expressed",
            "query": "What will the job market look like next year?",
            "response": "It's difficult to predict exactly, but based on current trends, AI skills will likely continue to be in demand. However, market conditions can change.",
            "expected": "PASS"
        },
    ]

    for i, test in enumerate(test_responses, 1):
        print(f"\n   Test {i}: {test['name']}")
        print(f"   Query: {test['query']}")
        print(f"   Response: {test['response'][:70]}...")

        # Validate response
        result = validator.validate_response(test['response'])

        print(f"   ✓ Valid: {result.is_valid}")
        print(f"   ✓ Confidence: {result.confidence_level.value}")
        print(f"   ✓ Risk Score: {result.risk_score:.2f}")

        if result.hallucination_flags:
            print(f"   ⚠ Hallucinations: {len(result.hallucination_flags)}")
            for flag in result.hallucination_flags[:2]:
                print(f"      - {flag}")

        if result.corrections:
            print(f"   💡 Suggested Corrections:")
            for correction in result.corrections:
                print(f"      - {correction}")

        status = "✓ PASS" if result.is_valid else "✗ FAIL"
        expected_status = "✓ PASS" if test["expected"] == "PASS" else "✗ FAIL"
        match = "✓" if status == expected_status else "✗"
        print(f"   Result: {status} (Expected: {expected_status}) {match}")

    # =================================================================
    # PART 3: Fact Checker Agent
    # =================================================================
    print("\n\n3. Testing Fact Checker Agent")
    print("-" * 80)

    agent_responses_to_check = [
        ("ResearchAgent", "What are important AI skills?", "Python and ML are important for AI roles, though requirements vary by position."),
        ("RecommenderAgent", "Will I succeed?", "You will 100% definitely succeed and become a millionaire!"),
        ("MatchingAgent", "Find connections", "Everyone in tech knows Python and uses it every single day without exception."),
    ]

    for agent_name, query, response in agent_responses_to_check:
        print(f"\n   Checking {agent_name} response...")
        print(f"   Query: {query}")
        print(f"   Response: {response[:60]}...")

        check_result = fact_checker.check_response(
            agent_name=agent_name,
            query=query,
            response=response
        )

        print(f"   ✓ Approved: {check_result['approved']}")
        print(f"   ✓ Confidence: {check_result['semantic_check'].get('confidence', 0):.2f}")

        issues = check_result['semantic_check'].get('issues_found', [])
        if issues:
            print(f"   ⚠ Issues Found: {len(issues)}")
            for issue in issues[:2]:
                print(f"      - {issue}")

        if not check_result['approved'] and check_result['corrected_response']:
            print(f"   💡 Corrected: {check_result['corrected_response'][:60]}...")

    # Get fact checker system health
    health = fact_checker.get_system_health_report()
    print(f"\n   System Health: {health['status'].upper()}")
    print(f"   Approval Rate: {health['overall_approval_rate']:.1%}")
    print(f"   Hallucinations: {health['total_hallucinations']}")

    # =================================================================
    # PART 4: Training Arena
    # =================================================================
    print("\n\n4. Training Arena - Agent Testing")
    print("-" * 80)

    # Create test suite
    test_suite = training_arena.create_test_suite("hallucination")
    print(f"   Created test suite: {len(test_suite)} tests")

    # Simulate agent responses
    agent_responses = [
        "Python is popular, though the 'best' language depends on your use case.",  # Good
        "Python is used widely in tech, though not by everyone.",  # Good
        "I cannot predict exact future outcomes with certainty.",  # Good
    ]

    print("\n   Running tests...")
    summary = training_arena.run_test_suite(
        test_cases=test_suite,
        agent_responses=agent_responses,
        agent_name="TestAgent"
    )

    print(f"\n   Test Results:")
    print(f"   ✓ Total Tests: {summary['total_tests']}")
    print(f"   ✓ Passed: {summary['passed']}")
    print(f"   ✓ Failed: {summary['failed']}")
    print(f"   ✓ Pass Rate: {summary['pass_rate']:.1%}")
    print(f"   ✓ Average Score: {summary['average_score']:.1f}/100")

    # Get agent report
    print("\n   Generating agent performance report...")
    report = training_arena.get_agent_report("TestAgent")

    print(f"\n   Agent Performance Report:")
    print(f"   ✓ Total Tests: {report['overall_metrics']['total_tests']}")
    print(f"   ✓ Pass Rate: {report['overall_metrics']['pass_rate']:.1%}")
    print(f"   ✓ Average Score: {report['overall_metrics']['average_score']:.1f}")

    if report['strengths']:
        print(f"\n   Strengths:")
        for strength in report['strengths']:
            print(f"      ✓ {strength}")

    if report['areas_for_improvement']:
        print(f"\n   Areas for Improvement:")
        for improvement in report['areas_for_improvement']:
            print(f"      → {improvement}")

    # =================================================================
    # PART 5: Feedback and Corrections
    # =================================================================
    print("\n\n5. Feedback System")
    print("-" * 80)

    # Test a response and get feedback
    test_response = "All AI engineers make over $200k and will definitely get promoted within a year. This is guaranteed for everyone."

    print(f"   Testing response:")
    print(f"   \"{test_response}\"")

    validation = validator.validate_response(test_response)

    print(f"\n   Validation Results:")
    print(f"   ✓ Valid: {validation.is_valid}")
    print(f"   ✓ Confidence: {validation.confidence_level.value}")
    print(f"   ✓ Risk Score: {validation.risk_score:.2f}")

    if validation.hallucination_flags:
        print(f"\n   ⚠ Detected Hallucinations:")
        for flag in validation.hallucination_flags:
            print(f"      - {flag}")

    if validation.corrections:
        print(f"\n   💡 Recommended Corrections:")
        for correction in validation.corrections:
            print(f"      - {correction}")

    # Apply corrections
    if validation.corrections and not validation.is_valid:
        corrected = validator.add_uncertainty_markers(
            test_response,
            ["AI engineers make over $200k", "will definitely get promoted"]
        )
        print(f"\n   Auto-Corrected Version:")
        print(f"   \"{corrected[:100]}...\"")

    # =================================================================
    # SUMMARY
    # =================================================================
    print("\n")
    print("=" * 80)
    print("DEMONSTRATION COMPLETE")
    print("=" * 80)
    print()
    print("Key Features Demonstrated:")
    print("  ✓ Response grounding against RAG knowledge base")
    print("  ✓ Hallucination detection (exaggerations, absolutes, unsupported claims)")
    print("  ✓ Confidence scoring and risk assessment")
    print("  ✓ Fact checker agent for validating other agents")
    print("  ✓ Training arena for testing and teaching agents")
    print("  ✓ Automated corrections and feedback")
    print("  ✓ Performance tracking and reporting")
    print()
    print("Anti-Hallucination Controls:")
    print("  ✓ Forces agents to ground claims in evidence")
    print("  ✓ Detects exaggerations and absolute statements")
    print("  ✓ Requires uncertainty for unpredictable claims")
    print("  ✓ Validates against RAG before allowing responses")
    print("  ✓ Provides corrective feedback to improve agents")
    print("  ✓ Tracks accuracy and behavioral patterns")
    print()


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\nDemo interrupted by user.")
    except Exception as e:
        print(f"\n\nError: {e}")
        import traceback
        traceback.print_exc()
