"""Notification template schemas."""
from datetime import datetime
from typing import Optional
from uuid import UUID
from pydantic import BaseModel

from app.schemas.base import BaseSchema


class NotificationTemplateBase(BaseModel):
    channel: str
    template_key: str
    subject: Optional[str] = None
    body: str
    is_active: bool = True


class NotificationTemplateResponse(BaseSchema):
    id: UUID
    hospital_id: Optional[UUID] = None
    channel: str
    template_key: str
    subject: Optional[str] = None
    body: str
    is_active: bool
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True
