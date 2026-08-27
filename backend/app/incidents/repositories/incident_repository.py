from uuid import UUID
from sqlalchemy import select, func, or_
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.incident import (
    Incident,
    IncidentComment,
    IncidentHistory,
    IncidentStatus,
    IncidentPriority,
)


class IncidentRepository:
    """Data access layer for incident-related operations."""

    def __init__(self, db: AsyncSession):
        self.db = db

    # ─── Incident CRUD ──────────────────────────────────────────────────────────

    async def create(self, incident: Incident) -> Incident:
        """Insert a new incident."""
        self.db.add(incident)
        await self.db.flush()
        await self.db.refresh(incident)
        return incident

    async def get_by_id(self, incident_id: UUID) -> Incident | None:
        """Fetch a single incident by ID."""
        result = await self.db.execute(
            select(Incident).where(Incident.id == incident_id)
        )
        return result.scalar_one_or_none()

    async def get_list(
        self,
        page: int = 1,
        page_size: int = 20,
        status: IncidentStatus | None = None,
        priority: IncidentPriority | None = None,
        assigned_to: UUID | None = None,
        created_by: UUID | None = None,
        search: str | None = None,
    ) -> tuple[list[Incident], int]:
        """Get paginated & filtered list of incidents."""
        query = select(Incident)

        # Apply filters
        if status:
            query = query.where(Incident.status == status)
        if priority:
            query = query.where(Incident.priority == priority)
        if assigned_to:
            query = query.where(Incident.assigned_to == assigned_to)
        if created_by:
            query = query.where(Incident.created_by == created_by)
        if search:
            search_conditions = [
                Incident.title.ilike(f"%{search}%"),
                Incident.description.ilike(f"%{search}%"),
            ]
            # If search is numeric, also match ticket number
            search_digits = search.strip().lstrip("#")
            if search_digits.isdigit():
                search_conditions.append(Incident.ticket_number == int(search_digits))
            query = query.where(or_(*search_conditions))

        # Count total matching records
        count_query = select(func.count()).select_from(query.subquery())
        total_result = await self.db.execute(count_query)
        total = total_result.scalar()

        # Apply pagination and ordering
        query = (
            query
            .order_by(Incident.created_at.desc())
            .offset((page - 1) * page_size)
            .limit(page_size)
        )
        result = await self.db.execute(query)
        items = result.scalars().all()

        return items, total

    async def update(self, incident: Incident) -> Incident:
        """Persist changes to an existing incident."""
        await self.db.flush()
        await self.db.refresh(incident)
        return incident

    async def delete(self, incident: Incident) -> None:
        """Delete an incident."""
        await self.db.delete(incident)
        await self.db.flush()

    # ─── Comments ───────────────────────────────────────────────────────────────

    async def add_comment(self, comment: IncidentComment) -> IncidentComment:
        """Add a comment to an incident."""
        self.db.add(comment)
        await self.db.flush()
        await self.db.refresh(comment)
        return comment

    async def get_comments(self, incident_id: UUID) -> list[IncidentComment]:
        """Get all comments for an incident, newest first."""
        result = await self.db.execute(
            select(IncidentComment)
            .where(IncidentComment.incident_id == incident_id)
            .order_by(IncidentComment.created_at.desc())
        )
        return result.scalars().all()

    # ─── History ────────────────────────────────────────────────────────────────

    async def add_history(self, history: IncidentHistory) -> None:
        """Record a field change in incident history."""
        self.db.add(history)
        await self.db.flush()

    async def get_history(self, incident_id: UUID) -> list[IncidentHistory]:
        """Get change history for an incident, newest first."""
        result = await self.db.execute(
            select(IncidentHistory)
            .where(IncidentHistory.incident_id == incident_id)
            .order_by(IncidentHistory.created_at.desc())
        )
        return result.scalars().all()
