from pydantic import BaseModel
from uuid import UUID


class IncidentStats(BaseModel):
    total_incidents: int
    open_incidents: int
    in_progress_incidents: int
    resolved_incidents: int
    closed_incidents: int
    escalated_incidents: int
    critical_incidents: int
    avg_resolution_hours: float | None
    resolved_today: int
    sla_breached: int


class EngineerPerformance(BaseModel):
    engineer_id: UUID
    engineer_name: str
    total_assigned: int
    total_resolved: int
    avg_resolution_hours: float | None
    resolution_rate: float  # percentage


class TeamPerformance(BaseModel):
    team_name: str
    total_incidents: int
    resolved: int


class MonthlyTrend(BaseModel):
    month: str
    total_created: int
    total_resolved: int


class PriorityBreakdown(BaseModel):
    low: int
    medium: int
    high: int
    critical: int


class DashboardResponse(BaseModel):
    stats: IncidentStats
    priority_breakdown: PriorityBreakdown
    monthly_trends: list[MonthlyTrend]
    top_engineers: list[EngineerPerformance]
    top_teams: list[TeamPerformance]


class SLAComplianceResponse(BaseModel):
    total_incidents: int
    within_sla: int
    breached_sla: int
    compliance_rate: float  # percentage
