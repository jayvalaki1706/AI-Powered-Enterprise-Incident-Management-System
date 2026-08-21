import logging
import asyncio
from uuid import UUID
from app.workers.celery_app import celery_app
from app.db.database import AsyncSessionLocal
from app.models.notification import Notification, NotificationType
from app.notifications.services.websocket_manager import ws_manager

logger = logging.getLogger("notification_tasks")


def _run_async(coro):
    """Helper to run async code in sync Celery tasks."""
    try:
        loop = asyncio.get_event_loop()
        if loop.is_running():
            # If loop is running, create a new one
            import concurrent.futures
            with concurrent.futures.ThreadPoolExecutor() as pool:
                return pool.submit(asyncio.run, coro).result()
        return loop.run_until_complete(coro)
    except RuntimeError:
        return asyncio.run(coro)


async def _create_notification(user_id: str, title: str, message: str, notif_type: str):
    """Create a notification in the database."""
    async with AsyncSessionLocal() as db:
        notification = Notification(
            user_id=UUID(user_id),
            title=title,
            message=message,
            type=NotificationType(notif_type),
        )
        db.add(notification)
        await db.commit()
        await db.refresh(notification)

        # Push via WebSocket if user is online
        await ws_manager.send_to_user(
            UUID(user_id),
            {
                "event": "new_notification",
                "data": {
                    "id": str(notification.id),
                    "title": title,
                    "message": message,
                    "type": notif_type,
                },
            },
        )
        return str(notification.id)


# ─── Tasks ──────────────────────────────────────────────────────────────────────

@celery_app.task(name="app.workers.notification_tasks.create_in_app_notification")
def create_in_app_notification(user_id: str, title: str, message: str):
    """Create an in-app notification for a user."""
    try:
        result = _run_async(
            _create_notification(user_id, title, message, NotificationType.IN_APP.value)
        )
        logger.info(f"In-app notification created for user {user_id}: {title}")
        return result
    except Exception as e:
        logger.error(f"Failed to create notification for {user_id}: {e}")


@celery_app.task(name="app.workers.notification_tasks.notify_incident_update")
def notify_incident_update(user_ids: list[str], incident_title: str, update_message: str):
    """Notify multiple users about an incident update."""
    for user_id in user_ids:
        create_in_app_notification.delay(
            user_id=user_id,
            title=f"Incident Update: {incident_title}",
            message=update_message,
        )


@celery_app.task(name="app.workers.notification_tasks.notify_assignment")
def notify_assignment(assignee_id: str, incident_title: str, assigned_by_name: str):
    """Notify an engineer about being assigned to an incident."""
    create_in_app_notification.delay(
        user_id=assignee_id,
        title="New Assignment",
        message=f"You have been assigned to '{incident_title}' by {assigned_by_name}.",
    )


@celery_app.task(name="app.workers.notification_tasks.notify_escalation")
def notify_escalation(manager_ids: list[str], incident_title: str, escalation_level: int):
    """Notify managers about an incident escalation."""
    for manager_id in manager_ids:
        create_in_app_notification.delay(
            user_id=manager_id,
            title=f"Escalation Alert (Level {escalation_level})",
            message=f"Incident '{incident_title}' has been escalated to level {escalation_level}.",
        )
