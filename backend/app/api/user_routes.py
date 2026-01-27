from typing import Optional

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from app.database import get_db

router = APIRouter()


def _get_supabase():
    client = get_db()
    if not client:
        raise HTTPException(status_code=503, detail="Database not configured.")
    return client


class ProfileCreateRequest(BaseModel):
    user_id: str
    industry: str = "general"
    summary: Optional[str] = None


class ProfileUpdateRequest(BaseModel):
    industry: Optional[str] = None
    summary: Optional[str] = None
    stage: Optional[str] = None


class CandidateRegisterRequest(BaseModel):
    user_id: str


class DocumentUploadRequest(BaseModel):
    user_id: str
    filename: str
    content_text: str  # Extracted text content from the document
    doc_type: str = "cv"  # cv, certificate, portfolio, other


class SocialLinksRequest(BaseModel):
    user_id: str
    linkedin: Optional[str] = None
    github: Optional[str] = None
    portfolio: Optional[str] = None
    other: list[str] = []


class AnalyzeProfileRequest(BaseModel):
    user_id: str


# --- STAGES ---
# onboarding: user is chatting with agent (initial)
# calibration: user is doing test opportunities
# certified: Master AI has verified the agent knows the user
# matchable: candidate is registered for A2A matching

VALID_STAGES = ["onboarding", "calibration", "certified", "matchable"]


@router.post("/profile")
async def create_or_update_profile(request: ProfileCreateRequest):
    """Create or update a user profile. Called when user starts chat."""
    client = _get_supabase()

    existing = (
        client.table("cv2_profiles")
        .select("*")
        .eq("user_id", request.user_id)
        .execute()
    )

    if existing.data:
        # Update existing profile
        update_data = {}
        if request.industry:
            update_data["industry"] = request.industry
        if request.summary:
            update_data["summary"] = request.summary
        if update_data:
            client.table("cv2_profiles").update(update_data).eq("user_id", request.user_id).execute()
        return {"status": "updated", "user_id": request.user_id}

    # Create new profile with onboarding stage
    record = {
        "user_id": request.user_id,
        "industry": request.industry,
        "summary": request.summary or "",
        "stage": "onboarding",
    }
    client.table("cv2_profiles").insert(record).execute()

    # Also create user entry in cv2_users
    try:
        client.table("cv2_users").upsert({"id": request.user_id}).execute()
    except Exception:
        pass  # User may already exist

    return {"status": "created", "user_id": request.user_id, "stage": "onboarding"}


@router.post("/upload-document")
async def upload_document(request: DocumentUploadRequest):
    """Upload a document (CV, certificate, etc.) for AI analysis.

    The content_text field should contain the extracted text from the document.
    Frontend handles file reading; backend stores and analyzes the text content.
    """
    client = _get_supabase()

    import uuid
    doc_id = str(uuid.uuid4())

    # Ensure user exists in cv2_users (required for foreign key)
    try:
        client.table("cv2_users").upsert({"id": request.user_id}).execute()
    except Exception:
        pass  # User may already exist

    # Ensure profile exists
    existing_profile = (
        client.table("cv2_profiles")
        .select("user_id")
        .eq("user_id", request.user_id)
        .execute()
    )
    if not existing_profile.data:
        client.table("cv2_profiles").insert({
            "user_id": request.user_id,
            "industry": "general",
            "stage": "onboarding",
        }).execute()

    record = {
        "id": doc_id,
        "user_id": request.user_id,
        "filename": request.filename,
        "doc_type": request.doc_type,
        "content_text": request.content_text[:50000],  # Limit size
    }

    try:
        client.table("cv2_documents").insert(record).execute()
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to save document: {str(e)}")

    # If it's a CV, trigger analysis immediately
    analysis = None
    if request.doc_type == "cv" and request.content_text.strip():
        from app.services.profile_analyzer import profile_analyzer

        # Get user industry for context
        profile = client.table("cv2_profiles").select("industry").eq("user_id", request.user_id).execute()
        industry = (profile.data[0]["industry"] if profile.data else "general")

        analysis = await profile_analyzer.analyze_cv_text(request.content_text, industry)

        # Store analysis result
        if analysis and not analysis.get("error"):
            client.table("cv2_documents").update({"analysis": analysis}).eq("id", doc_id).execute()

            # Update profile summary with career trajectory
            if analysis.get("career_trajectory"):
                client.table("cv2_profiles").update({
                    "summary": analysis["career_trajectory"]
                }).eq("user_id", request.user_id).execute()

    # Index in RAG store for semantic retrieval
    try:
        from app.services.embedding_store import embedding_store
        await embedding_store.index_content(
            content_type="document",
            content_id=doc_id,
            text_content=request.content_text[:5000],
            user_id=request.user_id,
            metadata={"doc_type": request.doc_type},
        )
    except Exception:
        pass  # RAG indexing is non-critical

    return {"status": "uploaded", "doc_id": doc_id, "analysis": analysis}


