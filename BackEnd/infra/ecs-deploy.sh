#!/usr/bin/env bash
# ecs-deploy.sh — Builds and deploys the CloudGraph API to ECS Fargate.
#
# Usage:
#   chmod +x BackEnd/infra/ecs-deploy.sh
#   bash BackEnd/infra/ecs-deploy.sh
#
# Prerequisites:
#   - AWS CLI configured (aws sso login, or IAM user with push perms)
#   - Docker running locally
#   - ECR repository already created
#   - ECS cluster and service already created (first-time setup only)

set -e  # Exit immediately on any error

# ── Configuration — update these for your environment ─────────────────────────
AWS_REGION="YOUR_REGION"
AWS_ACCOUNT_ID="YOUR_ACCOUNT_ID"
ECR_REPO="YOUR_ECR_REPO_NAME"          # e.g. cloudgraph-backend
ECS_CLUSTER="YOUR_ECS_CLUSTER_NAME"   # e.g. cloudgraph-cluster
ECS_SERVICE="YOUR_ECS_SERVICE_NAME"   # e.g. cloudgraph-api-service
TASK_FAMILY="cloudgraph-api"
TASK_DEF_FILE="$(dirname "$0")/ecs-task-definition.json"

ECR_URI="${AWS_ACCOUNT_ID}.dkr.ecr.${AWS_REGION}.amazonaws.com/${ECR_REPO}"
IMAGE_TAG="${ECR_URI}:latest"

# ── Step 1: Build Docker image ─────────────────────────────────────────────────
echo ">>> Building Docker image..."
docker build -t "${ECR_REPO}:latest" "$(dirname "$0")/../"
docker tag "${ECR_REPO}:latest" "${IMAGE_TAG}"

# ── Step 2: Authenticate with ECR ─────────────────────────────────────────────
echo ">>> Logging in to ECR..."
aws ecr get-login-password --region "${AWS_REGION}" \
  | docker login --username AWS --password-stdin "${AWS_ACCOUNT_ID}.dkr.ecr.${AWS_REGION}.amazonaws.com"

# ── Step 3: Push image to ECR ─────────────────────────────────────────────────
echo ">>> Pushing image to ECR: ${IMAGE_TAG}"
docker push "${IMAGE_TAG}"

# ── Step 4: Register new task definition revision ─────────────────────────────
echo ">>> Registering new task definition revision..."
NEW_TASK_DEF=$(aws ecs register-task-definition \
  --cli-input-json "file://${TASK_DEF_FILE}" \
  --region "${AWS_REGION}" \
  --query 'taskDefinition.taskDefinitionArn' \
  --output text)

echo ">>> Registered: ${NEW_TASK_DEF}"

# ── Step 5: Update ECS service to use the new revision ────────────────────────
echo ">>> Updating ECS service '${ECS_SERVICE}' in cluster '${ECS_CLUSTER}'..."
aws ecs update-service \
  --cluster "${ECS_CLUSTER}" \
  --service "${ECS_SERVICE}" \
  --task-definition "${NEW_TASK_DEF}" \
  --region "${AWS_REGION}" \
  --force-new-deployment \
  --query 'service.serviceName' \
  --output text

echo ">>> Deployment triggered successfully. Monitor progress:"
echo "    aws ecs wait services-stable --cluster ${ECS_CLUSTER} --services ${ECS_SERVICE} --region ${AWS_REGION}"
