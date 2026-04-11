import asyncio
import json
import logging
import time
import uuid
from typing import Optional

import boto3
from botocore.exceptions import ClientError

from app.config import get_settings

logger = logging.getLogger(__name__)


def _get_clients():
    settings = get_settings()
    region = settings.aws_region
    return {
        "ecs": boto3.client("ecs", region_name=region),
        "ecr": boto3.client("ecr", region_name=region),
        "elbv2": boto3.client("elbv2", region_name=region),
        "codebuild": boto3.client("codebuild", region_name=region),
        "s3": boto3.client("s3", region_name=region),
        "logs": boto3.client("logs", region_name=region),
    }


# ─────────────────────────────────────────────
# S3 Operations
# ─────────────────────────────────────────────

async def upload_zip_to_s3(file_content: bytes, app_id: str) -> str:
    """Upload user's zip to S3. Returns S3 key."""
    settings = get_settings()
    clients = _get_clients()

    s3_key = f"uploads/{app_id}/{int(time.time())}.zip"

    await asyncio.get_event_loop().run_in_executor(
        None,
        lambda: clients["s3"].put_object(
            Bucket=settings.uploads_bucket_name,
            Key=s3_key,
            Body=file_content,
            ContentType="application/zip",
        ),
    )

    logger.info(f"Uploaded zip to s3://{settings.uploads_bucket_name}/{s3_key}")
    return s3_key


# ─────────────────────────────────────────────
# CodeBuild Operations
# ─────────────────────────────────────────────

async def start_build(app_id: str, s3_key: str, image_tag: str) -> str:
    """
    Trigger a CodeBuild build for a user app.
    Returns the CodeBuild build ID.
    """
    settings = get_settings()
    clients = _get_clients()

    ecr_repo_url = (
        f"{settings.ecr_base_url}/tutaia/apps/{app_id}"
    )

    response = await asyncio.get_event_loop().run_in_executor(
        None,
        lambda: clients["codebuild"].start_build(
            projectName=settings.codebuild_project_name,
            environmentVariablesOverride=[
                {"name": "APP_ID", "value": app_id, "type": "PLAINTEXT"},
                {"name": "S3_KEY", "value": s3_key, "type": "PLAINTEXT"},
                {"name": "ECR_REPO_URL", "value": ecr_repo_url, "type": "PLAINTEXT"},
                {"name": "IMAGE_TAG", "value": image_tag, "type": "PLAINTEXT"},
            ],
        ),
    )

    build_id = response["build"]["id"]
    logger.info(f"Started CodeBuild build: {build_id} for app: {app_id}")
    return build_id


async def wait_for_build(build_id: str, timeout_seconds: int = 900) -> dict:
    """
    Poll CodeBuild until build completes or times out.
    Returns build result dict with status and logs URL.
    """
    clients = _get_clients()
    start_time = time.time()

    while time.time() - start_time < timeout_seconds:
        response = await asyncio.get_event_loop().run_in_executor(
            None,
            lambda: clients["codebuild"].batch_get_builds(ids=[build_id]),
        )

        build = response["builds"][0]
        build_status = build["buildStatus"]

        logger.info(f"Build {build_id} status: {build_status}")

        if build_status == "SUCCEEDED":
            return {"status": "succeeded", "build_id": build_id}

        if build_status in ("FAILED", "FAULT", "TIMED_OUT", "STOPPED"):
            # Get the failure phase
            failed_phase = next(
                (p for p in build.get("phases", []) if p.get("phaseStatus") == "FAILED"),
                None,
            )
            error_message = "Build failed"
            if failed_phase:
                context = failed_phase.get("contexts", [{}])[0]
                error_message = context.get("message", "Build failed")

            return {
                "status": "failed",
                "build_id": build_id,
                "error": error_message,
            }

        # Still in progress - wait before polling again
        await asyncio.sleep(10)

    return {"status": "failed", "build_id": build_id, "error": "Build timed out"}


