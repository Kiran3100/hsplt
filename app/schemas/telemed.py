"""
Telemedicine API schemas.
"""
from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel, Field


# ============================================================================
# TELE-APPOINTMENT
# ============================================================================

class TeleAppointmentCreate(BaseModel):
    patient_ref: str = Field(..., description="Patient reference (e.g. PAT-001)")
    doctor_ref: str = Field(..., description="Doctor ref (e.g. DOC-xxx) or doctor name")
    scheduled_start: datetime
    scheduled_end: datetime
    reason: Optional[str] = None
    notes: Optional[str] = None


class TeleAppointmentReschedule(BaseModel):
    scheduled_start: datetime
    scheduled_end: datetime
    reason: Optional[str] = None


class TeleAppointmentCancel(BaseModel):
    cancellation_reason: Optional[str] = None


class TeleAppointmentResponse(BaseModel):
    id: str
    hospital_id: str
    patient_id: str
    patient_ref: Optional[str] = None
    doctor_id: str
    doctor_ref: Optional[str] = None
    doctor_name: Optional[str] = None
    scheduled_start: datetime
    scheduled_end: datetime
    reason: Optional[str] = None
    notes: Optional[str] = None
    status: str
    created_by: str
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class TeleAppointmentListResponse(BaseModel):
    items: List[TeleAppointmentResponse]
    total: int


# ============================================================================
# SESSION
# ============================================================================

class TelemedSessionCreate(BaseModel):
    tele_appointment_id: str
    provider: str = "WEBRTC"


class TelemedSessionStart(BaseModel):
    pass


class TelemedSessionEnd(BaseModel):
    end_reason: str = "COMPLETED"


class TelemedSessionResponse(BaseModel):
    id: str
    hospital_id: str
    tele_appointment_id: str
    provider: str
    room_name: Optional[str] = None
    status: str
    scheduled_start: Optional[datetime] = None
    scheduled_end: Optional[datetime] = None
    started_at: Optional[datetime] = None
    ended_at: Optional[datetime] = None
    recording_enabled: bool = False
    recording_status: Optional[str] = None
    duration_seconds: Optional[int] = None
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class TelemedSessionListResponse(BaseModel):
    items: List[TelemedSessionResponse]
    total: int


# ============================================================================
# JOIN TOKEN
# ============================================================================

class JoinTokenRequest(BaseModel):
    device_type: str = "WEB"


class JoinTokenResponse(BaseModel):
    provider: str
    room_name: str
    token: str
    expires_at: datetime
    session_id: str


# ============================================================================
# CHAT / MESSAGES
# ============================================================================

class TelemedMessageCreate(BaseModel):
    message_type: str = "TEXT"  # TEXT, IMAGE, FILE
    content: Optional[str] = None
    file_ref: Optional[str] = None


class TelemedMessageResponse(BaseModel):
    id: str
    session_id: str
    sender_id: str
    sender_role: str
    message_type: str
    content: Optional[str] = None
    file_ref: Optional[str] = None
    created_at: datetime

    class Config:
        from_attributes = True


# ============================================================================
# FILES
# ============================================================================

class TelemedFileCreate(BaseModel):
    file_name: str
    mime_type: Optional[str] = None
    size_bytes: Optional[int] = None
    storage_url: Optional[str] = None
    checksum: Optional[str] = None


class TelemedFileResponse(BaseModel):
    id: str
    session_id: str
    uploaded_by: str
    file_name: str
    mime_type: Optional[str] = None
    size_bytes: Optional[int] = None
    storage_url: Optional[str] = None
    checksum: Optional[str] = None
    created_at: datetime

    class Config:
        from_attributes = True


# ============================================================================
# CONSULTATION NOTES (SOAP)
# ============================================================================

class TelemedNoteCreate(BaseModel):
    soap_json: Optional[str] = None
    soap_text: Optional[str] = None


class TelemedNoteResponse(BaseModel):
    id: str
    session_id: str
    doctor_id: str
    soap_json: Optional[str] = None
    soap_text: Optional[str] = None
    version: int
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


# ============================================================================
# PRESCRIPTION (Telemed only - no pharmacy DB; doctor types medicine name + directions)
# ============================================================================

class TelemedMedicineItem(BaseModel):
    """Medicine line for telemed prescription. No pharmacy lookup."""
    medicine_name: str = Field(..., description="Medicine name (free text)")
    medicine_strength: Optional[str] = Field(None, description="e.g. 500mg")
    dose: str = Field(..., description="e.g. 1 tablet, 5ml")
    frequency: str = Field(..., description="e.g. twice daily, TID")
    duration_days: int = Field(..., gt=0, description="Duration in days")
    instructions: Optional[str] = Field(None, description="e.g. After food")
    quantity: Optional[int] = Field(None, gt=0, description="Total quantity")


class TelemedPrescriptionCreate(BaseModel):
    diagnosis: str
    clinical_notes: Optional[str] = None
    follow_up_date: Optional[str] = None  # YYYY-MM-DD
    medicines: Optional[List[TelemedMedicineItem]] = Field(None, description="Medicine lines (no pharmacy DB)")


class TelemedPrescriptionResponse(BaseModel):
    id: str
    prescription_no: str
    session_id: Optional[str] = None
    tele_appointment_id: Optional[str] = None
    doctor_id: str
    patient_id: str
    diagnosis: str
    clinical_notes: Optional[str] = None
    follow_up_date: Optional[str] = None
    status: str
    signed_at: Optional[datetime] = None
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


# ============================================================================
# VITALS
# ============================================================================

class TelemedVitalsCreate(BaseModel):
    vitals_type: str  # BP, HR, SPO2, TEMP, WEIGHT, GLUCOSE
    value_json: str  # e.g. {"systolic": 120, "diastolic": 80}
    session_id: Optional[str] = None
    recorded_at: Optional[datetime] = None


class TelemedVitalsResponse(BaseModel):
    id: str
    patient_id: str
    session_id: Optional[str] = None
    vitals_type: str
    value_json: str
    recorded_at: datetime
    entered_by: str
    created_at: datetime

    class Config:
        from_attributes = True


# ============================================================================
# PROVIDER CONFIG (Hospital Admin)
# ============================================================================

class TelemedProviderConfigResponse(BaseModel):
    hospital_id: str
    default_provider: str
    enabled_providers: List[str]
    settings_json: Optional[dict] = None
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class TelemedProviderConfigUpdate(BaseModel):
    default_provider: Optional[str] = Field(None, description="WEBRTC, TWILIO, AGORA, ZOOM")
    enabled_providers: Optional[List[str]] = None
    settings_json: Optional[dict] = None
