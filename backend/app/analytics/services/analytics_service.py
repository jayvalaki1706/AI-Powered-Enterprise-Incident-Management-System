from sqlalchemy.ext.asyncio import AsyncSession
import redis.asyncio as aioredis

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
    """Business logic for analytics with optional Redis caching."""

    def __init__(self, db: AsyncSession, redis_client: aioredis.Redis | None = None):
        self.repository = AnalyticsRepository(db)
        self.redis = redis_client
        self.cache_ttl = 300  # 5 minutes

    # ─── Dashboard ──────────────────────────────────────────────────────────────

    async def get_dashboard(self, user_id=None) -> DashboardResponse:
        """Get full dashboard data (always fresh from DB)."""
        # Fetch from DB directly — no caching for real-time accuracy
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

        return DashboardResponse(
            stats=stats,
            priority_breakdown=priority_breakdown,
            monthly_trends=monthly_trends,
            top_engineers=top_engineers,
            top_teams=top_teams,
        )

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
        """Get SLA compliance data."""
        data = await self.repository.get_sla_compliance()
        return SLAComplianceResponse(**data)

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
        """Clear analytics cache (call after data changes)."""
        if self.redis:
            await self.redis.delete("analytics:dashboard", "analytics:sla")
