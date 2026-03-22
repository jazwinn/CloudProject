import boto3
from botocore.exceptions import ClientError
from typing import Tuple
from config import get_settings
import uuid
import logging

logger = logging.getLogger(__name__)

def get_s3_client():
    settings = get_settings()
    return boto3.client(
        's3',
        aws_access_key_id=settings.AWS_ACCESS_KEY_ID,
        aws_secret_access_key=settings.AWS_SECRET_ACCESS_KEY,
        region_name=settings.AWS_REGION
    )

def upload_file_to_s3(file_obj, original_filename: str, user_id: str, content_type: str = "image/jpeg") -> Tuple[str, str]:
    """
    Uploads a file object to S3 and returns the generated object key and a 1-hour presigned URL.
    The file is stored under uploads/{user_id}/{uuid}.{ext}.
    """
    try:
        settings = get_settings()
        s3_client = get_s3_client()
        
        # Generate a unique key for the file
        ext = original_filename.split('.')[-1] if '.' in original_filename else 'jpg'
        unique_id = str(uuid.uuid4())
        file_key = f"uploads/{user_id}/{unique_id}.{ext}"
        
        # Upload the file object mapped to the given content_type
        s3_client.upload_fileobj(
            file_obj,
            settings.S3_BUCKET_NAME,
            file_key,
            ExtraArgs={'ContentType': content_type}
        )
        
        # Generate a 1-hour presigned URL to return
        presigned_url = s3_client.generate_presigned_url(
            'get_object',
            Params={'Bucket': settings.S3_BUCKET_NAME, 'Key': file_key},
            ExpiresIn=3600
        )
        
        return file_key, presigned_url
    except ClientError as e:
        logger.error(f"S3 Upload Error: {e}")
        raise e
