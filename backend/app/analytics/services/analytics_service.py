from sqlalchemy.ext.asyncio import AsyncSession
import redis.asyncio as aioredis
import json

from app.analytics.repositories.analytics_repository import AnalyticsRepository
from app.analytics.schemas import (
    IncidentStats,
    EngineerPerformance,
    TeamPerformance,
    MonthlyTrend,
    PriorityBreakdown,
    DashboardResponse,
    SLAComplianceResponse,
)


class AnalyticsService:
    """Business logic for analytics with Redis caching for production performance."""

    def __init__(self, db: AsyncSession, redis_client: aioredis.Redis | None = None):
        self.repository = AnalyticsRepository(db)
        self.redis = redis_client
        self.cache_ttl = 30  # 30 seconds — short enough for near-real-time, long enough to handle bursts

    # ─── Cache Helpers ──────────────────────────────────────────────────────────

    async def _get_cached(self, key: str):
        """Get data from Redis cache. Returns None on miss or if Redis unavailable."""
        if not self.redis:
            return None
        try:
            data = await self.redis.get(key)
            if data:
                return json.loads(data)
        except Exception:
            pass
        return None

    async def _set_cached(self, key: str, data, ttl: int = None):
        """Set data in Redis cache. Fails silently if Redis unavailable."""
        if not self.redis:
            return
        try:
            await self.redis.set(key, json.dumps(data), ex=ttl or self.cache_ttl)
        except Exception:
            pass

    # ─── Dashboard ──────────────────────────────────────────────────────────────

    async def get_dashboard(self, user_id=None) -> DashboardResponse:
        """Get dashboard data with Redis caching (30s TTL, invalidated on changes)."""
        # Build cache key (different per user for customer isolation)
        cache_key = f"analytics:dashboard:{user_id or 'global'}"

        # Try cache first
        cached = await self._get_cached(cache_key)
        if cached:
            return DashboardResponse(**cached)

        # Cache miss — query DB
        counts = await self.repository.get_incident_counts(user_id=user_id)
        avg_resolution = await self.repository.get_avg_resolution_time(user_id=user_id)
        resolved_today = await self.repository.get_resolved_today(user_id=user_id)
        sla_breached = await self.repository.get_sla_breached_count(user_id=user_id)
        priority = await self.repository.get_priority_breakdown(user_id=user_id)
        trends = await self.repository.get_monthly_trends(user_id=user_id)
        engineers = await self.repository.get_engineer_performance()
        teams = await self.repository.get_top_teams()

        stats = IncidentStats(
            total_incidents=counts["total"],
            open_incidents=counts["open"],
            in_progress_incidents=counts["in_progress"],
            resolved_incidents=counts["resolved"],
            closed_incidents=counts["closed"],
            escalated_incidents=counts["escalated"],
            critical_incidents=counts["critical"],
            avg_resolution_hours=avg_resolution,
            resolved_today=resolved_today,
            sla_breached=sla_breached,
        )

        priority_breakdown = PriorityBreakdown(**priority)

        monthly_trends = [
            MonthlyTrend(
                month=t["month"],
                total_created=t["created"],
                total_resolved=t["resolved"],
            )
            for t in trends
        ]

        top_engineers = [
            EngineerPerformance(
                engineer_id=e["id"],
                engineer_name=e["full_name"],
                total_assigned=e["total_assigned"],
                total_resolved=e["total_resolved"],
                avg_resolution_hours=e["avg_hours"],
                resolution_rate=(
                    round(e["total_resolved"] / e["total_assigned"] * 100, 2)
                    if e["total_assigned"] > 0 else 0.0
                ),
            )
            for e in engineers
        ]

        top_teams = [
            TeamPerformance(
                team_name=t["team_name"],
                total_incidents=t["total_incidents"],
                resolved=t["resolved"],
            )
            for t in teams
        ]

        response = DashboardResponse(
            stats=stats,
            priority_breakdown=priority_breakdown,
            monthly_trends=monthly_trends,
            top_engineers=top_engineers,
            top_teams=top_teams,
        )

        # Store in cache (30s TTL)
        await self._set_cached(cache_key, response.model_dump())

        return response

    # ─── Individual Metrics ─────────────────────────────────────────────────────

    async def get_incident_stats(self) -> IncidentStats:
        """Get incident statistics only."""
        counts = await self.repository.get_incident_counts()
        avg_resolution = await self.repository.get_avg_resolution_time()
        resolved_today = await self.repository.get_resolved_today()
        sla_breached = await self.repository.get_sla_breached_count()

        return IncidentStats(
            total_incidents=counts["total"],
            open_incidents=counts["open"],
            in_progress_incidents=counts["in_progress"],
            resolved_incidents=counts["resolved"],
            closed_incidents=counts["closed"],
            escalated_incidents=counts["escalated"],
            critical_incidents=counts["critical"],
            avg_resolution_hours=avg_resolution,
            resolved_today=resolved_today,
            sla_breached=sla_breached,
        )

    async def get_sla_compliance(self) -> SLAComplianceResponse:
        """Get SLA compliance data (cached 30s)."""
        cache_key = "analytics:sla"
        cached = await self._get_cached(cache_key)
        if cached:
            return SLAComplianceResponse(**cached)

        data = await self.repository.get_sla_compliance()
        response = SLAComplianceResponse(**data)
        await self._set_cached(cache_key, response.model_dump())
        return response

    async def get_engineer_performance(self, limit: int = 10) -> list[EngineerPerformance]:
        """Get engineer performance rankings."""
        engineers = await self.repository.get_engineer_performance(limit=limit)

        return [
            EngineerPerformance(
                engineer_id=e["id"],
                engineer_name=e["full_name"],
                total_assigned=e["total_assigned"],
                total_resolved=e["total_resolved"],
                avg_resolution_hours=e["avg_hours"],
                resolution_rate=(
                    round(e["total_resolved"] / e["total_assigned"] * 100, 2)
                    if e["total_assigned"] > 0 else 0.0
                ),
            )
            for e in engineers
        ]

    async def get_monthly_trends(self, months: int = 6) -> list[MonthlyTrend]:
        """Get monthly trends."""
        trends = await self.repository.get_monthly_trends(months=months)
        return [
            MonthlyTrend(
                month=t["month"],
                total_created=t["created"],
                total_resolved=t["resolved"],
            )
            for t in trends
        ]

    # ─── Cache Invalidation ─────────────────────────────────────────────────────

    async def invalidate_cache(self) -> None:
        """Clear all analytics caches (called after incident changes).
        Uses key pattern to clear all user-specific dashboard caches."""
        if not self.redis:
            return
        try:
            # Delete global and SLA caches
            await self.redis.delete("analytics:dashboard:global", "analytics:sla")
            # Delete all user-specific dashboard caches using scan
            cursor = 0
            while True:
                cursor, keys = await self.redis.scan(cursor, match="analytics:dashboard:*", count=100)
                if keys:
                    await self.redis.delete(*keys)
                if cursor == 0:
                    break
        except Exception:
            pass  # Cache invalidation failure is non-critical
