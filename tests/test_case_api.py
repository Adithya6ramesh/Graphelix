import pytest
import pytest_asyncio
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession
from app.main import app
from app.models import User, UserRole, Case, CaseEvent
from app.database import get_db
from tests.test_auth import test_engine, TestSessionLocal, override_get_db
from sqlalchemy import select

app.dependency_overrides[get_db] = override_get_db


@pytest_asyncio.fixture
async def async_client():
    """Create async test client"""
    async with AsyncClient(app=app, base_url="http://test") as ac:
        yield ac


@pytest_asyncio.fixture(autouse=True)
async def setup_test_db():
    """Setup and teardown test database"""
    async with test_engine.begin() as conn:
        from app.database import Base
        await conn.run_sync(Base.metadata.create_all)
    
    yield
    
    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)


@pytest_asyncio.fixture
async def victim_token(async_client: AsyncClient):
    """Create victim user and return auth token"""
    # Register victim
    await async_client.post(
        "/api/auth/register",
        json={
            "email": "victim@example.com",
            "password": "password123",
            "role": "victim"
        }
    )
    
    # Login and get token
    response = await async_client.post(
        "/api/auth/login",
        json={
            "email": "victim@example.com",
            "password": "password123"
        }
    )
    return response.json()["access_token"]


@pytest_asyncio.fixture
async def officer_token(async_client: AsyncClient):
    """Create officer user and return auth token"""
    # Register officer
    await async_client.post(
        "/api/auth/register",
        json={
            "email": "officer@example.com",
            "password": "password123",
            "role": "officer"
        }
    )
    
    # Login and get token
    response = await async_client.post(
        "/api/auth/login",
        json={
            "email": "officer@example.com",
            "password": "password123"
        }
    )
    return response.json()["access_token"]


@pytest.mark.asyncio
async def test_submit_case_with_url(async_client: AsyncClient, victim_token: str):
    """Test submitting a case with URL"""
    response = await async_client.post(
        "/api/cases/",
        json={
            "url": "https://example.com/harmful-content",
            "description": "This content is harmful and should be removed"
        },
        headers={"Authorization": f"Bearer {victim_token}"}
    )
    
    assert response.status_code == 201
    data = response.json()
    assert data["existing"] is False
    assert data["message"] == "Case submitted successfully"
    assert data["case"]["url"] == "https://example.com/harmful-content"
    assert data["case"]["state"] == "submitted"
    assert data["case_id"] is not None


@pytest.mark.asyncio
async def test_submit_case_with_file_hash(async_client: AsyncClient, victim_token: str):
    """Test submitting a case with file hash"""
    file_hash = "a" * 64  # Valid SHA256
    response = await async_client.post(
        "/api/cases/",
        json={
            "file_hash": file_hash,
            "description": "Harmful file reported by hash"
        },
        headers={"Authorization": f"Bearer {victim_token}"}
    )
    
    assert response.status_code == 201
    data = response.json()
    assert data["existing"] is False
    assert data["case"]["file_hash"] == file_hash
    assert data["case"]["url"] in [None, ""]  # URL can be None or empty string


@pytest.mark.asyncio
async def test_submit_case_with_both_url_and_file_hash(async_client: AsyncClient, victim_token: str):
    """Test submitting a case with both URL and file hash"""
    file_hash = "b" * 64
    response = await async_client.post(
        "/api/cases/",
        json={
            "url": "https://example.com/page",
            "file_hash": file_hash,
            "description": "Content with both URL and file hash"
        },
        headers={"Authorization": f"Bearer {victim_token}"}
    )
    
    assert response.status_code == 201
    data = response.json()
    assert data["case"]["url"] == "https://example.com/page"
    assert data["case"]["file_hash"] == file_hash


