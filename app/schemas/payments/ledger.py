"""Ledger query and response."""
from typing import Optional
from uuid import UUID
from datetime import datetime
from decimal import Decimal
from pydantic import BaseModel, Field


class LedgerQuery(BaseModel):
    bill_id: Optional[UUID] = None
    patient_id: Optional[UUID] = None
    date_from: Optional[str] = None
    date_to: Optional[str] = None
    skip: int = 0
    limit: int = 100


class LedgerEntryResponse(BaseModel):
    id: UUID
    bill_id: UUID
    payment_id: Optional[UUID]
    entry_type: str
    amount: Decimal
    balance_after: Optional[Decimal]
    created_at: datetime

    class Config:
        from_attributes = True
