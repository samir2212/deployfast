import os
import uuid
import tempfile
import boto3
import structlog

from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session
from typing import Optional

from app.core.auth import get_current_user
from app.core.config import get_settings
from app.models.database import get_db, App, Deployment, DeploymentStatus, AppStatus
from app.services.deployment import deploy_app, scan_env_vars
from app.schemas.deploy import (
    PreflightResponse,
    DeployResponse,
    AppResponse,
    DeploymentResponse,
)

router = APIRouter(prefix="/api/v1", tags=["deployments"])
logger = structlog.get_logger()


# ─────────────────────────────────────────────
# Health check (no auth)
# ─────────────────────────────────────────────
@router.get("/health")
async def health():
    return {"status": "ok", "service": "tutaia-platform-api"}


# ─────────────────────────────────────────────
# Pre-flight: scan zip for required env vars
# before the user commits to a full deploy
# ─────────────────────────────────────────────
@router.post("/preflight", response_model=PreflightResponse)
async def preflight_check(
    file: UploadFile = File(...),
    user: dict = Depends(get_current_user),
):
    """
    Upload a zip, get back a list of env vars the app needs.
    Call this before /deploy to show the user what env vars to fill in.
    """
    if not file.filename.endswith(".zip"):
        raise HTTPException(400, "File must be a .zip archive")

    with tempfile.TemporaryDirectory() as tmp_dir:
        zip_path = os.path.join(tmp_dir, "app.zip")
        with open(zip_path, "wb") as f:
            content = await file.read()
            f.write(content)

        # Extract
        import zipfile
        project_dir = os.path.join(tmp_dir, "project")
        os.makedirs(project_dir)
        with zipfile.ZipFile(zip_path, "r") as zf:
            zf.extractall(project_dir)

        # Handle single root folder
        entries = os.listdir(project_dir)
        if len(entries) == 1 and os.path.isdir(
            os.path.join(project_dir, entries[0])
        ):
            project_dir = os.path.join(project_dir, entries[0])

        required_env_vars = scan_env_vars(project_dir)

    return PreflightResponse(
        required_env_vars=required_env_vars,
        message=(
            f"Found {len(required_env_vars)} environment variables your app needs."
            if required_env_vars
            else "No environment variables detected. Ready to deploy."
        ),
    )