@pytest.mark.asyncio
async def test_submit_case_no_content(async_client: AsyncClient, victim_token: str):
    """Test submitting a case without URL or file hash"""
    response = await async_client.post(
        "/api/cases/",
        json={
            "description": "No content provided"
        },
        headers={"Authorization": f"Bearer {victim_token}"}
    )
    
    assert response.status_code == 400
    assert "Either URL or file_hash must be provided" in response.json()["detail"]


@pytest.mark.asyncio
async def test_submit_case_duplicate_url(async_client: AsyncClient, victim_token: str):
    """Test that duplicate URLs are detected"""
    url = "https://example.com/duplicate-test"
    
    # Submit first case
    response1 = await async_client.post(
        "/api/cases/",
        json={"url": url, "description": "First submission"},
        headers={"Authorization": f"Bearer {victim_token}"}
    )
    assert response1.status_code == 201
    case1_id = response1.json()["case_id"]
    
    # Submit duplicate
    response2 = await async_client.post(
        "/api/cases/",
        json={"url": url, "description": "Second submission"},
        headers={"Authorization": f"Bearer {victim_token}"}
    )
    assert response2.status_code == 200  # 200 for existing case
    data2 = response2.json()
    assert data2["existing"] is True
    assert data2["case_id"] == case1_id
    assert "duplicate content detected" in data2["message"]


@pytest.mark.asyncio
async def test_submit_case_with_idempotency_key(async_client: AsyncClient, victim_token: str):
    """Test idempotency key functionality"""
    idem_key = "client-request-456"
    
    # Submit first request
    response1 = await async_client.post(
        "/api/cases/",
        json={
            "url": "https://example.com/idempotent",
            "description": "Test idempotency",
            "idempotency_key": idem_key
        },
        headers={"Authorization": f"Bearer {victim_token}"}
    )
    assert response1.status_code == 201
    case1_id = response1.json()["case_id"]
    
    # Submit same request again with same idempotency key
    response2 = await async_client.post(
        "/api/cases/",
        json={
            "url": "https://different.com/url",  # Different URL
            "description": "Different description",
            "idempotency_key": idem_key  # Same key
        },
        headers={"Authorization": f"Bearer {victim_token}"}
    )
    assert response2.status_code == 200
    assert response2.json()["case_id"] == case1_id


@pytest.mark.asyncio
async def test_submit_case_invalid_file_hash(async_client: AsyncClient, victim_token: str):
    """Test submitting case with invalid file hash"""
    response = await async_client.post(
        "/api/cases/",
        json={
            "file_hash": "invalid-hash",
            "description": "Invalid file hash"
        },
        headers={"Authorization": f"Bearer {victim_token}"}
    )
    
    assert response.status_code == 400
    assert "Either URL or file_hash must be provided" in response.json()["detail"]


@pytest.mark.asyncio
async def test_submit_case_normalized_url_dedup(async_client: AsyncClient, victim_token: str):
    """Test that URLs that normalize to the same thing are deduplicated"""
    url1 = "https://example.com/page?utm_source=google&important=keep"
    url2 = "HTTPS://EXAMPLE.COM/page/?important=keep&utm_medium=cpc"
    
    # Submit first case
    response1 = await async_client.post(
        "/api/cases/",
        json={"url": url1},
        headers={"Authorization": f"Bearer {victim_token}"}
    )
    assert response1.status_code == 201
    case1_id = response1.json()["case_id"]
    
    # Submit equivalent URL
    response2 = await async_client.post(
        "/api/cases/",
        json={"url": url2},
        headers={"Authorization": f"Bearer {victim_token}"}
    )
    assert response2.status_code == 200
    assert response2.json()["case_id"] == case1_id


@pytest.mark.asyncio
async def test_submit_case_unauthorized(async_client: AsyncClient):
    """Test submitting case without authentication"""
    response = await async_client.post(
        "/api/cases/",
        json={
            "url": "https://example.com/test",
            "description": "Unauthorized submission"
        }
    )
    
    assert response.status_code == 403  # FastAPI returns 403 for missing auth


