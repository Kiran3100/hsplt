"""Unified send, OTP, bulk SMS, schedule request schemas."""
from datetime import datetime
from typing import Optional, Any
from pydantic import BaseModel, Field


class NotificationSendRequest(BaseModel):
    """Unified multi-channel send (outbox: create job first, deliver async)."""
    channel: str = Field(..., description="EMAIL or SMS")
    to: str = Field(..., description="Email address or phone number")
    template_key: Optional[str] = Field(None, description="Template key (hospital or global)")
    raw_message: Optional[str] = Field(None, description="Raw body if no template")
    subject: Optional[str] = Field(None, description="Subject (email only)")
    payload: Optional[dict[str, Any]] = Field(default_factory=dict, description="Template variables")
    idempotency_key: str = Field(..., min_length=1, max_length=120)
    event_type: str = Field(default="GENERAL", description="e.g. PAYMENT_RECEIPT, APPOINTMENT_CONFIRM")


class NotificationScheduleRequest(BaseModel):
    """Schedule a notification for later delivery."""
    event_type: str = Field(..., description="APPOINTMENT_REMINDER, etc.")
    channel: str = Field(..., description="EMAIL or SMS")
    to: str = Field(..., description="Email or phone")
    template_key: Optional[str] = None
    payload: Optional[dict[str, Any]] = Field(default_factory=dict)
    scheduled_for: datetime = Field(..., description="When to send")
    idempotency_key: str = Field(..., min_length=1, max_length=120)


class OtpSendRequest(BaseModel):
    """Send OTP to phone (rate-limited per phone)."""
    phone: str = Field(..., min_length=10)
    purpose: Optional[str] = Field(default="LOGIN", description="LOGIN, REGISTER, etc.")


class OtpVerifyRequest(BaseModel):
    phone: str = Field(..., min_length=10)
    otp: str = Field(..., min_length=4, max_length=8)


class BulkSmsRequest(BaseModel):
    """Bulk SMS (staff-only, hospital-scoped)."""
    phones: list[str] = Field(..., min_length=1, max_length=500)
    message: str = Field(..., min_length=1, max_length=1600)
    idempotency_key: str = Field(..., min_length=1, max_length=120)
