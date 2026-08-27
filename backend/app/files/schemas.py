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
    # Microsoft Office
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document",  # .docx
    "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",  # .xlsx
    "application/vnd.openxmlformats-officedocument.presentationml.presentation",  # .pptx
    "application/msword",  # .doc
    "application/vnd.ms-excel",  # .xls
    "application/vnd.ms-powerpoint",  # .ppt
    # Logs
    "text/x-log",
    "application/octet-stream",
    # Archives
    "application/zip",
    "application/gzip",
}

MAX_FILE_SIZE = 10 * 1024 * 1024  # 10 MB
