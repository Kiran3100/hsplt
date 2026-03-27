"""Payment collect request/response."""
from typing import Optional
from uuid import UUID
from datetime import datetime
from decimal import Decimal
from pydantic import BaseModel, Field


PAYMENT_METHODS = ("CASH", "CARD", "UPI", "ONLINE", "WALLET")
PROVIDERS = ("RAZORPAY", "STRIPE", "PAYTM", None)


class PaymentCollectRequest(BaseModel):
    bill_id: UUID
    amount: float = Field(..., gt=0)
    method: str = Field(..., max_length=20)
    provider: Optional[str] = Field(None, max_length=30)
    idempotency_key: str = Field(..., min_length=1, max_length=100)
    transaction_id: Optional[str] = None
    gateway_order_id: Optional[str] = None
    gateway_signature: Optional[str] = None
    currency: str = "INR"


class PaymentCollectResponse(BaseModel):
    id: UUID
    hospital_id: UUID
    bill_id: UUID
    payment_reference: str
    method: str
    provider: Optional[str]
    amount: Decimal
    currency: str
    status: str
    transaction_id: Optional[str]
    paid_at: Optional[datetime]
    receipt_number: Optional[str]

    class Config:
        from_attributes = True
