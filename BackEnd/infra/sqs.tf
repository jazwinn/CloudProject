# SQS Queue and Dead Letter Queue for CloudGraph image processing pipeline.
# This decouples the S3 → SNS trigger from Lambda, buffering events during
# bulk uploads (300–400 images) to prevent Lambda concurrency exhaustion.
#
# New event flow: S3 → SNS → SQS → Lambda (image_processor + thumbnail_generator)

# ─────────────────────────────────────────────────────────────
# Dead Letter Queue
# Receives messages that fail processing more than maxReceiveCount times.
# ─────────────────────────────────────────────────────────────
resource "aws_sqs_queue" "cloudgraph_image_processing_dlq" {
  name                      = "cloudgraph-image-processing-dlq"
  message_retention_seconds = 1209600 # 14 days — gives time to inspect failed messages

  tags = {
    Project = "CloudGraph"
    Purpose = "DeadLetterQueue"
  }
}

# ─────────────────────────────────────────────────────────────
# Main Processing Queue
# ─────────────────────────────────────────────────────────────
resource "aws_sqs_queue" "cloudgraph_image_processing" {
  name                       = "cloudgraph-image-processing"
  visibility_timeout_seconds = 300 # Must be >= Lambda timeout to avoid duplicate processing
  message_retention_seconds  = 86400 # 1 day

  # Redrive policy: after 3 failed receive attempts, move to DLQ
  redrive_policy = jsonencode({
    deadLetterTargetArn = aws_sqs_queue.cloudgraph_image_processing_dlq.arn
    maxReceiveCount     = 3
  })

  tags = {
    Project = "CloudGraph"
    Purpose = "ImageProcessingQueue"
  }
}

# ─────────────────────────────────────────────────────────────
# Queue Policy
# Grants the existing CloudGraph SNS topic permission to send messages
# to the SQS queue. Replace YOUR_ACCOUNT_ID and YOUR_SNS_TOPIC_ARN.
# ─────────────────────────────────────────────────────────────
resource "aws_sqs_queue_policy" "cloudgraph_image_processing_policy" {
  queue_url = aws_sqs_queue.cloudgraph_image_processing.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Sid       = "AllowSNSToSendMessages"
        Effect    = "Allow"
        Principal = { Service = "sns.amazonaws.com" }
        Action    = "sqs:SendMessage"
        Resource  = aws_sqs_queue.cloudgraph_image_processing.arn
        Condition = {
          ArnEquals = {
            "aws:SourceArn" = "arn:aws:sns:YOUR_REGION:YOUR_ACCOUNT_ID:YOUR_SNS_TOPIC_NAME"
          }
        }
      }
    ]
  })
}

# ─────────────────────────────────────────────────────────────
# Outputs — use these ARNs when setting up the SNS subscription
# and Lambda event source mappings (see setup_lambda_triggers.py).
# ─────────────────────────────────────────────────────────────
output "sqs_queue_arn" {
  value       = aws_sqs_queue.cloudgraph_image_processing.arn
  description = "ARN of the main image processing SQS queue"
}

output "sqs_queue_url" {
  value       = aws_sqs_queue.cloudgraph_image_processing.id
  description = "URL of the main image processing SQS queue"
}

output "sqs_dlq_arn" {
  value       = aws_sqs_queue.cloudgraph_image_processing_dlq.arn
  description = "ARN of the image processing Dead Letter Queue"
}
