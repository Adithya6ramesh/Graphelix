from fastapi import APIRouter, Depends, HTTPException, status, Header
from fastapi.responses import JSONResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from typing import Optional
from app.database import get_db
from app.auth import get_current_user, require_role
from app.models import User, UserRole, Case, CaseEvent
from app.schemas.case import (
    CaseSubmissionRequest, 
    CaseSubmissionResponse, 
    CaseResponse,
    CaseDetailResponse,
    CaseEventResponse,
    CaseListResponse,
    CaseUpdateRequest
)
from app.services.deduplication import DeduplicationService
from app.workflow import CaseWorkflowManager
from app.models.case import CaseState
from typing import Optional, List
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


@router.get("/my-cases", response_model=CaseListResponse)
async def get_my_cases(
    page: int = 1,
    limit: int = 10,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Get cases submitted by the current user"""
    # Calculate offset
    offset = (page - 1) * limit
    
    # Get cases for the current user
    cases_query = (
        select(Case)
        .where(Case.submitter_id == current_user.id)
        .order_by(Case.created_at.desc())
        .offset(offset)
        .limit(limit)
    )
    
    cases_result = await db.execute(cases_query)
    cases = cases_result.scalars().all()
    
    # Get total count
    count_query = select(func.count(Case.id)).where(Case.submitter_id == current_user.id)
    count_result = await db.execute(count_query)
    total_cases = count_result.scalar()
    
    # Convert to response models
    case_responses = [CaseResponse.model_validate(case) for case in cases]
    
    return CaseListResponse(
        cases=case_responses,
        total=total_cases,
        page=page,
        limit=limit,
        has_more=(offset + len(cases)) < total_cases
    )


@router.get("/all", response_model=CaseListResponse)
async def get_all_cases(
    page: int = 1,
    limit: int = 10,
    state: Optional[str] = None,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Get all cases for officers and admins"""
    # Only officers and admins can view all cases
    if current_user.role == UserRole.VICTIM:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Insufficient permissions to view all cases"
        )
    
    # Calculate offset
    offset = (page - 1) * limit
    
    # Build query
    query = select(Case).order_by(Case.created_at.desc())
    
    # Filter by state if provided
    if state:
        from app.models.case import CaseState
        try:
            case_state = CaseState(state.lower())
            query = query.where(Case.state == case_state)
        except ValueError:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid state: {state}"
            )
    
    # Apply pagination
    cases_query = query.offset(offset).limit(limit)
    cases_result = await db.execute(cases_query)
    cases = cases_result.scalars().all()
    
    # Get total count
    count_query = select(func.count(Case.id))
    if state:
        count_query = count_query.where(Case.state == case_state)
    count_result = await db.execute(count_query)
    total_cases = count_result.scalar()
    
    # Convert to response models
    case_responses = [CaseResponse.model_validate(case) for case in cases]
    
    return CaseListResponse(
        cases=case_responses,
        total=total_cases,
        page=page,
        limit=limit,
        has_more=(offset + len(cases)) < total_cases
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


@router.get("/my-cases", response_model=CaseListResponse)
async def get_my_cases(
    page: int = 1,
    limit: int = 10,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Get cases submitted by the current user"""
    # Calculate offset
    offset = (page - 1) * limit
    
    # Get cases for the current user
    cases_query = (
        select(Case)
        .where(Case.submitter_id == current_user.id)
        .order_by(Case.created_at.desc())
        .offset(offset)
        .limit(limit)
    )
    
    cases_result = await db.execute(cases_query)
    cases = cases_result.scalars().all()
    
    # Get total count
    count_query = select(func.count(Case.id)).where(Case.submitter_id == current_user.id)
    count_result = await db.execute(count_query)
    total_cases = count_result.scalar()
    
    # Convert to response models
    case_responses = [CaseResponse.model_validate(case) for case in cases]
    
    return CaseListResponse(
        cases=case_responses,
        total=total_cases,
        page=page,
        limit=limit,
        has_more=(offset + len(cases)) < total_cases
    )

@router.put("/{case_id}/status", response_model=CaseResponse)
async def update_case_status(
    case_id: str,
    update_request: CaseUpdateRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Update case status (officers and admins only)"""
    # Only officers and admins can update case status
    if current_user.role == UserRole.VICTIM:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Insufficient permissions to update case status"
        )
    
    # Get the case
    case_query = select(Case).where(Case.id == case_id)
    case_result = await db.execute(case_query)
    case = case_result.scalar_one_or_none()
    
    if not case:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Case not found"
        )
    
    # Validate state transition using workflow manager
    try:
        new_state = CaseState(update_request.state.lower())
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid state: {update_request.state}"
        )
    
    # Use workflow manager for state transition
    workflow_manager = CaseWorkflowManager(db)
    
    try:
        # Check if transition is allowed
        can_transition, reason = await workflow_manager.can_transition(case, new_state, current_user)
        
        if not can_transition:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Transition not allowed: {reason}"
            )
        
        # Perform the transition
        await workflow_manager.transition_case(case, new_state, current_user, update_request.note)
        
        await db.refresh(case)
        return CaseResponse.model_validate(case)
        
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )


@router.get("/{case_id}/transitions")
async def get_available_transitions(
    case_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Get available state transitions for a case"""
    # Get the case
    case_query = select(Case).where(Case.id == case_id)
    case_result = await db.execute(case_query)
    case = case_result.scalar_one_or_none()
    
    if not case:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Case not found"
        )
    
    # Check permissions
    if (current_user.role == UserRole.VICTIM and 
        case.submitter_id != current_user.id):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You can only view your own cases"
        )
    
    workflow_manager = CaseWorkflowManager(db)
    transitions = workflow_manager.get_available_transitions(case, current_user)
    
    return {
        "case_id": case_id,
        "current_state": case.state.value,
        "available_transitions": transitions
    }


@router.get("/workflow/metrics")
async def get_workflow_metrics(
    current_user: User = Depends(require_role(UserRole.OFFICER)),
    db: AsyncSession = Depends(get_db)
):
    """Get workflow metrics and statistics"""
    workflow_manager = CaseWorkflowManager(db)
    metrics = await workflow_manager.get_workflow_metrics()
    
    return {
        "metrics": metrics,
        "timestamp": datetime.utcnow().isoformat()
    }


@router.get("/workflow/overdue")
async def get_overdue_cases(
    current_user: User = Depends(require_role(UserRole.OFFICER)),
    db: AsyncSession = Depends(get_db)
):
    """Get cases that are past their SLA deadline"""
    workflow_manager = CaseWorkflowManager(db)
    overdue_cases = await workflow_manager.get_overdue_cases()
    
    case_responses = [CaseResponse.model_validate(case) for case in overdue_cases]
    
    return {
        "overdue_cases": case_responses,
        "count": len(case_responses),
        "timestamp": datetime.utcnow().isoformat()
    }


# Import datetime for the new endpoints
from datetime import datetime