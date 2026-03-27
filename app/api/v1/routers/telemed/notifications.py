"""
Telemedicine in-app notifications. GET /me, PATCH /me/{id}/read for current user.
"""
import uuid
from typing import Optional
from fastapi import APIRouter, Depends, Query, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db_session
from app.api.deps import get_current_user, require_hospital_context
from app.models.user import User
from app.schemas.response import SuccessResponse
from app.services.telemed_notification_service import TelemedNotificationService

router = APIRouter(prefix="/notifications", tags=["Telemedicine - Notifications"])


def _notification_to_item(n):
    return {
        "id": str(n.id),
        "session_id": str(n.session_id) if n.session_id else None,
        "event_type": n.event_type,
        "title": n.title,
        "body": n.body,
        "read_at": n.read_at.isoformat() if n.read_at else None,
        "created_at": n.created_at.isoformat() if n.created_at else None,
    }


@router.get("/me", response_model=dict)
async def list_my_notifications(
    context: dict = Depends(require_hospital_context),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_session),
    read: Optional[bool] = Query(None, description="Filter: true=read, false=unread"),
    limit: int = Query(50, ge=1, le=100),
):
    """List in-app telemed notifications for the current user. Any authenticated user in hospital context."""
    hospital_id = uuid.UUID(context["hospital_id"])
    service = TelemedNotificationService(db, hospital_id)
    items = await service.list_for_user(
        recipient_user_id=current_user.id,
        read_filter=read,
        limit=limit,
    )
    return SuccessResponse(
        success=True,
        message="Notifications retrieved",
        data={"items": [_notification_to_item(n) for n in items]},
    ).model_dump()


@router.patch("/me/{notification_id}/read", response_model=dict)
async def mark_notification_read(
    notification_id: uuid.UUID,
    context: dict = Depends(require_hospital_context),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_session),
):
    """Mark a notification as read. Current user must be the recipient. Returns 404 if not found."""
    hospital_id = uuid.UUID(context["hospital_id"])
    service = TelemedNotificationService(db, hospital_id)
    n = await service.mark_as_read(notification_id, current_user.id)
    if not n:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Notification not found")
    await db.commit()
    return SuccessResponse(
        success=True,
        message="Notification marked as read",
        data=_notification_to_item(n),
    ).model_dump()
