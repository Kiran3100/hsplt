"""
Telemedicine in-app notification service.
Creates notifications for session ready/ended, new message, prescription issued.
Calls are non-blocking: failures are logged and do not affect the main flow.
"""
import uuid
import logging
from typing import Optional, List

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.telemedicine import TelemedSession
from app.repositories.telemed_repository import TelemedNotificationRepository

logger = logging.getLogger(__name__)

EVENT_SESSION_READY = "SESSION_READY"
EVENT_SESSION_ENDED = "SESSION_ENDED"
EVENT_NEW_MESSAGE = "NEW_MESSAGE"
EVENT_PRESCRIPTION_ISSUED = "PRESCRIPTION_ISSUED"


class TelemedNotificationService:
    """Create in-app notifications for telemed events. Does not raise on failure."""

    def __init__(self, db: AsyncSession, hospital_id: uuid.UUID):
        self.db = db
        self.hospital_id = hospital_id
        self._repo = TelemedNotificationRepository(db, hospital_id)

    async def _create(
        self,
        recipient_user_id: uuid.UUID,
        event_type: str,
        session_id: Optional[uuid.UUID] = None,
        title: Optional[str] = None,
        body: Optional[str] = None,
    ) -> None:
        try:
            await self._repo.create(
                recipient_user_id=recipient_user_id,
                event_type=event_type,
                session_id=session_id,
                title=title,
                body=body,
            )
        except Exception as e:
            logger.warning("Telemed notification create failed: %s", e, exc_info=True)

    async def notify_session_ready(self, session: TelemedSession) -> None:
        """Notify doctor and patient that a session is ready (created)."""
        apt = session.tele_appointment
        doctor_id = apt.doctor_id
        patient_user_id = apt.patient.user_id if apt.patient else None
        sid = session.id
        title = "Telemedicine session ready"
        body = "Your telemedicine session is ready to join."
        await self._create(doctor_id, EVENT_SESSION_READY, session_id=sid, title=title, body=body)
        if patient_user_id:
            await self._create(patient_user_id, EVENT_SESSION_READY, session_id=sid, title=title, body=body)

    async def notify_session_ended(self, session: TelemedSession) -> None:
        """Notify patient that the session has ended."""
        apt = session.tele_appointment
        patient_user_id = apt.patient.user_id if apt.patient else None
        if patient_user_id:
            await self._create(
                patient_user_id,
                EVENT_SESSION_ENDED,
                session_id=session.id,
                title="Session ended",
                body="Your telemedicine session has ended.",
            )

    async def notify_new_message(
        self,
        session_id: uuid.UUID,
        sender_user_id: uuid.UUID,
        recipient_user_id: uuid.UUID,
    ) -> None:
        """Notify the other participant that a new message was sent."""
        await self._create(
            recipient_user_id,
            EVENT_NEW_MESSAGE,
            session_id=session_id,
            title="New message",
            body="You have a new message in your telemedicine session.",
        )

    async def notify_prescription_issued(
        self,
        session_id: uuid.UUID,
        patient_user_id: uuid.UUID,
    ) -> None:
        """Notify patient that a prescription was issued."""
        await self._create(
            patient_user_id,
            EVENT_PRESCRIPTION_ISSUED,
            session_id=session_id,
            title="Prescription issued",
            body="A prescription has been issued for your telemedicine visit.",
        )

    async def list_for_user(
        self,
        recipient_user_id: uuid.UUID,
        read_filter: Optional[bool] = None,
        limit: int = 50,
    ) -> List:
        """List notifications for a user. read_filter: True=read only, False=unread only, None=all."""
        return await self._repo.list_by_recipient(
            recipient_user_id=recipient_user_id,
            read_filter=read_filter,
            limit=limit,
        )

    async def mark_as_read(
        self, notification_id: uuid.UUID, recipient_user_id: uuid.UUID
    ) -> Optional[object]:
        """Mark notification as read for the recipient. Returns notification or None if not found."""
        return await self._repo.mark_read(notification_id, recipient_user_id)
