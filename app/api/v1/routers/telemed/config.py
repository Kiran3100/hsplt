"""
Telemedicine provider config. Hospital Admin can update; any authenticated user in hospital can view.
"""
import uuid
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db_session
from app.api.deps import get_current_user, require_hospital_context, require_roles
from app.core.enums import UserRole
from app.models.user import User
from app.schemas.telemed import TelemedProviderConfigResponse, TelemedProviderConfigUpdate
from app.schemas.response import SuccessResponse
from app.repositories.telemed_repository import TelemedProviderConfigRepository

router = APIRouter(prefix="/config", tags=["Telemedicine - Provider Config"])


def _config_to_response(row) -> dict:
    return {
        "hospital_id": str(row.hospital_id),
        "default_provider": row.default_provider,
        "enabled_providers": row.enabled_providers or ["WEBRTC"],
        "settings_json": row.settings_json or {},
        "updated_at": row.updated_at.isoformat() if row.updated_at else None,
    }


@router.get("", response_model=dict)
async def get_provider_config(
    context: dict = Depends(require_hospital_context),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_session),
):
    """Get current hospital's telemed provider config. Any authenticated user in hospital context."""
    hospital_id = uuid.UUID(context["hospital_id"])
    repo = TelemedProviderConfigRepository(db, hospital_id)
    row = await repo.get_by_hospital()
    if not row:
        return SuccessResponse(
            success=True,
            message="Provider config (default)",
            data={
                "hospital_id": str(hospital_id),
                "default_provider": "WEBRTC",
                "enabled_providers": ["WEBRTC"],
                "settings_json": {},
                "updated_at": None,
            },
        ).model_dump()
    return SuccessResponse(
        success=True,
        message="Provider config retrieved",
        data=_config_to_response(row),
    ).model_dump()


@router.patch("", response_model=dict)
async def update_provider_config(
    body: TelemedProviderConfigUpdate,
    context: dict = Depends(require_hospital_context),
    current_user: User = Depends(require_roles(UserRole.HOSPITAL_ADMIN)),
    db: AsyncSession = Depends(get_db_session),
):
    """Update current hospital's telemed provider config. Hospital Admin only."""
    hospital_id = uuid.UUID(context["hospital_id"])
    repo = TelemedProviderConfigRepository(db, hospital_id)
    row = await repo.create_or_update(
        default_provider=body.default_provider,
        enabled_providers=body.enabled_providers,
        settings_json=body.settings_json,
    )
    await db.commit()
    return SuccessResponse(
        success=True,
        message="Provider config updated",
        data=_config_to_response(row),
    ).model_dump()
