"""
Pydantic schemas for digital prescription functionality.
"""
from datetime import datetime
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field, validator
from uuid import UUID
import uuid

from app.core.enums import (
    PrescriptionStatus, IntegrationType, IntegrationStatus, TestUrgency
)
from app.core.utils import validate_medicine_id


# ============================================================================
# REQUEST SCHEMAS
# ============================================================================

class PrescriptionCreateRequest(BaseModel):
    """Schema for creating a prescription"""
    diagnosis: str = Field(..., description="Primary diagnosis")
    clinical_notes: Optional[str] = Field(None, description="Additional clinical notes")
    follow_up_date: Optional[str] = Field(None, description="Follow-up date (YYYY-MM-DD)")
    
    @validator('follow_up_date')
    def validate_follow_up_date(cls, v):
        if v:
            try:
                datetime.strptime(v, '%Y-%m-%d')
                return v
            except ValueError:
                raise ValueError('Follow-up date must be in YYYY-MM-DD format')
        return v


class PrescriptionUpdateRequest(BaseModel):
    """Schema for updating a prescription"""
    diagnosis: Optional[str] = Field(None, description="Updated diagnosis")
    clinical_notes: Optional[str] = Field(None, description="Updated clinical notes")
    follow_up_date: Optional[str] = Field(None, description="Updated follow-up date (YYYY-MM-DD)")
    
    @validator('follow_up_date')
    def validate_follow_up_date(cls, v):
        if v:
            try:
                datetime.strptime(v, '%Y-%m-%d')
                return v
            except ValueError:
                raise ValueError('Follow-up date must be in YYYY-MM-DD format')
        return v


class MedicineItemRequest(BaseModel):
    """Schema for adding medicine to prescription"""
    medicine_id: Optional[str] = Field(None, description="Medicine ID from master data")
    medicine_name: str = Field(..., description="Medicine name")
    medicine_strength: Optional[str] = Field(None, description="Medicine strength (e.g., 500mg)")
    medicine_form: Optional[str] = Field(None, description="Medicine form (TABLET, CAPSULE, etc.)")
    dose: str = Field(..., description="Dose per administration (e.g., 1 tablet, 5ml)")
    frequency: str = Field(..., description="Frequency (e.g., 1-0-1, twice daily)")
    duration_days: int = Field(..., gt=0, description="Duration in days")
    instructions: Optional[str] = Field(None, description="Special instructions")
    quantity: Optional[int] = Field(None, gt=0, description="Total quantity to dispense")
    quantity_unit: Optional[str] = Field(None, description="Quantity unit (tablets, bottles)")
    
    @validator('medicine_id')
    def validate_medicine_id_format(cls, v):
        """Validate medicine ID format if provided"""
        if v is not None and v.strip():
            is_valid, error_message = validate_medicine_id(v)
            if not is_valid:
                # For backward compatibility, log warning but don't fail validation
                # In production, you might want to raise ValueError(error_message)
                pass
        return v


class LabOrderItemRequest(BaseModel):
    """Schema for adding lab test to prescription"""
    lab_test_id: Optional[str] = Field(None, description="Lab test ID from catalog")
    test_name: str = Field(..., description="Test name")
    test_code: Optional[str] = Field(None, description="Test code")
    test_category: Optional[str] = Field(None, description="Test category")
    clinical_notes: Optional[str] = Field(None, description="Clinical notes for test")
    urgency: TestUrgency = Field(TestUrgency.ROUTINE, description="Test urgency")


class PrescriptionItemsRequest(BaseModel):
    """Schema for adding medicines and lab tests to prescription"""
    medicines: Optional[List[MedicineItemRequest]] = Field(None, description="Medicine items")
    lab_orders: Optional[List[LabOrderItemRequest]] = Field(None, description="Lab test items")


class SignPrescriptionRequest(BaseModel):
    """Schema for signing a prescription"""
    signature_type: str = Field("DIGITAL", description="Signature type")
    doctor_notes: Optional[str] = Field(None, description="Additional notes from doctor")


class SharePrescriptionRequest(BaseModel):
    """Schema for sharing prescription"""
    share_with: List[str] = Field(..., description="Who to share with (PATIENT, etc.)")
    notification_channels: List[str] = Field(..., description="Notification channels (EMAIL, SMS)")
    message: Optional[str] = Field(None, description="Custom message")


# PHARMACY MODULE REMOVED
# class SendToPharmacyRequest(BaseModel):
#     """Schema for sending prescription to pharmacy"""
#     pharmacy_id: Optional[str] = Field(None, description="Specific pharmacy ID")
#     priority: str = Field("NORMAL", description="Priority level")
#     notes: Optional[str] = Field(None, description="Notes for pharmacy")


class SendToLabRequest(BaseModel):
    """Schema for sending prescription to lab"""
    lab_id: Optional[str] = Field(None, description="Specific lab ID")
    preferred_date: Optional[str] = Field(None, description="Preferred collection date (YYYY-MM-DD)")
    notes: Optional[str] = Field(None, description="Notes for lab")
    
    @validator('preferred_date')
    def validate_preferred_date(cls, v):
        if v:
            try:
                datetime.strptime(v, '%Y-%m-%d')
                return v
            except ValueError:
                raise ValueError('Preferred date must be in YYYY-MM-DD format')
        return v


