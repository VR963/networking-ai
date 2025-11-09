"""
PDF Ingestion Service - Document processing for memory system

Features:
- PDF text extraction
- Intelligent chunking (semantic boundaries)
- Metadata extraction (title, author, pages)
- Batch processing
- Error handling and validation
"""

import logging
from typing import List, Dict, Any, Optional, BinaryIO
from datetime import datetime
import hashlib
import re

try:
    import PyPDF2
    PYPDF2_AVAILABLE = True
except ImportError:
    PYPDF2_AVAILABLE = False
    logging.warning("PyPDF2 not available. PDF ingestion will be disabled.")

from ..memory.memory_orchestrator import MemoryOrchestrator

logger = logging.getLogger(__name__)


class PDFChunk:
    """Represents a chunk of PDF text."""

    def __init__(
        self,
        content: str,
        chunk_index: int,
        total_chunks: int,
        metadata: Optional[Dict[str, Any]] = None
    ):
        self.content = content
        self.chunk_index = chunk_index
        self.total_chunks = total_chunks
        self.metadata = metadata or {}

    def to_dict(self) -> dict:
        """Convert to dictionary."""
        return {
            "content": self.content,
            "chunk_index": self.chunk_index,
            "total_chunks": self.total_chunks,
            "metadata": self.metadata
        }


