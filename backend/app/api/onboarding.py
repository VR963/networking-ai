"""Symmetric Onboarding Routes - Handles structured interview flow for both Talent and HM.

Flow (same for both sides):
1. Upload context (CV for talent, job description for HM)
2. Start interview → generates personalized questions
3. Answer questions one at a time → each analyzed
4. Auto-activation check after each answer
5. When ready → generates AI profile → activates agent

Endpoints:
- POST /onboarding/talent/start-interview
- POST /onboarding/talent/answer
- GET  /onboarding/talent/status/{user_id}
- POST /onboarding/hm/start-interview
- POST /onboarding/hm/answer
- GET  /onboarding/hm/status/{user_id}/{job_id}
"""

import uuid
from typing import Optional

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from supabase import create_client

from app.config import SUPABASE_URL, SUPABASE_SERVICE_KEY
from app.services.interview_service import interview_service
from app.services.auto_activation import auto_activation

router = APIRouter()


def _get_supabase():
    if not SUPABASE_URL or not SUPABASE_SERVICE_KEY:
        raise HTTPException(status_code=503, detail="Database not configured.")
    return create_client(SUPABASE_URL, SUPABASE_SERVICE_KEY)


# --- Request Models ---

class TalentStartRequest(BaseModel):
    user_id: str
    industry: str = "general"


class HMStartRequest(BaseModel):
    user_id: str
    job_id: str
    industry: str = "general"


class AnswerRequest(BaseModel):
    user_id: str
    interview_id: str
    question_index: int
    answer: str


# --- TALENT FLOW ---

@router.post("/talent/start-interview")
async def start_talent_interview(request: TalentStartRequest):
    """Start a structured interview for a talent.

    Generates personalized questions from their CV analysis.
    If no CV uploaded, uses fallback questions.

    Returns the interview ID and first question.
    """
    client = _get_supabase()

    # Get CV analysis if available
    docs = (
        client.table("cv2_documents")
        .select("analysis")
        .eq("user_id", request.user_id)
        .eq("doc_type", "cv")
        .order("created_at", desc=True)
        .limit(1)
        .execute()
    )
    cv_analysis = None
    if docs.data and docs.data[0].get("analysis"):
        cv_analysis = docs.data[0]["analysis"]

    # Generate personalized questions
    questions = await interview_service.generate_talent_questions(
        cv_analysis=cv_analysis or {},
        industry=request.industry,
    )

    # Create interview record
    interview_id = str(uuid.uuid4())
    record = {
        "id": interview_id,
        "user_id": request.user_id,
        "agent_type": "talent",
        "context_id": request.user_id,
        "questions": questions,
        "answers": [],
        "current_index": 0,
        "status": "in_progress",
    }
    client.table("cv2_interviews").insert(record).execute()

    # Ensure profile exists
    existing = (
        client.table("cv2_profiles")
        .select("user_id")
        .eq("user_id", request.user_id)
        .execute()
    )
    if not existing.data:
        client.table("cv2_profiles").insert({
            "user_id": request.user_id,
            "industry": request.industry,
            "stage": "onboarding",
        }).execute()

    return {
        "interview_id": interview_id,
        "total_questions": len(questions),
        "current_index": 0,
        "question": questions[0] if questions else None,
    }


