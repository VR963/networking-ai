"""
Personal RAG Manager.

Manages ChromaDB collections for individual users.
Each user gets their own collection populated from interview knowledge.
"""

from typing import Dict, List, Optional
import chromadb
from chromadb.config import Settings
from datetime import datetime


class PersonalRAGManager:
    """
    Manages personal RAG collections for users.

    Each user gets their own ChromaDB collection:
    - Collection ID: user_{user_id}_personal_rag
    - Populated from interview knowledge
    - Updated from conversation feedback
    """

    def __init__(self, persist_directory: str = "./data/personal_rag"):
        """
        Initialize Personal RAG Manager.

        Args:
            persist_directory: Directory for ChromaDB storage
        """
        self.client = chromadb.PersistentClient(path=persist_directory)

    def create_collection(self, user_id: int) -> str:
        """
        Create personal RAG collection for user.

        Args:
            user_id: User ID

        Returns:
            Collection ID
        """
        collection_id = f"user_{user_id}_personal_rag"

        # Create or get existing collection
        self.client.get_or_create_collection(
            name=collection_id,
            metadata={"user_id": user_id, "created_at": datetime.utcnow().isoformat()}
        )

        print(f"[PERSONAL RAG] Created collection: {collection_id}")
        return collection_id

    def populate_from_interview(
        self,
        collection_id: str,
        knowledge: Dict,
        cv_data: Dict
    ):
        """
        Populate RAG from interview knowledge.

        Args:
            collection_id: ChromaDB collection ID
            knowledge: Extracted knowledge from interview
            cv_data: Parsed CV data
        """
        collection = self.client.get_collection(collection_id)

        documents = []
        metadatas = []
        ids = []

        # 1. CV Summary
        cv_summary = self._generate_cv_summary(cv_data)
        if cv_summary:
            documents.append(cv_summary)
            metadatas.append({"type": "profile", "source": "cv"})
            ids.append("cv_summary")

        # 2. Work History Details
        for idx, job in enumerate(cv_data.get("work_history", [])):
            job_description = f"{job.get('title', 'Role')} at {job.get('company', 'Company')}"
            if "description" in job:
                job_description += f": {job['description']}"

            documents.append(job_description)
            metadatas.append({
                "type": "work_history",
                "source": "cv",
                "company": job.get("company", ""),
                "years": job.get("years", 0)
            })
            ids.append(f"work_history_{idx}")

        # 3. Motivations
        for motivation_key, motivation_data in knowledge.get("motivations", {}).items():
            content = str(motivation_data)
            if isinstance(motivation_data, dict):
                content = motivation_data.get("description", str(motivation_data))

            documents.append(content)
            metadatas.append({
                "type": "motivation",
                "category": motivation_key,
                "priority": "high"
            })
            ids.append(f"motivation_{motivation_key}")

        # 4. Preferences
        for pref_key, pref_data in knowledge.get("preferences", {}).items():
            content = str(pref_data)
            if isinstance(pref_data, dict):
                content = pref_data.get("description", str(pref_data))

            documents.append(content)
            metadatas.append({
                "type": "preference",
                "category": pref_key
            })
            ids.append(f"preference_{pref_key}")

        # 5. Technical Skills (detailed)
        for skill_key, skill_data in knowledge.get("technical_skills", {}).items():
            content = f"Skill: {skill_key}"
            if isinstance(skill_data, dict):
                proficiency = skill_data.get("proficiency", "")
                years = skill_data.get("years", "")
                context = skill_data.get("context", "")
                content = f"{skill_key}: {proficiency} proficiency"
                if years:
                    content += f", {years} years experience"
                if context:
                    content += f". Context: {context}"

            documents.append(content)
            metadatas.append({
                "type": "technical_skill",
                "skill": skill_key,
                "source": "interview"
            })
            ids.append(f"skill_{skill_key}")

        # 6. Soft Skills
        for soft_skill_key, soft_skill_data in knowledge.get("soft_skills", {}).items():
            content = f"{soft_skill_key}: {soft_skill_data}"

            documents.append(content)
            metadatas.append({
                "type": "soft_skill",
                "skill": soft_skill_key
            })
            ids.append(f"soft_skill_{soft_skill_key}")

        # Add all documents to collection
        if documents:
            collection.add(
                documents=documents,
                metadatas=metadatas,
                ids=ids
            )

            print(f"[PERSONAL RAG] Added {len(documents)} documents to {collection_id}")
        else:
            print(f"[PERSONAL RAG] Warning: No documents to add for {collection_id}")

    def query(
        self,
        collection_id: str,
        query: str,
        filter: Optional[Dict] = None,
        n_results: int = 5
    ) -> List[Dict]:
        """
        Query personal RAG.

        Args:
            collection_id: ChromaDB collection ID
            query: Query text
            filter: Optional metadata filter
            n_results: Number of results to return

        Returns:
            List of matching documents with metadata
        """
        collection = self.client.get_collection(collection_id)

        results = collection.query(
            query_texts=[query],
            where=filter,
            n_results=n_results
        )

        # Format results
        formatted_results = []
        if results and results["documents"]:
            for i, doc in enumerate(results["documents"][0]):
                formatted_results.append({
                    "document": doc,
                    "metadata": results["metadatas"][0][i] if results["metadatas"] else {},
                    "distance": results["distances"][0][i] if results.get("distances") else None
                })

        return formatted_results

    def add_learning_document(
        self,
        collection_id: str,
        document: str,
        metadata: Dict
    ):
        """
        Add learning document from feedback.

        Args:
            collection_id: ChromaDB collection ID
            document: Document text
            metadata: Document metadata
        """
        collection = self.client.get_collection(collection_id)

        # Generate unique ID
        doc_id = f"learning_{datetime.utcnow().timestamp()}"

        collection.add(
            documents=[document],
            metadatas=[metadata],
            ids=[doc_id]
        )

        print(f"[PERSONAL RAG] Added learning document to {collection_id}")

    def delete_collection(self, collection_id: str):
        """
        Delete personal RAG collection.

        Args:
            collection_id: ChromaDB collection ID
        """
        try:
            self.client.delete_collection(collection_id)
            print(f"[PERSONAL RAG] Deleted collection: {collection_id}")
        except Exception as e:
            print(f"[PERSONAL RAG] Error deleting {collection_id}: {e}")

    def _generate_cv_summary(self, cv_data: Dict) -> str:
        """
        Generate summary from CV data.

        Args:
            cv_data: Parsed CV data

        Returns:
            Summary string
        """
        parts = []

        # Name
        contact = cv_data.get("contact_info", {})
        if contact.get("name"):
            parts.append(f"Name: {contact['name']}")

        # Work history summary
        work_history = cv_data.get("work_history", [])
        if work_history:
            total_years = sum(job.get("years", 0) for job in work_history)
            latest_job = work_history[0] if work_history else {}
            latest_title = latest_job.get("title", "")
            latest_company = latest_job.get("company", "")

            parts.append(f"{total_years} years of experience")
            if latest_title and latest_company:
                parts.append(f"Currently: {latest_title} at {latest_company}")

        # Skills summary
        skills = cv_data.get("skills", {})
        if isinstance(skills, dict):
            technical_skills = skills.get("technical", [])
            if technical_skills:
                parts.append(f"Technical skills: {', '.join(technical_skills[:5])}")
        elif isinstance(skills, list):
            if skills:
                parts.append(f"Skills: {', '.join(skills[:5])}")

        # Education
        education = cv_data.get("education", [])
        if education:
            degrees = [edu.get("degree", "") for edu in education if edu.get("degree")]
            if degrees:
                parts.append(f"Education: {degrees[0]}")

        return ". ".join(parts) if parts else "Professional profile"


def create_personal_rag_manager(persist_directory: str = "./data/personal_rag") -> PersonalRAGManager:
    """
    Factory function to create PersonalRAGManager.

    Args:
        persist_directory: Directory for ChromaDB storage

    Returns:
        PersonalRAGManager instance
    """
    return PersonalRAGManager(persist_directory=persist_directory)
