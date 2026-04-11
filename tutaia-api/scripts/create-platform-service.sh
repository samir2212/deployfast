#!/bin/bash
# ─────────────────────────────────────────────
# create-platform-service.sh
# One-time script to create the ECS service for
# the platform API. Run ONCE after first deploy.
# ─────────────────────────────────────────────
set -e

AWS_REGION="eu-central-1"
AWS_ACCOUNT_ID="856930835134"
ECS_CLUSTER="tutaia-cluster"
ECR_IMAGE="${AWS_ACCOUNT_ID}.dkr.ecr.${AWS_REGION}.amazonaws.com/tutaia/platform-api:latest"

# From terraform outputs
PRIVATE_SUBNETS="subnet-088505349ecd7387a,subnet-03ac7243e6039bfff"
PLATFORM_API_SG="sg-00cba46c42d4c1d5e"
EXECUTION_ROLE="arn:aws:iam::856930835134:role/tutaia-ecs-task-execution-role"
PLATFORM_TASK_ROLE="arn:aws:iam::856930835134:role/tutaia-platform-api-task-role"
PLATFORM_TG_ARN="arn:aws:elasticloadbalancing:eu-central-1:856930835134:targetgroup/tutaia-platform-api-tg/3f878fe6602a2259"

echo "Creating platform API ECS service..."

# ── Step 1: Register task definition ──────────
echo "Registering task definition..."

# Build env vars from .env file
if [ ! -f ".env" ]; then
  echo "❌ .env file not found. Copy .env.example to .env and fill in values."
  exit 1
fi

# Read env vars from .env file and format for ECS
ENV_VARS=$(grep -v '^#' .env | grep -v '^$' | \
  while IFS='=' read -r key value; do
    echo "{\"name\":\"$key\",\"value\":\"$value\"}"
  done | paste -sd ',' -)

TASK_DEF=$(cat <<EOF
{
  "family": "tutaia-platform-api",
  "taskRoleArn": "${PLATFORM_TASK_ROLE}",
  "executionRoleArn": "${EXECUTION_ROLE}",
  "networkMode": "awsvpc",
  "requiresCompatibilities": ["FARGATE"],
  "cpu": "512",
  "memory": "1024",
  "containerDefinitions": [
    {
      "name": "platform-api",
      "image": "${ECR_IMAGE}",
      "portMappings": [
        {
          "containerPort": 3000,
          "protocol": "tcp"
        }
      ],
      "environment": [${ENV_VARS}],
      "essential": true,
      "logConfiguration": {
        "logDriver": "awslogs",
        "options": {
          "awslogs-group": "/tutaia/platform-api",
          "awslogs-region": "${AWS_REGION}",
          "awslogs-stream-prefix": "api"
        }
      },
      "mountPoints": [
        {
          "sourceVolume": "docker-socket",
          "containerPath": "/var/run/docker.sock"
        }
      ]
    }
  ],
  "volumes": [
    {
      "name": "docker-socket",
      "host": {
        "sourcePath": "/var/run/docker.sock"
      }
    }
  ]
}
EOF
)

TASK_DEF_ARN=$(aws ecs register-task-definition \
  --cli-input-json "${TASK_DEF}" \
  --region ${AWS_REGION} \
  --query "taskDefinition.taskDefinitionArn" \
  --output text)

echo "Task definition: ${TASK_DEF_ARN}"

# ── Step 2: Create ECS service ─────────────────
echo "Creating ECS service..."

aws ecs create-service \
  --cluster ${ECS_CLUSTER} \
  --service-name tutaia-platform-api \
  --task-definition ${TASK_DEF_ARN} \
  --desired-count 1 \
  --launch-type FARGATE \
  --network-configuration "awsvpcConfiguration={
    subnets=[${PRIVATE_SUBNETS}],
    securityGroups=[${PLATFORM_API_SG}],
    assignPublicIp=DISABLED
  }" \
  --load-balancers "targetGroupArn=${PLATFORM_TG_ARN},containerName=platform-api,containerPort=3000" \
  --enable-execute-command \
  --region ${AWS_REGION} \
  --query "service.serviceArn" \
  --output text

echo ""
echo "✅ Platform API service created!"
echo ""
echo "Monitor startup:"
echo "  aws ecs describe-services --cluster ${ECS_CLUSTER} --services tutaia-platform-api --region ${AWS_REGION}"
echo ""
echo "View logs:"
echo "  aws logs tail /tutaia/platform-api --follow --region ${AWS_REGION}"
