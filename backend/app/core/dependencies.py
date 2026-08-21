import logging
import redis.asyncio as aioredis
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.ext.asyncio import AsyncSession
from uuid import UUID

from app.core.config import get_settings
from app.db.database import get_db

settings = get_settings()
security = HTTPBearer()
logger = logging.getLogger("dependencies")


# ─── Redis Dependency ───────────────────────────────────────────────────────────

async def get_redis():
    """Provide an async Redis client. Returns None if Redis is unavailable."""
    try:
        client = aioredis.from_url(settings.REDIS_URL, decode_responses=True)
        await client.ping()  # Test connection
        try:
            yield client
        finally:
            await client.close()
    except Exception as e:
        logger.warning(f"Redis unavailable: {e}. Proceeding without cache.")
        yield None


# ─── Auth Dependencies ──────────────────────────────────────────────────────────

async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: AsyncSession = Depends(get_db),
):
    """Extract and validate the current user from JWT token."""
    from app.core.security import decode_token
    from app.auth.repositories.user_repository import UserRepository

    token = credentials.credentials
    payload = decode_token(token)

    if not payload or payload.get("type") != "access":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token",
        )

    repo = UserRepository(db)
    user = await repo.get_by_id(UUID(payload["sub"]))

    if not user or not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found or inactive",
        )

    return user


def require_role(*roles):
    """Dependency factory to enforce role-based access control."""
    async def role_checker(current_user=Depends(get_current_user)):
        if current_user.role not in roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Insufficient permissions",
            )
        return current_user
    return role_checker
