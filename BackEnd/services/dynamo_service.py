from datetime import datetime, timezone
from services.database import get_db, ImageMetadata
import logging

logger = logging.getLogger(__name__)

def save_image_metadata(
    image_id: str,
    user_id: str,
    date_taken: str | None,
    gps_lat: float | None,
    gps_lon: float | None
) -> None:
    """
    Saves image metadata into the SQL database.
    """
    try:
        with get_db() as session:
            record = ImageMetadata(
                image_id=image_id,
                user_id=user_id,
                uploaded_at=datetime.now(timezone.utc).isoformat(),
                date_taken=date_taken,
                gps_lat=gps_lat,
                gps_lon=gps_lon,
            )
            session.merge(record)

    except Exception as e:
        logger.error(f"Database error while saving metadata for {image_id}: {e}")
        raise e
