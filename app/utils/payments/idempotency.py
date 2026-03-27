"""
DB-backed idempotency for payment operations.
Replaces the previous in-memory dict (_cache = {}) which was unsafe:
- Reset on every server restart
- Did not work across multiple worker processes
- Allowed duplicate payments after any deployment

This implementation stores idempotency keys in the database so they
survive restarts and are shared across all worker processes.
"""
import logging
from datetime import datetime, timedelta
from uuid import UUID
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, text

logger = logging.getLogger(__name__)

# TTL for idempotency keys (24 hours is standard for payment gateways)
IDEMPOTENCY_TTL_HOURS = 24


async def check_or_set_db(db: AsyncSession, key: str, hospital_id: UUID) -> bool:
    """
    DB-backed idempotency check.

    Returns True if this key is new (proceed with operation).
    Returns False if this key already exists (return cached result).

    Uses PostgreSQL INSERT ... ON CONFLICT DO NOTHING for atomic check-and-set.
    Safe under concurrent requests from multiple workers.
    """
    try:
        expiry = datetime.utcnow() + timedelta(hours=IDEMPOTENCY_TTL_HOURS)
        result = await db.execute(
            text("""
                INSERT INTO payment_idempotency_keys (key, hospital_id, created_at, expires_at)
                VALUES (:key, :hospital_id, NOW(), :expires_at)
                ON CONFLICT (key) DO NOTHING
                RETURNING key
            """),
            {"key": key, "hospital_id": str(hospital_id), "expires_at": expiry}
        )
        row = result.fetchone()
        return row is not None  # True = new key (proceed), False = duplicate
    except Exception as e:
        logger.error(f"Idempotency DB check failed for key={key}: {e}")
        # Fail open — allow the request to proceed but log the error
        return True


async def cleanup_expired_keys(db: AsyncSession) -> int:
    """Remove expired idempotency keys. Call from a scheduled task."""
    try:
        result = await db.execute(
            text("DELETE FROM payment_idempotency_keys WHERE expires_at < NOW()")
        )
        await db.commit()
        count = result.rowcount
        logger.info(f"Cleaned up {count} expired idempotency keys")
        return count
    except Exception as e:
        logger.error(f"Idempotency cleanup failed: {e}")
        return 0


# ─── Backward-compatibility shim ────────────────────────────────────────────
# The old synchronous check_or_set(key) is kept for any legacy callers but
# logs a warning — callers should migrate to check_or_set_db().
import time
_legacy_cache: dict = {}


def check_or_set(key: str) -> bool:
    """
    DEPRECATED: in-memory idempotency, not safe for production.
    Use check_or_set_db() instead.
    """
    logger.warning(
        f"DEPRECATED: Using in-memory idempotency for key={key}. "
        "Migrate to check_or_set_db() for production safety."
    )
    now = time.time()
    if key in _legacy_cache:
        return False
    _legacy_cache[key] = now
    return True
