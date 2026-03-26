import os
import sys

# Ensure the parent app root is visible to Python mapping relative imports (like 'config')
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import boto3
from config import get_settings

def create_metadata_table():
    """One-time execution script to create the DynamoDB table securely."""
    settings = get_settings()
    dynamodb = boto3.resource(
        'dynamodb',
        aws_access_key_id=settings.AWS_ACCESS_KEY_ID,
        aws_secret_access_key=settings.AWS_SECRET_ACCESS_KEY,
        aws_session_token=settings.AWS_SESSION_TOKEN,
        region_name=settings.AWS_REGION
    )

    table_name = settings.DYNAMO_TABLE_NAME

    try:
        print(f"Starting creation of DynamoDB table: '{table_name}'...")
        table = dynamodb.create_table(
            TableName=table_name,
            KeySchema=[
                {
                    'AttributeName': 'image_id',
                    'KeyType': 'HASH'  # Partition key
                }
            ],
            AttributeDefinitions=[
                {
                    'AttributeName': 'image_id',
                    'AttributeType': 'S'
                }
            ],
            BillingMode='PAY_PER_REQUEST'
        )
        
        # Block script completion until table finishes provisioning
        table.wait_until_exists()
        print(f"Table '{table_name}' successfully provisioned and ready to accept traffic.")
        
    except dynamodb.meta.client.exceptions.ResourceInUseException:
        print(f"Notice: Table '{table_name}' already exists.")
    except Exception as e:
        print(f"Critical error provisioning table: {e}")

if __name__ == "__main__":
    create_metadata_table()
