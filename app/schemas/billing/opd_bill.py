from typing import Optional, List
from uuid import UUID
from decimal import Decimal
from datetime import date, time
from pydantic import BaseModel, Field

from app.schemas.billing.base import BaseSchema, TimestampSchema


class OPDBillItemBase(BaseModel):
    """Base OPD bill item schema"""
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


class OPDBillItemCreate(OPDBillItemBase):
    """Schema for creating OPD bill item"""
    id: str = Field(..., max_length=50)


class OPDBillItemResponse(OPDBillItemBase, TimestampSchema):
    """Schema for OPD bill item response"""
    opd_bill_item_id: str = Field(validation_alias="id", serialization_alias="opd_bill_item_id")
    billing_id: str
    
    class Config:
        from_attributes = True
        populate_by_name = True


class OPDBillBase(BaseModel):
    """Base OPD bill schema"""
    hospital_id: Optional[UUID] = None
    patient_id: Optional[int] = None
    appointment_id: Optional[int] = None
    admission_id: Optional[int] = None
    bill_number: Optional[str] = Field(None, max_length=50)
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


class OPDBillCreate(OPDBillBase):
    """Schema for creating OPD bill"""
    items: Optional[List[OPDBillItemCreate]] = []


class OPDBillUpdate(BaseModel):
    """Schema for updating OPD bill"""
    subtotal_amount: Optional[Decimal] = Field(None, ge=0)
    discount_percentage: Optional[Decimal] = Field(None, ge=0, le=100)
    discount_amount: Optional[Decimal] = Field(None, ge=0)
    tax_percentage: Optional[Decimal] = Field(None, ge=0, le=100)
    tax_amount: Optional[Decimal] = Field(None, ge=0)
    total_amount: Optional[Decimal] = Field(None, ge=0)
    paid_amount: Optional[Decimal] = Field(None, ge=0)
    balance_amount: Optional[Decimal] = Field(None, ge=0)
    payment_status: Optional[str] = Field(None, max_length=20)
    notes: Optional[str] = None


class OPDBillResponse(OPDBillBase, TimestampSchema):
    """Schema for OPD bill response"""
    opd_bill_id: int = Field(validation_alias="id", serialization_alias="opd_bill_id")
    is_deleted: bool
    items: List[OPDBillItemResponse] = []
    
    class Config:
        from_attributes = True
        populate_by_name = True
