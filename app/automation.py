import asyncio
import logging
from datetime import datetime, timedelta
from typing import Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.database import async_session
from app.models import User, UserRole, Case, CaseState
from app.workflow import CaseWorkflowManager

logger = logging.getLogger(__name__)


class CaseAutomationService:
    """Background service for automated workflow operations"""
    
    def __init__(self):
        self.running = False
        self.system_user: Optional[User] = None
    
    async def ensure_system_user(self, db: AsyncSession) -> User:
        """Ensure system user exists for automated operations"""
        if self.system_user:
            return self.system_user
        
        # Check if system user exists
        query = select(User).where(User.email == "system@takedown.internal")
        result = await db.execute(query)
        system_user = result.scalar_one_or_none()
        
        if not system_user:
            # Create system user
            from app.auth import get_password_hash
            system_user = User(
                email="system@takedown.internal",
                hashed_password=get_password_hash("system_password"),
                role=UserRole.ADMIN
            )
            db.add(system_user)
            await db.commit()
            await db.refresh(system_user)
            logger.info("Created system user for automated operations")
        
        self.system_user = system_user
        return system_user
    
    async def sla_monitor_task(self):
        """Background task to monitor SLA compliance and escalate overdue cases"""
        logger.info("Starting SLA monitor task")
        
        while self.running:
            try:
                async with async_session() as db:
                    system_user = await self.ensure_system_user(db)
                    workflow_manager = CaseWorkflowManager(db)
                    
                    # Get overdue cases
                    overdue_cases = await workflow_manager.get_overdue_cases()
                    
                    if overdue_cases:
                        logger.info(f"Found {len(overdue_cases)} overdue cases")
                        
                        for case in overdue_cases:
                            try:
                                escalated = await workflow_manager.escalate_overdue_case(case, system_user)
                                if escalated:
                                    logger.info(f"Auto-escalated case {case.id} (was {case.state.value})")
                                else:
                                    logger.warning(f"Could not escalate case {case.id}")
                            except Exception as e:
                                logger.error(f"Error escalating case {case.id}: {e}")
                    
                    await db.commit()
                
            except Exception as e:
                logger.error(f"Error in SLA monitor task: {e}")
            
            # Check every 30 minutes
            await asyncio.sleep(1800)
    
    async def escalation_task(self):
        """Background task for additional escalation logic"""
        logger.info("Starting escalation monitoring task")
        
        while self.running:
            try:
                async with async_session() as db:
                    system_user = await self.ensure_system_user(db)
                    
                    # Check for cases that have been escalated for too long
                    escalated_deadline = datetime.utcnow() - timedelta(hours=48)
                    
                    query = select(Case).where(
                        Case.state == CaseState.ESCALATED,
                        Case.updated_at < escalated_deadline
                    )
                    
                    result = await db.execute(query)
                    stale_escalated = result.scalars().all()
                    
                    if stale_escalated:
                        logger.warning(f"Found {len(stale_escalated)} stale escalated cases")
                        # Could implement additional notifications or actions here
                    
                    await db.commit()
                
            except Exception as e:
                logger.error(f"Error in escalation task: {e}")
            
            # Check every 2 hours
            await asyncio.sleep(7200)
    
    async def assignment_task(self):
        """Background task for automatic case assignment"""
        logger.info("Starting case assignment task")
        
        while self.running:
            try:
                async with async_session() as db:
                    # Find unassigned cases in review
                    query = select(Case).where(
                        Case.state == CaseState.IN_REVIEW,
                        Case.assigned_officer_id.is_(None)
                    )
                    
                    result = await db.execute(query)
                    unassigned_cases = result.scalars().all()
                    
                    if unassigned_cases:
                        # Get available officers
                        officer_query = select(User).where(User.role == UserRole.OFFICER)
                        officer_result = await db.execute(officer_query)
                        officers = officer_result.scalars().all()
                        
                        if officers:
                            # Simple round-robin assignment
                            for i, case in enumerate(unassigned_cases):
                                assigned_officer = officers[i % len(officers)]
                                case.assigned_officer_id = assigned_officer.id
                                case.updated_at = datetime.utcnow()
                                
                                logger.info(f"Auto-assigned case {case.id} to officer {assigned_officer.email}")
                    
                    await db.commit()
                
            except Exception as e:
                logger.error(f"Error in assignment task: {e}")
            
            # Check every hour
            await asyncio.sleep(3600)
    
    async def start(self):
        """Start all background tasks"""
        if self.running:
            logger.warning("Automation service is already running")
            return
        
        self.running = True
        logger.info("Starting case automation service")
        
        # Start all tasks concurrently
        tasks = [
            asyncio.create_task(self.sla_monitor_task()),
            asyncio.create_task(self.escalation_task()),
            asyncio.create_task(self.assignment_task())
        ]
        
        try:
            await asyncio.gather(*tasks)
        except Exception as e:
            logger.error(f"Error in automation service: {e}")
        finally:
            self.running = False
    
    async def stop(self):
        """Stop the automation service"""
        logger.info("Stopping case automation service")
        self.running = False


# Global instance
automation_service = CaseAutomationService()


async def start_automation_service():
    """Start the automation service in the background"""
    await automation_service.start()


async def stop_automation_service():
    """Stop the automation service"""
    await automation_service.stop()
