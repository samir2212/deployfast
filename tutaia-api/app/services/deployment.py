import logging
import os
import tempfile
import time
import uuid
from datetime import datetime

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.config import get_settings
from app.models.models import App, DeploymentStatus, User
from app.services import aws
from app.services.preflight import scan_zip, inject_procfile_into_zip

logger = logging.getLogger(__name__)


def _generate_app_id() -> str:
    return str(uuid.uuid4()).replace("-", "")[:8]


def _generate_subdomain(app_id: str) -> str:
    settings = get_settings()
    return f"{app_id}.{settings.platform_domain}"


async def preflight_scan(zip_path: str) -> dict:
    result = scan_zip(zip_path)
    return {
        "stack": result.stack,
        "required_env_vars": result.required_env_vars,
        "has_sqlite": result.has_sqlite,
        "entry_point": result.entry_point,
        "warnings": result.warnings,
        "errors": result.errors,
        "can_deploy": len(result.errors) == 0,
        "procfile_injected": result.needs_procfile,
        "procfile_content": result.procfile_content,
    }


async def deploy_app(
    user: User,
    app_name: str,
    zip_content: bytes,
    zip_path: str,
    env_vars: dict,
    db: AsyncSession,
    custom_subdomain: str | None = None,
) -> App:
    """
    Full deployment flow:
    1. Pre-flight scan
    2. Auto-inject Procfile if missing
    3. Upload zip to S3
    4. Create app record in DB
    5. Trigger CodeBuild
    6. Wait for build
    7. Create ECS infrastructure
    8. Return app with live URL
    """
    settings = get_settings()

    app_id = _generate_app_id()
    if custom_subdomain:
        subdomain = f"{custom_subdomain}.{settings.platform_domain}"
    else:
        subdomain = _generate_subdomain(app_id)
    image_tag = f"v{int(time.time())}"

    logger.info(f"Starting deployment for user {user.id}, app {app_id}")

    # Run pre-flight scan
    preflight = scan_zip(zip_path)
    if preflight.errors:
        raise ValueError(f"Pre-flight check failed: {'; '.join(preflight.errors)}")

    # Log what we detected
    logger.info(
        f"[{app_id}] Stack: {preflight.stack}, "
        f"Entry: {preflight.entry_point}, "
        f"Procfile needed: {preflight.needs_procfile}"
    )

    # Create app record immediately so user can track progress
    app = App(
        id=app_id,
        user_id=user.id,
        name=app_name,
        subdomain=subdomain,
        status=DeploymentStatus.PENDING,
        env_vars=env_vars,
        required_env_vars=preflight.required_env_vars,
        image_tag=image_tag,
    )
    db.add(app)
    await db.commit()
    await db.refresh(app)

    try:
        # Step 1: Auto-inject Procfile if missing, then upload to S3
        logger.info(f"[{app_id}] Preparing zip for upload...")
        app.status = DeploymentStatus.BUILDING
        await db.commit()

        upload_content = zip_content

        if preflight.needs_procfile and preflight.procfile_content:
            logger.info(
                f"[{app_id}] Auto-injecting Procfile: {preflight.procfile_content}"
            )
            with tempfile.NamedTemporaryFile(suffix=".zip", delete=False) as tmp:
                tmp.write(zip_content)
                tmp_path = tmp.name

            try:
                patched_path = inject_procfile_into_zip(
                    tmp_path,
                    preflight.procfile_content,
                    tmp_path + "_patched.zip",
                )
                with open(patched_path, "rb") as f:
                    upload_content = f.read()
                logger.info(f"[{app_id}] Procfile injected successfully")
            except Exception as e:
                logger.warning(
                    f"[{app_id}] Procfile injection failed, using original zip: {e}"
                )
            finally:
                try:
                    os.unlink(tmp_path)
                except Exception:
                    pass

        # Step 2: Upload to S3
        logger.info(f"[{app_id}] Uploading to S3...")
        s3_key = await aws.upload_zip_to_s3(upload_content, app_id)

        # Step 3: Trigger CodeBuild
        logger.info(f"[{app_id}] Starting CodeBuild...")
        build_id = await aws.start_build(app_id, s3_key, image_tag)
        app.codebuild_build_id = build_id
        await db.commit()

        # Step 4: Wait for build to complete
        logger.info(f"[{app_id}] Waiting for build...")
        build_result = await aws.wait_for_build(build_id)

        if build_result["status"] != "succeeded":
            raise RuntimeError(
                f"Build failed: {build_result.get('error', 'Unknown build error')}"
            )

        logger.info(f"[{app_id}] Build succeeded, deploying to ECS...")
        app.status = DeploymentStatus.DEPLOYING
        await db.commit()

        # Step 5: Set up ECR repo URL
        image_uri = f"{settings.ecr_base_url}/tutaia/apps/{app_id}:{image_tag}"
        app.ecr_repo_url = f"{settings.ecr_base_url}/tutaia/apps/{app_id}"

        # Step 6: Create ALB target group
        logger.info(f"[{app_id}] Creating ALB target group...")
        tg_arn = await aws.create_target_group(app_id, subdomain)
        app.alb_target_group_arn = tg_arn

        # Step 7: Get next available rule priority
        priority = await aws.get_next_rule_priority()
        app.alb_rule_priority = priority

        # Step 8: Create ALB listener rule
        logger.info(f"[{app_id}] Creating ALB listener rule for {subdomain}...")
        rule_arn = await aws.create_listener_rule(
            app_id, subdomain, tg_arn, priority
        )
        app.alb_listener_rule_arn = rule_arn

        # Step 9: Register ECS task definition
        logger.info(f"[{app_id}] Registering ECS task definition...")
        task_def_arn = await aws.register_task_definition(
            app_id, image_uri, env_vars
        )
        app.ecs_task_definition_arn = task_def_arn

        # Step 10: Create ECS service
        logger.info(f"[{app_id}] Creating ECS service...")
        service_name = await aws.create_ecs_service(
            app_id, task_def_arn, tg_arn
        )
        app.ecs_service_name = service_name

        # Done
        app.status = DeploymentStatus.RUNNING
        app.last_deployed_at = datetime.utcnow()
        await db.commit()
        await db.refresh(app)

        logger.info(f"[{app_id}] Deployment complete: {app.url}")
        return app

    except Exception as e:
        logger.error(f"[{app_id}] Deployment failed: {e}")
        app.status = DeploymentStatus.FAILED
        app.error_message = str(e)
        await db.commit()
        raise


