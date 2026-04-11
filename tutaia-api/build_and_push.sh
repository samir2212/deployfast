#!/bin/bash
# build_and_push.sh
# Builds the platform API Docker image and pushes to ECR
# Run this from the tutaia-api directory

set -e

AWS_REGION="eu-central-1"
AWS_ACCOUNT_ID="856930835134"
ECR_REPO="${AWS_ACCOUNT_ID}.dkr.ecr.${AWS_REGION}.amazonaws.com/tutaia/platform-api"
IMAGE_TAG="latest"

echo "================================================"
echo "Building Tutaia Platform API"
echo "================================================"

# Authenticate Docker to ECR
echo "→ Authenticating to ECR..."
aws ecr get-login-password --region ${AWS_REGION} | \
  docker login --username AWS --password-stdin \
  ${AWS_ACCOUNT_ID}.dkr.ecr.${AWS_REGION}.amazonaws.com

# Build the image
echo "→ Building Docker image..."
docker build \
  --platform linux/amd64 \
  -t tutaia-platform-api:${IMAGE_TAG} \
  .

# Tag for ECR
echo "→ Tagging image..."
docker tag tutaia-platform-api:${IMAGE_TAG} ${ECR_REPO}:${IMAGE_TAG}
docker tag tutaia-platform-api:${IMAGE_TAG} ${ECR_REPO}:$(date +%Y%m%d%H%M%S)

# Push to ECR
echo "→ Pushing to ECR..."
docker push ${ECR_REPO}:${IMAGE_TAG}
docker push ${ECR_REPO}:$(date +%Y%m%d%H%M%S)

echo ""
echo "================================================"
echo "Image pushed: ${ECR_REPO}:${IMAGE_TAG}"
echo "Next: python deploy_platform_api.py"
echo "================================================"
