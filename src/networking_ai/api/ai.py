"""
AI API Endpoints - Phase 8.

REST API for AI-powered resume parsing, screening, and predictions.
"""

from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File
from sqlalchemy.orm import Session
from pydantic import BaseModel

from ..database import get_db
from ..models.ai_features import (
    ParsedResume,
    AIScreening,
    AIPrediction,
    CandidateInsight,
    PredictionType,
    ResumeParseStatus
)
from ..services.ai_service import (
    AIService,
    create_ai_service
)


# ==================== Request/Response Models ====================

class ResumeParseRequest(BaseModel):
    """Resume parse request."""
    resume_text: str
    source_file_name: Optional[str] = None


class ParsedResumeResponse(BaseModel):
    """Parsed resume response."""
    id: int
    full_name: Optional[str] = None
    professional_title: Optional[str] = None
    email: Optional[str] = None
    phone: Optional[str] = None
    location: Optional[str] = None
    summary: Optional[str] = None
    total_years_experience: Optional[float] = None
    highest_education_level: Optional[str] = None
    top_skills: list
    parsing_status: ResumeParseStatus
    parsing_confidence: Optional[float] = None

    class Config:
        from_attributes = True


class ScreeningRequest(BaseModel):
    """AI screening request."""
    application_id: int
    job_id: int


class ScreeningResponse(BaseModel):
    """AI screening response."""
    id: int
    decision: str
    confidence_score: float
    overall_match_score: float
    skills_match_score: float
    experience_match_score: float
    education_match_score: float
    matching_skills: list
    missing_skills: list
    strengths: list
    weaknesses: list
    summary: str
    reasoning: str

    class Config:
        from_attributes = True


class PredictionResponse(BaseModel):
    """AI prediction response."""
    id: int
    prediction_type: PredictionType
    predicted_value: float
    predicted_outcome: Optional[str] = None
    confidence: float
    explanation: Optional[str] = None

    class Config:
        from_attributes = True


class CandidateInsightResponse(BaseModel):
    """Candidate insight response."""
    id: int
    career_stage: Optional[str] = None
    career_trajectory: Optional[str] = None
    skill_level: Optional[str] = None
    market_value: Optional[str] = None
    salary_estimate_min: Optional[int] = None
    salary_estimate_max: Optional[int] = None
    demand_score: Optional[float] = None

    class Config:
        from_attributes = True


# ==================== Router Setup ====================

router = APIRouter(prefix="/api/ai", tags=["ai"])


# ==================== Helper Functions ====================

def get_ai_service() -> AIService:
    """Get AI service instance."""
    return create_ai_service()


# ==================== Resume Parsing ====================

@router.post("/parse-resume", response_model=ParsedResumeResponse, status_code=status.HTTP_201_CREATED)
def parse_resume(
    request: ResumeParseRequest,
    user_id: int,  # Should come from auth
    db: Session = Depends(get_db),
    service: AIService = Depends(get_ai_service)
):
    """
    Parse a resume and extract structured data.

    Uses AI to extract contact info, experience, education, and skills.
    """
    try:
        parsed = service.parse_resume(
            user_id=user_id,
            resume_text=request.resume_text,
            source_file_name=request.source_file_name,
            db=db
        )
        return parsed
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to parse resume: {str(e)}"
        )


@router.get("/parsed-resume/{user_id}", response_model=ParsedResumeResponse)
def get_parsed_resume(
    user_id: int,
    current_user_id: int,  # Should come from auth
    db: Session = Depends(get_db)
):
    """
    Get parsed resume for a user.

    Returns the structured resume data if it exists.
    """
    # Authorization check
    if user_id != current_user_id:
        # In production, check if user has permission to view
        pass

    parsed = db.query(ParsedResume).filter(ParsedResume.user_id == user_id).first()

    if not parsed:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Parsed resume not found"
        )

    return parsed


@router.delete("/parsed-resume/{user_id}")
def delete_parsed_resume(
    user_id: int,
    current_user_id: int,  # Should come from auth
    db: Session = Depends(get_db)
):
    """
    Delete parsed resume.

    Removes the parsed resume data for a user.
    """
    # Authorization check
    if user_id != current_user_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized"
        )

    parsed = db.query(ParsedResume).filter(ParsedResume.user_id == user_id).first()

    if not parsed:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Parsed resume not found"
        )

    db.delete(parsed)
    db.commit()

    return {"message": "Parsed resume deleted successfully"}


# ==================== AI Screening ====================

@router.post("/screen", response_model=ScreeningResponse, status_code=status.HTTP_201_CREATED)
def screen_application(
    request: ScreeningRequest,
    user_id: int,  # Should come from auth (hiring manager)
    db: Session = Depends(get_db),
    service: AIService = Depends(get_ai_service)
):
    """
    Screen an application using AI.

    Analyzes candidate qualifications against job requirements.
    """
    try:
        # Get application and verify permissions
        from ..models.application import Application
        application = db.query(Application).get(request.application_id)

        if not application:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Application not found"
            )

        # Check if already screened
        existing = db.query(AIScreening).filter(
            AIScreening.application_id == request.application_id
        ).first()

        if existing:
            return existing

        # Perform screening
        screening = service.screen_application(
            application_id=request.application_id,
            job_id=request.job_id,
            candidate_user_id=application.talent_user_id,
            db=db
        )

        return screening

    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Screening failed: {str(e)}"
        )


