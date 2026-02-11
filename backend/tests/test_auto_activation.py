"""Tests for auto-activation service."""

import pytest
from unittest.mock import patch, MagicMock, AsyncMock

from app.services.auto_activation import (
    AutoActivation,
    ACTIVATION_THRESHOLD,
    DOCUMENT_WEIGHT,
    INTERVIEW_WEIGHT,
)


class TestActivationConstants:
    """Test activation formula constants."""

    def test_weights_sum_to_one(self):
        assert abs(DOCUMENT_WEIGHT + INTERVIEW_WEIGHT - 1.0) < 0.001

    def test_threshold_reasonable(self):
        assert 0 < ACTIVATION_THRESHOLD <= 100


class TestCVScoring:
    """Test CV analysis scoring."""

    def setup_method(self):
        self.activation = AutoActivation()

    def test_empty_cv_scores_zero(self):
        assert self.activation._score_cv_analysis(None) == 0
        assert self.activation._score_cv_analysis({}) == 0
        assert self.activation._score_cv_analysis({"error": "failed"}) == 0

    def test_minimal_cv(self):
        cv = {"name": "John Doe"}
        score = self.activation._score_cv_analysis(cv)
        assert score == 10

    def test_complete_cv_high_score(self):
        cv = {
            "name": "Jane Smith",
            "current_role": "Senior Engineer",
            "experience_years": 8,
            "skills": ["Python", "Java", "Kubernetes", "AWS", "Docker",
                       "React", "PostgreSQL", "Redis", "Go", "Terraform"],
            "experience": [
                {"role": "Senior", "company": "A", "duration": "3y"},
                {"role": "Mid", "company": "B", "duration": "2y"},
                {"role": "Junior", "company": "C", "duration": "2y"},
            ],
            "education": [{"degree": "BSc CS"}],
            "career_trajectory": "Steady upward growth in backend engineering",
        }
        score = self.activation._score_cv_analysis(cv)
        assert score >= 80  # Should be high with all fields

    def test_skills_cap_at_20(self):
        cv = {"skills": [f"skill_{i}" for i in range(50)]}
        score = self.activation._score_cv_analysis(cv)
        assert score == 20  # Min(20, 50*2) = 20

    def test_experience_cap_at_25(self):
        cv = {"experience": [{"role": f"r{i}"} for i in range(20)]}
        score = self.activation._score_cv_analysis(cv)
        assert score == 25  # Min(25, 20*5) = 25

    def test_score_capped_at_100(self):
        cv = {
            "name": "Max",
            "current_role": "CTO",
            "experience_years": 20,
            "skills": [f"s{i}" for i in range(50)],
            "experience": [{"role": f"r{i}"} for i in range(20)],
            "education": [{"degree": "PhD"}],
            "career_trajectory": "Executive path",
        }
        score = self.activation._score_cv_analysis(cv)
        assert score == 100


class TestJobDescriptionScoring:
    """Test job description scoring."""

    def setup_method(self):
        self.activation = AutoActivation()

    def test_empty_job_scores_zero(self):
        assert self.activation._score_job_description(None) == 0
        assert self.activation._score_job_description({}) == 0

    def test_minimal_job(self):
        job = {"title": "Engineer"}
        assert self.activation._score_job_description(job) == 15

    def test_complete_job(self):
        job = {
            "title": "Senior Backend Engineer",
            "company": "Acme Corp",
            "description": "A" * 100,  # > 50 chars
            "requirements": ["Python", "5+ years", "System design", "AWS", "Docker"],
            "values": ["innovation", "collaboration"],
            "culture": "Fast-paced, data-driven team",
            "salary_range": "$150k-$200k",
        }
        score = self.activation._score_job_description(job)
        assert score >= 80

    def test_requirements_as_string(self):
        job = {"requirements": "Must have 5+ years Python and cloud experience"}
        score = self.activation._score_job_description(job)
        assert score == 15  # String > 30 chars

    def test_requirements_as_short_string(self):
        job = {"requirements": "Python"}
        score = self.activation._score_job_description(job)
        assert score == 0  # String <= 30 chars


class TestReadinessComputation:
    """Test readiness score calculation."""

    def setup_method(self):
        self.activation = AutoActivation()

    @pytest.mark.asyncio
    async def test_talent_readiness_with_both_scores(self):
        mock_client = MagicMock()
        # CV documents
        cv_table = MagicMock()
        cv_table.select.return_value = cv_table
        cv_table.eq.return_value = cv_table
        cv_table.execute.return_value = MagicMock(data=[{
            "analysis": {
                "name": "Test User",
                "current_role": "Engineer",
                "experience_years": 5,
                "skills": ["Python", "Java"],
                "experience": [{"role": "Engineer"}],
            }
        }])

        # Interview data
        interview_table = MagicMock()
        interview_table.select.return_value = interview_table
        interview_table.eq.return_value = interview_table
        interview_table.order.return_value = interview_table
        interview_table.limit.return_value = interview_table
        interview_table.execute.return_value = MagicMock(data=[{
            "answers": [{"question": "q1", "answer": "a1"}]
        }])

        call_count = [0]
        def table_side_effect(name):
            call_count[0] += 1
            if name == "cv2_documents":
                return cv_table
            return interview_table

        mock_client.table.side_effect = table_side_effect

        with patch("app.services.auto_activation.get_db", return_value=mock_client):
            with patch.object(
                self.activation, "_score_cv_analysis", return_value=80
            ):
                with patch(
                    "app.services.auto_activation.interview_service"
                ) as mock_interview:
                    mock_interview.compute_interview_quality = AsyncMock(
                        return_value={"quality_score": 70}
                    )
                    result = await self.activation.compute_talent_readiness("user1")
                    assert result["document_score"] == 80
                    assert result["interview_score"] == 70
                    expected = int(80 * 0.7 + 70 * 0.3)
                    assert result["combined_score"] == expected
                    assert result["ready"] is True


class TestActivationFormula:
    """Test the activation formula math."""

    def test_threshold_boundary(self):
        # Document = 80, Interview = 13.33 -> combined = 60
        # 80*0.7 + 13.33*0.3 = 56 + 4 = 60
        combined = int(80 * DOCUMENT_WEIGHT + 14 * INTERVIEW_WEIGHT)
        assert combined == 60  # Exactly at threshold
        assert combined >= ACTIVATION_THRESHOLD

    def test_below_threshold(self):
        combined = int(50 * DOCUMENT_WEIGHT + 50 * INTERVIEW_WEIGHT)
        assert combined == 50
        assert combined < ACTIVATION_THRESHOLD

    def test_high_document_can_compensate(self):
        combined = int(86 * DOCUMENT_WEIGHT + 0 * INTERVIEW_WEIGHT)
        assert combined == 60
        assert combined >= ACTIVATION_THRESHOLD
