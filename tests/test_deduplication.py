import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import AsyncSession
from app.models import User, UserRole, Case, CaseState, DedupIndex, IdempotencyKey
from app.services.deduplication import DeduplicationService
from app.database import Base
from tests.test_auth import test_engine, TestSessionLocal
from datetime import datetime


@pytest_asyncio.fixture
async def async_session():
    """Create async session for deduplication tests"""
    async with TestSessionLocal() as session:
        try:
            yield session
        finally:
            await session.close()


@pytest_asyncio.fixture(autouse=True)
async def setup_test_db():
    """Setup and teardown test database"""
    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    
    yield
    
    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)


@pytest_asyncio.fixture
async def victim_user(async_session: AsyncSession):
    """Create a victim user for testing"""
    user = User(
        email="victim@example.com",
        hashed_password="hashed",
        role=UserRole.VICTIM
    )
    async_session.add(user)
    await async_session.commit()
    await async_session.refresh(user)
    return user


@pytest_asyncio.fixture
async def dedup_service(async_session: AsyncSession):
    """Create deduplication service"""
    return DeduplicationService(async_session)


@pytest.mark.asyncio
async def test_create_new_case_url(dedup_service: DeduplicationService, victim_user: User):
    """Test creating a new case with URL"""
    case, is_new = await dedup_service.create_case(
        submitter=victim_user,
        url="https://example.com/harmful-content",
        description="This contains harmful content"
    )
    
    assert is_new is True
    assert case.id is not None
    assert case.submitter_id == victim_user.id
    assert case.url == "https://example.com/harmful-content"
    assert case.url_normalized == "https://example.com/harmful-content"
    assert case.url_hash is not None
    assert len(case.url_hash) == 64
    assert case.state == CaseState.SUBMITTED
    assert case.due_by is not None


@pytest.mark.asyncio
async def test_create_new_case_file_hash(dedup_service: DeduplicationService, victim_user: User):
    """Test creating a new case with file hash"""
    file_hash = "a" * 64
    case, is_new = await dedup_service.create_case(
        submitter=victim_user,
        file_hash=file_hash,
        description="File hash reported"
    )
    
    assert is_new is True
    assert case.file_hash == file_hash
    assert case.url is None or case.url == ""
    assert case.url_hash is None or case.url_hash == ""


@pytest.mark.asyncio
async def test_duplicate_url_detection(dedup_service: DeduplicationService, victim_user: User):
    """Test that duplicate URLs are detected"""
    url = "https://example.com/page"
    
    # Create first case
    case1, is_new1 = await dedup_service.create_case(
        submitter=victim_user,
        url=url
    )
    assert is_new1 is True
    
    # Create second case with same URL (should be duplicate)
    case2, is_new2 = await dedup_service.create_case(
        submitter=victim_user,
        url=url
    )
    assert is_new2 is False
    assert case1.id == case2.id


@pytest.mark.asyncio
async def test_duplicate_normalized_url_detection(dedup_service: DeduplicationService, victim_user: User):
    """Test that URLs that normalize to the same thing are detected as duplicates"""
    url1 = "https://example.com/page?utm_source=google&important=keep"
    url2 = "HTTPS://EXAMPLE.COM/page/?important=keep&utm_medium=cpc"
    
    # Create first case
    case1, is_new1 = await dedup_service.create_case(
        submitter=victim_user,
        url=url1
    )
    assert is_new1 is True
    
    # Create second case with equivalent URL
    case2, is_new2 = await dedup_service.create_case(
        submitter=victim_user,
        url=url2
    )
    assert is_new2 is False
    assert case1.id == case2.id


@pytest.mark.asyncio
async def test_duplicate_file_hash_detection(dedup_service: DeduplicationService, victim_user: User):
    """Test that duplicate file hashes are detected"""
    file_hash = "b" * 64
    
    # Create first case
    case1, is_new1 = await dedup_service.create_case(
        submitter=victim_user,
        file_hash=file_hash
    )
    assert is_new1 is True
    
    # Create second case with same file hash
    case2, is_new2 = await dedup_service.create_case(
        submitter=victim_user,
        file_hash=file_hash
    )
    assert is_new2 is False
    assert case1.id == case2.id


