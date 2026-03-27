from datetime import datetime
from pydantic import BaseModel, ConfigDict


class BaseSchema(BaseModel):
    """Base schema with common configuration"""
    
    model_config = ConfigDict(from_attributes=True)


class TimestampSchema(BaseModel):
    """Schema for timestamp fields"""
    
    created_at: datetime
    updated_at: datetime
    
    model_config = ConfigDict(from_attributes=True)
