"""
Video service for HD video consultation management.
Handles call lifecycle, participant tracking, and in-call controls.

DEPRECATED: Use app.services.telemed_session_service.TelemedSessionService and
app.api.v1.routers.telemed.sessions for join tokens instead.
This module targets the legacy schema (VideoSession, CallParticipant, CallEvent)
and will be removed once migration is complete.
"""
import uuid
import secrets
import hashlib
from datetime import datetime, timedelta
from typing import List, Optional, Dict, Any
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, or_, func, desc
from sqlalchemy.orm import selectinload

# Legacy models - VideoSession, CallParticipant, CallEvent were removed.
# Import from new telemedicine models; VideoService may fail at runtime.
try:
    from app.models.telemedicine import TeleAppointment, TelemedSession, TelemedParticipant
    # Aliases for legacy code - schema differs; VideoService is deprecated
    VideoSession = TelemedSession
    CallParticipant = TelemedParticipant
    CallEvent = None  # Not implemented in new schema
except ImportError:
    TeleAppointment = VideoSession = CallParticipant = CallEvent = None
from app.models.user import User
from app.schemas.telemedicine import (
    SessionReadinessResponse, CallTokenRequest, CallTokenResponse,
    JoinCallRequest, JoinCallResponse, CallParticipantResponse,
    CallEventResponse, CallSummaryResponse, ReconnectRequest,
    CallControlRequest
)
from app.core.enums import (
    TeleAppointmentStatus, VideoSessionStatus, DeviceType,
    CallEventType, ConnectionState, ParticipantRole
)


