from fastapi import APIRouter, File, UploadFile, Depends, HTTPException
from pydantic import BaseModel
from typing import Dict, Any, List
from auth.cognito import get_current_user
from services.s3_service import upload_file_to_s3, generate_presigned_put_url
from services.database import get_db, ImageMetadata
import io
import uuid
import logging
from datetime import datetime, timezone

logger = logging.getLogger(__name__)
router = APIRouter()

ALLOWED_CONTENT_TYPES = ["image/jpeg", "image/png", "image/heic"]
MAX_BATCH_SIZE = 500


# ─────────────────────────────────────────────────────────────
# Request / Response models for batch-presign
# ─────────────────────────────────────────────────────────────

class BatchFileRequest(BaseModel):
    filename: str
    content_type: str


class BatchPresignRequest(BaseModel):
    files: List[BatchFileRequest]


class BatchPresignItem(BaseModel):
    filename: str
    file_key: str
    presigned_url: str


class BatchPresignResponse(BaseModel):
    uploads: List[BatchPresignItem]


# ─────────────────────────────────────────────────────────────
# Original single-file upload endpoint (kept for backwards compatibility)
# ─────────────────────────────────────────────────────────────

@router.post("/upload")
async def upload_photo(
    file: UploadFile = File(...),
    user_id: str = Depends(get_current_user)
) -> Dict[str, Any]:

    if file.content_type not in ALLOWED_CONTENT_TYPES:
        raise HTTPException(status_code=400, detail="Invalid file type.")

    try:
        file_bytes = await file.read()
        file_obj = io.BytesIO(file_bytes)

        # Upload directly to S3. Lambda (image_processor) will handle EXIF extraction
        # and database writes via the S3 → SNS → SQS → Lambda event chain.
        file_key, presigned_url = upload_file_to_s3(
            file_obj=file_obj,
            original_filename=file.filename or 'upload.jpg',
            user_id=user_id,
            content_type=file.content_type
        )

        return {
            "file_key": file_key,
            "presigned_url": presigned_url,
            "message": "Upload successful. Background processing initiated."
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Upload failed: {e}")
        raise HTTPException(status_code=500, detail="Failed to upload file")


# ─────────────────────────────────────────────────────────────
# Bulk presigned URL endpoint
# Accepts up to 500 files, returns presigned S3 PUT URLs so the
# client can upload directly to S3 without routing through the API server.
# ─────────────────────────────────────────────────────────────

@router.post("/upload/batch-presign", response_model=BatchPresignResponse)
async def batch_presign(
    request: BatchPresignRequest,
    user_id: str = Depends(get_current_user)
) -> BatchPresignResponse:
    """
    Generates presigned S3 PUT URLs for a batch of files.

    - Validates each file's content_type is JPEG, PNG, or HEIC.
    - Caps the batch at 500 files (HTTP 400 if exceeded).
    - Each URL is scoped to uploads/{user_id}/{uuid}.{ext} with a 15-minute TTL.
    - Writes one image_metadata row per file with status='pending' so the database
      reflects the upload intent before S3 processing begins.
    """
    if len(request.files) > MAX_BATCH_SIZE:
        raise HTTPException(
            status_code=400,
            detail=f"Batch size {len(request.files)} exceeds the maximum of {MAX_BATCH_SIZE} files."
        )

    invalid = [f.filename for f in request.files if f.content_type not in ALLOWED_CONTENT_TYPES]
    if invalid:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid content_type for files: {', '.join(invalid)}. Allowed: {ALLOWED_CONTENT_TYPES}"
        )

    try:
        uploads: List[BatchPresignItem] = []
        now = datetime.now(timezone.utc).isoformat()
        
        from services.s3_service import get_s3_client
        s3_client = get_s3_client()

        with get_db() as session:
            for file_req in request.files:
                ext = file_req.filename.rsplit('.', 1)[-1].lower() if '.' in file_req.filename else 'jpg'
                unique_id = str(uuid.uuid4())
                file_key = f"uploads/{user_id}/{unique_id}.{ext}"

                # Generate a presigned PUT URL (15-minute TTL, scoped to exact key)
                presigned_url = generate_presigned_put_url(
                    object_key=file_key,
                    user_id=user_id,
                    content_type=file_req.content_type,
                    s3_client=s3_client
                )

                # Write a pending metadata row so the DB reflects the upload intent
                session.add(ImageMetadata(
                    image_id=file_key,
                    user_id=user_id,
                    uploaded_at=now,
                    status='pending'
                ))

                uploads.append(BatchPresignItem(
                    filename=file_req.filename,
                    file_key=file_key,
                    presigned_url=presigned_url
                ))

        return BatchPresignResponse(uploads=uploads)

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Batch presign failed: {e}")
        raise HTTPException(status_code=500, detail="Failed to generate presigned URLs")
