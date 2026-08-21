from pydantic import BaseModel
from uuid import UUID
from datetime import datetime


class AuditLogResponse(BaseModel):
    id: UUID
    user_id: UUID
    action: str
    resource_type: str
    resource_id: str
    old_value: str | None
    new_value: str | None
    ip_address: str | None
    created_at: datetime

    class Config:
        from_attributes = True


class AuditLogListResponse(BaseModel):
    items: list[AuditLogResponse]
    total: int
    page: int
    page_size: int
    total_pages: int


class AuditLogCreate(BaseModel):
    """Internal schema for creating audit logs programmatically."""
    user_id: UUID
    action: str
    resource_type: str
    resource_id: str
    old_value: str | None = None
    new_value: str | None = None
    ip_address: str | None = None
