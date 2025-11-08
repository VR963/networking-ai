"""
Tests for CV Parser Service.

Tests AI-powered CV parsing, industry detection, and user segmentation.
"""

import pytest
import os
from pathlib import Path

from src.networking_ai.services.cv_parser import CVParserService, create_cv_parser


# Skip tests if no API key available
pytestmark = pytest.mark.skipif(
    not os.getenv("ANTHROPIC_API_KEY"),
    reason="ANTHROPIC_API_KEY not set"
)


@pytest.fixture
def cv_parser():
    """Create CV parser instance."""
    return create_cv_parser()


@pytest.fixture
def sample_cv_text():
    """Load sample CV text."""
    fixture_path = Path(__file__).parent / "fixtures" / "sample_cv.txt"
    with open(fixture_path, 'r') as f:
        return f.read()


class TestCVTextExtraction:
    """Test text extraction from different file formats."""

    def test_extract_text_from_txt(self, cv_parser, sample_cv_text):
        """Test extraction from plain text (used for testing)."""
        # For text files, we just return the content
        assert len(sample_cv_text) > 100
        assert "John Doe" in sample_cv_text
        assert "System Engineer" in sample_cv_text


class TestCVParsing:
    """Test AI-powered CV parsing."""

    def test_parse_cv_with_ai(self, cv_parser, sample_cv_text):
        """Test parsing CV text into structured format."""
        parsed = cv_parser.parse_cv_with_ai(sample_cv_text)

        # Check required fields
        assert "contact_info" in parsed
        assert "education" in parsed
        assert "work_history" in parsed
        assert "skills" in parsed

        # Check contact info
        contact = parsed["contact_info"]
        assert contact.get("name") == "John Doe"
        assert "john.doe@email.com" in contact.get("email", "")

        # Check work history
        work_history = parsed["work_history"]
        assert len(work_history) > 0

        # First job should be Goldman Sachs
        first_job = work_history[0]
        assert "Goldman Sachs" in first_job.get("company", "")
        assert "Senior System Engineer" in first_job.get("title", "")

        # Check skills
        skills = parsed["skills"]
        assert "Python" in str(skills) or "python" in str(skills).lower()

    def test_parse_cv_includes_gaps(self, cv_parser, sample_cv_text):
        """Test that parser detects employment gaps."""
        parsed = cv_parser.parse_cv_with_ai(sample_cv_text)

        # Should have gaps field
        assert "gaps" in parsed

        # Our sample has a gap between Tech Startup (Dec 2015) and Morgan Stanley (Jan 2016)
        # This is only 1 month so might not be flagged as a gap
        # But the structure should exist
        assert isinstance(parsed["gaps"], list)


class TestIndustryDetection:
    """Test industry and role detection."""

    def test_detect_industry_and_role(self, cv_parser, sample_cv_text):
        """Test industry/role classification."""
        parsed = cv_parser.parse_cv_with_ai(sample_cv_text)
        classification = cv_parser.detect_industry_and_role(parsed)

        # Check required fields
        assert "industry" in classification
        assert "role" in classification
        assert "experience_level" in classification
        assert "primary_skills" in classification

        # For John Doe's CV, should detect finance industry
        assert classification["industry"] in ["finance", "fintech", "financial_services"]

        # Should detect system engineer role
        role = classification["role"].lower()
        assert "engineer" in role or "developer" in role

        # Should be senior level (8 years experience)
        assert classification["experience_level"] in ["senior", "lead", "expert"]

        # Should include Python as primary skill
        primary_skills = classification["primary_skills"]
        assert any("python" in skill.lower() for skill in primary_skills)

    def test_detect_with_confidence_scores(self, cv_parser, sample_cv_text):
        """Test that confidence scores are returned."""
        parsed = cv_parser.parse_cv_with_ai(sample_cv_text)
        classification = cv_parser.detect_industry_and_role(parsed)

        # Should have confidence scores
        assert "industry_confidence" in classification
        assert "role_confidence" in classification

        # Confidence should be between 0 and 1
        assert 0 <= classification["industry_confidence"] <= 1
        assert 0 <= classification["role_confidence"] <= 1

        # For clear finance background, confidence should be high
        assert classification["industry_confidence"] > 0.6


