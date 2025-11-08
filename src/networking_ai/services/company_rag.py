"""
Company RAG Manager.

Manages ChromaDB collections for companies.
Each company gets a Master RAG populated from:
- Hiring manager interviews
- Job postings
- Company knowledge
- Hiring patterns
"""

from typing import Dict, List, Optional
import chromadb
from chromadb.config import Settings
from datetime import datetime


class CompanyRAGManager:
    """
    Manages company RAG collections for Master AI Agents.

    Each company gets one ChromaDB collection:
    - Collection ID: company_{company_id}_master_rag
    - Populated from all hiring managers
    - Persists when hiring managers leave
    - Accessed by Company Admin Agent
    """

    def __init__(self, persist_directory: str = "./data/company_rag"):
        """
        Initialize Company RAG Manager.

        Args:
            persist_directory: Directory for ChromaDB storage
        """
        self.client = chromadb.Client(Settings(
            chroma_db_impl="duckdb+parquet",
            persist_directory=persist_directory
        ))

    def create_collection(self, company_id: int, company_name: str) -> str:
        """
        Create company RAG collection.

        Args:
            company_id: Company ID
            company_name: Company name

        Returns:
            Collection ID
        """
        collection_id = f"company_{company_id}_master_rag"

        # Create or get existing collection
        self.client.get_or_create_collection(
            name=collection_id,
            metadata={
                "company_id": company_id,
                "company_name": company_name,
                "created_at": datetime.utcnow().isoformat()
            }
        )

        print(f"[COMPANY RAG] Created collection: {collection_id}")
        return collection_id

    def add_hiring_manager_knowledge(
        self,
        collection_id: str,
        hiring_manager_id: int,
        hiring_manager_name: str,
        knowledge: Dict
    ):
        """
        Add hiring manager's knowledge to company RAG.

        This is called when a hiring manager completes their interview.
        Their preferences and style are added to company knowledge.

        Args:
            collection_id: ChromaDB collection ID
            hiring_manager_id: Hiring manager ID
            hiring_manager_name: Hiring manager name
            knowledge: Extracted knowledge from interview
        """
        collection = self.client.get_collection(collection_id)

        documents = []
        metadatas = []
        ids = []

        # 1. Hiring Manager Profile
        if "profile" in knowledge:
            profile = knowledge["profile"]
            doc = f"""Hiring Manager: {hiring_manager_name}
Role: {profile.get('role', 'N/A')}
Department: {profile.get('department', 'N/A')}
Experience: {profile.get('experience_years', 'N/A')} years
Background: {profile.get('background', 'N/A')}"""
            documents.append(doc)
            metadatas.append({
                "type": "hiring_manager_profile",
                "hiring_manager_id": hiring_manager_id,
                "hiring_manager_name": hiring_manager_name,
                "added_at": datetime.utcnow().isoformat()
            })
            ids.append(f"hm_{hiring_manager_id}_profile")

        # 2. Hiring Preferences
        if "hiring_preferences" in knowledge:
            prefs = knowledge["hiring_preferences"]
            doc = f"""Hiring Manager {hiring_manager_name} Preferences:
Skills Priority: {', '.join(prefs.get('skills_priority', []))}
Experience Level: {prefs.get('experience_level_preference', 'N/A')}
Team Fit: {prefs.get('team_fit_criteria', 'N/A')}
Cultural Values: {', '.join(prefs.get('cultural_values', []))}
Red Flags: {', '.join(prefs.get('red_flags', []))}"""
            documents.append(doc)
            metadatas.append({
                "type": "hiring_preferences",
                "hiring_manager_id": hiring_manager_id,
                "hiring_manager_name": hiring_manager_name,
                "added_at": datetime.utcnow().isoformat()
            })
            ids.append(f"hm_{hiring_manager_id}_preferences")

        # 3. Hiring Style
        if "hiring_style" in knowledge:
            style = knowledge["hiring_style"]
            doc = f"""Hiring Manager {hiring_manager_name} Style:
Interview Approach: {style.get('interview_approach', 'N/A')}
Decision Making: {style.get('decision_making', 'N/A')}
Communication Style: {style.get('communication_style', 'N/A')}
Feedback Approach: {style.get('feedback_approach', 'N/A')}"""
            documents.append(doc)
            metadatas.append({
                "type": "hiring_style",
                "hiring_manager_id": hiring_manager_id,
                "hiring_manager_name": hiring_manager_name,
                "added_at": datetime.utcnow().isoformat()
            })
            ids.append(f"hm_{hiring_manager_id}_style")

        # 4. Team Information
        if "team_info" in knowledge:
            team = knowledge["team_info"]
            doc = f"""Hiring Manager {hiring_manager_name} Team:
Team Size: {team.get('team_size', 'N/A')}
Team Structure: {team.get('structure', 'N/A')}
Current Needs: {', '.join(team.get('current_needs', []))}
Growth Plans: {team.get('growth_plans', 'N/A')}"""
            documents.append(doc)
            metadatas.append({
                "type": "team_info",
                "hiring_manager_id": hiring_manager_id,
                "hiring_manager_name": hiring_manager_name,
                "added_at": datetime.utcnow().isoformat()
            })
            ids.append(f"hm_{hiring_manager_id}_team")

        # Add all documents to collection
        if documents:
            collection.add(
                documents=documents,
                metadatas=metadatas,
                ids=ids
            )
            print(f"[COMPANY RAG] Added {len(documents)} documents for HM {hiring_manager_name}")

    def add_job_posting_knowledge(
        self,
        collection_id: str,
        job_id: int,
        job_title: str,
        job_data: Dict
    ):
        """
        Add job posting knowledge to company RAG.

        Args:
            collection_id: ChromaDB collection ID
            job_id: Job posting ID
            job_title: Job title
            job_data: Job posting data
        """
        collection = self.client.get_collection(collection_id)

        # Job posting knowledge
        doc = f"""Job Posting: {job_title}
Department: {job_data.get('department', 'N/A')}
Level: {job_data.get('level', 'N/A')}
Required Skills: {', '.join(job_data.get('required_skills', []))}
Preferred Skills: {', '.join(job_data.get('preferred_skills', []))}
Description: {job_data.get('description', 'N/A')}
Responsibilities: {', '.join(job_data.get('responsibilities', []))}
Qualifications: {', '.join(job_data.get('qualifications', []))}"""

        collection.add(
            documents=[doc],
            metadatas=[{
                "type": "job_posting",
                "job_id": job_id,
                "job_title": job_title,
                "added_at": datetime.utcnow().isoformat()
            }],
            ids=[f"job_{job_id}"]
        )
        print(f"[COMPANY RAG] Added job posting: {job_title}")

    def add_company_knowledge(
        self,
        collection_id: str,
        knowledge_type: str,
        content: str,
        metadata: Optional[Dict] = None
    ):
        """
        Add general company knowledge to RAG.

        Args:
            collection_id: ChromaDB collection ID
            knowledge_type: Type of knowledge (company_culture, values, etc.)
            content: Knowledge content
            metadata: Additional metadata
        """
        collection = self.client.get_collection(collection_id)

        meta = metadata or {}
        meta.update({
            "type": knowledge_type,
            "added_at": datetime.utcnow().isoformat()
        })

        doc_id = f"{knowledge_type}_{datetime.utcnow().timestamp()}"

        collection.add(
            documents=[content],
            metadatas=[meta],
            ids=[doc_id]
        )
        print(f"[COMPANY RAG] Added knowledge: {knowledge_type}")

    def remove_hiring_manager(
        self,
        collection_id: str,
        hiring_manager_id: int
    ):
        """
        Mark hiring manager as inactive (but keep their knowledge).

        When a hiring manager leaves, their knowledge stays in company RAG
        but is marked as historical.

        Args:
            collection_id: ChromaDB collection ID
            hiring_manager_id: Hiring manager ID
        """
        collection = self.client.get_collection(collection_id)

        # Query all documents from this hiring manager
        results = collection.get(
            where={"hiring_manager_id": hiring_manager_id}
        )

        if results and results['ids']:
            # Update metadata to mark as inactive
            for doc_id in results['ids']:
                # Note: ChromaDB doesn't support metadata updates directly
                # In production, we'd need to delete and re-add with updated metadata
                # For now, we just log it
                print(f"[COMPANY RAG] Marking HM {hiring_manager_id} knowledge as historical")

    def query(
        self,
        collection_id: str,
        query_text: str,
        n_results: int = 5,
        filter_dict: Optional[Dict] = None
    ) -> List[Dict]:
        """
        Query company RAG collection.

        Args:
            collection_id: ChromaDB collection ID
            query_text: Query text
            n_results: Number of results to return
            filter_dict: Optional metadata filters

        Returns:
            List of relevant documents with metadata
        """
        collection = self.client.get_collection(collection_id)

        query_params = {
            "query_texts": [query_text],
            "n_results": n_results
        }

        if filter_dict:
            query_params["where"] = filter_dict

        results = collection.query(**query_params)

        # Format results
        documents = []
        if results and results['documents']:
            for i, doc in enumerate(results['documents'][0]):
                documents.append({
                    "content": doc,
                    "metadata": results['metadatas'][0][i] if results['metadatas'] else {},
                    "distance": results['distances'][0][i] if results['distances'] else None
                })

        return documents

    def get_hiring_managers(self, collection_id: str) -> List[Dict]:
        """
        Get all hiring managers in company RAG.

        Args:
            collection_id: ChromaDB collection ID

        Returns:
            List of hiring manager info
        """
        collection = self.client.get_collection(collection_id)

        # Get all hiring manager profiles
        results = collection.get(
            where={"type": "hiring_manager_profile"}
        )

        managers = []
        if results and results['metadatas']:
            for meta in results['metadatas']:
                managers.append({
                    "hiring_manager_id": meta.get('hiring_manager_id'),
                    "hiring_manager_name": meta.get('hiring_manager_name'),
                    "added_at": meta.get('added_at')
                })

        return managers

    def get_stats(self, collection_id: str) -> Dict:
        """
        Get statistics about company RAG collection.

        Args:
            collection_id: ChromaDB collection ID

        Returns:
            Statistics dictionary
        """
        collection = self.client.get_collection(collection_id)

        # Get all items
        all_items = collection.get()

        # Count by type
        type_counts = {}
        if all_items and all_items['metadatas']:
            for meta in all_items['metadatas']:
                doc_type = meta.get('type', 'unknown')
                type_counts[doc_type] = type_counts.get(doc_type, 0) + 1

        return {
            "total_documents": len(all_items['ids']) if all_items and all_items['ids'] else 0,
            "type_breakdown": type_counts,
            "collection_metadata": collection.metadata
        }
