"""
Marketplace API Endpoints (Phase 12).

AI Agent Template Marketplace for publishing, discovering, and installing templates.
"""

from typing import List, Optional
from decimal import Decimal
from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from sqlalchemy import and_, or_, desc, asc, func
from datetime import datetime

from ..database import get_db
from ..models.user import User
from ..models.marketplace import (
    AgentTemplate, TemplatePurchase, TemplateReview, TemplateInstallation,
    CreatorFollow, TemplateComment, TemplateCategory, TemplateStatus
)
from ..models.personal_ai_agent import PersonalAIAgent, AgentStatus
from ..api.auth import get_current_active_user
from ..schemas.marketplace import (
    # Requests
    TemplateCreateRequest, TemplateUpdateRequest, TemplatePublishRequest,
    TemplateInstallRequest, ReviewCreateRequest, ReviewUpdateRequest,
    CreatorResponseRequest, CommentCreateRequest, TemplateSearchRequest,
    # Responses
    TemplateResponse, TemplateDetailResponse, TemplateListResponse,
    PurchaseResponse, CheckoutSessionResponse, ReviewResponse, ReviewListResponse,
    InstallationResponse, CreatorStatsResponse, CreatorDashboardResponse,
    CreatorEarningsResponse, CommentResponse, TemplateAnalyticsResponse
)


router = APIRouter()


# ============================================================================
# Template Management Endpoints
# ============================================================================

@router.post("/templates", response_model=TemplateDetailResponse, status_code=status.HTTP_201_CREATED)
async def create_template(
    template_data: TemplateCreateRequest,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """
    Create a new agent template.

    Creates a template in draft status. Creator can later publish it to the marketplace.
    """
    # Create template
    template = AgentTemplate(
        creator_id=current_user.id,
        **template_data.model_dump()
    )

    db.add(template)
    db.commit()
    db.refresh(template)

    return template


@router.get("/templates/{template_id}", response_model=TemplateDetailResponse)
async def get_template(
    template_id: UUID,
    db: Session = Depends(get_db),
    current_user: Optional[User] = Depends(get_current_active_user)
):
    """
    Get template details.

    Returns full template configuration if user is creator or has purchased.
    Returns limited info if template is published and user hasn't purchased.
    """
    template = db.query(AgentTemplate).filter(AgentTemplate.id == template_id).first()

    if not template:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Template not found"
        )

    # Check if user can view this template
    is_creator = current_user and template.creator_id == current_user.id
    is_published = template.status == TemplateStatus.PUBLISHED
    has_purchased = False

    if current_user and template.price > 0:
        has_purchased = db.query(TemplatePurchase).filter(
            TemplatePurchase.template_id == template_id,
            TemplatePurchase.buyer_id == current_user.id,
            TemplatePurchase.refunded == False
        ).first() is not None

    # Allow access if creator, published free template, or purchased
    if not (is_creator or (is_published and template.price == 0) or has_purchased):
        if not is_published:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Template not found"
            )
        elif template.price > 0:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Purchase required to view full template details"
            )

    return template


@router.put("/templates/{template_id}", response_model=TemplateDetailResponse)
async def update_template(
    template_id: UUID,
    template_data: TemplateUpdateRequest,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """
    Update an existing template.

    Only the template creator can update it.
    """
    template = db.query(AgentTemplate).filter(
        AgentTemplate.id == template_id,
        AgentTemplate.creator_id == current_user.id
    ).first()

    if not template:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Template not found"
        )

    # Update fields
    update_data = template_data.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(template, field, value)

    template.updated_at = datetime.utcnow()

    db.commit()
    db.refresh(template)

    return template


@router.delete("/templates/{template_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_template(
    template_id: UUID,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """
    Delete a template.

    Only the creator can delete. Cannot delete if there are purchases.
    """
    template = db.query(AgentTemplate).filter(
        AgentTemplate.id == template_id,
        AgentTemplate.creator_id == current_user.id
    ).first()

    if not template:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Template not found"
        )

    # Check if template has purchases
    purchase_count = db.query(TemplatePurchase).filter(
        TemplatePurchase.template_id == template_id
    ).count()

    if purchase_count > 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot delete template with existing purchases. Archive it instead."
        )

    db.delete(template)
    db.commit()


