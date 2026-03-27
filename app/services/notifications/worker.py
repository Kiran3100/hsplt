"""
Notification worker: process QUEUED jobs (scheduled_for <= now), send via provider, update status, write delivery logs.
Run as background task with the app or as a standalone process.
Exponential backoff: on failure, next attempt after 1m, 5m, 15m (handled by rescheduling or max_attempts).
"""
import asyncio
import logging
from datetime import datetime, timedelta

from sqlalchemy import select, and_, or_
from sqlalchemy.ext.asyncio import AsyncSession

from app.database.session import AsyncSessionLocal
from app.models.notifications import NotificationJob
from app.services.notifications import NotificationService

logger = logging.getLogger(__name__)

# Backoff delays in seconds: 1m, 5m, 15m
BACKOFF_SECONDS = [60, 300, 900]


async def process_one_job(db: AsyncSession, job: NotificationJob) -> None:
    """Mark as PROCESSING, run delivery, then commit."""
    job.status = "PROCESSING"
    await db.flush()
    svc = NotificationService(db, job.hospital_id)
    await svc.run_delivery(job)
    await db.commit()


async def run_worker_cycle(batch_size: int = 50) -> int:
    """Fetch QUEUED jobs (scheduled_for <= now or null), process up to batch_size. Returns count processed."""
    async with AsyncSessionLocal() as db:
        now = datetime.utcnow()
        r = await db.execute(
            select(NotificationJob)
            .where(
                and_(
                    NotificationJob.status == "QUEUED",
                    or_(
                        NotificationJob.scheduled_for.is_(None),
                        NotificationJob.scheduled_for <= now,
                    ),
                )
            )
            .order_by(NotificationJob.scheduled_for.asc().nulls_first(), NotificationJob.created_at.asc())
            .limit(batch_size)
        )
        jobs = list(r.scalars().all())
        for job in jobs:
            try:
                await process_one_job(db, job)
            except Exception as e:
                logger.exception("Worker failed for job %s: %s", job.id, e)
                await db.rollback()
        return len(jobs)


async def worker_loop(interval_seconds: int = 30, batch_size: int = 50) -> None:
    """Run worker in a loop with interval_seconds between cycles."""
    logger.info("Notification worker started (interval=%ss, batch=%s)", interval_seconds, batch_size)
    while True:
        try:
            n = await run_worker_cycle(batch_size=batch_size)
            if n:
                logger.info("Processed %d notification jobs", n)
        except Exception as e:
            logger.exception("Worker cycle error: %s", e)
        await asyncio.sleep(interval_seconds)


def start_worker_background(interval_seconds: int = 30, batch_size: int = 50):
    """Start the worker in the event loop (e.g. from FastAPI lifespan)."""
    return asyncio.create_task(worker_loop(interval_seconds=interval_seconds, batch_size=batch_size))
