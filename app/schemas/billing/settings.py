"""
Settings Schemas
"""
from pydantic import BaseModel, Field
from typing import Optional
from decimal import Decimal


class HospitalSettingsBase(BaseModel):
    hospital_name: str
    hospital_address: Optional[str] = None
    hospital_city: Optional[str] = None
    hospital_state: Optional[str] = None
    hospital_pincode: Optional[str] = None
    hospital_phone: Optional[str] = None
    hospital_email: Optional[str] = None
    hospital_website: Optional[str] = None
    gst_number: Optional[str] = None
    pan_number: Optional[str] = None
    hospital_logo_url: Optional[str] = None
    
    # Billing settings
    opd_prefix: str = "OPD"
    ipd_prefix: str = "IPD"
    receipt_prefix: str = "RCP"
    invoice_prefix: str = "INV"
    
    # Discount settings
    max_discount_percentage: Optional[Decimal] = Field(default=Decimal("50.00"), ge=0, le=100)
    discount_approval_threshold: Optional[Decimal] = Field(default=Decimal("20.00"), ge=0, le=100)
    
    # Tax settings
    default_tax_percentage: Optional[Decimal] = Field(default=Decimal("0.00"), ge=0, le=100)
    enable_gst: bool = False
    cgst_percentage: Optional[Decimal] = Field(default=Decimal("9.00"), ge=0, le=100)
    sgst_percentage: Optional[Decimal] = Field(default=Decimal("9.00"), ge=0, le=100)
    igst_percentage: Optional[Decimal] = Field(default=Decimal("18.00"), ge=0, le=100)
    
    # Invoice/Receipt settings
    invoice_terms: Optional[str] = None
    invoice_footer: Optional[str] = None
    receipt_footer: Optional[str] = None


class HospitalSettingsCreate(HospitalSettingsBase):
    hospital_id: int


class HospitalSettingsUpdate(BaseModel):
    hospital_name: Optional[str] = None
    hospital_address: Optional[str] = None
    hospital_city: Optional[str] = None
    hospital_state: Optional[str] = None
    hospital_pincode: Optional[str] = None
    hospital_phone: Optional[str] = None
    hospital_email: Optional[str] = None
    hospital_website: Optional[str] = None
    gst_number: Optional[str] = None
    pan_number: Optional[str] = None
    hospital_logo_url: Optional[str] = None
    opd_prefix: Optional[str] = None
    ipd_prefix: Optional[str] = None
    receipt_prefix: Optional[str] = None
    invoice_prefix: Optional[str] = None
    max_discount_percentage: Optional[Decimal] = None
    discount_approval_threshold: Optional[Decimal] = None
    default_tax_percentage: Optional[Decimal] = None
    enable_gst: Optional[bool] = None
    cgst_percentage: Optional[Decimal] = None
    sgst_percentage: Optional[Decimal] = None
    igst_percentage: Optional[Decimal] = None
    invoice_terms: Optional[str] = None
    invoice_footer: Optional[str] = None
    receipt_footer: Optional[str] = None


class HospitalSettingsResponse(HospitalSettingsBase):
    id: int
    hospital_id: int
    
    class Config:
        from_attributes = True


class BillSeriesConfigBase(BaseModel):
    series_type: str = Field(..., description="OPD, IPD, RECEIPT, INVOICE")
    prefix: str
    starting_number: int = 1
    number_length: int = 6
    suffix: str = ""


class BillSeriesConfigCreate(BillSeriesConfigBase):
    hospital_id: int


class BillSeriesConfigResponse(BillSeriesConfigBase):
    id: int
    hospital_id: int
    is_active: bool
    
    class Config:
        from_attributes = True


class SerialNumberRequest(BaseModel):
    series_type: str = Field(..., description="OPD, IPD, RECEIPT, INVOICE")
    financial_year: str = Field(..., description="e.g., 2024-25")


class SerialNumberResponse(BaseModel):
    serial_number: str
    series_type: str
    financial_year: str
    current_number: int
