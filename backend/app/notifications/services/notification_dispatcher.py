"""
Notification Dispatcher Service.

Orchestrates both in-app notifications and email notifications for key incident events.
Each method creates an in-app notification and queues an email via Celery.
"""

import logging
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.notifications.services.notification_service import NotificationService
from app.notifications.schemas import NotificationCreate
from app.models.notification import NotificationType
from app.workers.email_tasks import send_notification_email_task

logger = logging.getLogger("notification_dispatcher")


class NotificationDispatcher:
    """Dispatches in-app + email notifications for incident lifecycle events."""

    def __init__(self, db: AsyncSession):
        self.db = db
        self.notification_service = NotificationService(db)

    async def notify_assignment(self, incident, assignee_email: str) -> None:
        """
        Notify an assignee that an incident has been assigned to them.

        Args:
            incident: The Incident model instance.
            assignee_email: Email address of the assigned user.
        """
        title = f"Incident Assigned: {incident.title}"
        message = (
            f"You have been assigned to incident '{incident.title}' "
            f"(Priority: {incident.priority.value.upper()}). "
            f"Please begin investigation."
        )

        # Create in-app notification for the assignee
        if incident.assigned_to:
            await self.notification_service.send_notification(
                user_id=incident.assigned_to,
                title=title,
                message=message,
                notification_type=NotificationType.IN_APP,
            )

        # Queue email via Celery task
        subject = f"Incident Assigned: {incident.title}"
        body_html = f"""
        <h2>Incident Assigned to You</h2>
        <table style="border-collapse:collapse; margin:10px 0;">
            <tr><td style="padding:5px 15px 5px 0;"><strong>Title:</strong></td><td>{incident.title}</td></tr>
            <tr><td style="padding:5px 15px 5px 0;"><strong>Priority:</strong></td><td>{incident.priority.value.upper()}</td></tr>
            <tr><td style="padding:5px 15px 5px 0;"><strong>ID:</strong></td><td>{str(incident.id)}</td></tr>
        </table>
        <p>Please begin investigation immediately.</p>
        """
        send_notification_email_task.delay(assignee_email, subject, body_html)
        logger.info(f"Assignment notification dispatched for incident {incident.id} to {assignee_email}")

    async def notify_escalation(self, incident, manager_emails: list[str]) -> None:
        """
        Notify managers about an incident escalation.

        Args:
            incident: The Incident model instance.
            manager_emails: List of manager email addresses to notify.
        """
        title = f"Incident Escalated: {incident.title} (Level {incident.escalation_level})"
        message = (
            f"Incident '{incident.title}' has been escalated to level {incident.escalation_level}. "
            f"Priority: {incident.priority.value.upper()}. Immediate attention required."
        )

        # Create in-app notification for the incident creator (they should know)
        if incident.created_by:
            await self.notification_service.send_notification(
                user_id=incident.created_by,
                title=title,
                message=message,
                notification_type=NotificationType.IN_APP,
            )

        # Also notify the assignee if there is one
        if incident.assigned_to and incident.assigned_to != incident.created_by:
            await self.notification_service.send_notification(
                user_id=incident.assigned_to,
                title=title,
                message=message,
                notification_type=NotificationType.IN_APP,
            )

        # Queue email for each manager
        subject = f"⚠️ Escalation: {incident.title} (Level {incident.escalation_level})"
        body_html = f"""
        <h2 style="color:orange;">Incident Escalated</h2>
        <p>The following incident has been escalated and requires your attention:</p>
        <table style="border-collapse:collapse; margin:10px 0;">
            <tr><td style="padding:5px 15px 5px 0;"><strong>Title:</strong></td><td>{incident.title}</td></tr>
            <tr><td style="padding:5px 15px 5px 0;"><strong>Priority:</strong></td><td>{incident.priority.value.upper()}</td></tr>
            <tr><td style="padding:5px 15px 5px 0;"><strong>Escalation Level:</strong></td><td>{incident.escalation_level}</td></tr>
            <tr><td style="padding:5px 15px 5px 0;"><strong>ID:</strong></td><td>{str(incident.id)}</td></tr>
        </table>
        <p><strong>Please review and take action.</strong></p>
        """
        for email in manager_emails:
            send_notification_email_task.delay(email, subject, body_html)

        logger.info(
            f"Escalation notification dispatched for incident {incident.id} "
            f"to {len(manager_emails)} manager(s)"
        )

    async def notify_sla_breach(self, incident, manager_emails: list[str]) -> None:
        """
        Notify managers about an SLA breach.

        Args:
            incident: The Incident model instance.
            manager_emails: List of manager email addresses to notify.
        """
        title = f"⚠️ SLA Breach: {incident.title}"
        message = (
            f"Incident '{incident.title}' has breached its SLA deadline. "
            f"Escalation level: {incident.escalation_level}. "
            f"Priority: {incident.priority.value.upper()}. Immediate action required."
        )

        # Create in-app notification for the assignee
        if incident.assigned_to:
            await self.notification_service.send_notification(
                user_id=incident.assigned_to,
                title=title,
                message=message,
                notification_type=NotificationType.IN_APP,
            )

        # Create in-app notification for the creator
        if incident.created_by and incident.created_by != incident.assigned_to:
            await self.notification_service.send_notification(
                user_id=incident.created_by,
                title=title,
                message=message,
                notification_type=NotificationType.IN_APP,
            )

        # Queue email for each manager
        subject = f"🚨 SLA BREACH: {incident.title} (Level {incident.escalation_level})"
        body_html = f"""
        <h2 style="color:red;">SLA Breach Alert</h2>
        <p>The following incident has breached its SLA deadline:</p>
        <table style="border-collapse:collapse; margin:10px 0;">
            <tr><td style="padding:5px 15px 5px 0;"><strong>Title:</strong></td><td>{incident.title}</td></tr>
            <tr><td style="padding:5px 15px 5px 0;"><strong>Priority:</strong></td><td>{incident.priority.value.upper()}</td></tr>
            <tr><td style="padding:5px 15px 5px 0;"><strong>Escalation Level:</strong></td><td>{incident.escalation_level}</td></tr>
            <tr><td style="padding:5px 15px 5px 0;"><strong>SLA Deadline:</strong></td><td>{incident.sla_deadline.isoformat() if incident.sla_deadline else 'N/A'}</td></tr>
            <tr><td style="padding:5px 15px 5px 0;"><strong>ID:</strong></td><td>{str(incident.id)}</td></tr>
        </table>
        <p><strong>Immediate action required.</strong></p>
        """
        for email in manager_emails:
            send_notification_email_task.delay(email, subject, body_html)

        logger.info(
            f"SLA breach notification dispatched for incident {incident.id} "
            f"to {len(manager_emails)} manager(s)"
        )
