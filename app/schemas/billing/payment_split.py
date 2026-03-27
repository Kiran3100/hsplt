"""
Payment Split Schemas
"""
from pydantic import BaseModel, Field
from typing import Optional, List
from decimal import Decimal
from datetime import datetime, date


class PaymentSplitCreate(BaseModel):
    payment_mode: str = Field(..., description="CASH, CARD, UPI, CHEQUE, NEFT, etc.")
    amount: Decimal = Field(..., gt=0)
    transaction_id: Optional[str] = None
    card_last_4: Optional[str] = None
    bank_name: Optional[str] = None
    upi_id: Optional[str] = None
    cheque_number: Optional[str] = None
    cheque_date: Optional[date] = None


class PaymentSplitResponse(PaymentSplitCreate):
    id: int
    payment_id: int
    
    class Config:
        from_attributes = True


class CreateSplitPaymentRequest(BaseModel):
    payment_id: int
    splits: List[PaymentSplitCreate]


class AdvancePaymentCreate(BaseModel):
    patient_id: int
    amount: Decimal = Field(..., gt=0)
    payment_mode: str
    received_by: int
    remarks: Optional[str] = None


class AdvancePaymentResponse(BaseModel):
    id: int
    patient_id: int
    advance_number: str
    amount: Decimal
    utilized_amount: Decimal
    balance_amount: Decimal
    payment_method: str  # Fixed: was payment_mode
    payment_date: datetime  # Fixed: was received_at
    collected_by: int  # Fixed: was received_by
    status: str
    notes: Optional[str] = None  # Fixed: was remarks
    
    class Config:
        from_attributes = True


class AdvanceUtilizationCreate(BaseModel):
    advance_id: int
    bill_id: int
    bill_type: str = Field(..., description="OPD or IPD")
    utilized_amount: Decimal = Field(..., gt=0)
    utilized_by: int


class AdvanceUtilizationResponse(BaseModel):
    id: int
    advance_payment_id: int  # Fixed: was advance_id
    bill_id: int
    bill_type: str
    bill_number: str
    utilized_amount: Decimal
    utilized_date: datetime  # Fixed: was utilized_at
    utilized_by: int
    
    class Config:
        from_attributes = True





class PaginatedAdvanceResponse(BaseModel):
    advances: List[AdvancePaymentResponse]
    total: int
    skip: int
    limit: int


class AdvancePaymentFilter(BaseModel):
    status: Optional[str] = None
    patient_id: Optional[int] = None
    date_from: Optional[date] = None
    date_to: Optional[date] = None
