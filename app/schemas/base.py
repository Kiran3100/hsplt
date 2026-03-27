"""
Base schemas for common patterns and validation.
"""
from pydantic import BaseModel, Field, field_validator, ConfigDict
from typing import Optional, List
from datetime import datetime


class BaseSchema(BaseModel):
    """Base schema with common configuration"""
    
    model_config = ConfigDict(
        from_attributes=True,
        use_enum_values=True,
        json_encoders={
            datetime: lambda v: v.isoformat()
        }
    )


class TenantBaseSchema(BaseSchema):
    """Base schema for multi-tenant entities"""
    hospital_id: int = Field(..., description="Hospital ID for tenant isolation")


class TimestampMixin(BaseModel):
    """Mixin for timestamp fields"""
    created_at: datetime
    updated_at: datetime
    is_active: bool


class PaginationParams(BaseModel):
    """Standard pagination parameters"""
    page: int = Field(1, ge=1, description="Page number (1-based)")
    size: int = Field(20, ge=1, le=100, description="Items per page")
    
    @property
    def offset(self) -> int:
        return (self.page - 1) * self.size


class PaginatedResponse(BaseModel):
    """Standard paginated response wrapper"""
    items: List[BaseSchema]
    total: int
    page: int
    size: int
    pages: int
    
    @field_validator('pages', mode='before')
    @classmethod
    def calculate_pages(cls, v, info):
        values = info.data
        total = values.get('total', 0)
        size = values.get('size', 20)
        return (total + size - 1) // size if total > 0 else 0


class FilterParams(BaseModel):
    """Base filter parameters"""
    search: Optional[str] = Field(None, description="Search term")
    is_active: Optional[bool] = Field(None, description="Filter by active status")
    created_from: Optional[str] = Field(None, pattern=r'^\d{4}-\d{2}-\d{2}$', description="Created from date (YYYY-MM-DD)")
    created_to: Optional[str] = Field(None, pattern=r'^\d{4}-\d{2}-\d{2}$', description="Created to date (YYYY-MM-DD)")


class SortParams(BaseModel):
    """Standard sorting parameters"""
    sort_by: str = Field("created_at", description="Field to sort by")
    sort_order: str = Field("desc", pattern=r'^(asc|desc)$', description="Sort order")


class APIResponse(BaseModel):
    """Standard API response wrapper"""
    success: bool = True
    message: str = "Operation completed successfully"
    data: Optional[BaseSchema] = None
    errors: Optional[List[str]] = None