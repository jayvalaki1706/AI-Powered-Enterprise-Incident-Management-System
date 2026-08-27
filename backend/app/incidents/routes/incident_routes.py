import csv
import io
from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession
from starlette.responses import StreamingResponse
import redis.asyncio as aioredis

from app.db.database import get_db
from app.core.dependencies import get_current_user, require_role, get_redis
from app.incidents.schemas import (
    IncidentCreate,
    IncidentUpdate,
    IncidentResponse,
    IncidentListResponse,
    CommentCreate,
    CommentResponse,
    HistoryResponse,
)
from app.incidents.services.incident_service import IncidentService
from app.models.user import User, UserRole
from app.models.incident import IncidentStatus, IncidentPriority


async def _invalidate_analytics_cache(redis_client: aioredis.Redis | None):
    """Clear all analytics caches so new data is reflected immediately."""
    if not redis_client:
        return
    try:
        await redis_client.delete("analytics:dashboard:global", "analytics:sla")
        # Clear all user-specific dashboard caches
        cursor = 0
        while True:
            cursor, keys = await redis_client.scan(cursor, match="analytics:dashboard:*", count=100)
            if keys:
                await redis_client.delete(*keys)
            if cursor == 0:
                break
    except Exception:
        pass

router = APIRouter(prefix="/incidents", tags=["Incidents"])


# ─── CRUD Endpoints ─────────────────────────────────────────────────────────────

@router.post(
    "/",
    response_model=IncidentResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create a new incident",
)
async def create_incident(
    data: IncidentCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
    redis_client=Depends(get_redis),
):
    service = IncidentService(db)
    incident = await service.create_incident(data, current_user)
    await _invalidate_analytics_cache(redis_client)
    return incident


