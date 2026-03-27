"""
Staff/Cashier Schemas
"""
from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime


class StaffBase(BaseModel):
    staff_id: str = Field(..., description="Unique staff identifier (e.g., CASH001)")
    name: str = Field(..., description="Full name of the staff member")
    role: str = Field(..., description="Role: CASHIER, SUPERVISOR, MANAGER")
    department: str = Field(default="BILLING", description="Department")
    phone: Optional[str] = Field(None, description="Phone number")
    email: Optional[str] = Field(None, description="Email address")
    employee_id: Optional[str] = Field(None, description="Hospital employee ID")
    designation: Optional[str] = Field(None, description="Job designation")
    shift: Optional[str] = Field(None, description="Shift: MORNING, EVENING, NIGHT")
    can_handle_cash: bool = Field(default=True, description="Can handle cash transactions")
    can_approve_discounts: bool = Field(default=False, description="Can approve discounts")
    max_discount_percentage: int = Field(default=0, description="Maximum discount percentage allowed")
    remarks: Optional[str] = Field(None, description="Additional remarks")


class StaffCreate(StaffBase):
    """Schema for creating new staff member"""
    pass


class StaffUpdate(BaseModel):
    """Schema for updating staff member"""
    name: Optional[str] = None
    role: Optional[str] = None
    department: Optional[str] = None
    phone: Optional[str] = None
    email: Optional[str] = None
    employee_id: Optional[str] = None
    designation: Optional[str] = None
    shift: Optional[str] = None
    is_active: Optional[bool] = None
    can_handle_cash: Optional[bool] = None
    can_approve_discounts: Optional[bool] = None
    max_discount_percentage: Optional[int] = None
    remarks: Optional[str] = None


class StaffResponse(StaffBase):
    """Schema for staff response"""
    id: int
    is_active: bool
    created_at: datetime
    updated_at: Optional[datetime] = None
    last_login: Optional[datetime] = None
    
    class Config:
        from_attributes = True


class CashierListResponse(BaseModel):
    """Schema for listing active cashiers"""
    id: int
    staff_id: str
    name: str
    shift: Optional[str] = None
    is_active: bool
    
    class Config:
        from_attributes = True