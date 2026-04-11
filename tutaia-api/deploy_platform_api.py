#!/usr/bin/env python3
"""
Deploy the platform API itself to ECS.
Run this script after building and pushing the Docker image.

Usage:
    python deploy_platform_api.py
"""

import boto3
import json
import sys

# ── Fill these in from your terraform outputs ──
AWS_REGION = "eu-central-1"
AWS_ACCOUNT_ID = "856930835134"
ECR_REPO = f"{AWS_ACCOUNT_ID}.dkr.ecr.{AWS_REGION}.amazonaws.com/tutaia/platform-api"
IMAGE_TAG = "latest"
ECS_CLUSTER = "tutaia-cluster"
SERVICE_NAME = "tutaia-platform-api"
TASK_EXECUTION_ROLE = f"arn:aws:iam::{AWS_ACCOUNT_ID}:role/tutaia-ecs-task-execution-role"
TASK_ROLE = f"arn:aws:iam::{AWS_ACCOUNT_ID}:role/tutaia-platform-api-task-role"
TARGET_GROUP_ARN = f"arn:aws:elasticloadbalancing:{AWS_REGION}:{AWS_ACCOUNT_ID}:targetgroup/tutaia-platform-api-tg/3f878fe6602a2259"
SECURITY_GROUP = "sg-00cba46c42d4c1d5e"
PRIVATE_SUBNETS = [
    "subnet-088505349ecd7387a",
    "subnet-03ac7243e6039bfff",
]

ecs = boto3.client("ecs", region_name=AWS_REGION)


def register_task_definition():
    print("Registering task definition...")
    response = ecs.register_task_definition(
        family="tutaia-platform-api",
        networkMode="awsvpc",
        requiresCompatibilities=["FARGATE"],
        cpu="512",
        memory="1024",
        executionRoleArn=TASK_EXECUTION_ROLE,
        taskRoleArn=TASK_ROLE,
        containerDefinitions=[
            {
                "name": "platform-api",
                "image": f"{ECR_REPO}:{IMAGE_TAG}",
                "portMappings": [
                    {
                        "containerPort": 3000,
                        "protocol": "tcp",
                    }
                ],
                "essential": True,
                "environment": [
                    # All secrets come from SSM at runtime
                    # No secrets here
                    {"name": "TUTAIA_AWS_REGION", "value": AWS_REGION},
                    {"name": "TUTAIA_AWS_ACCOUNT_ID", "value": AWS_ACCOUNT_ID},
                ],
                "logConfiguration": {
                    "logDriver": "awslogs",
                    "options": {
                        "awslogs-group": "/tutaia/platform-api",
                        "awslogs-region": AWS_REGION,
                        "awslogs-stream-prefix": "api",
                        "awslogs-create-group": "true",
                    },
                },
                "healthCheck": {
                    "command": [
                        "CMD-SHELL",
                        "curl -f http://localhost:3000/health || exit 1",
                    ],
                    "interval": 30,
                    "timeout": 10,
                    "retries": 3,
                    "startPeriod": 30,
                },
            }
        ],
    )
    arn = response["taskDefinition"]["taskDefinitionArn"]
    print(f"Task definition registered: {arn}")
    return arn


def create_or_update_service(task_def_arn: str):
    print("Checking if service exists...")

    try:
        response = ecs.describe_services(
            cluster=ECS_CLUSTER,
            services=[SERVICE_NAME],
        )
        services = [
            s for s in response["services"]
            if s["status"] != "INACTIVE"
        ]

        if services:
            print(f"Service exists, updating...")
            ecs.update_service(
                cluster=ECS_CLUSTER,
                service=SERVICE_NAME,
                taskDefinition=task_def_arn,
                forceNewDeployment=True,
            )
            print(f"Service updated: {SERVICE_NAME}")
            return

    except Exception as e:
        print(f"Service check error (will create): {e}")

    print("Creating new service...")
    ecs.create_service(
        cluster=ECS_CLUSTER,
        serviceName=SERVICE_NAME,
        taskDefinition=task_def_arn,
        desiredCount=1,
        launchType="FARGATE",
        networkConfiguration={
            "awsvpcConfiguration": {
                "subnets": PRIVATE_SUBNETS,
                "securityGroups": [SECURITY_GROUP],
                "assignPublicIp": "DISABLED",
            }
        },
        loadBalancers=[
            {
                "targetGroupArn": TARGET_GROUP_ARN,
                "containerName": "platform-api",
                "containerPort": 3000,
            }
        ],
        deploymentConfiguration={
            "maximumPercent": 200,
            "minimumHealthyPercent": 100,
            "deploymentCircuitBreaker": {
                "enable": True,
                "rollback": True,
            },
        },
        enableExecuteCommand=True,
    )
    print(f"Service created: {SERVICE_NAME}")


def main():
    print("=" * 50)
    print("Deploying Tutaia Platform API to ECS")
    print("=" * 50)

    task_def_arn = register_task_definition()
    create_or_update_service(task_def_arn)

    print("\n" + "=" * 50)
    print("Deployment triggered successfully!")
    print(f"Monitor: https://eu-central-1.console.aws.amazon.com/ecs/v2/clusters/{ECS_CLUSTER}/services/{SERVICE_NAME}")
    print("API will be available at: https://api.ai-deploy.tutaia.com")
    print("=" * 50)


if __name__ == "__main__":
    main()
