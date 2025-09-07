from sqlalchemy import Column, String, DateTime, Enum as SQLEnum, Integer
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from app.database import Base
import enum
import uuid


class UserRole(str, enum.Enum):
    VICTIM = "victim"
    OFFICER = "officer"
    ADMIN = "admin"


class User(Base):
    __tablename__ = "users"
    
    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    email = Column(String(255), unique=True, nullable=False, index=True)
    hashed_password = Column(String(255), nullable=False)
    role = Column(SQLEnum(UserRole), nullable=False, default=UserRole.VICTIM)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    # Relationships
    submitted_cases = relationship("Case", foreign_keys="Case.submitter_id", back_populates="submitter")
    assigned_cases = relationship("Case", foreign_keys="Case.assigned_officer_id", back_populates="assigned_officer")
    actions = relationship("CaseEvent", back_populates="actor")
    
    def __repr__(self):
        return f"<User {self.email} ({self.role})>"
