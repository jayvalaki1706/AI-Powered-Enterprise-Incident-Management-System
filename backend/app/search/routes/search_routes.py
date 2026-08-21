from uuid import UUID
from datetime import datetime
from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.database import get_db
from app.core.dependencies import get_current_user
from app.search.schemas import SearchResponse, SortField, SortOrder
from app.search.services.search_service import SearchService
from app.models.user import User
from app.models.incident import IncidentStatus, IncidentPriority

router = APIRouter(prefix="/search", tags=["Search"])


@router.get(
    "/incidents",
    response_model=SearchResponse,
    summary="Search incidents with full-text search, filters, and sorting",
)
async def search_incidents(
    q: str | None = Query(None, description="Search query (searches title & description)"),
    status: IncidentStatus | None = None,
    priority: IncidentPriority | None = None,
    assigned_to: UUID | None = None,
    created_by: UUID | None = None,
    project_id: UUID | None = None,
    date_from: datetime | None = Query(None, description="Filter: created after (ISO format)"),
    date_to: datetime | None = Query(None, description="Filter: created before (ISO format)"),
    escalation_level_min: int | None = Query(None, ge=0, description="Minimum escalation level"),
    sort_by: SortField = Query(SortField.CREATED_AT, description="Field to sort by"),
    sort_order: SortOrder = Query(SortOrder.DESC, description="Sort direction"),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    service = SearchService(db)
    return await service.search_incidents(
        query=q,
        status=status,
        priority=priority,
        assigned_to=assigned_to,
        created_by=created_by,
        project_id=project_id,
        date_from=date_from,
        date_to=date_to,
        escalation_level_min=escalation_level_min,
        sort_by=sort_by,
        sort_order=sort_order,
        page=page,
        page_size=page_size,
    )


@router.get(
    "/suggestions",
    response_model=list[str],
    summary="Get search autocomplete suggestions",
)
async def search_suggestions(
    q: str = Query(..., min_length=2, description="Search query for suggestions"),
    limit: int = Query(5, ge=1, le=10),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    service = SearchService(db)
    return await service.search_suggestions(q, limit=limit)
