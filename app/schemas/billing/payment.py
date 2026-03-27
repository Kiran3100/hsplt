"""Schemas for payment collection."""
from typing import List, Optional
from uuid import UUID
from datetime import datetime
from decimal import Decimal
from pydantic import BaseModel, Field


PAYMENT_METHODS = ("CASH", "CARD", "UPI", "NETBANKING", "WALLET", "ONLINE_GATEWAY")


class PaymentCollect(BaseModel):
    bill_id: UUID
    amount: float = Field(..., gt=0)
    method: str = Field(..., max_length=30)
    provider: Optional[str] = None
    idempotency_key: str = Field(..., min_length=1, max_length=100)
    gateway_transaction_id: Optional[str] = None
    extra_data: Optional[dict] = None  # sent to service as metadata


class PaymentResponse(BaseModel):
    id: UUID
    hospital_id: UUID
    bill_id: UUID
    payment_ref: str
    method: str
    provider: Optional[str]
    amount: Decimal
    status: str
    paid_at: Optional[datetime]
    collected_by_user_id: UUID
    gateway_transaction_id: Optional[str]
    created_at: datetime

    class Config:
        from_attributes = True


class PaymentRefund(BaseModel):
    amount: Optional[float] = None  # full refund if not set
    reason: Optional[str] = None


class AdvancePaymentRequest(BaseModel):
    admission_id: UUID
    amount: float = Field(..., gt=0)
    method: str = Field(..., max_length=30)
    idempotency_key: str = Field(..., min_length=1, max_length=100)


class PaymentSplitItem(BaseModel):
    """Single split: amount + method + idempotency key."""
    amount: float = Field(..., gt=0)
    method: str = Field(..., max_length=30)
    idempotency_key: str = Field(..., min_length=1, max_length=100)
    provider: Optional[str] = None
    gateway_transaction_id: Optional[str] = None


class PaymentCollectSplit(BaseModel):
    """Collect payment as multiple methods (split) in one request."""
    bill_id: UUID
    splits: List["PaymentSplitItem"] = Field(..., min_length=1)

    class Config:
        from_attributes = True
