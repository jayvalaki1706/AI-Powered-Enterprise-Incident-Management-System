import logging
import os
from datetime import datetime, timedelta
from sqlalchemy import create_engine, select, func, case
from sqlalchemy.orm import Session
from app.workers.celery_app import celery_app

logger = logging.getLogger("report_tasks")


def _get_sync_engine():
    """Get sync SQLAlchemy engine for Celery tasks."""
    db_url = os.getenv(
        "DATABASE_URL_SYNC",
        "postgresql://postgres:password@localhost:5432/incident_management",
    )
    return create_engine(db_url, pool_pre_ping=True)


@celery_app.task(name="app.workers.report_tasks.generate_daily_report")
def generate_daily_report():
    """
    Generate and email a daily incident report.
    Runs every day at 8 AM UTC via Celery Beat.
    """
    from app.models.incident import Incident, IncidentStatus, IncidentPriority
    from app.models.user import User, UserRole

    engine = _get_sync_engine()
    yesterday = datetime.utcnow() - timedelta(days=1)

    with Session(engine) as session:
        # Gather metrics
        new_incidents = session.execute(
            select(func.count(Incident.id)).where(Incident.created_at >= yesterday)
        ).scalar() or 0

        resolved = session.execute(
            select(func.count(Incident.id)).where(
                Incident.resolved_at >= yesterday,
                Incident.resolved_at.isnot(None),
            )
        ).scalar() or 0

        open_count = session.execute(
            select(func.count(Incident.id)).where(
                Incident.status.in_([IncidentStatus.OPEN, IncidentStatus.IN_PROGRESS])
            )
        ).scalar() or 0

        critical_open = session.execute(
            select(func.count(Incident.id)).where(
                Incident.priority == IncidentPriority.CRITICAL,
                Incident.status.in_([IncidentStatus.OPEN, IncidentStatus.IN_PROGRESS, IncidentStatus.ESCALATED]),
            )
        ).scalar() or 0

        escalated = session.execute(
            select(func.count(Incident.id)).where(
                Incident.status == IncidentStatus.ESCALATED,
            )
        ).scalar() or 0

        # Get admin/manager emails
        admins = session.execute(
            select(User.email).where(
                User.role.in_([UserRole.ADMIN, UserRole.INCIDENT_MANAGER, UserRole.TEAM_LEAD]),
                User.is_active == True,
            )
        ).scalars().all()

    # Build report email
    report_date = datetime.utcnow().strftime("%Y-%m-%d")
    subject = f"Daily Incident Report - {report_date}"
    body = f"""
    <h2>Daily Incident Report</h2>
    <p><strong>Date:</strong> {report_date}</p>

    <h3>Last 24 Hours</h3>
    <table style="border-collapse:collapse; width:100%; max-width:400px;">
        <tr style="background:#f2f2f2;"><td style="padding:8px; border:1px solid #ddd;"><strong>New Incidents</strong></td><td style="padding:8px; border:1px solid #ddd; text-align:center;">{new_incidents}</td></tr>
        <tr><td style="padding:8px; border:1px solid #ddd;"><strong>Resolved</strong></td><td style="padding:8px; border:1px solid #ddd; text-align:center;">{resolved}</td></tr>
    </table>

    <h3>Current Status</h3>
    <table style="border-collapse:collapse; width:100%; max-width:400px;">
        <tr style="background:#f2f2f2;"><td style="padding:8px; border:1px solid #ddd;"><strong>Open/In Progress</strong></td><td style="padding:8px; border:1px solid #ddd; text-align:center;">{open_count}</td></tr>
        <tr><td style="padding:8px; border:1px solid #ddd;"><strong>Critical (Open)</strong></td><td style="padding:8px; border:1px solid #ddd; text-align:center; color:red;">{critical_open}</td></tr>
        <tr style="background:#f2f2f2;"><td style="padding:8px; border:1px solid #ddd;"><strong>Escalated</strong></td><td style="padding:8px; border:1px solid #ddd; text-align:center; color:orange;">{escalated}</td></tr>
    </table>

    <p style="margin-top:20px; color:#666; font-size:12px;">This is an automated report from the Incident Management System.</p>
    """

    # Send to all admins/managers
    from app.workers.email_tasks import send_email
    for email in admins:
        send_email.delay(email, subject, body)

    logger.info(f"Daily report sent to {len(admins)} recipients: new={new_incidents}, resolved={resolved}, open={open_count}")
    return {
        "new_incidents": new_incidents,
        "resolved": resolved,
        "open": open_count,
        "critical_open": critical_open,
        "recipients": len(admins),
    }


