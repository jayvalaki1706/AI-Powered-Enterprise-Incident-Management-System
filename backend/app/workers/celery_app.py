from celery import Celery
from celery.schedules import crontab
from kombu import Exchange, Queue

# Use environment variable or fallback
import os
from dotenv import load_dotenv

load_dotenv()

RABBITMQ_URL = os.getenv("RABBITMQ_URL", "amqp://guest:guest@localhost:5672//")
REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379/0")

# ─── Celery App ─────────────────────────────────────────────────────────────────

celery_app = Celery(
    "incident_management",
    broker=RABBITMQ_URL,
    backend="redis://localhost:6379/1",  # Use DB 1 for results
)

# ─── Configuration ──────────────────────────────────────────────────────────────

celery_app.conf.update(
    # Serialization
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",

    # Timezone
    timezone="UTC",
    enable_utc=True,

    # Reliability
    task_track_started=True,
    task_acks_late=True,
    worker_prefetch_multiplier=1,

    # Result backend
    result_expires=3600,  # Results expire after 1 hour

    # Retry
    task_default_retry_delay=60,  # 1 minute between retries
    task_max_retries=3,

    # Queues for priority separation
    task_queues=(
        Queue("default", Exchange("default"), routing_key="default"),
        Queue("email", Exchange("email"), routing_key="email"),
        Queue("sla", Exchange("sla"), routing_key="sla"),
        Queue("reports", Exchange("reports"), routing_key="reports"),
        Queue("cleanup", Exchange("cleanup"), routing_key="cleanup"),
    ),
    task_default_queue="default",

    # Route tasks to specific queues
    task_routes={
        "app.workers.email_tasks.*": {"queue": "email"},
        "app.workers.sla_tasks.*": {"queue": "sla"},
        "app.workers.report_tasks.*": {"queue": "reports"},
        "app.workers.cleanup_tasks.*": {"queue": "cleanup"},
    },
)

# ─── Beat Schedule (Periodic Tasks) ────────────────────────────────────────────

celery_app.conf.beat_schedule = {
    # Check SLA breaches every 5 minutes
    "check-sla-breaches": {
        "task": "app.workers.sla_tasks.check_sla_breaches",
        "schedule": 300.0,
    },
    # Daily report at 8 AM UTC
    "daily-incident-report": {
        "task": "app.workers.report_tasks.generate_daily_report",
        "schedule": crontab(hour=8, minute=0),
    },
    # Cleanup expired tokens every hour
    "cleanup-expired-tokens": {
        "task": "app.workers.cleanup_tasks.cleanup_expired_tokens",
        "schedule": 3600.0,
    },
    # Weekly summary report on Monday at 9 AM UTC
    "weekly-summary-report": {
        "task": "app.workers.report_tasks.generate_weekly_report",
        "schedule": crontab(hour=9, minute=0, day_of_week=1),
    },
}

# ─── Autodiscover tasks ─────────────────────────────────────────────────────────

celery_app.autodiscover_tasks([
    "app.workers.email_tasks",
    "app.workers.notification_tasks",
    "app.workers.sla_tasks",
    "app.workers.report_tasks",
    "app.workers.cleanup_tasks",
])