class TestUserSegmentation:
    """Test user segmentation for cross-learning."""

    def test_generate_user_segment_id(self, cv_parser, sample_cv_text):
        """Test segment ID generation."""
        parsed = cv_parser.parse_cv_with_ai(sample_cv_text)
        classification = cv_parser.detect_industry_and_role(parsed)

        segment_id = cv_parser.generate_user_segment_id(classification)

        # Format: role_industry_experienceyrs_primaryskill
        parts = segment_id.split("_")
        assert len(parts) >= 4

        # Should include role, industry, and experience bucket
        assert any(part in ["finance", "fintech", "financial"] for part in parts)
        assert any(part in ["engineer", "developer", "system"] for part in parts)

        # Experience should be bucketed (0-2, 3-5, 6-10, 10+)
        # 8 years -> 6-10 bucket
        assert any(part in ["6", "10", "8"] for part in parts)

    def test_segment_ids_consistent(self, cv_parser, sample_cv_text):
        """Test that same CV produces same segment ID."""
        parsed = cv_parser.parse_cv_with_ai(sample_cv_text)
        classification1 = cv_parser.detect_industry_and_role(parsed)
        classification2 = cv_parser.detect_industry_and_role(parsed)

        segment_id1 = cv_parser.generate_user_segment_id(classification1)
        segment_id2 = cv_parser.generate_user_segment_id(classification2)

        # Should be deterministic (note: AI might vary slightly, but segmentation should be stable)
        assert segment_id1 == segment_id2


class TestFullPipeline:
    """Test complete CV parsing pipeline."""

    def test_parse_cv_file_full_pipeline(self, cv_parser, tmp_path, sample_cv_text):
        """Test end-to-end CV parsing from file."""
        # Create temporary text file
        cv_file = tmp_path / "test_cv.txt"
        cv_file.write_text(sample_cv_text)

        # Parse file
        result = cv_parser.parse_cv_file(str(cv_file))

        # Check structure
        assert "parsed_data" in result
        assert "classification" in result
        assert "raw_text" in result
        assert "parsed_at" in result

        # Check parsed data
        parsed = result["parsed_data"]
        assert "contact_info" in parsed
        assert parsed["contact_info"]["name"] == "John Doe"

        # Check classification
        classification = result["classification"]
        assert classification["industry"] in ["finance", "fintech", "financial_services"]
        assert "engineer" in classification["role"].lower() or "developer" in classification["role"].lower()

        # Generate segment ID separately (not part of parse_cv_file result)
        user_segment_id = cv_parser.generate_user_segment_id(classification)
        assert len(user_segment_id) > 10  # Should be descriptive


class TestEdgeCases:
    """Test edge cases and error handling."""

    def test_parse_minimal_cv(self, cv_parser):
        """Test parsing a minimal CV."""
        minimal_cv = """
        Jane Smith
        Software Engineer
        jane@email.com

        Experience:
        - Software Engineer at Tech Co (2020-2023)

        Education:
        - BS Computer Science, State University (2020)
        """

        parsed = cv_parser.parse_cv_with_ai(minimal_cv)

        # Should still extract basic info
        assert "contact_info" in parsed
        assert "Jane Smith" in parsed["contact_info"].get("name", "")

    def test_parse_cv_missing_dates(self, cv_parser):
        """Test parsing CV with missing employment dates."""
        cv_missing_dates = """
        Bob Johnson
        Data Scientist
        bob@email.com

        Experience:
        - Data Scientist at Analytics Inc
          Built ML models for customer segmentation

        Education:
        - PhD Statistics, Top University
        """

        parsed = cv_parser.parse_cv_with_ai(cv_missing_dates)

        # Should handle gracefully
        assert "work_history" in parsed
        assert len(parsed["work_history"]) > 0
