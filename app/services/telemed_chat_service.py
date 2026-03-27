"""
Telemedicine chat and file services.
Participant-only access; doctor-only notes.
"""
import uuid
from typing import Optional, List
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from fastapi import HTTPException, status

from app.models.telemedicine import TelemedSession, TelemedParticipant
from app.repositories.telemed_repository import (
    TelemedSessionRepository,
    TelemedMessageRepository,
    TelemedFileRepository,
)
from app.services.telemed_notification_service import TelemedNotificationService


def _is_participant(session: TelemedSession, user_id: uuid.UUID) -> bool:
    """Check if user is doctor or patient in the session's tele_appointment."""
    apt = session.tele_appointment
    if apt.doctor_id == user_id:
        return True
    if apt.patient and apt.patient.user_id == user_id:
        return True
    return False


async def _require_participant(
    db: AsyncSession,
    hospital_id: uuid.UUID,
    session_id: uuid.UUID,
    user_id: uuid.UUID,
) -> TelemedSession:
    """Get session and verify user is participant. Raises 403/404 if not."""
    repo = TelemedSessionRepository(db, hospital_id)
    session = await repo.get_by_id(session_id)
    if not session:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Session not found")
    if not _is_participant(session, user_id):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied to this session")
    return session


class TelemedChatService:
    """Chat messages - participants only."""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def list_messages(
        self,
        hospital_id: uuid.UUID,
        session_id: uuid.UUID,
        user_id: uuid.UUID,
    ) -> List:
        session = await _require_participant(self.db, hospital_id, session_id, user_id)
        repo = TelemedMessageRepository(self.db, hospital_id)
        return await repo.list_for_session(session_id)

    async def send_message(
        self,
        hospital_id: uuid.UUID,
        session_id: uuid.UUID,
        user_id: uuid.UUID,
        message_type: str = "TEXT",
        content: Optional[str] = None,
        file_ref: Optional[str] = None,
    ):
        session = await _require_participant(self.db, hospital_id, session_id, user_id)
        role = "DOCTOR" if session.tele_appointment.doctor_id == user_id else "PATIENT"
        repo = TelemedMessageRepository(self.db, hospital_id)
        msg = await repo.create(
            session_id=session_id,
            sender_id=user_id,
            sender_role=role,
            message_type=message_type,
            content=content,
            file_ref=file_ref,
        )
        recipient_user_id = (
            session.tele_appointment.patient.user_id
            if role == "DOCTOR"
            else session.tele_appointment.doctor_id
        )
        notif = TelemedNotificationService(self.db, hospital_id)
        await notif.notify_new_message(session_id, user_id, recipient_user_id)
        return msg


class TelemedFileService:
    """File metadata - participants only. Storage URL from caller."""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def list_files(
        self,
        hospital_id: uuid.UUID,
        session_id: uuid.UUID,
        user_id: uuid.UUID,
    ) -> List:
        await _require_participant(self.db, hospital_id, session_id, user_id)
        repo = TelemedFileRepository(self.db, hospital_id)
        return await repo.list_for_session(session_id)

    async def register_file(
        self,
        hospital_id: uuid.UUID,
        session_id: uuid.UUID,
        user_id: uuid.UUID,
        file_name: str,
        mime_type: Optional[str] = None,
        size_bytes: Optional[int] = None,
        storage_url: Optional[str] = None,
        checksum: Optional[str] = None,
    ):
        await _require_participant(self.db, hospital_id, session_id, user_id)
        repo = TelemedFileRepository(self.db, hospital_id)
        return await repo.create(
            session_id=session_id,
            uploaded_by=user_id,
            file_name=file_name,
            mime_type=mime_type,
            size_bytes=size_bytes,
            storage_url=storage_url,
            checksum=checksum,
        )
