import logging
import os
from datetime import datetime
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session
from app.workers.celery_app import celery_app

logger = logging.getLogger("sla_tasks")


def _get_sync_engine():
    """Get sync SQLAlchemy engine for Celery tasks."""
    db_url = os.getenv(
        "DATABASE_URL_SYNC",
        "postgresql://postgres:password@localhost:5432/incident_management",
    )
    return create_engine(db_url, pool_pre_ping=True)


@celery_app.task(name="app.workers.sla_tasks.check_sla_breaches")
def check_sla_breaches():
    """
    Check for incidents that have breached their SLA deadline.
    Escalates them and notifies managers.
    Runs every 5 minutes via Celery Beat.
    """
    from app.models.incident import Incident, IncidentStatus
    from app.models.user import User, UserRole

    engine = _get_sync_engine()
    breached_count = 0

    with Session(engine) as session:
        # Find unresolved incidents past SLA deadline
        breached_incidents = session.execute(
            select(Incident).where(
                Incident.sla_deadline < datetime.utcnow(),
                Incident.status.in_([
                    IncidentStatus.OPEN,
                    IncidentStatus.IN_PROGRESS,
                ]),
                Incident.sla_deadline.isnot(None),
            )
        ).scalars().all()

        if not breached_incidents:
            logger.info("SLA check: No breaches found.")
            return {"breached": 0}

        # Get manager emails for notifications
        managers = session.execute(
            select(User).where(
                User.role.in_([UserRole.ADMIN, UserRole.INCIDENT_MANAGER, UserRole.TEAM_LEAD]),
                User.is_active == True,
            )
        ).scalars().all()

        manager_emails = [m.email for m in managers]
        manager_ids = [str(m.id) for m in managers]

        for incident in breached_incidents:
            # Escalate
            incident.escalation_level += 1
            incident.status = IncidentStatus.ESCALATED

            breached_count += 1

            # Send email alerts
            from app.workers.email_tasks import send_sla_breach_alert
            for email in manager_emails:
                send_sla_breach_alert.delay(
                    to_email=email,
                    incident_title=incident.title,
                    incident_id=str(incident.id),
                    escalation_level=incident.escalation_level,
                )

            # Send in-app notifications
            from app.workers.notification_tasks import notify_escalation
            notify_escalation.delay(
                manager_ids=manager_ids,
                incident_title=incident.title,
                escalation_level=incident.escalation_level,
            )

        session.commit()

    logger.info(f"SLA check complete: {breached_count} incidents escalated.")
    return {"breached": breached_count}


@celery_app.task(name="app.workers.sla_tasks.check_approaching_sla")
def check_approaching_sla():
    """
    Warn about incidents approaching SLA deadline (within 1 hour).
    Can be added to beat schedule if needed.
    """
    from app.models.incident import Incident, IncidentStatus
    from datetime import timedelta

    engine = _get_sync_engine()

    with Session(engine) as session:
        approaching = session.execute(
            select(Incident).where(
                Incident.sla_deadline.between(
                    datetime.utcnow(),
                    datetime.utcnow() + timedelta(hours=1),
                ),
                Incident.status.in_([
                    IncidentStatus.OPEN,
                    IncidentStatus.IN_PROGRESS,
                ]),
            )
        ).scalars().all()

        for incident in approaching:
            if incident.assigned_to:
                from app.workers.notification_tasks import create_in_app_notification
                create_in_app_notification.delay(
                    user_id=str(incident.assigned_to),
                    title="⏰ SLA Deadline Approaching",
                    message=f"Incident '{incident.title}' SLA deadline is within 1 hour!",
                )

    logger.info(f"SLA warning: {len(approaching)} incidents approaching deadline.")
    return {"approaching": len(approaching)}
