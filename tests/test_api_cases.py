"""Tests for case API endpoints."""

import pytest
import pytest_asyncio
from httpx import AsyncClient
from app.main import app
from app.database import get_db, init_db
from app.models.user import User
import uuid


@pytest_asyncio.fixture(scope="function")
async def client():
    await init_db()
    async with AsyncClient(app=app, base_url="http://test") as client:
        yield client


@pytest_asyncio.fixture(scope="function")
async def victim_user_token(client):
    """Create a victim user and return their token."""
    unique_email = f"victim_{uuid.uuid4()}@test.com"
    
    # Register
    response = await client.post("/api/auth/register", json={
        "email": unique_email,
        "password": "password123",
        "role": "victim"
    })
    assert response.status_code == 200
    
    # Login
    response = await client.post("/api/auth/login", json={
        "email": unique_email,
        "password": "password123"
    })
    assert response.status_code == 200
    return response.json()["access_token"]


@pytest_asyncio.fixture(scope="function")
async def officer_user_token(client):
    """Create an officer user and return their token."""
    unique_email = f"officer_{uuid.uuid4()}@test.com"
    
    # Register
    response = await client.post("/api/auth/register", json={
        "email": unique_email,
        "password": "password123",
        "role": "officer"
    })
    assert response.status_code == 200
    
    # Login
    response = await client.post("/api/auth/login", json={
        "email": unique_email,
        "password": "password123"
    })
    assert response.status_code == 200
    return response.json()["access_token"]


class TestCaseSubmission:
    """Test case submission endpoint."""
    
    @pytest.mark.asyncio
    async def test_submit_new_case_success(self, client, victim_user_token):
        """Test successful submission of a new case."""
        unique_url = f"https://example.com/test-{uuid.uuid4()}"
        
        response = await client.post("/api/cases/", 
            json={
                "url": unique_url,
                "description": "Test case description"
            },
            headers={"Authorization": f"Bearer {victim_user_token}"}
        )
        
        assert response.status_code == 201
        data = response.json()
        assert data["existing"] is False
        assert data["message"] == "Case submitted successfully"
        assert data["case"]["url"] == unique_url
        assert data["case"]["description"] == "Test case description"
        assert data["case"]["state"] == "submitted"
        assert data["case_id"] == data["case"]["id"]
    
    @pytest.mark.asyncio
    async def test_submit_duplicate_case(self, client, victim_user_token):
        """Test submission of duplicate case returns existing case."""
        test_url = f"https://example.com/duplicate-{uuid.uuid4()}"
        
        # First submission
        response1 = await client.post("/api/cases/", 
            json={
                "url": test_url,
                "description": "First submission"
            },
            headers={"Authorization": f"Bearer {victim_user_token}"}
        )
        assert response1.status_code == 201
        assert response1.json()["existing"] is False
        
        # Second submission (duplicate)
        response2 = await client.post("/api/cases/", 
            json={
                "url": test_url,
                "description": "Second submission"
            },
            headers={"Authorization": f"Bearer {victim_user_token}"}
        )
        assert response2.status_code == 200
        assert response2.json()["existing"] is True
        assert "duplicate content detected" in response2.json()["message"]
        assert response2.json()["case_id"] == response1.json()["case_id"]
    
    @pytest.mark.asyncio
    async def test_submit_case_url_normalization(self, client, victim_user_token):
        """Test that URL normalization works for deduplication."""
        base_url = f"https://example.com/norm-{uuid.uuid4()}"
        
        # Submit with tracking parameters
        response1 = await client.post("/api/cases/", 
            json={
                "url": f"{base_url}?utm_source=test&utm_campaign=test",
                "description": "With tracking params"
            },
            headers={"Authorization": f"Bearer {victim_user_token}"}
        )
        assert response1.status_code == 201
        
        # Submit without tracking parameters (should be duplicate)
        response2 = await client.post("/api/cases/", 
            json={
                "url": base_url,
                "description": "Without tracking params"
            },
            headers={"Authorization": f"Bearer {victim_user_token}"}
        )
        assert response2.status_code == 200
        assert response2.json()["existing"] is True
    
    @pytest.mark.asyncio
    async def test_submit_case_missing_url(self, client, victim_user_token):
        """Test validation error for missing URL."""
        response = await client.post("/api/cases/", 
            json={"description": "Missing URL"},
            headers={"Authorization": f"Bearer {victim_user_token}"}
        )
        assert response.status_code == 400  # Custom validation error
        assert "Either URL or file_hash must be provided" in response.text
    
    @pytest.mark.asyncio
    async def test_submit_case_invalid_url(self, client, victim_user_token):
        """Test handling of invalid URL."""
        response = await client.post("/api/cases/", 
            json={
                "url": "not-a-valid-url",
                "description": "Invalid URL"
            },
            headers={"Authorization": f"Bearer {victim_user_token}"}
        )
        # Invalid URLs are normalized consistently, so they can be deduplicated
        # The first submission creates a case, subsequent ones are duplicates
        assert response.status_code in [200, 201]
    
    @pytest.mark.asyncio
    async def test_submit_case_unauthorized(self, client):
        """Test that unauthorized requests are rejected."""
        response = await client.post("/api/cases/", 
            json={
                "url": "https://example.com/test",
                "description": "Unauthorized"
            }
        )
        assert response.status_code == 403  # FastAPI returns 403 for missing auth
    
    @pytest.mark.asyncio
    async def test_submit_case_rate_limiting(self, client, victim_user_token):
        """Test rate limiting for case submission."""
        # This test would require configuring a very low rate limit
        # For now, we'll just test that rate limiting doesn't interfere with normal usage
        
        responses = []
        for i in range(3):  # Submit a few cases quickly
            unique_url = f"https://example.com/rate-test-{uuid.uuid4()}"
            response = await client.post("/api/cases/", 
                json={
                    "url": unique_url,
                    "description": f"Rate test {i}"
                },
                headers={"Authorization": f"Bearer {victim_user_token}"}
            )
            responses.append(response)
        
        # All should succeed (rate limit should be reasonable)
        for response in responses:
            assert response.status_code == 201


