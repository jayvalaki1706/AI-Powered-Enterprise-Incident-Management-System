from pydantic import BaseModel, Field
from uuid import UUID
from datetime import datetime


# ─── Response Schemas ───────────────────────────────────────────────────────────

class FileUploadResponse(BaseModel):
    id: UUID
    incident_id: UUID
    file_name: str
    file_key: str
    file_size: int
    content_type: str
    uploaded_by: UUID
    created_at: datetime

    class Config:
        from_attributes = True


class PresignedUrlResponse(BaseModel):
    download_url: str
    file_name: str
    expires_in: int = Field(description="URL expiration time in seconds")


class AttachmentListResponse(BaseModel):
    items: list[FileUploadResponse]
    total: int


# ─── Constants ──────────────────────────────────────────────────────────────────

ALLOWED_CONTENT_TYPES = {
    # Images
    "image/jpeg",
    "image/png",
    "image/gif",
    "image/webp",
    # Documents
    "application/pdf",
    "text/plain",
    "text/csv",
    "application/json",
    # Logs
    "text/x-log",
    "application/octet-stream",
    # Archives
    "application/zip",
    "application/gzip",
}

MAX_FILE_SIZE = 10 * 1024 * 1024  # 10 MB