class PDFIngestionService:
    """
    Service for ingesting PDF documents into memory system.

    Features:
    - Extract text from PDF files
    - Chunk text into manageable pieces (1000 chars default)
    - Preserve document metadata
    - Store chunks in memory system
    """

    def __init__(
        self,
        memory_orchestrator: MemoryOrchestrator,
        chunk_size: int = 1000,
        chunk_overlap: int = 200
    ):
        """
        Initialize PDF Ingestion Service.

        Args:
            memory_orchestrator: Memory orchestrator instance
            chunk_size: Target size for chunks in characters (default 1000)
            chunk_overlap: Overlap between chunks for context (default 200)
        """
        if not PYPDF2_AVAILABLE:
            raise ImportError(
                "PyPDF2 is required for PDF ingestion. "
                "Install with: pip install PyPDF2"
            )

        self.orchestrator = memory_orchestrator
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap

    def ingest_pdf(
        self,
        user_id: int,
        pdf_file: BinaryIO,
        filename: str,
        importance: float = 0.7,
        auto_importance: bool = True
    ) -> Dict[str, Any]:
        """
        Ingest a PDF file into the memory system.

        Args:
            user_id: User ID
            pdf_file: PDF file object (binary mode)
            filename: Original filename
            importance: Base importance score (0.0 to 1.0)
            auto_importance: Auto-adjust importance based on content (default True)

        Returns:
            Dictionary with ingestion results
        """
        logger.info(f"Starting PDF ingestion for user {user_id}: {filename}")

        try:
            # 1. Extract text and metadata
            extraction = self._extract_pdf_content(pdf_file, filename)

            if not extraction["success"]:
                return {
                    "success": False,
                    "error": extraction["error"],
                    "filename": filename
                }

            text = extraction["text"]
            metadata = extraction["metadata"]

            # 2. Validate content
            if not text or len(text.strip()) < 50:
                return {
                    "success": False,
                    "error": "PDF contains insufficient text content",
                    "filename": filename
                }

            # 3. Chunk text
            chunks = self._chunk_text(text)

            if not chunks:
                return {
                    "success": False,
                    "error": "Failed to chunk PDF text",
                    "filename": filename
                }

            # 4. Auto-adjust importance if enabled
            if auto_importance:
                importance = self._calculate_importance(text, metadata)

            # 5. Store chunks in memory system
            stored_memories = []

            for chunk in chunks:
                # Prepare chunk metadata
                chunk_metadata = {
                    "source": "pdf_upload",
                    "filename": filename,
                    "chunk_index": chunk.chunk_index,
                    "total_chunks": chunk.total_chunks,
                    "pdf_metadata": metadata,
                    "ingested_at": datetime.utcnow().isoformat()
                }
                chunk_metadata.update(chunk.metadata)

                # Store in memory system
                memory = self.orchestrator.store(
                    user_id=user_id,
                    content=chunk.content,
                    metadata=chunk_metadata,
                    importance=importance,
                    memory_type="document",
                    tier="auto"
                )

                if memory:
                    stored_memories.append(memory.id)

            # 6. Return results
            result = {
                "success": True,
                "filename": filename,
                "total_chunks": len(chunks),
                "stored_memories": len(stored_memories),
                "memory_ids": stored_memories,
                "metadata": metadata,
                "importance": importance,
                "total_characters": len(text)
            }

            logger.info(
                f"PDF ingestion complete for user {user_id}: "
                f"{len(stored_memories)} chunks stored from {filename}"
            )

            return result

        except Exception as e:
            logger.error(f"PDF ingestion error: {str(e)}")
            return {
                "success": False,
                "error": str(e),
                "filename": filename
            }

    def _extract_pdf_content(
        self,
        pdf_file: BinaryIO,
        filename: str
    ) -> Dict[str, Any]:
        """
        Extract text and metadata from PDF file.

        Args:
            pdf_file: PDF file object
            filename: Original filename

        Returns:
            Dictionary with text, metadata, and success status
        """
        try:
            # Read PDF
            pdf_reader = PyPDF2.PdfReader(pdf_file)

            # Extract metadata
            metadata = {
                "filename": filename,
                "num_pages": len(pdf_reader.pages),
                "extracted_at": datetime.utcnow().isoformat()
            }

            # Extract PDF metadata if available
            if pdf_reader.metadata:
                pdf_info = pdf_reader.metadata
                if pdf_info.title:
                    metadata["title"] = pdf_info.title
                if pdf_info.author:
                    metadata["author"] = pdf_info.author
                if pdf_info.subject:
                    metadata["subject"] = pdf_info.subject
                if pdf_info.creator:
                    metadata["creator"] = pdf_info.creator

            # Extract text from all pages
            text_parts = []
            for page_num, page in enumerate(pdf_reader.pages):
                try:
                    page_text = page.extract_text()
                    if page_text:
                        # Add page number marker
                        text_parts.append(f"\n[Page {page_num + 1}]\n{page_text}")
                except Exception as e:
                    logger.warning(f"Failed to extract text from page {page_num + 1}: {str(e)}")

            full_text = "\n".join(text_parts)

            # Clean text
            full_text = self._clean_text(full_text)

            # Calculate file hash for deduplication
            pdf_file.seek(0)
            file_hash = hashlib.sha256(pdf_file.read()).hexdigest()
            metadata["file_hash"] = file_hash

            return {
                "success": True,
                "text": full_text,
                "metadata": metadata
            }

        except Exception as e:
            logger.error(f"PDF extraction error: {str(e)}")
            return {
                "success": False,
                "error": str(e),
                "text": "",
                "metadata": {}
            }

    def _chunk_text(self, text: str) -> List[PDFChunk]:
        """
        Chunk text into manageable pieces with overlap.

        Strategy:
        - Target chunk size: ~1000 characters
        - Overlap: 200 characters for context
        - Respect sentence boundaries when possible
        - Include page markers in metadata

        Args:
            text: Full text to chunk

        Returns:
            List of PDFChunk objects
        """
        chunks = []

        # Split by sentences (approximate)
        sentences = re.split(r'([.!?]+\s+)', text)

        # Reconstruct sentences with punctuation
        full_sentences = []
        for i in range(0, len(sentences) - 1, 2):
            sentence = sentences[i]
            if i + 1 < len(sentences):
                sentence += sentences[i + 1]
            full_sentences.append(sentence)

        # Build chunks
        current_chunk = ""
        chunk_index = 0

        for sentence in full_sentences:
            # Check if adding sentence exceeds chunk size
            if len(current_chunk) + len(sentence) > self.chunk_size and current_chunk:
                # Save current chunk
                chunks.append(current_chunk.strip())

                # Start new chunk with overlap
                # Take last N characters for context
                overlap_text = current_chunk[-self.chunk_overlap:] if len(current_chunk) > self.chunk_overlap else current_chunk
                current_chunk = overlap_text + " " + sentence
                chunk_index += 1
            else:
                current_chunk += " " + sentence

        # Add final chunk
        if current_chunk.strip():
            chunks.append(current_chunk.strip())

        # Convert to PDFChunk objects
        total_chunks = len(chunks)
        pdf_chunks = []

        for idx, chunk_text in enumerate(chunks):
            # Extract page number from chunk if present
            page_match = re.search(r'\[Page (\d+)\]', chunk_text)
            page_num = int(page_match.group(1)) if page_match else None

            chunk = PDFChunk(
                content=chunk_text,
                chunk_index=idx,
                total_chunks=total_chunks,
                metadata={
                    "page": page_num,
                    "char_count": len(chunk_text)
                }
            )
            pdf_chunks.append(chunk)

        return pdf_chunks

    def _clean_text(self, text: str) -> str:
        """
        Clean extracted text.

        Args:
            text: Raw text

        Returns:
            Cleaned text
        """
        # Remove excessive whitespace
        text = re.sub(r'\s+', ' ', text)

        # Remove special characters but keep basic punctuation
        text = re.sub(r'[^\w\s.,!?;:()\[\]-]', '', text)

        # Remove multiple consecutive newlines
        text = re.sub(r'\n{3,}', '\n\n', text)

        return text.strip()

    def _calculate_importance(
        self,
        text: str,
        metadata: Dict[str, Any]
    ) -> float:
        """
        Calculate importance score based on content analysis.

        Factors:
        - Document length (longer = more important, up to a point)
        - Presence of metadata (title, author)
        - Keyword density (technical terms, domain-specific)

        Args:
            text: Document text
            metadata: Document metadata

        Returns:
            Importance score (0.0 to 1.0)
        """
        importance = 0.5  # Base score

        # Factor 1: Document length (normalized)
        # Assume optimal length is 5000-20000 chars
        text_length = len(text)
        if 5000 <= text_length <= 20000:
            importance += 0.2
        elif text_length > 20000:
            importance += 0.15
        elif text_length > 2000:
            importance += 0.1

        # Factor 2: Metadata completeness
        if metadata.get("title"):
            importance += 0.1
        if metadata.get("author"):
            importance += 0.05
        if metadata.get("subject"):
            importance += 0.05

        # Factor 3: Page count (multi-page docs are typically important)
        num_pages = metadata.get("num_pages", 0)
        if num_pages > 10:
            importance += 0.15
        elif num_pages > 5:
            importance += 0.1

        # Normalize to 0.0-1.0
        return min(1.0, max(0.0, importance))
