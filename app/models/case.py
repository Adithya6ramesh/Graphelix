from sqlalchemy import Column, String, DateTime, Enum as SQLEnum, Text, ForeignKey, Index, Boolean
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from app.database import Base
import enum
import uuid


class CaseState(str, enum.Enum):
    SUBMITTED = "submitted"
    IN_REVIEW = "in_review"
    APPROVED = "approved"
    REJECTED = "rejected"
    ESCALATED = "escalated"
    MATCH_FOUND = "match_found"
    COMPLETED = "completed"


class Case(Base):
    __tablename__ = "cases"
    
    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    submitter_id = Column(String(36), ForeignKey("users.id"), nullable=False)
    url = Column(Text, nullable=True)  # Original URL
    url_normalized = Column(Text, nullable=True)  # Normalized URL for dedup
    url_hash = Column(String(64), nullable=True, index=True)  # SHA256 of normalized URL
    file_hash = Column(String(64), nullable=True, index=True)  # SHA256 provided by user
    description = Column(Text, nullable=True)
    state = Column(SQLEnum(CaseState), nullable=False, default=CaseState.SUBMITTED, index=True)
    assigned_officer_id = Column(String(36), ForeignKey("users.id"), nullable=True, index=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), index=True)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    due_by = Column(DateTime(timezone=True), nullable=True, index=True)  # SLA deadline
    
    # Relationships
    submitter = relationship("User", foreign_keys=[submitter_id], back_populates="submitted_cases")
    assigned_officer = relationship("User", foreign_keys=[assigned_officer_id], back_populates="assigned_cases")
    events = relationship("CaseEvent", back_populates="case", cascade="all, delete-orphan")
    
    def __repr__(self):
        return f"<Case {self.id} ({self.state}) by {self.submitter_id}>"


# Create composite indexes for deduplication
Index('idx_case_url_hash', Case.url_hash)
Index('idx_case_file_hash', Case.file_hash)
Index('idx_case_state_due', Case.state, Case.due_by)
Index('idx_case_assigned', Case.assigned_officer_id, Case.state)
