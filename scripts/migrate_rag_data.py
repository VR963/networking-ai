"""
RAG Data Migration Script.

Populates ChromaDB RAG collections from existing interview data.

Usage:
    python scripts/migrate_rag_data.py --type all
    python scripts/migrate_rag_data.py --type talent
    python scripts/migrate_rag_data.py --type hm
    python scripts/migrate_rag_data.py --type jobs
"""

import sys
import os
import argparse
from datetime import datetime

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from networking_ai.database import get_db_url
from networking_ai.models.user import User
from networking_ai.models.personal_ai_agent import PersonalAIAgent, AgentType, AgentStatus
from networking_ai.models.interview_session import InterviewSession, InterviewStatus
from networking_ai.models.job import Job, JobStatus
from networking_ai.services.chromadb_service import create_chromadb_service


class RAGMigration:
    """RAG data migration manager."""

    def __init__(self, db_url: str = None):
        """Initialize migration."""
        self.db_url = db_url or get_db_url()
        self.engine = create_engine(self.db_url)
        self.SessionLocal = sessionmaker(bind=self.engine)

        try:
            self.chromadb_service = create_chromadb_service()
            self.chromadb_available = True
            print("[MIGRATION] ChromaDB service initialized")
        except ImportError:
            self.chromadb_service = None
            self.chromadb_available = False
            print("[MIGRATION] ChromaDB not available - migration skipped")

    def migrate_talent_rags(self) -> Dict:
        """
        Migrate Talent Personal Agent RAG collections.

        Finds all Talent agents without RAG collections and populates them
        from their interview session data.
        """
        if not self.chromadb_available:
            return {"status": "skipped", "reason": "ChromaDB not available"}

        db = self.SessionLocal()
        results = {
            "total_agents": 0,
            "migrated": 0,
            "skipped": 0,
            "errors": 0,
            "error_details": []
        }

        try:
            # Get all Talent agents without RAG collections
            talent_agents = db.query(PersonalAIAgent).filter(
                PersonalAIAgent.agent_type == AgentType.TALENT,
                PersonalAIAgent.status == AgentStatus.ACTIVE
            ).all()

            results["total_agents"] = len(talent_agents)
            print(f"\n[MIGRATION] Found {len(talent_agents)} Talent agents")

            for agent in talent_agents:
                try:
                    # Check if RAG already exists
                    if agent.rag_collection_id:
                        print(f"  ⊙ Agent {agent.id}: Already has RAG collection '{agent.rag_collection_id}'")
                        results["skipped"] += 1
                        continue

                    # Find interview session for this user
                    interview_session = db.query(InterviewSession).filter(
                        InterviewSession.user_id == agent.user_id,
                        InterviewSession.status == InterviewStatus.COMPLETED
                    ).order_by(InterviewSession.created_at.desc()).first()

                    if not interview_session:
                        print(f"  ⊙ Agent {agent.id}: No completed interview found")
                        results["skipped"] += 1
                        continue

                    # Create RAG collection
                    collection_name = self.chromadb_service.create_talent_rag(
                        agent_id=agent.id,
                        user_id=agent.user_id
                    )

                    # Populate RAG
                    interview_data = interview_session.knowledge_extracted or {}
                    cv_data = interview_session.cv_parsed_data or {}

                    if interview_data or cv_data:
                        self.chromadb_service.populate_talent_rag(
                            collection_name=collection_name,
                            interview_data=interview_data,
                            cv_data=cv_data
                        )

                        # Update agent
                        agent.rag_collection_id = collection_name
                        db.commit()

                        print(f"  ✓ Agent {agent.id}: Created and populated RAG '{collection_name}'")
                        results["migrated"] += 1
                    else:
                        print(f"  ⊙ Agent {agent.id}: No interview data to migrate")
                        results["skipped"] += 1

                except Exception as e:
                    print(f"  ✗ Agent {agent.id}: Error - {e}")
                    results["errors"] += 1
                    results["error_details"].append({
                        "agent_id": agent.id,
                        "error": str(e)
                    })
                    db.rollback()

        finally:
            db.close()

        return results

    def migrate_hm_rags(self) -> Dict:
        """
        Migrate HM Personal Agent RAG collections.

        Finds all HM agents without RAG collections and populates them
        from their interview session data.
        """
        if not self.chromadb_available:
            return {"status": "skipped", "reason": "ChromaDB not available"}

        db = self.SessionLocal()
        results = {
            "total_agents": 0,
            "migrated": 0,
            "skipped": 0,
            "errors": 0,
            "error_details": []
        }

        try:
            # Get all HM agents without RAG collections
            hm_agents = db.query(PersonalAIAgent).filter(
                PersonalAIAgent.agent_type == AgentType.HIRING_MANAGER,
                PersonalAIAgent.status == AgentStatus.ACTIVE
            ).all()

            results["total_agents"] = len(hm_agents)
            print(f"\n[MIGRATION] Found {len(hm_agents)} HM agents")

            for agent in hm_agents:
                try:
                    # Check if RAG already exists
                    if agent.rag_collection_id:
                        print(f"  ⊙ Agent {agent.id}: Already has RAG collection '{agent.rag_collection_id}'")
                        results["skipped"] += 1
                        continue

                    # Find HM interview session
                    interview_session = db.query(InterviewSession).filter(
                        InterviewSession.user_id == agent.user_id,
                        InterviewSession.session_type == "hiring_manager",
                        InterviewSession.status == InterviewStatus.COMPLETED
                    ).order_by(InterviewSession.created_at.desc()).first()

                    if not interview_session:
                        print(f"  ⊙ Agent {agent.id}: No completed HM interview found")
                        results["skipped"] += 1
                        continue

                    # Get company_id from hiring manager role
                    from networking_ai.models.hiring_manager_role import HiringManagerRole
                    hm_role = db.query(HiringManagerRole).filter(
                        HiringManagerRole.user_id == agent.user_id,
                        HiringManagerRole.is_active == True
                    ).first()

                    if not hm_role:
                        print(f"  ⊙ Agent {agent.id}: No active HM role found")
                        results["skipped"] += 1
                        continue

                    # Create RAG collection
                    collection_name = self.chromadb_service.create_hm_rag(
                        agent_id=agent.id,
                        user_id=agent.user_id,
                        company_id=hm_role.company_id
                    )

                    # Populate RAG
                    interview_data = interview_session.knowledge_extracted or {}

                    if interview_data:
                        self.chromadb_service.populate_hm_rag(
                            collection_name=collection_name,
                            interview_data=interview_data
                        )

                        # Update agent
                        agent.rag_collection_id = collection_name
                        db.commit()

                        print(f"  ✓ Agent {agent.id}: Created and populated RAG '{collection_name}'")
                        results["migrated"] += 1
                    else:
                        print(f"  ⊙ Agent {agent.id}: No interview data to migrate")
                        results["skipped"] += 1

                except Exception as e:
                    print(f"  ✗ Agent {agent.id}: Error - {e}")
                    results["errors"] += 1
                    results["error_details"].append({
                        "agent_id": agent.id,
                        "error": str(e)
                    })
                    db.rollback()

        finally:
            db.close()

        return results

    def migrate_job_rags(self) -> Dict:
        """
        Migrate Job RAG collections.

        Finds all published jobs without RAG collections and creates them
        with dual access to HM and Company RAG.
        """
        if not self.chromadb_available:
            return {"status": "skipped", "reason": "ChromaDB not available"}

        db = self.SessionLocal()
        results = {
            "total_jobs": 0,
            "migrated": 0,
            "skipped": 0,
            "errors": 0,
            "error_details": []
        }

        try:
            # Get all active jobs without RAG collections
            jobs = db.query(Job).filter(
                Job.status == JobStatus.ACTIVE
            ).all()

            results["total_jobs"] = len(jobs)
            print(f"\n[MIGRATION] Found {len(jobs)} active jobs")

            for job in jobs:
                try:
                    # Check if RAG already exists
                    if job.job_rag_collection_id:
                        print(f"  ⊙ Job {job.id}: Already has RAG collection '{job.job_rag_collection_id}'")
                        results["skipped"] += 1
                        continue

                    # Check if job has HM and Company admin agents
                    if not job.hiring_manager_agent_id or not job.company_admin_agent_id:
                        print(f"  ⊙ Job {job.id}: Missing HM or Company admin agent")
                        results["skipped"] += 1
                        continue

                    # Create RAG collection
                    collection_name = self.chromadb_service.create_job_rag(
                        job_id=job.id,
                        company_id=job.company_id,
                        hiring_manager_id=job.hiring_manager_id
                    )

                    # Get HM and Company agents for dual access
                    hm_agent = db.query(PersonalAIAgent).filter(
                        PersonalAIAgent.id == job.hiring_manager_agent_id
                    ).first()

                    from networking_ai.models.company_admin_agent import CompanyAdminAgent
                    company_agent = db.query(CompanyAdminAgent).filter(
                        CompanyAdminAgent.id == job.company_admin_agent_id
                    ).first()

                    # Populate RAG
                    job_data = {
                        "title": job.title,
                        "description": job.description,
                        "required_skills": job.required_skills or [],
                        "preferred_skills": job.preferred_skills or [],
                        "experience_level": job.experience_level.value if job.experience_level else "mid_level",
                        "job_type": job.job_type.value if job.job_type else "full_time",
                        "is_remote": job.is_remote,
                        "location": job.location,
                        "department": job.department
                    }

                    self.chromadb_service.populate_job_rag(
                        collection_name=collection_name,
                        job_data=job_data,
                        hm_rag_collection=hm_agent.rag_collection_id if hm_agent else None,
                        company_rag_collection=company_agent.rag_collection_id if company_agent else None
                    )

                    # Update job
                    job.job_rag_collection_id = collection_name
                    db.commit()

                    print(f"  ✓ Job {job.id}: Created and populated RAG '{collection_name}'")
                    results["migrated"] += 1

                except Exception as e:
                    print(f"  ✗ Job {job.id}: Error - {e}")
                    results["errors"] += 1
                    results["error_details"].append({
                        "job_id": job.id,
                        "error": str(e)
                    })
                    db.rollback()

        finally:
            db.close()

        return results

    def run_full_migration(self) -> Dict:
        """Run full migration for all RAG types."""
        print("\n" + "="*70)
        print("RAG Data Migration")
        print("="*70)

        if not self.chromadb_available:
            print("\n⚠️  ChromaDB not available - migration cannot proceed")
            return {"status": "failed", "reason": "ChromaDB not available"}

        results = {
            "started_at": datetime.utcnow().isoformat(),
            "talent_rags": None,
            "hm_rags": None,
            "job_rags": None
        }

        # Migrate Talent RAGs
        print("\n1. Migrating Talent Personal Agent RAGs...")
        results["talent_rags"] = self.migrate_talent_rags()

        # Migrate HM RAGs
        print("\n2. Migrating HM Personal Agent RAGs...")
        results["hm_rags"] = self.migrate_hm_rags()

        # Migrate Job RAGs
        print("\n3. Migrating Job RAGs...")
        results["job_rags"] = self.migrate_job_rags()

        results["completed_at"] = datetime.utcnow().isoformat()

        # Print summary
        print("\n" + "="*70)
        print("Migration Summary")
        print("="*70)

        if results["talent_rags"]:
            tr = results["talent_rags"]
            print(f"\nTalent RAGs:")
            print(f"  Total agents: {tr['total_agents']}")
            print(f"  ✓ Migrated: {tr['migrated']}")
            print(f"  ⊙ Skipped: {tr['skipped']}")
            print(f"  ✗ Errors: {tr['errors']}")

        if results["hm_rags"]:
            hr = results["hm_rags"]
            print(f"\nHM RAGs:")
            print(f"  Total agents: {hr['total_agents']}")
            print(f"  ✓ Migrated: {hr['migrated']}")
            print(f"  ⊙ Skipped: {hr['skipped']}")
            print(f"  ✗ Errors: {hr['errors']}")

        if results["job_rags"]:
            jr = results["job_rags"]
            print(f"\nJob RAGs:")
            print(f"  Total jobs: {jr['total_jobs']}")
            print(f"  ✓ Migrated: {jr['migrated']}")
            print(f"  ⊙ Skipped: {jr['skipped']}")
            print(f"  ✗ Errors: {jr['errors']}")

        print("\n" + "="*70)

        return results


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(description="Migrate RAG data from existing interviews")
    parser.add_argument(
        "--type",
        choices=["all", "talent", "hm", "jobs"],
        default="all",
        help="Type of RAG to migrate (default: all)"
    )
    parser.add_argument(
        "--db-url",
        help="Database URL (default: from environment)"
    )

    args = parser.parse_args()

    migration = RAGMigration(db_url=args.db_url)

    if args.type == "all":
        migration.run_full_migration()
    elif args.type == "talent":
        print("\n" + "="*70)
        print("Migrating Talent Personal Agent RAGs")
        print("="*70)
        results = migration.migrate_talent_rags()
        print(f"\nResults: {results}")
    elif args.type == "hm":
        print("\n" + "="*70)
        print("Migrating HM Personal Agent RAGs")
        print("="*70)
        results = migration.migrate_hm_rags()
        print(f"\nResults: {results}")
    elif args.type == "jobs":
        print("\n" + "="*70)
        print("Migrating Job RAGs")
        print("="*70)
        results = migration.migrate_job_rags()
        print(f"\nResults: {results}")


if __name__ == "__main__":
    from typing import Dict
    main()
