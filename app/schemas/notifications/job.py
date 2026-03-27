"""Notification job and delivery log schemas."""
from datetime import datetime
from typing import Optional, Any
from uuid import UUID
from pydantic import BaseModel, Field

from app.schemas.base import BaseSchema


class NotificationJobResponse(BaseSchema):
    id: UUID
    hospital_id: UUID
    event_type: str
    channel: str
    to_address: str
    template_id: Optional[UUID] = None
    subject_rendered: Optional[str] = None
    message_rendered: Optional[str] = None
    scheduled_for: Optional[datetime] = None
    status: str
    attempts: int
    max_attempts: int
    last_error: Optional[str] = None
    provider_message_id: Optional[str] = None
    idempotency_key: str
    created_by_user_id: Optional[UUID] = None
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class NotificationDeliveryLogResponse(BaseSchema):
    id: UUID
    job_id: UUID
    provider: Optional[str] = None
    status: str
    raw_response: Optional[dict[str, Any]] = None
    created_at: datetime

    class Config:
        from_attributes = True


class NotificationJobDetailResponse(NotificationJobResponse):
    delivery_logs: list["NotificationDeliveryLogResponse"] = []


# Unify for Pydantic forward ref
NotificationJobDetailResponse.model_rebuild()
