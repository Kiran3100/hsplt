"""
Schemas for billing and accounts models.
"""
from pydantic import BaseModel, Field, validator
from typing import Optional, List, Dict, Any
from decimal import Decimal
from datetime import datetime
from app.schemas.base import BaseSchema, TenantBaseSchema, TimestampMixin
from app.core.enums import InvoiceStatus, PaymentStatus


# Invoice Schemas
class InvoiceBase(BaseModel):
    """Base invoice fields"""
    patient_id: int
    invoice_number: str = Field(..., min_length=5, max_length=50)
    invoice_date: str = Field(..., pattern=r'^\d{4}-\d{2}-\d{2}$')
    due_date: str = Field(..., pattern=r'^\d{4}-\d{2}-\d{2}$')
    invoice_type: str = Field(..., pattern=r'^(OPD|IPD|LAB)$')  # PHARMACY REMOVED
    appointment_id: Optional[int] = None
    admission_id: Optional[int] = None
    subtotal: Decimal = Field(..., ge=0, decimal_places=2)
    tax_amount: Decimal = Field(0, ge=0, decimal_places=2)
    discount_amount: Decimal = Field(0, ge=0, decimal_places=2)
    total_amount: Decimal = Field(..., ge=0, decimal_places=2)
    notes: Optional[str] = None
    terms_and_conditions: Optional[str] = None
    billing_address: Optional[Dict[str, Any]] = None
    
    @validator('total_amount')
    def validate_total_amount(cls, v, values):
        subtotal = values.get('subtotal', 0)
        tax_amount = values.get('tax_amount', 0)
        discount_amount = values.get('discount_amount', 0)
        expected_total = subtotal + tax_amount - discount_amount
        if abs(v - expected_total) > 0.01:  # Allow for rounding differences
            raise ValueError('Total amount must equal subtotal + tax - discount')
        return v


class InvoiceCreate(InvoiceBase):
    """Schema for creating an invoice"""
    items: List[Dict[str, Any]] = Field(..., min_items=1)


class InvoiceUpdate(BaseModel):
    """Schema for updating an invoice"""
    due_date: Optional[str] = Field(None, pattern=r'^\d{4}-\d{2}-\d{2}$')
    status: Optional[InvoiceStatus] = None
    notes: Optional[str] = None
    terms_and_conditions: Optional[str] = None
    billing_address: Optional[Dict[str, Any]] = None


class InvoiceResponse(InvoiceBase, TenantBaseSchema, TimestampMixin):
    """Schema for invoice API responses"""
    id: int
    status: InvoiceStatus
    paid_amount: Decimal
    balance_amount: Decimal
    
    # Related information
    patient_name: Optional[str] = None
    items: Optional[List[Dict[str, Any]]] = None
    payments: Optional[List[Dict[str, Any]]] = None


# Invoice Item Schemas
class InvoiceItemBase(BaseModel):
    """Base invoice item fields"""
    invoice_id: int
    item_type: str = Field(..., pattern=r'^(CONSULTATION|PROCEDURE|MEDICATION|LAB_TEST|ROOM_CHARGE|OTHER)$')
    item_code: Optional[str] = Field(None, max_length=50)
    item_name: str = Field(..., min_length=2, max_length=255)
    description: Optional[str] = None
    quantity: Decimal = Field(..., gt=0, decimal_places=3)
    unit_price: Decimal = Field(..., ge=0, decimal_places=2)
    discount_percentage: Decimal = Field(0, ge=0, le=100, decimal_places=2)
    discount_amount: Decimal = Field(0, ge=0, decimal_places=2)
    tax_percentage: Decimal = Field(0, ge=0, le=100, decimal_places=2)
    tax_amount: Decimal = Field(0, ge=0, decimal_places=2)
    line_total: Decimal = Field(..., ge=0, decimal_places=2)
    doctor_id: Optional[int] = None
    department_id: Optional[int] = None
    service_date: Optional[str] = Field(None, pattern=r'^\d{4}-\d{2}-\d{2}$')


class InvoiceItemCreate(InvoiceItemBase):
    """Schema for creating an invoice item"""
    pass


class InvoiceItemUpdate(BaseModel):
    """Schema for updating an invoice item"""
    description: Optional[str] = None
    quantity: Optional[Decimal] = Field(None, gt=0, decimal_places=3)
    unit_price: Optional[Decimal] = Field(None, ge=0, decimal_places=2)
    discount_percentage: Optional[Decimal] = Field(None, ge=0, le=100, decimal_places=2)
    discount_amount: Optional[Decimal] = Field(None, ge=0, decimal_places=2)
    tax_percentage: Optional[Decimal] = Field(None, ge=0, le=100, decimal_places=2)
    tax_amount: Optional[Decimal] = Field(None, ge=0, decimal_places=2)
    line_total: Optional[Decimal] = Field(None, ge=0, decimal_places=2)


class InvoiceItemResponse(InvoiceItemBase, TenantBaseSchema, TimestampMixin):
    """Schema for invoice item API responses"""
    id: int
    
    # Related information
    doctor_name: Optional[str] = None
    department_name: Optional[str] = None