@router.post("/talent/answer")
async def answer_talent_question(request: AnswerRequest):
    """Submit an answer to the current interview question.

    Analyzes the answer, stores it, advances to next question.
    After final answer, checks readiness and auto-activates if ready.

    Returns:
    - Next question (if more remain)
    - Activation result (if interview complete and ready)
    """
    client = _get_supabase()

    # Get interview
    interview = (
        client.table("cv2_interviews")
        .select("*")
        .eq("id", request.interview_id)
        .execute()
    )
    if not interview.data:
        raise HTTPException(status_code=404, detail="Interview not found.")

    interview_data = interview.data[0]
    questions = interview_data.get("questions", [])
    answers = interview_data.get("answers", [])

    if request.question_index >= len(questions):
        raise HTTPException(status_code=400, detail="Invalid question index.")

    # Analyze the answer
    question = questions[request.question_index]
    analysis = await interview_service.analyze_answer(
        question=question,
        answer=request.answer,
        agent_type="talent",
        previous_answers=answers,
    )

    # Store answer
    answer_record = {
        "question": question.get("question", ""),
        "answer": request.answer,
        "analysis": analysis,
        "index": request.question_index,
    }
    answers.append(answer_record)

    next_index = request.question_index + 1
    is_complete = next_index >= len(questions)

    # Update interview
    update = {
        "answers": answers,
        "current_index": next_index,
    }
    if is_complete:
        update["status"] = "completed"

    client.table("cv2_interviews").update(update).eq("id", request.interview_id).execute()

    # If complete, check readiness
    activation_result = None
    if is_complete:
        activation_result = await auto_activation.activate_talent_agent(request.user_id)

    response = {
        "answered": request.question_index,
        "total_questions": len(questions),
        "analysis_summary": analysis.get("content_summary", ""),
        "is_complete": is_complete,
    }

    if not is_complete:
        response["next_question"] = questions[next_index]
        response["next_index"] = next_index
    else:
        response["activation"] = activation_result

    return response


@router.get("/talent/status/{user_id}")
async def get_talent_status(user_id: str):
    """Get current onboarding status for a talent.

    Returns interview progress and readiness score.
    """
    client = _get_supabase()

    # Profile
    profile = (
        client.table("cv2_profiles")
        .select("stage, industry, ai_profile, activation_score")
        .eq("user_id", user_id)
        .execute()
    )

    # CV uploaded?
    docs = (
        client.table("cv2_documents")
        .select("id, filename, analysis")
        .eq("user_id", user_id)
        .eq("doc_type", "cv")
        .execute()
    )

    # Interview progress
    interviews = (
        client.table("cv2_interviews")
        .select("id, status, current_index, questions, answers")
        .eq("user_id", user_id)
        .eq("agent_type", "talent")
        .order("created_at", desc=True)
        .limit(1)
        .execute()
    )

    has_cv = bool(docs.data and docs.data[0].get("analysis"))
    interview = interviews.data[0] if interviews.data else None

    # Compute readiness
    readiness = await auto_activation.compute_talent_readiness(user_id)

    return {
        "user_id": user_id,
        "stage": profile.data[0]["stage"] if profile.data else "new",
        "has_cv": has_cv,
        "cv_filename": docs.data[0]["filename"] if docs.data else None,
        "interview": {
            "id": interview["id"] if interview else None,
            "status": interview["status"] if interview else "not_started",
            "progress": f"{interview['current_index']}/{len(interview['questions'])}" if interview else "0/0",
            "current_index": interview["current_index"] if interview else 0,
            "total_questions": len(interview["questions"]) if interview else 0,
        },
        "readiness": readiness,
        "activated": profile.data[0].get("stage") == "matchable" if profile.data else False,
    }


# --- HM FLOW (Mirror) ---

@router.post("/hm/start-interview")
async def start_hm_interview(request: HMStartRequest):
    """Start a structured interview for a hiring manager about a specific job.

    Generates personalized questions from the job description.

    Returns the interview ID and first question.
    """
    client = _get_supabase()

    # Get job description
    job = (
        client.table("cv2_jobs")
        .select("*")
        .eq("id", request.job_id)
        .execute()
    )
    if not job.data:
        raise HTTPException(status_code=404, detail="Job not found. Create a job first.")

    job_data = job.data[0]

    # Verify ownership
    if job_data.get("user_id") != request.user_id:
        raise HTTPException(status_code=403, detail="Not your job listing.")

    # Generate personalized questions
    questions = await interview_service.generate_hm_questions(
        job_analysis=job_data,
        industry=request.industry or job_data.get("industry", "general"),
    )

    # Create interview record
    interview_id = str(uuid.uuid4())
    record = {
        "id": interview_id,
        "user_id": request.user_id,
        "agent_type": "hm",
        "context_id": request.job_id,
        "questions": questions,
        "answers": [],
        "current_index": 0,
        "status": "in_progress",
    }
    client.table("cv2_interviews").insert(record).execute()

    return {
        "interview_id": interview_id,
        "job_id": request.job_id,
        "job_title": job_data.get("title", ""),
        "total_questions": len(questions),
        "current_index": 0,
        "question": questions[0] if questions else None,
    }


