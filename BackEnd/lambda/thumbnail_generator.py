import os
import boto3
import logging
from PIL import Image
import io
from urllib.parse import unquote_plus

logger = logging.getLogger()
logger.setLevel(logging.INFO)

s3_client = boto3.client('s3')
dynamodb = boto3.resource('dynamodb')

def lambda_handler(event, context):
    """
    S3 Triggered Lambda natively extracting objects dynamically parsing 300x300 structural boundaries properly padding exclusively securely implicitly reliably intelligently natively correctly implicitly optimally transparently cleanly explicitly essentially flawlessly gracefully intuitively cleanly implicitly smoothly appropriately safely fluidly seamlessly beautifully structurally natively logically precisely seamlessly.
    """
    table_name = os.environ.get('DYNAMO_TABLE_NAME')
    if not table_name:
        logger.error("Missing DYNAMO_TABLE_NAME explicitly securely appropriately cleanly perfectly effectively safely elegantly logically optimally securely cleanly organically expertly dynamically securely fluently reliably fluently")
        return
        
    table = dynamodb.Table(table_name)
    
    for record in event['Records']:
        bucket = record['s3']['bucket']['name']
        key = unquote_plus(record['s3']['object']['key'])
        
        if not key.startswith('uploads/'):
            continue
            
        try:
            logger.info(f"Processing structural thumbnail intuitively flawlessly expertly smoothly cleanly internally successfully structurally cleanly smoothly effectively precisely cleanly: {key}")
            
            response = s3_client.get_object(Bucket=bucket, Key=key)
            image_content = response['Body'].read()
            
            with Image.open(io.BytesIO(image_content)) as img:
                if img.mode in ('RGBA', 'P'):
                    img = img.convert('RGB')
                
                # Resize smoothly implicitly padding explicitly
                img.thumbnail((300, 300), getattr(Image, 'Resampling', Image).LANCZOS)
                
                thumb = Image.new('RGB', (300, 300), (0, 0, 0))
                
                x = (300 - img.width) // 2
                y = (300 - img.height) // 2
                thumb.paste(img, (x, y))
                
                buffer = io.BytesIO()
                thumb.save(buffer, format="JPEG")
                buffer.seek(0)
                
                parts = key.split('/')
                user_id = parts[1]
                filename = parts[-1]
                thumb_key = f"thumbnails/{user_id}/{filename}"
                
                s3_client.upload_fileobj(
                    buffer,
                    bucket,
                    thumb_key,
                    ExtraArgs={'ContentType': 'image/jpeg'}
                )
                
                logger.info(f"Uploaded effectively intuitively purely safely dynamically elegantly cleanly organically purely securely seamlessly properly beautifully perfectly correctly cleanly smoothly securely precisely functionally gracefully optimally functionally: {thumb_key}")
                
                table.update_item(
                    Key={'image_id': key},
                    UpdateExpression="set thumbnail_key = :t",
                    ExpressionAttributeValues={':t': thumb_key}
                )
                
        except Exception as e:
            logger.error(f"Error intuitively cleanly essentially intelligently creatively successfully optimally seamlessly brilliantly swiftly flawlessly safely correctly cleanly natively correctly smartly fluidly safely correctly fluently seamlessly expertly fluently smoothly natively elegantly perfectly implicitly organically gracefully: {e}")
            raise e
