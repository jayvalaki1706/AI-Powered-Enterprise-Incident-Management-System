import json
from uuid import UUID
from math import ceil
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.audit import AuditLog
from app.audit.schemas import AuditLogListResponse


class AuditService:
    """Service for recording and querying audit logs."""

    def __init__(self, db: AsyncSession):
        self.db = db

    # ─── Create Audit Log ───────────────────────────────────────────────────────

    async def log_action(
        self,
        user_id: UUID,
        action: str,
        resource_type: str,
        resource_id: str,
        old_value: str | dict | None = None,
        new_value: str | dict | None = None,
        ip_address: str | None = None,
    ) -> AuditLog:
        """Record an action in the audit log."""
        # Serialize dicts to JSON strings
        if isinstance(old_value, dict):
            old_value = json.dumps(old_value)
        if isinstance(new_value, dict):
            new_value = json.dumps(new_value)

        audit_log = AuditLog(
            user_id=user_id,
            action=action,
            resource_type=resource_type,
            resource_id=str(resource_id),
            old_value=old_value,
            new_value=new_value,
            ip_address=ip_address,
        )
        self.db.add(audit_log)
        await self.db.flush()
        return audit_log

    # ─── Query Audit Logs ───────────────────────────────────────────────────────

    async def get_logs(
        self,
        page: int = 1,
        page_size: int = 50,
        resource_type: str | None = None,
        resource_id: str | None = None,
        user_id: UUID | None = None,
        action: str | None = None,
    ) -> AuditLogListResponse:
        """Query audit logs with filters and pagination."""
        query = select(AuditLog)

        # Apply filters
        if resource_type:
            query = query.where(AuditLog.resource_type == resource_type)
        if resource_id:
            query = query.where(AuditLog.resource_id == resource_id)
        if user_id:
            query = query.where(AuditLog.user_id == user_id)
        if action:
            query = query.where(AuditLog.action == action)

        # Count total
        count_query = select(func.count()).select_from(query.subquery())
        total = (await self.db.execute(count_query)).scalar()

        # Paginate
        query = (
            query
            .order_by(AuditLog.created_at.desc())
            .offset((page - 1) * page_size)
            .limit(page_size)
        )
        result = await self.db.execute(query)
        items = result.scalars().all()

        return AuditLogListResponse(
            items=items,
            total=total,
            page=page,
            page_size=page_size,
            total_pages=ceil(total / page_size) if total > 0 else 0,
        )

    # ─── Get Logs for a Resource ────────────────────────────────────────────────

    async def get_resource_history(
        self,
        resource_type: str,
        resource_id: str,
    ) -> list[AuditLog]:
        """Get full audit trail for a specific resource."""
        result = await self.db.execute(
            select(AuditLog)
            .where(
                AuditLog.resource_type == resource_type,
                AuditLog.resource_id == resource_id,
            )
            .order_by(AuditLog.created_at.desc())
        )
        return result.scalars().all()