@router.put("/templates/{template_id}/publish", response_model=TemplateDetailResponse)
async def publish_template(
    template_id: UUID,
    publish_data: TemplatePublishRequest,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """
    Publish a template to the marketplace.

    Free templates are published immediately.
    Paid templates go to pending review status.
    """
    template = db.query(AgentTemplate).filter(
        AgentTemplate.id == template_id,
        AgentTemplate.creator_id == current_user.id
    ).first()

    if not template:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Template not found"
        )

    if template.status not in [TemplateStatus.DRAFT, TemplateStatus.REJECTED]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Cannot publish template with status: {template.status}"
        )

    # Free templates can be published immediately
    # Paid templates need review
    if template.price == 0:
        template.status = TemplateStatus.PUBLISHED
        template.published_at = datetime.utcnow()
    else:
        if publish_data.submit_for_review:
            template.status = TemplateStatus.PENDING_REVIEW
        else:
            template.status = TemplateStatus.PUBLISHED
            template.published_at = datetime.utcnow()

    db.commit()
    db.refresh(template)

    return template


# ============================================================================
# Marketplace Discovery Endpoints
# ============================================================================

@router.get("/templates", response_model=TemplateListResponse)
async def search_templates(
    query: Optional[str] = None,
    category: Optional[TemplateCategory] = None,
    tags: Optional[List[str]] = Query(None),
    min_rating: Optional[float] = Query(None, ge=0, le=5),
    max_price: Optional[Decimal] = Query(None, ge=0),
    free_only: bool = False,
    featured_only: bool = False,
    sort_by: str = "popular",
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db)
):
    """
    Search and filter marketplace templates.

    Supports filtering by category, price, rating, and tags.
    Supports multiple sort orders.
    """
    # Base query - only published templates
    base_query = db.query(AgentTemplate).filter(
        AgentTemplate.status == TemplateStatus.PUBLISHED
    )

    # Apply filters
    if query:
        search_filter = or_(
            AgentTemplate.name.ilike(f"%{query}%"),
            AgentTemplate.description.ilike(f"%{query}%"),
            AgentTemplate.tags.contains([query.lower()])
        )
        base_query = base_query.filter(search_filter)

    if category:
        base_query = base_query.filter(AgentTemplate.category == category)

    if tags:
        for tag in tags:
            base_query = base_query.filter(AgentTemplate.tags.contains([tag.lower()]))

    if min_rating is not None:
        base_query = base_query.filter(AgentTemplate.average_rating >= min_rating)

    if max_price is not None:
        base_query = base_query.filter(AgentTemplate.price <= max_price)

    if free_only:
        base_query = base_query.filter(AgentTemplate.price == 0)

    if featured_only:
        base_query = base_query.filter(AgentTemplate.is_featured == True)

    # Apply sorting
    if sort_by == "popular":
        base_query = base_query.order_by(desc(AgentTemplate.downloads_count))
    elif sort_by == "recent":
        base_query = base_query.order_by(desc(AgentTemplate.published_at))
    elif sort_by == "rating":
        base_query = base_query.order_by(desc(AgentTemplate.average_rating))
    elif sort_by == "price_low":
        base_query = base_query.order_by(asc(AgentTemplate.price))
    elif sort_by == "price_high":
        base_query = base_query.order_by(desc(AgentTemplate.price))
    elif sort_by == "name":
        base_query = base_query.order_by(asc(AgentTemplate.name))

    # Get total count
    total = base_query.count()

    # Pagination
    offset = (page - 1) * page_size
    templates = base_query.offset(offset).limit(page_size).all()

    total_pages = (total + page_size - 1) // page_size

    return {
        "templates": templates,
        "total": total,
        "page": page,
        "page_size": page_size,
        "total_pages": total_pages
    }


@router.get("/categories", response_model=List[dict])
async def get_categories():
    """
    Get all available template categories.
    """
    categories = [
        {"value": cat.value, "label": cat.name.replace("_", " ").title()}
        for cat in TemplateCategory
    ]
    return categories


@router.get("/featured", response_model=List[TemplateResponse])
async def get_featured_templates(
    limit: int = Query(10, ge=1, le=50),
    db: Session = Depends(get_db)
):
    """
    Get featured templates.
    """
    templates = db.query(AgentTemplate).filter(
        AgentTemplate.status == TemplateStatus.PUBLISHED,
        AgentTemplate.is_featured == True
    ).order_by(desc(AgentTemplate.downloads_count)).limit(limit).all()

    return templates