async def get_build_logs(build_id: str, num_lines: int = 50) -> list[str]:
    """Get the last N lines of CodeBuild logs."""
    clients = _get_clients()

    try:
        response = await asyncio.get_event_loop().run_in_executor(
            None,
            lambda: clients["codebuild"].batch_get_builds(ids=[build_id]),
        )

        build = response["builds"][0]
        log_group = build.get("logs", {}).get("groupName", "/tutaia/codebuild")
        log_stream = build.get("logs", {}).get("streamName", "")

        if not log_stream:
            return ["Build logs not yet available"]

        log_response = await asyncio.get_event_loop().run_in_executor(
            None,
            lambda: clients["logs"].get_log_events(
                logGroupName=log_group,
                logStreamName=log_stream,
                limit=num_lines,
                startFromHead=False,
            ),
        )

        return [event["message"] for event in log_response.get("events", [])]

    except Exception as e:
        logger.error(f"Failed to get build logs: {e}")
        return [f"Failed to retrieve logs: {str(e)}"]


# ─────────────────────────────────────────────
# ALB Operations
# ─────────────────────────────────────────────

async def get_next_rule_priority() -> int:
    """Find the next available ALB listener rule priority."""
    settings = get_settings()
    clients = _get_clients()

    response = await asyncio.get_event_loop().run_in_executor(
        None,
        lambda: clients["elbv2"].describe_rules(
            ListenerArn=settings.alb_https_listener_arn,
        ),
    )

    used_priorities = set()
    for rule in response["Rules"]:
        if rule["Priority"] != "default":
            used_priorities.add(int(rule["Priority"]))

    # Find first available priority in our range
    for priority in range(
        settings.alb_rule_priority_start,
        settings.alb_rule_priority_end,
    ):
        if priority not in used_priorities:
            return priority

    raise RuntimeError("No available ALB listener rule priorities")


async def create_target_group(app_id: str, subdomain: str) -> str:
    """Create an ALB target group for a user app. Returns TG ARN."""
    settings = get_settings()
    clients = _get_clients()

    tg_name = f"tutaia-app-{app_id}"

    response = await asyncio.get_event_loop().run_in_executor(
        None,
        lambda: clients["elbv2"].create_target_group(
            Name=tg_name,
            Protocol="HTTP",
            Port=8080,
            VpcId=_get_vpc_id(),
            TargetType="ip",
            HealthCheckProtocol="HTTP",
            HealthCheckPath="/",
            HealthCheckIntervalSeconds=30,
            HealthCheckTimeoutSeconds=10,
            HealthyThresholdCount=2,
            UnhealthyThresholdCount=3,
            Matcher={"HttpCode": "200-404"},  # Accept 404 as healthy
            Tags=[
                {"Key": "app_id", "Value": app_id},
                {"Key": "subdomain", "Value": subdomain},
            ],
        ),
    )

    tg_arn = response["TargetGroups"][0]["TargetGroupArn"]
    logger.info(f"Created target group: {tg_arn} for app: {app_id}")
    return tg_arn


async def create_listener_rule(
    app_id: str,
    subdomain: str,
    target_group_arn: str,
    priority: int,
) -> str:
    """Create ALB listener rule for host-based routing. Returns rule ARN."""
    settings = get_settings()
    clients = _get_clients()

    response = await asyncio.get_event_loop().run_in_executor(
        None,
        lambda: clients["elbv2"].create_rule(
            ListenerArn=settings.alb_https_listener_arn,
            Priority=priority,
            Conditions=[
                {
                    "Field": "host-header",
                    "HostHeaderConfig": {
                        "Values": [subdomain]
                    },
                }
            ],
            Actions=[
                {
                    "Type": "forward",
                    "TargetGroupArn": target_group_arn,
                }
            ],
            Tags=[
                {"Key": "app_id", "Value": app_id},
            ],
        ),
    )

    rule_arn = response["Rules"][0]["RuleArn"]
    logger.info(f"Created ALB listener rule: {rule_arn} for {subdomain}")
    return rule_arn


async def delete_listener_rule(rule_arn: str):
    """Delete an ALB listener rule."""
    clients = _get_clients()
    await asyncio.get_event_loop().run_in_executor(
        None,
        lambda: clients["elbv2"].delete_rule(RuleArn=rule_arn),
    )


