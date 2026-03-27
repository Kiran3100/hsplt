"""
Telemedicine models - standalone tele-appointments and video sessions.
Separate from regular appointments; no appointment_id FK.
"""
import uuid
from sqlalchemy import Column, String, DateTime, ForeignKey, Boolean, Integer, Text, UniqueConstraint
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from app.core.database_types import UUID_TYPE, JSON_TYPE
from app.models.base import TenantBaseModel


class TeleAppointment(TenantBaseModel):
    """
    Standalone telemedicine appointment.
    No link to regular appointments. Enforces doctor availability via overlap check.
    """
    __tablename__ = "tele_appointments"

    # Core references
    patient_id = Column(UUID_TYPE, ForeignKey("patient_profiles.id"), nullable=False, index=True)
    doctor_id = Column(UUID_TYPE, ForeignKey("users.id"), nullable=False, index=True)

    # Scheduling - timestamps for overlap checks
    scheduled_start = Column(DateTime(timezone=True), nullable=False, index=True)
    scheduled_end = Column(DateTime(timezone=True), nullable=False, index=True)

    # Clinical
    reason = Column(Text, nullable=True)
    notes = Column(Text, nullable=True)

    # Status: SCHEDULED, CONFIRMED, CANCELLED, MISSED, COMPLETED
    status = Column(String(20), nullable=False, default="SCHEDULED", index=True)

    # Audit
    created_by = Column(UUID_TYPE, ForeignKey("users.id"), nullable=False, index=True)

    # Cancellation
    cancelled_at = Column(DateTime(timezone=True), nullable=True)
    cancelled_by = Column(UUID_TYPE, ForeignKey("users.id"), nullable=True)
    cancellation_reason = Column(Text, nullable=True)

    # Relationships
    patient = relationship("PatientProfile")
    doctor = relationship("User", foreign_keys=[doctor_id])
    creator = relationship("User", foreign_keys=[created_by])
    cancelled_by_user = relationship("User", foreign_keys=[cancelled_by])
    sessions = relationship("TelemedSession", back_populates="tele_appointment", uselist=True)

    def __repr__(self):
        return f"<TeleAppointment(id={self.id}, doctor={self.doctor_id}, start={self.scheduled_start})>"


class TelemedSession(TenantBaseModel):
    """
    Video session linked to a tele-appointment.
    One session per tele_appointment. Tokens issued on demand, not stored.
    """
    __tablename__ = "telemed_sessions"

    tele_appointment_id = Column(
        UUID_TYPE, ForeignKey("tele_appointments.id"), nullable=False, unique=True, index=True
    )

    # Provider: TWILIO, AGORA, ZOOM, WEBRTC
    provider = Column(String(20), nullable=False, default="WEBRTC")
    room_name = Column(String(100), nullable=True)  # Unique per hospital; set on provision

    # Status: SCHEDULED, READY, IN_PROGRESS, ENDED, CANCELLED, EXPIRED
    status = Column(String(20), nullable=False, default="SCHEDULED", index=True)

    # Convenience copy from tele_appointment
    scheduled_start = Column(DateTime(timezone=True), nullable=True)
    scheduled_end = Column(DateTime(timezone=True), nullable=True)
    started_at = Column(DateTime(timezone=True), nullable=True)
    ended_at = Column(DateTime(timezone=True), nullable=True)

    # Recording
    recording_enabled = Column(Boolean, nullable=False, default=False)
    recording_status = Column(String(20), nullable=True)  # NONE, STARTED, COMPLETED, FAILED
    recording_url = Column(Text, nullable=True)
    duration_seconds = Column(Integer, nullable=True)

    ended_by = Column(UUID_TYPE, ForeignKey("users.id"), nullable=True)
    end_reason = Column(String(50), nullable=True)

    # Relationships
    tele_appointment = relationship("TeleAppointment", back_populates="sessions")
    ended_by_user = relationship("User", foreign_keys=[ended_by])
    participants = relationship("TelemedParticipant", back_populates="session", cascade="all, delete-orphan")
    messages = relationship("TelemedMessage", back_populates="session", cascade="all, delete-orphan")
    files = relationship("TelemedFile", back_populates="session", cascade="all, delete-orphan")
    consultation_notes = relationship("TelemedConsultationNote", back_populates="session", cascade="all, delete-orphan")

    def __repr__(self):
        return f"<TelemedSession(id={self.id}, status={self.status})>"


class TelemedParticipant(TenantBaseModel):
    """
    Audit of who joined/left a video session.
    UNIQUE(hospital_id, session_id, user_id) - one row per user per session.
    """
    __tablename__ = "telemed_participants"
    __table_args__ = (UniqueConstraint("hospital_id", "session_id", "user_id", name="uq_telemed_participant_session_user"),)

    session_id = Column(UUID_TYPE, ForeignKey("telemed_sessions.id"), nullable=False, index=True)
    user_id = Column(UUID_TYPE, ForeignKey("users.id"), nullable=False, index=True)
    role = Column(String(20), nullable=False)  # DOCTOR, PATIENT

    joined_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())
    left_at = Column(DateTime(timezone=True), nullable=True)

    # Relationships
    session = relationship("TelemedSession", back_populates="participants")
    user = relationship("User")

    def __repr__(self):
        return f"<TelemedParticipant(session={self.session_id}, user={self.user_id}, role={self.role})>"


