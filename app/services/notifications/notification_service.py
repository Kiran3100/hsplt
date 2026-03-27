"""
Notification service: outbox pattern, unified send, schedule, OTP, bulk SMS, preferences, history.
API creates job first (never fails on provider down); worker delivers async.
"""
import logging
from datetime import datetime, timedelta, time as dt_time
from uuid import UUID
from typing import Optional, Any

from sqlalchemy import select, and_, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.notifications import (
    NotificationProvider,
    NotificationJob,
    NotificationDeliveryLog,
    NotificationTemplate,
    NotificationPreference,
)
from app.repositories.notifications import NotificationRepository
from app.utils.notifications import get_email_provider, get_sms_provider
from app.services.notifications.template_renderer import render_template
from app.core.enums import NotificationEventType, NotificationJobStatus, NotificationDeliveryLogStatus

logger = logging.getLogger(__name__)

# Rate limit: max OTP sends per phone per window
OTP_RATE_LIMIT_COUNT = 5
OTP_RATE_LIMIT_WINDOW_MINUTES = 15


class NotificationService:
    def __init__(self, db: AsyncSession, hospital_id: Optional[UUID] = None):
        self.db = db
        self.hospital_id = hospital_id
        self.repo = NotificationRepository(db, hospital_id)

    def _provider_config(self, provider: NotificationProvider) -> Optional[dict]:
        if hasattr(provider, "config_") and provider.config_ is not None:
            return provider.config_
        return None

    async def _get_template_and_render(
        self,
        template_key: Optional[str],
        channel: str,
        payload: dict,
        subject_override: Optional[str] = None,
        raw_message: Optional[str] = None,
    ) -> tuple[Optional[str], Optional[str], Optional[UUID]]:
        """Returns (subject, body_rendered, template_id)."""
        if raw_message:
            body = render_template(raw_message, payload)
            return subject_override, body, None
        if not template_key:
            return subject_override, None, None
        template = await self.repo.get_template(template_key, channel=channel)
        if not template:
            return None, None, None
        subj = template.subject or subject_override
        body = render_template(template.body, payload)
        if template.subject:
            subj = render_template(template.subject, payload)
        return subj, body, template.id

    async def send(
        self,
        channel: str,
        to: str,
        idempotency_key: str,
        event_type: str = "GENERAL",
        template_key: Optional[str] = None,
        raw_message: Optional[str] = None,
        subject: Optional[str] = None,
        payload: Optional[dict] = None,
        created_by_user_id: Optional[UUID] = None,
    ) -> NotificationJob:
        """Outbox: create job (QUEUED), return. Does not throw on missing provider."""
        if not self.hospital_id:
            raise ValueError("hospital_id required for send")
        existing = await self.repo.get_job_by_idempotency(idempotency_key)
        if existing:
            return existing
        payload = payload or {}
        subject_rendered, message_rendered, template_id = await self._get_template_and_render(
            template_key, channel, payload, subject_override=subject, raw_message=raw_message
        )
        if not message_rendered and not raw_message:
            message_rendered = "(no template or raw message)"
        job = NotificationJob(
            hospital_id=self.hospital_id,
            event_type=event_type,
            channel=channel.upper(),
            to_address=to,
            template_id=template_id,
            payload_=payload,
            subject_rendered=subject_rendered,
            message_rendered=message_rendered,
            scheduled_for=None,
            status=NotificationJobStatus.QUEUED.value,
            idempotency_key=idempotency_key,
            created_by_user_id=created_by_user_id,
        )
        await self.repo.create_job(job)
        return job

    async def schedule(
        self,
        event_type: str,
        channel: str,
        to: str,
        scheduled_for: datetime,
        idempotency_key: str,
        template_key: Optional[str] = None,
        payload: Optional[dict] = None,
        created_by_user_id: Optional[UUID] = None,
    ) -> NotificationJob:
        if not self.hospital_id:
            raise ValueError("hospital_id required for schedule")
        existing = await self.repo.get_job_by_idempotency(idempotency_key)
        if existing:
            return existing
        payload = payload or {}
        subject_rendered, message_rendered, template_id = await self._get_template_and_render(template_key, channel, payload)
        job = NotificationJob(
            hospital_id=self.hospital_id,
            event_type=event_type,
            channel=channel.upper(),
            to_address=to,
            template_id=template_id,
            payload_=payload,
            subject_rendered=subject_rendered,
            message_rendered=message_rendered or "",
            scheduled_for=scheduled_for,
            status=NotificationJobStatus.QUEUED.value,
            idempotency_key=idempotency_key,
            created_by_user_id=created_by_user_id,
        )
        await self.repo.create_job(job)
        return job

    async def _check_otp_rate_limit(self, phone: str) -> None:
        """Raise if phone has exceeded OTP rate limit."""
        from datetime import datetime, timedelta
        since = datetime.utcnow() - timedelta(minutes=OTP_RATE_LIMIT_WINDOW_MINUTES)
        r = await self.db.execute(
            select(func.count(NotificationJob.id)).where(
                and_(
                    NotificationJob.hospital_id == self.hospital_id,
                    NotificationJob.event_type == NotificationEventType.OTP.value,
                    NotificationJob.to_address == phone,
                    NotificationJob.created_at >= since,
                )
            )
        )
        count = r.scalar() or 0
        if count >= OTP_RATE_LIMIT_COUNT:
            raise ValueError(f"OTP rate limit exceeded for this phone. Try again after {OTP_RATE_LIMIT_WINDOW_MINUTES} minutes.")

    async def otp_send(self, phone: str, purpose: str = "LOGIN") -> dict:
        """Generate OTP, enqueue SMS job. Rate-limited per phone."""
        if not self.hospital_id:
            raise ValueError("hospital_id required")
        await self._check_otp_rate_limit(phone)
        from app.services.otp_service import otp_service
        otp_code = await otp_service.generate_otp(phone, purpose)
        idempotency_key = f"otp:{purpose}:{phone}:{datetime.utcnow().strftime('%Y%m%d%H%M')}"
        await self.send(
            channel="SMS",
            to=phone,
            idempotency_key=idempotency_key,
            event_type=NotificationEventType.OTP.value,
            raw_message=f"Your OTP is {otp_code}. Valid for 10 minutes.",
            payload={"otp": otp_code},
            created_by_user_id=None,
        )
        return {"status": "sent", "message": "OTP sent to phone"}

    async def otp_verify(self, phone: str, otp: str, purpose: str = "LOGIN") -> bool:
        from app.services.otp_service import otp_service
        return await otp_service.verify_otp(phone, otp, purpose)

    async def bulk_sms(
        self,
        phones: list[str],
        message: str,
        idempotency_key: str,
        created_by_user_id: Optional[UUID] = None,
    ) -> list[NotificationJob]:
        if not self.hospital_id:
            raise ValueError("hospital_id required")
        jobs = []
        for i, phone in enumerate(phones):
            key = f"{idempotency_key}:{i}:{phone}"
            job = await self.send(
                channel="SMS",
                to=phone,
                idempotency_key=key,
                event_type=NotificationEventType.BULK_SMS.value,
                raw_message=message,
                created_by_user_id=created_by_user_id,
            )
            jobs.append(job)
        return jobs

    async def get_preferences_me(self, owner_type: str, owner_id: UUID) -> Optional[NotificationPreference]:
        return await self.repo.get_preference(owner_type, owner_id)

    async def upsert_preferences_me(
        self,
        owner_type: str,
        owner_id: UUID,
        email_enabled: bool = True,
        sms_enabled: bool = True,
        whatsapp_enabled: bool = False,
        quiet_hours_start: Optional[dt_time] = None,
        quiet_hours_end: Optional[dt_time] = None,
    ) -> NotificationPreference:
        return await self.repo.upsert_preference(
            owner_type, owner_id,
            email_enabled=email_enabled,
            sms_enabled=sms_enabled,
            whatsapp_enabled=whatsapp_enabled,
            quiet_hours_start=quiet_hours_start,
            quiet_hours_end=quiet_hours_end,
        )

    async def list_history(
        self,
        status: Optional[str] = None,
        from_ts: Optional[datetime] = None,
        to_ts: Optional[datetime] = None,
        event_type: Optional[str] = None,
        to_address_in: Optional[list[str]] = None,
        skip: int = 0,
        limit: int = 50,
    ) -> list[NotificationJob]:
        return await self.repo.list_jobs(
            status=status,
            from_ts=from_ts,
            to_ts=to_ts,
            event_type=event_type,
            to_address_in=to_address_in,
            skip=skip,
            limit=limit,
        )

    async def get_job(self, job_id: UUID) -> Optional[NotificationJob]:
        return await self.repo.get_job(job_id)

    async def cancel_job(self, job_id: UUID) -> Optional[NotificationJob]:
        job = await self.repo.get_job(job_id)
        if not job or job.status != NotificationJobStatus.QUEUED.value:
            return None
        job.status = NotificationJobStatus.CANCELLED.value
        await self.repo.update_job(job)
        return job

    async def retry_job(self, job_id: UUID) -> Optional[NotificationJob]:
        job = await self.repo.get_job(job_id)
        if not job or job.status != NotificationJobStatus.FAILED.value:
            return None
        job.status = NotificationJobStatus.QUEUED.value
        job.last_error = None
        await self.repo.update_job(job)
        return job

    async def list_queue(self, status: str = "QUEUED", limit: int = 100) -> list[NotificationJob]:
        return await self.repo.list_queued_jobs(status=status, scheduled_before=datetime.utcnow(), limit=limit)

    # ---------- Worker: run delivery for one job ----------
    async def run_delivery(self, job: NotificationJob) -> None:
        """Send one job via provider, update status, write delivery log."""
        provider = await self.repo.get_provider_for_channel(job.channel)
        if not provider:
            job.status = NotificationJobStatus.FAILED.value
            job.last_error = "No provider configured"
            job.attempts += 1
            await self.repo.update_job(job)
            await self.repo.create_delivery_log(
                NotificationDeliveryLog(
                    job_id=job.id,
                    provider=None,
                    status=NotificationDeliveryLogStatus.FAILED.value,
                    raw_response={"error": "No provider configured"},
                )
            )
            return
        config = self._provider_config(provider)
        try:
            if job.channel == "EMAIL":
                email_provider = get_email_provider(provider.provider_name, config)
                msg_id = await email_provider.send_email(
                    to=job.to_address,
                    subject=job.subject_rendered or "(no subject)",
                    html=job.message_rendered,
                    text=job.message_rendered,
                )
            else:
                sms_provider = get_sms_provider(provider.provider_name, config)
                msg_id = await sms_provider.send_sms(to=job.to_address, message=job.message_rendered or "")
            job.status = NotificationJobStatus.SENT.value
            job.provider_message_id = msg_id
            job.attempts += 1
            job.last_error = None
            await self.repo.update_job(job)
            await self.repo.create_delivery_log(
                NotificationDeliveryLog(
                    job_id=job.id,
                    provider=provider.provider_name,
                    status=NotificationDeliveryLogStatus.SENT.value,
                    raw_response={"message_id": msg_id},
                )
            )
        except Exception as e:
            job.attempts += 1
            job.last_error = str(e)
            if job.attempts >= job.max_attempts:
                job.status = NotificationJobStatus.FAILED.value
            else:
                job.status = NotificationJobStatus.QUEUED.value
            await self.repo.update_job(job)
            await self.repo.create_delivery_log(
                NotificationDeliveryLog(
                    job_id=job.id,
                    provider=provider.provider_name,
                    status=NotificationDeliveryLogStatus.FAILED.value,
                    raw_response={"error": str(e)},
                )
            )
            logger.exception("Delivery failed for job %s: %s", job.id, e)
