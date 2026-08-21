from math import ceil
from uuid import UUID
from sqlalchemy import select, func, or_, and_
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.incident import Incident, IncidentStatus, IncidentPriority
from app.search.schemas import (
    SearchResponse,
    SearchResultItem,
    SortField,
    SortOrder,
)


class SearchService:
    """Full-text search and advanced filtering for incidents."""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def search_incidents(
        self,
        query: str | None = None,
        status: IncidentStatus | None = None,
        priority: IncidentPriority | None = None,
        assigned_to: UUID | None = None,
        created_by: UUID | None = None,
        project_id: UUID | None = None,
        date_from=None,
        date_to=None,
        escalation_level_min: int | None = None,
        sort_by: SortField = SortField.CREATED_AT,
        sort_order: SortOrder = SortOrder.DESC,
        page: int = 1,
        page_size: int = 20,
    ) -> SearchResponse:
        """Search incidents with full-text search, filters, sorting, and pagination."""
        stmt = select(Incident)
        filters_applied = {}

        # ─── Full-text search ───────────────────────────────────────────────────
        if query:
            search_term = f"%{query}%"
            stmt = stmt.where(
                or_(
                    Incident.title.ilike(search_term),
                    Incident.description.ilike(search_term),
                )
            )
            filters_applied["query"] = query

        # ─── Filters ───────────────────────────────────────────────────────────
        if status:
            stmt = stmt.where(Incident.status == status)
            filters_applied["status"] = status.value
        if priority:
            stmt = stmt.where(Incident.priority == priority)
            filters_applied["priority"] = priority.value
        if assigned_to:
            stmt = stmt.where(Incident.assigned_to == assigned_to)
            filters_applied["assigned_to"] = str(assigned_to)
        if created_by:
            stmt = stmt.where(Incident.created_by == created_by)
            filters_applied["created_by"] = str(created_by)
        if project_id:
            stmt = stmt.where(Incident.project_id == project_id)
            filters_applied["project_id"] = str(project_id)
        if date_from:
            stmt = stmt.where(Incident.created_at >= date_from)
            filters_applied["date_from"] = str(date_from)
        if date_to:
            stmt = stmt.where(Incident.created_at <= date_to)
            filters_applied["date_to"] = str(date_to)
        if escalation_level_min is not None:
            stmt = stmt.where(Incident.escalation_level >= escalation_level_min)
            filters_applied["escalation_level_min"] = escalation_level_min

        # ─── Count total ────────────────────────────────────────────────────────
        count_stmt = select(func.count()).select_from(stmt.subquery())
        total = (await self.db.execute(count_stmt)).scalar()

        # ─── Sorting ───────────────────────────────────────────────────────────
        sort_column = getattr(Incident, sort_by.value, Incident.created_at)
        if sort_order == SortOrder.ASC:
            stmt = stmt.order_by(sort_column.asc())
        else:
            stmt = stmt.order_by(sort_column.desc())

        # ─── Pagination ─────────────────────────────────────────────────────────
        stmt = stmt.offset((page - 1) * page_size).limit(page_size)

        # ─── Execute ────────────────────────────────────────────────────────────
        result = await self.db.execute(stmt)
        items = result.scalars().all()

        return SearchResponse(
            items=items,
            total=total,
            page=page,
            page_size=page_size,
            total_pages=ceil(total / page_size) if total > 0 else 0,
            query=query,
            filters_applied=filters_applied if filters_applied else None,
        )

    async def search_suggestions(self, query: str, limit: int = 5) -> list[str]:
        """Get search suggestions based on incident titles (autocomplete)."""
        if not query or len(query) < 2:
            return []

        result = await self.db.execute(
            select(Incident.title)
            .where(Incident.title.ilike(f"%{query}%"))
            .distinct()
            .limit(limit)
        )
        return [row[0] for row in result.all()]
