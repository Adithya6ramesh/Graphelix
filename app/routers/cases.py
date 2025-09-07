from fastapi import APIRouter, Depends, HTTPException, status, Header
from fastapi.responses import JSONResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from app.database import get_db
from app.auth import get_current_user, require_role
from app.models import User, UserRole, Case, CaseEvent
from app.schemas.case import (
    CaseSubmissionRequest, 
    CaseSubmissionResponse, 
    CaseResponse,
    CaseDetailResponse,
    CaseEventResponse
)
from app.services.deduplication import DeduplicationService
from typing import Optional
import time
import asyncio

router = APIRouter(prefix="/api/cases", tags=["cases"])

# Simple rate limiting (in production, use Redis or proper rate limiter)
_rate_limit_store = {}
_rate_limit_window = 60  # 1 minute
_rate_limit_max = 10    # 10 requests per minute


async def check_rate_limit(user_id: str):
    """Simple rate limiting implementation"""
    current_time = time.time()
    if user_id not in _rate_limit_store:
        _rate_limit_store[user_id] = []
    
    # Clean old entries
    _rate_limit_store[user_id] = [
        req_time for req_time in _rate_limit_store[user_id]
        if current_time - req_time < _rate_limit_window
    ]
    
    # Check if rate limit exceeded
    if len(_rate_limit_store[user_id]) >= _rate_limit_max:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail=f"Rate limit exceeded. Maximum {_rate_limit_max} requests per {_rate_limit_window} seconds."
        )
    
    # Add current request
    _rate_limit_store[user_id].append(current_time)


@router.post("/", response_model=CaseSubmissionResponse, status_code=status.HTTP_201_CREATED)
async def submit_case(
    submission: CaseSubmissionRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Submit a new case for review
    
    Supports:
    - URL or file hash (at least one required)
    - Deduplication based on normalized URL/file hash
    - Idempotency keys for retry safety
    - Rate limiting per user
    """
    # Check rate limiting
    await check_rate_limit(current_user.id)
    
    # Validate that at least one content type is provided
    if not submission.url and not submission.file_hash:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Either URL or file_hash must be provided"
        )
    
    try:
        # Use deduplication service to create or find existing case
        dedup_service = DeduplicationService(db)
        case, is_new = await dedup_service.create_case(
            submitter=current_user,
            url=submission.url,
            file_hash=submission.file_hash,
            description=submission.description,
            idempotency_key=submission.idempotency_key
        )
        
        # Prepare response
        await db.refresh(case)  # Ensure all attributes are loaded
        case_response = CaseResponse.model_validate(case)
        
        response_data = CaseSubmissionResponse(
            case_id=case.id,
            existing=not is_new,
            message="Case submitted successfully" if is_new else "Linked to existing case due to duplicate content detected",
            case=case_response
        )
        
        status_code = 201 if is_new else 200
        return JSONResponse(
            content=response_data.model_dump(mode='json'),
            status_code=status_code
        )
    
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        # Log the error in production
        import logging
        logger = logging.getLogger(__name__)
        logger.error(f"Unexpected error in submit_case: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An error occurred while processing your submission"
        )


@router.get("/{case_id}", response_model=CaseDetailResponse)
async def get_case(
    case_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    page: int = 1,
    limit: int = 50
):
    """
    Get case details with events
    
    Access control:
    - Victims can only view their own submitted cases
    - Officers and admins can view any case
    """
    # Get the case
    query = select(Case).where(Case.id == case_id)
    result = await db.execute(query)
    case = result.scalar_one_or_none()
    
    if not case:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Case not found"
        )
    
    # Check access permissions
    if current_user.role == UserRole.VICTIM and case.submitter_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You can only view cases you submitted"
        )
    
    # Get events for the case (paginated)
    events_query = (
        select(CaseEvent)
        .where(CaseEvent.case_id == case_id)
        .order_by(CaseEvent.created_at.desc())
        .offset((page - 1) * limit)
        .limit(limit)
    )
    
    events_result = await db.execute(events_query)
    events = events_result.scalars().all()
    
    # Get total event count
    count_query = select(func.count(CaseEvent.id)).where(CaseEvent.case_id == case_id)
    count_result = await db.execute(count_query)
    total_events = count_result.scalar()
    
    # Convert to response models
    case_response = CaseResponse.model_validate(case)
    event_responses = [CaseEventResponse.model_validate(event) for event in events]
    
    return CaseDetailResponse(
        case=case_response,
        events=event_responses,
        total_events=total_events
    )
