from uuid import UUID
from fastapi import APIRouter, Depends, Query, WebSocket, WebSocketDisconnect, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.database import get_db, AsyncSessionLocal
from app.core.dependencies import get_current_user, require_role
from app.core.security import decode_token
from app.notifications.schemas import (
    NotificationCreate,
    NotificationResponse,
    NotificationListResponse,
    UnreadCountResponse,
)
from app.notifications.services.notification_service import NotificationService
from app.notifications.services.websocket_manager import ws_manager
from app.models.user import User, UserRole

router = APIRouter(prefix="/notifications", tags=["Notifications"])


# ─── REST Endpoints ─────────────────────────────────────────────────────────────

@router.get(
    "/",
    response_model=NotificationListResponse,
    summary="Get your notifications",
)
async def get_notifications(
    unread_only: bool = Query(False, description="Only return unread notifications"),
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    service = NotificationService(db)
    return await service.get_user_notifications(
        current_user.id, unread_only=unread_only, skip=skip, limit=limit
    )


@router.get(
    "/unread-count",
    response_model=UnreadCountResponse,
    summary="Get unread notification count",
)
async def get_unread_count(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    service = NotificationService(db)
    count = await service.get_unread_count(current_user.id)
    return UnreadCountResponse(unread_count=count)


@router.patch(
    "/{notification_id}/read",
    status_code=status.HTTP_200_OK,
    summary="Mark a notification as read",
)
async def mark_as_read(
    notification_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    service = NotificationService(db)
    await service.mark_as_read(notification_id, current_user.id)
    return {"message": "Notification marked as read"}


@router.patch(
    "/read-all",
    status_code=status.HTTP_200_OK,
    summary="Mark all notifications as read",
)
async def mark_all_as_read(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    service = NotificationService(db)
    count = await service.mark_all_as_read(current_user.id)
    return {"message": f"{count} notifications marked as read"}


@router.delete(
    "/{notification_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete a notification",
)
async def delete_notification(
    notification_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    service = NotificationService(db)
    await service.delete_notification(notification_id, current_user.id)


# ─── Admin: Send notification to a user ─────────────────────────────────────────

@router.post(
    "/send",
    response_model=NotificationResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Send a notification to a user (Admin/Manager)",
)
async def send_notification(
    data: NotificationCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role(UserRole.ADMIN, UserRole.INCIDENT_MANAGER, UserRole.TEAM_LEAD)),
):
    service = NotificationService(db)
    return await service.create_notification(data)


# ─── WebSocket Endpoint ──────────────────────────────────────────────────────────

@router.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket, token: str = Query(None)):
    """
    WebSocket endpoint for real-time notifications.
    Connect with: ws://localhost:8000/api/v1/notifications/ws?token={access_token}
    """
    if not token:
        await websocket.close(code=4001, reason="Token required")
        return
    # Validate token
    payload = decode_token(token)
    if not payload or payload.get("type") != "access":
        await websocket.close(code=4001, reason="Invalid token")
        return

    user_id = UUID(payload["sub"])

    # Connect
    await ws_manager.connect(websocket, user_id)

    try:
        # Send initial unread count
        async with AsyncSessionLocal() as db:
            service = NotificationService(db)
            unread = await service.get_unread_count(user_id)
            await websocket.send_json({
                "event": "connected",
                "data": {"unread_count": unread},
            })

        # Keep connection alive and listen for client messages
        while True:
            data = await websocket.receive_text()
            # Client can send "ping" to keep alive
            if data == "ping":
                await websocket.send_json({"event": "pong"})

    except WebSocketDisconnect:
        ws_manager.disconnect(websocket, user_id)
    except Exception:
        ws_manager.disconnect(websocket, user_id)
