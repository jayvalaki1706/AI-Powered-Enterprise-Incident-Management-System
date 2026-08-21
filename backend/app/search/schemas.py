from pydantic import BaseModel, Field
from uuid import UUID
from datetime import datetime
from enum import Enum
from app.models.incident import IncidentPriority, IncidentStatus


class SortOrder(str, Enum):
    ASC = "asc"
    DESC = "desc"


class SortField(str, Enum):
    CREATED_AT = "created_at"
    UPDATED_AT = "updated_at"
    PRIORITY = "priority"
    STATUS = "status"
    TITLE = "title"


class SearchFilters(BaseModel):
    """Filters for search queries."""
    query: str | None = Field(None, description="Full-text search in title and description")
    status: IncidentStatus | None = None
    priority: IncidentPriority | None = None
    assigned_to: UUID | None = None
    created_by: UUID | None = None
    project_id: UUID | None = None
    date_from: datetime | None = Field(None, description="Created after this date")
    date_to: datetime | None = Field(None, description="Created before this date")
    escalation_level_min: int | None = Field(None, ge=0)


class SearchResultItem(BaseModel):
    id: UUID
    title: str
    description: str
    priority: IncidentPriority
    status: IncidentStatus
    created_by: UUID
    assigned_to: UUID | None
    escalation_level: int
    sla_deadline: datetime | None
    resolved_at: datetime | None
    created_at: datetime
    updated_at: datetime
    relevance_score: float | None = None

    class Config:
        from_attributes = True


class SearchResponse(BaseModel):
    items: list[SearchResultItem]
    total: int
    page: int
    page_size: int
    total_pages: int
    query: str | None = None
    filters_applied: dict | None = None
