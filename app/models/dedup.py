from sqlalchemy import Column, String, DateTime, Boolean, Index
from sqlalchemy.sql import func
from app.database import Base
import uuid


class IdempotencyKey(Base):
    __tablename__ = "idempotency_keys"
    
    key = Column(String(255), primary_key=True)
    case_id = Column(String(36), nullable=False, index=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    def __repr__(self):
        return f"<IdempotencyKey {self.key} -> {self.case_id}>"


class DedupIndex(Base):
    """Explicit deduplication index table for faster lookups"""
    __tablename__ = "dedup_index"
    
    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    case_id = Column(String(36), nullable=False, index=True)
    url_hash = Column(String(64), nullable=True, unique=True)  # Unique URL hash
    file_hash = Column(String(64), nullable=True, unique=True)  # Unique file hash
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    def __repr__(self):
        return f"<DedupIndex {self.case_id}: url={self.url_hash}, file={self.file_hash}>"


# Indexes for fast dedup lookups
Index('idx_dedup_url_hash', DedupIndex.url_hash)
Index('idx_dedup_file_hash', DedupIndex.file_hash)