@router.get("/trending", response_model=List[TemplateResponse])
async def get_trending_templates(
    limit: int = Query(10, ge=1, le=50),
    db: Session = Depends(get_db)
):
    """
    Get trending templates (most downloaded in last 30 days).
    """
    # For now, sort by total downloads
    # TODO: Add time-based filtering when we track downloads with timestamps
    templates = db.query(AgentTemplate).filter(
        AgentTemplate.status == TemplateStatus.PUBLISHED
    ).order_by(desc(AgentTemplate.downloads_count)).limit(limit).all()

    return templates


# ============================================================================
# Installation Endpoints
# ============================================================================

@router.post("/templates/{template_id}/install", response_model=InstallationResponse, status_code=status.HTTP_201_CREATED)
async def install_template(
    template_id: UUID,
    install_data: TemplateInstallRequest,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """
    Install a template and create a personal AI agent.

    Free templates can be installed directly.
    Paid templates require prior purchase.
    """
    template = db.query(AgentTemplate).filter(
        AgentTemplate.id == template_id,
        AgentTemplate.status == TemplateStatus.PUBLISHED
    ).first()

    if not template:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Template not found"
        )

    # Check if paid template and verify purchase
    if template.price > 0:
        purchase = db.query(TemplatePurchase).filter(
            TemplatePurchase.template_id == template_id,
            TemplatePurchase.buyer_id == current_user.id,
            TemplatePurchase.refunded == False
        ).first()

        if not purchase:
            raise HTTPException(
                status_code=status.HTTP_402_PAYMENT_REQUIRED,
                detail="Purchase required to install this template"
            )

    # Create agent from template
    agent_name = install_data.agent_name or f"{template.name} - {current_user.full_name}"

    # Merge configuration
    agent_config = template.configuration.copy()
    if install_data.customized and install_data.custom_configuration:
        agent_config.update(install_data.custom_configuration)

    try:
        # Create personal AI agent
        agent = PersonalAIAgent(
            user_id=current_user.id,
            name=agent_name,
            status=AgentStatus.ACTIVE,
            system_prompt=template.prompt_template,
            configuration=agent_config
            # TODO: Handle knowledge_sources and sub_agents
        )

        db.add(agent)
        db.flush()

        # Record installation
        installation = TemplateInstallation(
            template_id=template_id,
            user_id=current_user.id,
            agent_id=agent.id,
            customized=install_data.customized,
            custom_configuration=install_data.custom_configuration if install_data.customized else None,
            installation_successful=True
        )

        db.add(installation)

        # Update template statistics
        template.installations_count += 1
        template.downloads_count += 1

        db.commit()
        db.refresh(installation)

        return installation

    except Exception as e:
        db.rollback()

        # Record failed installation
        installation = TemplateInstallation(
            template_id=template_id,
            user_id=current_user.id,
            agent_id=None,
            customized=install_data.customized,
            installation_successful=False,
            error_message=str(e)
        )

        db.add(installation)
        db.commit()
        db.refresh(installation)

        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to install template: {str(e)}"
        )


# ============================================================================
# Review Endpoints
# ============================================================================

@router.post("/templates/{template_id}/reviews", response_model=ReviewResponse, status_code=status.HTTP_201_CREATED)
async def create_review(
    template_id: UUID,
    review_data: ReviewCreateRequest,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """
    Create a review for a template.

    Users can only review templates they've installed.
    One review per user per template.
    """
    template = db.query(AgentTemplate).filter(AgentTemplate.id == template_id).first()

    if not template:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Template not found"
        )

    # Check if user has installed this template
    installation = db.query(TemplateInstallation).filter(
        TemplateInstallation.template_id == template_id,
        TemplateInstallation.user_id == current_user.id,
        TemplateInstallation.installation_successful == True
    ).first()

    if not installation:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You must install the template before reviewing"
        )

    # Check if user already reviewed
    existing_review = db.query(TemplateReview).filter(
        TemplateReview.template_id == template_id,
        TemplateReview.user_id == current_user.id
    ).first()

    if existing_review:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="You have already reviewed this template. Use PUT to update."
        )

    # Check if this is a verified purchase
    is_verified_purchase = False
    if template.price > 0:
        purchase = db.query(TemplatePurchase).filter(
            TemplatePurchase.template_id == template_id,
            TemplatePurchase.buyer_id == current_user.id,
            TemplatePurchase.refunded == False
        ).first()
        is_verified_purchase = purchase is not None

    # Create review
    review = TemplateReview(
        template_id=template_id,
        user_id=current_user.id,
        is_verified_purchase=is_verified_purchase,
        **review_data.model_dump()
    )

    db.add(review)

    # Update template rating
    template.review_count += 1
    avg_rating = db.query(func.avg(TemplateReview.rating)).filter(
        TemplateReview.template_id == template_id
    ).scalar()
    template.average_rating = Decimal(str(avg_rating)) if avg_rating else Decimal('0')

    db.commit()
    db.refresh(review)

    return review


