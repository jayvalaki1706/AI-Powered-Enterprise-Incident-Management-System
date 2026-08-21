from pydantic import BaseModel, Field
from uuid import UUID


# ─── Request Schemas ────────────────────────────────────────────────────────────

class LogAnalysisRequest(BaseModel):
    log_content: str = Field(..., min_length=10, max_length=50000, description="Raw log content to analyze")
    incident_id: UUID | None = Field(None, description="Link analysis to an existing incident")


class ChatRequest(BaseModel):
    message: str = Field(..., min_length=1, max_length=5000)
    incident_id: UUID | None = Field(None, description="Provide incident context for the conversation")
    conversation_history: list[dict] | None = Field(None, description="Previous messages for context")


class IncidentActionRequest(BaseModel):
    incident_id: UUID


# ─── Response Schemas ───────────────────────────────────────────────────────────

class LogAnalysisResponse(BaseModel):
    summary: str
    probable_cause: str | None = None
    severity: str  # low, medium, high, critical
    resolution_steps: list[str]
    affected_components: list[str]
    confidence: float = Field(default=0.8, ge=0.0, le=1.0)


class ChatResponse(BaseModel):
    response: str
    incident_context: str | None = None
    suggestions: list[str] | None = None


class ResolutionResponse(BaseModel):
    summary: str
    root_cause: str
    resolution_steps: list[str]
    preventive_measures: list[str]
    estimated_effort: str
    confidence: float = Field(default=0.8, ge=0.0, le=1.0)


class IncidentSummaryResponse(BaseModel):
    title_suggestion: str
    executive_summary: str
    timeline: list[str]
    impact_assessment: str
    current_status: str


class SOPStep(BaseModel):
    step_number: int = 0
    action: str = ""
    expected_result: str = ""


class SOPResponse(BaseModel):
    title: str = ""
    purpose: str = ""
    scope: str = ""
    prerequisites: list[str] = []
    steps: list = []  # Accept any format, will normalize in frontend
    escalation_criteria: str = ""
    rollback_procedure: str = ""
    notes: str = ""


class FiveWhy(BaseModel):
    why: str = ""
    answer: str = ""


class RCAResponse(BaseModel):
    incident_title: str = ""
    summary: str = ""
    root_cause: str = ""
    contributing_factors: list[str] = []
    five_whys: list = []  # Accept any format
    impact: str = ""
    timeline: list[str] = []
    corrective_actions: list[str] = []
    preventive_actions: list[str] = []
    lessons_learned: list[str] = []
