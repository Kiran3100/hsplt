"""Notification preference schemas."""
from datetime import datetime, time
from typing import Optional
from uuid import UUID
from pydantic import BaseModel, Field

from app.schemas.base import BaseSchema


class NotificationPreferenceBase(BaseModel):
    email_enabled: bool = True
    sms_enabled: bool = True
    whatsapp_enabled: bool = False
    quiet_hours_start: Optional[time] = None
    quiet_hours_end: Optional[time] = None


class NotificationPreferenceResponse(BaseSchema):
    id: UUID
    hospital_id: UUID
    owner_type: str
    owner_id: UUID
    email_enabled: bool
    sms_enabled: bool
    whatsapp_enabled: bool
    quiet_hours_start: Optional[time] = None
    quiet_hours_end: Optional[time] = None
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class NotificationPreferenceUpdate(BaseModel):
    email_enabled: Optional[bool] = None
    sms_enabled: Optional[bool] = None
    whatsapp_enabled: Optional[bool] = None
    quiet_hours_start: Optional[time] = None
    quiet_hours_end: Optional[time] = None
