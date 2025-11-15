"""
Company Agent Factory.

Creates and manages Company Admin Agents (Master AI for companies).
"""

from typing import Dict, Optional
from datetime import datetime
from sqlalchemy.orm import Session

from ..models.company_admin_agent import CompanyAdminAgent, AdminAgentStatus
from ..models.hiring_manager_role import HiringManagerRole
from ..models.company_v2 import CompanyV2 as Company
from .company_rag import CompanyRAGManager


class CompanyAgentFactory:
    """
    Factory for creating Company Admin Agents.

    Responsibilities:
    - Create Master AI Agent for company
    - Set up company RAG collection
    - Link hiring managers to company agent
    - Track company knowledge
    """

    def __init__(self, rag_manager: Optional[CompanyRAGManager] = None):
        """
        Initialize Company Agent Factory.

        Args:
            rag_manager: CompanyRAGManager instance (optional)
        """
        self.rag_manager = rag_manager or CompanyRAGManager()

    def create_for_company(
        self,
        company_id: int,
        db: Session
    ) -> CompanyAdminAgent:
        """
        Create Company Admin Agent for a company.

        This is called when the first hiring manager from a company joins.

        Args:
            company_id: Company ID
            db: Database session

        Returns:
            CompanyAdminAgent instance
        """
        # Get company
        company = db.query(Company).filter(Company.id == company_id).first()
        if not company:
            raise ValueError(f"Company {company_id} not found")

        # Check if admin agent already exists
        existing_agent = db.query(CompanyAdminAgent).filter(
            CompanyAdminAgent.company_id == company_id
        ).first()

        if existing_agent:
            print(f"[COMPANY AGENT] Admin agent already exists for company {company.name}")
            return existing_agent

        # Create ChromaDB collection
        collection_id = self.rag_manager.create_collection(
            company_id=company_id,
            company_name=company.name
        )

        # Add initial company knowledge
        if company.description:
            self.rag_manager.add_company_knowledge(
                collection_id=collection_id,
                knowledge_type="company_description",
                content=f"Company: {company.name}\nDescription: {company.description}",
                metadata={"source": "company_profile"}
            )

        if company.industry:
            self.rag_manager.add_company_knowledge(
                collection_id=collection_id,
                knowledge_type="company_industry",
                content=f"Industry: {company.industry}",
                metadata={"source": "company_profile"}
            )

        # Create Company Admin Agent
        admin_agent = CompanyAdminAgent(
            company_id=company_id,
            company_rag_collection_id=collection_id,
            status=AdminAgentStatus.ACTIVE,
            total_hiring_managers=0,
            active_hiring_managers=0,
            total_conversations=0,
            total_hires=0,
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow()
        )

        db.add(admin_agent)
        db.commit()
        db.refresh(admin_agent)

        print(f"[COMPANY AGENT] Created admin agent for company: {company.name}")
        return admin_agent

    def link_hiring_manager(
        self,
        company_admin_agent_id: int,
        hiring_manager_id: int,
        hiring_manager_agent_id: int,
        hiring_manager_name: str,
        hiring_manager_knowledge: Dict,
        db: Session
    ) -> HiringManagerRole:
        """
        Link a hiring manager to company admin agent.

        This is called when a hiring manager completes their interview.
        Their knowledge is added to the company RAG.

        Args:
            company_admin_agent_id: Company Admin Agent ID
            hiring_manager_id: User ID of hiring manager
            hiring_manager_agent_id: Personal AI Agent ID of hiring manager
            hiring_manager_name: Hiring manager name
            hiring_manager_knowledge: Knowledge from HM interview
            db: Database session

        Returns:
            HiringManagerRole instance
        """
        # Get company admin agent
        admin_agent = db.query(CompanyAdminAgent).filter(
            CompanyAdminAgent.id == company_admin_agent_id
        ).first()

        if not admin_agent:
            raise ValueError(f"Company Admin Agent {company_admin_agent_id} not found")

        # Add hiring manager knowledge to company RAG
        self.rag_manager.add_hiring_manager_knowledge(
            collection_id=admin_agent.company_rag_collection_id,
            hiring_manager_id=hiring_manager_id,
            hiring_manager_name=hiring_manager_name,
            knowledge=hiring_manager_knowledge
        )

        # Create HiringManagerRole link
        hm_role = HiringManagerRole(
            user_id=hiring_manager_id,
            company_id=admin_agent.company_id,
            hiring_manager_agent_id=hiring_manager_agent_id,
            company_admin_agent_id=company_admin_agent_id,
            is_active=True,
            joined_at=datetime.utcnow()
        )

        db.add(hm_role)

        # Update company admin agent stats
        admin_agent.record_new_hiring_manager()
        admin_agent.updated_at = datetime.utcnow()

        db.commit()
        db.refresh(hm_role)

        print(f"[COMPANY AGENT] Linked HM {hiring_manager_name} to company agent")
        return hm_role

    def deactivate_hiring_manager(
        self,
        hiring_manager_role_id: int,
        db: Session
    ):
        """
        Deactivate a hiring manager (they left the company).

        Their knowledge stays in company RAG, but they are marked as inactive.

        Args:
            hiring_manager_role_id: HiringManagerRole ID
            db: Database session
        """
        # Get hiring manager role
        hm_role = db.query(HiringManagerRole).filter(
            HiringManagerRole.id == hiring_manager_role_id
        ).first()

        if not hm_role:
            raise ValueError(f"HiringManagerRole {hiring_manager_role_id} not found")

        # Deactivate role
        hm_role.deactivate()

        # Get company admin agent
        admin_agent = db.query(CompanyAdminAgent).filter(
            CompanyAdminAgent.id == hm_role.company_admin_agent_id
        ).first()

        if admin_agent:
            # Update stats
            admin_agent.active_hiring_managers = max(0, admin_agent.active_hiring_managers - 1)
            admin_agent.updated_at = datetime.utcnow()

            # Mark knowledge as historical in RAG
            self.rag_manager.remove_hiring_manager(
                collection_id=admin_agent.company_rag_collection_id,
                hiring_manager_id=hm_role.user_id
            )

        db.commit()
        print(f"[COMPANY AGENT] Deactivated HM role {hiring_manager_role_id}")

    def add_job_posting(
        self,
        company_admin_agent_id: int,
        job_id: int,
        job_title: str,
        job_data: Dict,
        db: Session
    ):
        """
        Add job posting knowledge to company RAG.

        Args:
            company_admin_agent_id: Company Admin Agent ID
            job_id: Job posting ID
            job_title: Job title
            job_data: Job posting data
            db: Database session
        """
        # Get company admin agent
        admin_agent = db.query(CompanyAdminAgent).filter(
            CompanyAdminAgent.id == company_admin_agent_id
        ).first()

        if not admin_agent:
            raise ValueError(f"Company Admin Agent {company_admin_agent_id} not found")

        # Add to company RAG
        self.rag_manager.add_job_posting_knowledge(
            collection_id=admin_agent.company_rag_collection_id,
            job_id=job_id,
            job_title=job_title,
            job_data=job_data
        )

        admin_agent.updated_at = datetime.utcnow()
        db.commit()

        print(f"[COMPANY AGENT] Added job posting to company RAG: {job_title}")

    def record_hire(
        self,
        company_admin_agent_id: int,
        db: Session
    ):
        """
        Record a successful hire.

        Args:
            company_admin_agent_id: Company Admin Agent ID
            db: Database session
        """
        admin_agent = db.query(CompanyAdminAgent).filter(
            CompanyAdminAgent.id == company_admin_agent_id
        ).first()

        if admin_agent:
            admin_agent.record_hire()
            admin_agent.updated_at = datetime.utcnow()
            db.commit()
            print(f"[COMPANY AGENT] Recorded hire for company agent {company_admin_agent_id}")

    def record_conversation(
        self,
        company_admin_agent_id: int,
        db: Session
    ):
        """
        Record a conversation (company knowledge interaction).

        Args:
            company_admin_agent_id: Company Admin Agent ID
            db: Database session
        """
        admin_agent = db.query(CompanyAdminAgent).filter(
            CompanyAdminAgent.id == company_admin_agent_id
        ).first()

        if admin_agent:
            admin_agent.record_conversation()
            admin_agent.updated_at = datetime.utcnow()
            db.commit()

    def get_company_knowledge_stats(
        self,
        company_admin_agent_id: int,
        db: Session
    ) -> Dict:
        """
        Get statistics about company knowledge.

        Args:
            company_admin_agent_id: Company Admin Agent ID
            db: Database session

        Returns:
            Statistics dictionary
        """
        admin_agent = db.query(CompanyAdminAgent).filter(
            CompanyAdminAgent.id == company_admin_agent_id
        ).first()

        if not admin_agent:
            raise ValueError(f"Company Admin Agent {company_admin_agent_id} not found")

        # Get RAG stats
        rag_stats = self.rag_manager.get_stats(admin_agent.company_rag_collection_id)

        # Get hiring managers
        hiring_managers = self.rag_manager.get_hiring_managers(
            admin_agent.company_rag_collection_id
        )

        return {
            "agent_id": admin_agent.id,
            "company_id": admin_agent.company_id,
            "status": admin_agent.status.value,
            "total_hiring_managers": admin_agent.total_hiring_managers,
            "active_hiring_managers": admin_agent.active_hiring_managers,
            "total_conversations": admin_agent.total_conversations,
            "total_hires": admin_agent.total_hires,
            "rag_documents": rag_stats['total_documents'],
            "rag_type_breakdown": rag_stats['type_breakdown'],
            "hiring_managers": hiring_managers
        }

    def query_company_knowledge(
        self,
        company_admin_agent_id: int,
        query: str,
        n_results: int = 5,
        db: Session = None
    ) -> list:
        """
        Query company knowledge base.

        Args:
            company_admin_agent_id: Company Admin Agent ID
            query: Search query
            n_results: Number of results
            db: Database session

        Returns:
            List of relevant documents
        """
        admin_agent = db.query(CompanyAdminAgent).filter(
            CompanyAdminAgent.id == company_admin_agent_id
        ).first()

        if not admin_agent:
            raise ValueError(f"Company Admin Agent {company_admin_agent_id} not found")

        return self.rag_manager.query(
            collection_id=admin_agent.company_rag_collection_id,
            query_text=query,
            n_results=n_results
        )
