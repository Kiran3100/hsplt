"""Schemas for insurance claims."""
from typing import Optional
from uuid import UUID
from datetime import datetime
from decimal import Decimal
from pydantic import BaseModel, Field


class InsuranceClaimCreate(BaseModel):
    bill_id: UUID
    patient_id: UUID
    insurance_provider_name: str = Field(..., max_length=255)
    policy_number: Optional[str] = None
    claim_amount: float = Field(..., ge=0)


class InsuranceClaimUpdate(BaseModel):
    status: Optional[str] = None
    approved_amount: Optional[float] = None
    rejection_reason: Optional[str] = None
    settlement_reference: Optional[str] = None


class InsuranceClaimResponse(BaseModel):
    id: UUID
    hospital_id: UUID
    bill_id: UUID
    patient_id: UUID
    insurance_provider_name: str
    policy_number: Optional[str]
    claim_amount: Decimal
    approved_amount: Optional[Decimal]
    status: str
    rejection_reason: Optional[str]
    settlement_reference: Optional[str]
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True
