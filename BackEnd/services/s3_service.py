import boto3
from botocore.exceptions import ClientError
from typing import Tuple
from config import get_settings
import uuid
import logging

logger = logging.getLogger(__name__)

# On ECS Fargate, credentials are provided automatically via the Task IAM Role.
# Do not use static credentials — boto3 picks them up from the instance metadata service.


def get_s3_client():
    settings = get_settings()
    return boto3.client('s3', region_name=settings.AWS_REGION)


def upload_file_to_s3(file_obj, original_filename: str, user_id: str, content_type: str = "image/jpeg") -> Tuple[str, str]:
    """
    Uploads a file object to S3 under uploads/{user_id}/{uuid}.{ext}.
    Returns the generated object key and a 15-minute presigned GET URL.
    """
    try:
        settings = get_settings()
        s3_client = get_s3_client()

        ext = original_filename.rsplit('.', 1)[-1].lower() if '.' in original_filename else 'jpg'
        unique_id = str(uuid.uuid4())
        file_key = f"uploads/{user_id}/{unique_id}.{ext}"

        s3_client.upload_fileobj(
            file_obj,
            settings.S3_BUCKET_NAME,
            file_key,
            ExtraArgs={'ContentType': content_type}
        )

        presigned_url = s3_client.generate_presigned_url(
            'get_object',
            Params={'Bucket': settings.S3_BUCKET_NAME, 'Key': file_key},
            ExpiresIn=900  # 15-minute TTL
        )

        return file_key, presigned_url
    except ClientError as e:
        logger.error(f"S3 Upload Error: {e}")
        raise


def generate_presigned_url(object_key: str, user_id: str, expires_in: int = 900) -> str:
    """
    Generates a presigned GET URL for reading an existing S3 object.

    Args:
        object_key: Exact S3 key of the object. Must start with 'uploads/{user_id}/'.
        user_id:    The authenticated user's ID. Used to enforce key prefix ownership.
        expires_in: TTL in seconds (default 900 = 15 minutes).

    Raises:
        ValueError: If object_key does not start with the expected user prefix.
                    This prevents a caller bug from accidentally exposing another user's object.
    """
    expected_prefix = f"uploads/{user_id}/"
    if not object_key.startswith(expected_prefix):
        raise ValueError(
            f"object_key '{object_key}' does not start with expected prefix '{expected_prefix}'. "
            "Cross-user presigned URL generation is not permitted."
        )

    try:
        settings = get_settings()
        s3_client = get_s3_client()
        return s3_client.generate_presigned_url(
            'get_object',
            Params={'Bucket': settings.S3_BUCKET_NAME, 'Key': object_key},
            ExpiresIn=expires_in
        )
    except ClientError as e:
        logger.error(f"S3 Presign Error: {e}")
        raise


def generate_presigned_put_url(object_key: str, user_id: str, content_type: str, expires_in: int = 900) -> str:
    """
    Generates a presigned PUT URL for a client to upload directly to S3.

    The key must be the exact destination key — never a wildcard or prefix.
    Enforces that the key belongs to the requesting user's uploads/ prefix.

    Args:
        object_key:   Exact S3 destination key, e.g. 'uploads/{user_id}/{uuid}.jpg'.
        user_id:      The authenticated user's ID. Enforces key prefix ownership.
        content_type: MIME type to embed in the presigned URL signature.
        expires_in:   TTL in seconds (default 900 = 15 minutes).

    Raises:
        ValueError: If object_key does not start with 'uploads/{user_id}/'.
    """
    expected_prefix = f"uploads/{user_id}/"
    if not object_key.startswith(expected_prefix):
        raise ValueError(
            f"object_key '{object_key}' does not start with expected prefix '{expected_prefix}'. "
            "Cross-user presigned PUT URL generation is not permitted."
        )

    try:
        settings = get_settings()
        s3_client = get_s3_client()
        return s3_client.generate_presigned_url(
            'put_object',
            Params={
                'Bucket': settings.S3_BUCKET_NAME,
                'Key': object_key,
                'ContentType': content_type,
            },
            ExpiresIn=expires_in
        )
    except ClientError as e:
        logger.error(f"S3 Presign PUT Error: {e}")
        raise
