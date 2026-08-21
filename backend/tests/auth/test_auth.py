import pytest
from httpx import AsyncClient


@pytest.mark.auth
class TestRegistration:
    """Test user registration endpoints."""

    async def test_register_success(self, client: AsyncClient):
        response = await client.post("/api/v1/auth/register", json={
            "email": "new@test.com",
            "password": "SecurePass123!",
            "full_name": "New User",
            "role": "engineer",
        })
        assert response.status_code == 201
        data = response.json()
        assert data["email"] == "new@test.com"
        assert data["full_name"] == "New User"
        assert data["role"] == "engineer"
        assert data["is_active"] is True
        assert "id" in data

    async def test_register_duplicate_email(self, client: AsyncClient):
        user_data = {
            "email": "dup@test.com",
            "password": "SecurePass123!",
            "full_name": "User One",
        }
        await client.post("/api/v1/auth/register", json=user_data)
        response = await client.post("/api/v1/auth/register", json=user_data)
        assert response.status_code == 409

    async def test_register_invalid_email(self, client: AsyncClient):
        response = await client.post("/api/v1/auth/register", json={
            "email": "not-an-email",
            "password": "SecurePass123!",
            "full_name": "Bad Email",
        })
        assert response.status_code == 422

    async def test_register_short_password(self, client: AsyncClient):
        response = await client.post("/api/v1/auth/register", json={
            "email": "short@test.com",
            "password": "123",
            "full_name": "Short Pass",
        })
        assert response.status_code == 422


@pytest.mark.auth
class TestLogin:
    """Test login and token endpoints."""

    async def test_login_success(self, client: AsyncClient, registered_user):
        response = await client.post("/api/v1/auth/login", json={
            "email": registered_user["email"],
            "password": registered_user["password"],
        })
        assert response.status_code == 200
        data = response.json()
        assert "access_token" in data
        assert "refresh_token" in data
        assert data["token_type"] == "bearer"

    async def test_login_wrong_password(self, client: AsyncClient, registered_user):
        response = await client.post("/api/v1/auth/login", json={
            "email": registered_user["email"],
            "password": "WrongPassword123!",
        })
        assert response.status_code == 401

    async def test_login_nonexistent_email(self, client: AsyncClient):
        response = await client.post("/api/v1/auth/login", json={
            "email": "nobody@test.com",
            "password": "SomePass123!",
        })
        assert response.status_code == 401


@pytest.mark.auth
class TestTokenRefresh:
    """Test token refresh functionality."""

    async def test_refresh_token_success(self, client: AsyncClient, registered_user):
        # Login first
        login_response = await client.post("/api/v1/auth/login", json={
            "email": registered_user["email"],
            "password": registered_user["password"],
        })
        refresh_token = login_response.json()["refresh_token"]

        # Refresh
        response = await client.post("/api/v1/auth/refresh", json={
            "refresh_token": refresh_token,
        })
        assert response.status_code == 200
        data = response.json()
        assert "access_token" in data
        assert "refresh_token" in data
        # New refresh token should be different (rotation)
        assert data["refresh_token"] != refresh_token

    async def test_refresh_with_invalid_token(self, client: AsyncClient):
        response = await client.post("/api/v1/auth/refresh", json={
            "refresh_token": "invalid-token-string",
        })
        assert response.status_code == 401

    async def test_refresh_token_reuse_blocked(self, client: AsyncClient, registered_user):
        # Login
        login_response = await client.post("/api/v1/auth/login", json={
            "email": registered_user["email"],
            "password": registered_user["password"],
        })
        refresh_token = login_response.json()["refresh_token"]

        # Use refresh token once (should work)
        await client.post("/api/v1/auth/refresh", json={"refresh_token": refresh_token})

        # Use same refresh token again (should fail - revoked)
        response = await client.post("/api/v1/auth/refresh", json={"refresh_token": refresh_token})
        assert response.status_code == 401


@pytest.mark.auth
class TestProtectedEndpoints:
    """Test auth-protected endpoints."""

    async def test_get_me_authenticated(self, authenticated_client: AsyncClient, registered_user):
        response = await authenticated_client.get("/api/v1/auth/me")
        assert response.status_code == 200
        data = response.json()
        assert data["email"] == registered_user["email"]
        assert data["full_name"] == registered_user["full_name"]

    async def test_get_me_unauthenticated(self, client: AsyncClient):
        response = await client.get("/api/v1/auth/me")
        assert response.status_code == 403  # No Bearer token = forbidden

    async def test_get_me_invalid_token(self, client: AsyncClient):
        response = await client.get(
            "/api/v1/auth/me",
            headers={"Authorization": "Bearer invalid-token"},
        )
        assert response.status_code == 401


@pytest.mark.auth
class TestChangePassword:
    """Test password change functionality."""

    async def test_change_password_success(self, authenticated_client: AsyncClient, registered_user):
        response = await authenticated_client.post("/api/v1/auth/change-password", json={
            "old_password": registered_user["password"],
            "new_password": "NewSecurePass456!",
        })
        assert response.status_code == 200

    async def test_change_password_wrong_old(self, authenticated_client: AsyncClient):
        response = await authenticated_client.post("/api/v1/auth/change-password", json={
            "old_password": "WrongOldPassword!",
            "new_password": "NewSecurePass456!",
        })
        assert response.status_code == 400


@pytest.mark.auth
class TestRBAC:
    """Test role-based access control."""

    async def test_list_users_as_admin(self, client: AsyncClient, admin_headers):
        response = await client.get("/api/v1/auth/users", headers=admin_headers)
        assert response.status_code == 200
        assert isinstance(response.json(), list)

    async def test_list_users_as_engineer(self, authenticated_client: AsyncClient):
        response = await authenticated_client.get("/api/v1/auth/users")
        assert response.status_code == 403