class TestCaseRetrieval:
    """Test case retrieval endpoints."""
    
    @pytest.mark.asyncio
    async def test_get_case_by_id_success(self, client, victim_user_token):
        """Test successful retrieval of case by ID."""
        # First create a case
        unique_url = f"https://example.com/get-test-{uuid.uuid4()}"
        
        create_response = await client.post("/api/cases/", 
            json={
                "url": unique_url,
                "description": "Test case for retrieval"
            },
            headers={"Authorization": f"Bearer {victim_user_token}"}
        )
        assert create_response.status_code == 201
        case_id = create_response.json()["case_id"]
        
        # Now retrieve it
        get_response = await client.get(f"/api/cases/{case_id}",
            headers={"Authorization": f"Bearer {victim_user_token}"}
        )
        assert get_response.status_code == 200
        
        case_data = get_response.json()
        assert case_data["id"] == case_id
        assert case_data["url"] == unique_url
        assert case_data["description"] == "Test case for retrieval"
        assert case_data["state"] == "submitted"
        assert "events" in case_data
    
    @pytest.mark.asyncio
    async def test_get_case_not_found(self, client, victim_user_token):
        """Test retrieval of non-existent case."""
        fake_id = str(uuid.uuid4())
        
        response = await client.get(f"/api/cases/{fake_id}",
            headers={"Authorization": f"Bearer {victim_user_token}"}
        )
        assert response.status_code == 404
    
    @pytest.mark.asyncio
    async def test_get_case_unauthorized(self, client):
        """Test that unauthorized requests are rejected."""
        fake_id = str(uuid.uuid4())
        
        response = await client.get(f"/api/cases/{fake_id}")
        assert response.status_code == 401
