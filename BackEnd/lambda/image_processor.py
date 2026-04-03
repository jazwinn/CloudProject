import os
import json
import boto3
import logging
from urllib.parse import unquote_plus
import sys
from datetime import datetime, timezone

# Deploy with reserved concurrency = 10 to prevent runaway DBSCAN jobs
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from services.exif_service import extract_exif_metadata
from services.dynamo_service import save_image_metadata
from services.database import get_db, ImageMetadata

logger = logging.getLogger()
logger.setLevel(logging.INFO)

s3_client = boto3.client('s3')


def _extract_s3_event(record: dict) -> tuple[str | None, str | None]:
    """
    Parses an individual SQS record to extract the S3 bucket and key.

    SQS wraps the original SNS notification which itself wraps the S3 event:
      SQS record → body (str) → SNS Message (str) → S3 Records[0]

    Returns (bucket, key) or (None, None) if the event cannot be parsed.
    """
    try:
        sqs_body = json.loads(record['body'])

        # SNS wraps its payload in a "Message" field as a JSON string
        if 'Message' in sqs_body:
            sns_message = json.loads(sqs_body['Message'])
        else:
            sns_message = sqs_body

        s3_records = sns_message.get('Records', [])
        if not s3_records or 's3' not in s3_records[0]:
            logger.warning("No S3 records found in SQS message body.")
            return None, None

        bucket = s3_records[0]['s3']['bucket']['name']
        key = unquote_plus(s3_records[0]['s3']['object']['key'])
        return bucket, key

    except (KeyError, ValueError, json.JSONDecodeError) as e:
        logger.warning(f"Failed to parse SQS record body: {e} | record={record}")
        return None, None


def lambda_handler(event: dict, context) -> dict:
    """
    SQS-triggered Lambda that extracts EXIF metadata from uploaded images
    and writes the result to the image_metadata PostgreSQL table.

    Processes records in batches (BatchSize=10 configured on the event source mapping).
    Each record is wrapped in individual try/except so one bad image never aborts
    the full batch. Failed record IDs are reported via BatchItemFailures so Lambda
    only retries those records, not the entire batch.

    Event source: SQS ← SNS ← S3 ObjectCreated (uploads/)
    """
    logger.info(f"Processing SQS batch of {len(event.get('Records', []))} records.")

    batch_item_failures: list[dict] = []

    for record in event.get('Records', []):
        message_id = record.get('messageId', 'unknown')
        bucket, key = _extract_s3_event(record)

        if not bucket or not key:
            logger.warning(f"Skipping unrecognized record structure: messageId={message_id}")
            continue

        if not key.startswith('uploads/'):
            logger.info(f"Skipping non-upload key: {key}")
            continue

        try:
            logger.info(f"Extracting EXIF for: {key}")

            response = s3_client.get_object(Bucket=bucket, Key=key)
            image_content = response['Body'].read()

            metadata = extract_exif_metadata(image_content)

            # Key format: uploads/{user_id}/{uuid}.ext
            parts = key.split('/')
            user_id = parts[1] if len(parts) >= 2 else 'unknown'

            save_image_metadata(
                image_id=key,
                user_id=user_id,
                date_taken=metadata.get('date_taken'),
                gps_lat=metadata.get('gps_lat'),
                gps_lon=metadata.get('gps_lon')
            )

            # Update the status column from 'pending' → 'processed'
            # (set during batch-presign; marks that EXIF extraction succeeded)
            with get_db() as session:
                row = session.query(ImageMetadata).filter(
                    ImageMetadata.image_id == key
                ).first()
                if row:
                    row.status = 'processed'

            logger.info(f"Successfully processed: {key}")

        except Exception as e:
            # Log the error but continue processing remaining records in the batch.
            # Report this record as a failure so Lambda retries only this item.
            logger.error(f"Failed to process record messageId={message_id} key={key}: {e}")
            batch_item_failures.append({"itemIdentifier": message_id})

    return {"batchItemFailures": batch_item_failures}