@router.post("/social-links")
async def save_social_links(request: SocialLinksRequest):
    """Save social/professional profile links for the user.

    Stores LinkedIn, GitHub, portfolio URLs and triggers analysis
    to understand the user's professional presence.
    """
    client = _get_supabase()

    links = {}
    if request.linkedin:
        links["linkedin"] = request.linkedin
    if request.github:
        links["github"] = request.github
    if request.portfolio:
        links["portfolio"] = request.portfolio
    if request.other:
        links["other"] = request.other

    if not links:
        return {"status": "no_links_provided"}

    # Store links in profile
    client.table("cv2_profiles").update({
        "social_links": links
    }).eq("user_id", request.user_id).execute()

    # Analyze what the links reveal
    from app.services.profile_analyzer import profile_analyzer
    social_analysis = await profile_analyzer.analyze_social_profiles(links)

    # Store analysis
    if social_analysis and not social_analysis.get("error"):
        client.table("cv2_profiles").update({
            "social_analysis": social_analysis
        }).eq("user_id", request.user_id).execute()

    return {"status": "saved", "links": links, "analysis": social_analysis}


@router.get("/documents/{user_id}")
async def get_user_documents(user_id: str):
    """Get all documents uploaded by a user."""
    client = _get_supabase()

    result = (
        client.table("cv2_documents")
        .select("id, filename, doc_type, created_at, analysis")
        .eq("user_id", user_id)
        .order("created_at", desc=True)
        .execute()
    )

    return {"documents": result.data or []}


@router.get("/profile-context/{user_id}")
async def get_profile_context(user_id: str):
    """Get the pre-conversation context built from documents and social profiles.

    This is called by the chat system to enrich the AI agent's knowledge
    before the conversation begins.
    """
    client = _get_supabase()

    # Get profile with social analysis
    profile_result = (
        client.table("cv2_profiles")
        .select("industry, social_links, social_analysis")
        .eq("user_id", user_id)
        .execute()
    )

    # Get document analyses
    docs_result = (
        client.table("cv2_documents")
        .select("filename, doc_type, analysis")
        .eq("user_id", user_id)
        .execute()
    )

    cv_analysis = None
    documents = []
    for doc in (docs_result.data or []):
        documents.append({"filename": doc["filename"], "doc_type": doc["doc_type"]})
        if doc.get("analysis") and doc["doc_type"] == "cv":
            cv_analysis = doc["analysis"]

    social_analysis = None
    if profile_result.data:
        social_analysis = profile_result.data[0].get("social_analysis")

    from app.services.profile_analyzer import profile_analyzer
    context = await profile_analyzer.build_pre_conversation_context(
        cv_analysis=cv_analysis,
        social_analysis=social_analysis,
        documents=documents if documents else None,
    )

    return {
        "context": context,
        "has_cv": cv_analysis is not None,
        "has_social": social_analysis is not None,
        "documents_count": len(documents),
    }


@router.get("/profile/{user_id}")
async def get_profile(user_id: str):
    """Get a user's profile including their current stage. Auto-creates if missing."""
    client = _get_supabase()
    result = (
        client.table("cv2_profiles")
        .select("*")
        .eq("user_id", user_id)
        .execute()
    )
    if not result.data:
        # Auto-create user and profile for new users
        try:
            client.table("cv2_users").upsert({"id": user_id}).execute()
        except Exception:
            pass

        new_profile = {
            "user_id": user_id,
            "industry": "general",
            "stage": "onboarding",
            "summary": "",
        }
        try:
            client.table("cv2_profiles").insert(new_profile).execute()
            return new_profile
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Failed to create profile: {str(e)}")

    return result.data[0]


@router.patch("/profile/{user_id}")
async def update_profile(user_id: str, request: ProfileUpdateRequest):
    """Update profile fields (industry, summary, stage)."""
    client = _get_supabase()

    existing = (
        client.table("cv2_profiles")
        .select("user_id")
        .eq("user_id", user_id)
        .execute()
    )
    if not existing.data:
        raise HTTPException(status_code=404, detail="Profile not found.")

    update_data = {}
    if request.industry:
        update_data["industry"] = request.industry
    if request.summary is not None:
        update_data["summary"] = request.summary
    if request.stage:
        if request.stage not in VALID_STAGES:
            raise HTTPException(status_code=400, detail=f"Invalid stage. Must be one of: {VALID_STAGES}")
        update_data["stage"] = request.stage

    if update_data:
        client.table("cv2_profiles").update(update_data).eq("user_id", user_id).execute()

    return {"status": "updated", "user_id": user_id}


