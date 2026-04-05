import os
import sys
import json
import boto3
import logging
from PIL import Image
import io
from urllib.parse import unquote_plus

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from services.database import get_db, ImageMetadata

logger = logging.getLogger()
logger.setLevel(logging.INFO)

s3_client = boto3.client('s3')


def _extract_s3_event(record: dict) -> tuple[str | None, str | None]:
    """
    Parses an individual SQS record to extract the S3 bucket and key.
    """
    try:
        sqs_body = json.loads(record['body'])

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
    SQS-triggered Lambda that generates 300×300 JPEG thumbnails for uploaded images,
    stores them under thumbnails/{user_id}/{filename} in S3, and updates thumbnail_key
    in the image_metadata PostgreSQL table.
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
            logger.info(f"Generating thumbnail for: {key}")

            response = s3_client.get_object(Bucket=bucket, Key=key)
            image_content = response['Body'].read()

            with Image.open(io.BytesIO(image_content)) as img:
                if img.mode in ('RGBA', 'P'):
                    img = img.convert('RGB')

                # Resize to fit within 300×300, preserving aspect ratio
                img.thumbnail((300, 300), getattr(Image, 'Resampling', Image).LANCZOS)

                # Centre on a black 300×300 canvas for consistent dimensions
                thumb = Image.new('RGB', (300, 300), (0, 0, 0))
                x = (300 - img.width) // 2
                y = (300 - img.height) // 2
                thumb.paste(img, (x, y))

                buffer = io.BytesIO()
                thumb.save(buffer, format="JPEG")
                buffer.seek(0)

                parts = key.split('/')
                user_id = parts[1] if len(parts) >= 2 else 'unknown'
                filename = parts[-1]
                thumb_key = f"thumbnails/{user_id}/{filename}"

                s3_client.upload_fileobj(
                    buffer,
                    bucket,
                    thumb_key,
                    ExtraArgs={'ContentType': 'image/jpeg'}
                )

                logger.info(f"Uploaded thumbnail: {thumb_key}")

                with get_db() as session:
                    db_record = session.query(ImageMetadata).filter(
                        ImageMetadata.image_id == key
                    ).first()
                    if db_record:
                        db_record.thumbnail_key = thumb_key

        except Exception as e:
            # Log the error but continue processing remaining records in the batch.
            # Report this record as a failure so Lambda retries only this item.
            logger.error(f"Failed to generate thumbnail for messageId={message_id} key={key}: {e}")
            batch_item_failures.append({"itemIdentifier": message_id})

    return {"batchItemFailures": batch_item_failures}