async def delete_target_group(tg_arn: str):
    """Delete an ALB target group."""
    clients = _get_clients()
    await asyncio.get_event_loop().run_in_executor(
        None,
        lambda: clients["elbv2"].delete_target_group(TargetGroupArn=tg_arn),
    )


# ─────────────────────────────────────────────
# ECS Operations
# ─────────────────────────────────────────────

async def register_task_definition(
    app_id: str,
    image_uri: str,
    env_vars: dict,
) -> str:
    """Register an ECS task definition for a user app. Returns task def ARN."""
    settings = get_settings()
    clients = _get_clients()

    # Convert env vars dict to ECS format
    environment = [
        {"name": "PORT", "value": "8080"},
        {"name": "NODE_ENV", "value": "production"},
        {"name": "PYTHON_ENV", "value": "production"},
    ]
    for key, value in env_vars.items():
        environment.append({"name": key, "value": str(value)})

    response = await asyncio.get_event_loop().run_in_executor(
        None,
        lambda: clients["ecs"].register_task_definition(
            family=f"tutaia-app-{app_id}",
            networkMode="awsvpc",
            requiresCompatibilities=["FARGATE"],
            cpu=str(settings.ecs_task_cpu),
            memory=str(settings.ecs_task_memory),
            executionRoleArn=settings.ecs_task_execution_role_arn,
            taskRoleArn=settings.ecs_task_role_arn,
            containerDefinitions=[
                {
                    "name": f"app-{app_id}",
                    "image": image_uri,
                    "portMappings": [
                        {
                            "containerPort": 8080,
                            "protocol": "tcp",
                        }
                    ],
                    "environment": environment,
                    "essential": True,
                    "logConfiguration": {
                        "logDriver": "awslogs",
                        "options": {
                            "awslogs-group": f"/tutaia/apps/{app_id}",
                            "awslogs-region": settings.aws_region,
                            "awslogs-stream-prefix": "app",
                            "awslogs-create-group": "true",
                        },
                    },
                    "healthCheck": {
                        "command": [
                            "CMD-SHELL",
                            "curl -f http://localhost:8080/ || exit 1",
                        ],
                        "interval": 30,
                        "timeout": 10,
                        "retries": 3,
                        "startPeriod": 60,
                    },
                }
            ],
            tags=[
                {"key": "app_id", "value": app_id},
                {"key": "managed_by", "value": "tutaia"},
            ],
        ),
    )

    task_def_arn = response["taskDefinition"]["taskDefinitionArn"]
    logger.info(f"Registered task definition: {task_def_arn}")
    return task_def_arn


async def create_ecs_service(
    app_id: str,
    task_definition_arn: str,
    target_group_arn: str,
) -> str:
    """Create an ECS Fargate service for a user app. Returns service ARN."""
    settings = get_settings()
    clients = _get_clients()

    service_name = f"tutaia-app-{app_id}"

    response = await asyncio.get_event_loop().run_in_executor(
        None,
        lambda: clients["ecs"].create_service(
            cluster=settings.ecs_cluster_name,
            serviceName=service_name,
            taskDefinition=task_definition_arn,
            desiredCount=1,
            launchType="FARGATE",
            networkConfiguration={
                "awsvpcConfiguration": {
                    "subnets": settings.private_subnets,
                    "securityGroups": [settings.ecs_tasks_security_group_id],
                    "assignPublicIp": "DISABLED",
                }
            },
            loadBalancers=[
                {
                    "targetGroupArn": target_group_arn,
                    "containerName": f"app-{app_id}",
                    "containerPort": 8080,
                }
            ],
            # Rolling update - zero downtime redeploys
            deploymentConfiguration={
                "maximumPercent": 200,
                "minimumHealthyPercent": 100,
                "deploymentCircuitBreaker": {
                    "enable": True,
                    "rollback": True,  # Auto-rollback on failure
                },
            },
            enableExecuteCommand=True,  # Allows ECS Exec for debugging
            tags=[
                {"key": "app_id", "value": app_id},
                {"key": "managed_by", "value": "tutaia"},
            ],
        ),
    )

    service_arn = response["service"]["serviceArn"]
    logger.info(f"Created ECS service: {service_arn}")
    return service_name


