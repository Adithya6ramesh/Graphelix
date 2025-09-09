from typing import Optional, Tuple, Dict, Any
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, or_
from app.models import Case, DedupIndex, IdempotencyKey, CaseEvent, User
from app.models.case import CaseState
from app.services.normalization import URLNormalizer
from datetime import datetime, timedelta
from app.config import settings
import uuid


class DeduplicationService:
    """Service for handling case deduplication and submission"""
    
    def __init__(self, db: AsyncSession):
        self.db = db
    
    async def check_existing_case(
        self, 
        url_hash: Optional[str] = None, 
        file_hash: Optional[str] = None
    ) -> Optional[Case]:
        """
        Check if a case already exists for the given hashes
        
        Returns the existing case if found, None otherwise
        """
        if not url_hash and not file_hash:
            return None
        
        # Build query to check both dedup index and cases table
        conditions = []
        
        if url_hash:
            conditions.append(Case.url_hash == url_hash)
        
        if file_hash:
            conditions.append(Case.file_hash == file_hash)
        
        if not conditions:
            return None
        
        # Check cases table first (most direct)
        query = select(Case).where(or_(*conditions))
        result = await self.db.execute(query)
        existing_case = result.scalar_one_or_none()
        
        return existing_case
    
    async def check_idempotency_key(self, idempotency_key: str) -> Optional[str]:
        """
        Check if this idempotency key has been used before
        
        Returns case_id if found, None otherwise
        """
        if not idempotency_key:
            return None
        
        query = select(IdempotencyKey).where(IdempotencyKey.key == idempotency_key)
        result = await self.db.execute(query)
        idem_record = result.scalar_one_or_none()
        
        return idem_record.case_id if idem_record else None
    
    async def create_case(
        self,
        submitter: User,
        url: Optional[str] = None,
        file_hash: Optional[str] = None,
        description: Optional[str] = None,
        idempotency_key: Optional[str] = None
    ) -> Tuple[Case, bool]:
        """
        Create a new case or return existing one
        
        Returns:
            (case, is_new) tuple where is_new indicates if this is a new case
        """
        
        # Process and normalize the submission
        processed = URLNormalizer.process_submission(url, file_hash)
        
        if not processed['has_content']:
            raise ValueError("Either URL or file_hash must be provided")
        
        # Check idempotency key first
        if idempotency_key:
            existing_case_id = await self.check_idempotency_key(idempotency_key)
            if existing_case_id:
                query = select(Case).where(Case.id == existing_case_id)
                result = await self.db.execute(query)
                case = result.scalar_one()
                return case, False
        
        # Check for existing case
        existing_case = await self.check_existing_case(
            processed['url_hash'] if processed['url_hash'] else None,
            processed['file_hash'] if processed['file_hash'] else None
        )
        
        if existing_case:
            # Link this submission to existing case
            await self._create_link_event(existing_case, submitter)
            
            # Store idempotency key if provided
            if idempotency_key:
                await self._store_idempotency_key(idempotency_key, existing_case.id)
            
            await self.db.commit()
            return existing_case, False
        
        # Create new case
        # Calculate SLA deadline using workflow manager
        from app.workflow import CaseWorkflowManager
        workflow_manager = CaseWorkflowManager(self.db)
        due_by = workflow_manager.calculate_sla_deadline(CaseState.SUBMITTED)
        
        new_case = Case(
            submitter_id=submitter.id,
            url=processed['url'],
            url_normalized=processed['url_normalized'],
            url_hash=processed['url_hash'] if processed['url_hash'] else None,
            file_hash=processed['file_hash'] if processed['file_hash'] else None,
            description=description,
            due_by=due_by
        )
        
        self.db.add(new_case)
        await self.db.flush()  # Get the ID
        
        # Create dedup index entries
        await self._create_dedup_entries(new_case)
        
        # Create submission event
        await self._create_submission_event(new_case, submitter)
        
        # Store idempotency key if provided
        if idempotency_key:
            await self._store_idempotency_key(idempotency_key, new_case.id)
        
        await self.db.commit()
        return new_case, True
    
    async def _create_dedup_entries(self, case: Case) -> None:
        """Create deduplication index entries for the case"""
        if case.url_hash:
            dedup = DedupIndex(
                case_id=case.id,
                url_hash=case.url_hash
            )
            self.db.add(dedup)
        
        if case.file_hash:
            dedup = DedupIndex(
                case_id=case.id,
                file_hash=case.file_hash
            )
            self.db.add(dedup)
    
    async def _create_submission_event(self, case: Case, submitter: User) -> None:
        """Create audit event for case submission"""
        event = CaseEvent(
            case_id=case.id,
            actor_id=submitter.id,
            actor_role=submitter.role.value,
            action="submitted",
            event_metadata={
                "url": case.url,
                "has_url": bool(case.url),
                "has_file_hash": bool(case.file_hash),
                "description_length": len(case.description) if case.description else 0
            }
        )
        self.db.add(event)
    
    async def _create_link_event(self, existing_case: Case, submitter: User) -> None:
        """Create audit event for linking to existing case"""
        event = CaseEvent(
            case_id=existing_case.id,
            actor_id=submitter.id,
            actor_role=submitter.role.value,
            action="linked_submission",
            event_metadata={
                "reason": "duplicate_detected",
                "linked_at": datetime.utcnow().isoformat()
            }
        )
        self.db.add(event)
    
    async def _store_idempotency_key(self, key: str, case_id: str) -> None:
        """Store idempotency key mapping"""
        idem_key = IdempotencyKey(
            key=key,
            case_id=case_id
        )
        self.db.add(idem_key)
