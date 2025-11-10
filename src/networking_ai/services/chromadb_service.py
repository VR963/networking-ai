"""
ChromaDB Service - Phase 2 RAG Integration.

Manages ChromaDB collections for dual RAG system:
- Talent Personal Agent RAG (skills, preferences, career goals)
- HM Personal Agent RAG (hiring preferences, decision criteria)
- Company Admin Agent RAG (company culture, values, knowledge)
- Job RAG (requirements + dual access to HM + Company RAG)

Architecture:
- Each Personal Agent has its own collection (portable)
- Each Company Admin Agent has its own collection (persistent)
- Job postings have collections with dual access (HM + Company)
"""

import os
from typing import List, Dict, Optional, Any
import chromadb
from chromadb.config import Settings
from chromadb.utils import embedding_functions
import json


class ChromaDBService:
    """
    Service for managing ChromaDB collections and RAG operations.

    Handles:
    - Collection creation and management
    - Document addition and updates
    - Semantic search queries
    - Multi-collection queries (for dual RAG access)
    """

    def __init__(self, persist_directory: Optional[str] = None):
        """
        Initialize ChromaDB service.

        Args:
            persist_directory: Directory to persist ChromaDB data.
                              Defaults to ./chroma_data
        """
        self.persist_directory = persist_directory or os.getenv(
            "CHROMA_PERSIST_DIR",
            "./chroma_data"
        )

        # Initialize ChromaDB client
        self.client = chromadb.PersistentClient(
            path=self.persist_directory,
            settings=Settings(
                anonymized_telemetry=False,
                allow_reset=True
            )
        )

        # Use default embedding function (sentence transformers)
        self.embedding_function = embedding_functions.DefaultEmbeddingFunction()

        print(f"[ChromaDB] Initialized with persist directory: {self.persist_directory}")

    def create_collection(
        self,
        collection_name: str,
        metadata: Optional[Dict] = None
    ) -> chromadb.Collection:
        """
        Create or get a ChromaDB collection.

        Args:
            collection_name: Unique collection name
            metadata: Optional metadata for collection

        Returns:
            ChromaDB collection
        """
        try:
            collection = self.client.get_or_create_collection(
                name=collection_name,
                embedding_function=self.embedding_function,
                metadata=metadata or {}
            )
            print(f"[ChromaDB] Collection '{collection_name}' ready")
            return collection

        except Exception as e:
            print(f"[ChromaDB] Error creating collection '{collection_name}': {e}")
            raise

    def delete_collection(self, collection_name: str) -> bool:
        """
        Delete a collection.

        Args:
            collection_name: Collection to delete

        Returns:
            True if deleted successfully
        """
        try:
            self.client.delete_collection(name=collection_name)
            print(f"[ChromaDB] Collection '{collection_name}' deleted")
            return True

        except Exception as e:
            print(f"[ChromaDB] Error deleting collection '{collection_name}': {e}")
            return False

    def add_documents(
        self,
        collection_name: str,
        documents: List[str],
        metadatas: Optional[List[Dict]] = None,
        ids: Optional[List[str]] = None
    ) -> bool:
        """
        Add documents to a collection.

        Args:
            collection_name: Target collection
            documents: List of text documents
            metadatas: Optional metadata for each document
            ids: Optional IDs for documents (auto-generated if not provided)

        Returns:
            True if successful
        """
        try:
            collection = self.client.get_collection(
                name=collection_name,
                embedding_function=self.embedding_function
            )

            # Auto-generate IDs if not provided
            if ids is None:
                import uuid
                ids = [str(uuid.uuid4()) for _ in documents]

            collection.add(
                documents=documents,
                metadatas=metadatas,
                ids=ids
            )

            print(f"[ChromaDB] Added {len(documents)} documents to '{collection_name}'")
            return True

        except Exception as e:
            print(f"[ChromaDB] Error adding documents to '{collection_name}': {e}")
            raise

    def query_collection(
        self,
        collection_name: str,
        query_texts: List[str],
        n_results: int = 5,
        where: Optional[Dict] = None
    ) -> Dict:
        """
        Query a collection using semantic search.

        Args:
            collection_name: Collection to query
            query_texts: Query strings
            n_results: Number of results to return
            where: Optional filter conditions

        Returns:
            Query results with documents, distances, metadatas
        """
        try:
            collection = self.client.get_collection(
                name=collection_name,
                embedding_function=self.embedding_function
            )

            results = collection.query(
                query_texts=query_texts,
                n_results=n_results,
                where=where
            )

            print(f"[ChromaDB] Query '{collection_name}': {len(results['documents'][0])} results")
            return results

        except Exception as e:
            print(f"[ChromaDB] Error querying '{collection_name}': {e}")
            raise

    def update_documents(
        self,
        collection_name: str,
        ids: List[str],
        documents: Optional[List[str]] = None,
        metadatas: Optional[List[Dict]] = None
    ) -> bool:
        """
        Update documents in a collection.

        Args:
            collection_name: Target collection
            ids: Document IDs to update
            documents: New document texts (optional)
            metadatas: New metadatas (optional)

        Returns:
            True if successful
        """
        try:
            collection = self.client.get_collection(
                name=collection_name,
                embedding_function=self.embedding_function
            )

            collection.update(
                ids=ids,
                documents=documents,
                metadatas=metadatas
            )

            print(f"[ChromaDB] Updated {len(ids)} documents in '{collection_name}'")
            return True

        except Exception as e:
            print(f"[ChromaDB] Error updating documents in '{collection_name}': {e}")
            raise

    def delete_documents(
        self,
        collection_name: str,
        ids: List[str]
    ) -> bool:
        """
        Delete documents from a collection.

        Args:
            collection_name: Target collection
            ids: Document IDs to delete

        Returns:
            True if successful
        """
        try:
            collection = self.client.get_collection(
                name=collection_name,
                embedding_function=self.embedding_function
            )

            collection.delete(ids=ids)

            print(f"[ChromaDB] Deleted {len(ids)} documents from '{collection_name}'")
            return True

        except Exception as e:
            print(f"[ChromaDB] Error deleting documents from '{collection_name}': {e}")
            raise

    # ============================================================================
    # Talent Personal Agent RAG
    # ============================================================================

    def create_talent_rag(self, agent_id: int, user_id: int) -> str:
        """
        Create RAG collection for Talent Personal Agent.

        Args:
            agent_id: Personal AI agent ID
            user_id: User ID

        Returns:
            Collection name
        """
        collection_name = f"talent_agent_{agent_id}"

        self.create_collection(
            collection_name=collection_name,
            metadata={
                "agent_id": agent_id,
                "user_id": user_id,
                "agent_type": "talent",
                "created_at": str(chromadb.utils.get_current_time())
            }
        )

        return collection_name

    def populate_talent_rag(
        self,
        collection_name: str,
        interview_data: Dict,
        cv_data: Optional[Dict] = None
    ) -> bool:
        """
        Populate Talent RAG with interview and CV data.

        Args:
            collection_name: Talent agent collection
            interview_data: Extracted knowledge from interview
            cv_data: Optional CV data

        Returns:
            True if successful
        """
        documents = []
        metadatas = []
        ids = []

        # Add interview knowledge
        if "skills" in interview_data:
            skills_text = f"Technical skills: {', '.join(interview_data['skills'])}"
            documents.append(skills_text)
            metadatas.append({"type": "skills", "source": "interview"})
            ids.append("skills_interview")

        if "career_goals" in interview_data:
            documents.append(f"Career goals: {interview_data['career_goals']}")
            metadatas.append({"type": "career_goals", "source": "interview"})
            ids.append("career_goals")

        if "preferences" in interview_data:
            prefs = interview_data["preferences"]
            pref_text = f"Work preferences: Remote={prefs.get('remote')}, "
            pref_text += f"Salary range: {prefs.get('salary_min')}-{prefs.get('salary_max')}, "
            pref_text += f"Growth areas: {', '.join(prefs.get('growth_areas', []))}"
            documents.append(pref_text)
            metadatas.append({"type": "preferences", "source": "interview"})
            ids.append("preferences")

        if "work_style" in interview_data:
            documents.append(f"Work style: {interview_data['work_style']}")
            metadatas.append({"type": "work_style", "source": "interview"})
            ids.append("work_style")

        # Add CV data if available
        if cv_data:
            if "experience" in cv_data:
                documents.append(f"Experience: {cv_data['experience']}")
                metadatas.append({"type": "experience", "source": "cv"})
                ids.append("experience_cv")

            if "education" in cv_data:
                documents.append(f"Education: {cv_data['education']}")
                metadatas.append({"type": "education", "source": "cv"})
                ids.append("education_cv")

        # Add documents to collection
        if documents:
            return self.add_documents(
                collection_name=collection_name,
                documents=documents,
                metadatas=metadatas,
                ids=ids
            )

        return False

    def query_talent_profile(
        self,
        collection_name: str,
        query: str = "What are the candidate's skills, preferences, and career goals?",
        n_results: int = 10
    ) -> Dict:
        """
        Query Talent RAG for profile information.

        Args:
            collection_name: Talent agent collection
            query: Query text
            n_results: Number of results

        Returns:
            Profile data extracted from RAG
        """
        results = self.query_collection(
            collection_name=collection_name,
            query_texts=[query],
            n_results=n_results
        )

        # Parse results into structured profile
        profile = {
            "skills": [],
            "experience_level": "mid_level",
            "preferences": {},
            "career_goals": "",
            "work_style": ""
        }

        # Extract from documents
        for doc, metadata in zip(results["documents"][0], results["metadatas"][0]):
            doc_type = metadata.get("type")

            if doc_type == "skills":
                # Extract skills from text
                if "Technical skills:" in doc:
                    skills_text = doc.split("Technical skills:")[1].strip()
                    profile["skills"] = [s.strip() for s in skills_text.split(",")]

            elif doc_type == "preferences":
                # Parse preferences
                if "Remote=" in doc:
                    profile["preferences"]["remote"] = "True" in doc

            elif doc_type == "career_goals":
                profile["career_goals"] = doc.replace("Career goals:", "").strip()

            elif doc_type == "work_style":
                profile["work_style"] = doc.replace("Work style:", "").strip()

        return profile

    # ============================================================================
    # HM Personal Agent RAG
    # ============================================================================

    def create_hm_rag(self, agent_id: int, user_id: int, company_id: int) -> str:
        """
        Create RAG collection for HM Personal Agent.

        Args:
            agent_id: Personal AI agent ID
            user_id: User ID (HM)
            company_id: Company ID

        Returns:
            Collection name
        """
        collection_name = f"hm_agent_{agent_id}"

        self.create_collection(
            collection_name=collection_name,
            metadata={
                "agent_id": agent_id,
                "user_id": user_id,
                "company_id": company_id,
                "agent_type": "hiring_manager",
                "created_at": str(chromadb.utils.get_current_time())
            }
        )

        return collection_name

    def populate_hm_rag(
        self,
        collection_name: str,
        interview_data: Dict
    ) -> bool:
        """
        Populate HM RAG with hiring preferences and style.

        Args:
            collection_name: HM agent collection
            interview_data: Extracted knowledge from HM interview

        Returns:
            True if successful
        """
        documents = []
        metadatas = []
        ids = []

        # Hiring preferences
        if "hiring_preferences" in interview_data:
            prefs = interview_data["hiring_preferences"]
            pref_text = f"Hiring preferences: {json.dumps(prefs)}"
            documents.append(pref_text)
            metadatas.append({"type": "hiring_preferences", "source": "interview"})
            ids.append("hiring_preferences")

        # Hiring style
        if "hiring_style" in interview_data:
            style = interview_data["hiring_style"]
            documents.append(f"Hiring style: {json.dumps(style)}")
            metadatas.append({"type": "hiring_style", "source": "interview"})
            ids.append("hiring_style")

        # Team info
        if "team_info" in interview_data:
            team = interview_data["team_info"]
            documents.append(f"Team information: {json.dumps(team)}")
            metadatas.append({"type": "team_info", "source": "interview"})
            ids.append("team_info")

        # Technical requirements
        if "technical_requirements" in interview_data:
            tech = interview_data["technical_requirements"]
            documents.append(f"Technical requirements: {json.dumps(tech)}")
            metadatas.append({"type": "technical_requirements", "source": "interview"})
            ids.append("technical_requirements")

        # Decision criteria
        if "decision_criteria" in interview_data:
            criteria = interview_data["decision_criteria"]
            documents.append(f"Decision criteria: {json.dumps(criteria)}")
            metadatas.append({"type": "decision_criteria", "source": "interview"})
            ids.append("decision_criteria")

        # Add documents
        if documents:
            return self.add_documents(
                collection_name=collection_name,
                documents=documents,
                metadatas=metadatas,
                ids=ids
            )

        return False

    # ============================================================================
    # Job RAG (Dual Access)
    # ============================================================================

    def create_job_rag(
        self,
        job_id: int,
        company_id: int,
        hiring_manager_id: int
    ) -> str:
        """
        Create RAG collection for Job Posting (Company AI Agent).

        Args:
            job_id: Job ID
            company_id: Company ID
            hiring_manager_id: Hiring manager user ID

        Returns:
            Collection name
        """
        collection_name = f"job_{job_id}"

        self.create_collection(
            collection_name=collection_name,
            metadata={
                "job_id": job_id,
                "company_id": company_id,
                "hiring_manager_id": hiring_manager_id,
                "agent_type": "job",
                "created_at": str(chromadb.utils.get_current_time())
            }
        )

        return collection_name

    def populate_job_rag(
        self,
        collection_name: str,
        job_data: Dict,
        hm_rag_collection: Optional[str] = None,
        company_rag_collection: Optional[str] = None
    ) -> bool:
        """
        Populate Job RAG with dual access to HM and Company RAG.

        Args:
            collection_name: Job collection
            job_data: Job posting data
            hm_rag_collection: HM Personal Agent RAG (for hiring preferences)
            company_rag_collection: Company Admin Agent RAG (for culture)

        Returns:
            True if successful
        """
        documents = []
        metadatas = []
        ids = []

        # Job requirements
        if "title" in job_data:
            documents.append(f"Job title: {job_data['title']}")
            metadatas.append({"type": "title", "source": "job"})
            ids.append("job_title")

        if "description" in job_data:
            documents.append(f"Job description: {job_data['description']}")
            metadatas.append({"type": "description", "source": "job"})
            ids.append("job_description")

        if "required_skills" in job_data:
            skills_text = f"Required skills: {', '.join(job_data['required_skills'])}"
            documents.append(skills_text)
            metadatas.append({"type": "required_skills", "source": "job"})
            ids.append("required_skills")

        if "preferred_skills" in job_data:
            pref_skills = f"Preferred skills: {', '.join(job_data['preferred_skills'])}"
            documents.append(pref_skills)
            metadatas.append({"type": "preferred_skills", "source": "job"})
            ids.append("preferred_skills")

        # Add job metadata
        if "experience_level" in job_data:
            documents.append(f"Experience level: {job_data['experience_level']}")
            metadatas.append({"type": "experience_level", "source": "job"})
            ids.append("experience_level")

        # TODO: Query HM RAG and add hiring preferences
        if hm_rag_collection:
            # Query HM RAG for hiring preferences
            # Add to job RAG as context
            pass

        # TODO: Query Company RAG and add culture information
        if company_rag_collection:
            # Query Company Admin RAG for culture
            # Add to job RAG as context
            pass

        # Add documents
        if documents:
            return self.add_documents(
                collection_name=collection_name,
                documents=documents,
                metadatas=metadatas,
                ids=ids
            )

        return False

    def query_multi_rag(
        self,
        collection_names: List[str],
        query: str,
        n_results: int = 5
    ) -> Dict:
        """
        Query multiple RAG collections (for dual access).

        Used for Job RAG to access HM + Company knowledge.

        Args:
            collection_names: List of collections to query
            query: Query text
            n_results: Results per collection

        Returns:
            Combined results from all collections
        """
        combined_results = {
            "documents": [],
            "metadatas": [],
            "distances": []
        }

        for collection_name in collection_names:
            try:
                results = self.query_collection(
                    collection_name=collection_name,
                    query_texts=[query],
                    n_results=n_results
                )

                # Merge results
                combined_results["documents"].extend(results["documents"][0])
                combined_results["metadatas"].extend(results["metadatas"][0])
                combined_results["distances"].extend(results["distances"][0])

            except Exception as e:
                print(f"[ChromaDB] Error querying '{collection_name}': {e}")
                continue

        return combined_results


# Factory function
def create_chromadb_service(persist_directory: Optional[str] = None) -> ChromaDBService:
    """Create ChromaDB service instance."""
    return ChromaDBService(persist_directory=persist_directory)
