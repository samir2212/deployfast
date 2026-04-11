import json
import os
import tempfile
from typing import Optional

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.config import get_settings
from app.database import get_db
from app.middleware.auth import get_current_user
from app.models.models import App, DeploymentStatus, User
from app.services import aws
from app.services.deployment import (
    delete_app,
    deploy_app,
    preflight_scan,
    redeploy_app,
)

router = APIRouter()

MAX_ZIP_SIZE = 100 * 1024 * 1024  # 100MB


# ─────────────────────────────────────────────
# Pre-flight scan endpoint
# Call this BEFORE deploy to show user what env
# vars their app needs
# ─────────────────────────────────────────────
@router.post("/scan")
async def scan_app(
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_user),
):
    """
    Scan a zip file before deploying.
    Returns: detected stack, required env vars, warnings.
    Frontend should call this first, show the user the
    required env vars form, then call /deploy.
    """
    content = await file.read()

    if len(content) > MAX_ZIP_SIZE:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail="File too large. Maximum size is 100MB.",
        )

    with tempfile.NamedTemporaryFile(suffix=".zip", delete=False) as tmp:
        tmp.write(content)
        tmp_path = tmp.name

    try:
        result = await preflight_scan(tmp_path)
        return result
    finally:
        os.unlink(tmp_path)


# ─────────────────────────────────────────────
# Deploy endpoint
# ─────────────────────────────────────────────
@router.post("/", status_code=status.HTTP_201_CREATED)
async def deploy(
    file: UploadFile = File(...),
    name: str = Form(...),
    subdomain: Optional[str] = Form(default=None),
    env_vars: Optional[str] = Form(default="{}"),  # JSON string
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Deploy a vibe-coded app.

    - file: zip of the app source code
    - name: display name for the app
    - subdomain: custom subdomain prefix (e.g. "my-app" -> my-app.ai-deploy.tutaia.com)
    - env_vars: JSON string of environment variables {"KEY": "value"}

    Returns the app record with live URL.
    Deployment is async - poll /api/apps/{id}/status for progress.
    """
    content = await file.read()

    if len(content) > MAX_ZIP_SIZE:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail="File too large. Maximum size is 100MB.",
        )

    # Parse env vars
    try:
        parsed_env_vars = json.loads(env_vars) if env_vars else {}
    except json.JSONDecodeError:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="env_vars must be valid JSON",
        )

    # Write zip to temp file for scanning
    with tempfile.NamedTemporaryFile(suffix=".zip", delete=False) as tmp:
        tmp.write(content)
        tmp_path = tmp.name

    # Validate custom subdomain if provided
    if subdomain:
        subdomain = subdomain.strip().lower()
        import re
        if not re.match(r'^[a-z0-9]([a-z0-9-]*[a-z0-9])?$', subdomain):
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="Subdomain must contain only lowercase letters, numbers, and hyphens. Cannot start or end with a hyphen.",
            )
        if len(subdomain) < 3 or len(subdomain) > 40:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="Subdomain must be between 3 and 40 characters.",
            )
        # Check uniqueness
        settings = get_settings()
        full_subdomain = f"{subdomain}.{settings.platform_domain}"
        existing = await db.execute(
            select(App).where(App.subdomain == full_subdomain)
        )
        if existing.scalar_one_or_none():
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"Subdomain '{subdomain}' is already taken. Please choose a different name.",
            )

    try:
        app = await deploy_app(
            user=current_user,
            app_name=name,
            zip_content=content,
            zip_path=tmp_path,
            env_vars=parsed_env_vars,
            custom_subdomain=subdomain or None,
            db=db,
        )
    finally:
        os.unlink(tmp_path)

    return _app_response(app)


# ─────────────────────────────────────────────
# Redeploy endpoint
# ─────────────────────────────────────────────
@router.post("/{app_id}/redeploy")
async def redeploy(
    app_id: str,
    file: UploadFile = File(...),
    env_vars: Optional[str] = Form(default=None),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Redeploy an existing app with new code.
    Same URL, new container. Data resets (ephemeral storage).
    """
    app = await _get_user_app(app_id, current_user, db)

    content = await file.read()
    if len(content) > MAX_ZIP_SIZE:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail="File too large.",
        )

    parsed_env_vars = {}
    if env_vars:
        try:
            parsed_env_vars = json.loads(env_vars)
        except json.JSONDecodeError:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="env_vars must be valid JSON",
            )

    with tempfile.NamedTemporaryFile(suffix=".zip", delete=False) as tmp:
        tmp.write(content)
        tmp_path = tmp.name

    try:
        app = await redeploy_app(
            app=app,
            zip_content=content,
            zip_path=tmp_path,
            env_vars=parsed_env_vars,
            db=db,
        )
    finally:
        os.unlink(tmp_path)

    return _app_response(app)