# Payment Schemas
class PaymentBase(BaseModel):
    """Base payment fields"""
    invoice_id: int
    patient_id: int
    payment_number: str = Field(..., min_length=5, max_length=50)
    transaction_id: Optional[str] = Field(None, max_length=100)
    payment_date: str = Field(..., pattern=r'^\d{4}-\d{2}-\d{2}$')
    payment_time: str = Field(..., pattern=r'^\d{2}:\d{2}:\d{2}$')
    amount: Decimal = Field(..., gt=0, decimal_places=2)
    payment_method: str = Field(..., pattern=r'^(CASH|CARD|UPI|NET_BANKING|CHEQUE|WALLET)$')
    payment_details: Optional[Dict[str, Any]] = None
    gateway_name: Optional[str] = Field(None, max_length=50)
    gateway_transaction_id: Optional[str] = Field(None, max_length=100)
    gateway_response: Optional[Dict[str, Any]] = None
    notes: Optional[str] = None


class PaymentCreate(PaymentBase):
    """Schema for creating a payment"""
    pass


class PaymentUpdate(BaseModel):
    """Schema for updating a payment"""
    status: Optional[PaymentStatus] = None
    gateway_transaction_id: Optional[str] = Field(None, max_length=100)
    gateway_response: Optional[Dict[str, Any]] = None
    notes: Optional[str] = None


class PaymentResponse(PaymentBase, TenantBaseSchema, TimestampMixin):
    """Schema for payment API responses"""
    id: int
    status: PaymentStatus
    processed_by: Optional[int] = None
    processed_at: Optional[datetime] = None
    is_reconciled: bool
    reconciled_at: Optional[datetime] = None
    reconciled_by: Optional[int] = None
    
    # Related information
    patient_name: Optional[str] = None
    processor_name: Optional[str] = None
    reconciler_name: Optional[str] = None


# Insurance Claim Schemas
class InsuranceClaimBase(BaseModel):
    """Base insurance claim fields"""
    patient_id: int
    invoice_id: int
    claim_number: str = Field(..., min_length=5, max_length=50)
    policy_number: str = Field(..., min_length=5, max_length=100)
    insurance_provider: str = Field(..., min_length=2, max_length=100)
    insurance_tpa: Optional[str] = Field(None, max_length=100)
    claim_date: str = Field(..., pattern=r'^\d{4}-\d{2}-\d{2}$')
    treatment_date: str = Field(..., pattern=r'^\d{4}-\d{2}-\d{2}$')
    claimed_amount: Decimal = Field(..., gt=0, decimal_places=2)
    deductible_amount: Decimal = Field(0, ge=0, decimal_places=2)
    copay_amount: Decimal = Field(0, ge=0, decimal_places=2)
    supporting_documents: Optional[List[str]] = Field(default_factory=list)
    notes: Optional[str] = None


class InsuranceClaimCreate(InsuranceClaimBase):
    """Schema for creating an insurance claim"""
    pass


class InsuranceClaimUpdate(BaseModel):
    """Schema for updating an insurance claim"""
    status: Optional[str] = Field(None, pattern=r'^(SUBMITTED|UNDER_REVIEW|APPROVED|REJECTED|PAID)$')
    approved_amount: Optional[Decimal] = Field(None, ge=0, decimal_places=2)
    approval_date: Optional[str] = Field(None, pattern=r'^\d{4}-\d{2}-\d{2}$')
    rejection_reason: Optional[str] = None
    settlement_date: Optional[str] = Field(None, pattern=r'^\d{4}-\d{2}-\d{2}$')
    settlement_amount: Optional[Decimal] = Field(None, ge=0, decimal_places=2)
    settlement_reference: Optional[str] = Field(None, max_length=100)
    supporting_documents: Optional[List[str]] = None
    notes: Optional[str] = None


class InsuranceClaimResponse(InsuranceClaimBase, TenantBaseSchema, TimestampMixin):
    """Schema for insurance claim API responses"""
    id: int
    status: str
    approved_amount: Decimal
    submitted_by: Optional[int] = None
    submitted_at: Optional[datetime] = None
    reviewed_at: Optional[datetime] = None
    approval_date: Optional[str] = None
    rejection_reason: Optional[str] = None
    settlement_date: Optional[str] = None
    settlement_amount: Optional[Decimal] = None
    settlement_reference: Optional[str] = None
    
    # Related information
    patient_name: Optional[str] = None
    submitter_name: Optional[str] = None


# Billing Summary Schemas
class BillingSummary(BaseModel):
    """Schema for billing summary/dashboard"""
    total_invoices: int
    total_amount: Decimal
    paid_amount: Decimal
    pending_amount: Decimal
    overdue_amount: Decimal
    
    # By status
    draft_invoices: int
    sent_invoices: int
    paid_invoices: int
    overdue_invoices: int
    
    # By type
    opd_amount: Decimal
    ipd_amount: Decimal
    # pharmacy_amount: Decimal  # PHARMACY REMOVED
    lab_amount: Decimal


class PaymentSummary(BaseModel):
    """Schema for payment summary/dashboard"""
    total_payments: int
    total_amount: Decimal
    
    # By method
    cash_amount: Decimal
    card_amount: Decimal
    upi_amount: Decimal
    net_banking_amount: Decimal
    
    # By status
    pending_payments: int
    successful_payments: int
    failed_payments: int