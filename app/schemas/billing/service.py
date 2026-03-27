from typing import Optional
from decimal import Decimal
from datetime import date
from pydantic import BaseModel, Field

from app.schemas.billing.base import BaseSchema, TimestampSchema


class ServiceBase(BaseModel):
    """Base service schema"""
    name: str = Field(..., max_length=200)
    code: str = Field(..., max_length=50)
    description: Optional[str] = None
    base_price: Decimal = Field(..., ge=0)
    service_type: Optional[str] = Field(None, max_length=50)
    department_id: Optional[int] = Field(None, description="Department ID (optional)")
    is_active: bool = True


class ServiceCreate(ServiceBase):
    """Schema for creating a service"""
    pass


class ServiceUpdate(BaseModel):
    """Schema for updating a service"""
    name: Optional[str] = Field(None, max_length=200)
    code: Optional[str] = Field(None, max_length=50)
    description: Optional[str] = None
    base_price: Optional[Decimal] = Field(None, ge=0)
    service_type: Optional[str] = Field(None, max_length=50)
    department_id: Optional[int] = None
    is_active: Optional[bool] = None


class ServiceResponse(ServiceBase, TimestampSchema):
    """Schema for service response"""
    service_id: int = Field(validation_alias="id", serialization_alias="service_id")
    
    class Config:
        from_attributes = True
        populate_by_name = True


class ServicePriceBase(BaseModel):
    """Base service price schema"""
    service_id: int
    price: Decimal = Field(..., ge=0)
    effective_from: date
    effective_to: Optional[date] = None
    created_by: Optional[str] = None


class ServicePriceCreate(ServicePriceBase):
    """Schema for creating service price"""
    pass


class ServicePriceResponse(ServicePriceBase):
    """Schema for service price response"""
    service_price_id: int = Field(validation_alias="id", serialization_alias="service_price_id")
    created_at: Optional[date] = None
    
    class Config:
        from_attributes = True
        populate_by_name = True


class TaxConfigBase(BaseModel):
    """Base tax config schema"""
    service_id: int
    tax_name: Optional[str] = Field(None, max_length=50)
    tax_percentage: Decimal = Field(..., ge=0, le=100)
    is_active: bool = True


class TaxConfigCreate(TaxConfigBase):
    """Schema for creating tax config"""
    pass


class TaxConfigResponse(TaxConfigBase):
    """Schema for tax config response"""
    tax_config_id: int = Field(validation_alias="id", serialization_alias="tax_config_id")
    created_at: Optional[date] = None
    
    class Config:
        from_attributes = True
        populate_by_name = True
