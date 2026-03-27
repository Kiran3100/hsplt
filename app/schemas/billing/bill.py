"""Schemas for bills and bill items."""
from typing import Optional, List
from uuid import UUID
from datetime import datetime
from decimal import Decimal
from pydantic import BaseModel, Field


class BillItemCreate(BaseModel):
    service_item_id: Optional[UUID] = None
    description: str = Field(..., max_length=500)
    quantity: float = Field(..., ge=0.01)
    unit_price: float = Field(..., ge=0)
    tax_percentage: float = Field(0, ge=0, le=100)


class BillItemResponse(BaseModel):
    id: UUID
    bill_id: UUID
    service_item_id: Optional[UUID]
    description: str
    quantity: float
    unit_price: float
    tax_percentage: float
    line_subtotal: float
    line_tax: float
    line_total: float

    class Config:
        from_attributes = True


class BillItemUpdate(BaseModel):
    """Partial update for a bill item (quantity/price/tax/description)."""
    description: Optional[str] = None
    quantity: Optional[float] = Field(None, ge=0.01)
    unit_price: Optional[float] = Field(None, ge=0)
    tax_percentage: Optional[float] = Field(None, ge=0, le=100)


class BillCreate(BaseModel):
    """
    Create bill request.
    Uses reference IDs externally (patient_ref, appointment_ref, admission_number)
    and resolves to internal UUIDs in the router/service.
    """
    bill_type: str = Field(..., pattern="^(OPD|IPD)$")
    patient_ref: Optional[str] = Field(None, description="Hospital patient reference, e.g. PID-123")
    appointment_ref: Optional[str] = Field(None, description="Appointment reference, e.g. APPT-123 (for OPD)")
    admission_number: Optional[str] = Field(None, description="Admission number (for IPD)")
    items: List[BillItemCreate] = Field(..., min_length=1)
    notes: Optional[str] = None


class BillResponse(BaseModel):
    id: UUID
    hospital_id: UUID
    bill_number: str
    bill_type: str
    patient_id: UUID
    appointment_id: Optional[UUID]
    admission_id: Optional[UUID]
    status: str
    subtotal: Decimal
    discount_amount: Decimal
    tax_amount: Decimal
    total_amount: Decimal
    amount_paid: Decimal
    balance_due: Decimal
    created_by_user_id: UUID
    finalized_by_user_id: Optional[UUID]
    finalized_at: Optional[datetime]
    notes: Optional[str]
    items: List[BillItemResponse] = []
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class BillListQuery(BaseModel):
    status: Optional[str] = None
    patient_ref: Optional[str] = Field(None, description="Patient reference (e.g. PAT-001)")
    patient_id: Optional[UUID] = None  # backward compat
    date_from: Optional[str] = None
    date_to: Optional[str] = None
    skip: int = 0
    limit: int = 20


class BillFinalize(BaseModel):
    pass


class BillDiscountApply(BaseModel):
    discount_amount: float = Field(..., ge=0)
    reason: Optional[str] = None


class BillCancel(BaseModel):
    reason: Optional[str] = None


class BillReopen(BaseModel):
    """Reopen bill with an optional reason/note."""
    reason: Optional[str] = None
