"""
Marketplace Pydantic Schemas for API request/response validation (Phase 12).
"""

from datetime import datetime
from typing import Optional, List, Dict, Any
from decimal import Decimal
from uuid import UUID
from pydantic import BaseModel, Field, field_validator, ConfigDict

from ..models.marketplace import TemplateCategory, TemplateStatus


# ============================================================================
# Request Schemas - Template Management
# ============================================================================

class TemplateCreateRequest(BaseModel):
    """Create a new agent template."""
    name: str = Field(..., min_length=3, max_length=255, description="Template name")
    description: str = Field(..., min_length=10, max_length=5000, description="Template description")
    category: TemplateCategory = Field(..., description="Template category")
    tags: List[str] = Field(default_factory=list, max_length=20, description="Search tags")
    price: Decimal = Field(default=Decimal('0.00'), ge=0, le=999.99, description="Price in USD")

    # Configuration
    configuration: Dict[str, Any] = Field(..., description="Agent configuration JSON")
    prompt_template: str = Field(..., min_length=50, description="Agent system prompt template")
    knowledge_sources: Dict[str, Any] = Field(default_factory=dict, description="Knowledge base configuration")
    sub_agents: List[Dict[str, Any]] = Field(default_factory=list, description="Sub-agent configurations")

    # Metadata
    icon_url: Optional[str] = Field(None, max_length=500, description="Template icon URL")
    screenshots: List[str] = Field(default_factory=list, max_length=10, description="Screenshot URLs")
    demo_url: Optional[str] = Field(None, max_length=500, description="Demo video/page URL")

    # Version
    version: str = Field(default="1.0.0", pattern=r'^\d+\.\d+\.\d+$', description="Semantic version")
    changelog: Optional[str] = Field(None, max_length=2000, description="Version changelog")

    @field_validator('tags')
    @classmethod
    def validate_tags(cls, v):
        """Validate tags."""
        if v and len(v) > 20:
            raise ValueError('Maximum 20 tags allowed')
        # Remove duplicates and validate each tag
        unique_tags = []
        for tag in v:
            if len(tag) < 2 or len(tag) > 50:
                raise ValueError('Each tag must be between 2 and 50 characters')
            if tag.lower() not in [t.lower() for t in unique_tags]:
                unique_tags.append(tag.lower())
        return unique_tags

    @field_validator('screenshots')
    @classmethod
    def validate_screenshots(cls, v):
        """Validate screenshot URLs."""
        if v and len(v) > 10:
            raise ValueError('Maximum 10 screenshots allowed')
        return v

    model_config = ConfigDict(from_attributes=True)


class TemplateUpdateRequest(BaseModel):
    """Update an existing template."""
    name: Optional[str] = Field(None, min_length=3, max_length=255)
    description: Optional[str] = Field(None, min_length=10, max_length=5000)
    category: Optional[TemplateCategory] = None
    tags: Optional[List[str]] = Field(None, max_length=20)
    price: Optional[Decimal] = Field(None, ge=0, le=999.99)

    configuration: Optional[Dict[str, Any]] = None
    prompt_template: Optional[str] = Field(None, min_length=50)
    knowledge_sources: Optional[Dict[str, Any]] = None
    sub_agents: Optional[List[Dict[str, Any]]] = None

    icon_url: Optional[str] = Field(None, max_length=500)
    screenshots: Optional[List[str]] = Field(None, max_length=10)
    demo_url: Optional[str] = Field(None, max_length=500)

    version: Optional[str] = Field(None, pattern=r'^\d+\.\d+\.\d+$')
    changelog: Optional[str] = Field(None, max_length=2000)

    model_config = ConfigDict(from_attributes=True)


class TemplatePublishRequest(BaseModel):
    """Publish a template to the marketplace."""
    submit_for_review: bool = Field(default=True, description="Submit for admin review if paid template")

    model_config = ConfigDict(from_attributes=True)


# ============================================================================
# Request Schemas - Installation
# ============================================================================

