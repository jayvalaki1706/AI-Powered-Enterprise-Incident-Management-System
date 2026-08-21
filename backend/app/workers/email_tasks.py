import logging
import os
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

from app.workers.celery_app import celery_app

logger = logging.getLogger("email_tasks")


# ─── Helper Function ────────────────────────────────────────────────────────────


def send_notification_email(to_email: str, subject: str, body_html: str) -> bool:
    """
    Send an email using Python's smtplib (synchronous, Celery-compatible).

    Reads configuration from environment variables:
      - MAIL_SERVER (default: smtp.gmail.com)
      - MAIL_PORT (default: 587)
      - MAIL_USERNAME
      - MAIL_PASSWORD
      - MAIL_FROM (default: noreply@incidentmgmt.com)

    Falls back gracefully if email is not configured — just logs the notification.
    Returns True if sent successfully, False otherwise.
    """
    mail_server = os.getenv("MAIL_SERVER", "smtp.gmail.com")
    mail_port = int(os.getenv("MAIL_PORT", "587"))
    mail_username = os.getenv("MAIL_USERNAME", "")
    mail_password = os.getenv("MAIL_PASSWORD", "")
    mail_from = os.getenv("MAIL_FROM", "noreply@incidentmgmt.com")

    # If credentials are not configured, log and return gracefully
    if not mail_username or not mail_password:
        logger.warning(
            f"Email not configured. Would have sent to={to_email} subject='{subject}'"
        )
        logger.info(f"Email body (not sent): {body_html[:200]}...")
        return False

    try:
        # Build MIME message
        msg = MIMEMultipart("alternative")
        msg["From"] = mail_from
        msg["To"] = to_email
        msg["Subject"] = subject
        msg.attach(MIMEText(body_html, "html"))

        # Connect and send via TLS
        server = smtplib.SMTP(mail_server, mail_port)
        server.ehlo()
        server.starttls()
        server.ehlo()
        server.login(mail_username, mail_password)
        server.sendmail(mail_from, to_email, msg.as_string())
        server.quit()

        logger.info(f"Email sent successfully to {to_email}: {subject}")
        return True

    except Exception as e:
        logger.error(f"Failed to send email to {to_email}: {e}")
        return False


# ─── Celery Tasks ───────────────────────────────────────────────────────────────


@celery_app.task(
    name="app.workers.email_tasks.send_notification_email_task",
    bind=True,
    max_retries=3,
    default_retry_delay=60,
)
def send_notification_email_task(self, to_email: str, subject: str, body_html: str):
    """
    Celery task to send a notification email.
    Retries up to 3 times on failure.
    """
    try:
        success = send_notification_email(to_email, subject, body_html)
        if not success:
            # If email is not configured, don't retry — it's intentional
            mail_username = os.getenv("MAIL_USERNAME", "")
            if not mail_username:
                logger.info("Email not configured — skipping retry.")
                return
            raise RuntimeError(f"Email send to {to_email} returned failure")
    except Exception as e:
        logger.error(f"Email task failed for {to_email}: {e}")
        raise self.retry(exc=e)


@celery_app.task(name="app.workers.email_tasks.send_incident_created")
def send_incident_created(to_email: str, incident_title: str, incident_id: str, priority: str):
    """Notify about a new incident."""
    subject = f"[{priority.upper()}] New Incident: {incident_title}"
    body = f"""
    <h2>New Incident Created</h2>
    <table style="border-collapse:collapse; margin:10px 0;">
        <tr><td style="padding:5px 15px 5px 0;"><strong>Title:</strong></td><td>{incident_title}</td></tr>
        <tr><td style="padding:5px 15px 5px 0;"><strong>Priority:</strong></td><td>{priority.upper()}</td></tr>
        <tr><td style="padding:5px 15px 5px 0;"><strong>ID:</strong></td><td>{incident_id}</td></tr>
    </table>
    <p>Please review and take action at your earliest convenience.</p>
    """
    send_notification_email_task.delay(to_email, subject, body)


@celery_app.task(name="app.workers.email_tasks.send_incident_assigned")
def send_incident_assigned(to_email: str, incident_title: str, incident_id: str, assigned_by: str):
    """Notify engineer about incident assignment."""
    subject = f"Incident Assigned: {incident_title}"
    body = f"""
    <h2>Incident Assigned to You</h2>
    <table style="border-collapse:collapse; margin:10px 0;">
        <tr><td style="padding:5px 15px 5px 0;"><strong>Title:</strong></td><td>{incident_title}</td></tr>
        <tr><td style="padding:5px 15px 5px 0;"><strong>Assigned By:</strong></td><td>{assigned_by}</td></tr>
        <tr><td style="padding:5px 15px 5px 0;"><strong>ID:</strong></td><td>{incident_id}</td></tr>
    </table>
    <p>Please begin investigation immediately.</p>
    """
    send_notification_email_task.delay(to_email, subject, body)


@celery_app.task(name="app.workers.email_tasks.send_incident_resolved")
def send_incident_resolved(to_email: str, incident_title: str, incident_id: str):
    """Notify about incident resolution."""
    subject = f"Incident Resolved: {incident_title}"
    body = f"""
    <h2>Incident Resolved</h2>
    <p>The following incident has been marked as resolved:</p>
    <table style="border-collapse:collapse; margin:10px 0;">
        <tr><td style="padding:5px 15px 5px 0;"><strong>Title:</strong></td><td>{incident_title}</td></tr>
        <tr><td style="padding:5px 15px 5px 0;"><strong>ID:</strong></td><td>{incident_id}</td></tr>
    </table>
    """
    send_notification_email_task.delay(to_email, subject, body)


@celery_app.task(name="app.workers.email_tasks.send_sla_breach_alert")
def send_sla_breach_alert(to_email: str, incident_title: str, incident_id: str, escalation_level: int):
    """Alert about SLA breach and escalation."""
    subject = f"⚠️ SLA BREACH: {incident_title} (Level {escalation_level})"
    body = f"""
    <h2 style="color:red;">SLA Breach Alert</h2>
    <p>The following incident has breached its SLA deadline:</p>
    <table style="border-collapse:collapse; margin:10px 0;">
        <tr><td style="padding:5px 15px 5px 0;"><strong>Title:</strong></td><td>{incident_title}</td></tr>
        <tr><td style="padding:5px 15px 5px 0;"><strong>ID:</strong></td><td>{incident_id}</td></tr>
        <tr><td style="padding:5px 15px 5px 0;"><strong>Escalation Level:</strong></td><td>{escalation_level}</td></tr>
    </table>
    <p><strong>Immediate action required.</strong></p>
    """
    send_notification_email_task.delay(to_email, subject, body)
