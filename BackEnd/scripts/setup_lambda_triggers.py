import os
import sys

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from config import get_settings


def setup():
    """
    Prints the updated S3 → SNS → SQS → Lambda event routing instructions.

    New flow (replacing the old S3 → SNS → Lambda direct subscription):
      1. S3 ObjectCreated → fires to SNS topic (no change)
      2. SNS topic → delivers to SQS queue (cloudgraph-image-processing)
      3. SQS queue → triggers both image_processor and thumbnail_generator Lambda
         functions with BatchSize=10, handling up to 300–400 uploads in managed batches.

    Run scripts/setup_database.py first to create the SQL database tables.
    """
    settings = get_settings()
    bucket_name = settings.S3_BUCKET_NAME

    print("=" * 60)
    print("CloudGraph — S3 → SNS → SQS → Lambda Setup Instructions")
    print("=" * 60)
    print()
    print("STEP 1: Create the SQS queue using Terraform (recommended):")
    print("  cd BackEnd/infra && terraform init && terraform apply")
    print()
    print("  Or manually via AWS CLI:")
    print("""
  # Create DLQ
  aws sqs create-queue \\
    --queue-name cloudgraph-image-processing-dlq

  # Create main queue with redrive policy (replace DLQ_ARN)
  aws sqs create-queue \\
    --queue-name cloudgraph-image-processing \\
    --attributes '{
      "VisibilityTimeout": "300",
      "RedrivePolicy": "{\\"deadLetterTargetArn\\":\\"<DLQ_ARN>\\",\\"maxReceiveCount\\":\\"3\\"}"
    }'
""")

    print("STEP 2: Subscribe the SQS queue to the SNS topic:")
    print(f"""
  aws sns subscribe \\
    --topic-arn <YOUR_SNS_TOPIC_ARN> \\
    --protocol sqs \\
    --notification-endpoint <SQS_QUEUE_ARN> \\
    --attributes '{{"RawMessageDelivery": "false"}}'
""")

    print("STEP 3: Add SQS event source mappings to both Lambda functions")
    print("        (BatchSize=10 processes uploaded images in controlled batches):")
    print("""
  # image_processor Lambda
  aws lambda create-event-source-mapping \\
    --event-source-arn <SQS_QUEUE_ARN> \\
    --function-name image_processor \\
    --batch-size 10 \\
    --function-response-types ReportBatchItemFailures

  # thumbnail_generator Lambda
  aws lambda create-event-source-mapping \\
    --event-source-arn <SQS_QUEUE_ARN> \\
    --function-name thumbnail_generator \\
    --batch-size 10 \\
    --function-response-types ReportBatchItemFailures
""")

    print("STEP 4: Confirm S3 bucket notification still points to SNS:")
    print(f"""
  # S3 → SNS notification (unchanged from original setup)
  # Bucket: {bucket_name}
  # Event:  s3:ObjectCreated:*
  # Prefix: uploads/
  # Target: SNS Topic → now fan-out to SQS instead of directly to Lambda
""")
    print("NOTE: Remove any direct Lambda subscriptions from the SNS topic.")
    print("      The SQS queue is now the sole consumer of SNS messages.")


if __name__ == "__main__":
    setup()
