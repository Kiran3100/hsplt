"""
Notification repository: providers, templates, preferences, jobs, delivery_logs.
Hospital-scoped where applicable; global providers/templates when hospital_id is null.
"""
from uuid import UUID
from datetime import datetime, time
from typing import Optional, List
from sqlalchemy import select, and_, or_, func, desc
from sqlalchemy.orm import selectinload
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.notifications import (
    NotificationProvider,
    NotificationTemplate,
    NotificationPreference,
    NotificationJob,
    NotificationDeliveryLog,
)


class NotificationRepository:
    def __init__(self, db: AsyncSession, hospital_id: Optional[UUID] = None):
        self.db = db
        self.hospital_id = hospital_id

    # ---------- Providers ----------
    async def list_providers(
        self,
        provider_type: Optional[str] = None,
        include_global: bool = True,
    ) -> List[NotificationProvider]:
        """Hospital providers + optional global (hospital_id is null)."""
        conditions = []
        if self.hospital_id is not None:
            if include_global:
                conditions.append(
                    or_(
                        NotificationProvider.hospital_id == self.hospital_id,
                        NotificationProvider.hospital_id.is_(None),
                    )
                )
            else:
                conditions.append(NotificationProvider.hospital_id == self.hospital_id)
        else:
            conditions.append(NotificationProvider.hospital_id.is_(None))
        if provider_type:
            conditions.append(NotificationProvider.provider_type == provider_type)
        q = select(NotificationProvider).where(and_(*conditions)).order_by(NotificationProvider.provider_type)
        r = await self.db.execute(q)
        return list(r.scalars().all())

    async def get_provider(self, provider_id: UUID) -> Optional[NotificationProvider]:
        conditions = [NotificationProvider.id == provider_id]
        if self.hospital_id is not None:
            conditions.append(
                or_(
                    NotificationProvider.hospital_id == self.hospital_id,
                    NotificationProvider.hospital_id.is_(None),
                )
            )
        r = await self.db.execute(select(NotificationProvider).where(and_(*conditions)))
        return r.scalar_one_or_none()

    async def get_provider_for_channel(
        self,
        channel: str,
        provider_name: Optional[str] = None,
    ) -> Optional[NotificationProvider]:
        """Prefer hospital-specific provider, fallback to global. channel is EMAIL or SMS."""
        provider_type = "EMAIL" if channel.upper() == "EMAIL" else "SMS"
        conditions = [
            NotificationProvider.provider_type == provider_type,
            NotificationProvider.is_enabled == True,
            NotificationProvider.is_active == True,
        ]
        if provider_name:
            conditions.append(NotificationProvider.provider_name == provider_name)
        # Hospital first
        if self.hospital_id:
            r = await self.db.execute(
                select(NotificationProvider)
                .where(and_(*conditions, NotificationProvider.hospital_id == self.hospital_id))
                .limit(1)
            )
            row = r.scalar_one_or_none()
            if row:
                return row
        # Global
        r = await self.db.execute(
            select(NotificationProvider)
            .where(and_(*conditions, NotificationProvider.hospital_id.is_(None)))
            .limit(1)
        )
        return r.scalar_one_or_none()

    async def create_provider(self, provider: NotificationProvider) -> NotificationProvider:
        self.db.add(provider)
        await self.db.flush()
        return provider

    async def update_provider(self, provider: NotificationProvider) -> NotificationProvider:
        await self.db.flush()
        return provider

    # ---------- Templates ----------
    async def get_template(
        self,
        template_key: str,
        channel: Optional[str] = None,
    ) -> Optional[NotificationTemplate]:
        """Hospital template first, then global."""
        conditions = [
            NotificationTemplate.template_key == template_key,
            NotificationTemplate.is_active == True,
        ]
        if channel:
            conditions.append(NotificationTemplate.channel == channel)
        if self.hospital_id:
            r = await self.db.execute(
                select(NotificationTemplate).where(
                    and_(*conditions, NotificationTemplate.hospital_id == self.hospital_id)
                ).limit(1)
            )
            row = r.scalar_one_or_none()
            if row:
                return row
        r = await self.db.execute(
            select(NotificationTemplate).where(
                and_(*conditions, NotificationTemplate.hospital_id.is_(None))
            ).limit(1)
        )
        return r.scalar_one_or_none()

    async def create_template(self, template: NotificationTemplate) -> NotificationTemplate:
        self.db.add(template)
        await self.db.flush()
        return template

    # ---------- Preferences ----------
    async def get_preference(
        self,
        owner_type: str,
        owner_id: UUID,
    ) -> Optional[NotificationPreference]:
        if not self.hospital_id:
            return None
        r = await self.db.execute(
            select(NotificationPreference).where(
                and_(
                    NotificationPreference.hospital_id == self.hospital_id,
                    NotificationPreference.owner_type == owner_type,
                    NotificationPreference.owner_id == owner_id,
                )
            )
        )
        return r.scalar_one_or_none()

    async def upsert_preference(
        self,
        owner_type: str,
        owner_id: UUID,
        email_enabled: bool = True,
        sms_enabled: bool = True,
        whatsapp_enabled: bool = False,
        quiet_hours_start: Optional[time] = None,
        quiet_hours_end: Optional[time] = None,
    ) -> NotificationPreference:
        pref = await self.get_preference(owner_type, owner_id)
        if pref:
            pref.email_enabled = email_enabled
            pref.sms_enabled = sms_enabled
            pref.whatsapp_enabled = whatsapp_enabled
            pref.quiet_hours_start = quiet_hours_start
            pref.quiet_hours_end = quiet_hours_end
            await self.db.flush()
            return pref
        pref = NotificationPreference(
            hospital_id=self.hospital_id,
            owner_type=owner_type,
            owner_id=owner_id,
            email_enabled=email_enabled,
            sms_enabled=sms_enabled,
            whatsapp_enabled=whatsapp_enabled,
            quiet_hours_start=quiet_hours_start,
            quiet_hours_end=quiet_hours_end,
        )
        self.db.add(pref)
        await self.db.flush()
        return pref

    # ---------- Jobs (outbox) ----------
    async def get_job_by_idempotency(self, idempotency_key: str) -> Optional[NotificationJob]:
        conditions = [NotificationJob.idempotency_key == idempotency_key]
        if self.hospital_id is not None:
            conditions.append(NotificationJob.hospital_id == self.hospital_id)
        r = await self.db.execute(select(NotificationJob).where(and_(*conditions)))
        return r.scalar_one_or_none()

    async def get_job(self, job_id: UUID) -> Optional[NotificationJob]:
        conditions = [NotificationJob.id == job_id]
        if self.hospital_id is not None:
            conditions.append(NotificationJob.hospital_id == self.hospital_id)
        r = await self.db.execute(
            select(NotificationJob).options(selectinload(NotificationJob.delivery_logs)).where(and_(*conditions))
        )
        return r.scalar_one_or_none()

    async def create_job(self, job: NotificationJob) -> NotificationJob:
        self.db.add(job)
        await self.db.flush()
        return job

    async def list_jobs(
        self,
        status: Optional[str] = None,
        owner_type: Optional[str] = None,
        owner_id: Optional[UUID] = None,
        to_address_in: Optional[List[str]] = None,
        from_ts: Optional[datetime] = None,
        to_ts: Optional[datetime] = None,
        event_type: Optional[str] = None,
        skip: int = 0,
        limit: int = 50,
    ) -> List[NotificationJob]:
        conditions = []
        if self.hospital_id is not None:
            conditions.append(NotificationJob.hospital_id == self.hospital_id)
        if status:
            conditions.append(NotificationJob.status == status)
        if event_type:
            conditions.append(NotificationJob.event_type == event_type)
        if from_ts:
            conditions.append(NotificationJob.created_at >= from_ts)
        if to_ts:
            conditions.append(NotificationJob.created_at <= to_ts)
        if to_address_in:
            conditions.append(NotificationJob.to_address.in_(to_address_in))
        q = select(NotificationJob).where(and_(*conditions)).order_by(desc(NotificationJob.created_at)).offset(skip).limit(limit)
        r = await self.db.execute(q)
        return list(r.scalars().all())

    async def list_queued_jobs(
        self,
        status: str = "QUEUED",
        scheduled_before: Optional[datetime] = None,
        limit: int = 100,
    ) -> List[NotificationJob]:
        conditions = [NotificationJob.status == status]
        if self.hospital_id is not None:
            conditions.append(NotificationJob.hospital_id == self.hospital_id)
        if scheduled_before is not None:
            conditions.append(
                or_(
                    NotificationJob.scheduled_for.is_(None),
                    NotificationJob.scheduled_for <= scheduled_before,
                )
            )
        q = (
            select(NotificationJob)
            .where(and_(*conditions))
            .order_by(NotificationJob.scheduled_for.asc().nulls_first(), NotificationJob.created_at.asc())
            .limit(limit)
        )
        r = await self.db.execute(q)
        return list(r.scalars().all())

    async def update_job(self, job: NotificationJob) -> NotificationJob:
        await self.db.flush()
        return job

    async def create_delivery_log(self, log: NotificationDeliveryLog) -> NotificationDeliveryLog:
        self.db.add(log)
        await self.db.flush()
        return log