# ─────────────────────────────────────────────
# List apps
# ─────────────────────────────────────────────
@router.get("/")
async def list_apps(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """List all apps for the current user."""
    result = await db.execute(
        select(App)
        .where(App.user_id == current_user.id)
        .order_by(App.created_at.desc())
    )
    apps = result.scalars().all()
    return [_app_response(app) for app in apps]


# ─────────────────────────────────────────────
# Get app status + logs
# ─────────────────────────────────────────────
@router.get("/{app_id}")
async def get_app(
    app_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get app details and current deployment status."""
    app = await _get_user_app(app_id, current_user, db)
    return _app_response(app)


@router.get("/{app_id}/status")
async def get_app_status(
    app_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Poll this endpoint during deployment to get live status.
    Returns current status + ECS service health.
    """
    app = await _get_user_app(app_id, current_user, db)

    ecs_status = {}
    if app.ecs_service_name:
        ecs_status = await aws.get_service_status(app_id)

    return {
        "app_id": app.id,
        "status": app.status,
        "url": app.url,
        "ecs": ecs_status,
        "error": app.error_message,
        "last_deployed_at": (
            app.last_deployed_at.isoformat()
            if app.last_deployed_at
            else None
        ),
    }


@router.get("/{app_id}/logs")
async def get_app_logs(
    app_id: str,
    lines: int = 100,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get recent logs from a running app."""
    app = await _get_user_app(app_id, current_user, db)

    # If still building, return build logs
    if app.status == DeploymentStatus.BUILDING and app.codebuild_build_id:
        logs = await aws.get_build_logs(app.codebuild_build_id, lines)
        return {"source": "build", "logs": logs}

    # Otherwise return app runtime logs
    logs = await aws.get_app_logs(app_id, lines)
    return {"source": "runtime", "logs": logs}


# ─────────────────────────────────────────────
# Delete app
# ─────────────────────────────────────────────
@router.delete("/{app_id}", status_code=status.HTTP_204_NO_CONTENT)
async def remove_app(
    app_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Stop and permanently delete an app and all its AWS resources."""
    app = await _get_user_app(app_id, current_user, db)
    await delete_app(app, db)


# ─────────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────────

async def _get_user_app(
    app_id: str,
    user: User,
    db: AsyncSession,
) -> App:
    """Get an app by ID, ensuring it belongs to the current user."""
    result = await db.execute(
        select(App).where(App.id == app_id, App.user_id == user.id)
    )
    app = result.scalar_one_or_none()

    if not app:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="App not found",
        )
    return app


def _app_response(app: App) -> dict:
    """Serialize an App model to API response."""
    return {
        "id": app.id,
        "name": app.name,
        "url": app.url,
        "subdomain": app.subdomain,
        "status": app.status,
        "stack": None,  # Will add stack detection to model later
        "required_env_vars": app.required_env_vars,
        "error": app.error_message,
        "created_at": app.created_at.isoformat(),
        "last_deployed_at": (
            app.last_deployed_at.isoformat()
            if app.last_deployed_at
            else None
        ),
    }
