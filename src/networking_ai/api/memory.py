"""
Memory API Endpoints - Phase 10A Enhanced Memory System.

REST API for multi-tier memory management with intelligent caching.
"""

from typing import Optional, List
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session
from pydantic import BaseModel, Field
import time

from ..database import get_db
from ..models.user import User
from ..models.memory import UserMemory, MemoryTier, MemoryType
from ..memory import MemoryOrchestrator, Memory
from ..cache.redis_client import RedisClient
from ..services.chromadb_service import ChromaDBService
from ..services.pdf_ingestion_service import PDFIngestionService
from ..services.memory_analytics_service import MemoryAnalyticsService


# ==================== Request/Response Models ====================

class MemoryQueryRequest(BaseModel):
    """Request for querying memories."""
    query: str = Field(..., description="Search query")
    limit: int = Field(10, ge=1, le=100, description="Maximum results")
    tiers: Optional[List[str]] = Field(None, description="Specific tiers to search")


class MemoryStoreRequest(BaseModel):
    """Request for storing a new memory."""
    content: str = Field(..., min_length=1, max_length=10000, description="Memory content")
    metadata: Optional[dict] = Field(None, description="Optional metadata")
    importance: float = Field(0.5, ge=0.0, le=1.0, description="Importance score")
    memory_type: str = Field("conversation", description="Type of memory")
    tier: str = Field("auto", description="Target tier (hot/warm/cold/auto)")


class MemoryResponse(BaseModel):
    """Memory response."""
    id: int
    user_id: int
    content: str
    metadata: dict
    created_at: str
    last_accessed: str
    access_count: int
    importance: float
    tier: str
    score: float = 0.0

    @classmethod
    def from_memory(cls, memory: Memory) -> 'MemoryResponse':
        """Create from Memory object."""
        return cls(
            id=memory.id,
            user_id=memory.user_id,
            content=memory.content,
            metadata=memory.metadata,
            created_at=memory.created_at.isoformat() if isinstance(memory.created_at, datetime) else memory.created_at,
            last_accessed=memory.last_accessed.isoformat() if isinstance(memory.last_accessed, datetime) else memory.last_accessed,
            access_count=memory.access_count,
            importance=memory.importance,
            tier=memory.tier,
            score=memory.score
        )


class MemoryQueryResponse(BaseModel):
    """Query response with results and metadata."""
    success: bool
    results: List[MemoryResponse]
    query: str
    total_results: int
    query_time_ms: float
    tiers_searched: List[str]


class MemoryStatsResponse(BaseModel):
    """Memory statistics response."""
    total_memories: int
    tier_distribution: dict
    avg_importance: float
    cache_performance: Optional[dict] = None


class MemoryAnalyticsResponse(BaseModel):
    """Memory analytics response."""
    user_id: int
    time_window_hours: int
    cache_performance: dict
    performance: dict
    tier_distribution: dict
    total_memories: int


class PDFIngestResponse(BaseModel):
    """PDF ingestion response."""
    success: bool
    filename: str
    total_chunks: Optional[int] = None
    stored_memories: Optional[int] = None
    memory_ids: Optional[List[int]] = None
    error: Optional[str] = None


# ==================== Dependencies ====================

def get_memory_orchestrator(
    db: Session = Depends(get_db)
) -> MemoryOrchestrator:
    """
    Dependency to get MemoryOrchestrator instance.

    Args:
        db: Database session

    Returns:
        MemoryOrchestrator instance
    """
    # Initialize dependencies
    redis_client = RedisClient()
    chromadb_service = ChromaDBService()

    # Create orchestrator
    return MemoryOrchestrator(
        db_session=db,
        redis_client=redis_client,
        chromadb_service=chromadb_service
    )


def get_analytics_service(
    db: Session = Depends(get_db)
) -> MemoryAnalyticsService:
    """
    Dependency to get MemoryAnalyticsService instance.

    Args:
        db: Database session

    Returns:
        MemoryAnalyticsService instance
    """
    return MemoryAnalyticsService(db)


def get_current_user() -> User:
    """
    Dependency to get current authenticated user.

    TODO: Implement proper JWT authentication
    For now, returns mock user.

    Returns:
        User instance
    """
    # Mock user for development
    # In production, this should validate JWT token and return actual user
    user = User()
    user.id = 1
    user.email = "test@example.com"
    return user


# ==================== Router ====================

router = APIRouter(prefix="/api/v1/memory", tags=["memory"])


# ==================== Endpoints ====================

@router.post("/query", response_model=MemoryQueryResponse)
async def query_memories(
    request: MemoryQueryRequest,
    orchestrator: MemoryOrchestrator = Depends(get_memory_orchestrator),
    analytics: MemoryAnalyticsService = Depends(get_analytics_service),
    current_user: User = Depends(get_current_user)
):
    """
    Query memories with intelligent tier routing.

    Searches across hot/warm/cold tiers with automatic fallback.

    Args:
        request: Query request
        orchestrator: Memory orchestrator
        analytics: Analytics service
        current_user: Authenticated user

    Returns:
        Query results with metadata
    """
    try:
        start_time = time.time()

        # Query memories
        memories = orchestrator.query(
            user_id=current_user.id,
            query=request.query,
            limit=request.limit,
            tiers=request.tiers
        )

        # Calculate query time
        query_time_ms = (time.time() - start_time) * 1000

        # Determine which tier was hit
        tier_hit = 'miss'
        if memories:
            if memories[0].tier == 'hot':
                tier_hit = 'hot'
            elif memories[0].tier == 'warm':
                tier_hit = 'warm'
            elif memories[0].tier == 'cold':
                tier_hit = 'cold'

        # Record analytics
        analytics.record_query(
            user_id=current_user.id,
            tier_hit=tier_hit,
            query_time_ms=query_time_ms
        )

        # Convert to response format
        results = [MemoryResponse.from_memory(m) for m in memories]

        return MemoryQueryResponse(
            success=True,
            results=results,
            query=request.query,
            total_results=len(results),
            query_time_ms=round(query_time_ms, 2),
            tiers_searched=request.tiers or ['hot', 'warm', 'cold']
        )

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Memory query failed: {str(e)}"
        )


