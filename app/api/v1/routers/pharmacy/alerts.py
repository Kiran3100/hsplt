"""Alerts Router - Expiry & low stock alerts"""
from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Optional
from uuid import UUID

from app.database.session import get_db_session
from app.dependencies.auth import require_pharmacy_staff, require_hospital_admin, require_hospital_context
from app.models.user import User
from app.services.pharmacy_service import PharmacyService
from app.schemas.response import SuccessResponse

router = APIRouter(prefix="/alerts", tags=["Pharmacy - Alerts"])


@router.get("", response_model=dict)
async def list_alerts(
    alert_type: Optional[str] = Query(None),
    status_filter: Optional[str] = Query(None, alias="status"),
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    context: dict = Depends(require_hospital_context),
    db: AsyncSession = Depends(get_db_session)
):
    """List expiry/low stock alerts"""
    service = PharmacyService(db)
    alerts_list = await service.get_alerts(UUID(context["hospital_id"]), alert_type, status_filter, skip, limit)
    return SuccessResponse(success=True, message=f"Found {len(alerts_list)} alerts", data={"alerts": alerts_list}).dict()


@router.post("/{alert_id}/ack", response_model=dict)
async def acknowledge_alert(
    alert_id: UUID,
    current_user: User = Depends(require_pharmacy_staff()),
    db: AsyncSession = Depends(get_db_session)
):
    """Acknowledge alert"""
    service = PharmacyService(db)
    alert = await service.acknowledge_alert(alert_id, current_user.hospital_id, current_user.id)
    await db.commit()
    return SuccessResponse(success=True, message="Alert acknowledged", data={"alert_id": str(alert.id)}).dict()


@router.post("/run-expiry-scan", response_model=dict)
async def run_expiry_scan(
    current_user: User = Depends(require_hospital_admin()),
    db: AsyncSession = Depends(get_db_session)
):
    """Manual trigger for expiry scan. Admin only"""
    service = PharmacyService(db)
    result = await service.run_expiry_scan(current_user.hospital_id)
    await db.commit()
    return SuccessResponse(success=True, message="Expiry scan completed", data=result).dict()
