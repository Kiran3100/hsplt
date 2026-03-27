"""
Telemedicine session service.
Video session lifecycle, token generation.
"""
import uuid
import hashlib
from datetime import datetime, timedelta, timezone
from typing import Optional, List
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_
from sqlalchemy.orm import selectinload
from fastapi import HTTPException, status

from app.models.telemedicine import TeleAppointment, TelemedSession, TelemedParticipant
from app.core.enums import UserRole
from app.services.telemed_state_machine import validate_transition
from app.repositories.telemed_repository import (
    TeleAppointmentRepository,
    TelemedSessionRepository,
    TelemedProviderConfigRepository,
)
from app.services.telemed_notification_service import TelemedNotificationService


# Join window: 10 min before start, 15 min after end (configurable)
JOIN_WINDOW_BEFORE_MINUTES = 10
JOIN_WINDOW_AFTER_MINUTES = 15


class TelemedSessionService:
    """Service for video sessions and join tokens."""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def create(
        self,
        hospital_id: uuid.UUID,
        tele_appointment_id: uuid.UUID,
        provider: str = "WEBRTC"
    ) -> TelemedSession:
        """Create session for tele-appointment. One session per appointment."""
        apt_repo = TeleAppointmentRepository(self.db, hospital_id)
        tele_app = await apt_repo.get_by_id(tele_appointment_id)
        if not tele_app:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Tele-appointment not found")
        if tele_app.status not in ("SCHEDULED", "CONFIRMED"):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Cannot create session for appointment in current status"
            )

        session_repo = TelemedSessionRepository(self.db, hospital_id)
        existing = await session_repo.get_by_tele_appointment_id(tele_appointment_id)
        if existing:
            return existing

        # Use hospital's default provider from config when available; enforce enabled_providers
        config_repo = TelemedProviderConfigRepository(self.db, hospital_id)
        config = await config_repo.get_by_hospital()
        effective_provider = (config.default_provider if config else None) or provider
        if config and getattr(config, "enabled_providers", None):
            enabled = list(config.enabled_providers) if isinstance(config.enabled_providers, (list, tuple)) else []
            if enabled and effective_provider not in enabled:
                effective_provider = (
                    config.default_provider if getattr(config, "default_provider", None) in enabled else enabled[0]
                )
            if enabled and effective_provider not in enabled:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail={"code": "PROVIDER_NOT_ENABLED", "message": "Telemed provider is not enabled for this hospital"},
                )

        room_name = f"telemed_{hospital_id.hex[:8]}_{tele_appointment_id.hex[:8]}"
        session = TelemedSession(
            hospital_id=hospital_id,
            tele_appointment_id=tele_appointment_id,
            provider=effective_provider,
            room_name=room_name,
            status="SCHEDULED",
            scheduled_start=tele_app.scheduled_start,
            scheduled_end=tele_app.scheduled_end
        )
        self.db.add(session)
        await self.db.flush()
        await self.db.refresh(session)
        session.tele_appointment = tele_app  # attach for notification without extra query
        notif = TelemedNotificationService(self.db, hospital_id)
        await notif.notify_session_ready(session)
        return session

    async def get_by_id(self, session_id: uuid.UUID, hospital_id: uuid.UUID) -> Optional[TelemedSession]:
        repo = TelemedSessionRepository(self.db, hospital_id)
        return await repo.get_by_id(session_id)

    async def list_for_hospital(
        self,
        hospital_id: uuid.UUID,
        doctor_id: Optional[uuid.UUID] = None,
        patient_id: Optional[uuid.UUID] = None,
        status_filter: Optional[str] = None
    ) -> List[TelemedSession]:
        repo = TelemedSessionRepository(self.db, hospital_id)
        return await repo.list(doctor_id=doctor_id, patient_id=patient_id, status_filter=status_filter)

    async def start(self, session_id: uuid.UUID, hospital_id: uuid.UUID, user_id: uuid.UUID) -> TelemedSession:
        """Doctor starts session."""
        session = await self.get_by_id(session_id, hospital_id)
        if not session:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Session not found")
        if session.tele_appointment.doctor_id != user_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Only the doctor can start the session"
            )
        validate_transition(session.status, "IN_PROGRESS")
        now = datetime.utcnow()
        session.status = "IN_PROGRESS"
        if session.started_at is None:
            session.started_at = now
        if session.tele_appointment.status == "CONFIRMED":
            session.tele_appointment.status = "IN_PROGRESS"
        await self.db.flush()
        await self.db.refresh(session)
        return session

    async def end(
        self,
        session_id: uuid.UUID,
        hospital_id: uuid.UUID,
        user_id: uuid.UUID,
        end_reason: str = "COMPLETED"
    ) -> TelemedSession:
        """Doctor ends session."""
        session = await self.get_by_id(session_id, hospital_id)
        if not session:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Session not found")
        if session.tele_appointment.doctor_id != user_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Only the doctor can end the session"
            )
        validate_transition(session.status, "ENDED")
        # Use timezone-aware UTC to match DateTime(timezone=True) columns
        now = datetime.now(timezone.utc)
        session.status = "ENDED"
        if session.ended_at is None:
            session.ended_at = now
        session.ended_by = user_id
        session.end_reason = end_reason
        if session.started_at:
            session.duration_seconds = int((now - session.started_at).total_seconds())
        session.tele_appointment.status = "COMPLETED"
        await self.db.flush()
        await self.db.refresh(session)
        notif = TelemedNotificationService(self.db, hospital_id)
        await notif.notify_session_ended(session)
        
        return session

    def _is_in_join_window(self, scheduled_start: datetime, scheduled_end: datetime) -> bool:
        # Compare using timezone-aware UTC to avoid naive/aware errors
        now = datetime.now(timezone.utc)
        window_start = scheduled_start - timedelta(minutes=JOIN_WINDOW_BEFORE_MINUTES)
        window_end = scheduled_end + timedelta(minutes=JOIN_WINDOW_AFTER_MINUTES)
        return window_start <= now <= window_end

    async def generate_join_token(
        self,
        session_id: uuid.UUID,
        hospital_id: uuid.UUID,
        user_id: uuid.UUID,
        device_type: str = "WEB"
    ) -> dict:
        """Generate short-lived join token for doctor or patient."""
        session = await self.get_by_id(session_id, hospital_id)
        if not session:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Session not found")
        if session.tele_appointment.doctor_id != user_id and session.tele_appointment.patient_id != user_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access denied to this session"
            )
        if session.status in ("ENDED", "CANCELLED", "EXPIRED"):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Session is no longer available"
            )
        # IN_PROGRESS: allow join regardless of time (session is live)
        if session.status != "IN_PROGRESS":
            start_ts = session.scheduled_start or session.tele_appointment.scheduled_start
            end_ts = session.scheduled_end or session.tele_appointment.scheduled_end
            if not self._is_in_join_window(start_ts, end_ts):
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail={"code": "JOIN_WINDOW_VIOLATION", "message": "Outside join window (10 min before start to 15 min after end)"},
                )

        role = "DOCTOR" if session.tele_appointment.doctor_id == user_id else "PATIENT"
        token_data = f"{session_id}:{user_id}:{role}:{datetime.now(timezone.utc).isoformat()}"
        token_hash = hashlib.sha256(token_data.encode()).hexdigest()
        access_token = f"vt_{token_hash[:32]}"
        expires_at = datetime.utcnow() + timedelta(minutes=5)

        # Record participant
        existing = (
            await self.db.execute(
                select(TelemedParticipant)
                .where(
                    TelemedParticipant.session_id == session_id,
                    TelemedParticipant.user_id == user_id
                )
            )
        ).scalar_one_or_none()
        if not existing:
            participant = TelemedParticipant(
                hospital_id=hospital_id,
                session_id=session_id,
                user_id=user_id,
                role=role
            )
            self.db.add(participant)
            await self.db.flush()

        return {
            "provider": session.provider,
            "room_name": session.room_name or f"room_{session_id}",
            "token": access_token,
            "expires_at": expires_at,
            "session_id": str(session_id)
        }
