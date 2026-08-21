from uuid import UUID
from sqlalchemy import select, update, func
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.notification import Notification


class NotificationRepository:
    """Data access layer for notification operations."""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def create(self, notification: Notification) -> Notification:
        """Create a new notification."""
        self.db.add(notification)
        await self.db.flush()
        await self.db.refresh(notification)
        return notification

    async def create_bulk(self, notifications: list[Notification]) -> list[Notification]:
        """Create multiple notifications at once (for broadcast)."""
        self.db.add_all(notifications)
        await self.db.flush()
        for n in notifications:
            await self.db.refresh(n)
        return notifications

    async def get_by_id(self, notification_id: UUID) -> Notification | None:
        """Get a single notification by ID."""
        result = await self.db.execute(
            select(Notification).where(Notification.id == notification_id)
        )
        return result.scalar_one_or_none()

    async def get_user_notifications(
        self,
        user_id: UUID,
        unread_only: bool = False,
        skip: int = 0,
        limit: int = 50,
    ) -> list[Notification]:
        """Get notifications for a user, ordered newest first."""
        query = select(Notification).where(Notification.user_id == user_id)

        if unread_only:
            query = query.where(Notification.is_read == False)

        query = (
            query
            .order_by(Notification.created_at.desc())
            .offset(skip)
            .limit(limit)
        )
        result = await self.db.execute(query)
        return result.scalars().all()

    async def get_total_count(self, user_id: UUID) -> int:
        """Get total notification count for a user."""
        result = await self.db.execute(
            select(func.count(Notification.id)).where(
                Notification.user_id == user_id
            )
        )
        return result.scalar()

    async def get_unread_count(self, user_id: UUID) -> int:
        """Get unread notification count for a user."""
        result = await self.db.execute(
            select(func.count(Notification.id)).where(
                Notification.user_id == user_id,
                Notification.is_read == False,
            )
        )
        return result.scalar()

    async def mark_as_read(self, notification_id: UUID, user_id: UUID) -> bool:
        """Mark a single notification as read. Returns True if updated."""
        result = await self.db.execute(
            update(Notification)
            .where(
                Notification.id == notification_id,
                Notification.user_id == user_id,
            )
            .values(is_read=True)
        )
        await self.db.flush()
        return result.rowcount > 0

    async def mark_all_as_read(self, user_id: UUID) -> int:
        """Mark all notifications as read for a user. Returns count updated."""
        result = await self.db.execute(
            update(Notification)
            .where(
                Notification.user_id == user_id,
                Notification.is_read == False,
            )
            .values(is_read=True)
        )
        await self.db.flush()
        return result.rowcount

    async def delete(self, notification_id: UUID, user_id: UUID) -> bool:
        """Delete a notification. Returns True if deleted."""
        notification = await self.db.execute(
            select(Notification).where(
                Notification.id == notification_id,
                Notification.user_id == user_id,
            )
        )
        notif = notification.scalar_one_or_none()
        if notif:
            await self.db.delete(notif)
            await self.db.flush()
            return True
        return False
