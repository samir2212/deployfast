#!/bin/bash
# ─────────────────────────────────────────────
# deploy-platform.sh
# Builds and deploys the Tutaia Platform API to ECS
# Run this from the tutaia-api directory
# ─────────────────────────────────────────────
set -e

AWS_REGION="eu-central-1"
AWS_ACCOUNT_ID="856930835134"
ECR_REPO="${AWS_ACCOUNT_ID}.dkr.ecr.${AWS_REGION}.amazonaws.com/tutaia/platform-api"
ECS_CLUSTER="tutaia-cluster"
ECS_SERVICE="tutaia-platform-api"
IMAGE_TAG=$(git rev-parse --short HEAD 2>/dev/null || echo "latest")

echo "🚀 Deploying Tutaia Platform API"
echo "   Image tag: ${IMAGE_TAG}"
echo "   Region:    ${AWS_REGION}"
echo ""

# ── Step 1: Login to ECR ──────────────────────
echo "📦 Logging into ECR..."
aws ecr get-login-password --region ${AWS_REGION} | \
  docker login --username AWS --password-stdin \
  ${AWS_ACCOUNT_ID}.dkr.ecr.${AWS_REGION}.amazonaws.com

# ── Step 2: Build image ───────────────────────
echo "🔨 Building Docker image..."
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
API_DIR="$(cd "${SCRIPT_DIR}/.." && pwd)"

docker build \
  --platform linux/amd64 \
  -f ${API_DIR}/Dockerfile \
  -t ${ECR_REPO}:${IMAGE_TAG} \
  -t ${ECR_REPO}:latest \
  ${API_DIR}

# ── Step 3: Push to ECR ───────────────────────
echo "⬆️  Pushing to ECR..."
docker push ${ECR_REPO}:${IMAGE_TAG}
docker push ${ECR_REPO}:latest

# ── Step 4: Update ECS service ────────────────
echo "🔄 Updating ECS service..."

# Check if service exists
SERVICE_EXISTS=$(aws ecs describe-services \
  --cluster ${ECS_CLUSTER} \
  --services ${ECS_SERVICE} \
  --region ${AWS_REGION} \
  --query "services[?status=='ACTIVE'] | length(@)" \
  --output text 2>/dev/null || echo "0")

if [ "$SERVICE_EXISTS" = "0" ]; then
  echo "⚠️  ECS service not found. Creating it..."
  echo "   You need to run create-platform-service.sh first."
  echo "   See scripts/create-platform-service.sh"
  exit 1
fi

aws ecs update-service \
  --cluster ${ECS_CLUSTER} \
  --service ${ECS_SERVICE} \
  --force-new-deployment \
  --region ${AWS_REGION} \
  --query "service.deployments[0].status" \
  --output text

echo ""
echo "✅ Deployment triggered!"
echo "   Monitor: https://eu-central-1.console.aws.amazon.com/ecs/v2/clusters/${ECS_CLUSTER}/services/${ECS_SERVICE}"
echo "   Logs:    aws logs tail /tutaia/platform-api --follow --region ${AWS_REGION}"
echo ""
echo "   Health check: curl https://api.ai-deploy.tutaia.com/health"
