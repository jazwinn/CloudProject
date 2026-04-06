from fastapi import APIRouter, Depends, HTTPException
from typing import Dict, Any
from auth.cognito import get_current_user
from services.s3_service import generate_presigned_url
from services.database import get_db, ImageMetadata
import logging

logger = logging.getLogger(__name__)

router = APIRouter()


@router.get("/image/{image_id:path}")
def get_image_url(
    image_id: str,
    user_id: str = Depends(get_current_user)
) -> Dict[str, Any]:

    with get_db() as db:
        record = db.query(ImageMetadata).filter(
            ImageMetadata.image_id == image_id
        ).first()

        if not record:
            raise HTTPException(status_code=404, detail="Image not found")

        if record.user_id != user_id:
            raise HTTPException(status_code=403, detail="Access denied")

    # session can safely close AFTER we extracted what we need

    try:
        presigned_url = generate_presigned_url(image_id)
        return {"presigned_url": presigned_url}
    except Exception as e:
        logger.error(f"Failed to generate presigned URL for {image_id}: {e}")
        raise HTTPException(status_code=500, detail="Failed to generate image URL")
