# BackEnd/infra — Infrastructure Files Index

This directory contains all infrastructure configuration and deployment scripts for CloudGraph.

| File | Description |
|---|---|
| [`sqs.tf`](./sqs.tf) | Terraform: SQS queue, Dead Letter Queue, redrive policy, and SNS queue policy for the image processing pipeline |
| [`ecs-task-definition.json`](./ecs-task-definition.json) | AWS ECS Fargate task definition: container image, port, secrets from Secrets Manager, IAM roles, and CloudWatch log config |
| [`ecs-deploy.sh`](./ecs-deploy.sh) | Shell script to build the Docker image, push to ECR, register a new task definition revision, and update the ECS service |
| [`ecs-autoscaling.json`](./ecs-autoscaling.json) | Reference document for Application Auto Scaling: CPU target tracking at 60%, min 1 / max 10 tasks, with ready-to-run AWS CLI commands |
| [`cognito-identity-pool-policy.json`](./cognito-identity-pool-policy.json) | IAM policy for the Cognito Identity Pool authenticated role — restricts S3 access to each user's own prefix using the Cognito Identity sub variable |
| [`IDENTITY_POOL_SETUP.md`](./IDENTITY_POOL_SETUP.md) | Step-by-step guide to creating a Cognito Identity Pool, linking it to the existing User Pool, and attaching the per-user S3 isolation policy |

## Deployment Order

1. `sqs.tf` — provision queues before deploying Lambdas
2. Deploy Lambda functions (`../scripts/deploy_lambda.sh`) and attach SQS event source mappings
3. `ecs-task-definition.json` + `ecs-deploy.sh` — build and deploy the API container
4. `ecs-autoscaling.json` — apply auto-scaling after the ECS service is stable
5. `cognito-identity-pool-policy.json` + `IDENTITY_POOL_SETUP.md` — configure identity pool for direct client uploads
