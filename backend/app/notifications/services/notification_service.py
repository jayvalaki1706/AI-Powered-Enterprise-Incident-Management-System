from uuid import UUID
from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.notifications.repositories.notification_repository import NotificationRepository
from app.notifications.schemas import NotificationCreate, NotificationBroadcast, NotificationListResponse
from app.notifications.services.websocket_manager import ws_manager
from app.models.notification import Notification, NotificationType


class NotificationService:
    """Business logic layer for notifications with real-time WebSocket delivery."""

    def __init__(self, db: AsyncSession):
        self.repository = NotificationRepository(db)

    # ─── Create & Send ──────────────────────────────────────────────────────────

    async def create_notification(self, data: NotificationCreate) -> Notification:
        """Create a notification and push it via WebSocket if user is online."""
        notification = Notification(
            user_id=data.user_id,
            title=data.title,
            message=data.message,
            type=data.type,
        )
        saved = await self.repository.create(notification)

        # Push real-time notification via WebSocket
        await ws_manager.send_to_user(
            data.user_id,
            {
                "event": "new_notification",
                "data": {
                    "id": str(saved.id),
                    "title": saved.title,
                    "message": saved.message,
                    "type": saved.type.value,
                    "is_read": saved.is_read,
                    "created_at": saved.created_at.isoformat(),
                },
            },
        )

        return saved

    async def send_notification(
        self,
        user_id: UUID,
        title: str,
        message: str,
        notification_type: NotificationType = NotificationType.IN_APP,
    ) -> Notification:
        """Helper to create and send a notification programmatically."""
        data = NotificationCreate(
            user_id=user_id,
            title=title,
            message=message,
            type=notification_type,
        )
        return await self.create_notification(data)

    async def broadcast_notification(self, data: NotificationBroadcast, user_ids: list[UUID]) -> list[Notification]:
        """Send a notification to multiple users."""
        notifications = [
            Notification(
                user_id=uid,
                title=data.title,
                message=data.message,
                type=data.type,
            )
            for uid in user_ids
        ]
        saved = await self.repository.create_bulk(notifications)

        # Push via WebSocket to all online recipients
        ws_message = {
            "event": "new_notification",
            "data": {
                "title": data.title,
                "message": data.message,
                "type": data.type.value,
            },
        }
        for uid in user_ids:
            await ws_manager.send_to_user(uid, ws_message)

        return saved

    # ─── Read ───────────────────────────────────────────────────────────────────

    async def get_user_notifications(
        self,
        user_id: UUID,
        unread_only: bool = False,
        skip: int = 0,
        limit: int = 50,
    ) -> NotificationListResponse:
        """Get notifications for a user with counts."""
        items = await self.repository.get_user_notifications(
            user_id, unread_only=unread_only, skip=skip, limit=limit
        )
        total = await self.repository.get_total_count(user_id)
        unread_count = await self.repository.get_unread_count(user_id)

        return NotificationListResponse(
            items=items,
            total=total,
            unread_count=unread_count,
        )

    async def get_unread_count(self, user_id: UUID) -> int:
        """Get unread notification count."""
        return await self.repository.get_unread_count(user_id)

    # ─── Mark as Read ───────────────────────────────────────────────────────────

    async def mark_as_read(self, notification_id: UUID, user_id: UUID) -> None:
        """Mark a single notification as read."""
        success = await self.repository.mark_as_read(notification_id, user_id)
        if not success:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Notification not found",
            )

        # Notify client to update unread count
        unread = await self.repository.get_unread_count(user_id)
        await ws_manager.send_to_user(
            user_id,
            {"event": "unread_count_updated", "data": {"unread_count": unread}},
        )

    async def mark_all_as_read(self, user_id: UUID) -> int:
        """Mark all notifications as read for a user."""
        count = await self.repository.mark_all_as_read(user_id)

        # Notify client
        await ws_manager.send_to_user(
            user_id,
            {"event": "unread_count_updated", "data": {"unread_count": 0}},
        )

        return count

    # ─── Delete ─────────────────────────────────────────────────────────────────

    async def delete_notification(self, notification_id: UUID, user_id: UUID) -> None:
        """Delete a notification."""
        success = await self.repository.delete(notification_id, user_id)
        if not success:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Notification not found",
            )