@router.post("/hm/answer")
async def answer_hm_question(request: AnswerRequest):
    """Submit an answer to the current HM interview question.

    Same flow as talent: analyze → store → advance → auto-activate if ready.
    """
    client = _get_supabase()

    # Get interview
    interview = (
        client.table("cv2_interviews")
        .select("*")
        .eq("id", request.interview_id)
        .execute()
    )
    if not interview.data:
        raise HTTPException(status_code=404, detail="Interview not found.")

    interview_data = interview.data[0]
    questions = interview_data.get("questions", [])
    answers = interview_data.get("answers", [])
    job_id = interview_data.get("context_id", "")

    if request.question_index >= len(questions):
        raise HTTPException(status_code=400, detail="Invalid question index.")

    # Analyze the answer
    question = questions[request.question_index]
    analysis = await interview_service.analyze_answer(
        question=question,
        answer=request.answer,
        agent_type="hm",
        previous_answers=answers,
    )

    # Store answer
    answer_record = {
        "question": question.get("question", ""),
        "answer": request.answer,
        "analysis": analysis,
        "index": request.question_index,
    }
    answers.append(answer_record)

    next_index = request.question_index + 1
    is_complete = next_index >= len(questions)

    # Update interview
    update = {
        "answers": answers,
        "current_index": next_index,
    }
    if is_complete:
        update["status"] = "completed"

    client.table("cv2_interviews").update(update).eq("id", request.interview_id).execute()

    # If complete, check readiness
    activation_result = None
    if is_complete:
        activation_result = await auto_activation.activate_hm_agent(request.user_id, job_id)

    response = {
        "answered": request.question_index,
        "total_questions": len(questions),
        "analysis_summary": analysis.get("content_summary", ""),
        "is_complete": is_complete,
    }

    if not is_complete:
        response["next_question"] = questions[next_index]
        response["next_index"] = next_index
    else:
        response["activation"] = activation_result

    return response


@router.get("/hm/status/{user_id}/{job_id}")
async def get_hm_status(user_id: str, job_id: str):
    """Get current onboarding status for a hiring manager's job.

    Returns interview progress and readiness score.
    """
    client = _get_supabase()

    # Job data
    job = (
        client.table("cv2_jobs")
        .select("title, status, ai_profile, activation_score")
        .eq("id", job_id)
        .execute()
    )

    # Interview progress
    interviews = (
        client.table("cv2_interviews")
        .select("id, status, current_index, questions, answers")
        .eq("user_id", user_id)
        .eq("agent_type", "hm")
        .eq("context_id", job_id)
        .order("created_at", desc=True)
        .limit(1)
        .execute()
    )

    interview = interviews.data[0] if interviews.data else None

    # Compute readiness
    readiness = await auto_activation.compute_hm_readiness(user_id, job_id)

    return {
        "user_id": user_id,
        "job_id": job_id,
        "job_title": job.data[0]["title"] if job.data else "Unknown",
        "job_status": job.data[0].get("status", "draft") if job.data else "not_found",
        "interview": {
            "id": interview["id"] if interview else None,
            "status": interview["status"] if interview else "not_started",
            "progress": f"{interview['current_index']}/{len(interview['questions'])}" if interview else "0/0",
            "current_index": interview["current_index"] if interview else 0,
            "total_questions": len(interview["questions"]) if interview else 0,
        },
        "readiness": readiness,
        "activated": job.data[0].get("status") == "active" if job.data else False,
    }