async def redeploy_app(
    app: App,
    zip_content: bytes,
    zip_path: str,
    env_vars: dict,
    db: AsyncSession,
) -> App:
    """Redeploy an existing app with new code."""
    settings = get_settings()
    image_tag = f"v{int(time.time())}"

    logger.info(f"Redeploying app {app.id}")

    if env_vars:
        app.env_vars = {**app.env_vars, **env_vars}

    app.status = DeploymentStatus.BUILDING
    app.image_tag = image_tag
    app.error_message = None
    await db.commit()

    try:
        # Auto-inject Procfile on redeploy too
        preflight = scan_zip(zip_path)
        upload_content = zip_content

        if preflight.needs_procfile and preflight.procfile_content:
            logger.info(f"[{app.id}] Auto-injecting Procfile on redeploy")
            with tempfile.NamedTemporaryFile(suffix=".zip", delete=False) as tmp:
                tmp.write(zip_content)
                tmp_path = tmp.name
            try:
                patched_path = inject_procfile_into_zip(
                    tmp_path,
                    preflight.procfile_content,
                    tmp_path + "_patched.zip",
                )
                with open(patched_path, "rb") as f:
                    upload_content = f.read()
            except Exception as e:
                logger.warning(f"Procfile injection failed on redeploy: {e}")
            finally:
                try:
                    os.unlink(tmp_path)
                except Exception:
                    pass

        s3_key = await aws.upload_zip_to_s3(upload_content, app.id)
        build_id = await aws.start_build(app.id, s3_key, image_tag)
        app.codebuild_build_id = build_id
        await db.commit()

        build_result = await aws.wait_for_build(build_id)
        if build_result["status"] != "succeeded":
            raise RuntimeError(
                f"Build failed: {build_result.get('error', 'Unknown error')}"
            )

        app.status = DeploymentStatus.DEPLOYING
        await db.commit()

        image_uri = f"{settings.ecr_base_url}/tutaia/apps/{app.id}:{image_tag}"
        task_def_arn = await aws.register_task_definition(
            app.id, image_uri, app.env_vars
        )
        app.ecs_task_definition_arn = task_def_arn

        await aws.update_ecs_service(app.id, task_def_arn)

        app.status = DeploymentStatus.RUNNING
        app.last_deployed_at = datetime.utcnow()
        await db.commit()
        await db.refresh(app)

        logger.info(f"Redeployment complete for app {app.id}")
        return app

    except Exception as e:
        logger.error(f"Redeployment failed for app {app.id}: {e}")
        app.status = DeploymentStatus.FAILED
        app.error_message = str(e)
        await db.commit()
        raise


async def delete_app(app: App, db: AsyncSession):
    """Fully remove a user app and all its AWS resources."""
    logger.info(f"Deleting app {app.id}")
    errors = []

    if app.ecs_service_name:
        try:
            await aws.delete_ecs_service(app.id)
        except Exception as e:
            errors.append(f"ECS service deletion failed: {e}")

    if app.alb_listener_rule_arn:
        try:
            await aws.delete_listener_rule(app.alb_listener_rule_arn)
        except Exception as e:
            errors.append(f"ALB rule deletion failed: {e}")

    if app.alb_target_group_arn:
        try:
            import asyncio
            await asyncio.sleep(2)
            await aws.delete_target_group(app.alb_target_group_arn)
        except Exception as e:
            errors.append(f"Target group deletion failed: {e}")

    await db.delete(app)
    await db.commit()

    if errors:
        logger.warning(f"App {app.id} deleted with errors: {errors}")
    else:
        logger.info(f"App {app.id} fully deleted")