class TelemedMessage(TenantBaseModel):
    """
    Secure chat message within a video session.
    message_type: TEXT, IMAGE, FILE
    """
    __tablename__ = "telemed_messages"

    session_id = Column(UUID_TYPE, ForeignKey("telemed_sessions.id"), nullable=False, index=True)
    sender_id = Column(UUID_TYPE, ForeignKey("users.id"), nullable=False, index=True)
    sender_role = Column(String(20), nullable=False)  # DOCTOR, PATIENT

    message_type = Column(String(20), nullable=False, default="TEXT")  # TEXT, IMAGE, FILE
    content = Column(Text, nullable=True)  # For TEXT
    file_ref = Column(String(500), nullable=True)  # For IMAGE/FILE - storage reference

    content_encrypted = Column(Boolean, nullable=False, default=False)
    key_ref = Column(String(100), nullable=True)

    # Relationships
    session = relationship("TelemedSession", back_populates="messages")
    sender = relationship("User", foreign_keys=[sender_id])

    def __repr__(self):
        return f"<TelemedMessage(id={self.id}, session={self.session_id}, type={self.message_type})>"


class TelemedFile(TenantBaseModel):
    """
    Shared file metadata within a video session.
    Actual storage URL; checksum for integrity.
    """
    __tablename__ = "telemed_files"

    session_id = Column(UUID_TYPE, ForeignKey("telemed_sessions.id"), nullable=False, index=True)
    uploaded_by = Column(UUID_TYPE, ForeignKey("users.id"), nullable=False, index=True)
    file_name = Column(String(255), nullable=False)
    mime_type = Column(String(100), nullable=True)
    size_bytes = Column(Integer, nullable=True)
    storage_url = Column(Text, nullable=True)
    checksum = Column(String(64), nullable=True)

    # Relationships
    session = relationship("TelemedSession", back_populates="files")
    uploader = relationship("User", foreign_keys=[uploaded_by])

    def __repr__(self):
        return f"<TelemedFile(id={self.id}, session={self.session_id}, name={self.file_name})>"


class TelemedConsultationNote(TenantBaseModel):
    """
    SOAP consultation notes. Doctor-only. Version rules after session end.
    """
    __tablename__ = "telemed_consultation_notes"

    session_id = Column(UUID_TYPE, ForeignKey("telemed_sessions.id"), nullable=False, index=True)
    doctor_id = Column(UUID_TYPE, ForeignKey("users.id"), nullable=False, index=True)
    soap_json = Column(Text, nullable=True)  # JSON: subjective, objective, assessment, plan
    soap_text = Column(Text, nullable=True)  # Plain text fallback
    version = Column(Integer, nullable=False, default=1)

    # Relationships
    session = relationship("TelemedSession", back_populates="consultation_notes")
    doctor = relationship("User", foreign_keys=[doctor_id])

    def __repr__(self):
        return f"<TelemedConsultationNote(id={self.id}, session={self.session_id}, v={self.version})>"


class TelemedVitals(TenantBaseModel):
    """
    Remote vitals manual entry. session_id nullable for pre/post consultation.
    vitals_type: BP, HR, SPO2, TEMP, WEIGHT, GLUCOSE
    """
    __tablename__ = "telemed_vitals"

    patient_id = Column(UUID_TYPE, ForeignKey("patient_profiles.id"), nullable=False, index=True)
    session_id = Column(UUID_TYPE, ForeignKey("telemed_sessions.id"), nullable=True, index=True)
    vitals_type = Column(String(20), nullable=False, index=True)  # BP, HR, SPO2, TEMP, WEIGHT, GLUCOSE
    value_json = Column(Text, nullable=False)  # e.g. {"systolic": 120, "diastolic": 80} for BP
    recorded_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())
    entered_by = Column(UUID_TYPE, ForeignKey("users.id"), nullable=False, index=True)

    # Relationships
    patient = relationship("PatientProfile")
    session = relationship("TelemedSession")
    entered_by_user = relationship("User", foreign_keys=[entered_by])

    def __repr__(self):
        return f"<TelemedVitals(id={self.id}, patient={self.patient_id}, type={self.vitals_type})>"


class TelemedNotification(TenantBaseModel):
    """
    In-app notification for telemed events. No SMS/email; store only.
    event_type: SESSION_READY, SESSION_ENDED, NEW_MESSAGE, PRESCRIPTION_ISSUED
    """
    __tablename__ = "telemed_notifications"

    recipient_user_id = Column(UUID_TYPE, ForeignKey("users.id"), nullable=False, index=True)
    session_id = Column(UUID_TYPE, ForeignKey("telemed_sessions.id"), nullable=True, index=True)
    event_type = Column(String(30), nullable=False, index=True)
    title = Column(String(255), nullable=True)
    body = Column(Text, nullable=True)
    read_at = Column(DateTime(timezone=True), nullable=True)

    recipient = relationship("User", foreign_keys=[recipient_user_id])
    session = relationship("TelemedSession")

    def __repr__(self):
        return f"<TelemedNotification(id={self.id}, recipient={self.recipient_user_id}, event={self.event_type})>"


class TelemedProviderConfig(TenantBaseModel):
    """
    Per-hospital telemedicine provider configuration.
    One row per hospital. Hospital Admin can set default provider and enabled providers.
    """
    __tablename__ = "telemed_provider_config"
    __table_args__ = (UniqueConstraint("hospital_id", name="uq_telemed_provider_config_hospital_id"),)

    default_provider = Column(String(20), nullable=False, default="WEBRTC")  # WEBRTC, TWILIO, AGORA, ZOOM
    enabled_providers = Column(JSON_TYPE, nullable=False, default=lambda: ["WEBRTC"])  # list of provider codes
    settings_json = Column(JSON_TYPE, nullable=True, default=lambda: {})  # optional: API keys placeholder, URLs

    def __repr__(self):
        return f"<TelemedProviderConfig(hospital_id={self.hospital_id}, default={self.default_provider})>"
