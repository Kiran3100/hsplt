"""
Telemedicine consultation notes (SOAP). Doctor only.
"""
import uuid
from typing import Optional, List
from sqlalchemy.ext.asyncio import AsyncSession
from fastapi import HTTPException, status

from app.models.telemedicine import TelemedSession
from app.repositories.telemed_repository import TelemedSessionRepository, TelemedConsultationNoteRepository


class TelemedNotesService:
    """SOAP notes - doctor only."""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def list_notes(
        self,
        hospital_id: uuid.UUID,
        session_id: uuid.UUID,
        user_id: uuid.UUID,
    ) -> List:
        repo = TelemedSessionRepository(self.db, hospital_id)
        session = await repo.get_by_id(session_id)
        if not session:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Session not found")
        if session.tele_appointment.doctor_id != user_id:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Only the doctor can view notes")
        notes_repo = TelemedConsultationNoteRepository(self.db, hospital_id)
        return await notes_repo.list_for_session(session_id)

    async def create_note(
        self,
        hospital_id: uuid.UUID,
        session_id: uuid.UUID,
        doctor_id: uuid.UUID,
        soap_json: Optional[str] = None,
        soap_text: Optional[str] = None,
    ):
        repo = TelemedSessionRepository(self.db, hospital_id)
        session = await repo.get_by_id(session_id)
        if not session:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Session not found")
        if session.tele_appointment.doctor_id != doctor_id:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Only the doctor can create notes")
        notes_repo = TelemedConsultationNoteRepository(self.db, hospital_id)
        return await notes_repo.create(
            session_id=session_id,
            doctor_id=doctor_id,
            soap_json=soap_json,
            soap_text=soap_text,
        )