@celery_app.task(name="app.workers.report_tasks.generate_weekly_report")
def generate_weekly_report():
    """
    Generate and email a weekly summary report.
    Runs every Monday at 9 AM UTC via Celery Beat.
    """
    from app.models.incident import Incident, IncidentStatus, IncidentPriority
    from app.models.user import User, UserRole

    engine = _get_sync_engine()
    last_week = datetime.utcnow() - timedelta(days=7)

    with Session(engine) as session:
        # Weekly metrics
        total_created = session.execute(
            select(func.count(Incident.id)).where(Incident.created_at >= last_week)
        ).scalar() or 0

        total_resolved = session.execute(
            select(func.count(Incident.id)).where(
                Incident.resolved_at >= last_week,
                Incident.resolved_at.isnot(None),
            )
        ).scalar() or 0

        avg_resolution = session.execute(
            select(
                func.avg(
                    func.extract("epoch", Incident.resolved_at - Incident.created_at) / 3600
                )
            ).where(
                Incident.resolved_at >= last_week,
                Incident.resolved_at.isnot(None),
            )
        ).scalar()

        avg_hours = round(float(avg_resolution), 2) if avg_resolution else "N/A"

        # Get admin emails
        admins = session.execute(
            select(User.email).where(
                User.role.in_([UserRole.ADMIN, UserRole.INCIDENT_MANAGER, UserRole.TEAM_LEAD]),
                User.is_active == True,
            )
        ).scalars().all()

    # Build report
    report_date = datetime.utcnow().strftime("%Y-%m-%d")
    subject = f"Weekly Incident Summary - Week ending {report_date}"
    body = f"""
    <h2>Weekly Incident Summary</h2>
    <p><strong>Week ending:</strong> {report_date}</p>

    <table style="border-collapse:collapse; width:100%; max-width:400px;">
        <tr style="background:#f2f2f2;"><td style="padding:8px; border:1px solid #ddd;"><strong>Total Created</strong></td><td style="padding:8px; border:1px solid #ddd; text-align:center;">{total_created}</td></tr>
        <tr><td style="padding:8px; border:1px solid #ddd;"><strong>Total Resolved</strong></td><td style="padding:8px; border:1px solid #ddd; text-align:center;">{total_resolved}</td></tr>
        <tr style="background:#f2f2f2;"><td style="padding:8px; border:1px solid #ddd;"><strong>Avg Resolution Time</strong></td><td style="padding:8px; border:1px solid #ddd; text-align:center;">{avg_hours} hours</td></tr>
        <tr><td style="padding:8px; border:1px solid #ddd;"><strong>Resolution Rate</strong></td><td style="padding:8px; border:1px solid #ddd; text-align:center;">{round(total_resolved/total_created*100, 1) if total_created > 0 else 0}%</td></tr>
    </table>

    <p style="margin-top:20px; color:#666; font-size:12px;">This is an automated weekly report from the Incident Management System.</p>
    """

    from app.workers.email_tasks import send_email
    for email in admins:
        send_email.delay(email, subject, body)

    logger.info(f"Weekly report sent: created={total_created}, resolved={total_resolved}")
    return {
        "total_created": total_created,
        "total_resolved": total_resolved,
        "avg_resolution_hours": avg_hours,
        "recipients": len(admins),
    }
