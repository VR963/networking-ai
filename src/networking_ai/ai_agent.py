"""Anthropic Claude integration for intelligent profile analysis."""

from typing import Dict, List, Optional
import json
from anthropic import Anthropic
from .config import config


class AnthropicAgent:
    """AI agent powered by Anthropic Claude for profile analysis."""

    def __init__(self, api_key: Optional[str] = None):
        """
        Initialize the Anthropic agent.

        Args:
            api_key: Anthropic API key. Defaults to config.ANTHROPIC_API_KEY
        """
        self.api_key = api_key or config.ANTHROPIC_API_KEY
        if not self.api_key:
            raise ValueError("ANTHROPIC_API_KEY must be set in environment or passed to constructor")

        self.client = Anthropic(api_key=self.api_key)
        self.model = config.DEFAULT_MODEL

    def analyze_profile(self, profile: Dict) -> Dict:
        """
        Use Claude to analyze a user profile and extract insights.

        Args:
            profile: User profile dictionary

        Returns:
            Dictionary with analysis results including strengths, interests, and goals
        """
        prompt = f"""Analyze this professional profile and provide insights:

Profile:
{json.dumps(profile, indent=2)}

Please provide:
1. Key strengths and expertise areas
2. Professional interests and focus areas
3. Potential career goals and aspirations
4. Unique value propositions

Respond in JSON format with keys: strengths, interests, goals, value_proposition"""

        message = self.client.messages.create(
            model=self.model,
            max_tokens=config.MAX_TOKENS,
            temperature=config.TEMPERATURE,
            messages=[
                {"role": "user", "content": prompt}
            ]
        )

        # Extract text content from response
        response_text = message.content[0].text

        # Parse JSON from response
        try:
            # Try to extract JSON if wrapped in markdown code blocks
            if "```json" in response_text:
                json_start = response_text.find("```json") + 7
                json_end = response_text.find("```", json_start)
                response_text = response_text[json_start:json_end].strip()
            elif "```" in response_text:
                json_start = response_text.find("```") + 3
                json_end = response_text.find("```", json_start)
                response_text = response_text[json_start:json_end].strip()

            analysis = json.loads(response_text)
        except json.JSONDecodeError:
            # Fallback if JSON parsing fails
            analysis = {
                "strengths": ["Unable to parse strengths"],
                "interests": ["Unable to parse interests"],
                "goals": ["Unable to parse goals"],
                "value_proposition": response_text,
            }

        return analysis

    def generate_introduction(
        self, profile1: Dict, profile2: Dict, match_scores: Dict
    ) -> str:
        """
        Generate a personalized introduction message for connecting two profiles.

        Args:
            profile1: First user's profile
            profile2: Second user's profile
            match_scores: Similarity scores between profiles

        Returns:
            Personalized introduction message
        """
        prompt = f"""Generate a warm, professional introduction message to help these two professionals connect:

Person 1:
{json.dumps(profile1, indent=2)}

Person 2:
{json.dumps(profile2, indent=2)}

Match Score: {match_scores.get('weighted_score', 0):.2f}

The message should:
1. Be concise (2-3 sentences)
2. Highlight why they'd benefit from connecting
3. Mention specific shared interests or complementary skills
4. Be friendly and professional

Write the introduction message:"""

        message = self.client.messages.create(
            model=self.model,
            max_tokens=1024,
            temperature=0.7,
            messages=[
                {"role": "user", "content": prompt}
            ]
        )

        return message.content[0].text.strip()

    def explain_match(
        self, profile1: Dict, profile2: Dict, match_scores: Dict
    ) -> str:
        """
        Generate an explanation for why two profiles are a good match.

        Args:
            profile1: First user's profile
            profile2: Second user's profile
            match_scores: Similarity scores between profiles

        Returns:
            Explanation of the match
        """
        prompt = f"""Explain why these two professional profiles are a good match:

Profile 1:
{json.dumps(profile1, indent=2)}

Profile 2:
{json.dumps(profile2, indent=2)}

Similarity Scores:
- Overall: {match_scores.get('overall_score', 0):.2f}
- Skills: {match_scores.get('skill_score', 0):.2f}
- Weighted: {match_scores.get('weighted_score', 0):.2f}

Provide a brief explanation (2-4 sentences) focusing on:
1. Complementary skills or expertise
2. Shared interests or goals
3. Potential collaboration opportunities"""

        message = self.client.messages.create(
            model=self.model,
            max_tokens=1024,
            temperature=0.7,
            messages=[
                {"role": "user", "content": prompt}
            ]
        )

        return message.content[0].text.strip()

    def suggest_conversation_starters(
        self, profile1: Dict, profile2: Dict
    ) -> List[str]:
        """
        Generate conversation starter suggestions for two profiles.

        Args:
            profile1: First user's profile
            profile2: Second user's profile

        Returns:
            List of conversation starter suggestions
        """
        prompt = f"""Generate 3-5 conversation starter questions or topics for these two professionals:

Profile 1:
{json.dumps(profile1, indent=2)}

Profile 2:
{json.dumps(profile2, indent=2)}

Provide specific, relevant conversation starters as a JSON array of strings."""

        message = self.client.messages.create(
            model=self.model,
            max_tokens=1024,
            temperature=0.8,
            messages=[
                {"role": "user", "content": prompt}
            ]
        )

        response_text = message.content[0].text.strip()

        # Try to parse JSON array
        try:
            if "```json" in response_text:
                json_start = response_text.find("```json") + 7
                json_end = response_text.find("```", json_start)
                response_text = response_text[json_start:json_end].strip()
            elif "```" in response_text:
                json_start = response_text.find("```") + 3
                json_end = response_text.find("```", json_start)
                response_text = response_text[json_start:json_end].strip()

            starters = json.loads(response_text)
            if isinstance(starters, list):
                return starters
        except json.JSONDecodeError:
            pass

        # Fallback: split by newlines or return as single item
        return [line.strip() for line in response_text.split("\n") if line.strip()]

    def enrich_profile(self, profile: Dict) -> Dict:
        """
        Enrich a user profile with AI-generated insights.

        Args:
            profile: Original user profile

        Returns:
            Enhanced profile with additional AI-generated fields
        """
        if not config.ENABLE_AI_ANALYSIS:
            return profile

        try:
            analysis = self.analyze_profile(profile)

            # Add AI insights to profile
            enriched = profile.copy()
            enriched["ai_insights"] = analysis

            return enriched
        except Exception as e:
            # Return original profile if enrichment fails
            print(f"Warning: Profile enrichment failed: {e}")
            return profile
