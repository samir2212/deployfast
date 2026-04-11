import logging
import httpx
from jose import jwt, JWTError
from fastapi import Depends, HTTPException, Header, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from typing import Optional
from functools import lru_cache

from app.config import get_settings
from app.models.models import User
from app.database import get_db

logger = logging.getLogger(__name__)
security = HTTPBearer(auto_error=False)

# Test user ID for bypassing auth during validation phase
TEST_USER_ID = "test_user_validation"
TEST_API_KEY = "tutaia-test-key-validation-only"


@lru_cache(maxsize=1)
def _get_jwks(jwks_url: str) -> dict:
    """Fetch and cache Clerk's public keys for JWT verification."""
    logger.info(f"Fetching JWKS from {jwks_url}")
    response = httpx.get(jwks_url, timeout=10)
    response.raise_for_status()
    return response.json()


def _get_clerk_jwks_url() -> str:
    """Derive the JWKS URL from the Clerk publishable key."""
    settings = get_settings()
    pk = settings.clerk_publishable_key
    # publishable key format: pk_test_<base64-encoded-domain>
    # or pk_live_<base64-encoded-domain>
    import base64
    encoded = pk.split("_", 2)[-1]  # get the part after pk_test_ or pk_live_
    # Add padding if needed
    padding = 4 - len(encoded) % 4
    if padding != 4:
        encoded += "=" * padding
    domain = base64.b64decode(encoded).decode("utf-8").rstrip("$")
    return f"https://{domain}/.well-known/jwks.json"


async def verify_clerk_token(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security),
    x_test_key: Optional[str] = Header(None),
) -> dict:
    """
    Verifies auth using JWKS-based JWT verification.
    During validation phase also supports test API key bypass.
    """
    # ── TEST BYPASS (remove before going live to real users) ──
    if x_test_key and x_test_key == TEST_API_KEY:
        logger.info("Test API key used - bypassing Clerk auth")
        return {
            "sub": TEST_USER_ID,
            "email": "test@tutaia.com",
        }

    # ── REAL CLERK AUTH via JWKS ──
    if not credentials:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated",
            headers={"WWW-Authenticate": "Bearer"},
        )

    token = credentials.credentials

    try:
        jwks_url = _get_clerk_jwks_url()
        jwks = _get_jwks(jwks_url)

        payload = jwt.decode(
            token,
            jwks,
            algorithms=["RS256"],
            options={"verify_aud": False},
        )

        user_id = payload.get("sub")
        if not user_id:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid token: no subject",
            )

        return payload

    except JWTError as e:
        logger.warning(f"JWT verification failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token",
            headers={"WWW-Authenticate": "Bearer"},
        )
    except httpx.HTTPError as e:
        logger.error(f"JWKS fetch failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Authentication service unavailable",
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Auth error: {e}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication failed",
        )


async def get_current_user(
    token_data: dict = Depends(verify_clerk_token),
    db: AsyncSession = Depends(get_db),
) -> User:
    """Gets or creates the current user from the verified token."""
    clerk_user_id = token_data.get("sub")
    email = token_data.get("email", "")

    if not clerk_user_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token claims",
        )

    result = await db.execute(
        select(User).where(User.id == clerk_user_id)
    )
    user = result.scalar_one_or_none()

    if not user:
        # Fetch real email from Clerk if user has a real Clerk ID
        if not email and not clerk_user_id.startswith("test_"):
            try:
                settings = get_settings()
                async with httpx.AsyncClient() as client:
                    r = await client.get(
                        f"https://api.clerk.com/v1/users/{clerk_user_id}",
                        headers={
                            "Authorization": f"Bearer {settings.clerk_secret_key}"
                        },
                        timeout=5.0,
                    )
                if r.status_code == 200:
                    user_data = r.json()
                    emails = user_data.get("email_addresses", [])
                    if emails:
                        email = emails[0].get("email_address", "")
            except Exception:
                pass

        user = User(id=clerk_user_id, email=email)
        db.add(user)
        await db.commit()
        await db.refresh(user)
        logger.info(f"New user: {email} ({clerk_user_id})")

    return user
