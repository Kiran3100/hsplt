"""History and queue filter schemas."""
from datetime import date, datetime
from typing import Optional
from uuid import UUID
from pydantic import BaseModel, Field

from app.schemas.base import PaginationParams


class NotificationHistoryFilters(BaseModel):
    owner_type: Optional[str] = Field(None, description="PATIENT, STAFF")
    owner_id: Optional[UUID] = None
    status: Optional[str] = Field(None, description="QUEUED, SENT, FAILED, etc.")
    from_date: Optional[datetime] = Field(None, alias="from")
    to_date: Optional[datetime] = Field(None, alias="to")
    event_type: Optional[str] = None

    class Config:
        populate_by_name = True


class NotificationQueueQuery(BaseModel):
    status: Optional[str] = Field("QUEUED", description="QUEUED or FAILED")
    limit: int = Field(50, ge=1, le=200)
