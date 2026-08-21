from uuid import UUID
from fastapi import APIRouter, Depends, UploadFile, File, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.database import get_db
from app.core.dependencies import get_current_user
from app.files.schemas import (
    FileUploadResponse,
    PresignedUrlResponse,
    AttachmentListResponse,
)
from app.files.services.file_service import FileService
from app.models.user import User

router = APIRouter(prefix="/files", tags=["File Storage"])


@router.post(
    "/upload/{incident_id}",
    response_model=FileUploadResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Upload a file attachment to an incident",
)
async def upload_file(
    incident_id: UUID,
    file: UploadFile = File(..., description="File to upload (max 10MB)"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    service = FileService(db)
    return await service.upload_file(file, incident_id, current_user)


@router.get(
    "/download/{attachment_id}",
    response_model=PresignedUrlResponse,
    summary="Get a presigned download URL for an attachment",
)
async def get_download_url(
    attachment_id: UUID,
    expires_in: int = Query(3600, ge=60, le=86400, description="URL expiry in seconds"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    service = FileService(db)
    return await service.get_download_url(attachment_id, expiration=expires_in)


@router.get(
    "/incident/{incident_id}",
    response_model=AttachmentListResponse,
    summary="List all attachments for an incident",
)
async def list_attachments(
    incident_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    service = FileService(db)
    return await service.list_attachments(incident_id)


@router.delete(
    "/{attachment_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete an attachment (uploader or admin only)",
)
async def delete_file(
    attachment_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    service = FileService(db)
    await service.delete_file(attachment_id, current_user)