class TemplateInstallRequest(BaseModel):
    """Install a template."""
    agent_name: Optional[str] = Field(None, min_length=3, max_length=255, description="Custom agent name")
    customized: bool = Field(default=False, description="Is this a customized installation?")
    custom_configuration: Optional[Dict[str, Any]] = Field(None, description="Custom configuration overrides")

    model_config = ConfigDict(from_attributes=True)


# ============================================================================
# Request Schemas - Reviews
# ============================================================================

class ReviewCreateRequest(BaseModel):
    """Create a review for a template."""
    rating: int = Field(..., ge=1, le=5, description="Rating (1-5 stars)")
    title: Optional[str] = Field(None, min_length=3, max_length=255, description="Review title")
    review_text: Optional[str] = Field(None, min_length=10, max_length=2000, description="Review content")

    model_config = ConfigDict(from_attributes=True)


class ReviewUpdateRequest(BaseModel):
    """Update a review."""
    rating: Optional[int] = Field(None, ge=1, le=5)
    title: Optional[str] = Field(None, min_length=3, max_length=255)
    review_text: Optional[str] = Field(None, min_length=10, max_length=2000)

    model_config = ConfigDict(from_attributes=True)


class CreatorResponseRequest(BaseModel):
    """Creator response to a review."""
    response: str = Field(..., min_length=10, max_length=1000, description="Response to review")

    model_config = ConfigDict(from_attributes=True)


# ============================================================================
# Request Schemas - Comments
# ============================================================================

class CommentCreateRequest(BaseModel):
    """Create a comment on a template."""
    comment_text: str = Field(..., min_length=2, max_length=2000, description="Comment content")
    parent_comment_id: Optional[UUID] = Field(None, description="Parent comment ID for replies")

    model_config = ConfigDict(from_attributes=True)


# ============================================================================
# Request Schemas - Search & Discovery
# ============================================================================

class TemplateSearchRequest(BaseModel):
    """Search and filter templates."""
    query: Optional[str] = Field(None, min_length=1, max_length=255, description="Search query")
    category: Optional[TemplateCategory] = Field(None, description="Filter by category")
    tags: Optional[List[str]] = Field(None, description="Filter by tags")
    min_rating: Optional[float] = Field(None, ge=0, le=5, description="Minimum average rating")
    max_price: Optional[Decimal] = Field(None, ge=0, description="Maximum price")
    free_only: bool = Field(default=False, description="Show only free templates")
    featured_only: bool = Field(default=False, description="Show only featured templates")
    sort_by: str = Field(default="popular", description="Sort order")  # popular, recent, rating, price
    page: int = Field(default=1, ge=1, description="Page number")
    page_size: int = Field(default=20, ge=1, le=100, description="Results per page")

    @field_validator('sort_by')
    @classmethod
    def validate_sort_by(cls, v):
        """Validate sort order."""
        allowed = ['popular', 'recent', 'rating', 'price_low', 'price_high', 'name']
        if v not in allowed:
            raise ValueError(f'sort_by must be one of: {", ".join(allowed)}')
        return v

    model_config = ConfigDict(from_attributes=True)


# ============================================================================
# Response Schemas - Template
# ============================================================================

class TemplateResponse(BaseModel):
    """Template response (basic info)."""
    id: UUID
    creator_id: int
    name: str
    description: str
    category: TemplateCategory
    tags: List[str]
    status: TemplateStatus
    is_featured: bool
    is_verified: bool
    price: Decimal
    version: str
    icon_url: Optional[str]
    screenshots: List[str]
    demo_url: Optional[str]

    # Statistics
    downloads_count: int
    installations_count: int
    average_rating: Decimal
    review_count: int

    # Timestamps
    created_at: datetime
    updated_at: datetime
    published_at: Optional[datetime]

    model_config = ConfigDict(from_attributes=True)


class TemplateDetailResponse(BaseModel):
    """Detailed template response (includes configuration)."""
    id: UUID
    creator_id: int
    name: str
    description: str
    category: TemplateCategory
    tags: List[str]
    status: TemplateStatus
    is_featured: bool
    is_verified: bool
    price: Decimal
    version: str
    changelog: Optional[str]

    # Configuration
    configuration: Dict[str, Any]
    prompt_template: str
    knowledge_sources: Dict[str, Any]
    sub_agents: List[Dict[str, Any]]

    # Metadata
    icon_url: Optional[str]
    screenshots: List[str]
    demo_url: Optional[str]

    # Statistics
    downloads_count: int
    installations_count: int
    revenue_total: Decimal
    average_rating: Decimal
    review_count: int

    # Timestamps
    created_at: datetime
    updated_at: datetime
    published_at: Optional[datetime]

    model_config = ConfigDict(from_attributes=True)


