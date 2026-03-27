from typing import Optional, List
from uuid import UUID
from decimal import Decimal
from datetime import date, time
from pydantic import BaseModel, Field

from app.schemas.billing.base import BaseSchema, TimestampSchema


class IPDChargeBase(BaseModel):
    """Base IPD charge schema"""
    item_type: Optional[str] = Field(None, max_length=50)
    item_id: Optional[str] = Field(None, max_length=50)
    description: Optional[str] = Field(None, max_length=500)
    quantity: Decimal = Field(default=1, ge=0)
    unit_price: Decimal = Field(..., ge=0)
    discount_percentage: Optional[Decimal] = Field(None, ge=0, le=100)
    discount_amount: Optional[Decimal] = Field(None, ge=0)
    tax_percentage: Optional[Decimal] = Field(None, ge=0, le=100)
    tax_amount: Optional[Decimal] = Field(None, ge=0)
    amount: Decimal = Field(..., ge=0)
    hsn_sac_code: Optional[str] = Field(None, max_length=20)


class IPDChargeCreate(IPDChargeBase):
    """Schema for creating IPD charge"""
    id: Optional[str] = Field(None, max_length=50)


class IPDChargeResponse(IPDChargeBase, TimestampSchema):
    """Schema for IPD charge response"""
    ipd_charge_id: str = Field(validation_alias="id", serialization_alias="ipd_charge_id")
    billing_id: str
    
    class Config:
        from_attributes = True
        populate_by_name = True


class IPDBillBase(BaseModel):
    """Base IPD bill schema"""
    hospital_id: Optional[UUID] = None
    patient_id: int
    appointment_id: Optional[int] = None
    admission_id: Optional[int] = None
    bill_number: str = Field(..., max_length=50)
    bill_date: date
    bill_time: time
    bill_type: Optional[str] = Field(None, max_length=20)
    subtotal_amount: Decimal = Field(..., ge=0)
    discount_percentage: Optional[Decimal] = Field(None, ge=0, le=100)
    discount_amount: Decimal = Field(default=0, ge=0)
    tax_percentage: Optional[Decimal] = Field(None, ge=0, le=100)
    tax_amount: Decimal = Field(default=0, ge=0)
    net_total: Decimal = Field(..., ge=0)  # After discount & insurance, before tax
    total_amount: Decimal = Field(..., ge=0)
    paid_amount: Decimal = Field(default=0, ge=0)
    balance_amount: Decimal = Field(default=0, ge=0)
    payment_status: Optional[str] = Field(None, max_length=20)
    notes: Optional[str] = None
    generated_by: Optional[int] = None


class IPDBillCreate(IPDBillBase):
    """Schema for creating IPD bill"""
    bill_number: Optional[str] = Field(None, max_length=50)  # Override to make optional
    charges: Optional[List[IPDChargeCreate]] = []


class IPDBillUpdate(BaseModel):
    """Schema for updating IPD bill"""
    subtotal_amount: Optional[Decimal] = Field(None, ge=0)
    discount_percentage: Optional[Decimal] = Field(None, ge=0, le=100)
    discount_amount: Optional[Decimal] = Field(None, ge=0)
    tax_percentage: Optional[Decimal] = Field(None, ge=0, le=100)
    tax_amount: Optional[Decimal] = Field(None, ge=0)
    net_total: Optional[Decimal] = Field(None, ge=0)
    total_amount: Optional[Decimal] = Field(None, ge=0)
    paid_amount: Optional[Decimal] = Field(None, ge=0)
    balance_amount: Optional[Decimal] = Field(None, ge=0)
    payment_status: Optional[str] = Field(None, max_length=20)
    notes: Optional[str] = None


class IPDBillResponse(IPDBillBase, TimestampSchema):
    """Schema for IPD bill response"""
    ipd_bill_id: int = Field(validation_alias="id", serialization_alias="ipd_bill_id")
    is_deleted: bool
    charges: List[IPDChargeResponse] = []
    
    class Config:
        from_attributes = True
        populate_by_name = True
