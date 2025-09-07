# Import all models to ensure they're registered with SQLAlchemy
from app.models.user import User, UserRole
from app.models.case import Case, CaseState
from app.models.case_event import CaseEvent
from app.models.dedup import IdempotencyKey, DedupIndex

__all__ = [
    "User", "UserRole",
    "Case", "CaseState", 
    "CaseEvent",
    "IdempotencyKey", "DedupIndex"
]
