"""Schemas for finance audit trail."""
from typing import Optional, Any
from uuid import UUID
from datetime import datetime
from pydantic import BaseModel, Field


class FinanceAuditQuery(BaseModel):
    entity_type: Optional[str] = None
    action: Optional[str] = None
    date_from: Optional[str] = None
    date_to: Optional[str] = None
    skip: int = 0
    limit: int = 50


class FinanceAuditResponse(BaseModel):
    id: UUID
    hospital_id: UUID
    entity_type: str
    entity_id: UUID
    action: str
    old_value: Optional[dict] = None
    new_value: Optional[dict] = None
    performed_by_user_id: UUID
    performed_at: datetime
    ip_address: Optional[str] = None

    class Config:
        from_attributes = True
