from uuid import UUID
from datetime import datetime, timedelta
from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.incidents.repositories.incident_repository import IncidentRepository
from app.incidents.schemas import IncidentCreate, IncidentUpdate, CommentCreate, IncidentListResponse
from app.models.incident import Incident, IncidentComment, IncidentHistory, IncidentStatus, IncidentPriority
from app.models.user import User


# SLA hours based on priority
SLA_HOURS = {
    IncidentPriority.LOW: 72,
    IncidentPriority.MEDIUM: 24,
    IncidentPriority.HIGH: 8,
    IncidentPriority.CRITICAL: 2,
}


class IncidentService:
    """Business logic layer for incident management."""

    def __init__(self, db: AsyncSession):
        self.repository = IncidentRepository(db)

    # ─── Create ─────────────────────────────────────────────────────────────────

    async def create_incident(self, data: IncidentCreate, current_user: User) -> Incident:
        """Create a new incident with automatic SLA deadline calculation."""
        sla_deadline = datetime.utcnow() + timedelta(
            hours=SLA_HOURS.get(data.priority, 24)
        )

        incident = Incident(
            title=data.title,
            description=data.description,
            priority=data.priority,
            status=IncidentStatus.OPEN,
            created_by=current_user.id,
            assigned_to=data.assigned_to,
            project_id=data.project_id,
            sla_deadline=sla_deadline,
        )
        return await self.repository.create(incident)

    # ─── Read ───────────────────────────────────────────────────────────────────

    async def get_incident(self, incident_id: UUID) -> Incident:
        """Get a single incident or raise 404."""
        incident = await self.repository.get_by_id(incident_id)
        if not incident:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Incident not found",
            )
        return incident

    async def list_incidents(self, page: int, page_size: int, **filters) -> IncidentListResponse:
        """Get paginated list of incidents with filters."""
        items, total = await self.repository.get_list(
            page=page, page_size=page_size, **filters
        )
        total_pages = (total + page_size - 1) // page_size

        return IncidentListResponse(
            items=items,
            total=total,
            page=page,
            page_size=page_size,
            total_pages=total_pages,
        )

    # ─── Update ─────────────────────────────────────────────────────────────────

    async def update_incident(
        self, incident_id: UUID, data: IncidentUpdate, current_user: User
    ) -> Incident:
        """Update incident fields and track all changes in history."""
        incident = await self.get_incident(incident_id)

        update_data = data.model_dump(exclude_unset=True)

        for field, new_value in update_data.items():
            old_value = getattr(incident, field)

            # Only record if value actually changed
            if str(old_value) != str(new_value):
                history = IncidentHistory(
                    incident_id=incident.id,
                    user_id=current_user.id,
                    field_changed=field,
                    old_value=str(old_value) if old_value is not None else None,
                    new_value=str(new_value) if new_value is not None else None,
                )
                await self.repository.add_history(history)

            setattr(incident, field, new_value)

        # Auto-set resolved_at when status changes to RESOLVED
        if data.status == IncidentStatus.RESOLVED and incident.resolved_at is None:
            incident.resolved_at = datetime.utcnow()

        # Clear resolved_at if re-opened
        if data.status in (IncidentStatus.OPEN, IncidentStatus.IN_PROGRESS):
            incident.resolved_at = None

        return await self.repository.update(incident)

    # ─── Delete ─────────────────────────────────────────────────────────────────

    async def delete_incident(self, incident_id: UUID, current_user: User) -> None:
        """Delete an incident (only creator or admin can delete)."""
        incident = await self.get_incident(incident_id)

        if incident.created_by != current_user.id and current_user.role.value != "ADMIN":
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Only the creator or an admin can delete this incident",
            )

        await self.repository.delete(incident)

    # ─── Comments ───────────────────────────────────────────────────────────────

    async def add_comment(
        self, incident_id: UUID, data: CommentCreate, current_user: User
    ) -> IncidentComment:
        """Add a comment to an incident."""
        await self.get_incident(incident_id)  # Verify incident exists

        comment = IncidentComment(
            incident_id=incident_id,
            user_id=current_user.id,
            content=data.content,
        )
        return await self.repository.add_comment(comment)

    async def get_comments(self, incident_id: UUID) -> list[IncidentComment]:
        """Get all comments for an incident."""
        await self.get_incident(incident_id)  # Verify incident exists
        return await self.repository.get_comments(incident_id)

    # ─── History ────────────────────────────────────────────────────────────────

    async def get_history(self, incident_id: UUID) -> list[IncidentHistory]:
        """Get change history for an incident."""
        await self.get_incident(incident_id)  # Verify incident exists
        return await self.repository.get_history(incident_id)

    # ─── Assignment ─────────────────────────────────────────────────────────────

    async def assign_incident(
        self, incident_id: UUID, assignee_id: UUID, current_user: User
    ) -> Incident:
        """Assign an incident to an engineer."""
        incident = await self.get_incident(incident_id)

        old_assignee = incident.assigned_to
        incident.assigned_to = assignee_id

        # Track in history
        history = IncidentHistory(
            incident_id=incident.id,
            user_id=current_user.id,
            field_changed="assigned_to",
            old_value=str(old_assignee) if old_assignee else None,
            new_value=str(assignee_id),
        )
        await self.repository.add_history(history)

        # Auto-move to in_progress if still open
        if incident.status == IncidentStatus.OPEN:
            incident.status = IncidentStatus.IN_PROGRESS
            status_history = IncidentHistory(
                incident_id=incident.id,
                user_id=current_user.id,
                field_changed="status",
                old_value=IncidentStatus.OPEN.value,
                new_value=IncidentStatus.IN_PROGRESS.value,
            )
            await self.repository.add_history(status_history)

        return await self.repository.update(incident)

    # ─── Escalation ─────────────────────────────────────────────────────────────

    async def escalate_incident(self, incident_id: UUID, current_user: User) -> Incident:
        """Escalate an incident (increase level, change status)."""
        incident = await self.get_incident(incident_id)

        old_level = incident.escalation_level
        incident.escalation_level += 1
        incident.status = IncidentStatus.ESCALATED

        history = IncidentHistory(
            incident_id=incident.id,
            user_id=current_user.id,
            field_changed="escalation_level",
            old_value=str(old_level),
            new_value=str(incident.escalation_level),
        )
        await self.repository.add_history(history)

        return await self.repository.update(incident)
