from fastapi import APIRouter, File, UploadFile, Depends, HTTPException
from typing import Dict, Any
from auth.cognito import get_current_user
from services.s3_service import upload_file_to_s3
import io
import logging

logger = logging.getLogger(__name__)
router = APIRouter()

ALLOWED_CONTENT_TYPES = ["image/jpeg", "image/png", "image/heic"]

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
        
        # Upload directly to S3. Lambda (image_processor) will handle EXIF extraction and database writes via S3 events.
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
