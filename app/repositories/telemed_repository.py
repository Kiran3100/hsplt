"""
Telemedicine repositories - all queries scoped by hospital_id.
"""
import uuid
from datetime import datetime
from typing import Optional, List
from sqlalchemy import select, and_
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.telemedicine import (
    TeleAppointment,
    TelemedSession,
    TelemedParticipant,
    TelemedMessage,
    TelemedFile,
    TelemedConsultationNote,
    TelemedVitals,
    TelemedNotification,
    TelemedProviderConfig,
)
from app.models.patient import PatientProfile


class TeleAppointmentRepository:
    """Repository for tele-appointments. All methods require hospital_id."""

    def __init__(self, db: AsyncSession, hospital_id: uuid.UUID):
        self.db = db
        self.hospital_id = hospital_id

    async def get_by_id(self, tele_appointment_id: uuid.UUID) -> Optional[TeleAppointment]:
        """Get by ID, hospital-scoped. Returns None if not found or wrong hospital."""
        result = await self.db.execute(
            select(TeleAppointment)
            .where(
                TeleAppointment.id == tele_appointment_id,
                TeleAppointment.hospital_id == self.hospital_id,
            )
            .options(
                selectinload(TeleAppointment.patient).selectinload(PatientProfile.user),
                selectinload(TeleAppointment.doctor),
            )
        )
        return result.scalar_one_or_none()

    async def list(
        self,
        patient_id: Optional[uuid.UUID] = None,
        doctor_id: Optional[uuid.UUID] = None,
        status_filter: Optional[str] = None,
    ) -> List[TeleAppointment]:
        """List tele-appointments for hospital with optional filters."""
        q = (
            select(TeleAppointment)
            .where(TeleAppointment.hospital_id == self.hospital_id)
            .options(
                selectinload(TeleAppointment.patient).selectinload(PatientProfile.user),
                selectinload(TeleAppointment.doctor),
            )
        )
        if patient_id:
            q = q.where(TeleAppointment.patient_id == patient_id)
        if doctor_id:
            q = q.where(TeleAppointment.doctor_id == doctor_id)
        if status_filter:
            q = q.where(TeleAppointment.status == status_filter)
        q = q.order_by(TeleAppointment.scheduled_start.desc())
        result = await self.db.execute(q)
        return list(result.scalars().all())


class TelemedSessionRepository:
    """Repository for telemed sessions. All methods require hospital_id."""

    def __init__(self, db: AsyncSession, hospital_id: uuid.UUID):
        self.db = db
        self.hospital_id = hospital_id

    async def get_by_id(self, session_id: uuid.UUID) -> Optional[TelemedSession]:
        """Get by ID, hospital-scoped. Returns None if not found or wrong hospital."""
        result = await self.db.execute(
            select(TelemedSession)
            .where(
                TelemedSession.id == session_id,
                TelemedSession.hospital_id == self.hospital_id,
            )
            .options(
                selectinload(TelemedSession.tele_appointment).selectinload(TeleAppointment.patient),
                selectinload(TelemedSession.participants),
            )
        )
        return result.scalar_one_or_none()

    async def get_by_tele_appointment_id(self, tele_appointment_id: uuid.UUID) -> Optional[TelemedSession]:
        """Get session by tele_appointment_id, hospital-scoped."""
        result = await self.db.execute(
            select(TelemedSession)
            .where(
                TelemedSession.tele_appointment_id == tele_appointment_id,
                TelemedSession.hospital_id == self.hospital_id,
            )
            .options(
                selectinload(TelemedSession.tele_appointment),
                selectinload(TelemedSession.participants),
            )
        )
        return result.scalar_one_or_none()

    async def list(
        self,
        doctor_id: Optional[uuid.UUID] = None,
        patient_id: Optional[uuid.UUID] = None,
        status_filter: Optional[str] = None,
    ) -> List[TelemedSession]:
        """List sessions for hospital with optional filters."""
        q = (
            select(TelemedSession)
            .join(TeleAppointment, TelemedSession.tele_appointment_id == TeleAppointment.id)
            .where(TelemedSession.hospital_id == self.hospital_id)
        )
        if doctor_id:
            q = q.where(TeleAppointment.doctor_id == doctor_id)
        if patient_id:
            q = q.where(TeleAppointment.patient_id == patient_id)
        if status_filter:
            q = q.where(TelemedSession.status == status_filter)
        q = q.order_by(TelemedSession.scheduled_start.desc())
        result = await self.db.execute(q)
        return list(result.scalars().all())


