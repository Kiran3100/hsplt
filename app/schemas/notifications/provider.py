"""Notification provider schemas."""
from datetime import datetime
from typing import Optional, Any
from uuid import UUID
from pydantic import BaseModel, Field

from app.schemas.base import BaseSchema


class NotificationProviderBase(BaseModel):
    provider_type: str
    provider_name: str
    is_enabled: bool = True


class NotificationProviderResponse(BaseSchema):
    id: UUID
    hospital_id: Optional[UUID] = None
    provider_type: str
    provider_name: str
    is_enabled: bool
    config: Optional[dict[str, Any]] = Field(None, validation_alias="config_")
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class NotificationProviderStatusUpdate(BaseModel):
    is_enabled: bool


class NotificationProviderConfigUpdate(BaseModel):
    config: dict[str, Any] = Field(..., description="Provider config (keys stored/encrypted)")


class NotificationProviderTestRequest(BaseModel):
    to_address: str = Field(..., description="Email or phone for test send")
