from sqlalchemy import select, func, extract, case
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.incident import Incident, IncidentStatus, IncidentPriority
from app.models.user import User
from datetime import datetime, timedelta
from uuid import UUID


class AnalyticsRepository:
    """Data access layer for analytics queries."""

    def __init__(self, db: AsyncSession):
        self.db = db

    def _apply_user_filter(self, query, user_id: UUID | None):
        """Apply user filter to restrict results to a specific user's incidents."""
        if user_id:
            query = query.where(Incident.created_by == user_id)
        return query

    # ─── Incident Stats ─────────────────────────────────────────────────────────

    async def get_incident_counts(self, user_id: UUID | None = None) -> dict:
        """Get counts of incidents by status."""
        query = select(
            func.count(Incident.id).label("total"),
            func.count(case((Incident.status == IncidentStatus.OPEN, 1))).label("open"),
            func.count(case((Incident.status == IncidentStatus.IN_PROGRESS, 1))).label("in_progress"),
            func.count(case((Incident.status == IncidentStatus.RESOLVED, 1))).label("resolved"),
            func.count(case((Incident.status == IncidentStatus.CLOSED, 1))).label("closed"),
            func.count(case((Incident.status == IncidentStatus.ESCALATED, 1))).label("escalated"),
            func.count(case((Incident.priority == IncidentPriority.CRITICAL, 1))).label("critical"),
        )
        query = self._apply_user_filter(query, user_id)
        result = await self.db.execute(query)
        row = result.one()
        return {
            "total": row.total,
            "open": row.open,
            "in_progress": row.in_progress,
            "resolved": row.resolved,
            "closed": row.closed,
            "escalated": row.escalated,
            "critical": row.critical,
        }

    async def get_avg_resolution_time(self, user_id: UUID | None = None) -> float | None:
        """Get average resolution time in hours for resolved incidents."""
        query = select(
            func.avg(
                extract("epoch", Incident.resolved_at - Incident.created_at) / 3600
            )
        ).where(Incident.resolved_at.isnot(None))
        if user_id:
            query = query.where(Incident.created_by == user_id)
        result = await self.db.execute(query)
        value = result.scalar()
        return round(float(value), 2) if value else None

    # ─── Priority Breakdown ─────────────────────────────────────────────────────

    async def get_priority_breakdown(self, user_id: UUID | None = None) -> dict:
        """Get count of incidents by priority."""
        query = select(
            func.count(case((Incident.priority == IncidentPriority.LOW, 1))).label("low"),
            func.count(case((Incident.priority == IncidentPriority.MEDIUM, 1))).label("medium"),
            func.count(case((Incident.priority == IncidentPriority.HIGH, 1))).label("high"),
            func.count(case((Incident.priority == IncidentPriority.CRITICAL, 1))).label("critical"),
        )
        query = self._apply_user_filter(query, user_id)
        result = await self.db.execute(query)
        row = result.one()
        return {
            "low": row.low,
            "medium": row.medium,
            "high": row.high,
            "critical": row.critical,
        }

    # ─── Monthly Trends ─────────────────────────────────────────────────────────

    async def get_monthly_trends(self, months: int = 6, user_id: UUID | None = None) -> list[dict]:
        """Get monthly incident creation and resolution trends."""
        start_date = datetime.utcnow() - timedelta(days=months * 30)

        month_expr = func.to_char(Incident.created_at, "YYYY-MM")

        query = (
            select(
                month_expr.label("month"),
                func.count(Incident.id).label("created"),
                func.count(case((Incident.resolved_at.isnot(None), 1))).label("resolved"),
            )
            .where(Incident.created_at >= start_date)
        )
        if user_id:
            query = query.where(Incident.created_by == user_id)
        query = query.group_by(month_expr).order_by(month_expr)

        result = await self.db.execute(query)
        rows = result.all()
        return [
            {"month": row.month, "created": row.created, "resolved": row.resolved}
            for row in rows
        ]

    # ─── Engineer Performance ───────────────────────────────────────────────────

    async def get_engineer_performance(self, limit: int = 10) -> list[dict]:
        """Get top engineers by resolved incidents."""
        result = await self.db.execute(
            select(
                User.id,
                User.full_name,
                func.count(Incident.id).label("total_assigned"),
                func.count(case((Incident.resolved_at.isnot(None), 1))).label("total_resolved"),
                func.avg(
                    case(
                        (
                            Incident.resolved_at.isnot(None),
                            extract("epoch", Incident.resolved_at - Incident.created_at) / 3600,
                        )
                    )
                ).label("avg_hours"),
            )
            .join(Incident, Incident.assigned_to == User.id)
            .group_by(User.id, User.full_name)
            .order_by(func.count(case((Incident.resolved_at.isnot(None), 1))).desc())
            .limit(limit)
        )
        rows = result.all()
        return [
            {
                "id": row.id,
                "full_name": row.full_name,
                "total_assigned": row.total_assigned,
                "total_resolved": row.total_resolved,
                "avg_hours": round(float(row.avg_hours), 2) if row.avg_hours else None,
            }
            for row in rows
        ]

    # ─── SLA Compliance ─────────────────────────────────────────────────────────

    async def get_sla_compliance(self) -> dict:
        """Get SLA compliance statistics."""
        # Incidents that have been resolved
        result = await self.db.execute(
            select(
                func.count(Incident.id).label("total"),
                func.count(
                    case((Incident.resolved_at <= Incident.sla_deadline, 1))
                ).label("within_sla"),
                func.count(
                    case((Incident.resolved_at > Incident.sla_deadline, 1))
                ).label("breached"),
            )
            .where(
                Incident.resolved_at.isnot(None),
                Incident.sla_deadline.isnot(None),
            )
        )
        row = result.one()
        total = row.total or 0
        within = row.within_sla or 0
        breached = row.breached or 0

        compliance_rate = (within / total * 100) if total > 0 else 0.0

        return {
            "total_incidents": total,
            "within_sla": within,
            "breached_sla": breached,
            "compliance_rate": round(compliance_rate, 2),
        }

    # ─── Resolved Today ─────────────────────────────────────────────────────────

    async def get_resolved_today(self, user_id: UUID | None = None) -> int:
        """Get count of incidents resolved today."""
        today_start = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)
        query = select(func.count(Incident.id)).where(
            Incident.resolved_at >= today_start,
            Incident.resolved_at.isnot(None),
        )
        if user_id:
            query = query.where(Incident.created_by == user_id)
        result = await self.db.execute(query)
        return result.scalar() or 0

    # ─── SLA Breached (Active) ──────────────────────────────────────────────────

    async def get_sla_breached_count(self, user_id: UUID | None = None) -> int:
        """Get count of active incidents that have breached SLA deadline."""
        query = select(func.count(Incident.id)).where(
            Incident.sla_deadline < datetime.utcnow(),
            Incident.status.in_([IncidentStatus.OPEN, IncidentStatus.IN_PROGRESS, IncidentStatus.ESCALATED]),
            Incident.sla_deadline.isnot(None),
        )
        if user_id:
            query = query.where(Incident.created_by == user_id)
        result = await self.db.execute(query)
        return result.scalar() or 0

    # ─── Top Teams ──────────────────────────────────────────────────────────────

    async def get_top_teams(self, limit: int = 5) -> list[dict]:
        """Get teams with most incident resolutions."""
        from app.models.attachment import Team
        result = await self.db.execute(
            select(
                Team.name,
                func.count(Incident.id).label("total_incidents"),
                func.count(case((Incident.resolved_at.isnot(None), 1))).label("resolved"),
            )
            .join(User, User.department_id == Team.department_id)
            .join(Incident, Incident.assigned_to == User.id)
            .group_by(Team.name)
            .order_by(func.count(Incident.id).desc())
            .limit(limit)
        )
        rows = result.all()
        return [
            {
                "team_name": row.name,
                "total_incidents": row.total_incidents,
                "resolved": row.resolved,
            }
            for row in rows
        ]
