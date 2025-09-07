from sqlalchemy import Column, String, DateTime, ForeignKey, Text, JSON
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from app.database import Base
import uuid


class CaseEvent(Base):
    __tablename__ = "case_events"
    
    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    case_id = Column(String(36), ForeignKey("cases.id"), nullable=False, index=True)
    actor_id = Column(String(36), ForeignKey("users.id"), nullable=False)
    actor_role = Column(String(20), nullable=False)  # Store role at time of action
    action = Column(String(100), nullable=False, index=True)  # e.g., "submitted", "state_changed", "assigned"
    event_metadata = Column(JSON, nullable=True)  # Store additional context as JSON (renamed to avoid conflict)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), index=True)
    
    # Relationships
    case = relationship("Case", back_populates="events")
    actor = relationship("User", back_populates="actions")
    
    def __repr__(self):
        return f"<CaseEvent {self.action} on {self.case_id} by {self.actor_id}>"
