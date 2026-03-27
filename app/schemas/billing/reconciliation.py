"""Schemas for reconciliation."""
from typing import Optional
from uuid import UUID
from datetime import date, datetime
from decimal import Decimal
from pydantic import BaseModel, Field


class ReconciliationRun(BaseModel):
    date: date


class ReconciliationResponse(BaseModel):
    id: UUID
    hospital_id: UUID
    recon_date: date
    total_cash: Decimal
    total_card: Decimal
    total_upi: Decimal
    total_online: Decimal
    gateway_report_total: Optional[Decimal]
    discrepancy_amount: Optional[Decimal]
    status: str
    notes: Optional[str]
    created_by_user_id: UUID
    created_at: datetime

    class Config:
        from_attributes = True
