"""
Surgery module models.
Surgery case registration, team assignment, operative documentation, and video (patient-only access).
"""
import uuid
from sqlalchemy import Column, String, Text, Boolean, DateTime, ForeignKey, Integer
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from app.core.database_types import UUID_TYPE
from app.models.base import TenantBaseModel


class SurgeryCase(TenantBaseModel):
    """
    Surgery case - one per scheduled surgery.
    Doctor creates; lead_surgeon_id set to creating doctor.
    """
    __tablename__ = "surgery_cases"

    # References
    patient_id = Column(UUID_TYPE, ForeignKey("patient_profiles.id"), nullable=False, index=True)
    admission_id = Column(UUID_TYPE, ForeignKey("admissions.id"), nullable=False, index=True)
    lead_surgeon_id = Column(UUID_TYPE, ForeignKey("users.id"), nullable=False, index=True)

    # Case details
    surgery_name = Column(String(255), nullable=False)
    surgery_type = Column(String(20), nullable=False)  # MAJOR, MINOR, EMERGENCY
    scheduled_date = Column(DateTime(timezone=True), nullable=False)
    status = Column(String(20), nullable=False, default="SCHEDULED")  # SurgeryCaseStatus

    # Relationships
    patient = relationship("PatientProfile", back_populates="surgery_cases")
    admission = relationship("Admission", back_populates="surgery_cases")
    lead_surgeon = relationship("User", foreign_keys=[lead_surgeon_id])
    team_members = relationship("SurgeryTeamMember", back_populates="surgery_case", cascade="all, delete-orphan")
    documentation = relationship("SurgeryDocumentation", back_populates="surgery_case", uselist=False)
    videos = relationship("SurgeryVideo", back_populates="surgery_case", cascade="all, delete-orphan")

    def __repr__(self):
        return f"<SurgeryCase(id={self.id}, surgery_name='{self.surgery_name}', status='{self.status}')>"


class SurgeryTeamMember(TenantBaseModel):
    """
    Surgical team member - many per surgery.
    Only lead surgeon can assign. Staff must be same hospital, active.
    """
    __tablename__ = "surgery_team_members"

    surgery_id = Column(UUID_TYPE, ForeignKey("surgery_cases.id"), nullable=False, index=True)
    staff_id = Column(UUID_TYPE, ForeignKey("users.id"), nullable=False, index=True)
    role = Column(String(30), nullable=False)  # ASSISTANT, ANESTHESIOLOGIST, SUPPORTING (lead already on case)

    # Relationships
    surgery_case = relationship("SurgeryCase", back_populates="team_members")
    staff = relationship("User", foreign_keys=[staff_id])

    def __repr__(self):
        return f"<SurgeryTeamMember(surgery_id={self.surgery_id}, staff_id={self.staff_id}, role='{self.role}')>"


class SurgeryDocumentation(TenantBaseModel):
    """
    Operative report / surgical documentation.
    Only lead surgeon can submit; surgery must be COMPLETED.
    Patient-visible (only that patient can view).
    """
    __tablename__ = "surgery_documentation"

    surgery_id = Column(UUID_TYPE, ForeignKey("surgery_cases.id"), nullable=False, index=True)
    patient_id = Column(UUID_TYPE, ForeignKey("patient_profiles.id"), nullable=False, index=True)
    submitted_by = Column(UUID_TYPE, ForeignKey("users.id"), nullable=False)  # Must be lead_surgeon

    procedure_performed = Column(Text, nullable=False)
    findings = Column(Text)
    complications = Column(Text)
    notes = Column(Text)
    post_op_instructions = Column(Text)

    # Visibility: only the patient can view (enforced in API)
    patient_visible = Column(Boolean, default=True, nullable=False)

    # Relationships
    surgery_case = relationship("SurgeryCase", back_populates="documentation")
    patient = relationship("PatientProfile")
    submitted_by_user = relationship("User", foreign_keys=[submitted_by])

    def __repr__(self):
        return f"<SurgeryDocumentation(surgery_id={self.surgery_id})>"


class SurgeryVideo(TenantBaseModel):
    """
    Surgery video - uploaded by Head Nurse (OT).
    Stored path only; no direct URL exposure. Stream via token.
    Visibility = PATIENT_ONLY.
    """
    __tablename__ = "surgery_videos"

    surgery_id = Column(UUID_TYPE, ForeignKey("surgery_cases.id"), nullable=False, index=True)
    patient_id = Column(UUID_TYPE, ForeignKey("patient_profiles.id"), nullable=False, index=True)
    uploaded_by = Column(UUID_TYPE, ForeignKey("users.id"), nullable=False)

    file_path = Column(String(500), nullable=False)  # Server path; never exposed to client
    file_name = Column(String(255), nullable=False)
    file_size = Column(Integer)
    mime_type = Column(String(100), default="video/mp4")

    # Visibility
    visibility = Column(String(20), default="PATIENT_ONLY", nullable=False)

    # Relationships
    surgery_case = relationship("SurgeryCase", back_populates="videos")
    patient = relationship("PatientProfile")
    uploader = relationship("User", foreign_keys=[uploaded_by])
    view_audits = relationship("SurgeryVideoViewAudit", back_populates="surgery_video", cascade="all, delete-orphan")

    def __repr__(self):
        return f"<SurgeryVideo(surgery_id={self.surgery_id})>"


class SurgeryVideoViewAudit(TenantBaseModel):
    """
    Audit log when patient watches surgery video.
    patient_id, surgery_id, viewed_at for legal protection.
    """
    __tablename__ = "surgery_video_view_audits"

    surgery_video_id = Column(UUID_TYPE, ForeignKey("surgery_videos.id"), nullable=False, index=True)
    patient_id = Column(UUID_TYPE, ForeignKey("patient_profiles.id"), nullable=False, index=True)
    surgery_id = Column(UUID_TYPE, ForeignKey("surgery_cases.id"), nullable=False, index=True)
    viewed_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    ip_address = Column(String(45))
    user_agent = Column(String(500))

    # Relationships
    surgery_video = relationship("SurgeryVideo", back_populates="view_audits")

    def __repr__(self):
        return f"<SurgeryVideoViewAudit(video_id={self.surgery_video_id}, patient_id={self.patient_id}, viewed_at={self.viewed_at})>"
