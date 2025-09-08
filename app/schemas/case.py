from typing import Optional
from pydantic import BaseModel, Field, field_validator
from app.models import CaseState, UserRole
from datetime import datetime


class CaseSubmissionRequest(BaseModel):
    """Request model for submitting a case"""
    url: Optional[str] = Field(None, description="URL of harmful content")
    file_hash: Optional[str] = Field(None, description="SHA256 hash of harmful file")
    description: Optional[str] = Field(None, max_length=5000, description="Description of the case")
    idempotency_key: Optional[str] = Field(None, max_length=255, description="Client-provided idempotency key")
    
    @field_validator('url')
    @classmethod
    def validate_url(cls, v):
        if v is not None and v.strip() == "":
            return None
        return v.strip() if v else None
    
    @field_validator('file_hash')
    @classmethod
    def validate_file_hash(cls, v):
        if v is not None and v.strip() == "":
            return None
        return v.strip() if v else None
    
    @field_validator('description')
    @classmethod
    def validate_description(cls, v):
        if v is not None and v.strip() == "":
            return None
        return v.strip() if v else None
    
    @field_validator('idempotency_key')
    @classmethod
    def validate_idempotency_key(cls, v):
        if v is not None and v.strip() == "":
            return None
        return v.strip() if v else None


class CaseResponse(BaseModel):
    """Response model for case operations"""
    id: str
    submitter_id: str
    url: Optional[str]
    file_hash: Optional[str]
    description: Optional[str]
    state: CaseState
    assigned_officer_id: Optional[str]
    created_at: datetime
    updated_at: datetime
    due_by: Optional[datetime]
    
    class Config:
        from_attributes = True


class CaseSubmissionResponse(BaseModel):
    """Response model for case submission"""
    case_id: str
    existing: bool = False
    message: str
    case: CaseResponse
    
    class Config:
        from_attributes = True


class CaseEventResponse(BaseModel):
    """Response model for case events"""
    id: str
    case_id: str
    actor_id: str
    actor_role: str
    action: str
    event_metadata: Optional[dict]
    created_at: datetime
    
    class Config:
        from_attributes = True


class CaseDetailResponse(BaseModel):
    """Response model for detailed case view"""
    case: CaseResponse
    events: list[CaseEventResponse]
    total_events: int
    
    class Config:
        from_attributes = True


class CaseListResponse(BaseModel):
    """Response model for case list"""
    cases: list[CaseResponse]
    total: int
    page: int
    limit: int
    has_more: bool
    
    class Config:
        from_attributes = True


class CaseUpdateRequest(BaseModel):
    """Request model for case updates"""
    state: str
    note: Optional[str] = None
    
    class Config:
        from_attributes = True
