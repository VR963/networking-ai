"""
Memory Analytics Service - Performance tracking and insights

Features:
- Track cache hit rates across tiers
- Monitor query performance
- User-level and system-level statistics
- Time-bucketed analytics (hourly, daily, weekly)
- Storage usage tracking
"""

import logging
from typing import Dict, Any, Optional, List
from datetime import datetime, timedelta

from sqlalchemy.orm import Session
from sqlalchemy import func, and_, or_

from ..models.memory import UserMemory, MemoryAnalytics, MemoryTier

logger = logging.getLogger(__name__)


class MemoryAnalyticsService:
    """
    Service for tracking and analyzing memory system performance.

    Tracks:
    - Cache hit rates (hot/warm/cold)
    - Query performance
    - Tier distribution
    - Storage usage
    - User activity patterns
    """

    def __init__(self, db_session: Session):
        """
        Initialize Memory Analytics Service.

        Args:
            db_session: SQLAlchemy database session
        """
        self.db = db_session

    def record_query(
        self,
        user_id: int,
        tier_hit: str,
        query_time_ms: float
    ):
        """
        Record a memory query event.

        Args:
            user_id: User ID
            tier_hit: Tier that served the query ('hot', 'warm', 'cold', 'miss')
            query_time_ms: Query time in milliseconds
        """
        try:
            # Get or create current hour bucket
            now = datetime.utcnow()
            hour_start = now.replace(minute=0, second=0, microsecond=0)

            analytics = self.db.query(MemoryAnalytics).filter(
                and_(
                    MemoryAnalytics.user_id == user_id,
                    MemoryAnalytics.timestamp == hour_start,
                    MemoryAnalytics.bucket_size == "hour"
                )
            ).first()

            if not analytics:
                analytics = MemoryAnalytics(
                    user_id=user_id,
                    timestamp=hour_start,
                    bucket_size="hour"
                )
                self.db.add(analytics)

            # Update counters
            if tier_hit == 'hot':
                analytics.hot_tier_hits += 1
            elif tier_hit == 'warm':
                analytics.warm_tier_hits += 1
            elif tier_hit == 'cold':
                analytics.cold_tier_hits += 1
            else:
                analytics.cache_misses += 1

            # Update query metrics
            analytics.total_queries += 1

            # Update average query time (running average)
            if analytics.avg_query_time_ms:
                analytics.avg_query_time_ms = (
                    (analytics.avg_query_time_ms * (analytics.total_queries - 1) + query_time_ms)
                    / analytics.total_queries
                )
            else:
                analytics.avg_query_time_ms = query_time_ms

            self.db.commit()

        except Exception as e:
            logger.error(f"Failed to record query analytics: {str(e)}")
            self.db.rollback()

    def get_user_analytics(
        self,
        user_id: int,
        hours: int = 24
    ) -> Dict[str, Any]:
        """
        Get analytics for a specific user.

        Args:
            user_id: User ID
            hours: Time window in hours (default 24)

        Returns:
            Dictionary with user analytics
        """
        try:
            cutoff = datetime.utcnow() - timedelta(hours=hours)

            # Get analytics records
            records = self.db.query(MemoryAnalytics).filter(
                and_(
                    MemoryAnalytics.user_id == user_id,
                    MemoryAnalytics.timestamp >= cutoff
                )
            ).all()

            if not records:
                return self._empty_analytics()

            # Aggregate metrics
            total_hot = sum(r.hot_tier_hits for r in records)
            total_warm = sum(r.warm_tier_hits for r in records)
            total_cold = sum(r.cold_tier_hits for r in records)
            total_misses = sum(r.cache_misses for r in records)
            total_queries = sum(r.total_queries for r in records)

            # Calculate rates
            cache_hit_rate = 0.0
            hot_hit_rate = 0.0
            if total_queries > 0:
                cache_hit_rate = (total_hot + total_warm) / total_queries
                hot_hit_rate = total_hot / total_queries

            # Average query time
            avg_query_times = [r.avg_query_time_ms for r in records if r.avg_query_time_ms]
            avg_query_time = sum(avg_query_times) / len(avg_query_times) if avg_query_times else 0.0

            # Get current tier distribution
            tier_dist = self._get_tier_distribution(user_id)

            # Get memory count
            total_memories = self.db.query(func.count(UserMemory.id)).filter(
                and_(
                    UserMemory.user_id == user_id,
                    UserMemory.is_deleted == False
                )
            ).scalar() or 0

            return {
                "user_id": user_id,
                "time_window_hours": hours,
                "cache_performance": {
                    "total_queries": total_queries,
                    "hot_tier_hits": total_hot,
                    "warm_tier_hits": total_warm,
                    "cold_tier_hits": total_cold,
                    "cache_misses": total_misses,
                    "cache_hit_rate": round(cache_hit_rate, 3),
                    "hot_hit_rate": round(hot_hit_rate, 3)
                },
                "performance": {
                    "avg_query_time_ms": round(avg_query_time, 2)
                },
                "tier_distribution": tier_dist,
                "total_memories": total_memories
            }

        except Exception as e:
            logger.error(f"Failed to get user analytics: {str(e)}")
            return self._empty_analytics()

    def get_system_analytics(
        self,
        hours: int = 24
    ) -> Dict[str, Any]:
        """
        Get system-wide analytics.

        Args:
            hours: Time window in hours (default 24)

        Returns:
            Dictionary with system analytics
        """
        try:
            cutoff = datetime.utcnow() - timedelta(hours=hours)

            # Get all analytics records
            records = self.db.query(MemoryAnalytics).filter(
                MemoryAnalytics.timestamp >= cutoff
            ).all()

            if not records:
                return self._empty_analytics()

            # Aggregate metrics
            total_hot = sum(r.hot_tier_hits for r in records)
            total_warm = sum(r.warm_tier_hits for r in records)
            total_cold = sum(r.cold_tier_hits for r in records)
            total_misses = sum(r.cache_misses for r in records)
            total_queries = sum(r.total_queries for r in records)

            # Calculate rates
            cache_hit_rate = 0.0
            hot_hit_rate = 0.0
            if total_queries > 0:
                cache_hit_rate = (total_hot + total_warm) / total_queries
                hot_hit_rate = total_hot / total_queries

            # Average query time
            avg_query_times = [r.avg_query_time_ms for r in records if r.avg_query_time_ms]
            avg_query_time = sum(avg_query_times) / len(avg_query_times) if avg_query_times else 0.0

            # Get system-wide tier distribution
            tier_dist = self._get_tier_distribution(user_id=None)

            # Get total memory count
            total_memories = self.db.query(func.count(UserMemory.id)).filter(
                UserMemory.is_deleted == False
            ).scalar() or 0

            # Get active users count
            active_users = self.db.query(func.count(func.distinct(MemoryAnalytics.user_id))).filter(
                MemoryAnalytics.timestamp >= cutoff
            ).scalar() or 0

            return {
                "time_window_hours": hours,
                "cache_performance": {
                    "total_queries": total_queries,
                    "hot_tier_hits": total_hot,
                    "warm_tier_hits": total_warm,
                    "cold_tier_hits": total_cold,
                    "cache_misses": total_misses,
                    "cache_hit_rate": round(cache_hit_rate, 3),
                    "hot_hit_rate": round(hot_hit_rate, 3)
                },
                "performance": {
                    "avg_query_time_ms": round(avg_query_time, 2)
                },
                "tier_distribution": tier_dist,
                "total_memories": total_memories,
                "active_users": active_users
            }

        except Exception as e:
            logger.error(f"Failed to get system analytics: {str(e)}")
            return self._empty_analytics()

    def get_user_insights(
        self,
        user_id: int
    ) -> Dict[str, Any]:
        """
        Get actionable insights for a user.

        Provides recommendations based on usage patterns.

        Args:
            user_id: User ID

        Returns:
            Dictionary with insights and recommendations
        """
        try:
            analytics = self.get_user_analytics(user_id, hours=168)  # 7 days

            insights = {
                "user_id": user_id,
                "insights": [],
                "recommendations": []
            }

            # Insight: Low cache hit rate
            if analytics["cache_performance"]["cache_hit_rate"] < 0.5:
                insights["insights"].append({
                    "type": "low_cache_hit_rate",
                    "severity": "warning",
                    "message": "Your cache hit rate is below 50%. Memory queries are not benefiting from caching."
                })
                insights["recommendations"].append({
                    "action": "increase_important_memories",
                    "message": "Mark frequently accessed memories as important to keep them in hot tier."
                })

            # Insight: Many memories in cold tier
            cold_count = analytics["tier_distribution"]["cold"]
            total = analytics["total_memories"]
            if total > 0 and (cold_count / total) > 0.6:
                insights["insights"].append({
                    "type": "high_cold_tier_usage",
                    "severity": "info",
                    "message": f"Over 60% of your memories are in cold tier (archived). This is normal for rarely accessed data."
                })

            # Insight: Slow queries
            avg_time = analytics["performance"]["avg_query_time_ms"]
            if avg_time > 5000:
                insights["insights"].append({
                    "type": "slow_queries",
                    "severity": "warning",
                    "message": f"Average query time is {avg_time:.0f}ms. Queries are hitting cold tier frequently."
                })
                insights["recommendations"].append({
                    "action": "optimize_queries",
                    "message": "Consider adding more specific search terms to improve hit rates in hot/warm tiers."
                })

            # Insight: No recent activity
            if analytics["cache_performance"]["total_queries"] == 0:
                insights["insights"].append({
                    "type": "no_activity",
                    "severity": "info",
                    "message": "No memory queries in the past week."
                })

            return insights

        except Exception as e:
            logger.error(f"Failed to get user insights: {str(e)}")
            return {
                "user_id": user_id,
                "insights": [],
                "recommendations": []
            }

    def aggregate_hourly_to_daily(
        self,
        date: Optional[datetime] = None
    ) -> int:
        """
        Aggregate hourly analytics into daily buckets.

        Args:
            date: Date to aggregate (default: yesterday)

        Returns:
            Number of daily records created
        """
        try:
            if not date:
                date = datetime.utcnow() - timedelta(days=1)

            # Get start and end of day
            day_start = date.replace(hour=0, minute=0, second=0, microsecond=0)
            day_end = day_start + timedelta(days=1)

            # Get hourly records for the day
            hourly_records = self.db.query(MemoryAnalytics).filter(
                and_(
                    MemoryAnalytics.timestamp >= day_start,
                    MemoryAnalytics.timestamp < day_end,
                    MemoryAnalytics.bucket_size == "hour"
                )
            ).all()

            if not hourly_records:
                return 0

            # Group by user
            user_aggregates = {}
            for record in hourly_records:
                uid = record.user_id
                if uid not in user_aggregates:
                    user_aggregates[uid] = {
                        "hot_tier_hits": 0,
                        "warm_tier_hits": 0,
                        "cold_tier_hits": 0,
                        "cache_misses": 0,
                        "total_queries": 0,
                        "query_times": []
                    }

                user_aggregates[uid]["hot_tier_hits"] += record.hot_tier_hits
                user_aggregates[uid]["warm_tier_hits"] += record.warm_tier_hits
                user_aggregates[uid]["cold_tier_hits"] += record.cold_tier_hits
                user_aggregates[uid]["cache_misses"] += record.cache_misses
                user_aggregates[uid]["total_queries"] += record.total_queries
                if record.avg_query_time_ms:
                    user_aggregates[uid]["query_times"].append(record.avg_query_time_ms)

            # Create daily records
            count = 0
            for user_id, agg in user_aggregates.items():
                # Calculate average query time
                avg_time = (
                    sum(agg["query_times"]) / len(agg["query_times"])
                    if agg["query_times"]
                    else None
                )

                daily_record = MemoryAnalytics(
                    user_id=user_id,
                    timestamp=day_start,
                    bucket_size="day",
                    hot_tier_hits=agg["hot_tier_hits"],
                    warm_tier_hits=agg["warm_tier_hits"],
                    cold_tier_hits=agg["cold_tier_hits"],
                    cache_misses=agg["cache_misses"],
                    total_queries=agg["total_queries"],
                    avg_query_time_ms=avg_time
                )

                self.db.add(daily_record)
                count += 1

            self.db.commit()

            logger.info(f"Aggregated {len(hourly_records)} hourly records into {count} daily records for {day_start.date()}")
            return count

        except Exception as e:
            logger.error(f"Failed to aggregate hourly to daily: {str(e)}")
            self.db.rollback()
            return 0

    def _get_tier_distribution(
        self,
        user_id: Optional[int] = None
    ) -> Dict[str, int]:
        """
        Get current tier distribution.

        Args:
            user_id: Optional user ID (None = system-wide)

        Returns:
            Dictionary with tier counts
        """
        try:
            query = self.db.query(UserMemory).filter(
                UserMemory.is_deleted == False
            )

            if user_id:
                query = query.filter(UserMemory.user_id == user_id)

            hot = query.filter(UserMemory.memory_tier == MemoryTier.HOT).count()
            warm = query.filter(UserMemory.memory_tier == MemoryTier.WARM).count()
            cold = query.filter(UserMemory.memory_tier == MemoryTier.COLD).count()

            return {
                "hot": hot,
                "warm": warm,
                "cold": cold
            }

        except Exception as e:
            logger.error(f"Failed to get tier distribution: {str(e)}")
            return {"hot": 0, "warm": 0, "cold": 0}

    def _empty_analytics(self) -> Dict[str, Any]:
        """Return empty analytics structure."""
        return {
            "cache_performance": {
                "total_queries": 0,
                "hot_tier_hits": 0,
                "warm_tier_hits": 0,
                "cold_tier_hits": 0,
                "cache_misses": 0,
                "cache_hit_rate": 0.0,
                "hot_hit_rate": 0.0
            },
            "performance": {
                "avg_query_time_ms": 0.0
            },
            "tier_distribution": {
                "hot": 0,
                "warm": 0,
                "cold": 0
            },
            "total_memories": 0
        }
