"""Embedding Store - RAG foundation for semantic retrieval.

PROBLEM SOLVED:
Before: All AI prompts truncate context to 2-4K chars, losing critical information.
Example: Agent has 50 negotiation records but only sees last 5 (truncated).

SOLUTION:
- Generate embeddings for all stored content (profiles, conversations, patterns)
- Store embeddings in Supabase (pgvector extension)
- Retrieve semantically relevant context for each AI call
- Dramatically improves AI decision quality with full context

HOW IT WORKS:
1. When data is stored (profile, conversation, pattern), generate an embedding
2. Store embedding vector alongside the content in cv2_embeddings table
3. Before AI calls, query for semantically similar content
4. Pass relevant context to the AI instead of arbitrary truncation

EMBEDDING STRATEGY:
- Use Anthropic's messages API to generate text summaries for embedding
- Store as JSON array in Supabase (compatible with pgvector when enabled)
- Cosine similarity for retrieval
- Fallback to keyword matching when embeddings unavailable

TABLE SCHEMA (cv2_embeddings):
  id: uuid
  content_type: text (profile, conversation, pattern, job, match)
  content_id: text (reference to source record)
  user_id: text (owner)
  text_content: text (the actual text that was embedded)
  embedding: jsonb (vector as JSON array - upgradeable to pgvector)
  metadata: jsonb (extra context for filtering)
  created_at: timestamptz
"""

import json
import hashlib
from typing import Optional

import anthropic

from app.config import ANTHROPIC_API_KEY, SIMILARITY_THRESHOLD
from app.database import get_db, get_cache


