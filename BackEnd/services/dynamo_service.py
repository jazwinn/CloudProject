import boto3
from botocore.exceptions import ClientError
from config import get_settings
from datetime import datetime, timezone
from decimal import Decimal
import logging

logger = logging.getLogger(__name__)

def get_dynamodb_resource():
    settings = get_settings()
    return boto3.resource(
        'dynamodb',
        aws_access_key_id=settings.AWS_ACCESS_KEY_ID,
        aws_secret_access_key=settings.AWS_SECRET_ACCESS_KEY,
        aws_session_token=settings.AWS_SESSION_TOKEN,
        region_name=settings.AWS_REGION
    )

def save_image_metadata(
    image_id: str, 
    user_id: str, 
    date_taken: str | None, 
    gps_lat: float | None, 
    gps_lon: float | None
) -> None:
    """
    Saves image metadata into DynamoDB using a boto3 resource.
    Omits keys that are None to conform with standard NoSQL practices.
    """
    settings = get_settings()
    
    try:
        dynamodb = get_dynamodb_resource()
        table = dynamodb.Table(settings.DYNAMO_TABLE_NAME)
        
        # Build the baseline item metadata
        item = {
            "image_id": image_id,
            "user_id": user_id,
            "uploaded_at": datetime.now(timezone.utc).isoformat()
        }
        
        # Append conditionally based on EXIF availability
        if date_taken is not None:
            item["date_taken"] = date_taken
        if gps_lat is not None:
            # DynamoDB requires python Floats to be wrapped in Decimal
            item["gps_lat"] = Decimal(str(gps_lat))
        if gps_lon is not None:
            item["gps_lon"] = Decimal(str(gps_lon))
            
        table.put_item(Item=item)
        
    except ClientError as e:
        logger.error(f"DynamoDB Error while saving metadata for {image_id}: {e}")
        raise e