class TelemedMessageRepository:
    """Repository for session messages. All queries scoped by hospital_id."""

    def __init__(self, db: AsyncSession, hospital_id: uuid.UUID):
        self.db = db
        self.hospital_id = hospital_id

    async def list_for_session(self, session_id: uuid.UUID) -> List[TelemedMessage]:
        result = await self.db.execute(
            select(TelemedMessage)
            .where(
                TelemedMessage.session_id == session_id,
                TelemedMessage.hospital_id == self.hospital_id,
            )
            .order_by(TelemedMessage.created_at.asc())
        )
        return list(result.scalars().all())

    async def create(
        self,
        session_id: uuid.UUID,
        sender_id: uuid.UUID,
        sender_role: str,
        message_type: str = "TEXT",
        content: Optional[str] = None,
        file_ref: Optional[str] = None,
    ) -> TelemedMessage:
        msg = TelemedMessage(
            hospital_id=self.hospital_id,
            session_id=session_id,
            sender_id=sender_id,
            sender_role=sender_role,
            message_type=message_type,
            content=content,
            file_ref=file_ref,
        )
        self.db.add(msg)
        await self.db.flush()
        await self.db.refresh(msg)
        return msg


class TelemedFileRepository:
    """Repository for session files. All queries scoped by hospital_id."""

    def __init__(self, db: AsyncSession, hospital_id: uuid.UUID):
        self.db = db
        self.hospital_id = hospital_id

    async def list_for_session(self, session_id: uuid.UUID) -> List[TelemedFile]:
        result = await self.db.execute(
            select(TelemedFile)
            .where(
                TelemedFile.session_id == session_id,
                TelemedFile.hospital_id == self.hospital_id,
            )
            .order_by(TelemedFile.created_at.desc())
        )
        return list(result.scalars().all())

    async def create(
        self,
        session_id: uuid.UUID,
        uploaded_by: uuid.UUID,
        file_name: str,
        mime_type: Optional[str] = None,
        size_bytes: Optional[int] = None,
        storage_url: Optional[str] = None,
        checksum: Optional[str] = None,
    ) -> TelemedFile:
        f = TelemedFile(
            hospital_id=self.hospital_id,
            session_id=session_id,
            uploaded_by=uploaded_by,
            file_name=file_name,
            mime_type=mime_type,
            size_bytes=size_bytes,
            storage_url=storage_url,
            checksum=checksum,
        )
        self.db.add(f)
        await self.db.flush()
        await self.db.refresh(f)
        return f


class TelemedConsultationNoteRepository:
    """Repository for SOAP notes. All queries scoped by hospital_id."""

    def __init__(self, db: AsyncSession, hospital_id: uuid.UUID):
        self.db = db
        self.hospital_id = hospital_id

    async def list_for_session(self, session_id: uuid.UUID) -> List[TelemedConsultationNote]:
        result = await self.db.execute(
            select(TelemedConsultationNote)
            .where(
                TelemedConsultationNote.session_id == session_id,
                TelemedConsultationNote.hospital_id == self.hospital_id,
            )
            .order_by(TelemedConsultationNote.version.desc())
        )
        return list(result.scalars().all())

    async def get_latest(self, session_id: uuid.UUID) -> Optional[TelemedConsultationNote]:
        result = await self.db.execute(
            select(TelemedConsultationNote)
            .where(
                TelemedConsultationNote.session_id == session_id,
                TelemedConsultationNote.hospital_id == self.hospital_id,
            )
            .order_by(TelemedConsultationNote.version.desc())
            .limit(1)
        )
        return result.scalars().first()

    async def create(
        self,
        session_id: uuid.UUID,
        doctor_id: uuid.UUID,
        soap_json: Optional[str] = None,
        soap_text: Optional[str] = None,
    ) -> TelemedConsultationNote:
        latest = await self.get_latest(session_id)
        version = (latest.version + 1) if latest else 1
        note = TelemedConsultationNote(
            hospital_id=self.hospital_id,
            session_id=session_id,
            doctor_id=doctor_id,
            soap_json=soap_json,
            soap_text=soap_text,
            version=version,
        )
        self.db.add(note)
        await self.db.flush()
        await self.db.refresh(note)
        return note


