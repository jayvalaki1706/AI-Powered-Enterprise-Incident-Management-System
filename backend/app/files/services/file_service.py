import uuid
import logging
from fastapi import UploadFile, HTTPException, status
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession
import boto3
from botocore.exceptions import ClientError

from app.core.config import get_settings
from app.models.attachment import Attachment
from app.models.user import User
from app.files.schemas import ALLOWED_CONTENT_TYPES, MAX_FILE_SIZE, AttachmentListResponse

settings = get_settings()
logger = logging.getLogger("file_service")

# Singleton S3 client
_s3_client = None


def get_s3_client():
    """Get or create S3 client singleton."""
    global _s3_client
    if _s3_client is None:
        _s3_client = boto3.client(
            "s3",
            aws_access_key_id=settings.AWS_ACCESS_KEY_ID,
            aws_secret_access_key=settings.AWS_SECRET_ACCESS_KEY,
            region_name=settings.AWS_REGION,
        )
    return _s3_client


class FileService:
    """Service for file upload/download operations with S3."""

    def __init__(self, db: AsyncSession):
        self.db = db
        self.s3 = get_s3_client()
        self.bucket = settings.S3_BUCKET_NAME

    # ─── Upload ─────────────────────────────────────────────────────────────────

    async def upload_file(
        self,
        file: UploadFile,
        incident_id: uuid.UUID,
        current_user: User,
    ) -> Attachment:
        """Upload a file to S3 and save metadata to DB."""
        # Validate content type
        content_type = file.content_type or "application/octet-stream"
        if content_type not in ALLOWED_CONTENT_TYPES:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"File type '{content_type}' not allowed. Allowed: {', '.join(sorted(ALLOWED_CONTENT_TYPES))}",
            )

        # Read and validate file size
        content = await file.read()
        if len(content) > MAX_FILE_SIZE:
            raise HTTPException(
                status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
                detail=f"File too large. Maximum size: {MAX_FILE_SIZE // (1024*1024)}MB",
            )

        if len(content) == 0:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="File is empty",
            )

        # Generate unique S3 key
        file_ext = file.filename.rsplit(".", 1)[-1] if "." in file.filename else "bin"
        file_key = f"incidents/{incident_id}/{uuid.uuid4()}.{file_ext}"

        # Upload to S3
        try:
            self.s3.put_object(
                Bucket=self.bucket,
                Key=file_key,
                Body=content,
                ContentType=content_type,
                Metadata={
                    "original_filename": file.filename,
                    "uploaded_by": str(current_user.id),
                    "incident_id": str(incident_id),
                },
            )
        except ClientError as e:
            logger.error(f"S3 upload failed: {e}")
            raise HTTPException(
                status_code=status.HTTP_502_BAD_GATEWAY,
                detail="File upload failed. Please try again.",
            )

        # Save metadata to DB
        attachment = Attachment(
            incident_id=incident_id,
            uploaded_by=current_user.id,
            file_name=file.filename,
            file_key=file_key,
            file_size=len(content),
            content_type=content_type,
        )
        self.db.add(attachment)
        await self.db.flush()
        await self.db.refresh(attachment)

        return attachment

    # ─── Download (Presigned URL) ───────────────────────────────────────────────

    async def get_download_url(
        self,
        attachment_id: uuid.UUID,
        expiration: int = 3600,
    ) -> dict:
        """Generate a presigned download URL for an attachment."""
        attachment = await self._get_attachment(attachment_id)

        try:
            url = self.s3.generate_presigned_url(
                "get_object",
                Params={
                    "Bucket": self.bucket,
                    "Key": attachment.file_key,
                    "ResponseContentDisposition": f'attachment; filename="{attachment.file_name}"',
                },
                ExpiresIn=expiration,
            )
        except ClientError as e:
            logger.error(f"S3 presigned URL generation failed: {e}")
            raise HTTPException(
                status_code=status.HTTP_502_BAD_GATEWAY,
                detail="Could not generate download URL.",
            )

        return {
            "download_url": url,
            "file_name": attachment.file_name,
            "expires_in": expiration,
        }

    # ─── List Attachments ───────────────────────────────────────────────────────

    async def list_attachments(self, incident_id: uuid.UUID) -> AttachmentListResponse:
        """List all attachments for an incident."""
        result = await self.db.execute(
            select(Attachment)
            .where(Attachment.incident_id == incident_id)
            .order_by(Attachment.created_at.desc())
        )
        items = result.scalars().all()

        count_result = await self.db.execute(
            select(func.count(Attachment.id)).where(Attachment.incident_id == incident_id)
        )
        total = count_result.scalar()

        return AttachmentListResponse(items=items, total=total)

    # ─── Delete ─────────────────────────────────────────────────────────────────

    async def delete_file(
        self,
        attachment_id: uuid.UUID,
        current_user: User,
    ) -> None:
        """Delete a file from S3 and remove metadata from DB."""
        attachment = await self._get_attachment(attachment_id)

        # Only uploader or admin can delete
        if attachment.uploaded_by != current_user.id and current_user.role.value != "ADMIN":
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Only the uploader or an admin can delete this file",
            )

        # Delete from S3
        try:
            self.s3.delete_object(Bucket=self.bucket, Key=attachment.file_key)
        except ClientError as e:
            logger.error(f"S3 delete failed: {e}")
            # Continue with DB deletion even if S3 fails

        # Delete from DB
        await self.db.delete(attachment)
        await self.db.flush()

    # ─── Private Helpers ────────────────────────────────────────────────────────

    async def _get_attachment(self, attachment_id: uuid.UUID) -> Attachment:
        """Get attachment or raise 404."""
        result = await self.db.execute(
            select(Attachment).where(Attachment.id == attachment_id)
        )
        attachment = result.scalar_one_or_none()
        if not attachment:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Attachment not found",
            )
        return attachment