# ============================================================================
# RESPONSE SCHEMAS
# ============================================================================

class PrescriptionMedicineResponse(BaseModel):
    """Schema for prescription medicine response"""
    id: str
    medicine_id: Optional[str]
    medicine_name: str
    medicine_strength: Optional[str]
    medicine_form: Optional[str]
    dose: str
    frequency: str
    duration_days: int
    instructions: Optional[str]
    quantity: Optional[int]
    quantity_unit: Optional[str]
    created_at: datetime

    class Config:
        from_attributes = True


class PrescriptionLabOrderResponse(BaseModel):
    """Schema for prescription lab order response"""
    id: str
    lab_test_id: Optional[str]
    test_name: str
    test_code: Optional[str]
    test_category: Optional[str]
    clinical_notes: Optional[str]
    urgency: TestUrgency
    sent_to_lab: bool
    lab_order_id: Optional[str]
    sent_at: Optional[datetime]
    created_at: datetime

    class Config:
        from_attributes = True


class PDFResponse(BaseModel):
    """Schema for PDF response"""
    pdf_id: str
    file_name: str
    download_url: str
    access_token: Optional[str]
    expires_at: Optional[datetime]
    file_size: Optional[int]
    generated_at: datetime

    class Config:
        from_attributes = True


class IntegrationStatusResponse(BaseModel):
    """Schema for integration status response"""
    integration_id: str
    integration_type: IntegrationType
    status: IntegrationStatus
    sent_at: Optional[datetime]
    acknowledged_at: Optional[datetime]
    external_reference: Optional[str]
    error_message: Optional[str]
    retry_count: int
    next_retry_at: Optional[datetime]

    class Config:
        from_attributes = True


class AppointmentInfo(BaseModel):
    """Appointment information for prescription"""
    id: str
    patient_name: str
    appointment_date: str


class PrescriptionResponse(BaseModel):
    """Schema for prescription response"""
    prescription_id: str
    prescription_no: str
    tele_appointment_id: str
    appointment: Optional[AppointmentInfo]
    doctor_id: str
    patient_id: str
    diagnosis: str
    clinical_notes: Optional[str]
    follow_up_date: Optional[str]
    status: PrescriptionStatus
    signed_at: Optional[datetime]
    signed_by: Optional[str]
    cancelled_at: Optional[datetime]
    cancellation_reason: Optional[str]
    medicines: List[PrescriptionMedicineResponse]
    lab_orders: List[PrescriptionLabOrderResponse]
    medicines_count: int
    lab_orders_count: int
    pdf_available: bool
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class PrescriptionListItem(BaseModel):
    """Schema for prescription list item"""
    prescription_id: str
    prescription_no: str
    doctor_name: Optional[str]
    diagnosis: str
    status: PrescriptionStatus
    signed_at: Optional[datetime]
    medicines_count: int
    lab_orders_count: int
    pdf_available: bool
    created_at: datetime

    class Config:
        from_attributes = True


class PrescriptionListResponse(BaseModel):
    """Schema for prescription list response"""
    prescriptions: List[PrescriptionListItem]
    pagination: Dict[str, Any]


# ============================================================================
# OPERATION RESPONSE SCHEMAS
# ============================================================================

class PrescriptionCreateResponse(BaseModel):
    """Schema for prescription creation response"""
    prescription_id: str
    prescription_no: str
    status: PrescriptionStatus
    created_at: datetime


class PrescriptionUpdateResponse(BaseModel):
    """Schema for prescription update response"""
    prescription_id: str
    status: PrescriptionStatus
    updated_at: datetime


class ItemsAddResponse(BaseModel):
    """Schema for items addition response"""
    medicines_added: int
    lab_orders_added: int
    prescription_status: PrescriptionStatus


class SignResponse(BaseModel):
    """Schema for prescription signing response"""
    prescription_id: str
    status: PrescriptionStatus
    signed_at: datetime
    pdf_generated: bool


class CancelResponse(BaseModel):
    """Schema for prescription cancellation response"""
    prescription_id: str
    status: PrescriptionStatus
    cancelled_at: datetime


class ShareResponse(BaseModel):
    """Schema for prescription sharing response"""
    shared_with: List[str]
    notifications_sent: int
    share_link: Optional[str]


class IntegrationResponse(BaseModel):
    """Schema for integration response"""
    integration_id: str
    status: IntegrationStatus
    estimated_processing_time: Optional[str]
    lab_orders_count: Optional[int]


class IntegrationStatusListResponse(BaseModel):
    """Schema for integration status list response"""
    prescription_id: str
    integrations: List[IntegrationStatusResponse]


# ============================================================================
# VALIDATION SCHEMAS
# ============================================================================

class PrescriptionValidationError(BaseModel):
    """Schema for prescription validation errors"""
    field: str
    message: str
    code: str


class PrescriptionValidationResponse(BaseModel):
    """Schema for prescription validation response"""
    valid: bool
    errors: List[PrescriptionValidationError]
    warnings: List[PrescriptionValidationError]