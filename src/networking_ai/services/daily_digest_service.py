"""
Daily Digest Service - Phase 3 Week 2.

Sends daily email digests to users with summary of:
- New matches
- New messages
- Application updates
"""

from typing import List, Dict
from datetime import datetime, timedelta
from sqlalchemy.orm import Session
from sqlalchemy import and_

from ..models.user import User
from ..models.match import Match, MatchStatus
from ..models.agent_message import AgentMessage
from ..models.application import Application
from ..models.notification import NotificationPreferences
from ..services.email_service import EmailService


class DailyDigestService:
    """Service for sending daily digest emails."""

    def __init__(self, email_service: EmailService):
        """
        Initialize daily digest service.

        Args:
            email_service: Email service instance
        """
        self.email_service = email_service

    async def send_daily_digest_for_user(
        self,
        user: User,
        db: Session
    ) -> bool:
        """
        Send daily digest for a single user.

        Args:
            user: User to send digest to
            db: Database session

        Returns:
            True if sent successfully
        """
        # Check if user has digest enabled
        prefs = db.query(NotificationPreferences).filter(
            NotificationPreferences.user_id == user.id
        ).first()

        if prefs and not prefs.daily_digest_enabled:
            return False

        # Get yesterday's cutoff
        yesterday = datetime.utcnow() - timedelta(days=1)

        # Get new matches from last 24 hours
        matches = db.query(Match).filter(
            Match.talent_user_id == user.id,
            Match.created_at >= yesterday,
            Match.status == MatchStatus.PENDING
        ).limit(10).all()

        # Get new messages from last 24 hours
        messages = db.query(AgentMessage).filter(
            AgentMessage.receiver_user_id == user.id,
            AgentMessage.created_at >= yesterday,
            AgentMessage.is_read == False
        ).limit(10).all()

        # Get applications from last 24 hours
        applications = db.query(Application).filter(
            Application.user_id == user.id,
            Application.created_at >= yesterday
        ).limit(10).all()

        # Skip if no activity
        if not matches and not messages and not applications:
            return False

        # Format data for template
        matches_data = [
            {
                "job_title": m.job_title,
                "company_name": m.company_name,
                "match_score": m.match_score
            }
            for m in matches
        ]

        messages_data = [
            {
                "sender": f"{msg.sender_agent_type} agent",
                "preview": msg.content[:100] + "..." if len(msg.content) > 100 else msg.content
            }
            for msg in messages
        ]

        applications_data = [
            {"job_title": app.job.title if app.job else "Job"}
            for app in applications
        ]

        # Send email
        return await self.email_service.send_daily_digest(
            to_email=user.email,
            user_name=user.full_name or user.email.split("@")[0],
            matches=matches_data,
            messages=messages_data,
            applications=applications_data
        )

    async def send_daily_digests_for_all_users(
        self,
        db: Session,
        limit: Optional[int] = None
    ) -> Dict[str, int]:
        """
        Send daily digests to all users who have it enabled.

        Args:
            db: Database session
            limit: Optional limit on number of users

        Returns:
            Stats: {sent: int, failed: int, skipped: int}
        """
        stats = {"sent": 0, "failed": 0, "skipped": 0}

        # Get all active users
        query = db.query(User).filter(User.is_active == True)
        if limit:
            query = query.limit(limit)

        users = query.all()

        for user in users:
            try:
                success = await self.send_daily_digest_for_user(user, db)
                if success:
                    stats["sent"] += 1
                else:
                    stats["skipped"] += 1
            except Exception as e:
                print(f"[DailyDigest] Failed for user {user.id}: {e}")
                stats["failed"] += 1

        return stats


def create_daily_digest_service(email_service: EmailService) -> DailyDigestService:
    """
    Factory function to create daily digest service.

    Args:
        email_service: Email service instance

    Returns:
        DailyDigestService instance
    """
    return DailyDigestService(email_service=email_service)
