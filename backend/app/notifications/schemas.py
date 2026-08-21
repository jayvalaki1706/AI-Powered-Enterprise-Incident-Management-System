from pydantic import BaseModel, Field
from uuid import UUID
from datetime import datetime
from app.models.notification import NotificationType


# ─── Request Schemas ────────────────────────────────────────────────────────────

class NotificationCreate(BaseModel):
    user_id: UUID
    title: str = Field(..., min_length=1, max_length=255)
    message: str = Field(..., min_length=1, max_length=5000)
    type: NotificationType = NotificationType.IN_APP


class NotificationBroadcast(BaseModel):
    title: str = Field(..., min_length=1, max_length=255)
    message: str = Field(..., min_length=1, max_length=5000)
    type: NotificationType = NotificationType.IN_APP


# ─── Response Schemas ───────────────────────────────────────────────────────────

class NotificationResponse(BaseModel):
    id: UUID
    user_id: UUID
    title: str
    message: str
    type: NotificationType
    is_read: bool
    created_at: datetime

    class Config:
        from_attributes = True


class NotificationListResponse(BaseModel):
    items: list[NotificationResponse]
    total: int
    unread_count: int


class UnreadCountResponse(BaseModel):
    unread_count: int