@pytest.mark.asyncio
async def test_idempotency_key_functionality(dedup_service: DeduplicationService, victim_user: User):
    """Test idempotency key prevents duplicate submissions"""
    url = "https://example.com/page"
    idem_key = "client-request-123"
    
    # Create first case with idempotency key
    case1, is_new1 = await dedup_service.create_case(
        submitter=victim_user,
        url=url,
        idempotency_key=idem_key
    )
    assert is_new1 is True
    
    # Submit again with same idempotency key
    case2, is_new2 = await dedup_service.create_case(
        submitter=victim_user,
        url="https://different.com/page",  # Different URL but same idem key
        idempotency_key=idem_key
    )
    assert is_new2 is False
    assert case1.id == case2.id


@pytest.mark.asyncio
async def test_check_existing_case_by_url_hash(dedup_service: DeduplicationService, victim_user: User):
    """Test checking for existing cases by URL hash"""
    # Create a case first
    case, _ = await dedup_service.create_case(
        submitter=victim_user,
        url="https://example.com/page"
    )
    
    # Check if it can be found by hash
    existing = await dedup_service.check_existing_case(url_hash=case.url_hash)
    assert existing is not None
    assert existing.id == case.id


@pytest.mark.asyncio
async def test_check_existing_case_by_file_hash(dedup_service: DeduplicationService, victim_user: User):
    """Test checking for existing cases by file hash"""
    file_hash = "c" * 64
    
    # Create a case first
    case, _ = await dedup_service.create_case(
        submitter=victim_user,
        file_hash=file_hash
    )
    
    # Check if it can be found by file hash
    existing = await dedup_service.check_existing_case(file_hash=file_hash)
    assert existing is not None
    assert existing.id == case.id


@pytest.mark.asyncio
async def test_no_content_raises_error(dedup_service: DeduplicationService, victim_user: User):
    """Test that submitting without URL or file hash raises error"""
    with pytest.raises(ValueError, match="Either URL or file_hash must be provided"):
        await dedup_service.create_case(
            submitter=victim_user,
            description="No content provided"
        )


@pytest.mark.asyncio
async def test_invalid_file_hash_raises_error(dedup_service: DeduplicationService, victim_user: User):
    """Test that invalid file hash is treated as no content"""
    with pytest.raises(ValueError, match="Either URL or file_hash must be provided"):
        await dedup_service.create_case(
            submitter=victim_user,
            file_hash="invalid-hash",
            description="Invalid hash"
        )


@pytest.mark.asyncio
async def test_case_with_both_url_and_file_hash(dedup_service: DeduplicationService, victim_user: User):
    """Test creating case with both URL and file hash"""
    url = "https://example.com/page"
    file_hash = "d" * 64
    
    case, is_new = await dedup_service.create_case(
        submitter=victim_user,
        url=url,
        file_hash=file_hash,
        description="Both URL and file hash"
    )
    
    assert is_new is True
    assert case.url == url
    assert case.file_hash == file_hash
    assert case.url_hash is not None
    assert len(case.url_hash) == 64


@pytest.mark.asyncio
async def test_dedup_mixed_content_types(dedup_service: DeduplicationService, victim_user: User):
    """Test deduplication when one case has URL and another has file hash"""
    url = "https://example.com/page"
    file_hash = "e" * 64
    
    # Create case with URL only
    case1, is_new1 = await dedup_service.create_case(
        submitter=victim_user,
        url=url
    )
    assert is_new1 is True
    
    # Create case with file hash only (should be different case)
    case2, is_new2 = await dedup_service.create_case(
        submitter=victim_user,
        file_hash=file_hash
    )
    assert is_new2 is True
    assert case1.id != case2.id


@pytest.mark.asyncio
async def test_link_event_creation(dedup_service: DeduplicationService, victim_user: User, async_session: AsyncSession):
    """Test that link events are created for duplicate submissions"""
    url = "https://example.com/page"
    
    # Create first case
    case1, _ = await dedup_service.create_case(
        submitter=victim_user,
        url=url
    )
    
    # Create duplicate (should create link event)
    case2, _ = await dedup_service.create_case(
        submitter=victim_user,
        url=url
    )
    
    # Check that we have events for the case
    from sqlalchemy import select
    from app.models import CaseEvent
    
    query = select(CaseEvent).where(CaseEvent.case_id == case1.id)
    result = await async_session.execute(query)
    events = result.scalars().all()
    
    # Should have at least submission and link events
    assert len(events) >= 2
    actions = [event.action for event in events]
    assert "submitted" in actions
    assert "linked_submission" in actions
