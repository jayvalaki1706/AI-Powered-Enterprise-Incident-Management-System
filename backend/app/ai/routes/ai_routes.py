from fastapi import APIRouter, Depends, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from uuid import UUID
import json

from app.db.database import get_db
from app.core.dependencies import get_current_user, require_role
from app.ai.schemas import (
    LogAnalysisRequest,
    LogAnalysisResponse,
    ChatRequest,
    ChatResponse,
    IncidentActionRequest,
    ResolutionResponse,
    IncidentSummaryResponse,
    SOPResponse,
    RCAResponse,
)
from app.ai.services.ai_service import AIService
from app.models.user import User, UserRole
from app.models.ai_interaction import AIInteraction, AIInteractionType

router = APIRouter(prefix="/ai", tags=["AI Assistant"])


async def _save_interaction(
    db: AsyncSession, incident_id: UUID, user_id: UUID,
    interaction_type: AIInteractionType, input_text: str, output_text: str
):
    """Save an AI interaction to the database."""
    try:
        interaction = AIInteraction(
            incident_id=incident_id,
            user_id=user_id,
            interaction_type=interaction_type,
            input_text=input_text[:5000],
            output_text=output_text[:10000],
        )
        db.add(interaction)
        await db.flush()
    except Exception as e:
        import logging
        logging.getLogger("api").error(f"Failed to save AI interaction: {e}")


@router.post(
    "/analyze-logs",
    response_model=LogAnalysisResponse,
    summary="Analyze logs and identify issues, causes, and solutions",
)
async def analyze_logs(
    data: LogAnalysisRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role(
        UserRole.ADMIN, UserRole.INCIDENT_MANAGER, UserRole.TEAM_LEAD, UserRole.ENGINEER
    )),
):
    service = AIService(db)
    result = await service.analyze_logs(data.log_content)

    # Auto-save if incident_id provided
    if data.incident_id:
        await _save_interaction(
            db, data.incident_id, current_user.id,
            AIInteractionType.LOG_ANALYSIS,
            data.log_content[:2000],
            json.dumps(result.model_dump()),
        )

    return result


@router.post(
    "/suggest-resolution",
    response_model=ResolutionResponse,
    summary="Get AI-powered resolution suggestions for an incident",
)
async def suggest_resolution(
    data: IncidentActionRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role(
        UserRole.ADMIN, UserRole.INCIDENT_MANAGER, UserRole.TEAM_LEAD, UserRole.ENGINEER
    )),
):
    service = AIService(db)
    result = await service.suggest_resolution(data.incident_id)

    await _save_interaction(
        db, data.incident_id, current_user.id,
        AIInteractionType.SUGGEST_FIX,
        "Suggest resolution",
        json.dumps(result.model_dump()),
    )

    return result


@router.post(
    "/generate-sop",
    response_model=SOPResponse,
    summary="Generate a Standard Operating Procedure from an incident",
)
async def generate_sop(
    data: IncidentActionRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role(
        UserRole.ADMIN, UserRole.INCIDENT_MANAGER, UserRole.TEAM_LEAD, UserRole.ENGINEER
    )),
):
    service = AIService(db)
    result = await service.generate_sop(data.incident_id)

    await _save_interaction(
        db, data.incident_id, current_user.id,
        AIInteractionType.GENERATE_SOP,
        "Generate SOP",
        json.dumps(result.model_dump()),
    )

    return result


@router.post(
    "/generate-rca",
    response_model=RCAResponse,
    summary="Generate a Root Cause Analysis report for an incident",
)
async def generate_rca(
    data: IncidentActionRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role(
        UserRole.ADMIN, UserRole.INCIDENT_MANAGER, UserRole.TEAM_LEAD, UserRole.ENGINEER
    )),
):
    service = AIService(db)
    result = await service.generate_rca(data.incident_id)

    await _save_interaction(
        db, data.incident_id, current_user.id,
        AIInteractionType.GENERATE_RCA,
        "Generate RCA",
        json.dumps(result.model_dump()),
    )

    return result


@router.post(
    "/summarize-incident",
    response_model=IncidentSummaryResponse,
    summary="Generate an executive summary of an incident",
)
async def summarize_incident(
    data: IncidentActionRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role(
        UserRole.ADMIN, UserRole.INCIDENT_MANAGER, UserRole.TEAM_LEAD, UserRole.ENGINEER
    )),
):
    service = AIService(db)
    result = await service.summarize_incident(data.incident_id)

    await _save_interaction(
        db, data.incident_id, current_user.id,
        AIInteractionType.SUMMARIZE,
        "Summarize incident",
        json.dumps(result.model_dump()),
    )

    return result


@router.post(
    "/chat",
    response_model=ChatResponse,
    summary="Chat with AI assistant (optionally with incident context)",
)
async def chat(
    data: ChatRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role(
        UserRole.ADMIN, UserRole.INCIDENT_MANAGER, UserRole.TEAM_LEAD, UserRole.ENGINEER
    )),
):
    service = AIService(db)
    result = await service.chat(
        message=data.message,
        incident_id=data.incident_id,
        conversation_history=data.conversation_history,
    )

    # Auto-save chat if incident_id provided
    if data.incident_id:
        await _save_interaction(
            db, data.incident_id, current_user.id,
            AIInteractionType.CHAT,
            data.message,
            result.response,
        )

    return result


# ─── History Endpoints ──────────────────────────────────────────────────────────

@router.get(
    "/history/{incident_id}",
    summary="Get all AI interactions for an incident",
)
async def get_ai_history(
    incident_id: UUID,
    interaction_type: str | None = Query(None, description="Filter by type: chat, log_analysis, suggest_fix, generate_sop, generate_rca, summarize"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role(
        UserRole.ADMIN, UserRole.INCIDENT_MANAGER, UserRole.TEAM_LEAD, UserRole.ENGINEER
    )),
):
    """Get saved AI interactions for a specific incident."""
    query = select(AIInteraction).where(
        AIInteraction.incident_id == incident_id
    )
    if interaction_type:
        try:
            type_enum = AIInteractionType(interaction_type)
            query = query.where(AIInteraction.interaction_type == type_enum)
        except ValueError:
            pass  # Invalid type, skip filter
    query = query.order_by(AIInteraction.created_at.asc())

    result = await db.execute(query)
    interactions = result.scalars().all()

    return [
        {
            "id": str(i.id),
            "interaction_type": i.interaction_type.value,
            "input_text": i.input_text,
            "output_text": i.output_text,
            "created_at": i.created_at.isoformat(),
            "user_id": str(i.user_id),
        }
        for i in interactions
    ]


@router.delete(
    "/history/{incident_id}",
    summary="Clear AI history for an incident",
)
async def clear_ai_history(
    incident_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role(UserRole.ADMIN, UserRole.INCIDENT_MANAGER)),
):
    """Delete all AI interactions for an incident."""
    from sqlalchemy import delete
    await db.execute(
        delete(AIInteraction).where(AIInteraction.incident_id == incident_id)
    )
    await db.flush()
    return {"message": "AI history cleared"}
