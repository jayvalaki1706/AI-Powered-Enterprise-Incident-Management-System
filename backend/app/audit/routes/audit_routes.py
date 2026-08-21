from uuid import UUID
from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.database import get_db
from app.core.dependencies import get_current_user, require_role
from app.audit.schemas import AuditLogResponse, AuditLogListResponse
from app.audit.services.audit_service import AuditService
from app.models.user import User, UserRole

router = APIRouter(prefix="/audit-logs", tags=["Audit Logs"])


@router.get(
    "/",
    response_model=AuditLogListResponse,
    summary="Query audit logs with filters (Admin/Manager)",
)
async def get_audit_logs(
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=100),
    resource_type: str | None = Query(None, description="Filter by resource type (e.g., incident, user)"),
    resource_id: str | None = Query(None, description="Filter by resource ID"),
    user_id: UUID | None = Query(None, description="Filter by user who performed the action"),
    action: str | None = Query(None, description="Filter by action (e.g., create, update, delete)"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role(UserRole.ADMIN, UserRole.INCIDENT_MANAGER, UserRole.TEAM_LEAD)),
):
    service = AuditService(db)
    return await service.get_logs(
        page=page,
        page_size=page_size,
        resource_type=resource_type,
        resource_id=resource_id,
        user_id=user_id,
        action=action,
    )


@router.get(
    "/resource/{resource_type}/{resource_id}",
    response_model=list[AuditLogResponse],
    summary="Get full audit trail for a resource (Admin/Manager)",
)
async def get_resource_audit_trail(
    resource_type: str,
    resource_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role(UserRole.ADMIN, UserRole.INCIDENT_MANAGER, UserRole.TEAM_LEAD)),
):
    service = AuditService(db)
    return await service.get_resource_history(resource_type, resource_id)


@router.get(
    "/my-activity",
    response_model=AuditLogListResponse,
    summary="Get your own audit activity",
)
async def get_my_activity(
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    service = AuditService(db)
    return await service.get_logs(
        page=page,
        page_size=page_size,
        user_id=current_user.id,
    )
