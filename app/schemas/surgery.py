"""
Surgery module Pydantic schemas.
Phase 1 POA: create case, assign team, documentation, video, patient view.
"""
from datetime import datetime
from typing import Optional, List
from uuid import UUID
from pydantic import BaseModel, Field, ConfigDict


class SurgeryCaseCreate(BaseModel):
    """Create surgery case (Doctor only)."""
    patient_ref: str = Field(..., min_length=1, description="Patient reference (e.g. PAT-XXX)")
    admission_ref: str = Field(..., min_length=1, description="Admission reference (e.g. ADM-XXX)")
    surgery_name: str = Field(..., min_length=1, max_length=255)
    surgery_type: str = Field(..., description="MAJOR, MINOR, EMERGENCY")
    scheduled_date: datetime = Field(...)


class SurgeryTeamMemberAdd(BaseModel):
    """Add one team member by staff name (e.g. 'John Smith' or 'Dr. Jane Doe') and role."""
    staff_name: str = Field(..., min_length=1, description="Full name of doctor/staff (e.g. 'John Smith')")
    role: str = Field(..., description="ASSISTANT, ANESTHESIOLOGIST, SUPPORTING")


class SurgeryTeamAssignRequest(BaseModel):
    """Assign surgical team (Lead Surgeon only)."""
    members: List[SurgeryTeamMemberAdd] = Field(..., min_length=1)


class SurgeryDocumentationCreate(BaseModel):
    """Upload operative documentation (Lead Surgeon only; surgery must be COMPLETED)."""
    surgery_id: UUID = Field(..., description="Surgery case UUID from create response")
    patient_ref: str = Field(..., min_length=1, description="Patient reference (e.g. PAT-XXX)")
    procedure_performed: str = Field(..., min_length=1)
    findings: Optional[str] = None
    complications: Optional[str] = None
    notes: Optional[str] = None
    post_op_instructions: Optional[str] = None


class SurgeryCaseResponse(BaseModel):
    """Surgery case summary."""
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    hospital_id: UUID
    patient_ref: str = Field(..., description="Patient reference (e.g. PAT-XXX)")
    admission_id: UUID
    admission_ref: Optional[str] = Field(None, description="Admission number (e.g. ADM-XXX)")
    lead_surgeon_id: UUID
    surgery_name: str
    surgery_type: str
    scheduled_date: datetime
    status: str
    created_at: datetime


class SurgeryTeamMemberResponse(BaseModel):
    """Team member in a surgery (includes staff name for display)."""
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    surgery_id: UUID
    staff_id: UUID
    staff_name: Optional[str] = None
    role: str


class SurgeryDocumentationResponse(BaseModel):
    """Surgical documentation (patient-visible; only that patient can view)."""
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    surgery_id: UUID
    patient_ref: str = Field(..., description="Patient reference (e.g. PAT-XXX)")
    procedure_performed: str
    findings: Optional[str] = None
    complications: Optional[str] = None
    notes: Optional[str] = None
    post_op_instructions: Optional[str] = None
    submitted_at: Optional[datetime] = None


class SurgeryVideoResponse(BaseModel):
    """Surgery video metadata (no file_path exposed)."""
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    surgery_id: UUID
    file_name: str
    file_size: Optional[int] = None
    mime_type: Optional[str] = None
    uploaded_at: Optional[datetime] = None


class SurgeryVideoStreamTokenResponse(BaseModel):
    """Short-lived token for streaming video (patient only)."""
    stream_token: str = Field(..., description="Use with GET /patient/surgeries/videos/{video_id}/stream?token=...")
    expires_in_seconds: int = Field(..., description="Token validity in seconds")
