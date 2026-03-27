"""
Pydantic schemas for discount management
"""
from pydantic import BaseModel, Field, validator
from typing import Optional
from decimal import Decimal
from datetime import datetime
from enum import Enum


class DiscountTypeEnum(str, Enum):
    """Discount type enumeration"""
    PERCENTAGE = "PERCENTAGE"
    FLAT = "FLAT"
    STAFF = "STAFF"
    PACKAGE = "PACKAGE"
    MANAGEMENT = "MANAGEMENT"
    SENIOR_CITIZEN = "SENIOR_CITIZEN"
    INSURANCE = "INSURANCE"


class DiscountStatusEnum(str, Enum):
    """Discount approval status"""
    PENDING = "PENDING"
    APPROVED = "APPROVED"
    REJECTED = "REJECTED"
    AUTO_APPROVED = "AUTO_APPROVED"


# Request Schemas

class ApplyDiscountRequest(BaseModel):
    """Request to apply discount to a bill"""
    discount_type: DiscountTypeEnum
    discount_value: Decimal = Field(..., gt=0, description="Percentage or flat amount")
    discount_reason: str = Field(..., min_length=5, max_length=500)
    requested_by: int = Field(..., gt=0)
    approved_by: Optional[int] = Field(None, gt=0, description="Pre-approval by authorized user")
    
    @validator('discount_value')
    def validate_discount_value(cls, v, values):
        """Validate discount value based on type"""
        if 'discount_type' in values:
            discount_type = values['discount_type']
            if discount_type in [DiscountTypeEnum.PERCENTAGE, DiscountTypeEnum.STAFF, DiscountTypeEnum.SENIOR_CITIZEN]:
                if v > 100:
                    raise ValueError("Percentage discount cannot exceed 100%")
        return v
    
    class Config:
        json_schema_extra = {
            "example": {
                "discount_type": "PERCENTAGE",
                "discount_value": 15.00,
                "discount_reason": "Senior citizen discount",
                "requested_by": 1
            }
        }


class ApproveDiscountRequest(BaseModel):
    """Request to approve/reject discount"""
    approved: bool = Field(..., description="True to approve, False to reject")
    approved_by: int = Field(..., gt=0)
    rejection_reason: Optional[str] = Field(None, max_length=500)
    
    @validator('rejection_reason')
    def validate_rejection_reason(cls, v, values):
        """Rejection reason required if not approved"""
        if 'approved' in values and not values['approved'] and not v:
            raise ValueError("Rejection reason is required when rejecting discount")
        return v
    
    class Config:
        json_schema_extra = {
            "example": {
                "approved": True,
                "approved_by": 2,
                "rejection_reason": None
            }
        }


class DiscountRuleCreate(BaseModel):
    """Create discount rule"""
    discount_type: DiscountTypeEnum
    max_percentage: Optional[Decimal] = Field(None, ge=0, le=100)
    max_flat_amount: Optional[Decimal] = Field(None, ge=0)
    approval_threshold_percentage: Decimal = Field(20.00, ge=0, le=100)
    approval_threshold_amount: Optional[Decimal] = Field(None, ge=0)
    applicable_to_opd: bool = True
    applicable_to_ipd: bool = True
    applicable_to_items: bool = True
    auto_approve_below_threshold: bool = True
    requires_reason: bool = True
    description: Optional[str] = None
    
    class Config:
        json_schema_extra = {
            "example": {
                "discount_type": "PERCENTAGE",
                "max_percentage": 50.00,
                "approval_threshold_percentage": 20.00,
                "applicable_to_opd": True,
                "applicable_to_ipd": True,
                "auto_approve_below_threshold": True,
                "requires_reason": True,
                "description": "Standard percentage discount"
            }
        }


class DiscountRuleUpdate(BaseModel):
    """Update discount rule"""
    max_percentage: Optional[Decimal] = Field(None, ge=0, le=100)
    max_flat_amount: Optional[Decimal] = Field(None, ge=0)
    approval_threshold_percentage: Optional[Decimal] = Field(None, ge=0, le=100)
    approval_threshold_amount: Optional[Decimal] = Field(None, ge=0)
    applicable_to_opd: Optional[bool] = None
    applicable_to_ipd: Optional[bool] = None
    applicable_to_items: Optional[bool] = None
    auto_approve_below_threshold: Optional[bool] = None
    requires_reason: Optional[bool] = None
    is_active: Optional[bool] = None
    description: Optional[str] = None


# Response Schemas

class DiscountApprovalResponse(BaseModel):
    """Discount approval response"""
    id: int
    bill_type: str
    bill_id: int
    bill_number: str
    discount_type: DiscountTypeEnum
    discount_value: Decimal
    discount_amount: Decimal
    discount_reason: str
    gross_total: Decimal
    net_total: Decimal
    status: DiscountStatusEnum
    requested_by: int
    requested_at: datetime
    approved_by: Optional[int] = None
    approved_at: Optional[datetime] = None
    rejection_reason: Optional[str] = None
    requires_approval: bool
    
    class Config:
        from_attributes = True


class DiscountRuleResponse(BaseModel):
    """Discount rule response"""
    id: int
    discount_type: DiscountTypeEnum
    max_percentage: Optional[Decimal] = None
    max_flat_amount: Optional[Decimal] = None
    approval_threshold_percentage: Optional[Decimal] = None
    approval_threshold_amount: Optional[Decimal] = None
    applicable_to_opd: bool
    applicable_to_ipd: bool
    applicable_to_items: bool
    auto_approve_below_threshold: bool
    requires_reason: bool
    is_active: bool
    description: Optional[str] = None
    created_at: datetime
    updated_at: datetime
    
    class Config:
        from_attributes = True


class DiscountHistoryResponse(BaseModel):
    """Discount history response"""
    id: int
    bill_type: str
    bill_id: int
    bill_number: str
    action: str
    discount_type: Optional[DiscountTypeEnum] = None
    old_discount_amount: Optional[Decimal] = None
    new_discount_amount: Optional[Decimal] = None
    performed_by: int
    performed_at: datetime
    reason: Optional[str] = None
    remarks: Optional[str] = None
    
    class Config:
        from_attributes = True


class ApplyDiscountResponse(BaseModel):
    """Response after applying discount"""
    success: bool
    bill_id: int
    bill_number: str
    discount_amount: float
    discount_percentage: float
    net_total: float
    total_amount: float
    requires_approval: bool
    approval_status: str
    message: str


class ApproveDiscountResponse(BaseModel):
    """Response after approving/rejecting discount"""
    success: bool
    approval_id: int
    status: str
    message: str
