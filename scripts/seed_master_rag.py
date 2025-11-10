#!/usr/bin/env python3
"""
Seed Master RAG Database.

Loads initial knowledge into Master AI RAG database:
- Recruiter training guides
- Conversation templates
- Initial behavioral patterns
"""

import sys
import os

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from networking_ai.master_ai import create_master_rag


def load_recruiter_training(rag_manager):
    """Load recruiter training guides."""
    print("\n" + "="*80)
    print("Loading Recruiter Training Guides")
    print("="*80)

    knowledge_base_dir = os.path.join(
        os.path.dirname(__file__),
        '..',
        'knowledge_base',
        'recruiter_training'
    )

    guides = [
        ("finance", "finance_sector.md"),
        ("tech", "tech_sector.md"),
    ]

    for industry, filename in guides:
        filepath = os.path.join(knowledge_base_dir, filename)

        if not os.path.exists(filepath):
            print(f"⚠️  File not found: {filepath}")
            continue

        with open(filepath, 'r') as f:
            content = f.read()

        rag_manager.add_recruiter_training(
            industry=industry,
            content=content,
            metadata={
                "source": filename,
                "version": "1.0"
            }
        )

        print(f"✓ Loaded {industry} sector guide ({len(content)} chars)")

    print(f"\n✓ Loaded {len(guides)} recruiter training guides")


def load_conversation_templates(rag_manager):
    """Load conversation templates."""
    print("\n" + "="*80)
    print("Loading Conversation Templates")
    print("="*80)

    templates = [
        {
            "template_id": "technical_interview_finance",
            "industry": "finance",
            "role": "system_engineer",
            "content": """
# Technical Interview Template - Finance Sector

## Opening
1. Review candidate's background in financial systems
2. Discuss mission-critical system experience
3. Ask about specific technologies (Avlog, trading platforms, etc.)

## Technical Deep Dive
1. Real-time systems architecture
2. Performance optimization techniques
3. Error handling and reliability
4. Security and compliance

## Behavioral
1. High-pressure situations
2. Team collaboration examples
3. Production incident handling

## Closing
1. Assess compensation expectations
2. Gauge interest level
3. Discuss next steps
"""
        },
        {
            "template_id": "technical_interview_tech",
            "industry": "tech",
            "role": "backend_engineer",
            "content": """
# Technical Interview Template - Tech Sector

## Opening
1. Discuss most impactful project
2. What technologies excite them
3. Problem-solving approach

## Technical Deep Dive
1. System design question
2. Scalability challenges
3. Trade-off discussions
4. Debugging complex issues

## Ownership & Collaboration
1. End-to-end project ownership
2. Cross-functional collaboration
3. Technical decision-making

## Closing
1. Career goals and motivations
2. Company stage preferences
3. Learning opportunities discussion
"""
        }
    ]

    for template in templates:
        rag_manager.add_conversation_template(
            template_id=template["template_id"],
            industry=template["industry"],
            role=template["role"],
            content=template["content"]
        )

        print(f"✓ Loaded template: {template['template_id']}")

    print(f"\n✓ Loaded {len(templates)} conversation templates")


def load_initial_patterns(rag_manager):
    """Load initial behavioral patterns (examples)."""
    print("\n" + "="*80)
    print("Loading Initial Behavioral Patterns")
    print("="*80)

    patterns = [
        {
            "user_segment": "system_engineer_finance_5yrs",
            "pattern_type": "company_stage_preference",
            "pattern_data": {
                "prefers": ["series_b", "series_c", "public"],
                "avoids": ["seed", "series_a"],
                "reasoning": "Finance professionals value stability"
            },
            "confidence": 0.75
        },
        {
            "user_segment": "backend_engineer_tech_3yrs",
            "pattern_type": "work_life_balance_priority",
            "pattern_data": {
                "priority_level": "high",
                "typical_preference": "flexible_hours_over_high_growth",
                "reasoning": "Mid-career engineers often prioritize balance"
            },
            "confidence": 0.65
        }
    ]

    for pattern in patterns:
        rag_manager.add_behavioral_pattern(
            user_segment=pattern["user_segment"],
            pattern_type=pattern["pattern_type"],
            pattern_data=pattern["pattern_data"],
            confidence=pattern["confidence"]
        )

        print(f"✓ Loaded pattern: {pattern['pattern_type']} for {pattern['user_segment']}")

    print(f"\n✓ Loaded {len(patterns)} initial behavioral patterns")


def main():
    """Main function."""
    print("\n" + "="*80)
    print("MASTER AI RAG DATABASE SEEDING")
    print("="*80)

    # Create RAG manager
    rag_manager = create_master_rag()

    # Load all knowledge
    load_recruiter_training(rag_manager)
    load_conversation_templates(rag_manager)
    load_initial_patterns(rag_manager)

    # Persist to disk
    print("\n" + "="*80)
    print("Persisting to Disk")
    print("="*80)
    rag_manager.persist()

    # Show stats
    print("\n" + "="*80)
    print("Master RAG Statistics")
    print("="*80)
    stats = rag_manager.get_stats()
    for collection, count in stats.items():
        print(f"  {collection}: {count} documents")

    print("\n" + "="*80)
    print("✅ Master RAG seeding complete!")
    print("="*80 + "\n")


if __name__ == "__main__":
    main()
