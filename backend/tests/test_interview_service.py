"""Tests for interview service."""

import json
import pytest
from unittest.mock import patch, MagicMock, AsyncMock

from app.services.interview_service import InterviewService


class TestInterviewService:
    """Test structured interview logic."""

    def setup_method(self):
        self.service = InterviewService()

    @pytest.mark.asyncio
    async def test_compute_interview_quality_empty_answers(self):
        result = await self.service.compute_interview_quality([])
        assert result["quality_score"] == 0

    @pytest.mark.asyncio
    async def test_compute_interview_quality_with_answers(self):
        answers = [
            {"question": "What drives you?", "answer": "I love solving complex problems in distributed systems. At my last role, I redesigned the message queue which reduced latency by 40%."},
            {"question": "Tell me about a key achievement.", "answer": "Led migration of 50 microservices to Kubernetes, zero downtime."},
            {"question": "How do you prefer to work?", "answer": "I thrive in small teams with high autonomy. Daily standups are fine but I need focus time."},
        ]
        result = await self.service.compute_interview_quality(answers)
        assert result["quality_score"] > 0
        assert result["quality_score"] <= 100

    @pytest.mark.asyncio
    async def test_compute_interview_quality_short_answers_penalized(self):
        short_answers = [
            {"question": "What drives you?", "answer": "Money"},
            {"question": "Achievement?", "answer": "Got promoted"},
        ]
        long_answers = [
            {"question": "What drives you?", "answer": "I'm passionate about building products that genuinely help people. At my previous company, I spent 6 months leading a project that automated manual data entry for nurses, saving them 2 hours per shift. Seeing the direct impact on patient care was incredibly fulfilling."},
            {"question": "Achievement?", "answer": "I architected a real-time analytics pipeline processing 10M events/day using Kafka and Flink. The system reduced our reporting latency from hours to seconds and became the foundation for our ML feature store."},
        ]
        short_result = await self.service.compute_interview_quality(short_answers)
        long_result = await self.service.compute_interview_quality(long_answers)
        assert long_result["quality_score"] > short_result["quality_score"]


class TestQuestionGeneration:
    """Test interview question generation."""

    def setup_method(self):
        self.service = InterviewService()

    @pytest.mark.asyncio
    async def test_generate_talent_questions_without_api(self):
        with patch("app.services.interview_service.ANTHROPIC_API_KEY", ""):
            questions = await self.service.generate_talent_questions(
                industry="tech",
                cv_analysis={"skills": ["Python"], "current_role": "Engineer"},
            )
            assert isinstance(questions, list)
            assert len(questions) >= 1  # Should return fallback questions
