from typing import Dict, List, Optional, Tuple
from datetime import datetime, timedelta
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, or_, func
from app.models import Case, CaseState, User, UserRole, CaseEvent
from dataclasses import dataclass
from enum import Enum
import logging

logger = logging.getLogger(__name__)


@dataclass
class WorkflowTransition:
    """Represents a workflow state transition"""
    from_state: CaseState
    to_state: CaseState
    required_role: UserRole
    description: str
    auto_assign: bool = False


@dataclass
class SLAConfiguration:
    """SLA configuration for different states"""
    state: CaseState
    sla_hours: int
    escalation_state: Optional[CaseState] = None
    description: str = ""


class CaseWorkflowManager:
    """Manages case workflow transitions, SLA timers, and escalation"""
    
    # Define allowed transitions
    TRANSITIONS: List[WorkflowTransition] = [
        # Submitted state transitions
        WorkflowTransition(
            CaseState.SUBMITTED, CaseState.IN_REVIEW, UserRole.OFFICER,
            "Officer starts reviewing the case", auto_assign=True
        ),
        WorkflowTransition(
            CaseState.SUBMITTED, CaseState.ESCALATED, UserRole.ADMIN,
            "Admin escalates high-priority case immediately"
        ),
        
        # In Review state transitions
        WorkflowTransition(
            CaseState.IN_REVIEW, CaseState.APPROVED, UserRole.OFFICER,
            "Officer approves the takedown request"
        ),
        WorkflowTransition(
            CaseState.IN_REVIEW, CaseState.REJECTED, UserRole.OFFICER,
            "Officer rejects the takedown request"
        ),
        WorkflowTransition(
            CaseState.IN_REVIEW, CaseState.MATCH_FOUND, UserRole.OFFICER,
            "Officer finds matching content requiring action"
        ),
        WorkflowTransition(
            CaseState.IN_REVIEW, CaseState.ESCALATED, UserRole.OFFICER,
            "Officer escalates complex case to admin"
        ),
        
        # Escalated state transitions
        WorkflowTransition(
            CaseState.ESCALATED, CaseState.APPROVED, UserRole.ADMIN,
            "Admin approves escalated case"
        ),
        WorkflowTransition(
            CaseState.ESCALATED, CaseState.REJECTED, UserRole.ADMIN,
            "Admin rejects escalated case"
        ),
        WorkflowTransition(
            CaseState.ESCALATED, CaseState.IN_REVIEW, UserRole.ADMIN,
            "Admin sends case back to review"
        ),
        
        # Match Found state transitions
        WorkflowTransition(
            CaseState.MATCH_FOUND, CaseState.COMPLETED, UserRole.OFFICER,
            "Content removal action completed"
        ),
        WorkflowTransition(
            CaseState.MATCH_FOUND, CaseState.ESCALATED, UserRole.OFFICER,
            "Content removal requires admin intervention"
        ),
        
        # Final state transitions
        WorkflowTransition(
            CaseState.APPROVED, CaseState.COMPLETED, UserRole.OFFICER,
            "Takedown process completed successfully"
        ),
        WorkflowTransition(
            CaseState.REJECTED, CaseState.COMPLETED, UserRole.OFFICER,
            "Case closed as rejected"
        ),
    ]
    
    # SLA configurations
    SLA_CONFIG: List[SLAConfiguration] = [
        SLAConfiguration(
            CaseState.SUBMITTED, 24, CaseState.ESCALATED,
            "Cases must be reviewed within 24 hours"
        ),
        SLAConfiguration(
            CaseState.IN_REVIEW, 72, CaseState.ESCALATED,
            "Review must be completed within 72 hours"
        ),
        SLAConfiguration(
            CaseState.ESCALATED, 48, None,
            "Escalated cases must be resolved within 48 hours"
        ),
        SLAConfiguration(
            CaseState.MATCH_FOUND, 24, CaseState.ESCALATED,
            "Content removal must be completed within 24 hours"
        ),
    ]
    
    def __init__(self, db: AsyncSession):
        self.db = db
        self._transitions_map = {
            (t.from_state, t.to_state): t for t in self.TRANSITIONS
        }
        self._sla_map = {s.state: s for s in self.SLA_CONFIG}
    
    async def can_transition(
        self, 
        case: Case, 
        to_state: CaseState, 
        user: User
    ) -> Tuple[bool, str]:
        """
        Check if a transition is allowed
        
        Returns (is_allowed, reason)
        """
        transition_key = (case.state, to_state)
        
        if transition_key not in self._transitions_map:
            return False, f"Transition from {case.state.value} to {to_state.value} is not allowed"
        
        transition = self._transitions_map[transition_key]
        
        # Check user role permissions
        if user.role.value < transition.required_role.value:
            return False, f"User role {user.role.value} insufficient for this action (requires {transition.required_role.value})"
        
        # Additional business rules can be added here
        # For example: check if case is assigned to the user for certain transitions
        if case.state == CaseState.IN_REVIEW and case.assigned_officer_id:
            if case.assigned_officer_id != user.id and user.role != UserRole.ADMIN:
                return False, "Only the assigned officer or admin can modify this case"
        
        return True, transition.description
    
    async def transition_case(
        self, 
        case: Case, 
        to_state: CaseState, 
        user: User,
        notes: Optional[str] = None
    ) -> bool:
        """
        Transition a case to a new state
        
        Returns True if successful, raises exception if not allowed
        """
        can_transition, reason = await self.can_transition(case, to_state, user)
        
        if not can_transition:
            raise ValueError(reason)
        
        transition = self._transitions_map[(case.state, to_state)]
        old_state = case.state
        
        # Update case state
        case.state = to_state
        case.updated_at = datetime.utcnow()
        
        # Auto-assign if specified
        if transition.auto_assign and not case.assigned_officer_id:
            case.assigned_officer_id = user.id
        
        # Calculate new SLA deadline
        new_deadline = self.calculate_sla_deadline(to_state)
        if new_deadline:
            case.due_by = new_deadline
        
        # Create event record
        event = CaseEvent(
            case_id=case.id,
            actor_id=user.id,
            actor_role=user.role.value,
            action="STATE_CHANGE",
            event_metadata={
                "from_state": old_state.value,
                "to_state": to_state.value,
                "transition_reason": reason,
                "auto_assigned": transition.auto_assign,
                "notes": notes
            }
        )
        
        self.db.add(event)
        await self.db.commit()
        
        logger.info(f"Case {case.id} transitioned from {old_state.value} to {to_state.value} by user {user.id}")
        return True
    
    def calculate_sla_deadline(self, state: CaseState) -> Optional[datetime]:
        """Calculate SLA deadline for a given state"""
        if state not in self._sla_map:
            return None
        
        sla_config = self._sla_map[state]
        return datetime.utcnow() + timedelta(hours=sla_config.sla_hours)
    
    async def get_overdue_cases(self) -> List[Case]:
        """Get all cases that are past their SLA deadline"""
        query = select(Case).where(
            and_(
                Case.due_by.isnot(None),
                Case.due_by < datetime.utcnow(),
                Case.state.in_([
                    CaseState.SUBMITTED,
                    CaseState.IN_REVIEW,
                    CaseState.ESCALATED,
                    CaseState.MATCH_FOUND
                ])
            )
        )
        
        result = await self.db.execute(query)
        return result.scalars().all()
    
    async def escalate_overdue_case(self, case: Case, system_user: User) -> bool:
        """Escalate an overdue case"""
        sla_config = self._sla_map.get(case.state)
        
        if not sla_config or not sla_config.escalation_state:
            logger.warning(f"No escalation state defined for {case.state.value}")
            return False
        
        try:
            await self.transition_case(
                case, 
                sla_config.escalation_state,
                system_user,
                notes=f"Auto-escalated due to SLA breach (deadline: {case.due_by})"
            )
            return True
        except ValueError as e:
            logger.error(f"Failed to escalate case {case.id}: {e}")
            return False
    
    async def get_workflow_metrics(self) -> Dict[str, any]:
        """Get workflow metrics and statistics"""
        metrics = {}
        
        # Cases by state
        for state in CaseState:
            query = select(func.count(Case.id)).where(Case.state == state)
            result = await self.db.execute(query)
            metrics[f"cases_{state.value}"] = result.scalar() or 0
        
        # Overdue cases
        overdue_cases = await self.get_overdue_cases()
        metrics["overdue_cases"] = len(overdue_cases)
        
        # Average processing time (completed cases)
        query = select(
            func.avg(
                func.extract('epoch', Case.updated_at) - 
                func.extract('epoch', Case.created_at)
            )
        ).where(Case.state == CaseState.COMPLETED)
        
        result = await self.db.execute(query)
        avg_seconds = result.scalar()
        metrics["avg_processing_time_hours"] = (avg_seconds / 3600) if avg_seconds else 0
        
        # Cases per officer
        query = select(
            Case.assigned_officer_id,
            func.count(Case.id).label('case_count')
        ).where(
            Case.assigned_officer_id.isnot(None)
        ).group_by(Case.assigned_officer_id)
        
        result = await self.db.execute(query)
        officer_loads = {row.assigned_officer_id: row.case_count for row in result}
        metrics["officer_case_loads"] = officer_loads
        
        return metrics
    
    def get_available_transitions(self, case: Case, user: User) -> List[Dict[str, str]]:
        """Get available transitions for a case given current user"""
        available = []
        
        for transition in self.TRANSITIONS:
            if transition.from_state == case.state:
                if user.role.value >= transition.required_role.value:
                    # Additional checks for assigned cases
                    if (case.state == CaseState.IN_REVIEW and 
                        case.assigned_officer_id and 
                        case.assigned_officer_id != user.id and 
                        user.role != UserRole.ADMIN):
                        continue
                    
                    available.append({
                        "to_state": transition.to_state.value,
                        "description": transition.description,
                        "required_role": transition.required_role.value
                    })
        
        return available
