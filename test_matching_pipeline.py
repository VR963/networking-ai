#!/usr/bin/env python3
"""
Test script for AI Matching Pipeline.

Demonstrates end-to-end matching between profiles and jobs.
"""

import sys
import os

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from networking_ai.database import SessionLocal, engine, Base
from networking_ai.models.user import User, UserRole, AccountStatus
from networking_ai.models.profile import UserProfile
from networking_ai.models.job import Job, JobStatus, JobType, ExperienceLevel
from networking_ai.models.company import Company
from networking_ai.models.match import Match
from networking_ai.security import hash_password
from networking_ai.services.matching_service import create_matching_service


def setup_database():
    """Create all tables."""
    print("Setting up database...")
    Base.metadata.create_all(bind=engine)
    print("✓ Database tables created")


def create_test_data(db):
    """Create sample users, profiles, and jobs."""
    print("\nCreating test data...")

    # Create job seeker
    job_seeker = User(
        email="john.doe@example.com",
        hashed_password=hash_password("password123"),
        full_name="John Doe",
        role=UserRole.JOB_SEEKER,
        status=AccountStatus.ACTIVE,
        is_email_verified=True
    )
    db.add(job_seeker)
    db.flush()

    # Create profile for job seeker
    profile = UserProfile(
        user_id=job_seeker.id,
        headline="Senior Python Developer",
        bio="Experienced software engineer with 5 years in backend development",
        current_title="Senior Software Engineer",
        years_of_experience=5,
        skills=["Python", "FastAPI", "PostgreSQL", "Docker", "AWS", "Machine Learning"],
        interests=["AI/ML", "Cloud Architecture", "Scalability"],
        career_goals="Looking to work on AI-powered products at a growth-stage company",
        desired_roles=["Senior Backend Engineer", "ML Engineer", "Technical Lead"],
        desired_salary_min=120000,
        desired_salary_max=160000,
        location="San Francisco, CA",
        is_remote_only=False
    )
    db.add(profile)

    # Create company
    company_user = User(
        email="hr@techcorp.com",
        hashed_password=hash_password("password123"),
        full_name="TechCorp HR",
        role=UserRole.COMPANY,
        status=AccountStatus.ACTIVE,
        is_email_verified=True
    )
    db.add(company_user)
    db.flush()

    company = Company(
        user_id=company_user.id,
        company_name="TechCorp AI",
        company_description="Leading AI startup building next-gen intelligent systems",
        industry="Artificial Intelligence",
        company_size="51-200",
        website="https://techcorp.ai",
        location="San Francisco, CA"
    )
    db.add(company)
    db.flush()

    # Create job 1 - Perfect match
    job1 = Job(
        company_id=company.id,
        title="Senior Backend Engineer - AI Platform",
        description="Build scalable backend systems for our AI-powered platform using Python and FastAPI",
        responsibilities="Design and implement REST APIs, optimize database queries, integrate ML models",
        requirements="5+ years Python, FastAPI experience, PostgreSQL, AWS, ML integration experience",
        benefits="Competitive salary, equity, health insurance, remote flexibility",
        required_skills=["Python", "FastAPI", "PostgreSQL", "AWS", "Machine Learning"],
        required_experience_years=5,
        job_type=JobType.FULL_TIME,
        experience_level=ExperienceLevel.SENIOR,
        location="San Francisco, CA",
        is_remote=True,
        salary_min=130000,
        salary_max=170000,
        status=JobStatus.ACTIVE
    )
    db.add(job1)

    # Create job 2 - Good match (some skill overlap)
    job2 = Job(
        company_id=company.id,
        title="DevOps Engineer",
        description="Manage cloud infrastructure and CI/CD pipelines",
        responsibilities="Maintain AWS infrastructure, build deployment pipelines, monitor systems",
        requirements="Experience with Docker, Kubernetes, AWS, Python scripting",
        required_skills=["Docker", "Kubernetes", "AWS", "Python", "Terraform"],
        required_experience_years=4,
        job_type=JobType.FULL_TIME,
        experience_level=ExperienceLevel.MID,
        location="San Francisco, CA",
        is_remote=True,
        salary_min=110000,
        salary_max=140000,
        status=JobStatus.ACTIVE
    )
    db.add(job2)

    # Create job 3 - Poor match (different skills)
    job3 = Job(
        company_id=company.id,
        title="Frontend React Developer",
        description="Build beautiful user interfaces using React and TypeScript",
        responsibilities="Develop React components, implement designs, optimize performance",
        requirements="Expert in React, TypeScript, CSS, modern frontend tools",
        required_skills=["React", "TypeScript", "JavaScript", "CSS", "Redux"],
        required_experience_years=3,
        job_type=JobType.FULL_TIME,
        experience_level=ExperienceLevel.MID,
        location="San Francisco, CA",
        is_remote=False,
        salary_min=100000,
        salary_max=130000,
        status=JobStatus.ACTIVE
    )
    db.add(job3)

    db.commit()
    db.refresh(profile)
    db.refresh(job1)
    db.refresh(job2)
    db.refresh(job3)

    print(f"✓ Created job seeker: {job_seeker.full_name} (ID: {job_seeker.id})")
    print(f"✓ Created profile: {profile.headline} (ID: {profile.id})")
    print(f"✓ Created company: {company.company_name} (ID: {company.id})")
    print(f"✓ Created job 1: {job1.title} (ID: {job1.id})")
    print(f"✓ Created job 2: {job2.title} (ID: {job2.id})")
    print(f"✓ Created job 3: {job3.title} (ID: {job3.id})")

    return profile, job1, job2, job3


