import httpx
from jose import jwt, JWTError
from fastapi import HTTPException, Security, Depends
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from app.core.config import get_settings
from functools import lru_cache
import structlog

logger = structlog.get_logger()
security = HTTPBearer()


@lru_cache(maxsize=1)
def get_jwks() -> dict:
    """
    Fetch Clerk's public keys for JWT verification.
    Cached — only fetches once per process startup.
    Keys rarely change; restart service to refresh.
    """
    settings = get_settings()
    response = httpx.get(settings.clerk_jwks_url, timeout=10)
    response.raise_for_status()
    return response.json()


def verify_clerk_token(
    credentials: HTTPAuthorizationCredentials = Security(security),
) -> dict:
    """
    Verify a Clerk JWT token.
    Returns the decoded token payload (contains user_id, email, etc.)
    Raises 401 if token is invalid or expired.
    """
    settings = get_settings()
    token = credentials.credentials

    try:
        jwks = get_jwks()

        # Decode and verify the JWT
        payload = jwt.decode(
            token,
            jwks,
            algorithms=["RS256"],
            options={"verify_aud": False},  # Clerk doesn't use standard aud
        )

        # Clerk user ID is in the 'sub' claim
        user_id = payload.get("sub")
        if not user_id:
            raise HTTPException(status_code=401, detail="Invalid token: no subject")

        return payload

    except JWTError as e:
        logger.warning("jwt_verification_failed", error=str(e))
        raise HTTPException(status_code=401, detail="Invalid or expired token")
    except httpx.HTTPError as e:
        logger.error("clerk_jwks_fetch_failed", error=str(e))
        raise HTTPException(status_code=503, detail="Auth service unavailable")


def get_current_user(
    payload: dict = Depends(verify_clerk_token),
) -> dict:
    """
    Extract current user info from verified JWT payload.
    Use this as a dependency in any protected route.

    Usage:
        @router.post("/deploy")
        async def deploy(user: dict = Depends(get_current_user)):
            user_id = user["id"]
    """
    return {
        "id": payload["sub"],
        "email": payload.get("email", ""),
        # Clerk puts email in different places depending on config
        "email_verified": payload.get("email_verified", False),
    }
