import os
import sys
import boto3

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from config import get_settings

def setup():
    """
    Sets up the DynamoDB dependency tables and outputs S3 trigger mappings.
    """
    settings = get_settings()
    
    dynamodb = boto3.client(
        'dynamodb',
        aws_access_key_id=settings.AWS_ACCESS_KEY_ID,
        aws_secret_access_key=settings.AWS_SECRET_ACCESS_KEY,
        aws_session_token=settings.AWS_SESSION_TOKEN,
        region_name=settings.AWS_REGION
    )

    table_name = "ClusterResults"
    try:
        print(f"Creating DynamoDB table: {table_name}...")
        dynamodb.create_table(
            TableName=table_name,
            KeySchema=[
                {'AttributeName': 'user_id', 'KeyType': 'HASH'},
                {'AttributeName': 'computed_at', 'KeyType': 'RANGE'}
            ],
            AttributeDefinitions=[
                {'AttributeName': 'user_id', 'AttributeType': 'S'},
                {'AttributeName': 'computed_at', 'AttributeType': 'S'}
            ],
            BillingMode='PAY_PER_REQUEST'
        )
        print(f"Table '{table_name}' creation initiated successfully.")
    except dynamodb.exceptions.ResourceInUseException:
        print(f"Table '{table_name}' already exists.")
    except Exception as e:
        print(f"Failed to create table: {e}")

    bucket_name = settings.S3_BUCKET_NAME
    print(f"\n[Note] S3 ObjectCreated triggers must be manually bound to the Lambdas via AWS Console or CLI.")
    print("Example boto3 configuration map:")
    print(f"""
    s3_client.put_bucket_notification_configuration(
        Bucket='{bucket_name}',
        NotificationConfiguration={{
            'LambdaFunctionConfigurations': [
                {{
                    'LambdaFunctionArn': '<ARN_OF_THUMBNAIL_GENERATOR>',
                    'Events': ['s3:ObjectCreated:*'],
                    'Filter': {{'Key': {{'FilterRules': [{{'Name': 'prefix', 'Value': 'uploads/'}}]}}}}
                }},
                {{
                    'LambdaFunctionArn': '<ARN_OF_IMAGE_PROCESSOR>',
                    'Events': ['s3:ObjectCreated:*'],
                    'Filter': {{'Key': {{'FilterRules': [{{'Name': 'prefix', 'Value': 'uploads/'}}]}}}}
                }}
            ]
        }}
    )
    """)

if __name__ == "__main__":
    setup()
