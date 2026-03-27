from typing import Optional
from uuid import UUID
from pydantic import BaseModel, Field

from app.schemas.billing.base import BaseSchema, TimestampSchema


class DepartmentBase(BaseModel):
    """Base department schema"""
    hospital_id: Optional[UUID] = None
    department_name: str = Field(..., max_length=100)
    code: str = Field(..., max_length=20)
    description: Optional[str] = None
    head_doctor_id: Optional[int] = None
    is_active: bool = True
    
    model_config = {"populate_by_name": True}


class DepartmentCreate(DepartmentBase):
    """Schema for creating a department"""
    model_config = {
        "populate_by_name": True,
        "json_schema_extra": {
            "example": {
                "department_name": "Cardiology",
                "code": "CARD",
                "description": "Heart and cardiovascular care",
                "is_active": True
            }
        }
    }


class DepartmentUpdate(BaseModel):
    """Schema for updating a department"""
    hospital_id: Optional[UUID] = None
    department_name: Optional[str] = Field(None, max_length=100)
    code: Optional[str] = Field(None, max_length=20)
    description: Optional[str] = None
    head_doctor_id: Optional[int] = None
    is_active: Optional[bool] = None
    
    model_config = {
        "populate_by_name": True,
        "json_schema_extra": {
            "example": {
                "department_name": "Updated Cardiology",
                "description": "Comprehensive heart care services",
                "is_active": True
            }
        }
    }


class DepartmentResponse(BaseModel):
    """Schema for department response"""
    department_id: int
    hospital_id: Optional[UUID] = None
    department_name: str
    code: str
    description: Optional[str] = None
    head_doctor_id: Optional[int] = None
    is_active: bool = True
    created_at: Optional[str] = None
    updated_at: Optional[str] = None
    
    @classmethod
    def from_orm_model(cls, db_model):
        """Convert database model to response schema"""
        return cls(
            department_id=db_model.id,
            hospital_id=db_model.hospital_id,
            department_name=db_model.name,
            code=db_model.code,
            description=db_model.description,
            head_doctor_id=db_model.head_doctor_id,
            is_active=db_model.is_active,
            created_at=str(db_model.created_at) if hasattr(db_model, 'created_at') and db_model.created_at else None,
            updated_at=str(db_model.updated_at) if hasattr(db_model, 'updated_at') and db_model.updated_at else None
        )
    
    model_config = {
        "json_schema_extra": {
            "example": {
                "department_id": 1,
                "hospital_id": 1,
                "department_name": "Cardiology",
                "code": "CARD",
                "description": "Heart and cardiovascular care",
                "head_doctor_id": None,
                "is_active": True,
                "created_at": "2024-01-01T00:00:00",
                "updated_at": "2024-01-01T00:00:00"
            }
        }
    }
