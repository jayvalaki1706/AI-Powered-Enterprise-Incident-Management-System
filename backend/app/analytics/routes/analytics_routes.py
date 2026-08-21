from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.database import get_db
from app.core.dependencies import get_current_user, get_redis, require_role
from app.analytics.schemas import (
    DashboardResponse,
    IncidentStats,
    SLAComplianceResponse,
    EngineerPerformance,
    MonthlyTrend,
)
from app.analytics.services.analytics_service import AnalyticsService
from app.models.user import User, UserRole

router = APIRouter(prefix="/analytics", tags=["Analytics"])


@router.get(
    "/dashboard",
    response_model=DashboardResponse,
    summary="Get full dashboard data (stats, trends, engineers)",
)
async def get_dashboard(
    db: AsyncSession = Depends(get_db),
    redis_client=Depends(get_redis),
    current_user: User = Depends(get_current_user),
):
    service = AnalyticsService(db, redis_client)

    # Customers only see their own incident stats
    user_id = current_user.id if current_user.role == UserRole.CUSTOMER else None

    return await service.get_dashboard(user_id=user_id)


@router.get(
    "/stats",
    response_model=IncidentStats,
    summary="Get incident statistics",
)
async def get_incident_stats(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    service = AnalyticsService(db)
    return await service.get_incident_stats()


@router.get(
    "/sla-compliance",
    response_model=SLAComplianceResponse,
    summary="Get SLA compliance metrics",
)
async def get_sla_compliance(
    db: AsyncSession = Depends(get_db),
    redis_client=Depends(get_redis),
    current_user: User = Depends(get_current_user),
):
    service = AnalyticsService(db, redis_client)
    return await service.get_sla_compliance()


@router.get(
    "/engineer-performance",
    response_model=list[EngineerPerformance],
    summary="Get engineer performance rankings",
)
async def get_engineer_performance(
    limit: int = Query(10, ge=1, le=50, description="Number of top engineers"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role(UserRole.ADMIN, UserRole.INCIDENT_MANAGER, UserRole.TEAM_LEAD)),
):
    service = AnalyticsService(db)
    return await service.get_engineer_performance(limit=limit)


@router.get(
    "/monthly-trends",
    response_model=list[MonthlyTrend],
    summary="Get monthly incident trends",
)
async def get_monthly_trends(
    months: int = Query(6, ge=1, le=24, description="Number of months to look back"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    service = AnalyticsService(db)
    return await service.get_monthly_trends(months=months)


@router.post(
    "/invalidate-cache",
    summary="Clear analytics cache (Admin only)",
)
async def invalidate_cache(
    db: AsyncSession = Depends(get_db),
    redis_client=Depends(get_redis),
    current_user: User = Depends(require_role(UserRole.ADMIN)),
):
    service = AnalyticsService(db, redis_client)
    await service.invalidate_cache()
    return {"message": "Analytics cache cleared"}