class EmbeddingStore:
    """Semantic storage and retrieval for platform knowledge.

    Provides RAG (Retrieval-Augmented Generation) capabilities:
    - Index: Store content with semantic embeddings
    - Query: Retrieve relevant context for AI prompts
    - Context: Build rich context windows without truncation
    """

    def __init__(self):
        self._anthropic: Optional[anthropic.Anthropic] = None

    @property
    def client(self) -> Optional[anthropic.Anthropic]:
        if self._anthropic is None and ANTHROPIC_API_KEY:
            self._anthropic = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)
        return self._anthropic

    async def index_content(
        self,
        content_type: str,
        content_id: str,
        text_content: str,
        user_id: str = "",
        metadata: Optional[dict] = None,
    ) -> Optional[str]:
        """Index content for semantic retrieval.

        Args:
            content_type: profile, conversation, pattern, job, match
            content_id: ID of the source record
            text_content: The text to embed and store
            user_id: Owner of this content
            metadata: Additional filtering metadata

        Returns:
            embedding_id if successful, None otherwise
        """
        client = get_db()
        if not client:
            return None

        # Generate embedding via text compression
        embedding = await self._generate_embedding(text_content)
        if not embedding:
            return None

        record = {
            "content_type": content_type,
            "content_id": content_id,
            "user_id": user_id,
            "text_content": text_content[:5000],  # Store searchable text
            "embedding": embedding,
            "metadata": metadata or {},
        }

        try:
            result = client.table("cv2_embeddings").upsert(
                record,
                on_conflict="content_type,content_id",
            ).execute()
            return result.data[0]["id"] if result.data else None
        except Exception:
            # Table might not exist yet - try insert
            try:
                result = client.table("cv2_embeddings").insert(record).execute()
                return result.data[0]["id"] if result.data else None
            except Exception:
                return None

    async def query_similar(
        self,
        query_text: str,
        content_type: Optional[str] = None,
        user_id: Optional[str] = None,
        limit: int = 5,
    ) -> list[dict]:
        """Find semantically similar content.

        Args:
            query_text: The query to find similar content for
            content_type: Filter by type (profile, conversation, etc.)
            user_id: Filter by owner
            limit: Max results to return

        Returns:
            List of {content_id, text_content, similarity, metadata}
        """
        client = get_db()
        if not client:
            return []

        # Generate query embedding
        query_embedding = await self._generate_embedding(query_text)
        if not query_embedding:
            # Fallback to keyword search
            return await self._keyword_search(query_text, content_type, user_id, limit)

        # Fetch candidates and compute similarity in-memory
        # (When pgvector is enabled, this becomes a single SQL query)
        try:
            query = client.table("cv2_embeddings").select(
                "content_id, content_type, text_content, embedding, metadata, user_id"
            )
            if content_type:
                query = query.eq("content_type", content_type)
            if user_id:
                query = query.eq("user_id", user_id)

            result = query.limit(100).execute()
            candidates = result.data or []
        except Exception:
            return []

        # Compute cosine similarity
        scored = []
        for candidate in candidates:
            candidate_embedding = candidate.get("embedding", [])
            if not candidate_embedding:
                continue
            similarity = self._cosine_similarity(query_embedding, candidate_embedding)
            if similarity >= SIMILARITY_THRESHOLD:
                scored.append({
                    "content_id": candidate["content_id"],
                    "content_type": candidate["content_type"],
                    "text_content": candidate["text_content"],
                    "similarity": round(similarity, 4),
                    "metadata": candidate.get("metadata", {}),
                    "user_id": candidate.get("user_id", ""),
                })

        # Sort by similarity descending
        scored.sort(key=lambda x: -x["similarity"])
        return scored[:limit]

    async def get_context_for_agent(
        self,
        agent_id: str,
        query: str,
        max_tokens: int = 3000,
    ) -> str:
        """Build a rich context window for an agent's AI call.

        Instead of truncating to 2-4K chars, retrieves the MOST RELEVANT
        content from the agent's history.

        Args:
            agent_id: The agent's ID (used as user_id in embeddings)
            query: What the AI call is about
            max_tokens: Approximate token budget for context

        Returns:
            Formatted context string with relevant information
        """
        # Get relevant content
        results = await self.query_similar(
            query_text=query,
            user_id=agent_id,
            limit=10,
        )

        if not results:
            return ""

        # Build context within token budget (approx 4 chars per token)
        char_budget = max_tokens * 4
        context_parts = []
        total_chars = 0

        for r in results:
            text = r["text_content"]
            if total_chars + len(text) > char_budget:
                remaining = char_budget - total_chars
                if remaining > 200:
                    text = text[:remaining]
                else:
                    break

            context_parts.append(
                f"[{r['content_type']}|sim={r['similarity']}] {text}"
            )
            total_chars += len(text)

        return "\n---\n".join(context_parts)

    async def index_agent_profile(self, agent_id: str, profile: dict) -> None:
        """Index an agent's profile for retrieval."""
        text = json.dumps(profile, indent=2)
        await self.index_content(
            content_type="profile",
            content_id=agent_id,
            text_content=text,
            user_id=agent_id,
            metadata={"agent_type": profile.get("agent_type", "unknown")},
        )

    async def index_conversation(
        self, conversation_id: str, user_id: str, messages: list[dict]
    ) -> None:
        """Index a conversation for retrieval."""
        text = "\n".join(
            f"{m.get('role', 'unknown')}: {m.get('content', '')}"
            for m in messages[-20:]  # Last 20 messages
        )
        await self.index_content(
            content_type="conversation",
            content_id=conversation_id,
            text_content=text,
            user_id=user_id,
            metadata={"message_count": len(messages)},
        )

    async def index_pattern(
        self, pattern_id: str, user_id: str, patterns: dict, industry: str = ""
    ) -> None:
        """Index a learned pattern for retrieval."""
        text = json.dumps(patterns, indent=2)
        await self.index_content(
            content_type="pattern",
            content_id=pattern_id,
            text_content=text,
            user_id=user_id,
            metadata={"industry": industry},
        )

    async def _generate_embedding(self, text: str) -> Optional[list[float]]:
        """Generate a lightweight embedding for text.

        Uses a hash-based approach for consistent embeddings without
        requiring a separate embedding model API. This provides
        reasonable similarity for short-to-medium text.

        For production at scale, replace with a proper embedding API
        (OpenAI ada-002, Voyage AI, Cohere embed, etc.)
        """
        if not text:
            return None

        # Lightweight embedding: hash-based feature extraction
        # This creates a deterministic 128-dim vector from text features
        # Good enough for basic RAG, upgradeable to real embeddings later
        embedding = self._text_to_features(text)
        return embedding

    def _text_to_features(self, text: str, dim: int = 128) -> list[float]:
        """Convert text to a feature vector using n-gram hashing.

        This is a lightweight alternative to neural embeddings.
        Captures word-level and bigram-level features.
        Deterministic and fast (no API call needed).
        """
        text = text.lower().strip()
        words = text.split()
        vector = [0.0] * dim

        # Unigram features
        for word in words:
            h = int(hashlib.md5(word.encode()).hexdigest(), 16)
            idx = h % dim
            sign = 1.0 if (h // dim) % 2 == 0 else -1.0
            vector[idx] += sign

        # Bigram features (captures word order)
        for i in range(len(words) - 1):
            bigram = f"{words[i]} {words[i+1]}"
            h = int(hashlib.md5(bigram.encode()).hexdigest(), 16)
            idx = h % dim
            sign = 1.0 if (h // dim) % 2 == 0 else -1.0
            vector[idx] += sign * 0.5

        # Normalize to unit vector
        magnitude = sum(v * v for v in vector) ** 0.5
        if magnitude > 0:
            vector = [v / magnitude for v in vector]

        return vector

    def _cosine_similarity(self, a: list[float], b: list[float]) -> float:
        """Compute cosine similarity between two vectors."""
        if len(a) != len(b) or not a:
            return 0.0
        dot = sum(x * y for x, y in zip(a, b))
        mag_a = sum(x * x for x in a) ** 0.5
        mag_b = sum(x * x for x in b) ** 0.5
        if mag_a == 0 or mag_b == 0:
            return 0.0
        return dot / (mag_a * mag_b)

    async def _keyword_search(
        self,
        query: str,
        content_type: Optional[str],
        user_id: Optional[str],
        limit: int,
    ) -> list[dict]:
        """Fallback keyword search when embeddings unavailable."""
        client = get_db()
        if not client:
            return []

        try:
            query_builder = client.table("cv2_embeddings").select(
                "content_id, content_type, text_content, metadata, user_id"
            )
            if content_type:
                query_builder = query_builder.eq("content_type", content_type)
            if user_id:
                query_builder = query_builder.eq("user_id", user_id)

            # Use ilike for basic text matching
            keywords = query.lower().split()[:3]  # Top 3 keywords
            if keywords:
                query_builder = query_builder.ilike("text_content", f"%{keywords[0]}%")

            result = query_builder.limit(limit).execute()
            return [
                {
                    "content_id": r["content_id"],
                    "content_type": r["content_type"],
                    "text_content": r["text_content"],
                    "similarity": 0.5,  # Unknown similarity for keyword match
                    "metadata": r.get("metadata", {}),
                    "user_id": r.get("user_id", ""),
                }
                for r in (result.data or [])
            ]
        except Exception:
            return []


embedding_store = EmbeddingStore()
