from typing import Optional, Dict, Any
from datetime import datetime
from pydantic import BaseModel, Field


class AuditLogBase(BaseModel):
    """Base audit log schema"""
    table_name: str = Field(..., max_length=100)
    record_id: int
    action: str = Field(..., max_length=50)
    old_value: Optional[Dict[str, Any]] = None
    new_value: Optional[Dict[str, Any]] = None
    user_id: Optional[int] = None
    user_name: Optional[str] = Field(None, max_length=100)
    ip_address: Optional[str] = Field(None, max_length=50)


class AuditLogCreate(AuditLogBase):
    """Schema for creating audit log"""
    pass


class AuditLogResponse(AuditLogBase):
    """Schema for audit log response"""
    audit_log_id: int = Field(validation_alias="id", serialization_alias="audit_log_id")
    created_at: datetime
    
    class Config:
        from_attributes = True
        populate_by_name = True