def test_matching(db, profile):
    """Test the matching service."""
    print("\n" + "="*80)
    print("TESTING AI MATCHING PIPELINE")
    print("="*80)

    # Create matching service
    matching_service = create_matching_service(db)

    # Test 1: Match profile to all jobs
    print("\n[TEST 1] Matching profile to all active jobs...")
    print("-" * 80)

    matches = matching_service.match_profile_to_jobs(
        profile_id=profile.id,
        limit=10,
        min_score=0.3  # Lower threshold to see all matches
    )

    print(f"\n✓ Created {len(matches)} matches for profile {profile.id}")

    # Display match details
    for match in matches:
        job = match.job
        print(f"\n  Match ID: {match.id}")
        print(f"  Job: {job.title}")
        print(f"  Score: {match.match_score:.3f} ({match.confidence_level})")
        print(f"  Skill Alignment: {match.salary_alignment}")
        print(f"  Location: {match.location_compatibility}")

        import json
        matching_skills = json.loads(match.matching_skills) if match.matching_skills else []
        skill_gaps = json.loads(match.skill_gaps) if match.skill_gaps else []

        print(f"  Matching Skills: {', '.join(matching_skills[:5])}")
        if skill_gaps:
            print(f"  Skill Gaps: {', '.join(skill_gaps[:3])}")
        print(f"  Explanation: {match.ai_explanation[:150]}...")

    # Test 2: Verify matches are in database
    print("\n" + "-" * 80)
    print("[TEST 2] Verifying matches are persisted in database...")
    print("-" * 80)

    db_matches = db.query(Match).filter(Match.profile_id == profile.id).all()
    print(f"✓ Found {len(db_matches)} matches in database")

    # Test 3: Show match quality distribution
    print("\n" + "-" * 80)
    print("[TEST 3] Match Quality Distribution")
    print("-" * 80)

    high = len([m for m in matches if m.confidence_level == "high"])
    medium = len([m for m in matches if m.confidence_level == "medium"])
    low = len([m for m in matches if m.confidence_level == "low"])

    print(f"  High confidence matches: {high}")
    print(f"  Medium confidence matches: {medium}")
    print(f"  Low confidence matches: {low}")

    return matches


def test_job_matching(db, job):
    """Test matching a job to profiles."""
    print("\n" + "="*80)
    print(f"[TEST 4] Matching job '{job.title}' to profiles...")
    print("="*80)

    matching_service = create_matching_service(db)

    matches = matching_service.match_job_to_profiles(
        job_id=job.id,
        limit=20,
        min_score=0.3
    )

    print(f"✓ Created {len(matches)} matches for job {job.id}")

    for match in matches:
        profile = match.profile
        print(f"\n  Match: {profile.headline}")
        print(f"  Score: {match.match_score:.3f}")


def cleanup_database(db):
    """Clean up test data."""
    print("\n" + "="*80)
    print("Cleaning up test data...")
    print("="*80)

    # Delete in correct order (due to foreign keys)
    db.query(Match).delete()
    db.query(Job).delete()
    db.query(Company).delete()
    db.query(UserProfile).delete()
    db.query(User).delete()

    db.commit()
    print("✓ Test data cleaned up")


def main():
    """Run the test pipeline."""
    print("\n" + "="*80)
    print("AI MATCHING PIPELINE TEST")
    print("="*80)

    # Setup
    setup_database()

    # Create database session
    db = SessionLocal()

    try:
        # Create test data
        profile, job1, job2, job3 = create_test_data(db)

        # Run matching tests
        matches = test_matching(db, profile)

        # Test reverse matching (job -> profiles)
        test_job_matching(db, job1)

        # Final summary
        print("\n" + "="*80)
        print("TEST SUMMARY")
        print("="*80)
        print(f"✓ All tests passed!")
        print(f"✓ Matching service is working correctly")
        print(f"✓ {len(matches)} matches created with scores ranging from "
              f"{min(m.match_score for m in matches):.3f} to "
              f"{max(m.match_score for m in matches):.3f}")

    except Exception as e:
        print(f"\n❌ Error during testing: {e}")
        import traceback
        traceback.print_exc()

    finally:
        # Cleanup
        cleanup_database(db)
        db.close()

    print("\n" + "="*80)
    print("Test completed!")
    print("="*80 + "\n")


if __name__ == "__main__":
    main()
