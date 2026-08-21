from uuid import UUID
from datetime import datetime, timedelta
from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.repositories.user_repository import UserRepository
from app.auth.schemas import UserCreate, UserLogin, UserUpdate, ProfileUpdate, ChangePasswordRequest, TokenResponse
from app.models.user import User, RefreshToken, UserRole
from app.core.security import (
    hash_password,
    verify_password,
    create_access_token,
    create_refresh_token,
    create_reset_token,
    decode_token,
)
from app.core.config import get_settings

settings = get_settings()


class AuthService:
    """Business logic layer for authentication operations."""

    def __init__(self, db: AsyncSession):
        self.repository = UserRepository(db)

    # ─── Registration ───────────────────────────────────────────────────────────

    async def register(self, data: UserCreate) -> User:
        """Register a new user."""
        existing = await self.repository.get_by_email(data.email)
        if existing:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Email already registered",
            )

        user = User(
            email=data.email,
            hashed_password=hash_password(data.password),
            full_name=data.full_name,
            role=data.role,
        )
        return await self.repository.create(user)

    # ─── Login ──────────────────────────────────────────────────────────────────

    async def login(self, data: UserLogin) -> TokenResponse:
        """Authenticate user and return access + refresh tokens."""
        user = await self.repository.get_by_email(data.email)
        if not user or not verify_password(data.password, user.hashed_password):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid email or password",
            )

        if not user.is_active:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Account is disabled. Contact an administrator.",
            )

        return await self._generate_tokens(user)

    # ─── Refresh Token ──────────────────────────────────────────────────────────

    async def refresh_tokens(self, refresh_token: str) -> TokenResponse:
        """Issue new token pair using a valid refresh token (rotation)."""
        payload = decode_token(refresh_token)
        if not payload or payload.get("type") != "refresh":
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid refresh token",
            )

        # Check token exists and is not revoked
        token_record = await self.repository.get_refresh_token(refresh_token)
        if not token_record:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Refresh token has been revoked or does not exist",
            )

        # Check expiration
        if token_record.expires_at < datetime.utcnow():
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Refresh token has expired",
            )

        # Revoke old refresh token (token rotation)
        await self.repository.revoke_refresh_token(refresh_token)

        # Get user and generate new tokens
        user = await self.repository.get_by_id(token_record.user_id)
        if not user or not user.is_active:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="User not found or inactive",
            )

        return await self._generate_tokens(user)

    # ─── Logout ─────────────────────────────────────────────────────────────────

    async def logout(self, refresh_token: str) -> None:
        """Revoke the refresh token on logout."""
        await self.repository.revoke_refresh_token(refresh_token)

    # ─── Get Current User ───────────────────────────────────────────────────────

    async def get_current_user(self, user_id: UUID) -> User:
        """Get user by ID."""
        user = await self.repository.get_by_id(user_id)
        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found",
            )
        return user

    # ─── Change Password ────────────────────────────────────────────────────────

    async def change_password(self, user_id: UUID, data: ChangePasswordRequest) -> None:
        """Change user password and revoke all existing refresh tokens."""
        user = await self.repository.get_by_id(user_id)
        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found",
            )

        if not verify_password(data.old_password, user.hashed_password):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Current password is incorrect",
            )

        user.hashed_password = hash_password(data.new_password)
        await self.repository.update(user)

        # Revoke all refresh tokens for security
        await self.repository.revoke_all_user_tokens(user_id)

    # ─── Update Profile (Self) ─────────────────────────────────────────────────

    async def update_profile(self, user_id: UUID, data: ProfileUpdate) -> User:
        """Update own profile (name and timezone only)."""
        user = await self.repository.get_by_id(user_id)
        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found",
            )

        for field, value in data.model_dump(exclude_unset=True).items():
            setattr(user, field, value)

        return await self.repository.update(user)

    # ─── Update User (Admin) ───────────────────────────────────────────────────

    async def update_user(self, user_id: UUID, data: UserUpdate) -> User:
        """Update user fields (admin operation)."""
        user = await self.repository.get_by_id(user_id)
        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found",
            )

        for field, value in data.model_dump(exclude_unset=True).items():
            setattr(user, field, value)

        return await self.repository.update(user)

    # ─── List Users (Admin) ─────────────────────────────────────────────────────

    async def list_users(self, skip: int = 0, limit: int = 100) -> list[User]:
        """Get paginated list of all users."""
        return await self.repository.get_all(skip=skip, limit=limit)

    # ─── Delete User (Admin) ────────────────────────────────────────────────────

    async def delete_user(self, user_id: UUID, current_user_id: UUID) -> None:
        """Delete (deactivate) a user. Admin cannot delete themselves."""
        if user_id == current_user_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="You cannot delete your own account",
            )

        user = await self.repository.get_by_id(user_id)
        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found",
            )

        # Revoke all tokens so the user is logged out immediately
        await self.repository.revoke_all_user_tokens(user_id)

        # Soft delete — deactivate the user (preserves FK references)
        user.is_active = False
        await self.repository.update(user)

    # ─── Forgot Password ───────────────────────────────────────────────────────

    async def forgot_password(self, email: str) -> dict:
        """Generate a password reset token for the given email.
        
        In production, this would send an email with the reset link.
        For testing, we return the token directly in the response.
        """
        user = await self.repository.get_by_email(email)
        if not user:
            # Don't reveal whether email exists - always return success
            return {"message": "If an account with that email exists, a reset link has been sent.", "reset_token": None}

        if not user.is_active:
            return {"message": "If an account with that email exists, a reset link has been sent.", "reset_token": None}

        # Generate a reset token (JWT with 15 min expiry and type='reset')
        reset_token = create_reset_token(
            data={"sub": str(user.id)},
        )

        # In production: send email with reset link containing this token
        # For testing: return the token in the response
        return {
            "message": "If an account with that email exists, a reset link has been sent.",
            "reset_token": reset_token,  # Remove in production - only for testing
        }

    # ─── Reset Password ─────────────────────────────────────────────────────────

    async def reset_password(self, token: str, new_password: str) -> None:
        """Validate the reset token and update the user's password."""
        payload = decode_token(token)
        if not payload:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid or expired reset token",
            )

        # Verify this is a reset token (type is embedded in the JWT data, not the standard 'type' field)
        token_type = payload.get("type")
        if token_type != "reset":
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid token type",
            )

        user_id = payload.get("sub")
        if not user_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid reset token",
            )

        user = await self.repository.get_by_id(UUID(user_id))
        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found",
            )

        if not user.is_active:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Account is disabled",
            )

        # Update password
        user.hashed_password = hash_password(new_password)
        await self.repository.update(user)

        # Revoke all refresh tokens for security
        await self.repository.revoke_all_user_tokens(user.id)

    # ─── Private Helpers ────────────────────────────────────────────────────────

    async def _generate_tokens(self, user: User) -> TokenResponse:
        """Generate access + refresh tokens and store refresh token in DB."""
        access_token = create_access_token(
            data={"sub": str(user.id), "role": user.role.value}
        )
        refresh_token = create_refresh_token(
            data={"sub": str(user.id)}
        )

        # Persist refresh token
        token_record = RefreshToken(
            token=refresh_token,
            user_id=user.id,
            expires_at=datetime.utcnow() + timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS),
        )
        await self.repository.save_refresh_token(token_record)

        return TokenResponse(access_token=access_token, refresh_token=refresh_token)