class TemplateListResponse(BaseModel):
    """Paginated list of templates."""
    templates: List[TemplateResponse]
    total: int
    page: int
    page_size: int
    total_pages: int

    model_config = ConfigDict(from_attributes=True)


# ============================================================================
# Response Schemas - Purchase
# ============================================================================

class PurchaseResponse(BaseModel):
    """Purchase response."""
    id: UUID
    template_id: UUID
    buyer_id: int
    price_paid: Decimal
    purchased_at: datetime
    refunded: bool

    model_config = ConfigDict(from_attributes=True)


class CheckoutSessionResponse(BaseModel):
    """Stripe checkout session response."""
    session_id: str
    session_url: str
    template_id: UUID
    amount: Decimal

    model_config = ConfigDict(from_attributes=True)


# ============================================================================
# Response Schemas - Review
# ============================================================================

class ReviewResponse(BaseModel):
    """Review response."""
    id: UUID
    template_id: UUID
    user_id: int
    rating: int
    title: Optional[str]
    review_text: Optional[str]
    helpful_count: int
    is_verified_purchase: bool
    creator_response: Optional[str]
    creator_responded_at: Optional[datetime]
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class ReviewListResponse(BaseModel):
    """Paginated list of reviews."""
    reviews: List[ReviewResponse]
    total: int
    page: int
    page_size: int
    average_rating: Decimal

    model_config = ConfigDict(from_attributes=True)


# ============================================================================
# Response Schemas - Installation
# ============================================================================

class InstallationResponse(BaseModel):
    """Installation response."""
    id: UUID
    template_id: UUID
    user_id: int
    agent_id: Optional[int]
    customized: bool
    installation_successful: bool
    error_message: Optional[str]
    installed_at: datetime

    model_config = ConfigDict(from_attributes=True)


# ============================================================================
# Response Schemas - Creator
# ============================================================================

class CreatorStatsResponse(BaseModel):
    """Creator statistics."""
    creator_id: int
    total_templates: int
    published_templates: int
    total_downloads: int
    total_installations: int
    total_revenue: Decimal
    average_rating: Decimal
    total_reviews: int
    follower_count: int

    model_config = ConfigDict(from_attributes=True)


class CreatorDashboardResponse(BaseModel):
    """Creator dashboard data."""
    stats: CreatorStatsResponse
    templates: List[TemplateResponse]
    recent_reviews: List[ReviewResponse]
    revenue_by_month: Dict[str, Decimal]

    model_config = ConfigDict(from_attributes=True)


class CreatorEarningsResponse(BaseModel):
    """Creator earnings breakdown."""
    total_revenue: Decimal
    platform_commission: Decimal  # 20%
    net_earnings: Decimal  # 80%
    pending_payout: Decimal
    lifetime_earnings: Decimal
    earnings_by_template: List[Dict[str, Any]]

    model_config = ConfigDict(from_attributes=True)


# ============================================================================
# Response Schemas - Comments
# ============================================================================

class CommentResponse(BaseModel):
    """Comment response."""
    id: UUID
    template_id: UUID
    user_id: int
    parent_comment_id: Optional[UUID]
    comment_text: str
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


# ============================================================================
# Response Schemas - Analytics
# ============================================================================

class TemplateAnalyticsResponse(BaseModel):
    """Template analytics data."""
    template_id: UUID
    views_count: int
    downloads_count: int
    installations_count: int
    installation_success_rate: float
    revenue_total: Decimal
    average_rating: Decimal
    review_count: int
    views_by_day: Dict[str, int]
    installations_by_day: Dict[str, int]
    revenue_by_day: Dict[str, Decimal]

    model_config = ConfigDict(from_attributes=True)
