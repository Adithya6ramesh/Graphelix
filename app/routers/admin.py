from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, and_, or_
from typing import List, Dict, Any
from datetime import datetime, timedelta
from pydantic import BaseModel

from app.database import get_db
from app.models import User, Case, CaseState, UserRole, CaseEvent
from app.auth import get_current_user, require_admin
from app.workflow import CaseWorkflowManager

router = APIRouter(prefix="/api/admin", tags=["admin"])


class RoleUpdateRequest(BaseModel):
    role: UserRole


class UserResponse(BaseModel):
    id: str  # UUID string
    email: str
    role: UserRole
    created_at: datetime
    
    class Config:
        from_attributes = True


@router.get("/users")
async def get_all_users(
    current_user: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db)
) -> List[UserResponse]:
    """Get all users (admin only)"""
    query = select(User).order_by(User.created_at.desc())
    result = await db.execute(query)
    users = result.scalars().all()
    
    return [UserResponse.model_validate(user) for user in users]


@router.get("/stats")
async def get_system_stats(
    current_user: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db)
) -> Dict[str, Any]:
    """Get comprehensive system statistics (admin only)"""
    
    # User statistics
    total_users_query = select(func.count(User.id))
    total_users_result = await db.execute(total_users_query)
    total_users = total_users_result.scalar()
    
    users_by_role_query = select(User.role, func.count(User.id)).group_by(User.role)
    users_by_role_result = await db.execute(users_by_role_query)
    users_by_role = {role.value: count for role, count in users_by_role_result.all()}
    
    # Case statistics
    total_cases_query = select(func.count(Case.id))
    total_cases_result = await db.execute(total_cases_query)
    total_cases = total_cases_result.scalar()
    
    cases_by_state_query = select(Case.state, func.count(Case.id)).group_by(Case.state)
    cases_by_state_result = await db.execute(cases_by_state_query)
    cases_by_state = {state.value: count for state, count in cases_by_state_result.all()}
    
    # Recent activity (last 24 hours)
    yesterday = datetime.utcnow() - timedelta(hours=24)
    recent_cases_query = select(func.count(Case.id)).where(Case.created_at >= yesterday)
    recent_cases_result = await db.execute(recent_cases_query)
    recent_cases = recent_cases_result.scalar()
    
    recent_users_query = select(func.count(User.id)).where(User.created_at >= yesterday)
    recent_users_result = await db.execute(recent_users_query)
    recent_users = recent_users_result.scalar()
    
    # Overdue cases
    workflow_manager = CaseWorkflowManager(db)
    overdue_cases = await workflow_manager.get_overdue_cases()
    overdue_count = len(overdue_cases)
    
    # Average case resolution time (completed cases in last 30 days)
    thirty_days_ago = datetime.utcnow() - timedelta(days=30)
    completed_cases_query = select(Case).where(
        and_(
            Case.state == CaseState.COMPLETED,
            Case.updated_at >= thirty_days_ago
        )
    )
    completed_cases_result = await db.execute(completed_cases_query)
    completed_cases = completed_cases_result.scalars().all()
    
    avg_resolution_hours = None
    if completed_cases:
        total_hours = sum([
            (case.updated_at - case.created_at).total_seconds() / 3600 
            for case in completed_cases
        ])
        avg_resolution_hours = round(total_hours / len(completed_cases), 2)
    
    return {
        "users": {
            "total": total_users,
            "by_role": users_by_role,
            "recent_24h": recent_users
        },
        "cases": {
            "total": total_cases,
            "by_state": cases_by_state,
            "recent_24h": recent_cases,
            "overdue": overdue_count,
            "avg_resolution_hours": avg_resolution_hours
        },
        "system": {
            "generated_at": datetime.utcnow().isoformat(),
            "database_health": "healthy"  # Could add actual health checks
        }
    }


@router.post("/users/{user_id}/role")
async def update_user_role(
    user_id: int,
    request: RoleUpdateRequest,
    current_user: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db)
):
    """Update user role (admin only)"""
    if current_user.id == user_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot modify your own role"
        )
    
    user_query = select(User).where(User.id == user_id)
    user_result = await db.execute(user_query)
    user = user_result.scalar_one_or_none()
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    
    old_role = user.role
    user.role = request.role
    await db.commit()
    
    return {
        "message": f"User role updated from {old_role.value} to {request.role.value}",
        "user_id": user_id,
        "old_role": old_role.value,
        "new_role": request.role.value
    }


@router.get("/cases/recent")
async def get_recent_cases(
    limit: int = 50,
    current_user: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db)
):
    """Get recent cases with details (admin only)"""
    query = (
        select(Case)
        .order_by(Case.created_at.desc())
        .limit(limit)
    )
    
    result = await db.execute(query)
    cases = result.scalars().all()
    
    return [
        {
            "id": case.id,
            "url": case.url,  # Correct field name
            "state": case.state.value,
            "created_at": case.created_at.isoformat(),
            "updated_at": case.updated_at.isoformat(),
            "due_by": case.due_by.isoformat() if case.due_by else None,
            "assigned_to": case.assigned_officer_id,  # Correct field name
            "creator_id": case.submitter_id,  # Correct field name
            "overdue": case.due_by < datetime.utcnow() if case.due_by else False
        }
        for case in cases
    ]


@router.get("/analytics/workflow")
async def get_workflow_analytics(
    days: int = 30,
    current_user: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db)
):
    """Get detailed workflow analytics (admin only)"""
    start_date = datetime.utcnow() - timedelta(days=days)
    
    # Case events over time
    events_query = select(CaseEvent).where(
        CaseEvent.created_at >= start_date
    ).order_by(CaseEvent.created_at)
    
    events_result = await db.execute(events_query)
    events = events_result.scalars().all()
    
    # Group by day and action
    daily_actions = {}
    for event in events:
        day = event.created_at.date().isoformat()
        if day not in daily_actions:
            daily_actions[day] = {}
        
        action = event.action
        daily_actions[day][action] = daily_actions[day].get(action, 0) + 1
    
    # SLA compliance
    workflow_manager = CaseWorkflowManager(db)
    overdue_cases = await workflow_manager.get_overdue_cases()
    
    sla_compliance = {
        "total_overdue": len(overdue_cases),
        "overdue_by_state": {}
    }
    
    for case in overdue_cases:
        state = case.state.value
        sla_compliance["overdue_by_state"][state] = sla_compliance["overdue_by_state"].get(state, 0) + 1
    
    return {
        "period_days": days,
        "daily_actions": daily_actions,
        "sla_compliance": sla_compliance,
        "generated_at": datetime.utcnow().isoformat()
    }