@pytest.mark.asyncio
async def test_get_case_by_submitter(async_client: AsyncClient, victim_token: str):
    """Test that victim can view their own case"""
    # Submit a case
    submit_response = await async_client.post(
        "/api/cases/",
        json={
            "url": "https://example.com/test-case",
            "description": "Test case for viewing"
        },
        headers={"Authorization": f"Bearer {victim_token}"}
    )
    case_id = submit_response.json()["case_id"]
    
    # View the case
    response = await async_client.get(
        f"/api/cases/{case_id}",
        headers={"Authorization": f"Bearer {victim_token}"}
    )
    
    assert response.status_code == 200
    data = response.json()
    assert data["case"]["id"] == case_id
    assert data["case"]["url"] == "https://example.com/test-case"
    assert len(data["events"]) >= 1  # Should have at least submission event
    assert data["total_events"] >= 1


@pytest.mark.asyncio
async def test_get_case_by_officer(async_client: AsyncClient, victim_token: str, officer_token: str):
    """Test that officer can view any case"""
    # Submit a case as victim
    submit_response = await async_client.post(
        "/api/cases/",
        json={
            "url": "https://example.com/officer-test",
            "description": "Case for officer viewing"
        },
        headers={"Authorization": f"Bearer {victim_token}"}
    )
    case_id = submit_response.json()["case_id"]
    
    # View the case as officer
    response = await async_client.get(
        f"/api/cases/{case_id}",
        headers={"Authorization": f"Bearer {officer_token}"}
    )
    
    assert response.status_code == 200
    data = response.json()
    assert data["case"]["id"] == case_id


@pytest.mark.asyncio
async def test_get_case_access_denied(async_client: AsyncClient, victim_token: str):
    """Test that victim cannot view other victims' cases"""
    # Create another victim
    await async_client.post(
        "/api/auth/register",
        json={
            "email": "victim2@example.com",
            "password": "password123",
            "role": "victim"
        }
    )
    
    login_response = await async_client.post(
        "/api/auth/login",
        json={
            "email": "victim2@example.com",
            "password": "password123"
        }
    )
    victim2_token = login_response.json()["access_token"]
    
    # Submit case as victim2
    submit_response = await async_client.post(
        "/api/cases/",
        json={
            "url": "https://example.com/private-case",
            "description": "Private case"
        },
        headers={"Authorization": f"Bearer {victim2_token}"}
    )
    case_id = submit_response.json()["case_id"]
    
    # Try to view as first victim (should be denied)
    response = await async_client.get(
        f"/api/cases/{case_id}",
        headers={"Authorization": f"Bearer {victim_token}"}
    )
    
    assert response.status_code == 403
    assert "You can only view cases you submitted" in response.json()["detail"]


@pytest.mark.asyncio
async def test_get_nonexistent_case(async_client: AsyncClient, victim_token: str):
    """Test getting a case that doesn't exist"""
    response = await async_client.get(
        "/api/cases/nonexistent-case-id",
        headers={"Authorization": f"Bearer {victim_token}"}
    )
    
    assert response.status_code == 404
    assert "Case not found" in response.json()["detail"]


@pytest.mark.asyncio
async def test_rate_limiting(async_client: AsyncClient, victim_token: str):
    """Test rate limiting on case submission"""
    # This test might be flaky due to timing, but it demonstrates the concept
    # In a real implementation, you'd mock the rate limiter
    
    # Submit multiple cases rapidly
    for i in range(12):  # More than the limit of 10
        response = await async_client.post(
            "/api/cases/",
            json={
                "url": f"https://example.com/rate-limit-test-{i}",
                "description": f"Rate limit test {i}"
            },
            headers={"Authorization": f"Bearer {victim_token}"}
        )
        
        if i < 10:
            assert response.status_code in [200, 201]  # Should succeed
        else:
            assert response.status_code == 429  # Should be rate limited
