import pytest
import pytest_asyncio
from httpx import AsyncClient
from app.main import app
from app.database import get_db, engine
from app.models.user import User, UserRole
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker
import os


# Test database
TEST_DATABASE_URL = "sqlite+aiosqlite:///./test.db"
test_engine = create_async_engine(TEST_DATABASE_URL)
TestSessionLocal = sessionmaker(test_engine, class_=AsyncSession, expire_on_commit=False)


async def override_get_db():
    """Override database dependency for testing"""
    async with TestSessionLocal() as session:
        try:
            yield session
        finally:
            await session.close()


app.dependency_overrides[get_db] = override_get_db


@pytest_asyncio.fixture
async def async_client():
    """Create async test client"""
    async with AsyncClient(app=app, base_url="http://test") as ac:
        yield ac


@pytest_asyncio.fixture(autouse=True)
async def setup_test_db():
    """Setup and teardown test database"""
    # Create tables
    async with test_engine.begin() as conn:
        from app.database import Base
        await conn.run_sync(Base.metadata.create_all)
    
    yield
    
    # Clean up
    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    
    # Remove test database file
    if os.path.exists("./test.db"):
        os.remove("./test.db")


@pytest.mark.asyncio
async def test_register_user(async_client: AsyncClient):
    """Test user registration"""
    response = await async_client.post(
        "/api/auth/register",
        json={
            "email": "test@example.com",
            "password": "password123",
            "role": "victim"
        }
    )
    assert response.status_code == 200
    data = response.json()
    assert data["email"] == "test@example.com"
    assert data["role"] == "victim"
    assert "id" in data


@pytest.mark.asyncio
async def test_login_user(async_client: AsyncClient):
    """Test user login"""
    # First register a user
    await async_client.post(
        "/api/auth/register",
        json={
            "email": "test@example.com",
            "password": "password123",
            "role": "victim"
        }
    )
    
    # Then login
    response = await async_client.post(
        "/api/auth/login",
        json={
            "email": "test@example.com",
            "password": "password123"
        }
    )
    assert response.status_code == 200
    data = response.json()
    assert "access_token" in data
    assert data["token_type"] == "bearer"


@pytest.mark.asyncio
async def test_get_current_user(async_client: AsyncClient):
    """Test getting current user info"""
    # Register and login
    await async_client.post(
        "/api/auth/register",
        json={
            "email": "test@example.com",
            "password": "password123",
            "role": "officer"
        }
    )
    
    login_response = await async_client.post(
        "/api/auth/login",
        json={
            "email": "test@example.com",
            "password": "password123"
        }
    )
    token = login_response.json()["access_token"]
    
    # Get current user
    response = await async_client.get(
        "/api/auth/me",
        headers={"Authorization": f"Bearer {token}"}
    )
    assert response.status_code == 200
    data = response.json()
    assert data["email"] == "test@example.com"
    assert data["role"] == "officer"


@pytest.mark.asyncio
async def test_duplicate_email_registration(async_client: AsyncClient):
    """Test that duplicate email registration fails"""
    # Register first user
    await async_client.post(
        "/api/auth/register",
        json={
            "email": "test@example.com",
            "password": "password123",
            "role": "victim"
        }
    )
    
    # Try to register with same email
    response = await async_client.post(
        "/api/auth/register",
        json={
            "email": "test@example.com",
            "password": "different123",
            "role": "admin"
        }
    )
    assert response.status_code == 400
    assert "Email already registered" in response.json()["detail"]


@pytest.mark.asyncio
async def test_invalid_login(async_client: AsyncClient):
    """Test login with invalid credentials"""
    response = await async_client.post(
        "/api/auth/login",
        json={
            "email": "nonexistent@example.com",
            "password": "wrongpassword"
        }
    )
    assert response.status_code == 401
    assert "Incorrect email or password" in response.json()["detail"]