# ─────────────────────────────────────────────
# Deploy: full pipeline
# ─────────────────────────────────────────────
@router.post("/deploy", response_model=DeployResponse)
async def deploy(
    file: UploadFile = File(...),
    app_name: str = Form(...),
    env_vars_json: str = Form(default="{}"),  # JSON string of env vars
    app_id: Optional[str] = Form(default=None),  # If redeploying
    user: dict = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Deploy an app from a zip file.

    - First deploy: omit app_id, a new one is generated
    - Redeploy: pass app_id to update existing app
    """
    settings = get_settings()

    if not file.filename.endswith(".zip"):
        raise HTTPException(400, "File must be a .zip archive")

    # Parse env vars
    import json
    try:
        env_vars = json.loads(env_vars_json)
    except json.JSONDecodeError:
        raise HTTPException(400, "env_vars_json must be valid JSON")

    # Check if redeploying
    existing_app = None
    if app_id:
        existing_app = db.query(App).filter(
            App.id == app_id,
            App.user_id == user["id"],
        ).first()
        if not existing_app:
            raise HTTPException(404, f"App {app_id} not found")
    else:
        # Generate a short, URL-friendly app ID
        app_id = str(uuid.uuid4())[:8]

    # Save uploaded zip to temp file
    with tempfile.NamedTemporaryFile(suffix=".zip", delete=False) as tmp:
        content = await file.read()

        # Validate file size (50MB max)
        if len(content) > 50 * 1024 * 1024:
            raise HTTPException(400, "File too large. Maximum size is 50MB.")

        tmp.write(content)
        zip_path = tmp.name

    try:
        result = await deploy_app(
            app_id=app_id,
            user_id=user["id"],
            app_name=app_name,
            zip_path=zip_path,
            env_vars=env_vars,
            db=db,
            existing_app=existing_app,
        )
        return DeployResponse(**result)

    finally:
        # Always clean up the temp zip
        if os.path.exists(zip_path):
            os.unlink(zip_path)


# ─────────────────────────────────────────────
# List user's apps
# ─────────────────────────────────────────────
@router.get("/apps", response_model=list[AppResponse])
async def list_apps(
    user: dict = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    apps = db.query(App).filter(
        App.user_id == user["id"],
        App.status != AppStatus.DELETED,
    ).order_by(App.created_at.desc()).all()

    settings = get_settings()
    return [
        AppResponse(
            id=app.id,
            name=app.name,
            url=f"https://{app.id}.{settings.platform_domain}",
            status=app.status,
            created_at=app.created_at.isoformat(),
        )
        for app in apps
    ]


# ─────────────────────────────────────────────
# Get deployment status
# ─────────────────────────────────────────────
@router.get("/apps/{app_id}/deployments", response_model=list[DeploymentResponse])
async def get_deployments(
    app_id: str,
    user: dict = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    # Verify ownership
    app = db.query(App).filter(
        App.id == app_id,
        App.user_id == user["id"],
    ).first()
    if not app:
        raise HTTPException(404, "App not found")

    deployments = db.query(Deployment).filter(
        Deployment.app_id == app_id,
    ).order_by(Deployment.created_at.desc()).limit(10).all()

    return [
        DeploymentResponse(
            id=d.id,
            status=d.status,
            created_at=d.created_at.isoformat(),
            deployed_at=d.deployed_at.isoformat() if d.deployed_at else None,
            error_message=d.error_message,
        )
        for d in deployments
    ]


# ─────────────────────────────────────────────
# Get app logs (last 100 lines)
# ─────────────────────────────────────────────
@router.get("/apps/{app_id}/logs")
async def get_logs(
    app_id: str,
    user: dict = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    settings = get_settings()

    app = db.query(App).filter(
        App.id == app_id,
        App.user_id == user["id"],
    ).first()
    if not app:
        raise HTTPException(404, "App not found")

    logs_client = boto3.client("logs", region_name=settings.aws_region)

    try:
        response = logs_client.filter_log_events(
            logGroupName=app.log_group,
            limit=100,
            startFromHead=False,
        )
        events = [
            {
                "timestamp": e["timestamp"],
                "message": e["message"],
            }
            for e in response.get("events", [])
        ]
        return {"app_id": app_id, "logs": events}

    except logs_client.exceptions.ResourceNotFoundException:
        return {"app_id": app_id, "logs": [], "message": "No logs yet"}


# ─────────────────────────────────────────────
# Delete app
# ─────────────────────────────────────────────
@router.delete("/apps/{app_id}")
async def delete_app(
    app_id: str,
    user: dict = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    settings = get_settings()

    app = db.query(App).filter(
        App.id == app_id,
        App.user_id == user["id"],
    ).first()
    if not app:
        raise HTTPException(404, "App not found")

    ecs = boto3.client("ecs", region_name=settings.aws_region)
    alb = boto3.client("elbv2", region_name=settings.aws_region)

    errors = []

    # Stop ECS service
    try:
        ecs.update_service(
            cluster=settings.ecs_cluster_name,
            service=f"tutaia-app-{app_id}",
            desiredCount=0,
        )
        ecs.delete_service(
            cluster=settings.ecs_cluster_name,
            service=f"tutaia-app-{app_id}",
        )
    except Exception as e:
        errors.append(f"ECS cleanup: {e}")

    # Remove ALB rule and target group
    try:
        if app.alb_rule_arn:
            alb.delete_rule(RuleArn=app.alb_rule_arn)
        if app.alb_tg_arn:
            alb.delete_target_group(TargetGroupArn=app.alb_tg_arn)
    except Exception as e:
        errors.append(f"ALB cleanup: {e}")

    # Mark as deleted in DB
    app.status = AppStatus.DELETED
    db.commit()

    return {
        "message": f"App {app_id} deleted",
        "warnings": errors if errors else None,
    }