@router.get("/screening/{application_id}", response_model=ScreeningResponse)
def get_screening(
    application_id: int,
    user_id: int,  # Should come from auth
    db: Session = Depends(get_db)
):
    """
    Get AI screening results for an application.

    Returns the AI screening analysis if it exists.
    """
    screening = db.query(AIScreening).filter(
        AIScreening.application_id == application_id
    ).first()

    if not screening:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Screening not found"
        )

    return screening


# ==================== Predictions ====================

@router.post("/predict/interview-success", response_model=PredictionResponse, status_code=status.HTTP_201_CREATED)
def predict_interview_success(
    application_id: int,
    job_id: int,
    user_id: int,  # Should come from auth
    db: Session = Depends(get_db),
    service: AIService = Depends(get_ai_service)
):
    """
    Predict interview success probability.

    Uses ML to predict likelihood of successful interview.
    """
    try:
        from ..models.application import Application
        application = db.query(Application).get(application_id)

        if not application:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Application not found"
            )

        prediction = service.predict_interview_success(
            application_id=application_id,
            job_id=job_id,
            candidate_user_id=application.talent_user_id,
            db=db
        )

        return prediction

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Prediction failed: {str(e)}"
        )


@router.post("/predict/time-to-hire", response_model=PredictionResponse, status_code=status.HTTP_201_CREATED)
def predict_time_to_hire(
    job_id: int,
    user_id: int,  # Should come from auth
    db: Session = Depends(get_db),
    service: AIService = Depends(get_ai_service)
):
    """
    Predict time to hire for a job.

    Estimates how long it will take to fill the position.
    """
    try:
        prediction = service.predict_time_to_hire(
            job_id=job_id,
            db=db
        )

        return prediction

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Prediction failed: {str(e)}"
        )


@router.get("/predictions/application/{application_id}")
def get_application_predictions(
    application_id: int,
    user_id: int,  # Should come from auth
    db: Session = Depends(get_db)
):
    """
    Get all predictions for an application.

    Returns all AI predictions made for this application.
    """
    predictions = db.query(AIPrediction).filter(
        AIPrediction.application_id == application_id
    ).all()

    return predictions


# ==================== Insights ====================

@router.post("/insights/candidate", response_model=CandidateInsightResponse, status_code=status.HTTP_201_CREATED)
def generate_candidate_insights(
    user_id: int,  # Candidate user ID
    current_user_id: int,  # Should come from auth
    db: Session = Depends(get_db),
    service: AIService = Depends(get_ai_service)
):
    """
    Generate AI insights for a candidate.

    Analyzes career stage, skills, market value, and recommendations.
    """
    try:
        # Check if insights already exist
        existing = db.query(CandidateInsight).filter(
            CandidateInsight.user_id == user_id
        ).first()

        if existing:
            return existing

        insights = service.generate_candidate_insights(
            user_id=user_id,
            db=db
        )

        return insights

    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to generate insights: {str(e)}"
        )


@router.get("/insights/candidate/{user_id}", response_model=CandidateInsightResponse)
def get_candidate_insights(
    user_id: int,
    current_user_id: int,  # Should come from auth
    db: Session = Depends(get_db)
):
    """
    Get candidate insights.

    Returns AI-generated career insights for a candidate.
    """
    insights = db.query(CandidateInsight).filter(
        CandidateInsight.user_id == user_id
    ).first()

    if not insights:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Insights not found"
        )

    return insights


# ==================== Bulk Operations ====================

@router.post("/bulk/screen-applications")
def bulk_screen_applications(
    job_id: int,
    user_id: int,  # Should come from auth (hiring manager)
    db: Session = Depends(get_db),
    service: AIService = Depends(get_ai_service)
):
    """
    Screen all applications for a job.

    Runs AI screening on all pending applications.
    """
    try:
        from ..models.application import Application, ApplicationStatus

        # Get all applications for this job that haven't been screened
        applications = db.query(Application).filter(
            Application.job_id == job_id,
            Application.status.in_([ApplicationStatus.PENDING, ApplicationStatus.REVIEWING])
        ).all()

        results = []
        for application in applications:
            # Check if already screened
            existing = db.query(AIScreening).filter(
                AIScreening.application_id == application.id
            ).first()

            if existing:
                results.append({"application_id": application.id, "status": "already_screened"})
                continue

            try:
                screening = service.screen_application(
                    application_id=application.id,
                    job_id=job_id,
                    candidate_user_id=application.talent_user_id,
                    db=db
                )
                results.append({
                    "application_id": application.id,
                    "status": "screened",
                    "decision": screening.decision.value,
                    "score": screening.overall_match_score
                })
            except Exception as e:
                results.append({
                    "application_id": application.id,
                    "status": "failed",
                    "error": str(e)
                })

        return {
            "total_applications": len(applications),
            "results": results
        }

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Bulk screening failed: {str(e)}"
        )
