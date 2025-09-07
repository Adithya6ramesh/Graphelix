import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import AsyncSession
from app.models import User, UserRole, Case, CaseState, CaseEvent, DedupIndex, IdempotencyKey
from app.database import Base
from tests.test_auth import test_engine, TestSessionLocal
from datetime import datetime, timedelta


@pytest_asyncio.fixture
async def async_session():
    """Create async session for database tests"""
    async with TestSessionLocal() as session:
        try:
            yield session
        finally:
            await session.close()


@pytest_asyncio.fixture(autouse=True)
async def setup_test_db():
    """Setup and teardown test database for models"""
    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    
    yield
    
    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)


@pytest.mark.asyncio
async def test_create_case(async_session: AsyncSession):
    """Test creating a case with proper relationships"""
    # Create a user first
    user = User(
        email="victim@example.com",
        hashed_password="hashed",
        role=UserRole.VICTIM
    )
    async_session.add(user)
    await async_session.commit()
    await async_session.refresh(user)
    
    # Create a case
    case = Case(
        submitter_id=user.id,
        url="https://example.com/harmful-content",
        url_normalized="https://example.com/harmful-content",
        url_hash="abc123",
        description="Harmful content reported",
        due_by=datetime.utcnow() + timedelta(hours=24)
    )
    async_session.add(case)
    await async_session.commit()
    await async_session.refresh(case)
    
    assert case.id is not None
    assert case.submitter_id == user.id
    assert case.state == CaseState.SUBMITTED
    assert case.url_hash == "abc123"
    assert case.due_by is not None


@pytest.mark.asyncio
async def test_case_event_creation(async_session: AsyncSession):
    """Test creating case events for audit logging"""
    # Create user and case
    user = User(email="officer@example.com", hashed_password="hashed", role=UserRole.OFFICER)
    async_session.add(user)
    await async_session.commit()
    await async_session.refresh(user)
    
    case = Case(submitter_id=user.id, url_hash="test123")
    async_session.add(case)
    await async_session.commit()
    await async_session.refresh(case)
    
    # Create event
    event = CaseEvent(
        case_id=case.id,
        actor_id=user.id,
        actor_role=user.role.value,
        action="submitted",
        event_metadata={"source": "web_form", "ip": "192.168.1.1"}
    )
    async_session.add(event)
    await async_session.commit()
    await async_session.refresh(event)
    
    assert event.id is not None
    assert event.case_id == case.id
    assert event.actor_id == user.id
    assert event.action == "submitted"
    assert event.event_metadata["source"] == "web_form"


@pytest.mark.asyncio
async def test_dedup_index(async_session: AsyncSession):
    """Test deduplication index functionality"""
    # Create user and case
    user = User(email="test@example.com", hashed_password="hashed", role=UserRole.VICTIM)
    async_session.add(user)
    await async_session.commit()
    await async_session.refresh(user)
    
    case = Case(submitter_id=user.id, url_hash="unique123")
    async_session.add(case)
    await async_session.commit()
    await async_session.refresh(case)
    
    # Create dedup index
    dedup = DedupIndex(
        case_id=case.id,
        url_hash="unique123"
    )
    async_session.add(dedup)
    await async_session.commit()
    await async_session.refresh(dedup)
    
    assert dedup.case_id == case.id
    assert dedup.url_hash == "unique123"


@pytest.mark.asyncio
async def test_idempotency_key(async_session: AsyncSession):
    """Test idempotency key functionality"""
    # Create user and case
    user = User(email="test@example.com", hashed_password="hashed", role=UserRole.VICTIM)
    async_session.add(user)
    await async_session.commit()
    await async_session.refresh(user)
    
    case = Case(submitter_id=user.id, url_hash="test456")
    async_session.add(case)
    await async_session.commit()
    await async_session.refresh(case)
    
    # Create idempotency key
    idem_key = IdempotencyKey(
        key="client-request-123",
        case_id=case.id
    )
    async_session.add(idem_key)
    await async_session.commit()
    await async_session.refresh(idem_key)
    
    assert idem_key.key == "client-request-123"
    assert idem_key.case_id == case.id


@pytest.mark.asyncio
async def test_user_relationships(async_session: AsyncSession):
    """Test user relationships with cases"""
    # Create victim and officer
    victim = User(email="victim@example.com", hashed_password="hashed", role=UserRole.VICTIM)
    officer = User(email="officer@example.com", hashed_password="hashed", role=UserRole.OFFICER)
    
    async_session.add_all([victim, officer])
    await async_session.commit()
    await async_session.refresh(victim)
    await async_session.refresh(officer)
    
    # Create case submitted by victim, assigned to officer
    case = Case(
        submitter_id=victim.id,
        assigned_officer_id=officer.id,
        url_hash="relationship_test"
    )
    async_session.add(case)
    await async_session.commit()
    await async_session.refresh(case)
    
    # Test relationships work (would need to eager load in real queries)
    assert case.submitter_id == victim.id
    assert case.assigned_officer_id == officer.id