@router.get(
    "/",
    response_model=IncidentListResponse,
    summary="List incidents with pagination and filters",
)
async def list_incidents(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    status_filter: IncidentStatus | None = Query(None, alias="status"),
    priority: IncidentPriority | None = None,
    assigned_to: UUID | None = None,
    created_by: UUID | None = None,
    search: str | None = Query(None, description="Search in title and description"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    service = IncidentService(db)

    # Customers can only see their own incidents
    if current_user.role == UserRole.CUSTOMER:
        created_by = current_user.id

    return await service.list_incidents(
        page=page,
        page_size=page_size,
        status=status_filter,
        priority=priority,
        assigned_to=assigned_to,
        created_by=created_by,
        search=search,
    )


@router.get(
    "/export/csv",
    summary="Export incidents as CSV file (non-customer roles only)",
)
async def export_incidents_csv(
    status_filter: IncidentStatus | None = Query(None, alias="status"),
    priority: IncidentPriority | None = None,
    assigned_to: UUID | None = None,
    created_by: UUID | None = None,
    search: str | None = Query(None, description="Search in title and description"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Export all matching incidents as a CSV file. Restricted to non-customer roles."""
    if current_user.role == UserRole.CUSTOMER:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Customers cannot export incidents",
        )

    service = IncidentService(db)

    # Fetch all matching incidents (large page to get all)
    result = await service.list_incidents(
        page=1,
        page_size=10000,
        status=status_filter,
        priority=priority,
        assigned_to=assigned_to,
        created_by=created_by,
        search=search,
    )

    # Fetch all users to map UUIDs to names
    from app.auth.repositories.user_repository import UserRepository
    user_repo = UserRepository(db)
    all_users = await user_repo.get_all(skip=0, limit=1000)
    user_map = {user.id: user.full_name for user in all_users}

    def get_user_name(user_id):
        if not user_id:
            return "Unassigned"
        return user_map.get(user_id, str(user_id))

    def generate_csv():
        output = io.StringIO()
        writer = csv.writer(output)

        # Header row
        writer.writerow([
            "Title", "Priority", "Status", "Assigned To", "Created By",
            "Created At", "Resolved At", "SLA Deadline", "Escalation Level"
        ])
        yield output.getvalue()
        output.seek(0)
        output.truncate(0)

        # Data rows
        for incident in result.items:
            writer.writerow([
                incident.title,
                incident.priority.value if incident.priority else "",
                incident.status.value if incident.status else "",
                get_user_name(incident.assigned_to),
                get_user_name(incident.created_by),
                incident.created_at.isoformat() if incident.created_at else "",
                incident.resolved_at.isoformat() if incident.resolved_at else "",
                incident.sla_deadline.isoformat() if incident.sla_deadline else "",
                str(incident.escalation_level),
            ])
            yield output.getvalue()
            output.seek(0)
            output.truncate(0)

    return StreamingResponse(
        generate_csv(),
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=incidents_export.csv"},
    )


@router.get(
    "/{incident_id}",
    response_model=IncidentResponse,
    summary="Get a specific incident",
)
async def get_incident(
    incident_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    service = IncidentService(db)
    incident = await service.get_incident(incident_id)

    # Customers can only view their own incidents
    if current_user.role == UserRole.CUSTOMER and incident.created_by != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You do not have access to this incident",
        )

    return incident


@router.patch(
    "/{incident_id}",
    response_model=IncidentResponse,
    summary="Update an incident (tracks changes in history)",
)
async def update_incident(
    incident_id: UUID,
    data: IncidentUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
    redis_client=Depends(get_redis),
):
    service = IncidentService(db)
    incident = await service.update_incident(incident_id, data, current_user)
    await _invalidate_analytics_cache(redis_client)
    return incident


@router.delete(
    "/{incident_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete an incident (creator or admin only)",
)
async def delete_incident(
    incident_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
    redis_client=Depends(get_redis),
):
    service = IncidentService(db)
    await service.delete_incident(incident_id, current_user)
    await _invalidate_analytics_cache(redis_client)


# ─── Assignment & Escalation ────────────────────────────────────────────────────

@router.post(
    "/{incident_id}/assign/{assignee_id}",
    response_model=IncidentResponse,
    summary="Assign incident to an engineer (any non-customer user)",
)
async def assign_incident(
    incident_id: UUID,
    assignee_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
    redis_client=Depends(get_redis),
):
    if current_user.role == UserRole.CUSTOMER:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Customers cannot assign incidents",
        )
    service = IncidentService(db)
    incident = await service.assign_incident(incident_id, assignee_id, current_user)
    await _invalidate_analytics_cache(redis_client)

    # Send email notification to the assignee
    try:
        from app.auth.repositories.user_repository import UserRepository
        from app.notifications.services.notification_dispatcher import NotificationDispatcher
        user_repo = UserRepository(db)
        assignee = await user_repo.get_by_id(assignee_id)
        if assignee:
            dispatcher = NotificationDispatcher(db)
            await dispatcher.notify_assignment(incident, assignee.email)
    except Exception as e:
        import logging
        logging.getLogger("api").warning(f"Failed to send assignment notification: {e}")

    return incident


@router.post(
    "/{incident_id}/assign-me",
    response_model=IncidentResponse,
    summary="Assign incident to yourself (any non-customer user)",
)
async def assign_to_me(
    incident_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
    redis_client=Depends(get_redis),
):
    if current_user.role == UserRole.CUSTOMER:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Customers cannot assign incidents",
        )
    service = IncidentService(db)
    incident = await service.assign_incident(incident_id, current_user.id, current_user)
    await _invalidate_analytics_cache(redis_client)
    return incident


@router.post(
    "/{incident_id}/escalate",
    response_model=IncidentResponse,
    summary="Escalate an incident (Manager/Admin)",
)
async def escalate_incident(
    incident_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role(UserRole.ADMIN, UserRole.INCIDENT_MANAGER, UserRole.TEAM_LEAD)),
    redis_client=Depends(get_redis),
):
    service = IncidentService(db)
    incident = await service.escalate_incident(incident_id, current_user)
    await _invalidate_analytics_cache(redis_client)
    return incident


# ─── Comments ───────────────────────────────────────────────────────────────────

@router.post(
    "/{incident_id}/comments",
    response_model=CommentResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Add a comment to an incident",
)
async def add_comment(
    incident_id: UUID,
    data: CommentCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    service = IncidentService(db)
    return await service.add_comment(incident_id, data, current_user)


@router.get(
    "/{incident_id}/comments",
    summary="Get all comments for an incident",
)
async def get_comments(
    incident_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    service = IncidentService(db)
    comments = await service.get_comments(incident_id)

    # Resolve user names
    from app.auth.repositories.user_repository import UserRepository
    user_repo = UserRepository(db)
    all_users = await user_repo.get_all(skip=0, limit=500)
    user_map = {user.id: user.full_name for user in all_users}

    return [
        {
            "id": c.id,
            "incident_id": c.incident_id,
            "user_id": c.user_id,
            "user_name": user_map.get(c.user_id, "Unknown"),
            "content": c.content,
            "created_at": c.created_at,
        }
        for c in comments
    ]


# ─── History ────────────────────────────────────────────────────────────────────

@router.get(
    "/{incident_id}/history",
    response_model=list[HistoryResponse],
    summary="Get change history for an incident",
)
async def get_history(
    incident_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    service = IncidentService(db)
    return await service.get_history(incident_id)