class TelemedVitalsRepository:
    """Repository for remote vitals. All queries scoped by hospital_id."""

    def __init__(self, db: AsyncSession, hospital_id: uuid.UUID):
        self.db = db
        self.hospital_id = hospital_id

    async def list_for_patient(
        self,
        patient_id: uuid.UUID,
        from_date: Optional[datetime] = None,
        to_date: Optional[datetime] = None,
        vitals_type: Optional[str] = None,
    ) -> List[TelemedVitals]:
        q = select(TelemedVitals).where(
            TelemedVitals.patient_id == patient_id,
            TelemedVitals.hospital_id == self.hospital_id,
        )
        if from_date:
            q = q.where(TelemedVitals.recorded_at >= from_date)
        if to_date:
            q = q.where(TelemedVitals.recorded_at <= to_date)
        if vitals_type:
            q = q.where(TelemedVitals.vitals_type == vitals_type)
        q = q.order_by(TelemedVitals.recorded_at.desc())
        result = await self.db.execute(q)
        return list(result.scalars().all())

    async def create(
        self,
        patient_id: uuid.UUID,
        vitals_type: str,
        value_json: str,
        entered_by: uuid.UUID,
        session_id: Optional[uuid.UUID] = None,
        recorded_at: Optional[datetime] = None,
    ) -> TelemedVitals:
        v = TelemedVitals(
            hospital_id=self.hospital_id,
            patient_id=patient_id,
            session_id=session_id,
            vitals_type=vitals_type,
            value_json=value_json,
            entered_by=entered_by,
        )
        if recorded_at:
            v.recorded_at = recorded_at
        self.db.add(v)
        await self.db.flush()
        await self.db.refresh(v)
        return v


class TelemedNotificationRepository:
    """Repository for in-app telemed notifications. All queries scoped by hospital_id."""

    def __init__(self, db: AsyncSession, hospital_id: uuid.UUID):
        self.db = db
        self.hospital_id = hospital_id

    async def create(
        self,
        recipient_user_id: uuid.UUID,
        event_type: str,
        session_id: Optional[uuid.UUID] = None,
        title: Optional[str] = None,
        body: Optional[str] = None,
    ) -> TelemedNotification:
        n = TelemedNotification(
            hospital_id=self.hospital_id,
            recipient_user_id=recipient_user_id,
            session_id=session_id,
            event_type=event_type,
            title=title,
            body=body,
        )
        self.db.add(n)
        await self.db.flush()
        await self.db.refresh(n)
        return n

    async def list_by_recipient(
        self,
        recipient_user_id: uuid.UUID,
        read_filter: Optional[bool] = None,
        limit: int = 50,
    ) -> List[TelemedNotification]:
        q = (
            select(TelemedNotification)
            .where(
                TelemedNotification.hospital_id == self.hospital_id,
                TelemedNotification.recipient_user_id == recipient_user_id,
                TelemedNotification.is_active == True,
            )
        )
        if read_filter is True:
            q = q.where(TelemedNotification.read_at.isnot(None))
        elif read_filter is False:
            q = q.where(TelemedNotification.read_at.is_(None))
        q = q.order_by(TelemedNotification.created_at.desc()).limit(limit)
        result = await self.db.execute(q)
        return list(result.scalars().all())

    async def get_by_id_and_recipient(
        self, notification_id: uuid.UUID, recipient_user_id: uuid.UUID
    ) -> Optional[TelemedNotification]:
        result = await self.db.execute(
            select(TelemedNotification).where(
                TelemedNotification.id == notification_id,
                TelemedNotification.hospital_id == self.hospital_id,
                TelemedNotification.recipient_user_id == recipient_user_id,
                TelemedNotification.is_active == True,
            )
        )
        return result.scalar_one_or_none()

    async def mark_read(
        self, notification_id: uuid.UUID, recipient_user_id: uuid.UUID
    ) -> Optional[TelemedNotification]:
        n = await self.get_by_id_and_recipient(notification_id, recipient_user_id)
        if not n:
            return None
        n.read_at = datetime.utcnow()
        await self.db.flush()
        await self.db.refresh(n)
        return n


class TelemedProviderConfigRepository:
    """Repository for per-hospital telemed provider config. One row per hospital."""

    def __init__(self, db: AsyncSession, hospital_id: uuid.UUID):
        self.db = db
        self.hospital_id = hospital_id

    async def get_by_hospital(self) -> Optional[TelemedProviderConfig]:
        result = await self.db.execute(
            select(TelemedProviderConfig).where(
                TelemedProviderConfig.hospital_id == self.hospital_id,
                TelemedProviderConfig.is_active == True,
            )
        )
        return result.scalar_one_or_none()

    async def create_or_update(
        self,
        default_provider: Optional[str] = None,
        enabled_providers: Optional[List[str]] = None,
        settings_json: Optional[dict] = None,
    ) -> TelemedProviderConfig:
        row = await self.get_by_hospital()
        if row:
            if default_provider is not None:
                row.default_provider = default_provider
            if enabled_providers is not None:
                row.enabled_providers = enabled_providers
            if settings_json is not None:
                row.settings_json = settings_json
            await self.db.flush()
            await self.db.refresh(row)
            return row
        row = TelemedProviderConfig(
            hospital_id=self.hospital_id,
            default_provider=default_provider or "WEBRTC",
            enabled_providers=enabled_providers or ["WEBRTC"],
            settings_json=settings_json or {},
        )
        self.db.add(row)
        await self.db.flush()
        await self.db.refresh(row)
        return row