@router.post("/store", response_model=MemoryResponse)
async def store_memory(
    request: MemoryStoreRequest,
    orchestrator: MemoryOrchestrator = Depends(get_memory_orchestrator),
    current_user: User = Depends(get_current_user)
):
    """
    Store a new memory with intelligent tier placement.

    Args:
        request: Store request
        orchestrator: Memory orchestrator
        current_user: Authenticated user

    Returns:
        Stored memory details
    """
    try:
        # Store memory
        memory = orchestrator.store(
            user_id=current_user.id,
            content=request.content,
            metadata=request.metadata,
            importance=request.importance,
            memory_type=request.memory_type,
            tier=request.tier
        )

        if not memory:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to store memory"
            )

        return MemoryResponse.from_memory(memory)

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Memory storage failed: {str(e)}"
        )


@router.get("/stats", response_model=MemoryStatsResponse)
async def get_memory_stats(
    orchestrator: MemoryOrchestrator = Depends(get_memory_orchestrator),
    current_user: User = Depends(get_current_user)
):
    """
    Get memory statistics for current user.

    Args:
        orchestrator: Memory orchestrator
        current_user: Authenticated user

    Returns:
        Memory statistics
    """
    try:
        stats = orchestrator.get_stats(current_user.id)

        return MemoryStatsResponse(
            total_memories=stats.get("total_memories", 0),
            tier_distribution=stats.get("tier_distribution", {}),
            avg_importance=stats.get("avg_importance", 0.0),
            cache_performance=stats.get("cache_performance")
        )

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get memory stats: {str(e)}"
        )


@router.get("/analytics", response_model=MemoryAnalyticsResponse)
async def get_memory_analytics(
    hours: int = 24,
    analytics: MemoryAnalyticsService = Depends(get_analytics_service),
    current_user: User = Depends(get_current_user)
):
    """
    Get memory analytics for current user.

    Args:
        hours: Time window in hours (default 24)
        analytics: Analytics service
        current_user: Authenticated user

    Returns:
        Memory analytics
    """
    try:
        data = analytics.get_user_analytics(current_user.id, hours=hours)

        return MemoryAnalyticsResponse(**data)

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get analytics: {str(e)}"
        )


@router.post("/ingest-pdf", response_model=PDFIngestResponse)
async def ingest_pdf(
    file: UploadFile = File(...),
    importance: float = 0.7,
    orchestrator: MemoryOrchestrator = Depends(get_memory_orchestrator),
    current_user: User = Depends(get_current_user)
):
    """
    Ingest a PDF document into memory system.

    Extracts text, chunks intelligently, and stores in appropriate tiers.

    Args:
        file: PDF file upload
        importance: Base importance score (0.0 to 1.0)
        orchestrator: Memory orchestrator
        current_user: Authenticated user

    Returns:
        Ingestion results
    """
    try:
        # Validate file type
        if not file.filename.lower().endswith('.pdf'):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="File must be a PDF"
            )

        # Initialize PDF ingestion service
        pdf_service = PDFIngestionService(orchestrator)

        # Read file content
        content = await file.read()

        # Create file-like object
        from io import BytesIO
        pdf_file = BytesIO(content)

        # Ingest PDF
        result = pdf_service.ingest_pdf(
            user_id=current_user.id,
            pdf_file=pdf_file,
            filename=file.filename,
            importance=importance
        )

        return PDFIngestResponse(**result)

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"PDF ingestion failed: {str(e)}"
        )


@router.delete("/{memory_id}")
async def delete_memory(
    memory_id: int,
    orchestrator: MemoryOrchestrator = Depends(get_memory_orchestrator),
    current_user: User = Depends(get_current_user)
):
    """
    Delete a memory.

    Args:
        memory_id: Memory ID
        orchestrator: Memory orchestrator
        current_user: Authenticated user

    Returns:
        Success response
    """
    try:
        success = orchestrator.delete(current_user.id, memory_id)

        if not success:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Memory not found"
            )

        return {"success": True, "message": f"Memory {memory_id} deleted"}

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to delete memory: {str(e)}"
        )


@router.get("/{memory_id}", response_model=MemoryResponse)
async def get_memory(
    memory_id: int,
    orchestrator: MemoryOrchestrator = Depends(get_memory_orchestrator),
    current_user: User = Depends(get_current_user)
):
    """
    Get a specific memory by ID.

    Args:
        memory_id: Memory ID
        orchestrator: Memory orchestrator
        current_user: Authenticated user

    Returns:
        Memory details
    """
    try:
        memory = orchestrator.get_by_id(current_user.id, memory_id)

        if not memory:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Memory not found"
            )

        return MemoryResponse.from_memory(memory)

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get memory: {str(e)}"
        )