@router.post("/profile/{user_id}/advance-stage")
async def advance_stage(user_id: str):
    """Advance user to next stage in the pipeline.

    onboarding → calibration → certified → matchable

    Enforces prerequisites:
    - calibration: must have a profile
    - certified: must have completed calibration
    - matchable: must be certified (Master AI approved)
    """
    client = _get_supabase()

    result = (
        client.table("cv2_profiles")
        .select("*")
        .eq("user_id", user_id)
        .execute()
    )
    if not result.data:
        raise HTTPException(status_code=404, detail="Profile not found.")

    profile = result.data[0]
    current_stage = profile.get("stage", "onboarding")

    stage_order = VALID_STAGES
    current_idx = stage_order.index(current_stage) if current_stage in stage_order else 0
    if current_idx >= len(stage_order) - 1:
        return {"status": "already_at_final_stage", "stage": current_stage}

    next_stage = stage_order[current_idx + 1]

    # Enforce prerequisites
    if next_stage == "calibration":
        # Must have had at least 3 conversation turns
        conv_result = (
            client.table("cv2_conversations")
            .select("id", count="exact")
            .eq("user_id", user_id)
            .execute()
        )
        if (conv_result.count or 0) < 1:
            raise HTTPException(status_code=400, detail="Complete at least one onboarding conversation before calibration.")

    elif next_stage == "certified":
        # Must have completed calibration (all opportunities responded to)
        opp_result = (
            client.table("cv2_test_opportunities")
            .select("status")
            .eq("user_id", user_id)
            .execute()
        )
        opps = opp_result.data or []
        if not opps or any(o["status"] == "pending" for o in opps):
            raise HTTPException(status_code=400, detail="Complete all calibration opportunities first.")

    elif next_stage == "matchable":
        # Must be certified by Master AI
        if current_stage != "certified":
            raise HTTPException(status_code=400, detail="Must be certified by Master AI first.")

    client.table("cv2_profiles").update({"stage": next_stage}).eq("user_id", user_id).execute()
    return {"status": "advanced", "previous_stage": current_stage, "new_stage": next_stage}


@router.post("/register-candidate")
async def register_as_candidate(request: CandidateRegisterRequest):
    """Register a certified user as an A2A matchable candidate.

    Only users at 'matchable' stage can be registered.
    Copies their profile + learned patterns into cv2_a2a_candidates.
    """
    client = _get_supabase()

    # Verify user is at matchable stage
    profile_result = (
        client.table("cv2_profiles")
        .select("*")
        .eq("user_id", request.user_id)
        .execute()
    )
    if not profile_result.data:
        raise HTTPException(status_code=404, detail="Profile not found.")

    profile = profile_result.data[0]
    if profile.get("stage") != "matchable":
        raise HTTPException(
            status_code=400,
            detail=f"User is at stage '{profile.get('stage', 'onboarding')}'. Must be 'matchable' to register as candidate."
        )

    # Gather learned patterns
    patterns_result = (
        client.table("cv2_collective_patterns")
        .select("patterns, pattern_type")
        .eq("user_id", request.user_id)
        .order("created_at", desc=True)
        .limit(10)
        .execute()
    )

    # Build candidate profile from profile + patterns
    candidate_profile = {
        "industry": profile.get("industry", "general"),
        "summary": profile.get("summary", ""),
        "values": [],
        "hidden_criteria": [],
        "goals": [],
    }

    for p in (patterns_result.data or []):
        patterns = p.get("patterns", {})
        if patterns.get("values"):
            candidate_profile["values"].extend(
                patterns["values"] if isinstance(patterns["values"], list) else [patterns["values"]]
            )
        if patterns.get("hidden_criteria"):
            candidate_profile["hidden_criteria"].extend(
                patterns["hidden_criteria"] if isinstance(patterns["hidden_criteria"], list) else [patterns["hidden_criteria"]]
            )
        if patterns.get("inferred_criteria"):
            candidate_profile["hidden_criteria"].append(patterns["inferred_criteria"])
        if patterns.get("goals"):
            candidate_profile["goals"].extend(
                patterns["goals"] if isinstance(patterns["goals"], list) else [patterns["goals"]]
            )

    # Deduplicate
    candidate_profile["values"] = list(set(candidate_profile["values"]))[:10]
    candidate_profile["hidden_criteria"] = list(set(candidate_profile["hidden_criteria"]))[:10]
    candidate_profile["goals"] = list(set(candidate_profile["goals"]))[:5]

    # Upsert into cv2_a2a_candidates
    record = {
        "id": request.user_id,
        "user_id": request.user_id,
        "industry": profile.get("industry", "general"),
        "profile": candidate_profile,
    }
    client.table("cv2_a2a_candidates").upsert(record).execute()

    # Register agent
    try:
        agent_record = {
            "id": f"agent_{request.user_id}",
            "user_id": request.user_id,
            "industry": profile.get("industry", "general"),
        }
        client.table("cv2_agents").upsert(agent_record).execute()
    except Exception:
        pass

    return {"status": "registered", "user_id": request.user_id, "profile": candidate_profile}
