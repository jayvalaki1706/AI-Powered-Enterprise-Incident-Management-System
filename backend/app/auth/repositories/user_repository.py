from uuid import UUID
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.user import User, RefreshToken


class UserRepository:
    """Data access layer for user-related operations."""

    def __init__(self, db: AsyncSession):
        self.db = db

    # ─── User CRUD ──────────────────────────────────────────────────────────────

    async def get_by_email(self, email: str) -> User | None:
        """Fetch a user by email address."""
        result = await self.db.execute(
            select(User).where(User.email == email)
        )
        return result.scalar_one_or_none()

    async def get_by_id(self, user_id: UUID) -> User | None:
        """Fetch a user by their UUID."""
        result = await self.db.execute(
            select(User).where(User.id == user_id)
        )
        return result.scalar_one_or_none()

    async def create(self, user: User) -> User:
        """Insert a new user into the database."""
        self.db.add(user)
        await self.db.flush()
        await self.db.refresh(user)
        return user

    async def update(self, user: User) -> User:
        """Persist changes to an existing user."""
        await self.db.flush()
        await self.db.refresh(user)
        return user

    async def get_all(self, skip: int = 0, limit: int = 100) -> list[User]:
        """Get a paginated list of users."""
        result = await self.db.execute(
            select(User).offset(skip).limit(limit).order_by(User.created_at.desc())
        )
        return result.scalars().all()

    async def delete(self, user: User) -> None:
        """Delete a user from the database."""
        await self.db.delete(user)
        await self.db.flush()

    # ─── Refresh Token Operations ───────────────────────────────────────────────

    async def save_refresh_token(self, token: RefreshToken) -> RefreshToken:
        """Store a new refresh token."""
        self.db.add(token)
        await self.db.flush()
        return token

    async def get_refresh_token(self, token: str) -> RefreshToken | None:
        """Get a valid (non-revoked) refresh token."""
        result = await self.db.execute(
            select(RefreshToken).where(
                RefreshToken.token == token,
                RefreshToken.is_revoked == False,
            )
        )
        return result.scalar_one_or_none()

    async def revoke_refresh_token(self, token: str) -> None:
        """Revoke a specific refresh token."""
        await self.db.execute(
            update(RefreshToken)
            .where(RefreshToken.token == token)
            .values(is_revoked=True)
        )
        await self.db.flush()

    async def revoke_all_user_tokens(self, user_id: UUID) -> None:
        """Revoke all refresh tokens for a user (e.g., on password change)."""
        await self.db.execute(
            update(RefreshToken)
            .where(
                RefreshToken.user_id == user_id,
                RefreshToken.is_revoked == False,
            )
            .values(is_revoked=True)
        )
        await self.db.flush()
