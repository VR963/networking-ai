"""
CV Parser Service.

Extracts structured data from resumes using AI-powered parsing.
Supports PDF and DOCX formats.
"""

import os
import json
from typing import Dict, Optional, List
from datetime import datetime
import anthropic


class CVParserService:
    """
    CV Parser Service.

    Uses Claude AI to intelligently extract structured information from resumes.
    """

    def __init__(self, anthropic_api_key: Optional[str] = None):
        """
        Initialize CV Parser.

        Args:
            anthropic_api_key: Anthropic API key (defaults to env var)
        """
        self.api_key = anthropic_api_key or os.getenv("ANTHROPIC_API_KEY")

        if not self.api_key:
            raise ValueError("Anthropic API key required for CV parsing")

        self.client = anthropic.Anthropic(api_key=self.api_key)

    def extract_text_from_pdf(self, file_path: str) -> str:
        """
        Extract text from PDF file.

        Args:
            file_path: Path to PDF file

        Returns:
            Extracted text
        """
        try:
            import PyPDF2

            with open(file_path, 'rb') as file:
                reader = PyPDF2.PdfReader(file)
                text = ""

                for page in reader.pages:
                    text += page.extract_text() + "\n"

                return text.strip()

        except ImportError:
            # Fallback if PyPDF2 not available
            return "[PDF parsing requires PyPDF2: pip install PyPDF2]"
        except Exception as e:
            raise Exception(f"Error extracting PDF text: {str(e)}")

    def extract_text_from_docx(self, file_path: str) -> str:
        """
        Extract text from DOCX file.

        Args:
            file_path: Path to DOCX file

        Returns:
            Extracted text
        """
        try:
            import docx

            doc = docx.Document(file_path)
            text = "\n".join([paragraph.text for paragraph in doc.paragraphs])

            return text.strip()

        except ImportError:
            # Fallback if python-docx not available
            return "[DOCX parsing requires python-docx: pip install python-docx]"
        except Exception as e:
            raise Exception(f"Error extracting DOCX text: {str(e)}")

    def extract_text(self, file_path: str, file_type: str = None) -> str:
        """
        Extract text from CV file (auto-detect type).

        Args:
            file_path: Path to CV file
            file_type: Optional file type (pdf, docx)

        Returns:
            Extracted text
        """
        if file_type is None:
            # Auto-detect from extension
            _, ext = os.path.splitext(file_path)
            file_type = ext.lower().lstrip('.')

        if file_type == 'pdf':
            return self.extract_text_from_pdf(file_path)
        elif file_type in ['docx', 'doc']:
            return self.extract_text_from_docx(file_path)
        else:
            raise ValueError(f"Unsupported file type: {file_type}")

    def parse_cv_with_ai(self, cv_text: str) -> Dict:
        """
        Parse CV text using Claude AI.

        Args:
            cv_text: Raw CV text

        Returns:
            Structured CV data
        """
        prompt = f"""You are a professional recruiter analyzing a resume/CV. Extract structured information from this CV.

CV Text:
{cv_text}

Extract the following information in JSON format:

{{
  "contact_info": {{
    "name": "Full name",
    "email": "Email address",
    "phone": "Phone number",
    "location": "City, State/Country"
  }},
  "summary": "Brief professional summary (2-3 sentences)",
  "education": [
    {{
      "degree": "Degree name",
      "field": "Field of study",
      "school": "University name",
      "graduation_year": "Year or 'Expected YYYY'",
      "gpa": "GPA if mentioned"
    }}
  ],
  "work_history": [
    {{
      "company": "Company name",
      "title": "Job title",
      "start_date": "YYYY-MM or 'YYYY'",
      "end_date": "YYYY-MM or 'Present'",
      "duration": "e.g., '2 years 3 months'",
      "description": "Key responsibilities and achievements",
      "technologies": ["Tech1", "Tech2"]
    }}
  ],
  "skills": {{
    "technical": ["Python", "JavaScript", "AWS"],
    "soft_skills": ["Leadership", "Communication"],
    "languages": ["English (Native)", "Spanish (Fluent)"]
  }},
  "certifications": [
    {{
      "name": "Certification name",
      "issuer": "Issuing organization",
      "date": "YYYY-MM"
    }}
  ],
  "projects": [
    {{
      "name": "Project name",
      "description": "Brief description",
      "technologies": ["Tech1", "Tech2"],
      "url": "GitHub or project URL if mentioned"
    }}
  ],
  "achievements": [
    "Notable achievement 1",
    "Notable achievement 2"
  ],
  "gaps": [
    {{
      "type": "employment" or "education",
      "period": "YYYY-MM to YYYY-MM",
      "reason": "Detected reason or 'Unknown'"
    }}
  ]
}}

Important:
- Extract ALL information present in the CV
- If information is missing, use null or empty array
- For dates, use YYYY-MM format when possible
- Identify employment gaps (>6 months between jobs)
- Extract technical skills mentioned anywhere in CV
- Include achievements and quantifiable results

Respond ONLY with valid JSON, no other text."""

        try:
            response = self.client.messages.create(
                model="claude-3-5-sonnet-20241022",
                max_tokens=4096,
                messages=[
                    {"role": "user", "content": prompt}
                ]
            )

            # Extract JSON from response
            json_text = response.content[0].text

            # Remove markdown code blocks if present
            if "```json" in json_text:
                json_text = json_text.split("```json")[1].split("```")[0]
            elif "```" in json_text:
                json_text = json_text.split("```")[1].split("```")[0]

            parsed_data = json.loads(json_text.strip())

            return parsed_data

        except Exception as e:
            raise Exception(f"Error parsing CV with AI: {str(e)}")

    def detect_industry_and_role(self, parsed_cv: Dict) -> Dict:
        """
        Detect industry and role from parsed CV using AI.

        Args:
            parsed_cv: Parsed CV data

        Returns:
            Dict with industry, role, and confidence
        """
        # Build summary of CV for classification
        summary = f"""
Name: {parsed_cv.get('contact_info', {}).get('name', 'Unknown')}
Summary: {parsed_cv.get('summary', '')}

Work History:
"""

        for job in parsed_cv.get('work_history', [])[:3]:  # Last 3 jobs
            summary += f"- {job.get('title', '')} at {job.get('company', '')}\n"

        summary += f"\nSkills: {', '.join(parsed_cv.get('skills', {}).get('technical', [])[:10])}"

        prompt = f"""You are a professional recruiter categorizing a candidate's background.

Candidate Summary:
{summary}

Determine:
1. **Primary Industry**: The industry this candidate has worked in (e.g., finance, technology, healthcare, retail, manufacturing, consulting, etc.)
2. **Primary Role**: The type of role (e.g., backend_engineer, frontend_engineer, system_engineer, data_engineer, product_manager, designer, etc.)
3. **Experience Level**: junior, mid, senior, or staff
4. **Total Years**: Approximate total years of experience
5. **Primary Skills**: Top 5 technical skills

Respond in JSON format:
{{
  "industry": "primary industry (lowercase, snake_case)",
  "industry_confidence": 0.0-1.0,
  "role": "primary role (lowercase, snake_case)",
  "role_confidence": 0.0-1.0,
  "experience_level": "junior/mid/senior/staff",
  "total_years_experience": number,
  "primary_skills": ["skill1", "skill2", "skill3", "skill4", "skill5"],
  "reasoning": "Brief explanation of classification"
}}

Respond ONLY with valid JSON, no other text."""

        try:
            response = self.client.messages.create(
                model="claude-3-5-haiku-20241022",  # Use Haiku for faster/cheaper classification
                max_tokens=1024,
                messages=[
                    {"role": "user", "content": prompt}
                ]
            )

            json_text = response.content[0].text

            if "```json" in json_text:
                json_text = json_text.split("```json")[1].split("```")[0]
            elif "```" in json_text:
                json_text = json_text.split("```")[1].split("```")[0]

            classification = json.loads(json_text.strip())

            return classification

        except Exception as e:
            raise Exception(f"Error detecting industry/role: {str(e)}")

    def parse_cv_file(self, file_path: str) -> Dict:
        """
        Complete CV parsing pipeline.

        Args:
            file_path: Path to CV file

        Returns:
            Complete parsed CV with industry/role detection
        """
        print(f"[CV PARSER] Parsing {file_path}")

        # Step 1: Extract text
        cv_text = self.extract_text(file_path)

        if not cv_text or len(cv_text) < 100:
            raise Exception("CV text too short or empty")

        print(f"[CV PARSER] Extracted {len(cv_text)} characters")

        # Step 2: Parse with AI
        parsed_cv = self.parse_cv_with_ai(cv_text)
        print(f"[CV PARSER] Parsed CV structure")

        # Step 3: Detect industry and role
        classification = self.detect_industry_and_role(parsed_cv)
        print(f"[CV PARSER] Detected: {classification.get('industry')} / {classification.get('role')}")

        # Combine results
        result = {
            "raw_text": cv_text,
            "parsed_data": parsed_cv,
            "classification": classification,
            "parsed_at": datetime.utcnow().isoformat(),
            "parser_version": "1.0"
        }

        return result

    def generate_user_segment_id(self, classification: Dict) -> str:
        """
        Generate user segment ID for cross-learning.

        Format: "role_industry_experienceyrs_primaryskill"
        Example: "system_engineer_finance_5yrs_python"

        Args:
            classification: Classification data

        Returns:
            User segment ID
        """
        role = classification.get('role', 'engineer')
        industry = classification.get('industry', 'tech')
        years = classification.get('total_years_experience', 0)
        primary_skill = classification.get('primary_skills', ['none'])[0].lower()

        # Round years to nearest bucket
        if years <= 2:
            years_bucket = "0-2yrs"
        elif years <= 5:
            years_bucket = "3-5yrs"
        elif years <= 8:
            years_bucket = "6-8yrs"
        else:
            years_bucket = "9plus_yrs"

        segment_id = f"{role}_{industry}_{years_bucket}_{primary_skill}"

        # Clean up (remove spaces, special chars)
        segment_id = segment_id.replace(' ', '_').replace('-', '_').lower()

        return segment_id


# Factory function
def create_cv_parser(anthropic_api_key: Optional[str] = None) -> CVParserService:
    """
    Create CV Parser Service instance.

    Args:
        anthropic_api_key: Optional API key

    Returns:
        CVParserService instance
    """
    return CVParserService(anthropic_api_key=anthropic_api_key)