async def update_ecs_service(app_id: str, task_definition_arn: str):
    """Update an existing ECS service with a new task definition."""
    settings = get_settings()
    clients = _get_clients()

    service_name = f"tutaia-app-{app_id}"

    await asyncio.get_event_loop().run_in_executor(
        None,
        lambda: clients["ecs"].update_service(
            cluster=settings.ecs_cluster_name,
            service=service_name,
            taskDefinition=task_definition_arn,
            forceNewDeployment=True,
        ),
    )

    logger.info(f"Updated ECS service: {service_name}")


async def delete_ecs_service(app_id: str):
    """Stop and delete an ECS service."""
    settings = get_settings()
    clients = _get_clients()

    service_name = f"tutaia-app-{app_id}"

    try:
        # Scale to 0 first
        await asyncio.get_event_loop().run_in_executor(
            None,
            lambda: clients["ecs"].update_service(
                cluster=settings.ecs_cluster_name,
                service=service_name,
                desiredCount=0,
            ),
        )

        # Wait a moment for tasks to stop
        await asyncio.sleep(5)

        # Delete service
        await asyncio.get_event_loop().run_in_executor(
            None,
            lambda: clients["ecs"].delete_service(
                cluster=settings.ecs_cluster_name,
                service=service_name,
                force=True,
            ),
        )

        logger.info(f"Deleted ECS service: {service_name}")

    except ClientError as e:
        if "ServiceNotFoundException" in str(e):
            logger.warning(f"Service {service_name} not found, skipping delete")
        else:
            raise


async def get_service_status(app_id: str) -> dict:
    """Get current status of a user app's ECS service."""
    settings = get_settings()
    clients = _get_clients()

    service_name = f"tutaia-app-{app_id}"

    try:
        response = await asyncio.get_event_loop().run_in_executor(
            None,
            lambda: clients["ecs"].describe_services(
                cluster=settings.ecs_cluster_name,
                services=[service_name],
            ),
        )

        if not response["services"]:
            return {"status": "not_found"}

        service = response["services"][0]
        running_count = service.get("runningCount", 0)
        desired_count = service.get("desiredCount", 0)
        deployments = service.get("deployments", [])

        primary = next(
            (d for d in deployments if d["status"] == "PRIMARY"),
            {}
        )

        return {
            "status": service.get("status", "UNKNOWN"),
            "running_count": running_count,
            "desired_count": desired_count,
            "pending_count": service.get("pendingCount", 0),
            "is_healthy": running_count == desired_count and desired_count > 0,
            "deployment_status": primary.get("rolloutState", "UNKNOWN"),
        }

    except Exception as e:
        logger.error(f"Failed to get service status for {app_id}: {e}")
        return {"status": "error", "error": str(e)}


async def get_app_logs(app_id: str, num_lines: int = 100) -> list[str]:
    """Get recent logs from a user's app."""
    clients = _get_clients()
    settings = get_settings()

    log_group = f"/tutaia/apps/{app_id}"

    try:
        # Get latest log stream
        streams_response = await asyncio.get_event_loop().run_in_executor(
            None,
            lambda: clients["logs"].describe_log_streams(
                logGroupName=log_group,
                orderBy="LastEventTime",
                descending=True,
                limit=1,
            ),
        )

        streams = streams_response.get("logStreams", [])
        if not streams:
            return ["No logs available yet. App may still be starting."]

        stream_name = streams[0]["logStreamName"]

        log_response = await asyncio.get_event_loop().run_in_executor(
            None,
            lambda: clients["logs"].get_log_events(
                logGroupName=log_group,
                logStreamName=stream_name,
                limit=num_lines,
                startFromHead=False,
            ),
        )

        return [event["message"] for event in log_response.get("events", [])]

    except ClientError as e:
        if "ResourceNotFoundException" in str(e):
            return ["App logs not yet available. App may still be starting."]
        logger.error(f"Failed to get app logs: {e}")
        return [f"Failed to retrieve logs: {str(e)}"]


def _get_vpc_id() -> str:
    """Get VPC ID from settings."""
    return "vpc-0c8dd5275c6f7dcee"
