"""Refund request/response."""
from typing import Optional
from uuid import UUID
from datetime import datetime
from decimal import Decimal
from pydantic import BaseModel, Field


class RefundRequest(BaseModel):
    amount: Optional[float] = None  # full refund if omitted
    reason: Optional[str] = None


class RefundResponse(BaseModel):
    id: UUID
    payment_id: UUID
    refund_amount: Decimal
    reason: Optional[str]
    refund_status: str
    gateway_refund_id: Optional[str]
    created_at: datetime

    class Config:
        from_attributes = True