class VideoService:
    """Service for video call operations"""
    
    @staticmethod
    async def check_session_readiness(
        db: AsyncSession,
        hospital_id: uuid.UUID,
        session_id: str,
        user_id: uuid.UUID
    ) -> Dict[str, Any]:
        """
        Check if video session is ready for joining.
        Validates appointment timing, user role access, and session status.
        """
        # Get video session with appointment
        session_query = (
            select(VideoSession, TeleAppointment)
            .join(TeleAppointment, VideoSession.tele_appointment_id == TeleAppointment.id)
            .where(
                and_(
                    VideoSession.hospital_id == hospital_id,
                    VideoSession.session_id == session_id
                )
            )
        )
        
        result = await db.execute(session_query)
        session_data = result.first()
        
        if not session_data:
            raise ValueError("Video session not found")
        
        video_session, tele_appointment = session_data
        
        # Check user access
        if tele_appointment.doctor_id != user_id and tele_appointment.patient_id != user_id:
            raise PermissionError("Access denied to this session")
        
        # Check timing window (15 min before to 30 min after)
        scheduled_datetime = datetime.strptime(
            f"{tele_appointment.scheduled_date} {tele_appointment.start_time}",
            "%Y-%m-%d %H:%M:%S"
        )
        end_datetime = datetime.strptime(
            f"{tele_appointment.scheduled_date} {tele_appointment.end_time}",
            "%Y-%m-%d %H:%M:%S"
        )
        
        now = datetime.utcnow()
        join_window_start = scheduled_datetime - timedelta(minutes=15)
        join_window_end = end_datetime + timedelta(minutes=30)
        
        can_join = join_window_start <= now <= join_window_end
        ready = can_join and video_session.status in [VideoSessionStatus.CREATED, VideoSessionStatus.ACTIVE]
        
        # Calculate time differences
        time_until_start = None
        time_until_end = None
        
        if now < join_window_start:
            time_until_start = int((join_window_start - now).total_seconds() / 60)
        if now < join_window_end:
            time_until_end = int((join_window_end - now).total_seconds() / 60)
        
        # Get current participants
        participants_query = (
            select(CallParticipant, User.full_name)
            .join(User, CallParticipant.user_id == User.id)
            .where(CallParticipant.session_id == video_session.id)
            .order_by(CallParticipant.joined_at)
        )
        
        participants_result = await db.execute(participants_query)
        participants_data = participants_result.fetchall()
        
        current_participants = []
        for participant, user_name in participants_data:
            current_participants.append(CallParticipantResponse(
                id=str(participant.id),
                user_id=str(participant.user_id),
                role=ParticipantRole(participant.role),
                device_type=DeviceType(participant.device_type),
                connection_state=ConnectionState(participant.connection_state),
                joined_at=participant.joined_at,
                left_at=participant.left_at,
                last_seen_at=participant.last_seen_at,
                connection_quality=participant.connection_quality,
                is_connected=participant.is_connected,
                call_duration_minutes=participant.call_duration_seconds // 60
            ))
        
        # Generate message
        if not ready:
            if now < join_window_start:
                message = f"Session will be available in {time_until_start} minutes"
            elif now > join_window_end:
                message = "Session has expired"
            elif video_session.status == VideoSessionStatus.ENDED:
                message = "Session has ended"
            else:
                message = "Session is not ready"
        else:
            message = "Session is ready to join"
        
        return {
            "session_id": session_id,
            "ready": ready,
            "can_join": can_join,
            "time_until_start": time_until_start,
            "time_until_end": time_until_end,
            "message": message,
            "current_participants": current_participants
        }
    
    @staticmethod
    async def generate_call_token(
        db: AsyncSession,
        hospital_id: uuid.UUID,
        session_id: str,
        user_id: uuid.UUID,
        device_type: str
    ) -> CallTokenResponse:
        """
        Generate short-lived HD video call token.
        Returns provider-specific token for video SDK integration.
        """
        # Get video session
        session_query = (
            select(VideoSession, TeleAppointment)
            .join(TeleAppointment, VideoSession.tele_appointment_id == TeleAppointment.id)
            .where(
                and_(
                    VideoSession.hospital_id == hospital_id,
                    VideoSession.session_id == session_id
                )
            )
        )
        
        result = await db.execute(session_query)
        session_data = result.first()
        
        if not session_data:
            raise ValueError("Video session not found")
        
        video_session, tele_appointment = session_data
        
        # Check access
        if tele_appointment.doctor_id != user_id and tele_appointment.patient_id != user_id:
            raise PermissionError("Access denied to this session")
        
        # Determine participant role
        if tele_appointment.doctor_id == user_id:
            participant_role = ParticipantRole.DOCTOR
        else:
            participant_role = ParticipantRole.PATIENT
        
        # Generate access token (5 minutes TTL)
        token_data = f"{session_id}:{user_id}:{participant_role}:{datetime.utcnow().isoformat()}"
        access_token = hashlib.sha256(token_data.encode()).hexdigest()
        
        return CallTokenResponse(
            access_token=f"vt_{access_token[:32]}",
            expires_in=300,  # 5 minutes
            room_name=video_session.room_name or f"room_{session_id}",
            session_id=session_id,
            provider=video_session.provider,
            participant_role=participant_role
        )
    
    @staticmethod
    async def join_call(
        db: AsyncSession,
        hospital_id: uuid.UUID,
        session_id: str,
        user_id: uuid.UUID,
        device_type: str,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None
    ) -> JoinCallResponse:
        """
        Join a video call session.
        Creates participant entry and logs JOIN event.
        """
        # Get video session
        session_query = (
            select(VideoSession, TeleAppointment)
            .join(TeleAppointment, VideoSession.tele_appointment_id == TeleAppointment.id)
            .where(
                and_(
                    VideoSession.hospital_id == hospital_id,
                    VideoSession.session_id == session_id
                )
            )
        )
        
        result = await db.execute(session_query)
        session_data = result.first()
        
        if not session_data:
            raise ValueError("Video session not found")
        
        video_session, tele_appointment = session_data
        
        # Check access
        if tele_appointment.doctor_id != user_id and tele_appointment.patient_id != user_id:
            raise PermissionError("Access denied to this session")
        
        # Determine participant role
        if tele_appointment.doctor_id == user_id:
            participant_role = ParticipantRole.DOCTOR
        else:
            participant_role = ParticipantRole.PATIENT
        
        # Check if participant already exists
        existing_participant_query = (
            select(CallParticipant)
            .where(
                and_(
                    CallParticipant.session_id == video_session.id,
                    CallParticipant.user_id == user_id
                )
            )
        )
        
        existing_result = await db.execute(existing_participant_query)
        existing_participant = existing_result.scalar_one_or_none()
        
        now = datetime.utcnow()
        
        if existing_participant:
            # Update existing participant (rejoin)
            existing_participant.connection_state = ConnectionState.RECONNECTED
            existing_participant.last_seen_at = now
            existing_participant.device_type = device_type
            participant = existing_participant
            event_type = CallEventType.REJOIN
        else:
            # Create new participant
            participant = CallParticipant(
                hospital_id=hospital_id,
                session_id=video_session.id,
                user_id=user_id,
                role=participant_role,
                device_type=device_type,
                connection_state=ConnectionState.CONNECTED,
                joined_at=now,
                last_seen_at=now,
                ip_address=ip_address,
                user_agent=user_agent
            )
            db.add(participant)
            event_type = CallEventType.JOIN
        
        # Update session status
        if video_session.status == VideoSessionStatus.CREATED:
            video_session.status = VideoSessionStatus.ACTIVE
        
        # Update appointment status
        if tele_appointment.status == TeleAppointmentStatus.CONFIRMED:
            tele_appointment.status = TeleAppointmentStatus.IN_PROGRESS
            tele_appointment.session_started_at = now
        
        await db.flush()  # Get participant ID
        
        # Log event
        call_event = CallEvent(
            hospital_id=hospital_id,
            session_id=video_session.id,
            participant_id=participant.id,
            event_type=event_type,
            event_time=now,
            triggered_by=user_id,
            device_type=device_type,
            ip_address=ip_address,
            payload={"user_agent": user_agent} if user_agent else None
        )
        db.add(call_event)
        
        await db.commit()
        
        return JoinCallResponse(
            participant_id=str(participant.id),
            session_id=session_id,
            joined_at=participant.joined_at,
            role=participant_role,
            message="Successfully joined the call"
        )
    
    @staticmethod
    async def leave_call(
        db: AsyncSession,
        hospital_id: uuid.UUID,
        session_id: str,
        user_id: uuid.UUID
    ) -> Dict[str, Any]:
        """
        Leave a video call session.
        Sets left_at timestamp and logs LEAVE event.
        """
        # Get participant
        participant_query = (
            select(CallParticipant, VideoSession)
            .join(VideoSession, CallParticipant.session_id == VideoSession.id)
            .where(
                and_(
                    VideoSession.hospital_id == hospital_id,
                    VideoSession.session_id == session_id,
                    CallParticipant.user_id == user_id
                )
            )
        )
        
        result = await db.execute(participant_query)
        participant_data = result.first()
        
        if not participant_data:
            raise ValueError("Participant not found in session")
        
        participant, video_session = participant_data
        
        # Update participant
        now = datetime.utcnow()
        participant.left_at = now
        participant.connection_state = ConnectionState.DISCONNECTED
        
        # Log event
        call_event = CallEvent(
            hospital_id=hospital_id,
            session_id=video_session.id,
            participant_id=participant.id,
            event_type=CallEventType.LEAVE,
            event_time=now,
            triggered_by=user_id
        )
        db.add(call_event)
        
        await db.commit()
        
        return {
            "message": "Successfully left the call",
            "left_at": now,
            "duration_minutes": participant.call_duration_seconds // 60
        }
    
    @staticmethod
    async def handle_call_control(
        db: AsyncSession,
        hospital_id: uuid.UUID,
        session_id: str,
        user_id: uuid.UUID,
        control_type: CallEventType,
        payload: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Handle call control actions (mute, video off, etc.).
        Logs control event for auditing purposes.
        """
        # Get participant
        participant_query = (
            select(CallParticipant, VideoSession)
            .join(VideoSession, CallParticipant.session_id == VideoSession.id)
            .where(
                and_(
                    VideoSession.hospital_id == hospital_id,
                    VideoSession.session_id == session_id,
                    CallParticipant.user_id == user_id
                )
            )
        )
        
        result = await db.execute(participant_query)
        participant_data = result.first()
        
        if not participant_data:
            raise ValueError("Participant not found in session")
        
        participant, video_session = participant_data
        
        # Log control event
        call_event = CallEvent(
            hospital_id=hospital_id,
            session_id=video_session.id,
            participant_id=participant.id,
            event_type=control_type,
            event_time=datetime.utcnow(),
            triggered_by=user_id,
            payload=payload
        )
        db.add(call_event)
        
        await db.commit()
        
        return {
            "message": f"Control action {control_type} recorded",
            "event_time": call_event.event_time
        }
    
    @staticmethod
    async def end_call(
        db: AsyncSession,
        hospital_id: uuid.UUID,
        session_id: str,
        user_id: uuid.UUID,
        end_reason: str = "COMPLETED"
    ) -> Dict[str, Any]:
        """
        End video call session.
        Only doctors and admins can end calls.
        """
        # Get video session with appointment
        session_query = (
            select(VideoSession, TeleAppointment)
            .join(TeleAppointment, VideoSession.tele_appointment_id == TeleAppointment.id)
            .where(
                and_(
                    VideoSession.hospital_id == hospital_id,
                    VideoSession.session_id == session_id
                )
            )
        )
        
        result = await db.execute(session_query)
        session_data = result.first()
        
        if not session_data:
            raise ValueError("Video session not found")
        
        video_session, tele_appointment = session_data
        
        # Check permissions (only doctor can end call)
        if tele_appointment.doctor_id != user_id:
            raise PermissionError("Only the doctor can end the call")
        
        # Update session
        now = datetime.utcnow()
        video_session.status = VideoSessionStatus.ENDED
        video_session.ended_at = now
        video_session.ended_by = user_id
        video_session.end_reason = end_reason
        
        # Update appointment
        tele_appointment.status = TeleAppointmentStatus.COMPLETED
        tele_appointment.session_ended_at = now
        
        if tele_appointment.session_started_at:
            duration = now - tele_appointment.session_started_at
            tele_appointment.actual_duration_minutes = int(duration.total_seconds() / 60)
        
        # Disconnect all participants
        participants_query = (
            select(CallParticipant)
            .where(CallParticipant.session_id == video_session.id)
        )
        
        participants_result = await db.execute(participants_query)
        participants = participants_result.scalars().all()
        
        for participant in participants:
            if participant.connection_state != ConnectionState.DISCONNECTED:
                participant.left_at = now
                participant.connection_state = ConnectionState.DISCONNECTED
        
        # Log end event
        call_event = CallEvent(
            hospital_id=hospital_id,
            session_id=video_session.id,
            event_type=CallEventType.END,
            event_time=now,
            triggered_by=user_id,
            payload={"reason": end_reason}
        )
        db.add(call_event)
        
        await db.commit()
        
        return {
            "message": "Call ended successfully",
            "ended_at": now,
            "total_duration_minutes": tele_appointment.actual_duration_minutes,
            "end_reason": end_reason
        }
    
    @staticmethod
    async def get_session_participants(
        db: AsyncSession,
        hospital_id: uuid.UUID,
        session_id: str,
        user_id: uuid.UUID
    ) -> List[CallParticipantResponse]:
        """
        Get current participants in video session.
        Shows who is currently connected and their status.
        """
        # Get video session
        session_query = (
            select(VideoSession, TeleAppointment)
            .join(TeleAppointment, VideoSession.tele_appointment_id == TeleAppointment.id)
            .where(
                and_(
                    VideoSession.hospital_id == hospital_id,
                    VideoSession.session_id == session_id
                )
            )
        )
        
        result = await db.execute(session_query)
        session_data = result.first()
        
        if not session_data:
            raise ValueError("Video session not found")
        
        video_session, tele_appointment = session_data
        
        # Check access
        if tele_appointment.doctor_id != user_id and tele_appointment.patient_id != user_id:
            raise PermissionError("Access denied to this session")
        
        # Get participants
        participants_query = (
            select(CallParticipant)
            .where(CallParticipant.session_id == video_session.id)
            .order_by(CallParticipant.joined_at)
        )
        
        participants_result = await db.execute(participants_query)
        participants = participants_result.scalars().all()
        
        participant_responses = []
        for participant in participants:
            participant_responses.append(CallParticipantResponse(
                id=str(participant.id),
                user_id=str(participant.user_id),
                role=ParticipantRole(participant.role),
                device_type=DeviceType(participant.device_type),
                connection_state=ConnectionState(participant.connection_state),
                joined_at=participant.joined_at,
                left_at=participant.left_at,
                last_seen_at=participant.last_seen_at,
                connection_quality=participant.connection_quality,
                is_connected=participant.is_connected,
                call_duration_minutes=participant.call_duration_seconds // 60
            ))
        
        return participant_responses
    
    @staticmethod
    async def get_call_summary(
        db: AsyncSession,
        hospital_id: uuid.UUID,
        session_id: str,
        user_id: uuid.UUID
    ) -> CallSummaryResponse:
        """
        Get post-call summary.
        Returns call duration, participants, and session metadata.
        """
        # Get video session
        session_query = (
            select(VideoSession, TeleAppointment)
            .join(TeleAppointment, VideoSession.tele_appointment_id == TeleAppointment.id)
            .where(
                and_(
                    VideoSession.hospital_id == hospital_id,
                    VideoSession.session_id == session_id
                )
            )
        )
        
        result = await db.execute(session_query)
        session_data = result.first()
        
        if not session_data:
            raise ValueError("Video session not found")
        
        video_session, tele_appointment = session_data
        
        # Check access
        if tele_appointment.doctor_id != user_id and tele_appointment.patient_id != user_id:
            raise PermissionError("Access denied to this session")
        
        # Get participants
        participants = await VideoService.get_session_participants(
            db, hospital_id, session_id, user_id
        )
        
        # Get events
        events_query = (
            select(CallEvent)
            .where(CallEvent.session_id == video_session.id)
            .order_by(CallEvent.event_time)
        )
        
        events_result = await db.execute(events_query)
        events = events_result.scalars().all()
        
        event_responses = []
        for event in events:
            event_responses.append(CallEventResponse(
                id=str(event.id),
                event_type=CallEventType(event.event_type),
                event_time=event.event_time,
                user_id=str(event.triggered_by) if event.triggered_by else None,
                participant_role=ParticipantRole(event.participant.role) if event.participant else None,
                payload=event.payload,
                device_type=DeviceType(event.device_type) if event.device_type else None
            ))
        
        return CallSummaryResponse(
            session_id=session_id,
            tele_appointment_id=str(tele_appointment.id),
            started_at=tele_appointment.session_started_at,
            ended_at=tele_appointment.session_ended_at,
            total_duration_minutes=tele_appointment.actual_duration_minutes,
            participants=participants,
            events=event_responses,
            status=VideoSessionStatus(video_session.status)
        )