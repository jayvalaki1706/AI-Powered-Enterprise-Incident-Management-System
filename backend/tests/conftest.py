import pytest
import asyncio
from uuid import uuid4
from httpx import AsyncClient, ASGITransport
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker

from app.main import app
from app.db.database import Base, get_db
from app.core.config import get_settings

settings = get_settings()

# Use a separate test database
TEST_DATABASE_URL = settings.DATABASE_URL.replace(
    "/incident_management", "/incident_management_test"
)

engine_test = create_async_engine(TEST_DATABASE_URL, echo=False)
TestSessionLocal = async_sessionmaker(
    engine_test, class_=AsyncSession, expire_on_commit=False
)


# ─── Override DB dependency ──────────────────────────────────────────────────────

async def override_get_db():
    async with TestSessionLocal() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()


app.dependency_overrides[get_db] = override_get_db


# ─── Fixtures ────────────────────────────────────────────────────────────────────

@pytest.fixture(scope="session")
def event_loop():
    """Create an event loop for the test session."""
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()


@pytest.fixture(autouse=True)
async def setup_db():
    """Create tables before each test and drop after."""
    async with engine_test.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield
    async with engine_test.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)


@pytest.fixture
async def client():
    """Async HTTP client for testing endpoints."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac


@pytest.fixture
async def test_user_data():
    """Standard test user data."""
    return {
        "email": f"test_{uuid4().hex[:8]}@test.com",
        "password": "TestPass123!",
        "full_name": "Test User",
        "role": "engineer",
    }


@pytest.fixture
async def registered_user(client, test_user_data):
    """Register a user and return their data."""
    response = await client.post("/api/v1/auth/register", json=test_user_data)
    assert response.status_code == 201
    return {**test_user_data, "id": response.json()["id"]}


@pytest.fixture
async def auth_headers(client, registered_user):
    """Get auth headers for a registered user."""
    response = await client.post("/api/v1/auth/login", json={
        "email": registered_user["email"],
        "password": registered_user["password"],
    })
    assert response.status_code == 200
    token = response.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture
async def authenticated_client(client, auth_headers):
    """Client with auth headers pre-set."""
    client.headers.update(auth_headers)
    return client


@pytest.fixture
async def admin_user_data():
    """Admin user data."""
    return {
        "email": f"admin_{uuid4().hex[:8]}@test.com",
        "password": "AdminPass123!",
        "full_name": "Admin User",
        "role": "admin",
    }


@pytest.fixture
async def admin_headers(client, admin_user_data):
    """Get auth headers for an admin user."""
    await client.post("/api/v1/auth/register", json=admin_user_data)
    response = await client.post("/api/v1/auth/login", json={
        "email": admin_user_data["email"],
        "password": admin_user_data["password"],
    })
    token = response.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}
