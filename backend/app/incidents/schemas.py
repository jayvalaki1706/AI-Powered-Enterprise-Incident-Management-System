from pydantic import BaseModel, Field
from uuid import UUID
from datetime import datetime
from app.models.incident import IncidentPriority, IncidentStatus


# ─── Request Schemas ────────────────────────────────────────────────────────────

class IncidentCreate(BaseModel):
    title: str = Field(..., min_length=3, max_length=255)
    description: str = Field(..., min_length=10)
    priority: IncidentPriority = IncidentPriority.MEDIUM
    assigned_to: UUID | None = None
    project_id: UUID | None = None


class IncidentUpdate(BaseModel):
    title: str | None = None
    description: str | None = None
    priority: IncidentPriority | None = None
    status: IncidentStatus | None = None
    assigned_to: UUID | None = None


class CommentCreate(BaseModel):
    content: str = Field(..., min_length=1, max_length=5000)


# ─── Response Schemas ───────────────────────────────────────────────────────────

class IncidentResponse(BaseModel):
    id: UUID
    ticket_number: int | None = None
    title: str
    description: str
    priority: IncidentPriority
    status: IncidentStatus
    created_by: UUID
    assigned_to: UUID | None
    project_id: UUID | None
    sla_deadline: datetime | None
    resolved_at: datetime | None
    escalation_level: int
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class CommentResponse(BaseModel):
    id: UUID
    incident_id: UUID
    user_id: UUID
    user_name: str | None = None
    content: str
    created_at: datetime

    class Config:
        from_attributes = True


class HistoryResponse(BaseModel):
    id: UUID
    incident_id: UUID
    user_id: UUID
    field_changed: str
    old_value: str | None
    new_value: str | None
    created_at: datetime

    class Config:
        from_attributes = True


class IncidentListResponse(BaseModel):
    items: list[IncidentResponse]
    total: int
    page: int
    page_size: int
    total_pages: int