@router.get("/templates/{template_id}/reviews", response_model=ReviewListResponse)
async def get_template_reviews(
    template_id: UUID,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db)
):
    """
    Get reviews for a template.
    """
    template = db.query(AgentTemplate).filter(AgentTemplate.id == template_id).first()

    if not template:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Template not found"
        )

    # Query reviews
    query = db.query(TemplateReview).filter(
        TemplateReview.template_id == template_id,
        TemplateReview.is_hidden == False
    ).order_by(desc(TemplateReview.created_at))

    total = query.count()
    offset = (page - 1) * page_size
    reviews = query.offset(offset).limit(page_size).all()

    return {
        "reviews": reviews,
        "total": total,
        "page": page,
        "page_size": page_size,
        "average_rating": template.average_rating
    }


# ============================================================================
# Creator Endpoints
# ============================================================================

@router.get("/creator/dashboard", response_model=CreatorDashboardResponse)
async def get_creator_dashboard(
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """
    Get creator dashboard data.
    """
    # Get creator stats
    templates = db.query(AgentTemplate).filter(
        AgentTemplate.creator_id == current_user.id
    ).all()

    total_downloads = sum(t.downloads_count for t in templates)
    total_installations = sum(t.installations_count for t in templates)
    total_revenue = sum(t.revenue_total for t in templates)
    published_count = sum(1 for t in templates if t.status == TemplateStatus.PUBLISHED)

    # Calculate average rating across all templates
    ratings = [t.average_rating for t in templates if t.review_count > 0]
    avg_rating = Decimal(str(sum(ratings) / len(ratings))) if ratings else Decimal('0')

    # Get follower count
    follower_count = db.query(CreatorFollow).filter(
        CreatorFollow.creator_id == current_user.id
    ).count()

    stats = {
        "creator_id": current_user.id,
        "total_templates": len(templates),
        "published_templates": published_count,
        "total_downloads": total_downloads,
        "total_installations": total_installations,
        "total_revenue": total_revenue,
        "average_rating": avg_rating,
        "total_reviews": sum(t.review_count for t in templates),
        "follower_count": follower_count
    }

    # Get recent reviews
    recent_reviews = db.query(TemplateReview).join(AgentTemplate).filter(
        AgentTemplate.creator_id == current_user.id
    ).order_by(desc(TemplateReview.created_at)).limit(10).all()

    # Revenue by month (placeholder - would need actual implementation)
    revenue_by_month = {}

    return {
        "stats": stats,
        "templates": templates,
        "recent_reviews": recent_reviews,
        "revenue_by_month": revenue_by_month
    }


@router.get("/creator/earnings", response_model=CreatorEarningsResponse)
async def get_creator_earnings(
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """
    Get creator earnings breakdown.
    """
    templates = db.query(AgentTemplate).filter(
        AgentTemplate.creator_id == current_user.id
    ).all()

    total_revenue = sum(t.revenue_total for t in templates)
    platform_commission = total_revenue * Decimal('0.20')  # 20%
    net_earnings = total_revenue * Decimal('0.80')  # 80%

    earnings_by_template = [
        {
            "template_id": str(t.id),
            "template_name": t.name,
            "revenue": t.revenue_total,
            "net_earnings": t.revenue_total * Decimal('0.80')
        }
        for t in templates if t.revenue_total > 0
    ]

    return {
        "total_revenue": total_revenue,
        "platform_commission": platform_commission,
        "net_earnings": net_earnings,
        "pending_payout": Decimal('0'),  # TODO: Implement payout tracking
        "lifetime_earnings": net_earnings,
        "earnings_by_template": earnings_by_template
    }


# ============================================================================
# TODO: Additional endpoints to implement
# ============================================================================
# - POST /templates/{template_id}/purchase - Create Stripe checkout
# - POST /webhooks/stripe - Handle Stripe webhooks
# - POST /creators/{creator_id}/follow - Follow a creator
# - DELETE /creators/{creator_id}/follow - Unfollow a creator
# - POST /templates/{template_id}/comments - Add comment
# - GET /templates/{template_id}/comments - List comments
# - PUT /reviews/{review_id}/helpful - Mark review as helpful
# - GET /templates/{template_id}/analytics - Get template analytics
