from fastapi import APIRouter, Depends, HTTPException
from typing import Dict, Any
from auth.cognito import get_current_user
from services.s3_service import generate_presigned_url
import logging

logger = logging.getLogger(__name__)

router = APIRouter()


@router.get("/image/{image_id:path}")
def get_image_url(
    image_id: str,
    user_id: str = Depends(get_current_user)
) -> Dict[str, Any]:
    """
    Returns a fresh presigned S3 URL for the given image key.
    The image_id must belong to the requesting user.
    """
    parts = image_id.split('/')
    if len(parts) < 2 or parts[1] != user_id:
        raise HTTPException(status_code=403, detail="Access denied")

    try:
        presigned_url = generate_presigned_url(image_id)
        return {"presigned_url": presigned_url}
    except Exception as e:
        logger.error(f"Failed to generate presigned URL for {image_id}: {e}")
        raise HTTPException(status_code=500, detail="Failed to generate image URL")
