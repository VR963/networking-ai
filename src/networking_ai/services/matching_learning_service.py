"""
Matching Learning Service - Phase 2.

Implements learning loop to improve matching algorithm based on user feedback.

Key Features:
- Collect match feedback (interested/not interested + reasons)
- Analyze feedback patterns
- Adjust matching weights dynamically
- Personalize matching for individual users
- Track algorithm performance metrics
"""

from typing import List, Dict, Optional
from datetime import datetime, timedelta
from sqlalchemy.orm import Session
from sqlalchemy import func
import json

from ..models.match import Match, MatchStatus
from ..models.user import User
from ..models.personal_ai_agent import PersonalAIAgent


class MatchingLearningService:
    """
    Service for learning from match feedback to improve matching.

    Uses feedback to:
    1. Adjust skill vs preference vs culture weights
    2. Identify user-specific preferences
    3. Improve match score predictions
    4. Reduce irrelevant matches
    """

    def __init__(self):
        """Initialize learning service."""
        # Default weights (can be adjusted per user)
        self.default_weights = {
            "skill_match": 0.5,      # 50%
            "preference_match": 0.3,  # 30%
            "culture_match": 0.2      # 20%
        }

    def collect_feedback_patterns(
        self,
        user_id: int,
        db: Session,
        lookback_days: int = 30
    ) -> Dict:
        """
        Collect and analyze feedback patterns for a user.

        Args:
            user_id: User ID
            db: Database session
            lookback_days: Days to look back for feedback

        Returns:
            Feedback analysis dict
        """
        cutoff_date = datetime.utcnow() - timedelta(days=lookback_days)

        # Get matches with feedback
        matches_with_feedback = db.query(Match).filter(
            Match.talent_user_id == user_id,
            Match.talent_responded_at >= cutoff_date,
            Match.talent_feedback.in_(["interested", "not_interested"])
        ).all()

        if not matches_with_feedback:
            return {
                "total_feedback": 0,
                "patterns": {},
                "message": "No feedback data available"
            }

        # Analyze patterns
        interested_matches = [m for m in matches_with_feedback if m.talent_feedback == "interested"]
        not_interested_matches = [m for m in matches_with_feedback if m.talent_feedback == "not_interested"]

        analysis = {
            "total_feedback": len(matches_with_feedback),
            "interested_count": len(interested_matches),
            "not_interested_count": len(not_interested_matches),
            "interest_rate": len(interested_matches) / len(matches_with_feedback) if matches_with_feedback else 0,
            "patterns": {}
        }

        # Analyze interested matches
        if interested_matches:
            analysis["patterns"]["interested"] = {
                "avg_match_score": sum(m.match_score for m in interested_matches) / len(interested_matches),
                "avg_skill_match": sum(m.skill_match_score for m in interested_matches if m.skill_match_score) / len([m for m in interested_matches if m.skill_match_score]) if any(m.skill_match_score for m in interested_matches) else 0,
                "avg_preference_match": sum(m.preference_match_score for m in interested_matches if m.preference_match_score) / len([m for m in interested_matches if m.preference_match_score]) if any(m.preference_match_score for m in interested_matches) else 0,
                "avg_culture_match": sum(m.culture_match_score for m in interested_matches if m.culture_match_score) / len([m for m in interested_matches if m.culture_match_score]) if any(m.culture_match_score for m in interested_matches) else 0,
                "common_skills": self._extract_common_skills(interested_matches),
                "common_feedback_reasons": self._extract_common_reasons(interested_matches)
            }

        # Analyze not interested matches
        if not_interested_matches:
            analysis["patterns"]["not_interested"] = {
                "avg_match_score": sum(m.match_score for m in not_interested_matches) / len(not_interested_matches),
                "avg_skill_match": sum(m.skill_match_score for m in not_interested_matches if m.skill_match_score) / len([m for m in not_interested_matches if m.skill_match_score]) if any(m.skill_match_score for m in not_interested_matches) else 0,
                "avg_preference_match": sum(m.preference_match_score for m in not_interested_matches if m.preference_match_score) / len([m for m in not_interested_matches if m.preference_match_score]) if any(m.preference_match_score for m in not_interested_matches) else 0,
                "avg_culture_match": sum(m.culture_match_score for m in not_interested_matches if m.culture_match_score) / len([m for m in not_interested_matches if m.culture_match_score]) if any(m.culture_match_score for m in not_interested_matches) else 0,
                "common_rejection_reasons": self._extract_common_reasons(not_interested_matches)
            }

        return analysis

    def calculate_personalized_weights(
        self,
        user_id: int,
        db: Session
    ) -> Dict[str, float]:
        """
        Calculate personalized matching weights based on user feedback.

        Adjusts weights to maximize likelihood of user interest.

        Args:
            user_id: User ID
            db: Database session

        Returns:
            Personalized weight dict
        """
        feedback_patterns = self.collect_feedback_patterns(user_id, db)

        if feedback_patterns["total_feedback"] < 5:
            # Not enough data - use defaults
            return {
                **self.default_weights,
                "personalized": False,
                "reason": "Insufficient feedback data (minimum 5 required)"
            }

        interested = feedback_patterns["patterns"].get("interested", {})
        not_interested = feedback_patterns["patterns"].get("not_interested", {})

        if not interested:
            # No interested matches - can't learn preferences
            return {
                **self.default_weights,
                "personalized": False,
                "reason": "No interested matches to learn from"
            }

        # Calculate relative importance of each dimension
        # Higher scores in interested matches = more important
        skill_importance = interested.get("avg_skill_match", 0.5)
        preference_importance = interested.get("avg_preference_match", 0.5)
        culture_importance = interested.get("avg_culture_match", 0.5)

        # Normalize to sum to 1.0
        total_importance = skill_importance + preference_importance + culture_importance

        if total_importance == 0:
            return {
                **self.default_weights,
                "personalized": False,
                "reason": "Cannot determine importance weights"
            }

        personalized_weights = {
            "skill_match": skill_importance / total_importance,
            "preference_match": preference_importance / total_importance,
            "culture_match": culture_importance / total_importance,
            "personalized": True,
            "based_on_feedback_count": feedback_patterns["total_feedback"],
            "interest_rate": feedback_patterns["interest_rate"]
        }

        return personalized_weights

    def get_match_score_threshold(
        self,
        user_id: int,
        db: Session
    ) -> float:
        """
        Get personalized match score threshold for a user.

        Adjusts threshold based on historical feedback.

        Args:
            user_id: User ID
            db: Database session

        Returns:
            Match score threshold (0.0 to 1.0)
        """
        feedback_patterns = self.collect_feedback_patterns(user_id, db)

        if feedback_patterns["total_feedback"] < 5:
            return 0.6  # Default threshold

        interested = feedback_patterns["patterns"].get("interested", {})

        if not interested:
            return 0.6  # Default

        # Use average match score of interested matches as threshold
        # This ensures we only show matches similar to what they liked
        avg_interested_score = interested.get("avg_match_score", 0.6)

        # Don't set threshold too high (keep some variety)
        threshold = max(0.5, min(0.75, avg_interested_score * 0.9))

        return round(threshold, 2)

    def get_skill_preferences(
        self,
        user_id: int,
        db: Session
    ) -> Dict:
        """
        Extract skill preferences from feedback.

        Identifies which skills the user values most.

        Args:
            user_id: User ID
            db: Database session

        Returns:
            Skill preferences dict
        """
        feedback_patterns = self.collect_feedback_patterns(user_id, db)

        interested = feedback_patterns["patterns"].get("interested", {})
        not_interested = feedback_patterns["patterns"].get("not_interested", {})

        return {
            "preferred_skills": interested.get("common_skills", []),
            "avoided_skills": [],  # TODO: Extract from not_interested feedback
            "skill_importance": "high" if interested.get("avg_skill_match", 0) > 0.8 else "medium"
        }

    def track_algorithm_performance(
        self,
        db: Session,
        days: int = 7
    ) -> Dict:
        """
        Track overall matching algorithm performance.

        Metrics:
        - Match quality (how many matches get positive feedback)
        - Response rate (how many matches get any feedback)
        - Interest rate (percentage of positive feedback)
        - Score calibration (correlation between score and interest)

        Args:
            db: Database session
            days: Days to analyze

        Returns:
            Performance metrics dict
        """
        cutoff_date = datetime.utcnow() - timedelta(days=days)

        # Get all matches in period
        all_matches = db.query(Match).filter(
            Match.created_at >= cutoff_date
        ).all()

        # Get matches with feedback
        matches_with_feedback = [m for m in all_matches if m.talent_responded_at]

        # Get interested matches
        interested_matches = [m for m in all_matches if m.talent_feedback == "interested"]

        total_matches = len(all_matches)

        if total_matches == 0:
            return {
                "period_days": days,
                "total_matches": 0,
                "message": "No matches in period"
            }

        metrics = {
            "period_days": days,
            "total_matches": total_matches,
            "response_rate": len(matches_with_feedback) / total_matches if total_matches > 0 else 0,
            "interest_rate": len(interested_matches) / len(matches_with_feedback) if matches_with_feedback else 0,
            "avg_match_score": sum(m.match_score for m in all_matches) / total_matches,
            "avg_interested_score": sum(m.match_score for m in interested_matches) / len(interested_matches) if interested_matches else 0,
            "score_calibration": self._calculate_score_calibration(matches_with_feedback)
        }

        return metrics

    def _extract_common_skills(self, matches: List[Match]) -> List[str]:
        """Extract most common skills from matches."""
        skill_counts = {}

        for match in matches:
            if match.matched_skills:
                for skill in match.matched_skills:
                    skill_counts[skill] = skill_counts.get(skill, 0) + 1

        # Return top 5 skills
        sorted_skills = sorted(skill_counts.items(), key=lambda x: x[1], reverse=True)
        return [skill for skill, count in sorted_skills[:5]]

    def _extract_common_reasons(self, matches: List[Match]) -> List[str]:
        """Extract common feedback reasons."""
        reasons = []

        for match in matches:
            if match.talent_feedback_reason:
                reasons.append(match.talent_feedback_reason)

        # TODO: Use NLP to cluster similar reasons
        return reasons[:5]  # Return first 5 for now

    def _calculate_score_calibration(self, matches: List[Match]) -> str:
        """
        Calculate how well match scores predict interest.

        Returns calibration quality: "good", "fair", "poor"
        """
        if len(matches) < 10:
            return "insufficient_data"

        interested = [m for m in matches if m.talent_feedback == "interested"]
        not_interested = [m for m in matches if m.talent_feedback == "not_interested"]

        if not interested or not not_interested:
            return "insufficient_data"

        avg_interested_score = sum(m.match_score for m in interested) / len(interested)
        avg_not_interested_score = sum(m.match_score for m in not_interested) / len(not_interested)

        # Good calibration = interested matches have significantly higher scores
        score_diff = avg_interested_score - avg_not_interested_score

        if score_diff > 0.15:
            return "good"  # Clear separation
        elif score_diff > 0.05:
            return "fair"  # Some separation
        else:
            return "poor"  # No clear separation


def create_matching_learning_service() -> MatchingLearningService:
    """Factory function to create learning service."""
    return MatchingLearningService()
