"""
Schemas for tenant and subscription models.
"""
from pydantic import BaseModel, Field, validator, EmailStr
from typing import Optional, Dict, Any
from decimal import Decimal
from datetime import datetime
from app.schemas.base import BaseSchema, TimestampMixin
from app.core.enums import SubscriptionPlan, SubscriptionStatus


# Hospital Schemas
class HospitalBase(BaseModel):
    """Base hospital fields"""
    name: str = Field(..., min_length=2, max_length=255)
    registration_number: str = Field(..., min_length=5, max_length=100)
    email: EmailStr
    phone: str = Field(..., pattern=r'^\+?[\d\s\-\(\)]{10,20}$')
    address: str = Field(..., min_length=10)
    city: str = Field(..., min_length=2, max_length=100)
    state: str = Field(..., min_length=2, max_length=100)
    country: str = Field(..., min_length=2, max_length=100)
    pincode: str = Field(..., pattern=r'^\d{5,10}$')
    
    # Optional fields
    license_number: Optional[str] = Field(None, max_length=100)
    established_date: Optional[str] = Field(None, pattern=r'^\d{4}-\d{2}-\d{2}$')
    website: Optional[str] = Field(None, max_length=255)
    logo_url: Optional[str] = Field(None, max_length=500)
    settings: Optional[Dict[str, Any]] = Field(default_factory=dict)


class HospitalCreate(HospitalBase):
    """Schema for creating a hospital"""
    pass


class HospitalUpdate(BaseModel):
    """Schema for updating a hospital"""
    name: Optional[str] = Field(None, min_length=2, max_length=255)
    email: Optional[EmailStr] = None
    phone: Optional[str] = Field(None, pattern=r'^\+?[\d\s\-\(\)]{10,20}$')
    address: Optional[str] = Field(None, min_length=10)
    city: Optional[str] = Field(None, min_length=2, max_length=100)
    state: Optional[str] = Field(None, min_length=2, max_length=100)
    country: Optional[str] = Field(None, min_length=2, max_length=100)
    pincode: Optional[str] = Field(None, pattern=r'^\d{5,10}$')
    license_number: Optional[str] = Field(None, max_length=100)
    established_date: Optional[str] = Field(None, pattern=r'^\d{4}-\d{2}-\d{2}$')
    website: Optional[str] = Field(None, max_length=255)
    logo_url: Optional[str] = Field(None, max_length=500)
    settings: Optional[Dict[str, Any]] = None


class HospitalResponse(HospitalBase, BaseSchema, TimestampMixin):
    """Schema for hospital API responses"""
    id: int
    
    # Computed fields
    subscription_status: Optional[str] = None
    subscription_plan: Optional[str] = None


class HospitalList(BaseModel):
    """Schema for hospital list items"""
    id: int
    name: str
    email: str
    city: str
    state: str
    subscription_status: Optional[str]
    created_at: datetime
    is_active: bool


# Subscription Plan Schemas
class SubscriptionPlanBase(BaseModel):
    """Base subscription plan fields"""
    name: SubscriptionPlan
    display_name: str = Field(..., min_length=2, max_length=100)
    description: Optional[str] = None
    monthly_price: Decimal = Field(..., ge=0, decimal_places=2)
    yearly_price: Decimal = Field(..., ge=0, decimal_places=2)
    max_doctors: int = Field(..., ge=0)
    max_patients: int = Field(..., ge=0)
    max_appointments_per_month: int = Field(..., ge=0)
    max_storage_gb: int = Field(..., ge=1)
    features: Optional[Dict[str, Any]] = Field(default_factory=dict)


class SubscriptionPlanCreate(SubscriptionPlanBase):
    """Schema for creating a subscription plan"""
    pass


class SubscriptionPlanUpdate(BaseModel):
    """Schema for updating a subscription plan"""
    display_name: Optional[str] = Field(None, min_length=2, max_length=100)
    description: Optional[str] = None
    monthly_price: Optional[Decimal] = Field(None, ge=0, decimal_places=2)
    yearly_price: Optional[Decimal] = Field(None, ge=0, decimal_places=2)
    max_doctors: Optional[int] = Field(None, ge=0)
    max_patients: Optional[int] = Field(None, ge=0)
    max_appointments_per_month: Optional[int] = Field(None, ge=0)
    max_storage_gb: Optional[int] = Field(None, ge=1)
    features: Optional[Dict[str, Any]] = None


class SubscriptionPlanResponse(SubscriptionPlanBase, BaseSchema, TimestampMixin):
    """Schema for subscription plan API responses"""
    id: int


# Hospital Subscription Schemas
class HospitalSubscriptionBase(BaseModel):
    """Base hospital subscription fields"""
    plan_id: int
    start_date: str = Field(..., pattern=r'^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}')
    end_date: str = Field(..., pattern=r'^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}')
    is_trial: bool = False
    trial_end_date: Optional[str] = Field(None, pattern=r'^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}')
    auto_renew: bool = True


class HospitalSubscriptionCreate(HospitalSubscriptionBase):
    """Schema for creating a hospital subscription"""
    hospital_id: int


class HospitalSubscriptionUpdate(BaseModel):
    """Schema for updating a hospital subscription"""
    plan_id: Optional[int] = None
    end_date: Optional[str] = Field(None, pattern=r'^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}')
    status: Optional[SubscriptionStatus] = None
    auto_renew: Optional[bool] = None


class HospitalSubscriptionResponse(HospitalSubscriptionBase, BaseSchema, TimestampMixin):
    """Schema for hospital subscription API responses"""
    id: int
    hospital_id: int
    status: SubscriptionStatus
    current_usage: Dict[str, Any]
    
    # Related data
    plan: Optional[SubscriptionPlanResponse] = None