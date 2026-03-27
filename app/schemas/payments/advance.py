"""Advance payment (IPD) request/response."""
from typing import Optional
from uuid import UUID
from datetime import datetime
from decimal import Decimal
from pydantic import BaseModel, Field


class AdvancePaymentRequest(BaseModel):
    admission_id: UUID
    amount: float = Field(..., gt=0)
    method: str = Field(..., max_length=20)
    idempotency_key: str = Field(..., min_length=1, max_length=100)
    currency: str = "INR"


class AdvancePaymentResponse(BaseModel):
    id: UUID
    bill_id: UUID
    payment_reference: str
    amount: Decimal
    status: str
    paid_at: Optional[datetime] = None

    class Config:
        from_attributes = True
