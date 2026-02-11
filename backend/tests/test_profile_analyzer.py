"""Tests for profile analyzer service."""

import json
import pytest
from unittest.mock import patch, MagicMock

from app.services.profile_analyzer import ProfileAnalyzer


class TestAnalyzeCvText:
    """Test CV text analysis."""

    def setup_method(self):
        self.analyzer = ProfileAnalyzer()

    @pytest.mark.asyncio
    async def test_no_api_key(self):
        with patch("app.services.profile_analyzer.ANTHROPIC_API_KEY", ""):
            result = await self.analyzer.analyze_cv_text("Some CV text")
            assert "error" in result

    @pytest.mark.asyncio
    async def test_successful_cv_analysis(self):
        mock_response = MagicMock()
        mock_response.content = [MagicMock(text=json.dumps({
            "name": "Jane Doe",
            "current_role": "Senior Engineer",
            "experience_years": 8,
            "skills": ["Python", "AWS"],
            "education": [{"degree": "BSc CS", "institution": "MIT", "year": "2015"}],
            "experience": [{"role": "Senior Engineer", "company": "Acme"}],
            "certifications": [],
            "languages": ["Python", "English"],
            "industry_signals": ["tech"],
            "career_trajectory": "Backend to full-stack",
            "suggested_deep_questions": ["What drives you?"],
        }))]

        with patch.object(self.analyzer, "_anthropic") as mock_client:
            mock_client.messages.create.return_value = mock_response
            self.analyzer._anthropic = mock_client

            result = await self.analyzer.analyze_cv_text("Jane Doe - Senior Engineer at Acme...")
            assert result["name"] == "Jane Doe"
            assert "Python" in result["skills"]
            assert result["experience_years"] == 8

    @pytest.mark.asyncio
    async def test_handles_markdown_wrapped_json(self):
        mock_response = MagicMock()
        mock_response.content = [MagicMock(text='```json\n{"name": "Test", "skills": []}\n```')]

        with patch.object(self.analyzer, "_anthropic") as mock_client:
            mock_client.messages.create.return_value = mock_response
            self.analyzer._anthropic = mock_client

            result = await self.analyzer.analyze_cv_text("test cv")
            assert result["name"] == "Test"

    @pytest.mark.asyncio
    async def test_handles_invalid_json(self):
        mock_response = MagicMock()
        mock_response.content = [MagicMock(text="This is not JSON at all")]

        with patch.object(self.analyzer, "_anthropic") as mock_client:
            mock_client.messages.create.return_value = mock_response
            self.analyzer._anthropic = mock_client

            result = await self.analyzer.analyze_cv_text("test cv")
            assert "error" in result


class TestAnalyzeJobDescription:
    """Test job description analysis."""

    def setup_method(self):
        self.analyzer = ProfileAnalyzer()

    @pytest.mark.asyncio
    async def test_no_api_key(self):
        with patch("app.services.profile_analyzer.ANTHROPIC_API_KEY", ""):
            result = await self.analyzer.analyze_job_description("Senior Engineer needed")
            assert "error" in result

    @pytest.mark.asyncio
    async def test_successful_jd_analysis(self):
        mock_response = MagicMock()
        mock_response.content = [MagicMock(text=json.dumps({
            "title": "Senior Backend Engineer",
            "company": "Acme Corp",
            "description": "Build scalable systems",
            "requirements": ["Python", "5+ years"],
            "skills": ["Python", "AWS", "PostgreSQL"],
            "experience_level": "senior",
            "salary_range": "$150k-$200k",
            "location": "Remote",
            "remote_policy": "remote",
            "team_size": "8-10",
            "reporting_to": "VP Engineering",
            "suggested_deep_questions": ["What does success look like?"],
        }))]

        with patch.object(self.analyzer, "_anthropic") as mock_client:
            mock_client.messages.create.return_value = mock_response
            self.analyzer._anthropic = mock_client

            result = await self.analyzer.analyze_job_description("Backend Engineer at Acme...")
            assert result["title"] == "Senior Backend Engineer"
            assert result["experience_level"] == "senior"


class TestBuildPreConversationContext:
    """Test context string builder."""

    def setup_method(self):
        self.analyzer = ProfileAnalyzer()

    @pytest.mark.asyncio
    async def test_empty_inputs(self):
        result = await self.analyzer.build_pre_conversation_context()
        assert result == ""

    @pytest.mark.asyncio
    async def test_with_cv_analysis(self):
        cv = {
            "name": "Jane Doe",
            "current_role": "Engineer",
            "experience_years": 5,
            "skills": ["Python", "AWS"],
            "career_trajectory": "Backend specialist",
        }
        result = await self.analyzer.build_pre_conversation_context(cv_analysis=cv)
        assert "Jane Doe" in result
        assert "Engineer" in result
        assert "Python" in result
        assert "go DEEPER" in result

    @pytest.mark.asyncio
    async def test_with_social_analysis(self):
        social = {
            "profiles_shared": ["GitHub", "LinkedIn"],
            "professional_presence": "Strong online presence",
        }
        result = await self.analyzer.build_pre_conversation_context(social_analysis=social)
        assert "GitHub" in result
        assert "LinkedIn" in result

    @pytest.mark.asyncio
    async def test_with_documents(self):
        docs = [{"filename": "resume.pdf"}, {"filename": "portfolio.pdf"}]
        result = await self.analyzer.build_pre_conversation_context(documents=docs)
        assert "2 document(s)" in result
        assert "resume.pdf" in result

    @pytest.mark.asyncio
    async def test_cv_with_error_ignored(self):
        result = await self.analyzer.build_pre_conversation_context(
            cv_analysis={"error": "Failed to parse"}
        )
        assert result == ""

    @pytest.mark.asyncio
    async def test_combined_context(self):
        cv = {"name": "Jane", "current_role": "Engineer", "skills": ["Python"]}
        social = {"profiles_shared": ["GitHub"]}
        docs = [{"filename": "cv.pdf"}]
        result = await self.analyzer.build_pre_conversation_context(
            cv_analysis=cv, social_analysis=social, documents=docs
        )
        assert "Jane" in result
        assert "GitHub" in result
        assert "cv.pdf" in result
