import logging
import os
from datetime import datetime, timedelta
from sqlalchemy import create_engine, delete, select, func
from sqlalchemy.orm import Session
from app.workers.celery_app import celery_app

logger = logging.getLogger("cleanup_tasks")


def _get_sync_engine():
    """Get sync SQLAlchemy engine for Celery tasks."""
    db_url = os.getenv(
        "DATABASE_URL_SYNC",
        "postgresql://postgres:password@localhost:5432/incident_management",
    )
    return create_engine(db_url, pool_pre_ping=True)


@celery_app.task(name="app.workers.cleanup_tasks.cleanup_expired_tokens")
def cleanup_expired_tokens():
    """
    Remove expired and revoked refresh tokens from the database.
    Runs every hour via Celery Beat.
    """
    from app.models.user import RefreshToken

    engine = _get_sync_engine()

    with Session(engine) as session:
        # Delete expired tokens
        expired_result = session.execute(
            delete(RefreshToken).where(
                RefreshToken.expires_at < datetime.utcnow()
            )
        )
        expired_count = expired_result.rowcount

        # Delete revoked tokens older than 7 days
        old_revoked_result = session.execute(
            delete(RefreshToken).where(
                RefreshToken.is_revoked == True,
                RefreshToken.created_at < datetime.utcnow() - timedelta(days=7),
            )
        )
        revoked_count = old_revoked_result.rowcount

        session.commit()

    total = expired_count + revoked_count
    if total > 0:
        logger.info(f"Token cleanup: removed {expired_count} expired, {revoked_count} old revoked tokens.")
    return {"expired_removed": expired_count, "revoked_removed": revoked_count}


@celery_app.task(name="app.workers.cleanup_tasks.cleanup_old_notifications")
def cleanup_old_notifications():
    """
    Remove read notifications older than 30 days.
    Can be added to beat schedule if needed.
    """
    from app.models.notification import Notification

    engine = _get_sync_engine()
    cutoff = datetime.utcnow() - timedelta(days=30)

    with Session(engine) as session:
        result = session.execute(
            delete(Notification).where(
                Notification.is_read == True,
                Notification.created_at < cutoff,
            )
        )
        count = result.rowcount
        session.commit()

    if count > 0:
        logger.info(f"Notification cleanup: removed {count} old read notifications.")
    return {"removed": count}


@celery_app.task(name="app.workers.cleanup_tasks.cleanup_old_audit_logs")
def cleanup_old_audit_logs():
    """
    Archive/remove audit logs older than 90 days.
    Can be added to beat schedule if needed.
    """
    from app.models.audit import AuditLog

    engine = _get_sync_engine()
    cutoff = datetime.utcnow() - timedelta(days=90)

    with Session(engine) as session:
        # Count before delete (for logging)
        count = session.execute(
            select(func.count(AuditLog.id)).where(AuditLog.created_at < cutoff)
        ).scalar() or 0

        if count > 0:
            session.execute(
                delete(AuditLog).where(AuditLog.created_at < cutoff)
            )
            session.commit()
            logger.info(f"Audit log cleanup: removed {count} logs older than 90 days.")

    return {"removed": count}


@celery_app.task(name="app.workers.cleanup_tasks.db_health_check")
def db_health_check():
    """
    Simple database health check task.
    Useful for monitoring that workers can reach the DB.
    """
    from app.models.user import User

    engine = _get_sync_engine()

    try:
        with Session(engine) as session:
            user_count = session.execute(
                select(func.count(User.id))
            ).scalar()
        logger.info(f"DB health check OK: {user_count} users in system.")
        return {"status": "healthy", "user_count": user_count}
    except Exception as e:
        logger.error(f"DB health check FAILED: {e}")
        return {"status": "unhealthy", "error": str(e)}
