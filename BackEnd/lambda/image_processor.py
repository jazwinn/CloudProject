import os
import json
import boto3
import logging
from urllib.parse import unquote_plus
import sys
import io

# Support HEIC decoding in Pillow
from pillow_heif import register_heif_opener
register_heif_opener()

from PIL import Image

# Deploy with reserved concurrency = 10 to prevent runaway DBSCAN jobs
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from services.exif_service import extract_exif_metadata
from services.metadata_service import save_image_metadata
from services.database import get_db, ImageMetadata

logger = logging.getLogger()
logger.setLevel(logging.INFO)

s3_client = boto3.client('s3')

def _extract_s3_event(record: dict) -> tuple[str | None, str | None]:
    try:
        sqs_body = json.loads(record['body'])
        if 'Message' in sqs_body:
            sns_message = json.loads(sqs_body['Message'])
        else:
            sns_message = sqs_body

        s3_records = sns_message.get('Records', [])
        if not s3_records or 's3' not in s3_records[0]:
            return None, None

        bucket = s3_records[0]['s3']['bucket']['name']
        key = unquote_plus(s3_records[0]['s3']['object']['key'])
        return bucket, key

    except Exception as e:
        logger.warning(f"Failed to parse SQS record body: {e}")
        return None, None

def lambda_handler(event: dict, context) -> dict:
    """"
    Combined Lambda Worker for Thumbnail generation & EXIF extraction.
    """
    logger.info(f"Processing SQS batch of {len(event.get('Records', []))} records.")
    batch_item_failures = []

    for record in event.get('Records', []):
        message_id = record.get('messageId', 'unknown')
        bucket, key = _extract_s3_event(record)

        if not bucket or not key or not key.startswith('uploads/'):
            continue

        try:
            logger.info(f"Processing image: {key}")
            response = s3_client.get_object(Bucket=bucket, Key=key)
            image_content = response['Body'].read()

            parts = key.split('/')
            user_id = parts[1] if len(parts) >= 2 else 'unknown'
            filename = parts[-1]
            thumb_key = f"thumbnails/{user_id}/{filename}"

            # 1. Generate and upload Thumbnail
            with Image.open(io.BytesIO(image_content)) as img:
                if img.mode in ('RGBA', 'P'):
                    img = img.convert('RGB')
                img.thumbnail((300, 300), getattr(Image, 'Resampling', Image).LANCZOS)
                thumb = Image.new('RGB', (300, 300), (0, 0, 0))
                x = (300 - img.width) // 2
                y = (300 - img.height) // 2
                thumb.paste(img, (x, y))

                buffer = io.BytesIO()
                thumb.save(buffer, format="JPEG")
                buffer.seek(0)
                
                # Upload thumbnail
                s3_client.upload_fileobj(
                    buffer,
                    bucket,
                    thumb_key,
                    ExtraArgs={'ContentType': 'image/jpeg'}
                )
                logger.info(f"Uploaded thumbnail: {thumb_key}")

            # 2. Extract EXIF and save to DB
            metadata = extract_exif_metadata(image_content)
            save_image_metadata(
                image_id=key,
                user_id=user_id,
                date_taken=metadata.get('date_taken'),
                gps_lat=metadata.get('gps_lat'),
                gps_lon=metadata.get('gps_lon')
            )

            # Update status and thumbnail_key
            with get_db() as session:
                row = session.query(ImageMetadata).filter(
                    ImageMetadata.image_id == key
                ).first()
                if row:
                    row.status = 'processed'
                    row.thumbnail_key = thumb_key

            logger.info(f"Successfully processed: {key}")

        except Exception as e:
            logger.error(f"Failed to process record messageId={message_id} key={key}: {e}")
            batch_item_failures.append({"itemIdentifier": message_id})

    return {"batchItemFailures": batch_item_failures}
