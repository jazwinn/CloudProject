import os
import sys
import boto3

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from config import get_settings

def setup():
    """
    Outputs S3 trigger configuration mappings for Lambda functions.
    Run scripts/setup_database.py first to create the SQL database tables.
    """
    settings = get_settings()
    bucket_name = settings.S3_BUCKET_NAME

    print("[Note] S3 ObjectCreated triggers must be manually bound to the Lambdas via AWS Console or CLI.")
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
