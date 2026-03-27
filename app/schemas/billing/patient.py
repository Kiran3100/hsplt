from typing import Optional, List, Dict, Any
from uuid import UUID
from datetime import date
from pydantic import BaseModel, Field, EmailStr

from app.schemas.billing.base import BaseSchema, TimestampSchema


class PatientBase(BaseModel):
    """Base patient schema"""
    patient_number: str = Field(..., max_length=50)
    mrn: Optional[str] = Field(None, max_length=50)
    hospital_id: Optional[UUID] = None
    first_name: str = Field(..., max_length=100)
    last_name: str = Field(..., max_length=100)
    date_of_birth: Optional[date] = None
    gender: Optional[str] = Field(None, max_length=10)
    blood_group: Optional[str] = Field(None, max_length=5)
    phone: Optional[str] = Field(None, max_length=20)
    email: Optional[EmailStr] = None
    address: Optional[str] = None
    
    # Emergency contact
    emergency_contact_name: Optional[str] = Field(None, max_length=100)
    emergency_contact_phone: Optional[str] = Field(None, max_length=20)
    emergency_contact_relation: Optional[str] = Field(None, max_length=50)
    
    # Insurance flag (details managed via Insurance Info endpoints)
    has_insurance: Optional[str] = Field("No", max_length=10, description="Yes or No")
    
    # Medical information
    allergies: Optional[List[str]] = None
    chronic_conditions: Optional[List[str]] = None
    current_medications: Optional[List[Dict[str, Any]]] = None


class PatientCreate(PatientBase):
    """Schema for creating a patient"""
    pass


class PatientUpdate(BaseModel):
    """Schema for updating a patient"""
    patient_number: Optional[str] = Field(None, max_length=50)
    mrn: Optional[str] = Field(None, max_length=50)
    hospital_id: Optional[UUID] = None
    first_name: Optional[str] = Field(None, max_length=100)
    last_name: Optional[str] = Field(None, max_length=100)
    date_of_birth: Optional[date] = None
    gender: Optional[str] = Field(None, max_length=10)
    blood_group: Optional[str] = Field(None, max_length=5)
    phone: Optional[str] = Field(None, max_length=20)
    email: Optional[EmailStr] = None
    address: Optional[str] = None
    
    # Emergency contact
    emergency_contact_name: Optional[str] = Field(None, max_length=100)
    emergency_contact_phone: Optional[str] = Field(None, max_length=20)
    emergency_contact_relation: Optional[str] = Field(None, max_length=50)
    
    # Insurance flag (details managed via Insurance Info endpoints)
    has_insurance: Optional[str] = Field(None, max_length=10, description="Yes or No")
    
    # Medical information
    allergies: Optional[List[str]] = None
    chronic_conditions: Optional[List[str]] = None
    current_medications: Optional[List[Dict[str, Any]]] = None


class PatientResponse(PatientBase, TimestampSchema):
    """Schema for patient response"""
    patient_id: int = Field(validation_alias="id", serialization_alias="patient_id")
    
    class Config:
        from_attributes = True
        populate_by_name = True
