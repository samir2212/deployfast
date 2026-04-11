from fastapi import APIRouter, Depends

from app.config import get_settings
from app.middleware.auth import get_current_user
from app.models.models import User

router = APIRouter()


@router.get("/config")
async def auth_config():
    """
    Returns Clerk publishable key for frontend initialization.
    Publishable key is safe to expose - it's designed for frontend use.
    """
    settings = get_settings()
    return {
        "publishable_key": settings.clerk_publishable_key,
    }


@router.get("/me")
async def get_me(current_user: User = Depends(get_current_user)):
    """Returns the current authenticated user's profile."""
    return {
        "id": current_user.id,
        "email": current_user.email,
        "created_at": current_user.created_at.isoformat(),
    }
