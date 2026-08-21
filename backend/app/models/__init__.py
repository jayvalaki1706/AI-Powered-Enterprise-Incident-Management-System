"""
Import all models here so Alembic and SQLAlchemy can discover them.
"""
from app.models.attachment import Department, Project, Team, Attachment
from app.models.user import User, RefreshToken
from app.models.incident import Incident, IncidentComment, IncidentHistory
from app.models.notification import Notification
from app.models.audit import AuditLog
