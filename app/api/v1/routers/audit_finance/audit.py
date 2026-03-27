"""
Audit trail for financial transactions.
RBAC: Hospital Admin; Super Admin platform view.
"""
from uuid import UUID
from datetime import datetime
from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.database.session import get_db_session
from app.core.security import get_current_user
from app.api.deps import require_hospital_context, require_roles
from app.core.enums import UserRole
from app.models.user import User
from app.schemas.billing import FinanceAuditQuery, FinanceAuditResponse
from app.schemas.response import SuccessResponse
from app.repositories.billing.billing_repository import BillingRepository

router = APIRouter(prefix="/finance/audit", tags=["M1.9 Finance - Audit Trail"])
require_admin = require_roles(UserRole.HOSPITAL_ADMIN)


@router.get("", response_model=dict)
async def list_audit_logs(
    entity_type: str | None = Query(None),
    action: str | None = Query(None),
    date_from: str | None = Query(None),
    date_to: str | None = Query(None),
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=100),
    context: dict = Depends(require_hospital_context),
    user: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db_session),
):
    """List finance audit logs with filters and pagination."""
    repo = BillingRepository(db, UUID(context["hospital_id"]))
    date_from_d = datetime.fromisoformat(date_from) if date_from else None
    date_to_d = datetime.fromisoformat(date_to) if date_to else None
    logs = await repo.list_audit_logs(entity_type=entity_type, action=action, date_from=date_from_d, date_to=date_to_d, skip=skip, limit=limit)
    data = [
        {
            "id": str(l.id),
            "hospital_id": str(l.hospital_id),
            "entity_type": l.entity_type,
            "entity_id": str(l.entity_id),
            "action": l.action,
            "old_value": l.old_value,
            "new_value": l.new_value,
            "performed_by_user_id": str(l.performed_by_user_id),
            "performed_at": l.performed_at.isoformat() if l.performed_at else None,
            "ip_address": l.ip_address,
        }
        for l in logs
    ]
    return SuccessResponse(success=True, message=f"Found {len(logs)} audit logs", data=data).dict()


@router.get("/{audit_id}", response_model=dict)
async def get_audit_log(
    audit_id: UUID,
    context: dict = Depends(require_hospital_context),
    user: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db_session),
):
    """Get single audit log by ID."""
    from sqlalchemy import select
    from app.models.billing import FinanceAuditLog
    r = await db.execute(
        select(FinanceAuditLog).where(
            FinanceAuditLog.id == audit_id,
            FinanceAuditLog.hospital_id == UUID(context["hospital_id"]),
        )
    )
    log = r.scalar_one_or_none()
    if not log:
        from fastapi import HTTPException, status
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail={"code": "AUDIT_NOT_FOUND", "message": "Audit log not found"})
    data = {
        "id": str(log.id),
        "hospital_id": str(log.hospital_id),
        "entity_type": log.entity_type,
        "entity_id": str(log.entity_id),
        "action": log.action,
        "old_value": log.old_value,
        "new_value": log.new_value,
        "performed_by_user_id": str(log.performed_by_user_id),
        "performed_at": log.performed_at.isoformat() if log.performed_at else None,
        "ip_address": log.ip_address,
    }
    return SuccessResponse(success=True, message="Audit log retrieved", data=data).dict()
